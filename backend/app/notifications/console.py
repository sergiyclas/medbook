import logging

from app.notifications.decorators import mask
from app.notifications.ports import EmailMessage, SmsMessage

log = logging.getLogger("medbook.notifications")


# Demo transports: implement the same Sender interface but only print the
# message, so the whole pipeline runs without SMTP or Twilio accounts.
class ConsoleEmailSender:
    def send(self, message: EmailMessage) -> None:
        log.info("[e-mail to %s] %s\n%s", mask(message.to), message.subject, message.text)


class ConsoleSmsSender:
    def send(self, message: SmsMessage) -> None:
        log.info("[SMS to %s] %s", mask(message.to), message.text)
