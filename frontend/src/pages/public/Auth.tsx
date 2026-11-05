import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../../api/client'
import type { Token } from '../../api/types'
import { HOME_BY_ROLE, useAuth } from '../../auth/context'
import { ErrorBox } from '../../components/ui'
import { useAction } from '../../lib/useResource'

const DEMO = [
  ['Пацієнт', 'patient@medbook.example', 'patient123'],
  ['Лікар', 'doctor@medbook.example', 'doctor123'],
  ['Адміністратор', 'admin@medbook.example', 'admin123'],
]

function useAfterLogin() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  return (role: keyof typeof HOME_BY_ROLE) => navigate(params.get('next') ?? HOME_BY_ROLE[role])
}

export function Login() {
  const { login } = useAuth()
  const done = useAfterLogin()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const action = useAction()

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const me = await action.run(() => login(email, password))
    if (me) done(me.role)
  }

  return (
    <div className="wrap" style={{ maxWidth: 460 }}>
      <form className="card stack" onSubmit={submit}>
        <h1 style={{ fontSize: 28 }}>Вхід</h1>
        <label className="field">
          <span>E-mail</span>
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="field">
          <span>Пароль</span>
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <ErrorBox error={action.error} />
        <button className="btn" disabled={action.busy}>
          {action.busy ? 'Входимо…' : 'Увійти'}
        </button>
        <p className="muted">
          Ще немає облікового запису? <Link to="/register">Зареєструватися</Link>
        </p>
      </form>
      <div className="card" style={{ marginTop: 16 }}>
        <p className="eyebrow" style={{ marginBottom: 8 }}>
          Демо-доступ
        </p>
        <div className="stack" style={{ gap: 6 }}>
          {DEMO.map(([role, demoEmail, demoPassword]) => (
            <button
              key={role}
              type="button"
              className="link-btn"
              style={{ textAlign: 'left' }}
              onClick={() => {
                setEmail(demoEmail)
                setPassword(demoPassword)
              }}
            >
              {role}: <span className="mono">{demoEmail}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export function Register() {
  const { acceptToken } = useAuth()
  const done = useAfterLogin()
  const [form, setForm] = useState({
    last_name: '',
    first_name: '',
    middle_name: '',
    birth_date: '',
    phone: '',
    email: '',
    password: '',
  })
  const action = useAction()
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value })

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const me = await action.run(async () => {
      const { access_token } = await api<Token>('/auth/register', {
        method: 'POST',
        body: { ...form, middle_name: form.middle_name || null },
      })
      return acceptToken(access_token)
    })
    if (me) done(me.role)
  }

  return (
    <div className="wrap" style={{ maxWidth: 640 }}>
      <form className="card stack" onSubmit={submit}>
        <div>
          <h1 style={{ fontSize: 28 }}>Реєстрація пацієнта</h1>
          <p className="muted" style={{ marginTop: 6 }}>
            Потрібна один раз – далі записуєтеся до будь-якого лікаря в кілька кліків.
          </p>
        </div>
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
            <input
              type="tel"
              required
              placeholder="+380 67 123 45 67"
              value={form.phone}
              onChange={set('phone')}
            />
            <small>Сюди прийде SMS-нагадування</small>
          </label>
          <label className="field">
            <span>E-mail</span>
            <input type="email" required value={form.email} onChange={set('email')} />
          </label>
          <label className="field">
            <span>Пароль</span>
            <input
              type="password"
              required
              minLength={6}
              autoComplete="new-password"
              value={form.password}
              onChange={set('password')}
            />
            <small>Щонайменше 6 символів</small>
          </label>
        </div>
        <ErrorBox error={action.error} />
        <button className="btn" disabled={action.busy}>
          {action.busy ? 'Реєструємо…' : 'Зареєструватися'}
        </button>
        <p className="muted">
          Уже є обліковий запис? <Link to="/login">Увійти</Link>
        </p>
      </form>
    </div>
  )
}
