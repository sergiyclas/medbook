from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum
from sqlalchemy.types import TypeDecorator


# Timezone-aware datetime that always comes back in UTC. PostgreSQL keeps the
# offset (timestamptz); SQLite drops it, so naive values read from SQLite are UTC.
class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to UTCDateTime")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def str_enum(enum_cls: type[StrEnum]) -> Enum:
    # VARCHAR + values instead of a native PG enum: behaves the same on SQLite
    # and adding a status later does not need ALTER TYPE.
    return Enum(
        enum_cls,
        native_enum=False,
        values_callable=lambda members: [m.value for m in members],
        length=20,
    )
