import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { ArrowLeft, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import ClassBadge from '../components/ClassBadge'
import Card from '../components/Card'
import api from '../api/client'
import { useApp } from '../context/AppContext'

const TREND_LABELS = {
  improving:        { label: 'Улучшение',    color: '#1E8E4E', icon: CheckCircle },
  stable:           { label: 'Стабильно',    color: '#3C6BB5', icon: CheckCircle },
  deteriorating:    { label: 'Ухудшение',    color: '#D24B4B', icon: AlertTriangle },
  single_visit:     { label: 'Один приём',   color: '#7A8396', icon: Clock },
  insufficient_data:{ label: 'Недост. данных', color: '#7A8396', icon: Clock },
}

function formatDt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatDay(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
}

const DOCTOR_LABEL_MAP = { N: 'Normal', S: 'Suspect', P: 'Pathological' }

export default function PatientCard() {
  const { pid } = useParams()
  const navigate = useNavigate()
  const { setActivePatient, addToast } = useApp()

  const [patient,   setPatient]   = useState(null)
  const [aggregate, setAggregate] = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)

  useEffect(() => {
    const patientId = decodeURIComponent(pid)
    Promise.all([
      api.patient(patientId),
      api.patientAggregate(patientId).catch(() => null),
    ])
      .then(([p, agg]) => {
        setPatient(p)
        setAggregate(agg)
        setLoading(false)
      })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [pid])

  function openVisit(visit) {
    setActivePatient({
      id:           visit.patient_id || pid,
      weeks:        visit.gestational_week ? `${visit.gestational_week} нед.` : '—',
      date:         formatDt(visit.visit_date),
      time:         '',
      filename:     visit.input_format || 'api',
      format:       visit.input_format || 'API',
      duration:     '—',
      fs:           '—',
      samples:      '—',
      cls:          visit.predicted_class,
      conf:         Math.max(...Object.values(visit.probabilities || { v: 0 })),
      probabilities: visit.probabilities || {},
      features:     visit.features || {},
      topFeatures:  visit.shap_top || [],
      visitId:      visit.id,
    })
    addToast(`Открыт приём #${visit.id}`, 'info')
    navigate('/analysis')
  }

  if (loading) {
    return (
      <div>
        <div className="skeleton h-6 w-40 rounded mb-6" />
        <div className="skeleton h-8 w-64 rounded mb-2" />
        <div className="skeleton h-4 w-80 rounded mb-8" />
        <div className="grid grid-cols-2 gap-5">
          {[140, 180, 200, 160].map((h, i) => (
            <div key={i} className="skeleton rounded-2xl" style={{ height: h }} />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-red-dark mb-4">{error}</p>
        <button onClick={() => navigate(-1)} className="text-navy text-sm hover:underline">
          ← Назад
        </button>
      </div>
    )
  }

  const visits = patient?.visits || []
  const trendCfg = TREND_LABELS[aggregate?.trend] || TREND_LABELS.stable
  const TrendIcon = trendCfg.icon

  // Build chart data from visits (chronological)
  const chartData = [...visits]
    .sort((a, b) => new Date(a.visit_date) - new Date(b.visit_date))
    .map(v => ({
      name:  formatDay(v.visit_date),
      ASTV:  v.features?.ASTV ?? null,
      LB:    v.features?.LB   ?? null,
      DL:    v.features?.DL   ?? null,
    }))
    .filter(d => d.ASTV !== null || d.LB !== null)

  // Schedule info
  const overdue  = patient?.overdue
  const interval = patient?.expected_interval_days
  const daysSince = patient?.days_since_last_visit

  return (
    <div>
      {/* Back */}
      <button
        onClick={() => navigate('/patients')}
        className="flex items-center gap-1.5 text-sm text-muted dark:text-gray-400 hover:text-navy dark:hover:text-blue-300 mb-5 transition-colors"
      >
        <ArrowLeft size={15} /> Все пациентки
      </button>

      {/* Header */}
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          {patient?.patient_id}
        </h1>
        <p className="text-muted dark:text-gray-400 mt-1" style={{ fontSize: 14 }}>
          {patient?.weeks_gestation ? `${patient.weeks_gestation} нед. гестации · ` : ''}
          Приёмов: {visits.length} · Зарегистрирована: {formatDt(patient?.created_at)}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-5">

        {/* ── Aggregate prediction ── */}
        {aggregate && (
          <Card title="Сводный прогноз" className="animate-fade-up delay-100">
            <div className="flex items-center gap-3 mb-3">
              <ClassBadge cls={aggregate.aggregate_class} />
              <div
                className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs"
                style={{ background: trendCfg.color + '18', color: trendCfg.color, fontWeight: 600 }}
              >
                <TrendIcon size={13} />
                {trendCfg.label}
              </div>
            </div>
            <ul className="space-y-1.5">
              {aggregate.explanation.map((ex, i) => (
                <li key={i} className="text-sm text-ink dark:text-gray-200 flex gap-2">
                  <span className="text-muted shrink-0">·</span>
                  <span>{ex}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* ── Schedule info ── */}
        <Card title="Частота наблюдения" className="animate-fade-up delay-150">
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted dark:text-gray-400">Рекомендуемый интервал</span>
              <span className="text-ink dark:text-gray-100" style={{ fontWeight: 600 }}>
                {interval != null ? `${interval} дн.` : '—'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted dark:text-gray-400">Дней с последнего приёма</span>
              <span
                className={daysSince != null
                  ? overdue ? 'text-red-dark font-600' : 'text-green font-600'
                  : 'text-muted'
                }
                style={{ fontWeight: 600 }}
              >
                {daysSince != null ? daysSince : '—'}
              </span>
            </div>
            {overdue && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-bg border border-red-200 text-red-dark text-xs">
                <AlertTriangle size={13} />
                Превышен рекомендуемый интервал наблюдения
              </div>
            )}
            {!overdue && daysSince != null && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-green-bg border border-green-100 text-green text-xs">
                <CheckCircle size={13} />
                Наблюдение проводится в срок
              </div>
            )}
          </div>
        </Card>

        {/* ── Feature dynamics chart ── */}
        {chartData.length >= 2 && (
          <div className="col-span-2 animate-fade-up delay-200">
            <Card title="Динамика признаков по приёмам">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData} margin={{ top: 4, right: 16, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E6EAF2" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#7A8396' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#7A8396' }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E6EAF2' }} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="ASTV" name="ASTV (вариабельность)"
                    stroke="#023A84" strokeWidth={2} dot={{ r: 4 }} connectNulls />
                  <Line type="monotone" dataKey="LB"   name="LB (базальный ритм)"
                    stroke="#1E8E4E" strokeWidth={2} dot={{ r: 4 }} connectNulls />
                  <Line type="monotone" dataKey="DL"   name="DL (децелерации)"
                    stroke="#D24B4B" strokeWidth={2} dot={{ r: 4 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </div>
        )}

        {/* ── Visits table ── */}
        <div className="col-span-2 animate-fade-up delay-300">
          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 overflow-hidden">
            <div className="px-5 py-4 border-b border-border dark:border-gray-700">
              <h2 className="text-base text-ink dark:text-gray-100" style={{ fontWeight: 700 }}>
                История приёмов
              </h2>
            </div>
            <table className="w-full">
              <thead>
                <tr className="bg-[#F8FAFD] dark:bg-gray-900 text-left">
                  {['Дата', 'Срок', 'Прогноз', 'Оценка врача', 'Модель', ''].map(col => (
                    <th key={col} className="px-4 py-3 text-xs text-muted dark:text-gray-400 uppercase tracking-wide" style={{ fontWeight: 600 }}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visits.length === 0
                  ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-10 text-center text-sm text-muted dark:text-gray-500">
                        Нет приёмов
                      </td>
                    </tr>
                  )
                  : [...visits]
                      .sort((a, b) => new Date(b.visit_date) - new Date(a.visit_date))
                      .map((v) => (
                        <tr
                          key={v.id}
                          onClick={() => openVisit(v)}
                          className="border-t border-border dark:border-gray-700 hover:bg-card-bg dark:hover:bg-gray-700 cursor-pointer transition-colors"
                        >
                          <td className="px-4 py-3 text-sm text-muted dark:text-gray-400">
                            {formatDt(v.visit_date)}
                          </td>
                          <td className="px-4 py-3 text-sm text-ink dark:text-gray-200">
                            {v.gestational_week ? `${v.gestational_week} нед.` : '—'}
                          </td>
                          <td className="px-4 py-3">
                            <ClassBadge cls={v.predicted_class} size="sm" />
                          </td>
                          <td className="px-4 py-3">
                            {v.doctor_label
                              ? <ClassBadge cls={DOCTOR_LABEL_MAP[v.doctor_label] || v.doctor_label} size="sm" />
                              : <span className="text-xs text-muted dark:text-gray-500">не оценено</span>
                            }
                          </td>
                          <td className="px-4 py-3 text-xs text-muted dark:text-gray-500">
                            {v.model_version || '—'}
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

      </div>
    </div>
  )
}
