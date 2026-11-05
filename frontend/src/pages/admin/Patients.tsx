import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../../api/client'
import type { Patient } from '../../api/types'
import { Empty, ErrorBox, Loading, Modal } from '../../components/ui'
import { useToast } from '../../components/toast'
import { age, fmtDate } from '../../lib/time'
import { useAction, useResource } from '../../lib/useResource'

const PAGE = 50

export function Patients() {
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [editing, setEditing] = useState<Patient | 'new' | null>(null)
  const toast = useToast()
  const list = useResource(
    () => api<Patient[]>('/admin/patients', { query: { search, limit: PAGE, offset } }),
    [search, offset],
  )

  return (
    <>
      <div className="page__head">
        <div>
          <h1>Пацієнти</h1>
          <p>Пошук за прізвищем, ім’ям, телефоном або e-mail.</p>
        </div>
        <button className="btn" onClick={() => setEditing('new')}>
          Зареєструвати пацієнта
        </button>
      </div>
      <div className="filters">
        <label className="field" style={{ flex: 1, maxWidth: 420 }}>
          <span>Пошук</span>
          <input
            type="search"
            value={search}
            placeholder="Наприклад: Мельник або 067"
            onChange={(e) => {
              setSearch(e.target.value)
              setOffset(0)
            }}
          />
        </label>
      </div>
      <ErrorBox error={list.error} />
      {list.loading && !list.data && <Loading />}
      {list.data && !list.data.length && <Empty>Нікого не знайдено.</Empty>}
      {!!list.data?.length && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Пацієнт</th>
                <th>Телефон</th>
                <th>E-mail</th>
                <th>Нагадування</th>
                <th>Зареєстрований</th>
                <th aria-label="Дії" />
              </tr>
            </thead>
            <tbody>
              {list.data.map((p) => (
                <tr key={p.id}>
                  <td>
                    {p.full_name}
                    <span className="cell-sub">
                      {fmtDate(`${p.birth_date}T12:00:00Z`)} · {age(p.birth_date)} р.
                    </span>
                  </td>
                  <td className="mono">{p.phone}</td>
                  <td className="mono">{p.email}</td>
                  <td>
                    {[p.notify_email && 'e-mail', p.notify_sms && 'SMS']
                      .filter(Boolean)
                      .join(', ') || <span className="muted">вимкнено</span>}
                  </td>
                  <td className="mono">{fmtDate(p.created_at)}</td>
                  <td>
                    <button className="btn btn--ghost btn--sm" onClick={() => setEditing(p)}>
                      Змінити
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="row" style={{ marginTop: 16 }}>
        <button
          className="btn btn--ghost btn--sm"
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - PAGE))}
        >
          ← Попередні
        </button>
        <button
          className="btn btn--ghost btn--sm"
          disabled={(list.data?.length ?? 0) < PAGE}
          onClick={() => setOffset(offset + PAGE)}
        >
          Наступні →
        </button>
      </div>
      {editing && (
        <PatientDialog
          patient={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onDone={(message) => {
            setEditing(null)
            toast(message)
            list.reload()
          }}
        />
      )}
    </>
  )
}

function PatientDialog({
  patient,
  onClose,
  onDone,
}: {
  patient: Patient | null
  onClose: () => void
  onDone: (message: string) => void
}) {
  const [form, setForm] = useState({
    last_name: patient?.last_name ?? '',
    first_name: patient?.first_name ?? '',
    middle_name: patient?.middle_name ?? '',
    birth_date: patient?.birth_date ?? '',
    phone: patient?.phone ?? '',
    email: '',
    password: '',
    notify_email: patient?.notify_email ?? true,
    notify_sms: patient?.notify_sms ?? true,
  })
  const action = useAction()
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value })

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const { email, password, ...rest } = form
    const body = { ...rest, middle_name: rest.middle_name || null }
    const ok = await action.run(() =>
      patient
        ? api<Patient>(`/admin/patients/${patient.id}`, { method: 'PATCH', body })
        : api<Patient>('/admin/patients', {
            method: 'POST',
            body: { ...body, email, password },
          }),
    )
    if (ok) onDone(patient ? 'Дані пацієнта збережено' : 'Пацієнта зареєстровано')
  }

  return (
    <Modal open onClose={onClose} title={patient ? patient.full_name : 'Новий пацієнт'} wide>
      <form className="stack" onSubmit={submit}>
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
            <span>Дата народження</span>
            <input type="date" required value={form.birth_date} onChange={set('birth_date')} />
          </label>
          <label className="field">
            <span>Телефон</span>
            <input type="tel" required value={form.phone} onChange={set('phone')} />
          </label>
          {!patient && (
            <>
              <label className="field">
                <span>E-mail</span>
                <input type="email" required value={form.email} onChange={set('email')} />
              </label>
              <label className="field">
                <span>Пароль для входу</span>
                <input required minLength={6} value={form.password} onChange={set('password')} />
                <small>Пацієнт зможе змінити дані в кабінеті</small>
              </label>
            </>
          )}
        </div>
        {patient && (
          <div className="row">
            <label className="check">
              <input
                type="checkbox"
                checked={form.notify_email}
                onChange={(e) => setForm({ ...form, notify_email: e.target.checked })}
              />
              Нагадування на e-mail
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={form.notify_sms}
                onChange={(e) => setForm({ ...form, notify_sms: e.target.checked })}
              />
              SMS-нагадування
            </label>
          </div>
        )}
        <ErrorBox error={action.error} />
        <div className="row">
          <button className="btn" disabled={action.busy}>
            {patient ? 'Зберегти' : 'Зареєструвати'}
          </button>
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Скасувати
          </button>
        </div>
      </form>
    </Modal>
  )
}
