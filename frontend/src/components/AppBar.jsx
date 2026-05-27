import { Activity, Moon, Sun } from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function AppBar() {
  const { darkMode, setDarkMode } = useApp()

  return (
    <header
      className="flex items-center justify-between px-6 shrink-0 no-print"
      style={{ height: 78, background: '#023A84' }}
    >
      {/* Left: logo + title */}
      <div className="flex items-center gap-3">
        <div
          className="flex items-center justify-center bg-white/10 shrink-0"
          style={{ width: 44, height: 44, borderRadius: 10 }}
        >
          <Activity size={22} color="#AFC4E6" strokeWidth={2.2} />
        </div>
        <div>
          <div style={{ fontSize: 21, fontWeight: 800, color: '#fff', lineHeight: 1.1 }}>
            PerinatalCare AI
          </div>
          <div style={{ fontSize: 13, fontWeight: 400, color: '#AFC4E6', lineHeight: 1.2 }}>
            Оценка состояния матери и плода · ГБУЗ «ПКПЦ»
          </div>
        </div>
      </div>

      {/* Right: dark-mode toggle + user */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setDarkMode(d => !d)}
          className="flex items-center justify-center w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
          title={darkMode ? 'Светлая тема' : 'Тёмная тема'}
        >
          {darkMode
            ? <Sun size={17} color="#AFC4E6" />
            : <Moon size={17} color="#AFC4E6" />}
        </button>

        <div className="flex items-center gap-2">
          <span style={{ fontSize: 13, fontWeight: 500, color: '#AFC4E6' }}>
            Врач акушер-гинеколог
          </span>
          <div
            className="flex items-center justify-center shrink-0"
            style={{
              width: 40, height: 40, borderRadius: '50%',
              background: '#3C6BB5',
              fontSize: 15, fontWeight: 700, color: '#fff',
            }}
          >
            АС
          </div>
        </div>
      </div>
    </header>
  )
}
