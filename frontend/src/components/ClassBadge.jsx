/**
 * Цветной pill для класса Normal / Suspect / Pathological
 */
const cfg = {
  Normal:       { bg: 'bg-green-bg',  text: 'text-green',      label: 'Normal'       },
  Suspect:      { bg: 'bg-amber-bg',  text: 'text-amber-dark', label: 'Suspect'      },
  Pathological: { bg: 'bg-red-bg',    text: 'text-red-dark',   label: 'Pathological' },
}

export default function ClassBadge({ cls, size = 'md' }) {
  const c = cfg[cls] || cfg.Normal
  const px = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-3 py-1 text-xs'
  return (
    <span className={`inline-flex items-center rounded-full font-600 ${px} ${c.bg} ${c.text}`}
      style={{ fontWeight: 600 }}>
      {c.label}
    </span>
  )
}
