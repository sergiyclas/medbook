from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from app.core.clock import local_to_utc


# Weekdays on which (weekday, start, end) intervals overlap each other
def overlapping_weekdays(rows: Iterable[tuple[int, time, time]]) -> set[int]:
    by_day: dict[int, list[tuple[time, time]]] = defaultdict(list)
    for weekday, start, end in rows:
        by_day[weekday].append((start, end))
    clashes = set()
    for weekday, intervals in by_day.items():
        intervals.sort()
        if any(
            prev_end > start
            for (_, prev_end), (start, _) in zip(intervals, intervals[1:], strict=False)
        ):
            clashes.add(weekday)
    return clashes


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
