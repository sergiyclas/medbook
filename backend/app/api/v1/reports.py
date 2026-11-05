from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import SessionDep, require_role
from app.core.clock import local_today
from app.domain.enums import Role
from app.repositories.reports import ReportRepository
from app.schemas.reports import GroupingOut, ReportInfo, ReportOut
from app.services.reports.concrete import REPORTS
from app.services.reports.grouping import GROUPINGS, ReportContext

router = APIRouter(
    prefix="/admin/reports", tags=["reports"], dependencies=[Depends(require_role(Role.ADMIN))]
)

MAX_PERIOD_DAYS = 731


@router.get("", response_model=list[ReportInfo])
def available_reports():
    return [
        ReportInfo(
            name=r.name,
            title=r.title,
            groupings=[
                GroupingOut(name=g, title=GROUPINGS[g].title) for g in r.supported_groupings
            ],
        )
        for r in REPORTS.values()
    ]


@router.get("/{report_name}", response_model=ReportOut)
def run_report(
    report_name: str,
    session: SessionDep,
    grouping: str = "day",
    date_from: date | None = None,
    date_to: date | None = None,
    doctor_id: Annotated[int | None, Query(description="Only this doctor's data")] = None,
):
    report_cls, strategy = REPORTS.get(report_name), GROUPINGS.get(grouping)
    if report_cls is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Такого звіту немає")
    if strategy is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Невідоме групування")
    end = date_to or local_today()
    start = date_from or end - timedelta(days=29)
    if start > end or (end - start).days > MAX_PERIOD_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Період має бути від 1 дня до 2 років"
        )
    repo = ReportRepository(session)
    ctx = ReportContext(start, end, repo.doctors(doctor_id), doctor_id)
    return report_cls(repo).generate(ctx, strategy)
