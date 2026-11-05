import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api/client'
import type { DayOff, DoctorAdmin, Specialization, WorkingHours } from '../../api/types'
import { Empty, ErrorBox, Loading } from '../../components/ui'
import { useToast } from '../../components/toast'
import { weeklySummary } from '../../lib/format'
import { WEEKDAYS, dayLabel, today } from '../../lib/time'
import { useAction, useResource } from '../../lib/useResource'

export function DoctorsAdmin() {
  const list = useResource(() => api<DoctorAdmin[]>('/admin/doctors'), [])
  return (
    <>
      <div className="page__head">
        <div>
          <h1>Лікарі</h1>
          <p>Профілі, графіки роботи та вихідні.</p>
        </div>
        <Link className="btn" to="/admin/doctors/new">
          Додати лікаря
        </Link>
      </div>
      <ErrorBox error={list.error} />
      {list.loading && !list.data && <Loading />}
      {list.data && !list.data.length && <Empty>Лікарів ще немає.</Empty>}
      {!!list.data?.length && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Лікар</th>
                <th>Кабінет</th>
                <th>Графік</th>
                <th>Слот</th>
                <th>Стан</th>
              </tr>
            </thead>
            <tbody>
              {list.data.map((d) => (
                <tr key={d.id}>
                  <td>
                    <Link to={`/admin/doctors/${d.id}`}>{d.full_name}</Link>
                    <span className="cell-sub">
                      {d.specialization.name} · {d.email}
                    </span>
                  </td>
                  <td className="mono">{d.room ?? '–'}</td>
                  <td className="mono" style={{ fontSize: 13 }}>
                    {weeklySummary(d.working_hours).map(([day, text]) => (
                      <div key={day}>
                        {day} {text}
                      </div>
                    ))}
                  </td>
                  <td className="num">{d.slot_minutes} хв</td>
                  <td>
                    <span className={`badge ${d.is_active ? 'badge--scheduled' : ''}`}>
                      {d.is_active ? 'Приймає' : 'Не приймає'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

type HoursRow = Pick<WorkingHours, 'weekday' | 'start_time' | 'end_time'>

const EMPTY_FORM = {
  email: '',
  password: '',
  last_name: '',
  first_name: '',
  middle_name: '',
  specialization_id: '',
  room: '',
  bio: '',
  slot_minutes: '20',
  is_active: true,
}

const DEFAULT_HOURS: HoursRow[] = [0, 1, 2, 3, 4].flatMap((weekday) => [
  { weekday, start_time: '09:00', end_time: '13:00' },
  { weekday, start_time: '14:00', end_time: '18:00' },
])

function formOf(d: DoctorAdmin) {
  return {
    ...EMPTY_FORM,
    last_name: d.last_name,
    first_name: d.first_name,
    middle_name: d.middle_name ?? '',
    specialization_id: String(d.specialization.id),
    room: d.room ?? '',
    bio: d.bio ?? '',
    slot_minutes: String(d.slot_minutes),
    is_active: d.is_active,
  }
}

const hoursOf = (d: DoctorAdmin): HoursRow[] =>
  d.working_hours.map((h) => ({
    weekday: h.weekday,
    start_time: h.start_time.slice(0, 5),
    end_time: h.end_time.slice(0, 5),
  }))

export function DoctorEdit() {
  const { id } = useParams()
  const doctor = useResource(
    () => (id === undefined ? Promise.resolve(null) : api<DoctorAdmin>(`/admin/doctors/${id}`)),
    [id],
  )
  if (id !== undefined && doctor.loading && !doctor.data) return <Loading />
  if (doctor.error) return <ErrorBox error={doctor.error} />
  // keyed by id: a freshly created doctor opens with its own saved values
  return <DoctorEditor key={id ?? 'new'} doctor={id === undefined ? null : (doctor.data ?? null)} />
}

function DoctorEditor({ doctor }: { doctor: DoctorAdmin | null }) {
  const isNew = doctor === null
  const id = doctor?.id
  const navigate = useNavigate()
  const toast = useToast()
  const specs = useResource(() => api<Specialization[]>('/specializations'), [])
  const [form, setForm] = useState(() => (doctor ? formOf(doctor) : EMPTY_FORM))
  const [hours, setHours] = useState<HoursRow[]>(() => (doctor ? hoursOf(doctor) : DEFAULT_HOURS))
  const profile = useAction()
  const schedule = useAction()

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value })

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault()
    const common = {
      last_name: form.last_name,
      first_name: form.first_name,
      middle_name: form.middle_name || null,
      specialization_id: Number(form.specialization_id),
      room: form.room || null,
      bio: form.bio || null,
      slot_minutes: Number(form.slot_minutes),
    }
    if (isNew) {
      const created = await profile.run(() =>
        api<DoctorAdmin>('/admin/doctors', {
          method: 'POST',
          body: { ...common, email: form.email, password: form.password, working_hours: hours },
        }),
      )
      if (created) {
        toast('Лікаря додано')
        navigate(`/admin/doctors/${created.id}`, { replace: true })
      }
      return
    }
    const saved = await profile.run(() =>
      api<DoctorAdmin>(`/admin/doctors/${id}`, {
        method: 'PATCH',
        body: { ...common, is_active: form.is_active },
      }),
    )
    if (saved) toast('Профіль збережено')
  }

  const saveHours = async () => {
    const saved = await schedule.run(() =>
      api<DoctorAdmin>(`/admin/doctors/${id}/working-hours`, {
        method: 'PUT',
        body: { working_hours: hours },
      }),
    )
    if (saved) toast('Графік збережено')
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <div className="page__head" style={{ marginBottom: 0 }}>
        <div>
          <p>
            <Link to="/admin/doctors">← Лікарі</Link>
          </p>
          <h1>{isNew ? 'Новий лікар' : doctor.full_name}</h1>
        </div>
      </div>

      <form className="card stack" onSubmit={saveProfile}>
        <h2>Профіль</h2>
        <div className="form-grid">
          <label className="field">
            <span>Прізвище</span>
            <input required value={form.last_name} onChange={set('last_name')} />
          </label>
          <label className="field">
            <span>Ім’я</span>
            <input required value={form.first_name} onChange={set('first_name')} />
          </label>
          <label className="field">
            <span>По батькові</span>
            <input value={form.middle_name} onChange={set('middle_name')} />
          </label>
          <label className="field">
            <span>Спеціалізація</span>
            <select required value={form.specialization_id} onChange={set('specialization_id')}>
              <option value="">Оберіть</option>
              {specs.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Кабінет</span>
            <input value={form.room} maxLength={20} onChange={set('room')} />
          </label>
          <label className="field">
            <span>Тривалість прийому, хв</span>
            <input
              type="number"
              min={10}
              max={120}
              step={5}
              required
              value={form.slot_minutes}
              onChange={set('slot_minutes')}
            />
          </label>
          {isNew && (
            <>
              <label className="field">
                <span>E-mail для входу</span>
                <input type="email" required value={form.email} onChange={set('email')} />
              </label>
              <label className="field">
                <span>Початковий пароль</span>
                <input required minLength={6} value={form.password} onChange={set('password')} />
                <small>Передайте лікарю особисто</small>
              </label>
            </>
          )}
        </div>
        <label className="field">
          <span>Про лікаря</span>
          <textarea value={form.bio} onChange={set('bio')} />
        </label>
        {!isNew && (
          <label className="check">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Приймає пацієнтів (вимкнення ховає лікаря з сайту й блокує вхід)
          </label>
        )}
        {isNew && <HoursEditor hours={hours} onChange={setHours} />}
        <ErrorBox error={profile.error} />
        <div>
          <button className="btn" disabled={profile.busy}>
            {isNew ? 'Додати лікаря' : 'Зберегти профіль'}
          </button>
        </div>
      </form>

      {!isNew && (
        <section className="card stack">
          <h2>Графік роботи</h2>
          <p className="muted">
            Уже записані прийоми поза новим графіком не скасовуються – за потреби перенесіть їх
            вручну.
          </p>
          <HoursEditor hours={hours} onChange={setHours} />
          <ErrorBox error={schedule.error} />
          <div>
            <button className="btn" onClick={saveHours} disabled={schedule.busy}>
              Зберегти графік
            </button>
          </div>
        </section>
      )}

      {id !== undefined && <DaysOff doctorId={id} />}
    </div>
  )
}

function HoursEditor({
  hours,
  onChange,
}: {
  hours: HoursRow[]
  onChange: (h: HoursRow[]) => void
}) {
  const update = (index: number, patch: Partial<HoursRow>) =>
    onChange(hours.map((h, i) => (i === index ? { ...h, ...patch } : h)))
  return (
    <div className="hours-editor">
      {WEEKDAYS.map((label, weekday) => {
        const rows = hours
          .map((h, index) => ({ h, index }))
          .filter(({ h }) => h.weekday === weekday)
        return (
          <div className="hours-row" key={weekday}>
            <span style={{ fontWeight: 500, paddingTop: 10 }}>{label}</span>
            <div className="stack" style={{ gap: 8 }}>
              {!rows.length && (
                <span className="muted" style={{ paddingTop: 10 }}>
                  вихідний
                </span>
              )}
              {rows.map(({ h, index }) => (
                <div className="interval" key={index}>
                  <input
                    type="time"
                    aria-label={`${label}, початок`}
                    value={h.start_time}
                    onChange={(e) => update(index, { start_time: e.target.value })}
                  />
                  <span>–</span>
                  <input
                    type="time"
                    aria-label={`${label}, кінець`}
                    value={h.end_time}
                    onChange={(e) => update(index, { end_time: e.target.value })}
                  />
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    aria-label="Прибрати інтервал"
                    onClick={() => onChange(hours.filter((_, i) => i !== index))}
                  >
                    ✕
                  </button>
                </div>
              ))}
              <div>
                <button
                  type="button"
                  className="link-btn"
                  onClick={() =>
                    onChange([...hours, { weekday, start_time: '09:00', end_time: '13:00' }])
                  }
                >
                  + інтервал
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function DaysOff({ doctorId }: { doctorId: number }) {
  const list = useResource(() => api<DayOff[]>(`/admin/doctors/${doctorId}/days-off`), [doctorId])
  const [day, setDay] = useState('')
  const [reason, setReason] = useState('')
  const action = useAction()
  const toast = useToast()

  const add = async (e: FormEvent) => {
    e.preventDefault()
    const created = await action.run(() =>
      api<DayOff & { cancelled_appointments: number }>(`/admin/doctors/${doctorId}/days-off`, {
        method: 'POST',
        body: { day, reason: reason || null },
      }),
    )
    if (created) {
      toast(
        created.cancelled_appointments
          ? `Вихідний додано, скасовано прийомів: ${created.cancelled_appointments}`
          : 'Вихідний додано',
      )
      setDay('')
      setReason('')
      list.reload()
    }
  }
  const remove = async (dayOff: DayOff) => {
    await action.run(() => api(`/admin/days-off/${dayOff.id}`, { method: 'DELETE' }))
    list.reload()
  }

  const upcoming = (list.data ?? []).filter((d) => d.day >= today())
  return (
    <section className="card stack">
      <h2>Вихідні та відпустки</h2>
      <p className="muted">
        Записи на вихідний день буде скасовано, пацієнти отримають повідомлення.
      </p>
      <form className="filters" onSubmit={add} style={{ marginBottom: 0 }}>
        <label className="field">
          <span>День</span>
          <input
            type="date"
            required
            min={today()}
            value={day}
            onChange={(e) => setDay(e.target.value)}
          />
        </label>
        <label className="field" style={{ flex: 1 }}>
          <span>Причина</span>
          <input value={reason} maxLength={200} onChange={(e) => setReason(e.target.value)} />
        </label>
        <button className="btn" disabled={action.busy}>
          Додати вихідний
        </button>
      </form>
      <ErrorBox error={action.error} />
      {upcoming.length ? (
        <ul className="history">
          {upcoming.map((d) => (
            <li key={d.id}>
              <span className="mono">{dayLabel(d.day)}</span>
              <span className="row spread">
                {d.reason ?? <span className="muted">без причини</span>}
                <button className="link-btn" onClick={() => remove(d)}>
                  Прибрати
                </button>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">Найближчим часом вихідних немає.</p>
      )}
    </section>
  )
}
