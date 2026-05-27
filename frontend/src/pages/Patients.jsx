import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import ClassBadge from '../components/ClassBadge'
import { useApp } from '../context/AppContext'
import { records } from '../data/dashboard'

const ALL_CLASSES = ['Все', 'Normal', 'Suspect', 'Pathological']

function SkeletonRow() {
  return (
    <tr>
      {[35, 18, 14, 18, 12, 10].map((w, i) => (
        <td key={i} className="px-4 py-3">
          <div className="skeleton h-3 rounded" style={{ width: `${w}%` }} />
        </td>
      ))}
    </tr>
  )
}

export default function Patients() {
  const navigate = useNavigate()
  const { setActivePatient, addToast } = useApp()
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('Все')

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 650)
    return () => clearTimeout(t)
  }, [])

  const filtered = records.filter(r => {
    const matchSearch = r.id.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === 'Все' || r.cls === filter
    return matchSearch && matchFilter
  })

  function handleRowClick(rec) {
    setActivePatient({
      id: rec.id, weeks: rec.weeks, date: '27.05.2026', time: rec.time,
      filename: `ctg_${rec.id.replace('№', '')}_record.dat`,
      format: 'WFDB', duration: '20 мин', fs: '4 Гц', samples: '4 800 отсчётов',
      cls: rec.cls, conf: rec.conf,
      probabilities: rec.cls === 'Normal'
        ? { Normal: rec.conf, Suspect: +(1 - rec.conf - 0.01).toFixed(2), Pathological: 0.01 }
        : rec.cls === 'Suspect'
        ? { Normal: +(1 - rec.conf - 0.05).toFixed(2), Suspect: rec.conf, Pathological: 0.05 }
        : { Normal: 0.03, Suspect: +(1 - rec.conf - 0.03).toFixed(2), Pathological: rec.conf },
    })
    addToast(`Открыта карточка ${rec.id}`, 'success')
    navigate('/analysis')
  }

  return (
    <div>
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          Пациентки
        </h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          Все записи КТГ · смена 27.05.2026
        </p>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3 mb-5 animate-fade-up delay-100">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Поиск по ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-xl border border-border dark:border-gray-600 bg-white dark:bg-gray-800 text-ink dark:text-gray-100 outline-none focus:ring-2 focus:ring-navy/30"
          />
        </div>

        <div className="flex gap-1.5">
          {ALL_CLASSES.map(cls => (
            <button
              key={cls}
              onClick={() => setFilter(cls)}
              className={`px-3 py-1.5 text-xs font-600 rounded-lg transition-colors ${
                filter === cls
                  ? 'bg-navy text-white'
                  : 'bg-white dark:bg-gray-800 text-muted dark:text-gray-400 border border-border dark:border-gray-600 hover:bg-card-bg dark:hover:bg-gray-700'
              }`}
              style={{ fontWeight: 600 }}
            >
              {cls}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 overflow-hidden animate-fade-up delay-200">
        <table className="w-full">
          <thead>
            <tr className="bg-[#F8FAFD] dark:bg-gray-900 text-left border-b border-border dark:border-gray-700">
              {['Пациентка', 'Срок', 'Время', 'Прогноз', 'Conf.', ''].map(col => (
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
              : filtered.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm text-muted dark:text-gray-500">
                    Нет записей, соответствующих фильтру
                  </td>
                </tr>
              )
              : filtered.map((rec, i) => (
                <tr
                  key={rec.id}
                  onClick={() => handleRowClick(rec)}
                  className="border-t border-border dark:border-gray-700 hover:bg-card-bg dark:hover:bg-gray-700 cursor-pointer transition-colors animate-fade-up"
                  style={{ animationDelay: `${i * 50}ms` }}
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
                  <td className="px-4 py-3 text-xs text-navy dark:text-blue-400 font-500" style={{ fontWeight: 500 }}>
                    Открыть →
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  )
}
