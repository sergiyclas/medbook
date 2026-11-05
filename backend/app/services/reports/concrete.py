from app.core.clock import to_local
from app.domain.enums import ACTIVE_STATUSES, AppointmentStatus
from app.repositories.reports import ReportRepository
from app.services.availability import AvailabilityCalendar
from app.services.reports.base import BaseReport, Column, ReportRow
from app.services.reports.grouping import Fact, ReportContext

# The three reports from the assignment. Each one only says what it measures;
# the order of steps comes from BaseReport.generate, the bucketing from Grouping.


def _bounds(ctx: ReportContext):
    start, _ = AvailabilityCalendar.day_bounds(ctx.start)
    _, end = AvailabilityCalendar.day_bounds(ctx.end)
    return start, end


class AppointmentsCountReport(BaseReport):
    name = "appointments"
    title = "Кількість прийомів"
    columns = [
        Column("total", "Усього"),
        Column("completed", "Завершено"),
        Column("upcoming", "Заплановано"),
        Column("cancelled", "Скасовано"),
        Column("no_show", "Неявки"),
    ]

    def collect(self, ctx: ReportContext) -> list[Fact]:
        facts = []
        for starts_at, _, doctor_id, status in self.repo.appointments(*_bounds(ctx), ctx.doctor_id):
            values = {"total": 1.0}
            if status in ACTIVE_STATUSES:
                values["upcoming"] = 1.0
            else:
                values[status.value] = 1.0
            facts.append(Fact(to_local(starts_at).date(), doctor_id, values))
        return facts


class DoctorLoadReport(BaseReport):
    name = "doctor-load"
    title = "Завантаженість лікарів"
    columns = [
        Column("capacity_hours", "Робочий час", "год"),
        Column("booked_hours", "Зайнято", "год"),
        Column("load_pct", "Завантаженість", "%"),
        Column("visits", "Прийомів"),
        Column("no_show", "Неявки"),
    ]

    # Two kinds of facts go through the same grouping: booked visits (a no-show
    # still occupied the slot) and the working time each doctor had each day
    def collect(self, ctx: ReportContext) -> list[Fact]:
        facts = []
        for starts_at, ends_at, doctor_id, status in self.repo.appointments(
            *_bounds(ctx), ctx.doctor_id
        ):
            if status == AppointmentStatus.CANCELLED:
                continue
            hours = (ends_at - starts_at).total_seconds() / 3600
            values = {"booked_hours": hours, "visits": 1.0}
            if status == AppointmentStatus.NO_SHOW:
                values["no_show"] = 1.0
            facts.append(Fact(to_local(starts_at).date(), doctor_id, values))
        for doctor in ctx.doctors:
            for day in ctx.days():
                slots = len(AvailabilityCalendar.grid(doctor, day))
                if slots:
                    hours = slots * doctor.slot_minutes / 60
                    facts.append(Fact(day, doctor.id, {"capacity_hours": hours}))
        return facts

    # A percentage cannot be summed – it is derived from the summed hours
    def postprocess(self, rows: list[ReportRow], totals: dict[str, float]) -> None:
        for values in [*(r.values for r in rows), totals]:
            capacity = values.get("capacity_hours", 0.0)
            values["load_pct"] = (
                100 * values.get("booked_hours", 0.0) / capacity if capacity else 0.0
            )


class NewPatientsReport(BaseReport):
    name = "new-patients"
    title = "Нові пацієнти"
    columns = [
        Column("new", "Нових пацієнтів"),
        Column("cumulative", "Усього в базі"),
    ]
    # Registration is not tied to a doctor
    supported_groupings = ("day", "month")

    def __init__(self, repo: ReportRepository) -> None:
        super().__init__(repo)
        self._registered_before = 0

    def collect(self, ctx: ReportContext) -> list[Fact]:
        start, end = _bounds(ctx)
        self._registered_before = self.repo.patients_registered_before(start)
        return [
            Fact(to_local(created).date(), None, {"new": 1.0})
            for created in self.repo.patient_registrations(start, end)
        ]

    # Running total turns "new per period" into the growth curve of the patient base
    def postprocess(self, rows: list[ReportRow], totals: dict[str, float]) -> None:
        running = float(self._registered_before)
        for row in rows:
            running += row.values.get("new", 0.0)
            row.values["cumulative"] = running
        totals["cumulative"] = running


REPORTS: dict[str, type[BaseReport]] = {
    r.name: r for r in (AppointmentsCountReport, DoctorLoadReport, NewPatientsReport)
}
