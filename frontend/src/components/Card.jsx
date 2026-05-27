/**
 * Универсальная карточка с заголовком-кружком.
 * stepNum — цифра в navy-кружке (опционально)
 */
export default function Card({
  children,
  title,
  stepNum,
  className = '',
  style = {},
}) {
  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 p-5 ${className}`}
      style={style}
    >
      {(title || stepNum != null) && (
        <div className="flex items-center gap-2.5 mb-4">
          {stepNum != null && (
            <span
              className="flex items-center justify-center w-6 h-6 rounded-full text-white text-xs font-700 shrink-0"
              style={{ background: '#023A84', fontWeight: 700, fontSize: 12 }}
            >
              {stepNum}
            </span>
          )}
          {title && (
            <h3 className="text-sm font-600 text-ink dark:text-gray-100" style={{ fontWeight: 600 }}>
              {title}
            </h3>
          )}
        </div>
      )}
      {children}
    </div>
  )
}
