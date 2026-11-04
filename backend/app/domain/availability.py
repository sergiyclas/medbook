from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from app.core.clock import local_to_utc


# Splits local working intervals of one day into equal slots and returns
# their starts in UTC. A tail shorter than a slot is dropped.
def slot_starts(
    intervals: Iterable[tuple[time, time]], day: date, slot_minutes: int
) -> list[datetime]:
    step = timedelta(minutes=slot_minutes)
    starts: list[datetime] = []
    for start, end in sorted(intervals):
        moment, finish = local_to_utc(day, start), local_to_utc(day, end)
        while moment + step <= finish:
            starts.append(moment)
            moment += step
    return starts
