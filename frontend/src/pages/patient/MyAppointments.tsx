import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { Appointment } from '../../api/types'
import { CancelDialog, HistoryDialog, RescheduleDialog } from '../../components/AppointmentDialogs'
import { Talon } from '../../components/Talon'
import { Empty, ErrorBox, Loading } from '../../components/ui'
import { useToast } from '../../components/toast'
import { isActive } from '../../lib/labels'
import { useResource } from '../../lib/useResource'

type Scope = 'upcoming' | 'past'
type Dialog = { kind: 'cancel' | 'reschedule' | 'history'; appointment: Appointment } | null

export function MyAppointments() {
  const [scope, setScope] = useState<Scope>('upcoming')
  const [dialog, setDialog] = useState<Dialog>(null)
  const toast = useToast()
  const list = useResource(
    () => api<Appointment[]>('/appointments/my', { query: { scope } }),
    [scope],
  )

  const done = (message: string) => () => {
    setDialog(null)
    toast(message)
    list.reload()
  }

  return (
    <div className="wrap" style={{ maxWidth: 820 }}>
      <div className="page__head">
        <div>
          <h1>Мої записи</h1>
          <p>Талони на прийоми. Скасувати чи перенести можна не пізніше ніж за кілька годин.</p>
        </div>
        <div className="segmented" role="group" aria-label="Які записи показати">
          <button aria-pressed={scope === 'upcoming'} onClick={() => setScope('upcoming')}>
            Майбутні
          </button>
          <button aria-pressed={scope === 'past'} onClick={() => setScope('past')}>
            Минулі
          </button>
        </div>
      </div>

      <ErrorBox error={list.error} />
      {list.loading && !list.data && <Loading />}
      {list.data && !list.data.length && (
        <Empty>
          {scope === 'upcoming' ? (
            <>
              <span>Запланованих прийомів немає.</span>
              <Link className="btn" to="/doctors">
                Записатися до лікаря
              </Link>
            </>
          ) : (
            'Тут з’являться прийоми, які вже відбулися.'
          )}
        </Empty>
      )}

      <div className="stack">
        {list.data?.map((appt) => (
          <Talon
            key={appt.id}
            startsAt={appt.starts_at}
            doctorName={appt.doctor.full_name}
            specialization={appt.doctor.specialization.name}
            room={appt.doctor.room}
            number={appt.id}
            status={appt.status}
            muted={!isActive(appt.status)}
          >
            {appt.reason && <p className="talon__extra">Скарга: {appt.reason}</p>}
            {appt.doctor_notes && (
              <p className="talon__extra">
                <b>Висновок лікаря:</b> {appt.doctor_notes}
              </p>
            )}
            <div className="talon__actions">
              {isActive(appt.status) && (
                <>
                  <button
                    className="btn btn--ghost btn--sm"
                    onClick={() => setDialog({ kind: 'reschedule', appointment: appt })}
                  >
                    Перенести
                  </button>
                  <button
                    className="btn btn--danger btn--sm"
                    onClick={() => setDialog({ kind: 'cancel', appointment: appt })}
                  >
                    Скасувати
                  </button>
                </>
              )}
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => setDialog({ kind: 'history', appointment: appt })}
              >
                Історія
              </button>
            </div>
          </Talon>
        ))}
      </div>

      {dialog?.kind === 'cancel' && (
        <CancelDialog
          appointment={dialog.appointment}
          onClose={() => setDialog(null)}
          onDone={done('Прийом скасовано')}
        />
      )}
      {dialog?.kind === 'reschedule' && (
        <RescheduleDialog
          appointment={dialog.appointment}
          onClose={() => setDialog(null)}
          onDone={done('Прийом перенесено')}
        />
      )}
      {dialog?.kind === 'history' && (
        <HistoryDialog appointment={dialog.appointment} onClose={() => setDialog(null)} />
      )}
    </div>
  )
}
