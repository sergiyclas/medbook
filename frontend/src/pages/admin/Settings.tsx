import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../../api/client'
import type { ClinicSettings } from '../../api/types'
import { ErrorBox, Loading } from '../../components/ui'
import { useToast } from '../../components/toast'
import { useAction, useResource } from '../../lib/useResource'

const FIELDS: [keyof ClinicSettings, string, string, number, number][] = [
  ['reminder_email_hours_before', 'Лист-нагадування', 'годин до прийому', 1, 168],
  ['reminder_sms_hours_before', 'SMS-нагадування', 'годин до прийому', 1, 72],
  ['patient_cancel_cutoff_hours', 'Скасування онлайн', 'не пізніше ніж за, год', 0, 72],
  ['booking_horizon_days', 'Запис наперед', 'днів максимум', 1, 365],
  ['max_daily_bookings_per_patient', 'Записів на день', 'для одного пацієнта', 1, 10],
]

export function Settings() {
  const current = useResource(() => api<ClinicSettings>('/admin/settings'), [])
  return (
    <>
      <div className="page__head">
        <div>
          <h1>Налаштування клініки</h1>
          <p>
            Нові значення діють одразу: для нових записів і для нагадувань, створених після зміни.
          </p>
        </div>
      </div>
      {current.loading && !current.data && <Loading />}
      <ErrorBox error={current.error} />
      {current.data && <SettingsForm initial={current.data} />}
    </>
  )
}

function SettingsForm({ initial }: { initial: ClinicSettings }) {
  const [form, setForm] = useState(initial)
  const action = useAction()
  const toast = useToast()

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const saved = await action.run(() =>
      api<ClinicSettings>('/admin/settings', { method: 'PATCH', body: form }),
    )
    if (saved) {
      setForm(saved)
      toast('Налаштування збережено')
    }
  }

  return (
    <form className="card stack" onSubmit={submit} style={{ maxWidth: 720 }}>
      <div className="form-grid">
        {FIELDS.map(([key, label, hint, min, max]) => (
          <label className="field" key={key}>
            <span>{label}</span>
            <input
              type="number"
              className="mono"
              min={min}
              max={max}
              required
              value={form[key]}
              onChange={(e) => setForm({ ...form, [key]: Number(e.target.value) })}
            />
            <small>{hint}</small>
          </label>
        ))}
      </div>
      <ErrorBox error={action.error} />
      <div>
        <button className="btn" disabled={action.busy}>
          Зберегти налаштування
        </button>
      </div>
    </form>
  )
}
