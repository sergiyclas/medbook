import { useState } from 'react'
import { api } from '../../api/client'
import type { Appointment } from '../../api/types'
import { Empty, ErrorBox, Loading, StatusBadge } from '../../components/ui'
import { age, fmtDateTime } from '../../lib/time'
import { useResource } from '../../lib/useResource'

const PAGE = 50

export function History() {
  const [offset, setOffset] = useState(0)
  const list = useResource(
    () => api<Appointment[]>('/doctor/history', { query: { limit: PAGE, offset } }),
    [offset],
  )

  return (
    <div className="wrap">
      <div className="page__head">
        <div>
          <h1>Історія прийомів</h1>
          <p>Прийоми, що вже відбулися, від найновіших.</p>
        </div>
      </div>
      <ErrorBox error={list.error} />
      {list.loading && !list.data && <Loading />}
      {list.data && !list.data.length && <Empty>Минулих прийомів поки немає.</Empty>}
      {!!list.data?.length && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Дата і час</th>
                <th>Пацієнт</th>
                <th>Скарга</th>
                <th>Висновок</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {list.data.map((a) => (
                <tr key={a.id}>
                  <td className="mono">{fmtDateTime(a.starts_at)}</td>
                  <td>
                    {a.patient.full_name}
                    <span className="cell-sub">{age(a.patient.birth_date)} р.</span>
                  </td>
                  <td>{a.reason ?? <span className="muted">–</span>}</td>
                  <td>{a.doctor_notes ?? <span className="muted">–</span>}</td>
                  <td>
                    <StatusBadge status={a.status} />
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
          ← Новіші
        </button>
        <button
          className="btn btn--ghost btn--sm"
          disabled={(list.data?.length ?? 0) < PAGE}
          onClick={() => setOffset(offset + PAGE)}
        >
          Старіші →
        </button>
      </div>
    </div>
  )
}
