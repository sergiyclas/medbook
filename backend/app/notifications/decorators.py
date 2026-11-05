import logging
import time
from collections.abc import Callable

from app.notifications.ports import DeliveryError, Sender

log = logging.getLogger("medbook.notifications")


# GoF Decorator. Each decorator is itself a Sender and wraps another Sender, so
# behaviour is stacked at assembly time without touching the adapters:
#   LoggingSender(RetryingSender(TwilioSmsAdapter(...)))
# logs one line per logical message, however many attempts the retry makes.
class SenderDecorator[M]:
    def __init__(self, inner: Sender[M]) -> None:
        self.inner = inner

    def send(self, message: M) -> None:
        self.inner.send(message)


# A few quick in-process retries for blips (a dropped TCP connection). Longer
# outages are handled one level up: the worker reschedules the notification
# with a growing delay, up to notification_max_attempts.
class RetryingSender[M](SenderDecorator[M]):
    def __init__(
        self,
        inner: Sender[M],
        attempts: int = 3,
        delay_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(inner)
        self.attempts = attempts
        self.delay_seconds = delay_seconds
        self.sleep = sleep

    def send(self, message: M) -> None:
        for attempt in range(1, self.attempts + 1):
            try:
                self.inner.send(message)
                return
            except DeliveryError as exc:
                if not exc.transient or attempt == self.attempts:
                    raise
                self.sleep(self.delay_seconds * attempt)


class LoggingSender[M](SenderDecorator[M]):
    def __init__(self, inner: Sender[M], channel: str) -> None:
        super().__init__(inner)
        self.channel = channel

    def send(self, message: M) -> None:
        recipient = mask(getattr(message, "to", "?"))
        try:
            self.inner.send(message)
        except DeliveryError as exc:
            kind = "temporary" if exc.transient else "permanent"
            log.warning("%s to %s failed (%s): %s", self.channel, recipient, kind, exc)
            raise
        log.info("%s to %s delivered", self.channel, recipient)


# Logs are not the place for full contact details: o***@example.com, +38067***67
def mask(recipient: str) -> str:
    if "@" in recipient:
        name, domain = recipient.split("@", 1)
        return f"{name[:1]}***@{domain}"
    return recipient[:6] + "***" + recipient[-2:] if len(recipient) > 8 else "***"
