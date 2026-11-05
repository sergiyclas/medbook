import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../api/client'
import type { Appointment, Doctor, NextSlot, Slot } from '../../api/types'
import { useAuth } from '../../auth/context'
import { DayStrip, SlotGrid } from '../../components/SlotPicker'
import { Talon } from '../../components/Talon'
import { ErrorBox, Loading } from '../../components/ui'
import { weeklySummary } from '../../lib/format'
import { localDay } from '../../lib/time'
import { useAction, useResource } from '../../lib/useResource'

const BOOKING_DAYS = 14

export function DoctorPage() {
  const { id } = useParams()
  const doctorId = Number(id)
  const { user } = useAuth()
  const doctor = useResource(() => api<Doctor>(`/doctors/${doctorId}`), [doctorId])
  const [day, setDay] = useState<string | null>(null)
  const [slot, setSlot] = useState<Slot | null>(null)
  const [reason, setReason] = useState('')
  const [booked, setBooked] = useState<Appointment | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const action = useAction()

  // Open on the day of the doctor's nearest free slot rather than on an empty today
  useEffect(() => {
    api<NextSlot[]>('/doctors/next-free')
      .then((all) => {
        const next = all.find((s) => s.doctor_id === doctorId)
        setDay(next ? localDay(next.starts_at) : localDay(new Date()))
      })
      .catch(() => setDay(localDay(new Date())))
  }, [doctorId])

  if (doctor.loading && !doctor.data)
    return (
      <div className="wrap">
        <Loading />
      </div>
    )
  if (doctor.error || !doctor.data) {
    return (
      <div className="wrap">
        <ErrorBox error={doctor.error ?? 'Лікаря не знайдено'} />
      </div>
    )
  }
  const d = doctor.data

  const book = async () => {
    if (!slot) return
    const result = await action.run(() =>
      api<Appointment>('/appointments', {
        method: 'POST',
        body: { doctor_id: d.id, starts_at: slot.starts_at, reason: reason.trim() || null },
      }),
    )
    if (result) setBooked(result)
    else setRefreshKey((k) => k + 1) // the slot may have just been taken
  }

  return (
    <div className="wrap">
      <p style={{ marginBottom: 16 }}>
        <Link to={`/doctors?spec=${d.specialization.id}`}>← {d.specialization.name}</Link>
      </p>
      <div className="doctor-layout">
        <aside className="card doctor-card">
          <span className="eyebrow">{d.specialization.name}</span>
          <h1 style={{ fontSize: 28 }}>{d.full_name}</h1>
          {d.room && (
            <span className="door-plate">
              <span className="mono">{d.room}</span>
              <span>кабінет</span>
            </span>
          )}
          {d.bio && <p className="muted">{d.bio}</p>}
          <div>
            <p className="eyebrow" style={{ marginBottom: 8 }}>
              Графік прийому · {d.slot_minutes} хв на пацієнта
            </p>
            <table className="table">
              <tbody>
                {weeklySummary(d.working_hours).map(([label, text]) => (
                  <tr key={label}>
                    <td className="mono">{label}</td>
                    <td className="mono">{text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </aside>

        <section className="stack">
          {booked ? (
            <>
              <h2>Ви записані</h2>
              <Talon
                startsAt={booked.starts_at}
                doctorName={booked.doctor.full_name}
                specialization={booked.doctor.specialization.name}
                room={booked.doctor.room}
                number={booked.id}
                stampText="Записано"
                status="scheduled"
                freshStamp
              />
              <p className="muted">
                Підтвердження вже в черзі на відправку, а перед прийомом надійде нагадування.
              </p>
              <div className="row">
                <Link className="btn" to="/my">
                  Мої записи
                </Link>
                <button
                  className="btn btn--ghost"
                  onClick={() => {
                    setBooked(null)
                    setSlot(null)
                    setReason('')
                    setRefreshKey((k) => k + 1)
                  }}
                >
                  Записатися ще раз
                </button>
              </div>
            </>
          ) : (
            <>
              <div>
                <h2 style={{ marginBottom: 12 }}>Оберіть день і час</h2>
                {day && (
                  <DayStrip
                    days={BOOKING_DAYS}
                    value={day}
                    workingHours={d.working_hours}
                    onChange={(next) => {
                      setDay(next)
                      setSlot(null)
                    }}
                  />
                )}
              </div>
              {day && (
                <SlotGrid
                  doctorId={d.id}
                  day={day}
                  value={slot?.starts_at ?? null}
                  onChange={setSlot}
                  refreshKey={refreshKey}
                />
              )}
              {slot && (
                <div className="stack">
                  <Talon
                    startsAt={slot.starts_at}
                    doctorName={d.full_name}
                    specialization={d.specialization.name}
                    room={d.room}
                    muted
                  />
                  <label className="field">
                    <span>Що турбує (необов’язково)</span>
                    <textarea
                      value={reason}
                      maxLength={500}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Наприклад: підвищений тиск зранку"
                    />
                    <small>Лікар побачить це перед прийомом.</small>
                  </label>
                  <ErrorBox error={action.error} />
                  {!user && (
                    <Link className="btn" to={`/login?next=/doctors/${d.id}`}>
                      Увійдіть, щоб записатися
                    </Link>
                  )}
                  {user?.role === 'patient' && (
                    <button className="btn" onClick={book} disabled={action.busy}>
                      {action.busy ? 'Записуємо…' : 'Записатися на цей час'}
                    </button>
                  )}
                  {user && user.role !== 'patient' && (
                    <p className="alert alert--info">
                      Онлайн записуються пацієнти. Адміністратор записує пацієнта в розділі
                      «Прийоми».
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  )
}
