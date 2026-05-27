import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import Card from '../components/Card'
import SkeletonCard from '../components/SkeletonCard'
import { modelMetrics, featureImportance } from '../data/dashboard'

const metricColors = {
  'ROC-AUC':               '#023A84',
  'Recall (Pathological)': '#D24B4B',
  'F1-macro':              '#1E8E4E',
  'Accuracy':              '#3C6BB5',
}

export default function MLModel() {
  const [loading, setLoading] = useState(true)
  useEffect(() => { const t = setTimeout(() => setLoading(false), 600); return () => clearTimeout(t) }, [])

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

  return (
    <div>
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          ML-модель
        </h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          CatBoost · UCI Cardiotocography Dataset · 2126 записей · 21 FIGO-признак
        </p>
      </div>

      {/* Описание */}
      <div className="bg-[#EEF2F9] dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 px-5 py-4 mb-5 animate-fade-up delay-100">
        <p className="text-sm text-ink dark:text-gray-200 leading-relaxed">
          Модель <strong>CatBoost</strong> обучена на 21 FIGO-признаке.
          Приоритет — максимальный <strong>Recall по классу патологии</strong> (пропуск недопустим).
          Стратифицированная 5-fold кросс-валидация, компенсация дисбаланса классов через <code>class_weights</code>.
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 gap-4 mb-5">
        {modelMetrics.map(({ metric, value, note }, i) => (
          <div
            key={metric}
            className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 px-5 py-4 animate-fade-up"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="text-xs text-muted dark:text-gray-400 mb-1 font-500" style={{ fontWeight: 500 }}>
              {metric}
            </div>
            <div
              className="text-3xl font-800"
              style={{ fontWeight: 800, color: metricColors[metric] || '#023A84' }}
            >
              {value}
            </div>
            <div className="text-[11px] text-muted dark:text-gray-500 mt-1">{note}</div>
          </div>
        ))}
      </div>

      {/* Feature importance chart */}
      <Card title="Важность признаков (топ-7, Gain)" className="animate-fade-up delay-300">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            data={featureImportance}
            layout="vertical"
            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E6EAF2" />
            <XAxis type="number" tick={{ fontSize: 11, fill: '#7A8396' }} />
            <YAxis
              type="category"
              dataKey="name"
              width={220}
              tick={{ fontSize: 11, fill: '#7A8396' }}
            />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E6EAF2' }}
              formatter={(v) => [`${v}%`, 'Gain']}
            />
            <Bar dataKey="value" radius={[0, 6, 6, 0]} isAnimationActive animationDuration={900}>
              {featureImportance.map((_, i) => (
                <Cell
                  key={i}
                  fill={i === 0 ? '#D24B4B' : i === 1 ? '#023A84' : '#3C6BB5'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted dark:text-gray-500 mt-2">
          * Красным выделен признак с наибольшим вкладом в классификацию (ASTV — краткосрочная вариабельность ЧСС плода)
        </p>
      </Card>

      {/* Params */}
      <Card title="Параметры обучения" className="mt-5 animate-fade-up delay-400">
        <div className="grid grid-cols-3 gap-4">
          {[
            ['iterations',            '500'],
            ['learning_rate',         '0.03'],
            ['depth',                 '6'],
            ['early_stopping_rounds', '50'],
            ['eval_metric',           'TotalF1'],
            ['task_type',             'CPU'],
          ].map(([k, v]) => (
            <div key={k} className="bg-[#F4F6FB] dark:bg-gray-700 rounded-xl px-4 py-3">
              <div className="text-[11px] text-muted dark:text-gray-400 font-500" style={{ fontWeight: 500 }}>
                {k}
              </div>
              <div className="text-sm font-700 text-navy dark:text-blue-300 mt-0.5" style={{ fontWeight: 700 }}>
                {v}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
