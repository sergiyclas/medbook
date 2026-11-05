import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import type { ApiError } from '../api/client'
import type { AppointmentStatus, NotificationStatus, Role } from '../api/types'
import { useAuth } from '../auth/context'
import { NOTIFICATION_STATUS, STATUS } from '../lib/labels'
import { ToastContext } from './toast'

export function StatusBadge({ status }: { status: AppointmentStatus }) {
  return <span className={`badge badge--${status}`}>{STATUS[status]}</span>
}

export function NotificationBadge({ status }: { status: NotificationStatus }) {
  return <span className={`badge badge--${status}`}>{NOTIFICATION_STATUS[status]}</span>
}

export function Loading({ text = 'Завантаження…' }: { text?: string }) {
  return <p className="loading">{text}</p>
}

export function ErrorBox({ error }: { error: ApiError | string | null }) {
  if (!error) return null
  return (
    <p className="alert" role="alert">
      {typeof error === 'string' ? error : error.message}
    </p>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>
}

// Native <dialog>: focus trapping and Esc come from the browser
export function Modal({
  open,
  onClose,
  title,
  wide,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  wide?: boolean
  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      className={`modal${wide ? ' modal--wide' : ''}`}
      onClose={onClose}
      aria-labelledby="modal-title"
    >
      {open && (
        <div className="modal__body">
          <div className="row spread">
            <h2 id="modal-title">{title}</h2>
            <button className="btn btn--ghost btn--sm" onClick={onClose} aria-label="Закрити">
              ✕
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  )
}

export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <Loading />
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  if (user.role !== role) {
    return (
      <div className="wrap">
        <ErrorBox error="Ця сторінка доступна іншій ролі. Увійдіть під відповідним обліковим записом." />
      </div>
    )
  }
  return <>{children}</>
}

// ---------- toast ----------
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const show = useCallback((text: string) => {
    setMessage(text)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setMessage(null), 3500)
  }, [])
  return (
    <ToastContext.Provider value={show}>
      {children}
      {message && (
        <div className="toast" role="status">
          {message}
        </div>
      )}
    </ToastContext.Provider>
  )
}
