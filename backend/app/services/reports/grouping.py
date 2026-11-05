from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Hashable
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.models import Doctor

MONTHS = [
    "січень", "лютий", "березень", "квітень", "травень", "червень",
    "липень", "серпень", "вересень", "жовтень", "листопад", "грудень",
]  # fmt: skip


# One measured fact, already reduced to what grouping needs: the local day it
# happened on, the doctor it belongs to (if any) and the numbers it adds.
@dataclass(frozen=True)
class Fact:
    day: date
    doctor_id: int | None
    values: dict[str, float]


@dataclass(frozen=True)
class ReportContext:
    start: date
    end: date  # inclusive
    doctors: list[Doctor] = field(default_factory=list)
    doctor_id: int | None = None  # optional filter: one doctor's numbers only

    def days(self) -> list[date]:
        return [self.start + timedelta(days=i) for i in range((self.end - self.start).days + 1)]


# GoF Strategy: how facts are put into buckets. The report (Context) delegates
# to whichever grouping the user picked, so "per day", "per month" and "per
# doctor" are interchangeable for every report without subclassing reports.
class Grouping(ABC):
    name: str
    title: str

    @abstractmethod
    def key(self, fact: Fact) -> Hashable: ...

    @abstractmethod
    def label(self, key: Hashable, ctx: ReportContext) -> str: ...

    # Every bucket of the period, including empty ones: a day without visits is
    # a zero on the chart, not a missing point
    @abstractmethod
    def buckets(self, ctx: ReportContext) -> list[Hashable]: ...

    def key_id(self, key: Hashable) -> str:
        return str(key)


class GroupByDay(Grouping):
    name, title = "day", "За днями"

    def key(self, fact: Fact) -> Hashable:
        return fact.day

    def label(self, key: Hashable, ctx: ReportContext) -> str:
        assert isinstance(key, date)
        return f"{key:%d.%m}"

    def buckets(self, ctx: ReportContext) -> list[Hashable]:
        return list(ctx.days())

    def key_id(self, key: Hashable) -> str:
        assert isinstance(key, date)
        return key.isoformat()


class GroupByMonth(Grouping):
    name, title = "month", "За місяцями"

    def key(self, fact: Fact) -> Hashable:
        return (fact.day.year, fact.day.month)

    def label(self, key: Hashable, ctx: ReportContext) -> str:
        year, month = key  # type: ignore[misc]
        return f"{MONTHS[month - 1]} {year}"

    def buckets(self, ctx: ReportContext) -> list[Hashable]:
        return sorted({(d.year, d.month) for d in ctx.days()})

    def key_id(self, key: Hashable) -> str:
        year, month = key  # type: ignore[misc]
        return f"{year}-{month:02d}"


class GroupByDoctor(Grouping):
    name, title = "doctor", "За лікарями"

    def key(self, fact: Fact) -> Hashable:
        return fact.doctor_id

    def label(self, key: Hashable, ctx: ReportContext) -> str:
        doctor = next((d for d in ctx.doctors if d.id == key), None)
        if doctor is None:
            return f"Лікар #{key}"
        return f"{doctor.full_name} ({doctor.specialization.name.lower()})"

    def buckets(self, ctx: ReportContext) -> list[Hashable]:
        return [d.id for d in ctx.doctors]


GROUPINGS: dict[str, Grouping] = {
    g.name: g for g in (GroupByDay(), GroupByMonth(), GroupByDoctor())
}
