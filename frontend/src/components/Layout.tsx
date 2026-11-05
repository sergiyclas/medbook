import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/context'
import type { Role } from '../api/types'

const LINKS: Record<Role | 'guest', [string, string][]> = {
  guest: [
    ['/doctors', 'Лікарі'],
    ['/login', 'Увійти'],
  ],
  patient: [
    ['/doctors', 'Записатися'],
    ['/my', 'Мої записи'],
    ['/profile', 'Профіль'],
  ],
  doctor: [
    ['/doctor', 'Розклад'],
    ['/doctor/history', 'Історія прийомів'],
  ],
  admin: [
    ['/admin', 'Звіти'],
    ['/admin/appointments', 'Прийоми'],
    ['/doctors', 'Сайт'],
  ],
}

const ROLE_LABEL: Record<Role, string> = {
  patient: 'Пацієнт',
  doctor: 'Лікар',
  admin: 'Адміністратор',
}

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const name = user?.patient?.full_name ?? user?.doctor?.full_name ?? user?.email

  return (
    <div className="shell">
      <header className="topbar">
        <div className="wrap topbar__row">
          <NavLink to="/" className="brand" aria-label="MedBook, на головну">
            <span className="brand__name">
              Med<b>Book</b>
            </span>
            <span className="brand__tag">онлайн-реєстратура</span>
          </NavLink>
          <nav className="nav" aria-label="Основна навігація">
            {LINKS[user?.role ?? 'guest'].map(([to, label]) => (
              <NavLink key={to} to={to} end={to === '/admin' || to === '/doctor'}>
                {label}
              </NavLink>
            ))}
            {user && (
              <div className="user-chip">
                <span>
                  <span className="cell-sub">{ROLE_LABEL[user.role]}</span>
                  {name}
                </span>
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={() => {
                    logout()
                    navigate('/')
                  }}
                >
                  Вийти
                </button>
              </div>
            )}
          </nav>
        </div>
      </header>
      <main className="page">
        <Outlet />
      </main>
      <footer className="footer">
        <div className="wrap">
          MedBook – онлайн-запис до лікаря. Час прийомів указано за Києвом.
        </div>
      </footer>
    </div>
  )
}
