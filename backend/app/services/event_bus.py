from collections import defaultdict
from typing import Protocol

from app.domain.events import DomainEvent


class EventHandler(Protocol):
    def handle(self, event: DomainEvent) -> None: ...


# GoF Observer: EventBus is the Subject (a change manager in GoF terms) and
# every EventHandler is an Observer subscribed to the event types it cares
# about. Publishers never know who listens, so adding a reaction to a booking
# means adding a subscriber, not editing BookingFacade.
#
# Handlers run synchronously inside the caller's transaction and only add rows
# to the same session – no commits and no network I/O here. Anything slow
# (e-mail, SMS) is written to the notifications outbox and sent by the worker.
class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: EventHandler) -> None:
        self._handlers[event_type].remove(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers[type(event)]:
            handler.handle(event)
