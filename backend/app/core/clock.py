from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from app.core.config import get_settings

# Timestamps are stored and compared in UTC. Working hours are local wall-clock
# times, so they are combined with a concrete date in the clinic timezone first –
# that way a DST switch shifts the UTC offset, not the visit hour.


def utc_now() -> datetime:
    return datetime.now(UTC)


def clinic_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().clinic_timezone)


def to_local(moment: datetime) -> datetime:
    return moment.astimezone(clinic_tz())


def local_to_utc(day: date, at: time) -> datetime:
    return datetime.combine(day, at, tzinfo=clinic_tz()).astimezone(UTC)


def local_today() -> date:
    return to_local(utc_now()).date()
