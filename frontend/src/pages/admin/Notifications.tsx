import { useState } from 'react'
import { api } from '../../api/client'
import type { NotificationChannel, NotificationRow, NotificationStatus } from '../../api/types'
import { Empty, ErrorBox, Loading, NotificationBadge } from '../../components/ui'
import { useToast } from '../../components/toast'
import { CHANNEL, KIND, NOTIFICATION_STATUS } from '../../lib/labels'
import { fmtDateTime } from '../../lib/time'
import { useAction, useResource } from '../../lib/useResource'

export function Notifications() {
  const [status, setStatus] = useState<NotificationStatus | ''>('')
  const [channel, setChannel] = useState<NotificationChannel | ''>('')
  const toast = useToast()
  const action = useAction()
  const list = useResource(
    () =>
      api<NotificationRow[]>('/admin/notifications', { query: { status, channel, limit: 200 } }),
    [status, channel],
  )

  const retry = async (row: NotificationRow) => {
    const ok = await action.run(() =>
      api<NotificationRow>(`/admin/notifications/${row.id}/retry`, { method: 'POST' }),
    )
    if (ok) {
      toast('Повідомлення знову в черзі')
      list.reload()
    }
  }

  return (
    <>
      <div className="page__head">
        <div>
          <h1>Нагадування</h1>
          <p>Черга листів і SMS. Фоновий процес надсилає їх, коли настає час.</p>
        </div>
      </div>
      <div className="filters">
        <label className="field">
          <span>Статус</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as NotificationStatus | '')}
          >
            <option value="">Будь-який</option>
            {Object.entries(NOTIFICATION_STATUS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Канал</span>
          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value as NotificationChannel | '')}
          >
            <option value="">Усі</option>
            <option value="email">E-mail</option>
            <option value="sms">SMS</option>
          </select>
        </label>
      </div>
      <ErrorBox error={list.error ?? action.error} />
      {list.loading && !list.data && <Loading />}
      {list.data && !list.data.length && <Empty>Повідомлень з такими умовами немає.</Empty>}
      {!!list.data?.length && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Коли</th>
                <th>Що</th>
                <th>Кому</th>
                <th>Прийом</th>
                <th>Статус</th>
                <th aria-label="Дії" />
              </tr>
            </thead>
            <tbody>
              {list.data.map((n) => (
                <tr key={n.id}>
                  <td className="mono">
                    {fmtDateTime(n.sent_at ?? n.send_at)}
                    <span className="cell-sub">{n.sent_at ? 'надіслано' : 'заплановано'}</span>
                  </td>
                  <td>
                    {KIND[n.kind]}
                    <span className="cell-sub">{CHANNEL[n.channel]}</span>
                  </td>
                  <td>{n.appointment.patient.full_name}</td>
                  <td>
                    <span className="mono">{fmtDateTime(n.appointment.starts_at)}</span>
                    <span className="cell-sub">{n.appointment.doctor.full_name}</span>
                  </td>
                  <td>
                    <NotificationBadge status={n.status} />
                    {n.last_error && <span className="cell-sub">{n.last_error}</span>}
                    {n.attempts > 1 && <span className="cell-sub">спроб: {n.attempts}</span>}
                  </td>
                  <td>
                    {n.status === 'failed' && (
                      <button className="btn btn--ghost btn--sm" onClick={() => retry(n)}>
                        Надіслати ще раз
                      </button>
                    )}
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
