import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload as UploadIcon, FileText, Activity, Heart,
  Download, CheckCircle, AlertTriangle, XCircle,
  ChevronRight, Info,
} from 'lucide-react'
import Card from '../components/Card'
import ClassBadge from '../components/ClassBadge'
import { useApp } from '../context/AppContext'
import api from '../api/client'

// ── Tabs config ──────────────────────────────────────────────────────
const TABS = [
  {
    id:       'ctg_features',
    label:    'КТГ-признаки (CSV)',
    icon:     FileText,
    desc:     'CSV с 21 FIGO-признаком — прямой предикт без извлечения',
    example:  'ctg_features',
    endpoint: 'uploadCTGFeatures',
    accept:   '.csv',
    fields:   'LB, AC, FM, UC, ASTV, MSTV, ALTV, MLTV, DL, DS, DP, DR, Width, Min, Max, Nmax, Nzeros, Mode, Mean, Median, Variance',
  },
  {
    id:       'ctg_signals',
    label:    'КТГ-сигналы (CSV)',
    icon:     Activity,
    desc:     'CSV с сырыми сигналами fhr и uc — система извлечёт FIGO-признаки',
    example:  'ctg_signals',
    endpoint: 'uploadCTGSignals',
    accept:   '.csv',
    fields:   'fhr, uc  (≥1200 строк при 4 Гц)',
    extra:    { fs: 4 },
  },
  {
    id:       'ecg_maternal',
    label:    'ЭКГ матери (CSV)',
    icon:     Heart,
    desc:     'CSV с витальными показателями: АД, ЧСС, сахар, температура',
    example:  'ecg_maternal',
    endpoint: 'uploadECGMaternal',
    accept:   '.csv',
    fields:   'Age, SystolicBP, DiastolicBP, BS, BodyTemp, HeartRate',
  },
  {
    id:       'wfdb',
    label:    'WFDB (PhysioNet)',
    icon:     Activity,
    desc:     'ZIP с .dat + .hea файлами PhysioNet CTU-UHB формата',
    example:  null,
    endpoint: 'uploadWFDB',
    accept:   '.zip',
    fields:   'ZIP: <name>.dat + <name>.hea',
  },
]

// ── Helper ───────────────────────────────────────────────────────────
function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const riskColors = {
  'low risk':  { bg: 'bg-green-bg',  text: 'text-green',      label: 'Низкий риск'  },
  'mid risk':  { bg: 'bg-amber-bg',  text: 'text-amber-dark', label: 'Средний риск' },
  'high risk': { bg: 'bg-red-bg',    text: 'text-red-dark',   label: 'Высокий риск' },
  unknown:     { bg: 'bg-gray-100',  text: 'text-muted',      label: 'Неизвестно'   },
}

function RiskBadge({ risk }) {
  const c = riskColors[risk] || riskColors.unknown
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-600 ${c.bg} ${c.text}`}
      style={{ fontWeight: 600 }}>
      {c.label}
    </span>
  )
}

// ── Drop zone ────────────────────────────────────────────────────────
function DropZone({ accept, onFile, disabled }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)

  const handleDrop = useCallback(e => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer?.files?.[0]
    if (f) onFile(f)
  }, [onFile])

  return (
    <div
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`relative border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer select-none
        ${dragging ? 'border-navy bg-[#EEF2F9]' : 'border-border dark:border-gray-600 hover:border-navy hover:bg-[#F8FAFF]'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <UploadIcon size={36} className="mx-auto mb-3 text-muted" strokeWidth={1.4} />
      <p className="text-sm font-600 text-ink dark:text-gray-200" style={{ fontWeight: 600 }}>
        Перетащите файл или нажмите для выбора
      </p>
      <p className="text-xs text-muted mt-1">{accept.toUpperCase()} · макс. 50 МБ</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={e => e.target.files?.[0] && onFile(e.target.files[0])}
        disabled={disabled}
      />
    </div>
  )
}

// ── Result card ──────────────────────────────────────────────────────
function CTGResultCard({ result, index }) {
  return (
    <div className="border border-border dark:border-gray-600 rounded-xl p-4 animate-fade-up"
      style={{ animationDelay: `${index * 60}ms` }}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <span className="text-xs text-muted">Строка {index + 1}</span>
        <ClassBadge cls={result.class_label} size="sm" />
      </div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm font-600 text-ink dark:text-gray-100" style={{ fontWeight: 600 }}>
          Уверенность:
        </span>
        <span className="text-sm text-navy dark:text-blue-300 font-600" style={{ fontWeight: 600 }}>
          {(Math.max(...Object.values(result.probabilities || {})) * 100).toFixed(1)}%
        </span>
      </div>
      {/* Prob bars */}
      <div className="space-y-1.5">
        {Object.entries(result.probabilities || {}).map(([cls, val]) => {
          const colors = { Normal: '#1E8E4E', Suspect: '#E0A526', Pathological: '#D24B4B' }
          const pct = Math.round(val * 100)
          return (
            <div key={cls} className="flex items-center gap-2">
              <span className="text-[11px] text-muted w-20 shrink-0">{cls}</span>
              <div className="flex-1 h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full rounded-full"
                  style={{ width: `${Math.max(pct, 3)}%`, background: colors[cls] }} />
              </div>
              <span className="text-[11px] font-600 w-8 text-right"
                style={{ color: colors[cls], fontWeight: 600 }}>{pct}%</span>
            </div>
          )
        })}
      </div>
      {result.warning && (
        <div className="flex items-center gap-1.5 mt-2 text-[11px] text-amber-dark dark:text-yellow-400">
          <AlertTriangle size={11} /> {result.warning}
        </div>
      )}
    </div>
  )
}

function MHRResultCard({ result, index }) {
  return (
    <div className="border border-border dark:border-gray-600 rounded-xl p-4 animate-fade-up"
      style={{ animationDelay: `${index * 60}ms` }}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <span className="text-xs text-muted">Строка {index + 1}</span>
        <RiskBadge risk={result.maternal_risk} />
      </div>
      <div className="text-sm text-muted">
        Уверенность: <strong className="text-ink dark:text-gray-100">
          {((result.maternal_confidence || 0) * 100).toFixed(1)}%
        </strong>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────
export default function Upload() {
  const { addToast, setActivePatient } = useApp()
  const navigate = useNavigate()

  const [activeTab, setActiveTab]   = useState(0)
  const [file, setFile]             = useState(null)
  const [patientId, setPatientId]   = useState('')
  const [loading, setLoading]       = useState(false)
  const [result, setResult]         = useState(null)
  const [error, setError]           = useState(null)

  const tab = TABS[activeTab]

  function handleFile(f) {
    setFile(f)
    setResult(null)
    setError(null)
  }

  async function handleUpload() {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)

    const form = new FormData()
    form.append('file', file)
    if (patientId) form.append('patient_id', patientId)
    if (tab.extra) {
      Object.entries(tab.extra).forEach(([k, v]) => form.append(k, String(v)))
    }

    try {
      const res = await api[tab.endpoint](form)
      setResult(res)
      addToast('✅ Файл обработан успешно!', 'success')

      // Если CTG features и одна строка → открываем страницу анализа
      if ((tab.id === 'ctg_features' || tab.id === 'ctg_signals') &&
          res.results?.length === 1) {
        const r = res.result || res.results[0]
        if (r && patientId) {
          setActivePatient({
            id: patientId || '—',
            weeks: '—', date: new Date().toLocaleDateString('ru'), time: '—',
            filename: file.name,
            format: tab.id === 'wfdb' ? 'WFDB' : 'CSV',
            duration: '—', fs: '4 Гц', samples: '—',
            cls:  r.class_label,
            conf: Math.max(...Object.values(r.probabilities || { Normal: 0.9 })),
            probabilities: r.probabilities,
          })
        }
      }
    } catch (err) {
      setError(err.message)
      addToast(`❌ ${err.message}`, 'error', 5000)
    } finally {
      setLoading(false)
    }
  }

  function openAnalysis() {
    const r = result?.result || result?.results?.[0]
    if (!r) return
    navigate('/analysis')
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          Загрузить данные
        </h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          КТГ-сигналы, FIGO-признаки, ЭКГ матери — форматы CSV и WFDB (PhysioNet)
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-5 flex-wrap animate-fade-up delay-100">
        {TABS.map((t, i) => {
          const Icon = t.icon
          return (
            <button
              key={t.id}
              onClick={() => { setActiveTab(i); setFile(null); setResult(null); setError(null) }}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-600 transition-all
                ${i === activeTab
                  ? 'bg-navy text-white shadow-sm'
                  : 'bg-white dark:bg-gray-800 text-muted dark:text-gray-400 border border-border dark:border-gray-600 hover:bg-card-bg dark:hover:bg-gray-700'}`}
              style={{ fontWeight: 600 }}
            >
              <Icon size={15} />
              {t.label}
            </button>
          )
        })}
      </div>

      <div className="flex gap-6">
        {/* Left — upload */}
        <div className="flex-[1.2] flex flex-col gap-4">
          <Card className="animate-fade-up delay-150">
            {/* Description */}
            <div className="flex items-start gap-3 mb-4 p-3 bg-[#EEF2F9] dark:bg-gray-700 rounded-xl">
              <Info size={16} className="text-navy dark:text-blue-300 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-600 text-ink dark:text-gray-100" style={{ fontWeight: 600 }}>
                  {tab.desc}
                </p>
                <p className="text-xs text-muted dark:text-gray-400 mt-1">
                  Обязательные колонки: <code className="bg-white dark:bg-gray-600 px-1 rounded">{tab.fields}</code>
                </p>
              </div>
            </div>

            {/* Download example */}
            {tab.example && (
              <a
                href={api.exampleUrl(tab.example)}
                download
                className="flex items-center gap-2 text-sm text-navy dark:text-blue-300 font-500 mb-4 hover:underline"
                style={{ fontWeight: 500 }}
              >
                <Download size={14} />
                Скачать пример данных ({tab.example}_example.csv)
              </a>
            )}

            {/* Drop zone */}
            <DropZone accept={tab.accept} onFile={handleFile} disabled={loading} />

            {/* File info */}
            {file && (
              <div className="flex items-center gap-3 mt-3 px-3 py-2.5 bg-[#EEF2F9] dark:bg-gray-700 rounded-xl">
                <FileText size={16} className="text-navy dark:text-blue-300 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-600 truncate text-ink dark:text-gray-100"
                    style={{ fontWeight: 600 }}>{file.name}</p>
                  <p className="text-xs text-muted">{fmtSize(file.size)}</p>
                </div>
                <button onClick={() => { setFile(null); setResult(null) }}
                  className="text-muted hover:text-red transition-colors">
                  <XCircle size={16} />
                </button>
              </div>
            )}

            {/* Patient ID */}
            <div className="mt-4">
              <label className="block text-xs font-600 text-muted dark:text-gray-400 mb-1"
                style={{ fontWeight: 600 }}>
                ID пациентки (опционально)
              </label>
              <input
                type="text"
                placeholder="Например: №2024-0871"
                value={patientId}
                onChange={e => setPatientId(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-xl border border-border dark:border-gray-600 bg-white dark:bg-gray-800 text-ink dark:text-gray-100 outline-none focus:ring-2 focus:ring-navy/30"
              />
            </div>

            {/* Upload button */}
            <button
              onClick={handleUpload}
              disabled={!file || loading}
              className="w-full mt-4 flex items-center justify-center gap-2 py-3 rounded-xl text-white text-sm font-600 transition-all hover:opacity-90 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: '#023A84', fontWeight: 600 }}
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Обрабатывается...
                </>
              ) : (
                <>
                  <UploadIcon size={16} />
                  Загрузить и получить оценку
                </>
              )}
            </button>

            {/* Error */}
            {error && (
              <div className="mt-3 flex items-center gap-2 p-3 bg-red-bg rounded-xl">
                <XCircle size={15} className="text-red-dark shrink-0" />
                <p className="text-sm text-red-dark">{error}</p>
              </div>
            )}
          </Card>
        </div>

        {/* Right — results */}
        <div className="flex-[1.0]">
          {!result && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-muted dark:text-gray-500 text-sm gap-3 min-h-[300px]">
              <UploadIcon size={40} strokeWidth={1.2} />
              <p>Загрузите файл — результаты появятся здесь</p>
            </div>
          )}

          {loading && (
            <div className="space-y-4">
              {[1,2,3].map(i => (
                <div key={i} className="skeleton h-32 rounded-2xl" />
              ))}
            </div>
          )}

          {result && !loading && (
            <div className="space-y-4 animate-fade-in">
              {/* Summary */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 px-5 py-4">
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle size={18} className="text-green" />
                  <span className="text-sm font-700 text-ink dark:text-gray-100" style={{ fontWeight: 700 }}>
                    Обработано успешно
                  </span>
                </div>
                <div className="flex gap-6 text-sm">
                  <div>
                    <span className="text-muted">Строк: </span>
                    <strong className="text-navy dark:text-blue-300">
                      {result.parsed_rows ?? result.n_samples ?? 1}
                    </strong>
                  </div>
                  {result.processing_ms && (
                    <div>
                      <span className="text-muted">Время: </span>
                      <strong className="text-ink dark:text-gray-200">
                        {result.processing_ms.toFixed(0)} мс
                      </strong>
                    </div>
                  )}
                </div>

                {/* Single result navigation */}
                {(result.result || (result.results?.length === 1)) && (
                  <button
                    onClick={openAnalysis}
                    className="mt-3 flex items-center gap-1.5 text-sm font-600 text-navy dark:text-blue-300 hover:underline"
                    style={{ fontWeight: 600 }}
                  >
                    Открыть страницу анализа <ChevronRight size={14} />
                  </button>
                )}
              </div>

              {/* CTG single result */}
              {result.result && (
                <CTGResultCard result={result.result} index={0} />
              )}

              {/* CTG multi results */}
              {result.results?.map((r, i) => (
                tab.id === 'ecg_maternal'
                  ? <MHRResultCard key={i} result={r} index={i} />
                  : <CTGResultCard key={i} result={r} index={i} />
              ))}

              {/* Warnings */}
              {result.warnings?.length > 0 && (
                <div className="bg-amber-bg rounded-xl p-3 border border-amber/30">
                  <p className="text-xs font-600 text-amber-dark mb-1" style={{ fontWeight: 600 }}>
                    ⚠️ Предупреждения ({result.warnings.length})
                  </p>
                  {result.warnings.slice(0, 3).map((w, i) => (
                    <p key={i} className="text-xs text-amber-dark">{w}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Format guide */}
      <Card title="Форматы данных и ожидаемые значения" className="mt-6 animate-fade-up delay-200">
        <div className="grid grid-cols-3 gap-4 text-sm">
          {[
            { label: 'Нормальные КТГ-признаки',        ex: 'LB ≈ 120–160, ASTV > 20%, AC > 0, DL = 0', color: 'text-green' },
            { label: 'Подозрительные КТГ-признаки',    ex: 'LB < 110 или > 160, ASTV < 20%, AC = 0, DL > 0', color: 'text-amber-dark' },
            { label: 'Патологические КТГ-признаки',    ex: 'LB < 100, ASTV < 10%, DS > 0, DP > 0, DL > 2', color: 'text-red-dark' },
            { label: 'Нормальные сигналы FHR (уд/мин)', ex: '110–160, волновые колебания ±10–15', color: 'text-green' },
            { label: 'Низкий материнский риск',        ex: 'АД < 120/80, сахар < 7.8, темп. < 37°C', color: 'text-green' },
            { label: 'Высокий материнский риск',       ex: 'АД ≥ 140/90, сахар ≥ 11, ЧСС > 90', color: 'text-red-dark' },
          ].map(({ label, ex, color }) => (
            <div key={label} className="bg-[#F4F6FB] dark:bg-gray-700 rounded-xl p-3">
              <p className={`text-xs font-600 mb-1 ${color}`} style={{ fontWeight: 600 }}>{label}</p>
              <p className="text-xs text-muted dark:text-gray-400">{ex}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
