import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import Card from '../components/Card'
import SkeletonCard from '../components/SkeletonCard'
import api from '../api/client'

const METRIC_COLORS = {
  'ROC-AUC':               '#023A84',
  'Recall (Pathological)': '#D24B4B',
  'F1-macro':              '#1E8E4E',
  'Accuracy':              '#3C6BB5',
}

export default function MLModel() {
  const [modelInfo,  setModelInfo]  = useState(null)
  const [importance, setImportance] = useState([])
  const [loading,    setLoading]    = useState(true)

  useEffect(() => {
    Promise.all([api.models(), api.featureImportance()])
      .then(([models, fi]) => {
        setModelInfo(models[0] || null)
        const imp = fi.importance || {}
        const sorted = Object.entries(imp)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 7)
          .map(([name, value]) => ({ name, value: +(value * 100).toFixed(1) }))
        setImportance(sorted)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div>
        <div className="skeleton h-8 w-52 rounded mb-1" />
        <div className="skeleton h-4 w-64 rounded mb-6" />
        <div className="grid grid-cols-2 gap-5">
          <SkeletonCard height={80} rows={2} />
          <SkeletonCard height={80} rows={2} />
          <SkeletonCard height={200} rows={0} />
          <SkeletonCard height={200} rows={0} />
        </div>
      </div>
    )
  }

  const metrics = modelInfo
    ? [
        { metric: 'ROC-AUC',               value: modelInfo.roc_auc?.toFixed(3),               note: 'Macro OvR, тест' },
        { metric: 'Recall (Pathological)', value: modelInfo.recall_pathological?.toFixed(3), note: 'Приоритетная метрика' },
        { metric: 'F1-macro',              value: modelInfo.f1_macro?.toFixed(3),              note: 'Средн. по классам' },
        { metric: 'Accuracy',              value: modelInfo.accuracy?.toFixed(3),              note: 'Доля правильных' },
      ]
    : []

  return (
    <div>
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>ML-модель</h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          {modelInfo?.name || 'Stacking Ensemble'} · v{modelInfo?.version || '—'} · {modelInfo?.features_count || 31} признаков
        </p>
      </div>

      <div className="bg-[#EEF2F9] dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 px-5 py-4 mb-5 animate-fade-up delay-100">
        <p className="text-sm text-ink dark:text-gray-200 leading-relaxed">
          Ансамбль <strong>LightGBM + XGBoost + CatBoost</strong> с мета-классификатором Logistic Regression
          и калибровкой вероятностей (Platt scaling).
          Обучен на {modelInfo?.trained_on || '3 датасетах'}.
          Приоритет — <strong>Recall по классу патологии</strong>.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-5">
        {metrics.map(({ metric, value, note }, i) => (
          <div
            key={metric}
            className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 px-5 py-4 animate-fade-up"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="text-xs text-muted dark:text-gray-400 mb-1" style={{ fontWeight: 500 }}>{metric}</div>
            <div className="text-3xl" style={{ fontWeight: 800, color: METRIC_COLORS[metric] || '#023A84' }}>{value}</div>
            <div className="text-[11px] text-muted dark:text-gray-500 mt-1">{note}</div>
          </div>
        ))}
      </div>

      {importance.length > 0 && (
        <Card title="Важность признаков (топ-7)" className="animate-fade-up delay-300">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={importance} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E6EAF2" />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#7A8396' }} />
              <YAxis type="category" dataKey="name" width={220} tick={{ fontSize: 11, fill: '#7A8396' }} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={v => [`${v}%`, 'Важность']} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]} isAnimationActive animationDuration={900}>
                {importance.map((_, i) => (
                  <Cell key={i} fill={i === 0 ? '#D24B4B' : i === 1 ? '#023A84' : '#3C6BB5'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      <Card title="Датасеты обучения" className="mt-5 animate-fade-up delay-400">
        <div className="divide-y divide-border dark:divide-gray-700">
          {[
            ['UCI CTG',               '2 126', 'Кардиотокограммы, FIGO-признаки'],
            ['CTU-UHB PhysioNet',     '552',   'Интранатальные КТГ-записи WFDB'],
            ['Maternal Health Risk',  '1 014', 'Витальные показатели матери'],
          ].map(([name, n, desc]) => (
            <div key={name} className="flex items-start justify-between py-3">
              <div>
                <div className="text-sm text-ink dark:text-gray-200" style={{ fontWeight: 600 }}>{name}</div>
                <div className="text-[12px] text-muted dark:text-gray-500 mt-0.5">{desc}</div>
              </div>
              <span className="text-sm text-navy dark:text-blue-300 shrink-0 ml-4" style={{ fontWeight: 700 }}>
                {n} записей
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
