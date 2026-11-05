import type {
  AppointmentStatus,
  NotificationChannel,
  NotificationKind,
  NotificationStatus,
  Role,
} from '../api/types'

export const ROLE: Record<Role, string> = {
  patient: 'пацієнт',
  doctor: 'лікар',
  admin: 'реєстратура',
}

export const STATUS: Record<AppointmentStatus, string> = {
  scheduled: 'Заплановано',
  confirmed: 'Підтверджено',
  completed: 'Завершено',
  cancelled: 'Скасовано',
  no_show: 'Неявка',
}

export const NOTIFICATION_STATUS: Record<NotificationStatus, string> = {
  pending: 'У черзі',
  sending: 'Надсилається',
  sent: 'Надіслано',
  failed: 'Помилка',
  cancelled: 'Відкликано',
  skipped: 'Пропущено',
}

export const CHANNEL: Record<NotificationChannel, string> = { email: 'E-mail', sms: 'SMS' }

export const KIND: Record<NotificationKind, string> = {
  confirmation: 'Підтвердження запису',
  reminder: 'Нагадування',
  cancellation: 'Скасування',
}

export const isActive = (status: AppointmentStatus) =>
  status === 'scheduled' || status === 'confirmed'
