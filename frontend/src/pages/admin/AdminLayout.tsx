import { NavLink, Outlet } from 'react-router-dom'

const SECTIONS: [string, [string, string][]][] = [
  ['Аналітика', [['/admin', 'Звіти']]],
  [
    'Робота реєстратури',
    [
      ['/admin/appointments', 'Прийоми'],
      ['/admin/notifications', 'Нагадування'],
    ],
  ],
  [
    'Довідники',
    [
      ['/admin/doctors', 'Лікарі'],
      ['/admin/specializations', 'Спеціалізації'],
      ['/admin/patients', 'Пацієнти'],
    ],
  ],
  ['Клініка', [['/admin/settings', 'Налаштування']]],
]

export function AdminLayout() {
  return (
    <div className="wrap admin">
      <nav className="side-nav" aria-label="Розділи адміністратора">
        {SECTIONS.map(([title, links]) => (
          <div key={title} style={{ display: 'contents' }}>
            <span className="eyebrow">{title}</span>
            {links.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === '/admin'}>
                {label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div>
        <Outlet />
      </div>
    </div>
  )
}
