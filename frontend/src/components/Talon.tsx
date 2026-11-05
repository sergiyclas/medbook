import type { ReactNode } from 'react'
import type { AppointmentStatus } from '../api/types'
import { STATUS } from '../lib/labels'
import { fmtLong, fmtTime } from '../lib/time'

interface TalonProps {
  startsAt: string
  doctorName: string
  specialization: string
  room: string | null
  number?: number
  status?: AppointmentStatus
  stampText?: string
  freshStamp?: boolean
  muted?: boolean
  children?: ReactNode
}

// The paper ticket a Ukrainian clinic registry hands out: big time, the doctor,
// and the cabinet number on a tear-off stub. Status is a rubber stamp.
export function Talon({
  startsAt,
  doctorName,
  specialization,
  room,
  number,
  status,
  stampText,
  freshStamp,
  muted,
  children,
}: TalonProps) {
  const stamp = stampText ?? (status ? STATUS[status] : null)
  return (
    <article className={`talon${muted ? ' talon--muted' : ''}`}>
      <div className="talon__main">
        <span className="eyebrow">
          Талон до лікаря{number ? <span className="mono"> · № {number}</span> : null}
        </span>
        <time className="talon__time" dateTime={startsAt}>
          {fmtTime(startsAt)}
        </time>
        <span className="talon__date">{fmtLong(startsAt)}</span>
        <span className="talon__doctor">{doctorName}</span>
        <span className="muted">{specialization}</span>
        {children}
        {stamp && (
          <span
            className={`stamp${status ? ` stamp--${status}` : ''}${freshStamp ? ' stamp--fresh' : ''}`}
          >
            {stamp}
          </span>
        )}
      </div>
      <div className="talon__stub">
        <span className="eyebrow">Кабінет</span>
        <span className="talon__room">{room ?? '–'}</span>
      </div>
    </article>
  )
}
