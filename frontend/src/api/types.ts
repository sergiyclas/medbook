// Mirrors the backend Pydantic schemas (app/schemas). Datetimes arrive as ISO
// strings in UTC; dates as YYYY-MM-DD in the clinic's local calendar.

export type Role = 'patient' | 'doctor' | 'admin'
export type AppointmentStatus = 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | 'no_show'
export type NotificationStatus = 'pending' | 'sending' | 'sent' | 'failed' | 'cancelled' | 'skipped'
export type NotificationChannel = 'email' | 'sms'
export type NotificationKind = 'confirmation' | 'reminder' | 'cancellation'

export interface Specialization {
  id: number
  name: string
  description: string | null
}

export interface WorkingHours {
  id?: number
  weekday: number
  start_time: string
  end_time: string
}

export interface Doctor {
  id: number
  last_name: string
  first_name: string
  middle_name: string | null
  full_name: string
  specialization: Specialization
  room: string | null
  bio: string | null
  slot_minutes: number
  is_active: boolean
  working_hours: WorkingHours[]
}

export interface DoctorAdmin extends Doctor {
  email: string
}

export interface Patient {
  id: number
  email: string
  last_name: string
  first_name: string
  middle_name: string | null
  full_name: string
  phone: string
  birth_date: string
  notify_email: boolean
  notify_sms: boolean
  created_at: string
}

export interface Me {
  id: number
  email: string
  role: Role
  patient: Patient | null
  doctor: Doctor | null
}

export interface Token {
  access_token: string
  role: Role
}

export interface Slot {
  starts_at: string
  ends_at: string
}

export interface NextSlot {
  doctor_id: number
  starts_at: string
}

export interface Appointment {
  id: number
  starts_at: string
  ends_at: string
  status: AppointmentStatus
  reason: string | null
  doctor_notes: string | null
  created_at: string
  doctor: { id: number; full_name: string; specialization: Specialization; room: string | null }
  patient: { id: number; full_name: string; phone: string; email: string; birth_date: string }
}

export interface StatusChange {
  from_status: AppointmentStatus | null
  to_status: AppointmentStatus
  reason: string | null
  changed_at: string
  changed_by_role: Role | null
  changed_by_email: string | null
}

export interface DayOff {
  id: number
  doctor_id: number
  day: string
  reason: string | null
}

export interface ClinicSettings {
  reminder_email_hours_before: number
  reminder_sms_hours_before: number
  max_daily_bookings_per_patient: number
  booking_horizon_days: number
  patient_cancel_cutoff_hours: number
}

export interface NotificationRow {
  id: number
  channel: NotificationChannel
  kind: NotificationKind
  status: NotificationStatus
  send_at: string
  sent_at: string | null
  attempts: number
  last_error: string | null
  appointment: {
    id: number
    starts_at: string
    status: AppointmentStatus
    patient: { id: number; full_name: string }
    doctor: { id: number; full_name: string }
  }
}

export interface ReportColumn {
  key: string
  label: string
  unit: string
}

export interface Report {
  report: string
  title: string
  grouping: string
  columns: ReportColumn[]
  rows: { key: string; label: string; values: Record<string, number> }[]
  totals: Record<string, number>
}

export interface ReportInfo {
  name: string
  title: string
  groupings: { name: string; title: string }[]
}
