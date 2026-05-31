import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import ClassBadge from '../components/ClassBadge'
import api from '../api/client'

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

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: '2-digit', month: '2-digit', year: '2-digit',
  })
}

export default function Patients() {
  const navigate = useNavigate()
  const [patients, setPatients] = useState([])
  const [total, setTotal]       = useState(0)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [search, setSearch]     = useState('')
  const [filter, setFilter]     = useState('Все')

  const load = useCallback((q) => {
    setLoading(true)
    setError(null)
    api.patients(q ? { search: q } : {})
      .then(d => {
        setPatients(d.patients || [])
        setTotal(d.total || 0)
        setLoading(false)
      })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(search) }, [])

  function handleSearch(e) {
    setSearch(e.target.value)
    load(e.target.value)
  }

  const filtered = filter === 'Все'
    ? patients
    : patients.filter(p => p.last_visit?.predicted_class === filter)

  return (
    <div>
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          Пациентки
        </h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          {loading ? 'Загрузка...' : `Всего: ${total}`}
        </p>
      </div>

      <div className="flex items-center gap-3 mb-5 animate-fade-up delay-100">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Поиск по ID..."
            value={search}
            onChange={handleSearch}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-xl border border-border dark:border-gray-600 bg-white dark:bg-gray-800 text-ink dark:text-gray-100 outline-none focus:ring-2 focus:ring-navy/30"
          />
        </div>
        <div className="flex gap-1.5">
          {ALL_CLASSES.map(cls => (
            <button
              key={cls}
              onClick={() => setFilter(cls)}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
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

      {error && (
        <div className="mb-4 px-4 py-3 rounded-xl bg-red-bg text-red-dark text-sm border border-red-200">
          Ошибка загрузки: {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 overflow-hidden animate-fade-up delay-200">
        <table className="w-full">
          <thead>
            <tr className="bg-[#F8FAFD] dark:bg-gray-900 text-left border-b border-border dark:border-gray-700">
              {['Пациентка', 'Срок', 'Приёмов', 'Последний прогноз', 'Дата', ''].map(col => (
                <th key={col} className="px-4 py-3 text-xs text-muted dark:text-gray-400 uppercase tracking-wide" style={{ fontWeight: 600 }}>
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
                    {search ? 'Нет результатов для поиска' : 'Нет пациентов. Загрузите первую запись КТГ.'}
                  </td>
                </tr>
              )
              : filtered.map((pat, i) => (
                <tr
                  key={pat.patient_id}
                  onClick={() => navigate(`/patients/${encodeURIComponent(pat.patient_id)}`)}
                  className="border-t border-border dark:border-gray-700 hover:bg-card-bg dark:hover:bg-gray-700 cursor-pointer transition-colors animate-fade-up"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <td className="px-4 py-3 text-sm text-navy dark:text-blue-300" style={{ fontWeight: 700 }}>
                    {pat.patient_id}
                  </td>
                  <td className="px-4 py-3 text-sm text-ink dark:text-gray-200">
                    {pat.weeks_gestation ? `${pat.weeks_gestation} нед.` : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-ink dark:text-gray-200">
                    {pat.visits_count ?? 0}
                  </td>
                  <td className="px-4 py-3">
                    {pat.last_visit
                      ? <ClassBadge cls={pat.last_visit.predicted_class} size="sm" />
                      : <span className="text-xs text-muted">—</span>
                    }
                  </td>
                  <td className="px-4 py-3 text-sm text-muted dark:text-gray-400">
                    {pat.last_visit ? formatDate(pat.last_visit.visit_date) : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-navy dark:text-blue-400" style={{ fontWeight: 500 }}>
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
