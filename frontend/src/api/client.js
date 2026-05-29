/**
 * Axios API-клиент для PerinatalCare AI backend.
 * Базовый URL берётся из VITE_API_URL (или localhost:8000)
 */
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
    try { detail = (await res.json()).detail ?? detail } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  // ── System ──────────────────────────────────────────────────────────
  health:            ()         => req('GET',  '/health'),
  models:            ()         => req('GET',  '/models'),
  featureImportance: ()         => req('GET',  '/features/importance'),

  // ── Prediction ───────────────────────────────────────────────────────
  predict:      (data)          => req('POST', '/predict', data),
  predictBatch: (records)       => req('POST', '/predict/batch', { records }),

  // ── Upload ───────────────────────────────────────────────────────────
  uploadCTGFeatures: (formData) => req('POST', '/upload/ctg-features',  formData, true),
  uploadCTGSignals:  (formData) => req('POST', '/upload/ctg-signals',   formData, true),
  uploadWFDB:        (formData) => req('POST', '/upload/wfdb',          formData, true),
  uploadECGMaternal: (formData) => req('POST', '/upload/ecg-maternal',  formData, true),

  exampleUrl: (type) => `${BASE}/upload/examples/${type}`,

  // ── History ──────────────────────────────────────────────────────────
  predictions: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return req('GET', `/history/predictions${qs ? '?' + qs : ''}`)
  },
  prediction:    (id)         => req('GET',    `/history/predictions/${id}`),
  deletePrediction: (id)      => req('DELETE', `/history/predictions/${id}`),
  patients:      (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return req('GET', `/history/patients${qs ? '?' + qs : ''}`)
  },
  patient:       (id)         => req('GET', `/history/patients/${id}`),
  dbStats:       ()           => req('GET', '/history/stats'),
}

export default api
