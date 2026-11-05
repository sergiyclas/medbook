import { useState } from 'react'
import { api } from '../api/client'
import type { Appointment, Doctor, Slot, StatusChange } from '../api/types'
import { ROLE, STATUS } from '../lib/labels'
import { fmtDateTime, localDay } from '../lib/time'
import { useAction, useResource } from '../lib/useResource'
import { DayStrip, SlotGrid } from './SlotPicker'
import { ErrorBox, Loading, Modal } from './ui'

interface DialogProps {
  appointment: Appointment
  onClose: () => void
  onDone: (updated: Appointment) => void
}

export function CancelDialog({ appointment, onClose, onDone }: DialogProps) {
  const [reason, setReason] = useState('')
  const action = useAction()
  const submit = async () => {
    const updated = await action.run(() =>
      api<Appointment>(`/appointments/${appointment.id}/cancel`, {
        method: 'POST',
        body: { reason: reason.trim() || null },
      }),
    )
    if (updated) onDone(updated)
  }
  return (
    <Modal open onClose={onClose} title="Скасувати прийом">
      <p>
        {appointment.doctor.full_name}, {fmtDateTime(appointment.starts_at)}. Час звільниться для
        інших пацієнтів, нагадування не надходитимуть.
      </p>
      <label className="field">
        <span>Причина (необов’язково)</span>
        <input value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
      </label>
      <ErrorBox error={action.error} />
      <div className="row">
        <button className="btn btn--danger" onClick={submit} disabled={action.busy}>
          Скасувати прийом
        </button>
        <button className="btn btn--ghost" onClick={onClose}>
          Залишити
        </button>
      </div>
    </Modal>
  )
}

export function RescheduleDialog({ appointment, onClose, onDone }: DialogProps) {
  const doctor = useResource(
    () => api<Doctor>(`/doctors/${appointment.doctor.id}`),
    [appointment.doctor.id],
  )
  const [day, setDay] = useState(localDay(appointment.starts_at))
  const [slot, setSlot] = useState<Slot | null>(null)
  const action = useAction()
  const submit = async () => {
    if (!slot) return
    const updated = await action.run(() =>
      api<Appointment>(`/appointments/${appointment.id}/reschedule`, {
        method: 'POST',
        body: { starts_at: slot.starts_at },
      }),
    )
    if (updated) onDone(updated)
  }
  return (
    <Modal open onClose={onClose} title="Перенести прийом" wide>
      <p className="muted">
        Зараз: {fmtDateTime(appointment.starts_at)}. Після перенесення прийом знову потребує
        підтвердження реєстратури.
      </p>
      {doctor.loading && <Loading />}
      {doctor.data && (
        <>
          <DayStrip
            days={14}
            value={day}
            workingHours={doctor.data.working_hours}
            onChange={(next) => {
              setDay(next)
              setSlot(null)
            }}
          />
          <SlotGrid
            doctorId={doctor.data.id}
            day={day}
            value={slot?.starts_at ?? null}
            onChange={setSlot}
          />
        </>
      )}
      <ErrorBox error={action.error} />
      <div className="row">
        <button className="btn" onClick={submit} disabled={!slot || action.busy}>
          {slot ? `Перенести на ${fmtDateTime(slot.starts_at)}` : 'Оберіть новий час'}
        </button>
        <button className="btn btn--ghost" onClick={onClose}>
          Не переносити
        </button>
      </div>
    </Modal>
  )
}

export function HistoryDialog({ appointment, onClose }: Omit<DialogProps, 'onDone'>) {
  const history = useResource(
    () => api<StatusChange[]>(`/appointments/${appointment.id}/history`),
    [appointment.id],
  )
  return (
    <Modal open onClose={onClose} title={`Історія прийому № ${appointment.id}`}>
      {history.loading && <Loading />}
      <ErrorBox error={history.error} />
      <ol className="history">
        {history.data?.map((change, i) => (
          <li key={i}>
            <span className="mono muted">{fmtDateTime(change.changed_at)}</span>
            <span>
              <b>
                {change.from_status ? `${STATUS[change.from_status]} → ` : ''}
                {STATUS[change.to_status]}
              </b>
              {change.reason && <span className="cell-sub">{change.reason}</span>}
              {change.changed_by_role && (
                <span className="cell-sub">
                  ким: {change.changed_by_email ?? ROLE[change.changed_by_role]}
                </span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </Modal>
  )
}
