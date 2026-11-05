import smtplib

import pytest
from pydantic import SecretStr
from twilio.base.exceptions import TwilioRestException

from app.core.config import Settings
from app.notifications import adapters
from app.notifications.adapters import SmtpEmailAdapter, TwilioSmsAdapter
from app.notifications.console import ConsoleEmailSender, ConsoleSmsSender
from app.notifications.decorators import LoggingSender, RetryingSender, mask
from app.notifications.factory import (
    ConfigurationError,
    ConsoleTransportFactory,
    LiveTransportFactory,
    make_transport_factory,
)
from app.notifications.ports import DeliveryError, EmailMessage, SmsMessage

MAIL = EmailMessage("olena@clinic.example", "Тема", "Текст", "<p>Текст</p>")
SMS = SmsMessage("+380671234567", "Нагадування")

LIVE = dict(
    notification_mode="live",
    smtp_username="clinic@gmail.example",
    smtp_password=SecretStr("app-password"),
    twilio_account_sid="AC123",
    twilio_auth_token=SecretStr("token"),
    twilio_from_number="+15005550006",
)


# ---------- Abstract Factory ----------
def test_console_mode_builds_the_console_family() -> None:
    factory = make_transport_factory(Settings(notification_mode="console"))
    assert isinstance(factory, ConsoleTransportFactory)
    email, sms = factory.create_email_sender(), factory.create_sms_sender()
    assert isinstance(email, LoggingSender) and isinstance(email.inner, ConsoleEmailSender)
    assert isinstance(sms, LoggingSender) and isinstance(sms.inner, ConsoleSmsSender)


def test_live_mode_builds_decorated_adapters() -> None:
    factory = make_transport_factory(Settings(**LIVE))
    assert isinstance(factory, LiveTransportFactory)
    email, sms = factory.create_email_sender(), factory.create_sms_sender()
    # Logging(Retrying(adapter)) – one log line per message, retries inside
    assert isinstance(email.inner, RetryingSender)
    assert isinstance(email.inner.inner, SmtpEmailAdapter)
    assert email.inner.inner.sender == "clinic@gmail.example"
    assert isinstance(sms.inner.inner, TwilioSmsAdapter)


def test_live_mode_refuses_to_start_half_configured() -> None:
    with pytest.raises(ConfigurationError) as err:
        make_transport_factory(Settings(**LIVE | {"twilio_auth_token": SecretStr("")}))
    assert "TWILIO_AUTH_TOKEN" in str(err.value)


# ---------- Decorator ----------
class Flaky:
    def __init__(self, failures: list[DeliveryError]) -> None:
        self.failures = failures
        self.calls = 0

    def send(self, message) -> None:
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)


def test_retrying_sender_gets_through_a_temporary_blip() -> None:
    inner = Flaky([DeliveryError("timeout", transient=True)])
    pauses: list[float] = []
    RetryingSender(inner, attempts=3, delay_seconds=0.5, sleep=pauses.append).send(SMS)
    assert inner.calls == 2
    assert pauses == [0.5]


def test_retrying_sender_gives_up_on_permanent_errors_at_once() -> None:
    inner = Flaky([DeliveryError("bad number", transient=False)])
    with pytest.raises(DeliveryError):
        RetryingSender(inner, sleep=lambda _: None).send(SMS)
    assert inner.calls == 1


def test_retrying_sender_stops_after_the_last_attempt() -> None:
    inner = Flaky([DeliveryError("down", transient=True)] * 5)
    with pytest.raises(DeliveryError):
        RetryingSender(inner, attempts=3, sleep=lambda _: None).send(SMS)
    assert inner.calls == 3


def test_logging_sender_masks_recipients(caplog) -> None:
    caplog.set_level("INFO", logger="medbook.notifications")
    LoggingSender(Flaky([]), "SMS").send(SMS)
    assert "+38067***67" in caplog.text
    assert "1234567" not in caplog.text
    assert mask("olena@clinic.example") == "o***@clinic.example"


# ---------- Adapter: smtplib ----------
class FakeSMTP:
    instances: list["FakeSMTP"] = []
    fail_with: Exception | None = None

    def __init__(self, host, port, timeout) -> None:
        self.host, self.port, self.calls, self.sent = host, port, [], None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        pass

    def starttls(self, context) -> None:
        self.calls.append("starttls")

    def login(self, user, password) -> None:
        self.calls.append(f"login:{user}")
        if FakeSMTP.fail_with:
            raise FakeSMTP.fail_with

    def send_message(self, msg) -> None:
        self.sent = msg


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.instances, FakeSMTP.fail_with = [], None
    monkeypatch.setattr(adapters.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def smtp_adapter() -> SmtpEmailAdapter:
    return SmtpEmailAdapter("smtp.gmail.com", 587, "clinic@gmail.example", "pw", "MedBook <c@g.e>")


def test_smtp_adapter_translates_our_message_into_mime(fake_smtp) -> None:
    smtp_adapter().send(MAIL)
    [conn] = fake_smtp.instances
    assert (conn.host, conn.port) == ("smtp.gmail.com", 587)
    assert conn.calls == ["starttls", "login:clinic@gmail.example"]
    assert conn.sent["To"] == "olena@clinic.example"
    assert conn.sent["Subject"] == "Тема"
    assert conn.sent.get_body(("html",)).get_content().strip() == "<p>Текст</p>"


@pytest.mark.parametrize(
    ("error", "transient"),
    [
        (smtplib.SMTPAuthenticationError(535, b"bad credentials"), False),
        (smtplib.SMTPResponseException(451, b"try later"), True),
        (smtplib.SMTPResponseException(550, b"no such user"), False),
        (ConnectionRefusedError("refused"), True),
    ],
)
def test_smtp_adapter_maps_library_errors(fake_smtp, error, transient) -> None:
    fake_smtp.fail_with = error
    with pytest.raises(DeliveryError) as err:
        smtp_adapter().send(MAIL)
    assert err.value.transient is transient


# ---------- Adapter: Twilio SDK ----------
class FakeMessages:
    def __init__(self, error: Exception | None = None) -> None:
        self.error, self.created = error, []

    def create(self, **kwargs) -> None:
        if self.error:
            raise self.error
        self.created.append(kwargs)


class FakeTwilio:
    def __init__(self, error: Exception | None = None) -> None:
        self.messages = FakeMessages(error)


def test_twilio_adapter_calls_the_sdk_with_its_own_argument_names() -> None:
    client = FakeTwilio()
    TwilioSmsAdapter("AC1", "t", "+15005550006", client=client).send(SMS)
    assert client.messages.created == [
        {"to": "+380671234567", "from_": "+15005550006", "body": "Нагадування"}
    ]


@pytest.mark.parametrize(("status", "transient"), [(400, False), (429, True), (503, True)])
def test_twilio_adapter_maps_http_status(status: int, transient: bool) -> None:
    error = TwilioRestException(status, "/Messages", "nope", code=21608)
    adapter = TwilioSmsAdapter("AC1", "t", "+1", client=FakeTwilio(error))
    with pytest.raises(DeliveryError) as err:
        adapter.send(SMS)
    assert err.value.transient is transient
