// FHR: базовая ~138, колебания ±10–15, акцелерации +20
export const fhrData = Array.from({ length: 120 }, (_, i) => ({
  t: i,
  v: parseFloat(
    (
      138 +
      10 * Math.sin(i / 8) +
      (i > 40 && i < 50 ? 20 : 0) +
      (i > 80 && i < 88 ? 18 : 0) +
      (Math.sin(i * 17.3) * 3)
    ).toFixed(1)
  ),
}))

// UC: 2–3 гауссовы волны
export const ucData = Array.from({ length: 120 }, (_, i) => ({
  t: i,
  v: parseFloat(
    Math.max(
      0,
      30 * Math.exp(-0.5 * ((i - 30) / 8) ** 2) +
        28 * Math.exp(-0.5 * ((i - 75) / 7) ** 2) +
        10 * Math.exp(-0.5 * ((i - 105) / 6) ** 2)
    ).toFixed(2)
  ),
}))

export const figoFeatures = [
  { key: 'Базальный ритм (LB)',                value: '138 уд/мин' },
  { key: 'Краткосрочная вариабельность (STV)',  value: '6.4 мс'    },
  { key: 'Акцелерации (AC)',                    value: '4 / 20 мин' },
  { key: 'Децелерации (DC)',                    value: '0'          },
  { key: 'Гистограмма: ширина / медиана',       value: '68 / 140'  },
]

export const currentPatient = {
  id:       '№2024-0871',
  weeks:    '32 нед.',
  date:     '27.05.2026',
  time:     '10:42',
  filename: 'ctg_2024-0871_record.dat',
  format:   'WFDB',
  duration: '20 мин',
  fs:       '4 Гц',
  samples:  '4 800 отсчётов',
  cls:      'Normal',
  conf:     0.94,
  probabilities: { Normal: 0.94, Suspect: 0.05, Pathological: 0.01 },
}
