import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { AppProvider, useApp } from './context/AppContext'
import Layout from './components/Layout'

import Analysis    from './pages/Analysis'
import Dashboard   from './pages/Dashboard'
import MLModel     from './pages/MLModel'
import PatientCard from './pages/PatientCard'
import Patients    from './pages/Patients'
import Reports     from './pages/Reports'
import Upload      from './pages/Upload'

const PAGE_NAMES = {
  '/analysis':  'Анализ записи КТГ',
  '/dashboard': 'Дашборд наблюдений',
  '/ml-model':  'ML-модель',
  '/patients':  'Пациентки',
  '/reports':   'Отчёты',
  '/upload':    'Загрузить данные',
}

function RouterToast() {
  const { addToast } = useApp()
  const location = useLocation()

  useEffect(() => {
    const name = PAGE_NAMES[location.pathname]
    if (name) addToast(`Открыт раздел: ${name}`, 'info', 2000)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])

  return null
}

function AppInner() {
  return (
    <Layout>
      <RouterToast />
      <Routes>
        <Route path="/"               element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard"      element={<Dashboard />}   />
        <Route path="/analysis"       element={<Analysis />}    />
        <Route path="/upload"         element={<Upload />}      />
        <Route path="/ml-model"       element={<MLModel />}     />
        <Route path="/patients"       element={<Patients />}    />
        <Route path="/patients/:pid"  element={<PatientCard />} />
        <Route path="/reports"        element={<Reports />}     />
        <Route path="*"               element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  )
}

export default function App() {
  return (
    <AppProvider>
      <AppInner />
    </AppProvider>
  )
}
