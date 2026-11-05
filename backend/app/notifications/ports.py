from dataclasses import dataclass
from typing import Protocol

# The interfaces the rest of the system talks to. Concrete transports (SMTP,
# Twilio, console) hide behind them – GRASP Protected Variations: switching the
# SMS provider touches one adapter, not the dispatcher or the message builders.


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str


@dataclass(frozen=True)
class SmsMessage:
    to: str
    text: str


class DeliveryError(Exception):
    # transient – worth trying again later (network, 4xx SMTP, Twilio 5xx/429);
    # permanent – will fail the same way every time (bad credentials, bad number)
    def __init__(self, message: str, transient: bool) -> None:
        super().__init__(message)
        self.transient = transient


# One protocol, two separate interfaces (ISP): the e-mail side never sees SMS
# methods and vice versa. Senders and their decorators all conform to it.
class Sender[M](Protocol):
    def send(self, message: M) -> None: ...


type EmailSender = Sender[EmailMessage]
type SmsSender = Sender[SmsMessage]
