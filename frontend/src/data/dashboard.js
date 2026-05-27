export const stats = [
  { value: 24, label: 'Под наблюдением', color: 'navy'  },
  { value: 18, label: 'Норма',           color: 'green' },
  { value: 5,  label: 'Подозрительные', color: 'amber' },
  { value: 1,  label: 'Патология',       color: 'red'   },
]

export const records = [
  { id: '№2024-0871', weeks: '32 нед.', time: '10:42', cls: 'Normal',       conf: 0.94 },
  { id: '№2024-0863', weeks: '38 нед.', time: '10:15', cls: 'Suspect',      conf: 0.71 },
  { id: '№2024-0840', weeks: '40 нед.', time: '09:58', cls: 'Pathological', conf: 0.89 },
  { id: '№2024-0855', weeks: '34 нед.', time: '09:30', cls: 'Normal',       conf: 0.96 },
  { id: '№2024-0829', weeks: '36 нед.', time: '09:12', cls: 'Normal',       conf: 0.92 },
  { id: '№2024-0817', weeks: '39 нед.', time: '08:47', cls: 'Suspect',      conf: 0.68 },
]

export const featureImportance = [
  { name: 'ASTV (краткоср. вариабельность)', value: 18.4 },
  { name: 'LB (базальный ритм)',             value: 15.2 },
  { name: 'MSTV (среднее STV)',              value: 12.8 },
  { name: 'AC (акцелерации)',                value: 11.3 },
  { name: 'DP (пролонг. децелерации)',       value: 9.7  },
  { name: 'Width (ширина гистограммы)',      value: 8.1  },
  { name: 'DL (поздние децелерации)',        value: 7.6  },
]

export const modelMetrics = [
  { metric: 'ROC-AUC',                value: '0.892', note: 'Цель ≥ 0.89' },
  { metric: 'Recall (Pathological)',  value: '0.887', note: '⚡ Приоритет ≥ 0.88' },
  { metric: 'F1-macro',               value: '0.871', note: 'Цель ≥ 0.85' },
  { metric: 'Accuracy',               value: '0.862', note: '—' },
]
