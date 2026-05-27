import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import ClassBadge from '../components/ClassBadge'
import { stats, records } from '../data/dashboard'

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
      <span className={`text-[38px] font-800 leading-none ${c.text}`} style={{ fontWeight: 800 }}>
        {value}
      </span>
      <span className={`text-sm font-500 mt-1 text-center ${c.text} opacity-80`} style={{ fontWeight: 500 }}>
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

export default function Dashboard() {
  const navigate = useNavigate()
  const { setActivePatient, addToast } = useApp()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 650)
    return () => clearTimeout(t)
  }, [])

  function handleRowClick(rec) {
    setActivePatient({
      id:       rec.id,
      weeks:    rec.weeks,
      date:     '27.05.2026',
      time:     rec.time,
      filename: `ctg_${rec.id.replace('№', '')}_record.dat`,
      format:   'WFDB',
      duration: '20 мин',
      fs:       '4 Гц',
      samples:  '4 800 отсчётов',
      cls:      rec.cls,
      conf:     rec.conf,
      probabilities: rec.cls === 'Normal'
        ? { Normal: rec.conf, Suspect: +(1 - rec.conf - 0.01).toFixed(2), Pathological: 0.01 }
        : rec.cls === 'Suspect'
        ? { Normal: +(1 - rec.conf - 0.05).toFixed(2), Suspect: rec.conf, Pathological: 0.05 }
        : { Normal: 0.03, Suspect: +(1 - rec.conf - 0.03).toFixed(2), Pathological: rec.conf },
    })
    addToast(`Открыта запись пациентки ${rec.id}`, 'success')
    navigate('/analysis')
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          Дашборд наблюдений
        </h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          Смена 27.05.2026 · активных пациенток: 24
        </p>
      </div>

      {/* Stat cards */}
      <div className="flex gap-3.5 mb-6">
        {stats.map((s, i) => (
          <StatCard key={s.label} {...s} delay={i * 80} />
        ))}
      </div>

      {/* Table */}
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 overflow-hidden animate-fade-up delay-300"
      >
        <div className="px-5 py-4 border-b border-border dark:border-gray-700">
          <h2 className="text-base font-700 text-ink dark:text-gray-100" style={{ fontWeight: 700 }}>
            Последние записи КТГ
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#F8FAFD] dark:bg-gray-900 text-left">
                {['Пациентка', 'Срок', 'Время', 'Прогноз', 'Conf.'].map(col => (
                  <th
                    key={col}
                    className="px-4 py-3 text-xs font-600 text-muted dark:text-gray-400 uppercase tracking-wide"
                    style={{ fontWeight: 600 }}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)
                : records.map((rec, i) => (
                  <tr
                    key={rec.id}
                    onClick={() => handleRowClick(rec)}
                    className="border-t border-border dark:border-gray-700 hover:bg-card-bg dark:hover:bg-gray-700 cursor-pointer transition-colors animate-fade-up"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <td className="px-4 py-3 text-sm font-700 text-navy dark:text-blue-300" style={{ fontWeight: 700 }}>
                      {rec.id}
                    </td>
                    <td className="px-4 py-3 text-sm text-ink dark:text-gray-200">{rec.weeks}</td>
                    <td className="px-4 py-3 text-sm text-muted dark:text-gray-400">{rec.time}</td>
                    <td className="px-4 py-3">
                      <ClassBadge cls={rec.cls} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-sm font-600 text-ink dark:text-gray-200" style={{ fontWeight: 600 }}>
                      {rec.conf.toFixed(2)}
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
