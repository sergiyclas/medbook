from abc import ABC, abstractmethod
from datetime import datetime
from html import escape

from app.core.clock import to_local
from app.domain.enums import NotificationKind
from app.models import Appointment, Patient
from app.notifications.ports import EmailMessage, SmsMessage

WEEKDAYS = ["понеділок", "вівторок", "середа", "четвер", "п'ятниця", "субота", "неділя"]
MONTHS = [
    "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
]  # fmt: skip

SMS_MAX_LENGTH = 134  # two concatenated UCS-2 segments – Cyrillic text


def long_date(moment: datetime) -> str:
    local = to_local(moment)
    day = f"{local.day} {MONTHS[local.month - 1]} {local:%Y}"
    return f"{WEEKDAYS[local.weekday()]}, {day}, {local:%H:%M}"


def initials(last: str, first: str, middle: str | None) -> str:
    return f"{last} {first[:1]}." + (f" {middle[:1]}." if middle else "")


# GoF Builder: the steps every notification is made of. Concrete builders turn
# the same steps into different representations; a builder may ignore a step
# that makes no sense for its format (an SMS has no room for a greeting).
# Optional steps are deliberately empty by default, as GoF suggests, hence noqa.
class MessageBuilder(ABC):
    @abstractmethod
    def set_recipient(self, patient: Patient) -> None: ...

    @abstractmethod
    def set_title(self, title: str) -> None: ...

    def add_greeting(self) -> None:  # noqa: B027
        pass

    def add_paragraph(self, text: str) -> None:  # noqa: B027
        pass

    @abstractmethod
    def add_visit(self, appt: Appointment) -> None: ...

    def add_link(self, label: str, url: str) -> None:  # noqa: B027
        pass

    def add_signature(self, clinic: str) -> None:  # noqa: B027
        pass


class EmailMessageBuilder(MessageBuilder):
    def __init__(self) -> None:
        self._to = self._title = ""
        self._text: list[str] = []
        self._html: list[str] = []

    def set_recipient(self, patient: Patient) -> None:
        self._to = patient.email

    def set_title(self, title: str) -> None:
        self._title = title
        self._html.append(f'<h2 style="color:#0f5f6e;margin:0 0 16px">{escape(title)}</h2>')

    def add_greeting(self) -> None:
        self._add("Доброго дня!")

    def add_paragraph(self, text: str) -> None:
        self._add(text)

    def add_visit(self, appt: Appointment) -> None:
        doctor = appt.doctor
        rows = [
            ("Пацієнт", appt.patient.full_name),
            ("Лікар", f"{doctor.full_name} ({doctor.specialization.name.lower()})"),
            ("Дата і час", long_date(appt.starts_at)),
        ]
        if doctor.room:
            rows.append(("Кабінет", doctor.room))
        self._text.extend(f"{label}: {value}" for label, value in rows)
        self._text.append("")
        cells = "".join(
            f'<tr><td style="padding:4px 16px 4px 0;color:#5b6b70">{escape(label)}</td>'
            f"<td><b>{escape(value)}</b></td></tr>"
            for label, value in rows
        )
        self._html.append(
            f'<table style="margin:8px 0 16px;border-collapse:collapse">{cells}</table>'
        )

    def add_link(self, label: str, url: str) -> None:
        self._text.extend([f"{label}: {url}", ""])
        self._html.append(
            f'<p><a href="{escape(url, quote=True)}" style="background:#0f7a8a;color:#fff;'
            f'padding:10px 18px;border-radius:6px;text-decoration:none">{escape(label)}</a></p>'
        )

    def add_signature(self, clinic: str) -> None:
        self._text.append(f"З повагою,\n{clinic}")
        self._html.append(
            f'<p style="color:#5b6b70;margin-top:24px">З повагою,<br>{escape(clinic)}</p>'
        )

    def get_result(self) -> EmailMessage:
        body = "".join(self._html)
        html = (
            f'<div style="font-family:Arial,sans-serif;font-size:15px;color:#1d2b2f">{body}</div>'
        )
        return EmailMessage(self._to, self._title, "\n".join(self._text).strip(), html)

    def _add(self, text: str) -> None:
        self._text.extend([text, ""])
        self._html.append(f"<p>{escape(text)}</p>")


class SmsMessageBuilder(MessageBuilder):
    def __init__(self, sender_name: str) -> None:
        self._sender_name = sender_name
        self._to = self._title = self._visit = ""

    def set_recipient(self, patient: Patient) -> None:
        self._to = patient.phone

    def set_title(self, title: str) -> None:
        self._title = title

    def add_visit(self, appt: Appointment) -> None:
        d, local = appt.doctor, to_local(appt.starts_at)
        parts = [
            f"{local:%d.%m} о {local:%H:%M}",
            initials(d.last_name, d.first_name, d.middle_name),
            d.specialization.name.lower(),
        ]
        if d.room:
            parts.append(f"каб. {d.room}")
        self._visit = ", ".join(parts)

    def get_result(self) -> SmsMessage:
        text = f"{self._sender_name}. {self._title}: {self._visit}"
        if len(text) > SMS_MAX_LENGTH:
            text = text[: SMS_MAX_LENGTH - 1] + "…"
        return SmsMessage(self._to, text)


# GoF Director: knows which steps, in which order, make up each kind of
# notification – and nothing about e-mail or SMS formats. The caller picks the
# builder for the channel and takes the finished product from that builder.
class MessageComposer:
    def __init__(self, clinic_name: str, app_url: str) -> None:
        self.clinic_name = clinic_name
        self.app_url = app_url.rstrip("/")

    def compose(self, kind: NotificationKind, appt: Appointment, builder: MessageBuilder) -> None:
        builder.set_recipient(appt.patient)
        match kind:
            case NotificationKind.CONFIRMATION:
                builder.set_title("Ви записані на прийом")
                builder.add_greeting()
                builder.add_paragraph("Ваш запис до лікаря створено.")
                builder.add_visit(appt)
                builder.add_paragraph(
                    "Якщо плани зміняться, скасуйте або перенесіть запис у кабінеті пацієнта."
                )
                builder.add_link("Мої записи", f"{self.app_url}/my")
            case NotificationKind.REMINDER:
                builder.set_title("Нагадування про прийом")
                builder.add_greeting()
                builder.add_visit(appt)
                builder.add_paragraph(
                    "Будь ласка, приходьте за 10 хвилин до початку та візьміть із собою документ, "
                    "що посвідчує особу."
                )
                builder.add_link("Мої записи", f"{self.app_url}/my")
            case NotificationKind.CANCELLATION:
                builder.set_title("Прийом скасовано")
                builder.add_greeting()
                builder.add_paragraph("На жаль, ваш прийом скасовано.")
                builder.add_visit(appt)
                if appt.cancellation_reason:
                    builder.add_paragraph(f"Причина: {appt.cancellation_reason}")
                builder.add_link("Записатися знову", f"{self.app_url}/doctors")
        builder.add_signature(self.clinic_name)
