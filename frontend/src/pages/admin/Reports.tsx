import { useState } from 'react'
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js'
import type { ChartData, ChartOptions } from 'chart.js'
import { Bar } from 'react-chartjs-2'
import { api } from '../../api/client'
import type { DoctorAdmin, Report, ReportInfo } from '../../api/types'
import { ErrorBox, Loading } from '../../components/ui'
import { addDays, today } from '../../lib/time'
import { useResource } from '../../lib/useResource'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)
ChartJS.defaults.font.family = "'IBM Plex Sans', system-ui, sans-serif"
ChartJS.defaults.font.size = 12

// Validated with the dataviz palette checker against the white card surface:
// lightness band, chroma, adjacent CVD separation (≥ 8) and 3:1 contrast all pass
// in this stacking order. Colour follows the entity, never the rank.
const SERIES: Record<string, string> = {
  completed: '#1a7f5a',
  no_show: '#c07c00',
  upcoming: '#6250d6',
  cancelled: '#c73a3a',
}
const SINGLE = '#1a7f5a'
const SURFACE = '#ffffff'
const INK = '#14211d'
const MUTED = '#5a6a64'
const GRID = '#e3e9e6'

const PRESETS: [string, number, string][] = [
  ['30 днів', 30, 'day'],
  ['90 днів', 90, 'day'],
  ['6 місяців', 182, 'month'],
  ['Рік', 365, 'month'],
]

// What each report plots; everything else stays in the table
const PLOTTED: Record<string, string[]> = {
  appointments: ['completed', 'no_show', 'upcoming', 'cancelled'],
  'doctor-load': ['load_pct'],
  'new-patients': ['new'],
}

const fmtNumber = (value: number, unit = '') =>
  `${value.toLocaleString('uk-UA', { maximumFractionDigits: 1 })}${unit ? ` ${unit}` : ''}`

export function Reports() {
  const reports = useResource(() => api<ReportInfo[]>('/admin/reports'), [])
  const doctors = useResource(() => api<DoctorAdmin[]>('/admin/doctors'), [])
  const [name, setName] = useState('appointments')
  const [days, setDays] = useState(30)
  const [grouping, setGrouping] = useState('day')
  const [doctorId, setDoctorId] = useState('')

  const groupings = reports.data?.find((r) => r.name === name)?.groupings ?? []
  // A report that cannot be grouped the chosen way falls back to its first option
  const effective = groupings.some((g) => g.name === grouping)
    ? grouping
    : (groupings[0]?.name ?? grouping)

  const dateTo = today()
  const dateFrom = addDays(dateTo, -(days - 1))
  const supportsDoctor = name !== 'new-patients'
  const report = useResource(
    () =>
      api<Report>(`/admin/reports/${name}`, {
        query: {
          grouping: effective,
          date_from: dateFrom,
          date_to: dateTo,
          doctor_id: supportsDoctor ? doctorId : null,
        },
      }),
    [name, effective, dateFrom, dateTo, doctorId],
  )

  return (
    <>
      <div className="page__head">
        <div>
          <h1>Звіти</h1>
          <p>Прийоми, завантаженість лікарів і приплив нових пацієнтів.</p>
        </div>
      </div>

      <div className="segmented" role="tablist" aria-label="Звіт" style={{ marginBottom: 16 }}>
        {reports.data?.map((r) => (
          <button
            key={r.name}
            role="tab"
            aria-selected={r.name === name}
            aria-pressed={r.name === name}
            onClick={() => setName(r.name)}
          >
            {r.title}
          </button>
        ))}
      </div>

      <div className="filters">
        <div className="field">
          <span>Період</span>
          <div className="chips">
            {PRESETS.map(([label, n, defaultGrouping]) => (
              <button
                key={n}
                className="chip"
                aria-pressed={days === n}
                onClick={() => {
                  setDays(n)
                  if (groupings.some((g) => g.name === defaultGrouping))
                    setGrouping(defaultGrouping)
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="field">
          <span>Групування</span>
          <div className="segmented">
            {groupings.map((g) => (
              <button
                key={g.name}
                aria-pressed={g.name === effective}
                onClick={() => setGrouping(g.name)}
              >
                {g.title}
              </button>
            ))}
          </div>
        </div>
        {supportsDoctor && (
          <label className="field">
            <span>Лікар</span>
            <select value={doctorId} onChange={(e) => setDoctorId(e.target.value)}>
              <option value="">Уся клініка</option>
              {doctors.data?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.full_name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <ErrorBox error={report.error ?? reports.error} />
      {!report.data && report.loading && <Loading />}
      {report.data && <ReportView report={report.data} />}
    </>
  )
}

function ReportView({ report }: { report: Report }) {
  const columns = Object.fromEntries(report.columns.map((c) => [c.key, c]))
  const plotted = PLOTTED[report.report] ?? []
  const horizontal = report.grouping === 'doctor'

  const data: ChartData<'bar'> = {
    labels: report.rows.map((r) => r.label),
    datasets: plotted.map((key, i) => ({
      label: columns[key]?.label ?? key,
      data: report.rows.map((r) => r.values[key] ?? 0),
      backgroundColor: plotted.length > 1 ? SERIES[key] : SINGLE,
      // 2px surface-coloured edge = the gap between stacked segments
      borderColor: SURFACE,
      borderWidth: plotted.length > 1 && i > 0 ? (horizontal ? { left: 2 } : { bottom: 2 }) : 0,
      borderRadius:
        i === plotted.length - 1
          ? horizontal
            ? { topRight: 4, bottomRight: 4 }
            : { topLeft: 4, topRight: 4 }
          : 0,
      borderSkipped: false,
      maxBarThickness: 24,
    })),
  }

  const unit = plotted.length === 1 ? columns[plotted[0]]?.unit : ''
  const valueAxis = {
    stacked: plotted.length > 1,
    beginAtZero: true,
    suggestedMax: unit === '%' ? 100 : undefined,
    grid: { color: GRID, drawTicks: false },
    border: { display: false },
    ticks: {
      color: MUTED,
      padding: 8,
      precision: 0,
      callback: (v: string | number) => `${v}${unit === '%' ? '%' : ''}`,
    },
  }
  const categoryAxis = {
    stacked: plotted.length > 1,
    grid: { display: false },
    border: { color: '#c9d3ce' },
    ticks: { color: MUTED, autoSkipPadding: 12, maxRotation: 0 },
  }

  const options: ChartOptions<'bar'> = {
    indexAxis: horizontal ? 'y' : 'x',
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 250 },
    interaction: { mode: 'index', intersect: false, axis: horizontal ? 'y' : 'x' },
    plugins: {
      legend: {
        display: plotted.length > 1,
        position: 'top',
        align: 'start',
        labels: {
          color: INK,
          boxWidth: 12,
          boxHeight: 12,
          useBorderRadius: true,
          borderRadius: 3,
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: INK,
        padding: 10,
        cornerRadius: 8,
        boxPadding: 4,
        callbacks: {
          label: (ctx) => ` ${ctx.dataset.label}: ${fmtNumber(Number(ctx.raw), unit ?? '')}`,
        },
      },
    },
    scales: horizontal ? { x: valueAxis, y: categoryAxis } : { x: categoryAxis, y: valueAxis },
  }

  const height = horizontal ? Math.max(260, report.rows.length * 34 + 60) : 340

  return (
    <div className="stack">
      <div className="kpis">
        {report.columns.map((c) => (
          <div className="kpi" key={c.key}>
            <div className="kpi__value">{fmtNumber(report.totals[c.key] ?? 0, c.unit)}</div>
            <div className="kpi__label">
              {c.label}
              {c.key === 'load_pct' ? ' (середня за період)' : ''}
            </div>
          </div>
        ))}
      </div>

      <figure className="card" style={{ margin: 0 }}>
        <figcaption style={{ marginBottom: 12 }}>
          <h2>{report.title}</h2>
          {plotted.length === 1 && (
            <p className="muted" style={{ marginTop: 4 }}>
              {columns[plotted[0]]?.label}
              {unit ? `, ${unit}` : ''}
            </p>
          )}
        </figcaption>
        <div className="chart-box" style={{ height }}>
          {report.rows.length ? (
            <Bar data={data} options={options} aria-label={`Графік: ${report.title}`} role="img" />
          ) : (
            <p className="muted">За цей період даних немає.</p>
          )}
        </div>
      </figure>

      <details className="data-table" open={report.rows.length <= 12}>
        <summary>Таблиця даних · {report.rows.length} рядків</summary>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>
                  {report.grouping === 'doctor'
                    ? 'Лікар'
                    : report.grouping === 'month'
                      ? 'Місяць'
                      : 'День'}
                </th>
                {report.columns.map((c) => (
                  <th key={c.key} className="num">
                    {c.label}
                    {c.unit ? `, ${c.unit}` : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.rows.map((row) => (
                <tr key={row.key}>
                  <td>{row.label}</td>
                  {report.columns.map((c) => (
                    <td key={c.key} className="num">
                      {fmtNumber(row.values[c.key] ?? 0)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td>Разом</td>
                {report.columns.map((c) => (
                  <td key={c.key} className="num">
                    {fmtNumber(report.totals[c.key] ?? 0)}
                  </td>
                ))}
              </tr>
            </tfoot>
          </table>
        </div>
      </details>
    </div>
  )
}
