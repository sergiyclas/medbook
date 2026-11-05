import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { Doctor, NextSlot, Specialization } from '../../api/types'
import { Talon } from '../../components/Talon'
import { Loading } from '../../components/ui'
import { plural } from '../../lib/format'
import { useResource } from '../../lib/useResource'

export function Home() {
  const data = useResource(
    () =>
      Promise.all([
        api<Specialization[]>('/specializations'),
        api<Doctor[]>('/doctors'),
        api<NextSlot[]>('/doctors/next-free'),
      ]),
    [],
  )
  const [specs = [], doctors = [], nextFree = []] = data.data ?? []
  const nearest = nextFree[0]
  const nearestDoctor = doctors.find((d) => d.id === nearest?.doctor_id)
  const countBySpec = (id: number) => doctors.filter((d) => d.specialization.id === id).length

  return (
    <div className="wrap">
      <section className="hero">
        <div>
          <span className="eyebrow">Поліклініка без черги в реєстратурі</span>
          <h1 style={{ marginTop: 12 }}>
            Талон до лікаря – <em>за хвилину</em>, з дому
          </h1>
          <p>
            Оберіть лікаря, подивіться його вільний час і візьміть талон онлайн. Перед прийомом
            нагадаємо листом і SMS.
          </p>
          <div className="row">
            <Link className="btn" to="/doctors">
              Обрати лікаря
            </Link>
            <Link className="btn btn--ghost" to="/register">
              Зареєструватися
            </Link>
          </div>
        </div>
        <div className="hero__talon">
          {data.loading && <Loading text="Шукаємо найближчий вільний час…" />}
          {nearest && nearestDoctor && (
            <Talon
              startsAt={nearest.starts_at}
              doctorName={nearestDoctor.full_name}
              specialization={nearestDoctor.specialization.name}
              room={nearestDoctor.room}
              stampText="Вільно"
            >
              <div className="talon__actions">
                <Link className="btn btn--sm" to={`/doctors/${nearestDoctor.id}`}>
                  Узяти цей час
                </Link>
                <span className="muted" style={{ fontSize: 14, alignSelf: 'center' }}>
                  найближчий вільний прийом у клініці
                </span>
              </div>
            </Talon>
          )}
        </div>
      </section>

      <section>
        <div className="page__head">
          <div>
            <h2>Спеціалізації</h2>
            <p>
              {doctors.length} лікарів приймають у {specs.length} напрямах
            </p>
          </div>
        </div>
        <div className="grid-cards">
          {specs.map((spec) => (
            <Link key={spec.id} className="spec-card" to={`/doctors?spec=${spec.id}`}>
              <h3>{spec.name}</h3>
              <p>{spec.description}</p>
              <span className="mono">
                {countBySpec(spec.id)} {plural(countBySpec(spec.id), 'лікар', 'лікарі', 'лікарів')}{' '}
                →
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="steps" aria-label="Як це працює">
        <div>
          <h3>Оберіть лікаря</h3>
          <p>За спеціалізацією або за найближчим вільним часом.</p>
        </div>
        <div>
          <h3>Візьміть талон</h3>
          <p>Час закріплюється за вами одразу – ніхто інший його вже не займе.</p>
        </div>
        <div>
          <h3>Отримайте нагадування</h3>
          <p>Лист і SMS перед прийомом. Скасувати чи перенести можна в кабінеті.</p>
        </div>
      </section>
    </div>
  )
}
