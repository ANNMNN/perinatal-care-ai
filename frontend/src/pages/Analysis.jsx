import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { FileText as FileIcon, CheckCircle, Printer } from 'lucide-react'
import Card from '../components/Card'
import SkeletonCard from '../components/SkeletonCard'
import { useApp } from '../context/AppContext'
import { fhrData, ucData, figoFeatures, currentPatient } from '../data/patient'

/* ── helpers ──────────────────────────────────────────────────── */
const classCfg = {
  Normal:       { label: 'НОРМА',      bigColor: '#1E8E4E', bgCard: '#F3F8F4', border: '#CDE8D6' },
  Suspect:      { label: 'ПОДОЗР.',    bigColor: '#B9831A', bgCard: '#FBF6EC', border: '#F0D79A' },
  Pathological: { label: 'ПАТОЛОГИЯ',  bigColor: '#C0392B', bgCard: '#FBE9E9', border: '#F0BABA' },
}

const probColors = { Normal: '#1E8E4E', Suspect: '#E0A526', Pathological: '#D24B4B' }

function ProbBar({ label, value, color }) {
  const pct = Math.round(value * 100)
  const visual = Math.max(pct, 4) // минимальная видимость
  return (
    <div className="flex items-center gap-3">
      <span className="text-[13px] text-muted dark:text-gray-400 w-28 shrink-0">{label}</span>
      <div className="flex-1 h-2.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${visual}%`, background: color }}
        />
      </div>
      <span className="text-[13px] font-600 w-9 text-right" style={{ color, fontWeight: 600 }}>
        {pct}%
      </span>
    </div>
  )
}

/* ── Component ────────────────────────────────────────────────── */
export default function Analysis() {
  const { addToast, activePatient } = useApp()
  const [loading, setLoading] = useState(true)
  const patient = activePatient || currentPatient

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 700)
    return () => clearTimeout(t)
  }, [patient?.id])

  const cfg = classCfg[patient.cls] || classCfg.Normal

  function handlePrint() {
    addToast('📄 Отчёт формируется...', 'info', 3000)
    setTimeout(() => window.print(), 400)
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

  return (
    <div>
      {/* Header */}
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          Анализ записи КТГ
        </h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          Пациентка {patient.id} · {patient.weeks} · запись от {patient.date}, {patient.time}
        </p>
      </div>

      <div className="flex gap-[26px]">
        {/* ─── LEFT COLUMN ─── */}
        <div className="flex flex-col gap-5" style={{ flex: 1.35 }}>

          {/* Card 1 — Загруженная запись */}
          <Card stepNum={1} title="Загруженная запись" className="animate-fade-up delay-100">
            {/* File row */}
            <div
              className="flex items-center gap-3 px-4 py-3 rounded-xl mb-4"
              style={{ background: '#EEF2F9' }}
            >
              <FileIcon size={20} style={{ color: '#023A84', flexShrink: 0 }} />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-600 text-ink dark:text-gray-100 truncate" style={{ fontWeight: 600 }}>
                  {patient.filename}
                </div>
                <div className="text-[12px] text-muted mt-0.5">
                  {patient.format} · {patient.duration} · {patient.fs} · {patient.samples}
                </div>
              </div>
              <span
                className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-600 shrink-0"
                style={{ background: '#E4F4EA', color: '#1E8E4E', fontWeight: 600 }}
              >
                <CheckCircle size={11} /> Обработано
              </span>
            </div>

            {/* FHR chart */}
            <div className="mb-1">
              <p className="text-[11px] text-muted mb-1 font-500" style={{ fontWeight: 500 }}>
                ЧСС плода (FHR), уд/мин
              </p>
              <ResponsiveContainer width="100%" height={118}>
                <LineChart data={fhrData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E6EAF2" />
                  <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#7A8396' }} interval={19} />
                  <YAxis domain={[100, 180]} tick={{ fontSize: 10, fill: '#7A8396' }} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E6EAF2' }}
                    formatter={(v) => [`${v} уд/мин`, 'FHR']}
                    labelFormatter={(t) => `t = ${t}s`}
                  />
                  <Line
                    type="monotone"
                    dataKey="v"
                    stroke="#023A84"
                    strokeWidth={2.2}
                    dot={false}
                    isAnimationActive={true}
                    animationDuration={900}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* UC chart */}
            <div>
              <p className="text-[11px] text-muted mb-1 font-500" style={{ fontWeight: 500 }}>
                Маточная активность (UC)
              </p>
              <ResponsiveContainer width="100%" height={54}>
                <LineChart data={ucData} margin={{ top: 2, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E6EAF2" />
                  <XAxis dataKey="t" tick={false} />
                  <YAxis domain={[0, 40]} tick={{ fontSize: 9, fill: '#7A8396' }} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    formatter={(v) => [`${v}`, 'UC']}
                  />
                  <Line
                    type="monotone"
                    dataKey="v"
                    stroke="#3C6BB5"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={true}
                    animationDuration={1000}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Card 2 — FIGO-признаки */}
          <Card stepNum={2} title="Извлечённые признаки (FIGO)" className="animate-fade-up delay-200">
            <div className="divide-y divide-border dark:divide-gray-700">
              {figoFeatures.map(({ key, value }) => (
                <div key={key} className="flex justify-between items-center py-2.5">
                  <span className="text-sm text-muted dark:text-gray-400">{key}</span>
                  <span className="text-sm font-600 text-ink dark:text-gray-100" style={{ fontWeight: 600 }}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* ─── RIGHT COLUMN ─── */}
        <div className="flex flex-col gap-5" style={{ flex: 1 }}>

          {/* Verdict card */}
          <div
            className="rounded-2xl border p-5 animate-fade-up delay-100"
            style={{ background: cfg.bgCard, borderColor: cfg.border }}
          >
            <p
              className="text-xs uppercase tracking-[0.8px] mb-2"
              style={{ color: '#7A8396', fontWeight: 600 }}
            >
              Заключение модели
            </p>
            <p style={{ fontSize: 32, fontWeight: 800, color: cfg.bigColor, lineHeight: 1 }}>
              {cfg.label}
            </p>
            <p className="text-muted dark:text-gray-400 mt-2" style={{ fontSize: 13.5 }}>
              Confidence {patient.conf.toFixed(2)} · класс «{patient.cls}»
            </p>
          </div>

          {/* Card 3 — Вероятности */}
          <Card stepNum={3} title="Вероятности классов" className="animate-fade-up delay-200">
            <div className="flex flex-col gap-3">
              {Object.entries(patient.probabilities).map(([cls, val]) => (
                <ProbBar key={cls} label={cls} value={val} color={probColors[cls]} />
              ))}
            </div>
          </Card>

          {/* Card 4 — Модель и действия */}
          <Card stepNum={4} title="Модель и действия" className="animate-fade-up delay-300">
            <div className="divide-y divide-border dark:divide-gray-700 mb-4">
              {[
                ['Модель',             'CatBoost v1.3'],
                ['ROC-AUC (test)',      '0.892'],
                ['Время инференса',    '38 мс'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between py-2.5">
                  <span className="text-sm text-muted dark:text-gray-400">{k}</span>
                  <span className="text-sm font-600 text-ink dark:text-gray-100" style={{ fontWeight: 600 }}>{v}</span>
                </div>
              ))}
            </div>
            <button
              onClick={handlePrint}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-[11px] text-white text-sm font-600 transition-all hover:opacity-90 active:scale-[0.98]"
              style={{ background: '#023A84', fontWeight: 600 }}
            >
              <Printer size={16} />
              Сформировать PDF-отчёт
            </button>
          </Card>
        </div>
      </div>
    </div>
  )
}
