// All times are shown in the clinic's timezone, whatever the viewer's device says.
export const CLINIC_TZ = 'Europe/Kyiv'

const fmt = (options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat('uk-UA', { timeZone: CLINIC_TZ, ...options })

const timeFmt = fmt({ hour: '2-digit', minute: '2-digit' })
const dateFmt = fmt({ day: '2-digit', month: '2-digit', year: 'numeric' })
const longFmt = fmt({ weekday: 'long', day: 'numeric', month: 'long' })
const dayMonthFmt = fmt({ day: 'numeric', month: 'long' })
const isoDayFmt = new Intl.DateTimeFormat('en-CA', { timeZone: CLINIC_TZ })

// Intl writes "пʼятниця" with U+02BC, which IBM Plex spaces out; use ’ instead
const apostrophe = (text: string) => text.replace(/\u02BC/g, '\u2019')

export const fmtTime = (iso: string) => timeFmt.format(new Date(iso))
export const fmtDate = (iso: string) => dateFmt.format(new Date(iso))
export const fmtLong = (iso: string) => apostrophe(longFmt.format(new Date(iso)))
export const fmtDayMonth = (iso: string) => apostrophe(dayMonthFmt.format(new Date(iso)))
export const fmtDateTime = (iso: string) => `${fmtDate(iso)} ${fmtTime(iso)}`

// YYYY-MM-DD of a moment, in clinic time
export const localDay = (iso: string | Date) =>
  isoDayFmt.format(typeof iso === 'string' ? new Date(iso) : iso)

export const today = () => localDay(new Date())

// Calendar arithmetic on YYYY-MM-DD strings (noon UTC avoids DST edges)
export function addDays(day: string, n: number): string {
  const d = new Date(`${day}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

export function weekdayOf(day: string): number {
  return (new Date(`${day}T12:00:00Z`).getUTCDay() + 6) % 7 // 0 = Monday
}

export const WEEKDAYS_SHORT = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'нд']
export const WEEKDAYS = [
  'понеділок',
  'вівторок',
  'середа',
  'четвер',
  'п’ятниця',
  'субота',
  'неділя',
]

export function dayLabel(day: string): string {
  const d = new Date(`${day}T12:00:00Z`)
  return new Intl.DateTimeFormat('uk-UA', {
    day: 'numeric',
    month: 'long',
    timeZone: 'UTC',
  }).format(d)
}

export function age(birthDate: string): number {
  const [y, m, d] = birthDate.split('-').map(Number)
  const [ty, tm, td] = today().split('-').map(Number)
  return ty - y - (tm < m || (tm === m && td < d) ? 1 : 0)
}

export function relativeDay(iso: string): string {
  const day = localDay(iso)
  if (day === today()) return 'сьогодні'
  if (day === addDays(today(), 1)) return 'завтра'
  return fmtLong(iso)
}
