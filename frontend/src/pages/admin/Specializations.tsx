import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../../api/client'
import type { Specialization } from '../../api/types'
import { ErrorBox, Loading } from '../../components/ui'
import { useToast } from '../../components/toast'
import { useAction, useResource } from '../../lib/useResource'

export function Specializations() {
  const list = useResource(() => api<Specialization[]>('/specializations'), [])
  const [editing, setEditing] = useState<Specialization | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const action = useAction()
  const toast = useToast()

  const startEdit = (spec: Specialization | null) => {
    setEditing(spec)
    setName(spec?.name ?? '')
    setDescription(spec?.description ?? '')
    action.setError(null)
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const body = { name: name.trim(), description: description.trim() || null }
    const saved = await action.run(() =>
      editing
        ? api<Specialization>(`/admin/specializations/${editing.id}`, { method: 'PUT', body })
        : api<Specialization>('/admin/specializations', { method: 'POST', body }),
    )
    if (saved) {
      toast(editing ? 'Зміни збережено' : 'Спеціалізацію додано')
      startEdit(null)
      list.reload()
    }
  }

  const remove = async (spec: Specialization) => {
    await action.run(() => api(`/admin/specializations/${spec.id}`, { method: 'DELETE' }))
    list.reload()
  }

  return (
    <>
      <div className="page__head">
        <div>
          <h1>Спеціалізації</h1>
          <p>Напрями, за якими пацієнти шукають лікаря на сайті.</p>
        </div>
      </div>
      <form className="card stack" onSubmit={submit} style={{ marginBottom: 16 }}>
        <h2>{editing ? `Редагування: ${editing.name}` : 'Нова спеціалізація'}</h2>
        <div className="form-grid">
          <label className="field">
            <span>Назва</span>
            <input required minLength={2} value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="field">
            <span>Опис для пацієнтів</span>
            <input value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
        </div>
        <ErrorBox error={action.error} />
        <div className="row">
          <button className="btn" disabled={action.busy}>
            {editing ? 'Зберегти' : 'Додати'}
          </button>
          {editing && (
            <button type="button" className="btn btn--ghost" onClick={() => startEdit(null)}>
              Скасувати редагування
            </button>
          )}
        </div>
      </form>
      {list.loading && !list.data && <Loading />}
      {list.data && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Назва</th>
                <th>Опис</th>
                <th aria-label="Дії" />
              </tr>
            </thead>
            <tbody>
              {list.data.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 500 }}>{s.name}</td>
                  <td className="muted">{s.description}</td>
                  <td>
                    <div className="row" style={{ gap: 6, justifyContent: 'flex-end' }}>
                      <button className="btn btn--ghost btn--sm" onClick={() => startEdit(s)}>
                        Змінити
                      </button>
                      <button className="btn btn--danger btn--sm" onClick={() => remove(s)}>
                        Видалити
                      </button>
                    </div>
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
