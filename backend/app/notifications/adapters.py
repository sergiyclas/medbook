import smtplib
import ssl
from email.message import EmailMessage as MimeMessage

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.notifications.ports import DeliveryError, EmailMessage, SmsMessage

# GoF Adapter (object adapter). The adaptees – smtplib and the Twilio SDK – have
# their own APIs, message formats and exception hierarchies. Each adapter
# implements our Sender interface, translates the message into the library's
# format and maps library errors onto DeliveryError(transient=...), so the
# dispatcher never imports smtplib or twilio.


class SmtpEmailAdapter:
    def __init__(
        self, host: str, port: int, username: str, password: str, sender: str, timeout: float = 20
    ) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.username, self.password, self.sender = username, password, sender

    def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self.sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text)
        mime.add_alternative(message.html, subtype="html")
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(self.username, self.password)
                smtp.send_message(mime)
        except smtplib.SMTPAuthenticationError as exc:
            raise DeliveryError(f"SMTP login rejected: {exc.smtp_code}", transient=False) from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise DeliveryError("SMTP server refused the recipient", transient=False) from exc
        except smtplib.SMTPResponseException as exc:
            # 4xx replies are temporary by definition (RFC 5321), 5xx are final
            raise DeliveryError(
                f"SMTP error {exc.smtp_code}", transient=400 <= exc.smtp_code < 500
            ) from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise DeliveryError(f"SMTP connection failed: {exc}", transient=True) from exc


class TwilioSmsAdapter:
    def __init__(
        self, account_sid: str, auth_token: str, from_number: str, client: Client | None = None
    ) -> None:
        self.client = client or Client(account_sid, auth_token)
        self.from_number = from_number

    def send(self, message: SmsMessage) -> None:
        try:
            self.client.messages.create(to=message.to, from_=self.from_number, body=message.text)
        except TwilioRestException as exc:
            # 429 (rate limit) and 5xx are worth retrying; other 4xx mean a bad
            # number, unverified trial recipient, blocked country and the like
            transient = exc.status == 429 or exc.status >= 500
            raise DeliveryError(f"Twilio error {exc.code}: {exc.msg}", transient) from exc
        except OSError as exc:  # requests' network errors derive from OSError
            raise DeliveryError(f"Twilio unreachable: {exc}", transient=True) from exc
