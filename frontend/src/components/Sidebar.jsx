import { NavLink } from 'react-router-dom'
import { LayoutGrid, Activity, Users, FileText, Settings, Upload } from 'lucide-react'

const nav = [
  { to: '/dashboard', icon: LayoutGrid, label: 'Дашборд'           },
  { to: '/analysis',  icon: Activity,   label: 'Анализ записи'     },
  { to: '/upload',    icon: Upload,     label: 'Загрузить данные'  },
  { to: '/patients',  icon: Users,      label: 'Пациентки'         },
  { to: '/reports',   icon: FileText,   label: 'Отчёты'            },
  { to: '/ml-model',  icon: Settings,   label: 'ML-модель'         },
]

export default function Sidebar() {
  return (
    <aside
      className="flex flex-col shrink-0 border-r border-border dark:border-gray-700 bg-white dark:bg-gray-900 no-print"
      style={{ width: 264 }}
    >
      <nav className="flex flex-col pt-5 gap-0.5 px-3">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 select-none
              ${isActive
                ? 'bg-card-bg dark:bg-gray-800 text-navy dark:text-navy-faint border-l-4 border-navy dark:border-navy-faint pl-[8px]'
                : 'text-[#5A6478] dark:text-gray-400 hover:bg-card-bg dark:hover:bg-gray-800 hover:text-ink dark:hover:text-gray-200'
              }`
            }
          >
            <Icon size={18} strokeWidth={1.8} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto px-4 py-4 border-t border-border dark:border-gray-700">
        <p className="text-[10.5px] text-muted dark:text-gray-500 leading-relaxed">
          Система носит вспомогательный характер. Все клинические решения принимаются врачом.
        </p>
      </div>
    </aside>
  )
}
