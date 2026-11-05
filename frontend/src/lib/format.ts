import type { WorkingHours } from '../api/types'
import { WEEKDAYS_SHORT } from './time'

// Ukrainian plural forms: 1 лікар, 2 лікарі, 5 лікарів, 11 лікарів, 21 лікар
export function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
  return many
}

// [["пн", "09:00–13:00, 14:00–18:00"], ...] for the days the doctor works
export function weeklySummary(hours: WorkingHours[]): [string, string][] {
  return WEEKDAYS_SHORT.map((label, weekday): [string, string] => {
    const intervals = hours
      .filter((h) => h.weekday === weekday)
      .sort((a, b) => a.start_time.localeCompare(b.start_time))
      .map((h) => `${h.start_time.slice(0, 5)}–${h.end_time.slice(0, 5)}`)
    return [label, intervals.join(', ')]
  }).filter(([, text]) => text)
}
