from datetime import UTC, date, datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.clock import local_to_utc
from app.domain.enums import AppointmentStatus as S
from app.domain.errors import InvalidData
from app.repositories.reports import ReportRepository
from app.services.reports.concrete import (
    AppointmentsCountReport,
    DoctorLoadReport,
    NewPatientsReport,
)
from app.services.reports.grouping import GROUPINGS, Fact, GroupByMonth, ReportContext
from tests.factories import make_appointment, make_doctor, make_patient

MON, TUE, WED = date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 18)


def at(day: date, hour: int) -> datetime:
    return local_to_utc(day, time(hour))


@pytest.fixture
def clinic(session: Session):
    alpha = make_doctor(session, slot_minutes=30, last_name="Альфа")  # 7 h a day, Mon–Fri
    beta = make_doctor(session, slot_minutes=30, last_name="Бета")
    p1, p2 = make_patient(session), make_patient(session)
    make_appointment(session, p1, alpha, at(MON, 9), S.COMPLETED)
    make_appointment(session, p2, alpha, at(MON, 10), S.NO_SHOW)
    make_appointment(session, p1, alpha, at(WED, 9), S.CANCELLED)
    make_appointment(session, p2, beta, at(WED, 14), S.SCHEDULED)
    session.flush()
    repo = ReportRepository(session)
    return repo, alpha, beta


def ctx(repo: ReportRepository, start=MON, end=WED, doctor_id=None) -> ReportContext:
    return ReportContext(start, end, repo.doctors(doctor_id), doctor_id)


def rows(result) -> dict[str, dict[str, float]]:
    return {r.key: r.values for r in result.rows}


def test_counts_per_day_include_empty_days(clinic) -> None:
    repo, *_ = clinic
    result = AppointmentsCountReport(repo).generate(ctx(repo), GROUPINGS["day"])
    by_day = rows(result)
    assert list(by_day) == ["2026-11-16", "2026-11-17", "2026-11-18"]
    assert by_day["2026-11-16"] == {
        "total": 2, "completed": 1, "upcoming": 0, "cancelled": 0, "no_show": 1,
    }  # fmt: skip
    assert by_day["2026-11-17"]["total"] == 0  # a quiet day is a zero, not a gap
    assert by_day["2026-11-18"] == {
        "total": 2, "completed": 0, "upcoming": 1, "cancelled": 1, "no_show": 0,
    }  # fmt: skip
    assert result.totals["total"] == 4


def test_same_report_grouped_by_doctor_and_filtered(clinic) -> None:
    repo, alpha, beta = clinic
    report = AppointmentsCountReport(repo)
    by_doctor = rows(report.generate(ctx(repo), GROUPINGS["doctor"]))
    assert by_doctor[str(alpha.id)]["total"] == 3
    assert by_doctor[str(beta.id)]["total"] == 1

    only_beta = report.generate(ctx(repo, doctor_id=beta.id), GROUPINGS["day"])
    assert only_beta.totals["total"] == 1


def test_doctor_load_derives_percent_from_summed_hours(clinic) -> None:
    repo, alpha, beta = clinic
    by_doctor = rows(DoctorLoadReport(repo).generate(ctx(repo), GROUPINGS["doctor"]))
    a = by_doctor[str(alpha.id)]
    # 3 working days x 7 h; a completed and a no-show visit occupied 1 h, the
    # cancelled one did not count
    assert a["capacity_hours"] == 21
    assert a["booked_hours"] == 1
    assert a["visits"] == 2 and a["no_show"] == 1
    assert a["load_pct"] == pytest.approx(4.8, abs=0.05)
    assert by_doctor[str(beta.id)]["booked_hours"] == 0.5


def test_doctor_load_total_is_not_an_average_of_percentages(clinic) -> None:
    repo, *_ = clinic
    result = DoctorLoadReport(repo).generate(ctx(repo), GROUPINGS["day"])
    assert result.totals["capacity_hours"] == 42
    assert result.totals["load_pct"] == pytest.approx(100 * 1.5 / 42, abs=0.05)


def test_new_patients_running_total(session: Session) -> None:
    for created in (datetime(2026, 9, 20, tzinfo=UTC), datetime(2026, 10, 5, tzinfo=UTC)):
        make_patient(session, created_at=created)
    for day in (datetime(2026, 11, 2, 9, tzinfo=UTC), datetime(2026, 11, 3, 9, tzinfo=UTC)):
        make_patient(session, created_at=day)
    repo = ReportRepository(session)
    result = NewPatientsReport(repo).generate(
        ReportContext(date(2026, 10, 1), date(2026, 11, 30)), GroupByMonth()
    )
    assert [(r.label, r.values["new"], r.values["cumulative"]) for r in result.rows] == [
        ("жовтень 2026", 1, 2),  # one patient registered before the period
        ("листопад 2026", 2, 4),
    ]
    assert result.totals == {"new": 3, "cumulative": 4}


def test_new_patients_cannot_be_grouped_by_doctor(session: Session) -> None:
    repo = ReportRepository(session)
    with pytest.raises(InvalidData) as err:
        NewPatientsReport(repo).generate(ReportContext(MON, WED), GROUPINGS["doctor"])
    assert err.value.code == "grouping_not_supported"


def test_month_buckets_span_the_period() -> None:
    period = ReportContext(date(2026, 10, 30), date(2026, 12, 2))
    assert GroupByMonth().buckets(period) == [(2026, 10), (2026, 11), (2026, 12)]
    assert GroupByMonth().key(Fact(date(2026, 11, 5), None, {})) == (2026, 11)


def test_reports_api(client: TestClient, clinic, admin_headers) -> None:
    listing = client.get("/api/v1/admin/reports", headers=admin_headers).json()
    assert {r["name"] for r in listing} == {"appointments", "doctor-load", "new-patients"}

    response = client.get(
        f"/api/v1/admin/reports/appointments?grouping=day&date_from={MON}&date_to={WED}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["totals"]["total"] == 4
    assert [c["key"] for c in response.json()["columns"]][0] == "total"

    bad = client.get("/api/v1/admin/reports/new-patients?grouping=doctor", headers=admin_headers)
    assert bad.status_code == 422
    assert client.get("/api/v1/admin/reports/nope", headers=admin_headers).status_code == 404
    reversed_period = client.get(
        f"/api/v1/admin/reports/appointments?date_from={WED}&date_to={MON}", headers=admin_headers
    )
    assert reversed_period.status_code == 422


def test_doctor_grouping_lists_every_doctor_even_without_visits(clinic, session) -> None:
    repo, *_ = clinic
    idle = make_doctor(session, last_name="Гамма")
    session.flush()
    by_doctor = rows(AppointmentsCountReport(repo).generate(ctx(repo), GROUPINGS["doctor"]))
    assert by_doctor[str(idle.id)]["total"] == 0
    assert len(by_doctor) == 3
