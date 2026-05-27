import { CheckCircle, AlertTriangle, XCircle, Info, X } from 'lucide-react'
import { useApp } from '../context/AppContext'

const icons = {
  success: <CheckCircle size={18} className="text-green" />,
  warning: <AlertTriangle size={18} className="text-amber" />,
  error:   <XCircle size={18} className="text-red" />,
  info:    <Info size={18} className="text-navy-light" />,
}

const borders = {
  success: 'border-l-4 border-green',
  warning: 'border-l-4 border-amber',
  error:   'border-l-4 border-red',
  info:    'border-l-4 border-navy-light',
}

export default function ToastContainer() {
  const { toasts, removeToast } = useApp()

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 no-print">
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`flex items-center gap-3 bg-white dark:bg-gray-800 shadow-lg rounded-xl px-4 py-3 min-w-[280px] max-w-sm animate-fade-up ${borders[toast.type] || borders.info}`}
        >
          {icons[toast.type] || icons.info}
          <span className="flex-1 text-sm font-medium text-ink dark:text-gray-100">
            {toast.message}
          </span>
          <button
            onClick={() => removeToast(toast.id)}
            className="text-muted hover:text-ink transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
