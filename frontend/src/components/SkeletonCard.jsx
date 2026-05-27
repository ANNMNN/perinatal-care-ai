/** Skeleton-заглушка для загрузки карточки */
export default function SkeletonCard({ rows = 4, height = 120 }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 p-5 space-y-3">
      <div className="skeleton h-4 w-32 rounded" />
      <div className="skeleton rounded" style={{ height }} />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-3 rounded" style={{ width: `${70 + (i % 3) * 10}%` }} />
      ))}
    </div>
  )
}
