import { useState } from 'react'
import { api } from '../../api/client'
import type {
  Appointment,
  AppointmentStatus,
  Doctor,
  DoctorAdmin,
  Patient,
  Slot,
} from '../../api/types'
import { CancelDialog, HistoryDialog, RescheduleDialog } from '../../components/AppointmentDialogs'
import { DayStrip, SlotGrid } from '../../components/SlotPicker'
import { Empty, ErrorBox, Loading, Modal, StatusBadge } from '../../components/ui'
import { useToast } from '../../components/toast'
import { STATUS, isActive } from '../../lib/labels'
import { fmtDate, fmtTime, localDay, today } from '../../lib/time'
import { useAction, useResource } from '../../lib/useResource'

type Dialog = { kind: 'cancel' | 'reschedule' | 'history'; appointment: Appointment } | null

export function Appointments() {
  const [filters, setFilters] = useState({
    doctor_id: '',
    status: '' as AppointmentStatus | '',
    date_from: today(),
    date_to: today(),
  })
  const [dialog, setDialog] = useState<Dialog>(null)
  const [booking, setBooking] = useState(false)
  const toast = useToast()
  const action = useAction()
  const doctors = useResource(() => api<DoctorAdmin[]>('/admin/doctors'), [])
  const list = useResource(
    () => api<Appointment[]>('/admin/appointments', { query: { ...filters, limit: 300 } }),
    [filters],
  )
  const set = (key: keyof typeof filters) => (e: { target: { value: string } }) =>
    setFilters({ ...filters, [key]: e.target.value })

  const confirm = async (appt: Appointment) => {
    const ok = await action.run(() =>
      api<Appointment>(`/appointments/${appt.id}/confirm`, { method: 'POST' }),
    )
    if (ok) {
      toast('Прийом підтверджено')
      list.reload()
    }
  }
  const done = (message: string) => () => {
    setDialog(null)
    setBooking(false)
    toast(message)
    list.reload()
  }

  return (
    <>
      <div className="page__head">
        <div>
          <h1>Прийоми</h1>
          <p>Усі записи клініки: підтвердження, перенесення, скасування.</p>
        </div>
        <button className="btn" onClick={() => setBooking(true)}>
          Записати пацієнта
        </button>
      </div>

      <div className="filters">
        <label className="field">
          <span>Лікар</span>
          <select value={filters.doctor_id} onChange={set('doctor_id')}>
            <option value="">Усі лікарі</option>
            {doctors.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.full_name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Статус</span>
          <select value={filters.status} onChange={set('status')}>
            <option value="">Будь-який</option>
            {Object.entries(STATUS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>З</span>
          <input type="date" value={filters.date_from} onChange={set('date_from')} />
        </label>
        <label className="field">
          <span>По</span>
          <input type="date" value={filters.date_to} onChange={set('date_to')} />
        </label>
      </div>

      <ErrorBox error={list.error ?? action.error} />
      {list.loading && !list.data && <Loading />}
      {list.data && !list.data.length && <Empty>За цими умовами прийомів немає.</Empty>}
      {!!list.data?.length && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Час</th>
                <th>Пацієнт</th>
                <th>Лікар</th>
                <th>Статус</th>
                <th aria-label="Дії" />
              </tr>
            </thead>
            <tbody>
              {list.data.map((a) => (
                <tr key={a.id}>
                  <td className="mono">
                    {fmtTime(a.starts_at)}
                    <span className="cell-sub">{fmtDate(a.starts_at)}</span>
                  </td>
                  <td>
                    {a.patient.full_name}
                    <span className="cell-sub mono">{a.patient.phone}</span>
                  </td>
                  <td>
                    {a.doctor.full_name}
                    <span className="cell-sub">
                      {a.doctor.specialization.name}
                      {a.doctor.room ? ` · каб. ${a.doctor.room}` : ''}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={a.status} />
                  </td>
                  <td>
                    <div className="row" style={{ gap: 6, justifyContent: 'flex-end' }}>
                      {a.status === 'scheduled' && (
                        <button className="btn btn--ghost btn--sm" onClick={() => confirm(a)}>
                          Підтвердити
                        </button>
                      )}
                      {isActive(a.status) && (
                        <>
                          <button
                            className="btn btn--ghost btn--sm"
                            onClick={() => setDialog({ kind: 'reschedule', appointment: a })}
                          >
                            Перенести
                          </button>
                          <button
                            className="btn btn--danger btn--sm"
                            onClick={() => setDialog({ kind: 'cancel', appointment: a })}
                          >
                            Скасувати
                          </button>
                        </>
                      )}
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => setDialog({ kind: 'history', appointment: a })}
                      >
                        Історія
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dialog?.kind === 'cancel' && (
        <CancelDialog
          appointment={dialog.appointment}
          onClose={() => setDialog(null)}
          onDone={done('Прийом скасовано')}
        />
      )}
      {dialog?.kind === 'reschedule' && (
        <RescheduleDialog
          appointment={dialog.appointment}
          onClose={() => setDialog(null)}
          onDone={done('Прийом перенесено')}
        />
      )}
      {dialog?.kind === 'history' && (
        <HistoryDialog appointment={dialog.appointment} onClose={() => setDialog(null)} />
      )}
      {booking && (
        <BookForPatient
          doctors={doctors.data?.filter((d) => d.is_active) ?? []}
          onClose={() => setBooking(false)}
          onDone={done('Пацієнта записано')}
        />
      )}
    </>
  )
}

// Reception books on the patient's behalf: the server applies the reception
// rule chain (no per-day limit, no online horizon)
function BookForPatient({
  doctors,
  onClose,
  onDone,
}: {
  doctors: Doctor[]
  onClose: () => void
  onDone: () => void
}) {
  const [search, setSearch] = useState('')
  const [patient, setPatient] = useState<Patient | null>(null)
  const [doctorId, setDoctorId] = useState<number | null>(null)
  const [day, setDay] = useState(today())
  const [slot, setSlot] = useState<Slot | null>(null)
  const [reason, setReason] = useState('')
  const action = useAction()
  const found = useResource(
    () =>
      search.trim().length >= 2
        ? api<Patient[]>('/admin/patients', { query: { search, limit: 8 } })
        : Promise.resolve([]),
    [search],
  )
  const doctor = doctors.find((d) => d.id === doctorId)

  const submit = async () => {
    if (!patient || !doctor || !slot) return
    const ok = await action.run(() =>
      api<Appointment>('/appointments', {
        method: 'POST',
        body: {
          doctor_id: doctor.id,
          patient_id: patient.id,
          starts_at: slot.starts_at,
          reason: reason.trim() || null,
        },
      }),
    )
    if (ok) onDone()
  }

  return (
    <Modal open onClose={onClose} title="Записати пацієнта" wide>
      {patient ? (
        <div className="row spread card" style={{ padding: '12px 16px' }}>
          <span>
            <b>{patient.full_name}</b>
            <span className="cell-sub mono">
              {patient.phone} · {fmtDate(`${patient.birth_date}T12:00:00Z`)}
            </span>
          </span>
          <button className="link-btn" onClick={() => setPatient(null)}>
            Інший пацієнт
          </button>
        </div>
      ) : (
        <label className="field">
          <span>Пацієнт</span>
          <input
            autoFocus
            value={search}
            placeholder="Прізвище, телефон або e-mail"
            onChange={(e) => setSearch(e.target.value)}
          />
          {found.data?.map((p) => (
            <button
              key={p.id}
              type="button"
              className="btn btn--ghost"
              style={{ justifyContent: 'space-between' }}
              onClick={() => setPatient(p)}
            >
              <span>{p.full_name}</span>
              <span className="mono muted">{p.phone}</span>
            </button>
          ))}
          {search.trim().length >= 2 && found.data?.length === 0 && (
            <small>Не знайдено. Зареєструйте пацієнта в розділі «Пацієнти».</small>
          )}
        </label>
      )}

      <label className="field">
        <span>Лікар</span>
        <select
          value={doctorId ?? ''}
          onChange={(e) => {
            setDoctorId(e.target.value ? Number(e.target.value) : null)
            setSlot(null)
          }}
        >
          <option value="">Оберіть лікаря</option>
          {doctors.map((d) => (
            <option key={d.id} value={d.id}>
              {d.full_name} – {d.specialization.name}
            </option>
          ))}
        </select>
      </label>

      {doctor && (
        <>
          <DayStrip
            days={30}
            value={day}
            workingHours={doctor.working_hours}
            onChange={(next) => {
              setDay(next)
              setSlot(null)
            }}
          />
          <SlotGrid
            doctorId={doctor.id}
            day={day}
            value={slot?.starts_at ?? null}
            onChange={setSlot}
          />
          <label className="field">
            <span>Скарга (необов’язково)</span>
            <input value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
          </label>
        </>
      )}
      <ErrorBox error={action.error} />
      <div className="row">
        <button className="btn" disabled={!patient || !slot || action.busy} onClick={submit}>
          {slot
            ? `Записати на ${localDay(slot.starts_at) === today() ? 'сьогодні' : fmtDate(slot.starts_at)} ${fmtTime(slot.starts_at)}`
            : 'Записати'}
        </button>
        <button className="btn btn--ghost" onClick={onClose}>
          Скасувати
        </button>
      </div>
    </Modal>
  )
}
