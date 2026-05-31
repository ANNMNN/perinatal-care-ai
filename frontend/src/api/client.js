const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function req(method, path, body, isForm = false) {
  const opts = {
    method,
    headers: isForm ? {} : { 'Content-Type': 'application/json' },
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  }
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail ?? detail } catch { /* ignore */ }
    throw new Error(detail)
  }
  return res.json()
}

function qs(params) {
  const p = new URLSearchParams(params).toString()
  return p ? '?' + p : ''
}

export const api = {
  // System
  health:            ()       => req('GET', '/health'),
  models:            ()       => req('GET', '/models'),
  featureImportance: ()       => req('GET', '/features/importance'),

  // Prediction
  predict:      (data)        => req('POST', '/predict', data),
  predictBatch: (records)     => req('POST', '/predict/batch', { records }),

  // Upload
  uploadCTGFeatures: (fd)     => req('POST', '/upload/ctg-features',  fd, true),
  uploadCTGSignals:  (fd)     => req('POST', '/upload/ctg-signals',   fd, true),
  uploadWFDB:        (fd)     => req('POST', '/upload/wfdb',          fd, true),
  uploadECGMaternal: (fd)     => req('POST', '/upload/ecg-maternal',  fd, true),
  exampleUrl: (type)          => `${BASE}/upload/examples/${type}`,

  // Dashboard
  dashboardStats: ()          => req('GET', '/dashboard/stats'),

  // Patients
  patients: (params = {})     => req('GET', `/patients${qs(params)}`),
  patient:  (pid)             => req('GET', `/patients/${encodeURIComponent(pid)}`),
  createPatient: (body)       => req('POST', '/patients', body),
  patientVisits: (pid, p = {}) =>
    req('GET', `/patients/${encodeURIComponent(pid)}/visits${qs(p)}`),
  patientAggregate: (pid)     =>
    req('GET', `/patients/${encodeURIComponent(pid)}/aggregate-prediction`),

  // Visits
  visit:       (id)           => req('GET',   `/patients/visits/${id}`),
  labelVisit:  (id, body)     => req('PATCH', `/patients/visits/${id}/label`, body),

  // History (legacy)
  predictions:      (p = {})  => req('GET', `/history/predictions${qs(p)}`),
  prediction:       (id)      => req('GET', `/history/predictions/${id}`),
  deletePrediction: (id)      => req('DELETE', `/history/predictions/${id}`),
  dbStats:          ()        => req('GET', '/history/stats'),

  // Training
  exportLabeled:  ()          => `${BASE}/training-data/export`,
  reloadModel:    ()          => req('POST', '/models/reload'),
}

export default api
