import { api } from '../api/client'
import type { Slot, WorkingHours } from '../api/types'
import { useResource } from '../lib/useResource'
import { WEEKDAYS_SHORT, addDays, fmtTime, today, weekdayOf } from '../lib/time'

const MONTHS_SHORT = [
  'січ',
  'лют',
  'бер',
  'кві',
  'тра',
  'чер',
  'лип',
  'сер',
  'вер',
  'жов',
  'лис',
  'гру',
]

interface DayStripProps {
  days: number
  value: string
  onChange: (day: string) => void
  workingHours: WorkingHours[]
}

// Days the doctor never works on are disabled straight away, from the weekly
// schedule; days off and fully booked days show up as "no free time" below.
export function DayStrip({ days, value, onChange, workingHours }: DayStripProps) {
  const workdays = new Set(workingHours.map((h) => h.weekday))
  const first = today()
  return (
    <div className="day-strip" role="group" aria-label="Оберіть день">
      {Array.from({ length: days }, (_, i) => {
        const day = addDays(first, i)
        const [, month, date] = day.split('-').map(Number)
        return (
          <button
            key={day}
            type="button"
            className="day"
            aria-pressed={day === value}
            disabled={!workdays.has(weekdayOf(day))}
            onClick={() => onChange(day)}
          >
            <span className="day__wd">{i === 0 ? 'сьог' : WEEKDAYS_SHORT[weekdayOf(day)]}</span>
            <span className="day__num">{date}</span>
            <span className="day__month">{MONTHS_SHORT[month - 1]}</span>
          </button>
        )
      })}
    </div>
  )
}

interface SlotGridProps {
  doctorId: number
  day: string
  value: string | null
  onChange: (slot: Slot) => void
  refreshKey?: number
}

export function SlotGrid({ doctorId, day, value, onChange, refreshKey = 0 }: SlotGridProps) {
  const slots = useResource(
    () => api<Slot[]>(`/doctors/${doctorId}/slots`, { query: { day } }),
    [doctorId, day, refreshKey],
  )
  if (slots.loading && !slots.data) return <p className="loading">Шукаємо вільний час…</p>
  if (slots.error) return <p className="alert">{slots.error.message}</p>
  if (!slots.data?.length) {
    return <p className="empty">Цього дня вільного часу немає. Оберіть інший день.</p>
  }

  const morning = slots.data.filter((s) => Number(fmtTime(s.starts_at).slice(0, 2)) < 13)
  const groups: [string, Slot[]][] = [
    ['До обіду', morning],
    ['Після обіду', slots.data.filter((s) => !morning.includes(s))],
  ]
  return (
    <div>
      {groups
        .filter(([, group]) => group.length)
        .map(([title, group]) => (
          <div className="slot-group" key={title}>
            <p className="eyebrow">{title}</p>
            <div className="slots">
              {group.map((slot) => (
                <button
                  key={slot.starts_at}
                  type="button"
                  className="slot"
                  aria-pressed={slot.starts_at === value}
                  onClick={() => onChange(slot)}
                >
                  {fmtTime(slot.starts_at)}
                </button>
              ))}
            </div>
          </div>
        ))}
    </div>
  )
}
