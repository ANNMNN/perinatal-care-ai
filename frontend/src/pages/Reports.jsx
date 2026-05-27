import { FileText, Download } from 'lucide-react'
import { useApp } from '../context/AppContext'

const reportList = [
  { title: 'Дневной отчёт — 27.05.2026', records: 6, date: '27.05.2026 11:00' },
  { title: 'Дневной отчёт — 26.05.2026', records: 9, date: '26.05.2026 23:59' },
  { title: 'Дневной отчёт — 25.05.2026', records: 7, date: '25.05.2026 23:59' },
]

export default function Reports() {
  const { addToast } = useApp()

  return (
    <div>
      <div className="mb-6 animate-fade-in">
        <h1 className="text-ink dark:text-white" style={{ fontSize: 25, fontWeight: 800 }}>
          Отчёты
        </h1>
        <p className="text-muted dark:text-gray-400" style={{ fontSize: 14, fontWeight: 500, marginTop: 3 }}>
          Сводные отчёты по сменам
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {reportList.map((rep, i) => (
          <div
            key={rep.title}
            className="bg-white dark:bg-gray-800 rounded-2xl border border-border dark:border-gray-700 px-5 py-4 flex items-center gap-4 animate-fade-up"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-[#EEF2F9] dark:bg-gray-700 shrink-0">
              <FileText size={20} className="text-navy dark:text-blue-300" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-600 text-ink dark:text-gray-100" style={{ fontWeight: 600 }}>
                {rep.title}
              </div>
              <div className="text-xs text-muted dark:text-gray-500 mt-0.5">
                {rep.records} записей · сформирован {rep.date}
              </div>
            </div>
            <button
              onClick={() => {
                addToast(`📄 Отчёт «${rep.title}» формируется...`, 'info', 3000)
                setTimeout(() => window.print(), 400)
              }}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-600 text-navy dark:text-blue-300 border border-navy/30 dark:border-blue-500/30 hover:bg-[#EEF2F9] dark:hover:bg-gray-700 transition-colors"
              style={{ fontWeight: 600 }}
            >
              <Download size={14} />
              Скачать PDF
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
