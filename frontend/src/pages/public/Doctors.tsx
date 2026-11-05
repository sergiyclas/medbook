import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../api/client'
import type { Doctor, NextSlot, Specialization } from '../../api/types'
import { Empty, ErrorBox, Loading } from '../../components/ui'
import { useResource } from '../../lib/useResource'
import { fmtTime, relativeDay } from '../../lib/time'

export function Doctors() {
  const [params, setParams] = useSearchParams()
  const specId = params.get('spec') ? Number(params.get('spec')) : null

  const specs = useResource(() => api<Specialization[]>('/specializations'), [])
  const list = useResource(
    () =>
      Promise.all([
        api<Doctor[]>('/doctors', { query: { specialization_id: specId } }),
        api<NextSlot[]>('/doctors/next-free', { query: { specialization_id: specId } }),
      ]),
    [specId],
  )
  const [doctors = [], nextFree = []] = list.data ?? []
  const nextOf = (id: number) => nextFree.find((s) => s.doctor_id === id)?.starts_at

  return (
    <div className="wrap">
      <div className="page__head">
        <div>
          <h1>Лікарі</h1>
          <p>Біля кожного лікаря – його найближчий вільний час.</p>
        </div>
      </div>

      <div className="chips" role="group" aria-label="Спеціалізація" style={{ marginBottom: 24 }}>
        <button className="chip" aria-pressed={specId === null} onClick={() => setParams({})}>
          Усі
        </button>
        {specs.data?.map((s) => (
          <button
            key={s.id}
            className="chip"
            aria-pressed={specId === s.id}
            onClick={() => setParams({ spec: String(s.id) })}
          >
            {s.name}
          </button>
        ))}
      </div>

      <ErrorBox error={list.error} />
      {list.loading && !list.data && <Loading />}
      {list.data && !doctors.length && (
        <Empty>За цією спеціалізацією зараз ніхто не приймає.</Empty>
      )}

      <div className="stack">
        {doctors.map((doctor) => {
          const next = nextOf(doctor.id)
          return (
            <Link
              key={doctor.id}
              to={`/doctors/${doctor.id}`}
              className="card doctor-list-item spec-card"
            >
              <div className="doctor-card">
                <div>
                  <h3>{doctor.full_name}</h3>
                  <span className="muted">{doctor.specialization.name}</span>
                </div>
                {doctor.room && (
                  <span className="door-plate">
                    <span className="mono">{doctor.room}</span>
                    <span>кабінет</span>
                  </span>
                )}
              </div>
              <div className="next-free">
                <span className="eyebrow">Найближчий вільний</span>
                {next ? (
                  <>
                    <div className="mono">{fmtTime(next)}</div>
                    <div className="muted">{relativeDay(next)}</div>
                  </>
                ) : (
                  <div className="muted">поки немає</div>
                )}
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
