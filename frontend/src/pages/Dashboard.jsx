import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import ClassBadge from '../components/ClassBadge'
import api from '../api/client'

const statColors = {
  navy:  { bg: 'bg-[#EEF2F9]', text: 'text-navy',      dark: 'dark:bg-blue-950 dark:text-blue-300' },
  green: { bg: 'bg-green-bg',  text: 'text-green',      dark: 'dark:bg-green-950 dark:text-green-400' },
  amber: { bg: 'bg-amber-bg',  text: 'text-amber-dark', dark: 'dark:bg-yellow-950 dark:text-yellow-400' },
  red:   { bg: 'bg-red-bg',    text: 'text-red-dark',   dark: 'dark:bg-red-950 dark:text-red-400' },
}

function StatCard({ value, label, color, delay }) {
  const c = statColors[color] || statColors.navy
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl px-6 py-5 flex-1 animate-fade-up ${c.bg} ${c.dark}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <span className={`text-[38px] leading-none ${c.text}`} style={{ fontWeight: 800 }}>
        {value}
      </span>
      <span className={`text-sm mt-1 text-center ${c.text} opacity-80`} style={{ fontWeight: 500 }}>
        {label}
      </span>
    </div>
  )
}

function SkeletonRow() {
  return (
    <tr>
      {[40, 20, 16, 20, 12].map((w, i) => (
        <td key={i} className="px-4 py-3">
          <div className="skeleton h-3 rounded" style={{ width: `${w}%` }} />
        </td>
      ))}
    </tr>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { setActivePatient, addToast } = useApp()
  const [stats, setStats]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    api.dashboardStats()
      .then(data => { setStats(data); setLoading(false) })
      .catch(e  => { setError(e.message); setLoading(false) })
  }, [])

  function handleRowClick(visit) {
    setActivePatient({
      id:           visit.patient_id || '—',
      weeks:        visit.weeks_gestation ? `${visit.weeks_gestation} нед.` : '—',
      date:         formatDate(visit.visit_date),
      time:         '',
      filename:     visit.input_format || 'api',
      format:       visit.input_format || 'API',
      duration:     '—',
      fs:           '—',
      samples:      '—',
      cls:          visit.predicted_class,
      conf:         Math.max(...Object.values(visit.probabilities || {})),
      probabilities: visit.probabilities || {},
      features:     visit.features || {},
      topFeatures:  visit.shap_top || [],
      visitId:      visit.id,
    })
    addToast(`Открыта запись пациента ${visit.patient_id || '#' + visit.id}`, 'success')
    navigate('/analysis')
  }

  const statCards = stats
    ? [
        { value: stats.total_patients,          label: 'Пациентов',         color: 'navy'  },
        { value: stats.by_class?.Normal ?? 0,   label: 'Норма',             color: 'green' },
        { value: stats.by_class?.Suspect ?? 0,  label: 'Подозрительные',    color: 'amber' },
        { value: stats.by_class?.Pathological ?? 0, label: 'Патология',     color: 'red'   },
      ]
    : []

  return (
    <div>
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          Дашборд наблюдений
        </h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          {stats
            ? `Всего приёмов: ${stats.total_visits} · сегодня: ${stats.today_visits}`
            : 'Загрузка...'}
        </p>
      </div>

      {/* Stat cards */}
      <div className="flex gap-3.5 mb-6">
        {loading
          ? [0, 1, 2, 3].map(i => (
              <div key={i} className="skeleton rounded-2xl flex-1 h-[88px]" />
            ))
          : statCards.map((s, i) => (
              <StatCard key={s.label} {...s} delay={i * 80} />
            ))
        }
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-xl bg-red-bg text-red-dark text-sm border border-red-200">
          Не удалось загрузить данные: {error}
        </div>
      )}

      {/* Recent visits table */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 overflow-hidden animate-fade-up delay-300">
        <div className="px-5 py-4 border-b border-border dark:border-gray-700">
          <h2 className="text-base text-ink dark:text-gray-100" style={{ fontWeight: 700 }}>
            Последние записи КТГ
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#F8FAFD] dark:bg-gray-900 text-left">
                {['Пациент', 'Срок', 'Дата/Время', 'Прогноз', 'Conf.'].map(col => (
                  <th key={col} className="px-4 py-3 text-xs text-muted dark:text-gray-400 uppercase tracking-wide" style={{ fontWeight: 600 }}>
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)
                : (!stats?.recent_visits?.length)
                ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-sm text-muted dark:text-gray-500">
                      Нет записей. Загрузите данные через раздел «Загрузить данные».
                    </td>
                  </tr>
                )
                : stats.recent_visits.map((v, i) => {
                  const conf = v.probabilities
                    ? Math.max(...Object.values(v.probabilities))
                    : 0
                  return (
                    <tr
                      key={v.id}
                      onClick={() => handleRowClick(v)}
                      className="border-t border-border dark:border-gray-700 hover:bg-card-bg dark:hover:bg-gray-700 cursor-pointer transition-colors animate-fade-up"
                      style={{ animationDelay: `${i * 60}ms` }}
                    >
                      <td className="px-4 py-3 text-sm text-navy dark:text-blue-300" style={{ fontWeight: 700 }}>
                        {v.patient_id || <span className="text-muted">—</span>}
                      </td>
                      <td className="px-4 py-3 text-sm text-ink dark:text-gray-200">
                        {v.weeks_gestation ? `${v.weeks_gestation} нед.` : '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted dark:text-gray-400">
                        {formatDate(v.visit_date)}
                      </td>
                      <td className="px-4 py-3">
                        <ClassBadge cls={v.predicted_class} size="sm" />
                      </td>
                      <td className="px-4 py-3 text-sm text-ink dark:text-gray-200" style={{ fontWeight: 600 }}>
                        {conf.toFixed(2)}
                      </td>
                    </tr>
                  )
                })
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
