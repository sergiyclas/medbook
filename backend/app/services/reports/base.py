from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Hashable
from dataclasses import dataclass
from typing import ClassVar, final

from app.domain.errors import InvalidData
from app.repositories.reports import ReportRepository
from app.services.reports.grouping import Fact, Grouping, ReportContext


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    unit: str = ""


@dataclass
class ReportRow:
    key: str
    label: str
    values: dict[str, float]


@dataclass
class ReportResult:
    report: str
    title: str
    grouping: str
    columns: list[Column]
    rows: list[ReportRow]
    totals: dict[str, float]


# GoF Template Method. generate() fixes the algorithm every report follows:
#   collect facts -> group them (via the Strategy) -> post-process -> present.
# Subclasses fill in only what differs – which facts to collect and which
# columns to show – and may override the post-processing hook.
class BaseReport(ABC):
    name: ClassVar[str]
    title: ClassVar[str]
    columns: ClassVar[list[Column]]
    supported_groupings: ClassVar[tuple[str, ...]] = ("day", "month", "doctor")

    def __init__(self, repo: ReportRepository) -> None:
        self.repo = repo

    @final
    def generate(self, ctx: ReportContext, grouping: Grouping) -> ReportResult:
        if grouping.name not in self.supported_groupings:
            raise InvalidData(
                f"Звіт «{self.title}» не можна згрупувати так: {grouping.title.lower()}",
                "grouping_not_supported",
            )
        facts = self.collect(ctx)
        rows, totals = self.aggregate(facts, ctx, grouping)
        self.postprocess(rows, totals)
        return self.present(rows, totals, grouping)

    # ---------- primitive operation: each report decides what it measures ----------
    @abstractmethod
    def collect(self, ctx: ReportContext) -> list[Fact]: ...

    # ---------- invariant steps ----------
    def aggregate(
        self, facts: list[Fact], ctx: ReportContext, grouping: Grouping
    ) -> tuple[list[ReportRow], dict[str, float]]:
        keys = [c.key for c in self.columns]
        sums: dict[Hashable, dict[str, float]] = defaultdict(lambda: dict.fromkeys(keys, 0.0))
        for fact in facts:
            bucket = sums[grouping.key(fact)]
            for name, value in fact.values.items():
                bucket[name] = bucket.get(name, 0.0) + value
        rows = [
            ReportRow(grouping.key_id(k), grouping.label(k, ctx), sums[k])
            for k in grouping.buckets(ctx)
        ]
        totals = dict.fromkeys(keys, 0.0)
        for row in rows:
            for name, value in row.values.items():
                totals[name] = totals.get(name, 0.0) + value
        return rows, totals

    def present(
        self, rows: list[ReportRow], totals: dict[str, float], grouping: Grouping
    ) -> ReportResult:
        shown = [c.key for c in self.columns]
        for row in rows:
            row.values = {k: round(row.values.get(k, 0.0), 1) for k in shown}
        return ReportResult(
            report=self.name,
            title=self.title,
            grouping=grouping.name,
            columns=self.columns,
            rows=rows,
            totals={k: round(totals.get(k, 0.0), 1) for k in shown},
        )

    # ---------- hook: derived values that cannot be summed ----------
    def postprocess(self, rows: list[ReportRow], totals: dict[str, float]) -> None:  # noqa: B027
        pass
