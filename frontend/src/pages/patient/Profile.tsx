import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../../api/client'
import type { Patient } from '../../api/types'
import { useAuth } from '../../auth/context'
import { ErrorBox } from '../../components/ui'
import { useToast } from '../../components/toast'
import { fmtDate } from '../../lib/time'
import { useAction } from '../../lib/useResource'

export function Profile() {
  const { user, refresh } = useAuth()
  const patient = user?.patient as Patient
  const [phone, setPhone] = useState(patient.phone)
  const [notifyEmail, setNotifyEmail] = useState(patient.notify_email)
  const [notifySms, setNotifySms] = useState(patient.notify_sms)
  const action = useAction()
  const toast = useToast()

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const saved = await action.run(() =>
      api<Patient>('/patients/me', {
        method: 'PATCH',
        body: { phone, notify_email: notifyEmail, notify_sms: notifySms },
      }),
    )
    if (saved) {
      await refresh()
      setPhone(saved.phone)
      toast('Зміни збережено')
    }
  }

  return (
    <div className="wrap" style={{ maxWidth: 720 }}>
      <div className="page__head">
        <div>
          <h1>Профіль</h1>
          <p>Ім’я та дату народження змінює реєстратура – зверніться туди, якщо є помилка.</p>
        </div>
      </div>
      <form className="card stack" onSubmit={submit}>
        <dl className="form-grid" style={{ margin: 0 }}>
          <div>
            <dt className="eyebrow">Пацієнт</dt>
            <dd style={{ margin: '4px 0 0', fontWeight: 600 }}>{patient.full_name}</dd>
          </div>
          <div>
            <dt className="eyebrow">Дата народження</dt>
            <dd className="mono" style={{ margin: '4px 0 0' }}>
              {fmtDate(`${patient.birth_date}T12:00:00Z`)}
            </dd>
          </div>
          <div>
            <dt className="eyebrow">E-mail</dt>
            <dd className="mono" style={{ margin: '4px 0 0' }}>
              {patient.email}
            </dd>
          </div>
        </dl>
        <label className="field">
          <span>Телефон</span>
          <input type="tel" required value={phone} onChange={(e) => setPhone(e.target.value)} />
        </label>
        <fieldset className="stack" style={{ border: 0, padding: 0, margin: 0, gap: 10 }}>
          <legend className="eyebrow" style={{ marginBottom: 10 }}>
            Нагадування про прийоми
          </legend>
          <label className="check">
            <input
              type="checkbox"
              checked={notifyEmail}
              onChange={(e) => setNotifyEmail(e.target.checked)}
            />
            Лист на e-mail перед прийомом
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={notifySms}
              onChange={(e) => setNotifySms(e.target.checked)}
            />
            SMS перед прийомом
          </label>
        </fieldset>
        <ErrorBox error={action.error} />
        <div>
          <button className="btn" disabled={action.busy}>
            Зберегти зміни
          </button>
        </div>
      </form>
    </div>
  )
}
