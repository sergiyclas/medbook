from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.notifications.adapters import SmtpEmailAdapter, TwilioSmsAdapter
from app.notifications.console import ConsoleEmailSender, ConsoleSmsSender
from app.notifications.decorators import LoggingSender, RetryingSender
from app.notifications.ports import EmailSender, SmsSender


class ConfigurationError(RuntimeError):
    pass


# GoF Abstract Factory. A family of products – one e-mail sender and one SMS
# sender – is created together, so the two channels can never be mixed by
# accident (real e-mail with fake SMS). Each create_* method is a Factory Method.
# The factory also assembles each product: adapter wrapped in decorators.
class TransportFactory(ABC):
    @abstractmethod
    def create_email_sender(self) -> EmailSender: ...

    @abstractmethod
    def create_sms_sender(self) -> SmsSender: ...


class ConsoleTransportFactory(TransportFactory):
    def create_email_sender(self) -> EmailSender:
        return LoggingSender(ConsoleEmailSender(), "e-mail")

    def create_sms_sender(self) -> SmsSender:
        return LoggingSender(ConsoleSmsSender(), "SMS")


class LiveTransportFactory(TransportFactory):
    def __init__(self, settings: Settings) -> None:
        missing = [
            name
            for name, value in (
                ("SMTP_USERNAME", settings.smtp_username),
                ("SMTP_PASSWORD", settings.smtp_password.get_secret_value()),
                ("TWILIO_ACCOUNT_SID", settings.twilio_account_sid),
                ("TWILIO_AUTH_TOKEN", settings.twilio_auth_token.get_secret_value()),
                ("TWILIO_FROM_NUMBER", settings.twilio_from_number),
            )
            if not value
        ]
        if missing:
            raise ConfigurationError(
                "NOTIFICATION_MODE=live needs these variables in .env: " + ", ".join(missing)
            )
        self.settings = settings

    def create_email_sender(self) -> EmailSender:
        s = self.settings
        adapter = SmtpEmailAdapter(
            s.smtp_host,
            s.smtp_port,
            s.smtp_username,
            s.smtp_password.get_secret_value(),
            s.mail_from or s.smtp_username,
        )
        return LoggingSender(RetryingSender(adapter), "e-mail")

    def create_sms_sender(self) -> SmsSender:
        s = self.settings
        adapter = TwilioSmsAdapter(
            s.twilio_account_sid, s.twilio_auth_token.get_secret_value(), s.twilio_from_number
        )
        return LoggingSender(RetryingSender(adapter), "SMS")


def make_transport_factory(settings: Settings) -> TransportFactory:
    if settings.notification_mode == "live":
        return LiveTransportFactory(settings)
    return ConsoleTransportFactory()


# GoF notes that a concrete factory is usually a Singleton – one per process,
# chosen once from the configuration (itself a Singleton).
@lru_cache
def get_transport_factory() -> TransportFactory:
    return make_transport_factory(get_settings())
