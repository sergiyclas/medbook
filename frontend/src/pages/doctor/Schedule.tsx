import { useState } from 'react'
import { api } from '../../api/client'
import type { Appointment } from '../../api/types'
import { ErrorBox, Loading, Modal, StatusBadge } from '../../components/ui'
import { useToast } from '../../components/toast'
import { plural } from '../../lib/format'
import { isActive } from '../../lib/labels'
import {
  WEEKDAYS,
  addDays,
  age,
  dayLabel,
  fmtTime,
  localDay,
  today,
  weekdayOf,
} from '../../lib/time'
import { useAction, useResource } from '../../lib/useResource'

const mondayOf = (day: string) => addDays(day, -weekdayOf(day))
const countLabel = (n: number) => `${n} ${plural(n, 'прийом', 'прийоми', 'прийомів')}`

export function Schedule() {
  const [week, setWeek] = useState(mondayOf(today()))
  const [completing, setCompleting] = useState<Appointment | null>(null)
  // "Has the visit started?" is judged against the moment the list was loaded
  const [now, setNow] = useState(Date.now)
  const toast = useToast()
  const action = useAction()
  const list = useResource(
    () =>
      api<Appointment[]>('/doctor/schedule', {
        query: { date_from: week, date_to: addDays(week, 6) },
      }),
    [week],
  )

  const act = async (appt: Appointment, path: string, message: string) => {
    const ok = await action.run(() =>
      api<Appointment>(`/appointments/${appt.id}/${path}`, { method: 'POST' }),
    )
    if (ok) {
      toast(message)
      setNow(() => Date.now())
      list.reload()
    }
  }

  const changeWeek = (next: string) => {
    setWeek(next)
    setNow(() => Date.now())
  }
  const days = Array.from({ length: 7 }, (_, i) => addDays(week, i))
  const byDay = (day: string) => (list.data ?? []).filter((a) => localDay(a.starts_at) === day)

  return (
    <div className="wrap" style={{ maxWidth: 920 }}>
      <div className="page__head">
        <div>
          <h1>Розклад прийомів</h1>
          <p>
            Тиждень {dayLabel(week)} – {dayLabel(addDays(week, 6))}
          </p>
        </div>
        <div className="row">
          <button className="btn btn--ghost btn--sm" onClick={() => changeWeek(addDays(week, -7))}>
            ← Попередній
          </button>
          <button className="btn btn--ghost btn--sm" onClick={() => changeWeek(mondayOf(today()))}>
            Цей тиждень
          </button>
          <button className="btn btn--ghost btn--sm" onClick={() => changeWeek(addDays(week, 7))}>
            Наступний →
          </button>
        </div>
      </div>

      <ErrorBox error={list.error ?? action.error} />
      {list.loading && !list.data && <Loading />}

      {list.data &&
        days.map((day) => {
          const visits = byDay(day)
          if (!visits.length && day !== today()) return null
          return (
            <section className="schedule-day" key={day}>
              <h2>
                {day === today() ? 'Сьогодні, ' : ''}
                {WEEKDAYS[weekdayOf(day)]}, {dayLabel(day)}
                <span className="muted mono" style={{ fontSize: 14, marginLeft: 12 }}>
                  {countLabel(visits.filter((v) => v.status !== 'cancelled').length)}
                </span>
              </h2>
              {!visits.length && <p className="muted">Записів на сьогодні немає.</p>}
              {visits.map((appt) => {
                const started = new Date(appt.starts_at).getTime() <= now
                return (
                  <div
                    key={appt.id}
                    className={`visit${isActive(appt.status) ? '' : ' visit--done'}`}
                  >
                    <span className="visit__time">{fmtTime(appt.starts_at)}</span>
                    <div>
                      <b>{appt.patient.full_name}</b>
                      <span className="cell-sub">
                        {age(appt.patient.birth_date)} р. ·{' '}
                        <span className="mono">{appt.patient.phone}</span>
                      </span>
                      {appt.reason && <p style={{ marginTop: 6 }}>Скарга: {appt.reason}</p>}
                      {appt.doctor_notes && (
                        <p className="muted" style={{ marginTop: 6 }}>
                          Висновок: {appt.doctor_notes}
                        </p>
                      )}
                    </div>
                    <div className="row" style={{ justifyContent: 'flex-end' }}>
                      <StatusBadge status={appt.status} />
                      {appt.status === 'scheduled' && (
                        <button
                          className="btn btn--ghost btn--sm"
                          disabled={action.busy}
                          onClick={() => act(appt, 'confirm', 'Прийом підтверджено')}
                        >
                          Підтвердити
                        </button>
                      )}
                      {isActive(appt.status) && started && (
                        <>
                          <button className="btn btn--sm" onClick={() => setCompleting(appt)}>
                            Завершити
                          </button>
                          <button
                            className="btn btn--danger btn--sm"
                            disabled={action.busy}
                            onClick={() => act(appt, 'no-show', 'Позначено неявку')}
                          >
                            Неявка
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </section>
          )
        })}

      {list.data && !list.data.length && (
        <p className="muted" style={{ marginTop: 16 }}>
          На цей тиждень записів немає.
        </p>
      )}

      {completing && (
        <CompleteDialog
          appointment={completing}
          onClose={() => setCompleting(null)}
          onDone={() => {
            setCompleting(null)
            toast('Прийом завершено')
            list.reload()
          }}
        />
      )}
    </div>
  )
}

function CompleteDialog({
  appointment,
  onClose,
  onDone,
}: {
  appointment: Appointment
  onClose: () => void
  onDone: () => void
}) {
  const [notes, setNotes] = useState('')
  const action = useAction()
  const submit = async () => {
    const ok = await action.run(() =>
      api<Appointment>(`/appointments/${appointment.id}/complete`, {
        method: 'POST',
        body: { notes: notes.trim() || null },
      }),
    )
    if (ok) onDone()
  }
  return (
    <Modal open onClose={onClose} title="Завершити прийом">
      <p>
        {appointment.patient.full_name}, {fmtTime(appointment.starts_at)}
      </p>
      <label className="field">
        <span>Висновок і рекомендації</span>
        <textarea
          value={notes}
          maxLength={2000}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Пацієнт побачить це у своєму кабінеті"
        />
      </label>
      <ErrorBox error={action.error} />
      <div className="row">
        <button className="btn" onClick={submit} disabled={action.busy}>
          Завершити прийом
        </button>
        <button className="btn btn--ghost" onClick={onClose}>
          Назад
        </button>
      </div>
    </Modal>
  )
}
