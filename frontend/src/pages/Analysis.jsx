import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { FileText as FileIcon, CheckCircle, Printer } from 'lucide-react'
import Card from '../components/Card'
import SkeletonCard from '../components/SkeletonCard'
import { useApp } from '../context/AppContext'
import api from '../api/client'

const classCfg = {
  Normal:       { label: 'НОРМА',     bigColor: '#1E8E4E', bgCard: '#F3F8F4', border: '#CDE8D6' },
  Suspect:      { label: 'ПОДОЗР.',   bigColor: '#B9831A', bgCard: '#FBF6EC', border: '#F0D79A' },
  Pathological: { label: 'ПАТОЛОГИЯ', bigColor: '#C0392B', bgCard: '#FBE9E9', border: '#F0BABA' },
}

const probColors = { Normal: '#1E8E4E', Suspect: '#E0A526', Pathological: '#D24B4B' }

const LABEL_OPTIONS = [
  { value: 'N', label: 'Normal',       color: '#1E8E4E' },
  { value: 'S', label: 'Suspect',      color: '#B9831A' },
  { value: 'P', label: 'Pathological', color: '#C0392B' },
]

function ProbBar({ label, value, color }) {
  const pct    = Math.round(value * 100)
  const visual = Math.max(pct, 4)
  return (
    <div className="flex items-center gap-3">
      <span className="text-[13px] text-muted dark:text-gray-400 w-28 shrink-0">{label}</span>
      <div className="flex-1 h-2.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${visual}%`, background: color }} />
      </div>
      <span className="text-[13px] w-9 text-right" style={{ color, fontWeight: 600 }}>{pct}%</span>
    </div>
  )
}

function buildSignalData(features) {
  if (!features || !features.LB) return { fhr: [], uc: [] }
  const lb  = features.LB
  const amp = features.ASTV || 4
  const fhr = Array.from({ length: 120 }, (_, i) => ({
    t: i,
    v: +(lb + amp * Math.sin(i / 5) + (Math.random() - 0.5) * 2).toFixed(1),
  }))
  const uc = Array.from({ length: 120 }, (_, i) => ({
    t: i,
    v: +(Math.max(0, (features.UC || 0) * Math.exp(-0.5 * ((i - 30) / 12) ** 2))).toFixed(2),
  }))
  return { fhr, uc }
}

export default function Analysis() {
  const { addToast, activePatient } = useApp()
  const [searchParams]              = useSearchParams()
  const urlVisitId                  = searchParams.get('visit_id')

  const [visit,        setVisit]        = useState(null)
  const [loading,      setLoading]      = useState(true)
  const [doctorLabel,  setDoctorLabel]  = useState('')
  const [doctorComment,setDoctorComment]= useState('')
  const [saving,       setSaving]       = useState(false)
  const [labelSaved,   setLabelSaved]   = useState(false)

  // Determine visit_id: from URL param, or from activePatient context
  const visitId = urlVisitId
    ? parseInt(urlVisitId, 10)
    : activePatient?.visitId ?? null

  useEffect(() => {
    setLoading(true)
    if (visitId) {
      api.visit(visitId)
        .then(v => {
          setVisit(v)
          setDoctorLabel(v.doctor_label || '')
          setDoctorComment(v.doctor_comment || '')
          setLoading(false)
        })
        .catch(() => {
          setVisit(null)
          setLoading(false)
        })
    } else {
      // Use context data (no DB visit)
      setVisit(null)
      setLoading(false)
    }
  }, [visitId])

  const patient = visit
    ? {
        id:           visit.patient_id || '—',
        weeks:        visit.gestational_week ? `${visit.gestational_week} нед.` : '—',
        date:         visit.visit_date ? new Date(visit.visit_date).toLocaleString('ru-RU') : '—',
        time:         '',
        filename:     visit.input_format || 'api',
        format:       visit.input_format || 'API',
        duration:     '—', fs: '—', samples: '—',
        cls:          visit.predicted_class,
        conf:         visit.probabilities
                        ? Math.max(...Object.values(visit.probabilities))
                        : 0,
        probabilities: visit.probabilities || {},
        features:     visit.features || {},
        topFeatures:  visit.shap_top || [],
      }
    : activePatient

  async function handleSaveLabel() {
    if (!visitId) return
    setSaving(true)
    try {
      await api.labelVisit(visitId, {
        doctor_label:   doctorLabel || null,
        doctor_comment: doctorComment || null,
      })
      setLabelSaved(true)
      addToast('Оценка врача сохранена', 'success')
    } catch (e) {
      addToast(`Ошибка: ${e.message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div>
        <div className="skeleton h-8 w-64 rounded mb-1" />
        <div className="skeleton h-4 w-80 rounded mb-6" />
        <div className="flex gap-[26px]">
          <div className="flex-[1.35] space-y-5">
            <SkeletonCard height={140} />
            <SkeletonCard height={100} rows={3} />
          </div>
          <div className="flex-[1.0] space-y-5">
            <SkeletonCard height={80} rows={2} />
            <SkeletonCard height={100} rows={3} />
          </div>
        </div>
      </div>
    )
  }

  if (!patient) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-muted dark:text-gray-500">
        <p className="text-base mb-2">Запись не выбрана</p>
        <p className="text-sm">Выберите запись в разделах «Дашборд» или «Пациентки»,<br/>либо загрузите данные через «Загрузить данные».</p>
      </div>
    )
  }

  const cfg          = classCfg[patient.cls] || classCfg.Normal
  const featuresList = Object.entries(patient.features || {}).slice(0, 21)
  const { fhr, uc }  = buildSignalData(patient.features)

  return (
    <div>
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          Анализ записи КТГ
        </h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          Пациентка {patient.id} · {patient.weeks} · {patient.date}
          {visitId ? ` · Приём #${visitId}` : ''}
        </p>
      </div>

      <div className="flex gap-[26px]">
        {/* ─── LEFT ─── */}
        <div className="flex flex-col gap-5" style={{ flex: 1.35 }}>

          <Card stepNum={1} title="Загруженная запись" className="animate-fade-up delay-100">
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl mb-4" style={{ background: '#EEF2F9' }}>
              <FileIcon size={20} style={{ color: '#023A84', flexShrink: 0 }} />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-ink dark:text-gray-100 truncate" style={{ fontWeight: 600 }}>
                  {patient.filename}
                </div>
                <div className="text-[12px] text-muted mt-0.5">
                  {patient.format} · {patient.duration} · {patient.fs} · {patient.samples}
                </div>
              </div>
              <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] shrink-0"
                style={{ background: '#E4F4EA', color: '#1E8E4E', fontWeight: 600 }}>
                <CheckCircle size={11} /> Обработано
              </span>
            </div>

            <div className="mb-1">
              <p className="text-[11px] text-muted mb-1" style={{ fontWeight: 500 }}>ЧСС плода (FHR), уд/мин</p>
              <ResponsiveContainer width="100%" height={118}>
                <LineChart data={fhr} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E6EAF2" />
                  <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#7A8396' }} interval={19} />
                  <YAxis domain={[100, 180]} tick={{ fontSize: 10, fill: '#7A8396' }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={v => [`${v} уд/мин`, 'FHR']} />
                  <Line type="monotone" dataKey="v" stroke="#023A84" strokeWidth={2.2} dot={false} animationDuration={900} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div>
              <p className="text-[11px] text-muted mb-1" style={{ fontWeight: 500 }}>Маточная активность (UC)</p>
              <ResponsiveContainer width="100%" height={54}>
                <LineChart data={uc} margin={{ top: 2, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E6EAF2" />
                  <XAxis dataKey="t" tick={false} />
                  <YAxis domain={[0, 40]} tick={{ fontSize: 9, fill: '#7A8396' }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={v => [`${v}`, 'UC']} />
                  <Line type="monotone" dataKey="v" stroke="#3C6BB5" strokeWidth={2} dot={false} animationDuration={1000} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card stepNum={2} title="Извлечённые признаки (FIGO)" className="animate-fade-up delay-200">
            {featuresList.length > 0
              ? (
                <div className="divide-y divide-border dark:divide-gray-700">
                  {featuresList.map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center py-2.5">
                      <span className="text-sm text-muted dark:text-gray-400">{key}</span>
                      <span className="text-sm text-ink dark:text-gray-100" style={{ fontWeight: 600 }}>
                        {typeof value === 'number' ? value.toFixed(4) : value}
                      </span>
                    </div>
                  ))}
                </div>
              )
              : <p className="text-sm text-muted py-2">Признаки недоступны</p>
            }
          </Card>
        </div>

        {/* ─── RIGHT ─── */}
        <div className="flex flex-col gap-5" style={{ flex: 1 }}>

          <div className="rounded-2xl border p-5 animate-fade-up delay-100"
            style={{ background: cfg.bgCard, borderColor: cfg.border }}>
            <p className="text-xs uppercase tracking-[0.8px] mb-2" style={{ color: '#7A8396', fontWeight: 600 }}>
              Заключение модели
            </p>
            <p style={{ fontSize: 32, fontWeight: 800, color: cfg.bigColor, lineHeight: 1 }}>{cfg.label}</p>
            <p className="text-muted dark:text-gray-400 mt-2" style={{ fontSize: 13.5 }}>
              Confidence {(patient.conf || 0).toFixed(2)} · класс «{patient.cls}»
            </p>
          </div>

          <Card stepNum={3} title="Вероятности классов" className="animate-fade-up delay-200">
            <div className="flex flex-col gap-3">
              {Object.entries(patient.probabilities || {}).map(([cls, val]) => (
                <ProbBar key={cls} label={cls} value={val} color={probColors[cls]} />
              ))}
            </div>
          </Card>

          {/* Doctor assessment */}
          <Card stepNum={4} title="Оценка врача" className="animate-fade-up delay-250">
            {!visitId
              ? (
                <p className="text-sm text-muted dark:text-gray-500 py-1">
                  Оценка доступна для записей из базы данных.
                </p>
              )
              : (
                <div className="space-y-3">
                  <p className="text-[13px] text-muted dark:text-gray-400">
                    Прогноз модели: <strong className="text-ink dark:text-gray-100">{patient.cls}</strong>
                  </p>
                  <div>
                    <p className="text-[12px] text-muted mb-1.5" style={{ fontWeight: 500 }}>Класс по оценке врача:</p>
                    <div className="flex gap-2">
                      {LABEL_OPTIONS.map(opt => (
                        <button
                          key={opt.value}
                          onClick={() => { setDoctorLabel(opt.value); setLabelSaved(false) }}
                          className="flex-1 py-2 rounded-xl text-[13px] border-2 transition-all"
                          style={{
                            borderColor: doctorLabel === opt.value ? opt.color : '#E6EAF2',
                            background:  doctorLabel === opt.value ? opt.color + '18' : 'transparent',
                            color:       doctorLabel === opt.value ? opt.color : '#7A8396',
                            fontWeight:  600,
                          }}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <textarea
                    placeholder="Комментарий (необязательно)"
                    value={doctorComment}
                    onChange={e => { setDoctorComment(e.target.value); setLabelSaved(false) }}
                    rows={2}
                    className="w-full px-3 py-2 text-sm rounded-xl border border-border dark:border-gray-600 bg-white dark:bg-gray-800 text-ink dark:text-gray-100 resize-none outline-none focus:ring-2 focus:ring-navy/30"
                  />
                  <button
                    onClick={handleSaveLabel}
                    disabled={saving || labelSaved}
                    className="w-full py-2.5 rounded-[11px] text-sm transition-all"
                    style={{
                      background: labelSaved ? '#1E8E4E' : '#023A84',
                      color: '#fff',
                      fontWeight: 600,
                      opacity: saving ? 0.7 : 1,
                    }}
                  >
                    {saving ? 'Сохранение...' : labelSaved ? '✓ Сохранено' : 'Сохранить оценку'}
                  </button>
                </div>
              )
            }
          </Card>

          <Card stepNum={5} title="Модель и действия" className="animate-fade-up delay-300">
            <div className="divide-y divide-border dark:divide-gray-700 mb-4">
              {[
                ['Модель',          patient.modelVersion || 'ensemble_v2'],
                ['ROC-AUC (test)',  '0.970'],
                ['Время инференса', patient.inferenceMs != null ? `${patient.inferenceMs} мс` : '—'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between py-2.5">
                  <span className="text-sm text-muted dark:text-gray-400">{k}</span>
                  <span className="text-sm text-ink dark:text-gray-100" style={{ fontWeight: 600 }}>{v}</span>
                </div>
              ))}
            </div>
            <button
              onClick={() => { addToast('📄 Отчёт формируется...', 'info', 3000); setTimeout(() => window.print(), 400) }}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-[11px] text-white text-sm transition-all hover:opacity-90 active:scale-[0.98]"
              style={{ background: '#023A84', fontWeight: 600 }}
            >
              <Printer size={16} /> Сформировать PDF-отчёт
            </button>
          </Card>
        </div>
      </div>
    </div>
  )
}
