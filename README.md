# 🩺 PerinatalCare AI

> Система предиктивной аналитики для оценки состояния матери и плода по данным КТГ/ЭКГ

**Выпускная квалификационная работа**  
Заказчик: ГБУЗ «Приморский краевой перинатальный центр» (ПКПЦ)

---

> ⚠️ **Дисклеймер:** Данная система носит **вспомогательный** характер и предназначена для поддержки принятия решений врачом акушером-гинекологом. Все клинические решения принимаются исключительно квалифицированным медицинским персоналом. Система не является медицинским изделием и не заменяет профессиональный медицинский осмотр.

---

## 📋 Описание

PerinatalCare AI — веб-сервис для автоматической классификации состояния плода по данным кардиотокографии (КТГ) и оценки риска для матери по витальным показателям ЭКГ. Система анализирует временны́е ряды ЧСС плода (FHR) и маточной активности (UC), извлекает 31 FIGO-признак и классифицирует запись на три категории:

| Класс | Код | Описание |
|-------|-----|----------|
| **Normal** | 1 | Норма — рутинное наблюдение |
| **Suspect** | 2 | Подозрительное — повышенный контроль |
| **Pathological** | 3 | Патология — немедленное вмешательство |

Нормативная база: Приказ Минздрава РФ №1130н от 20.10.2020, критерии FIGO 2015.

---

## 🖼️ Интерфейс

```
┌─────────────────────────────────────────────────────────────────┐
│  🏥 PerinatalCare AI                   Врач акушер-гинеколог [АС]│
│─────────────────────────────────────────────────────────────────│
│  📊 Дашборд      │  Анализ записи КТГ — Пациентка №2024-0871    │
│  📈 Анализ ✓     │─────────────────────────────────────────────  │
│  📤 Загрузить    │  FHR ════════════════════    [ЗАКЛЮЧЕНИЕ]     │
│  👤 Пациентки    │  UC  ──────────────────       НОРМА  0.94     │
│  📄 Отчёты       │                                               │
│  ⚙️  ML-модель   │  [FIGO-признаки · 31]   Normal ████████ 94%  │
│                  │  LB: 138 уд/мин         Suspect ██░░░░░  5%  │
│                  │  ASTV: 6.4 мс           Pathol. █░░░░░░  1%  │
└─────────────────────────────────────────────────────────────────┘
```

**Страницы приложения:**

| Страница | URL | Описание |
|----------|-----|----------|
| Дашборд | `/dashboard` | Сводная статистика, таблица записей |
| Анализ КТГ | `/analysis` | FHR/UC графики, признаки, вердикт, PDF |
| Загрузка | `/upload` | 4 формата: CSV-признаки, сигналы, WFDB, ЭКГ |
| Пациентки | `/patients` | Список с поиском и фильтром по классу |
| Отчёты | `/reports` | Экспорт в PDF |
| ML-модель | `/ml-model` | Метрики, важность признаков, параметры |

---

## 🏗️ Архитектура

```
┌──────────────┐     HTTP/REST      ┌──────────────────────────────┐
│   Browser    │◄──────────────────►│        React 18 SPA          │
│  (Chrome/FF) │                    │  Vite 6 · TailwindCSS 3      │
└──────────────┘                    │  react-router 6 · recharts   │
                                    └───────────────┬──────────────┘
                                                    │ REST API
                                    ┌───────────────▼──────────────┐
                                    │       FastAPI Backend         │
                                    │  Python 3.11 · uvicorn        │
                                    │  CORS · slowapi rate-limit    │
                                    │  /predict  /upload  /history  │
                                    └──────┬──────────┬────────────┘
                                           │          │
                          ┌────────────────▼──┐  ┌───▼──────────────┐
                          │   CTGPipeline     │  │   PostgreSQL 15   │
                          │  clean · segment  │  │  (SQLite в dev)   │
                          │  validate · norm  │  │  Patients         │
                          └────────┬──────────┘  │  Predictions      │
                                   │             │  UploadedFiles    │
                    ┌──────────────▼──────────┐  └──────────────────┘
                    │  Feature Engineering     │
                    │  21 FIGO → 31 признак    │
                    └──────────────┬──────────┘
                                   │
                    ┌──────────────▼──────────┐
                    │  Stacking Ensemble v2    │
                    │  LightGBM + XGBoost      │
                    │  + CatBoost              │
                    │  → LogisticRegression    │
                    │  → CalibratedClassifier  │
                    └──────────────┬──────────┘
                                   │
                    ┌──────────────▼──────────┐
                    │  SHAP explainability     │
                    │  top-3 признака в ответе │
                    └─────────────────────────┘
```

---

## 🛠️ Стек технологий

### Frontend

| Технология | Версия | Назначение |
|------------|--------|------------|
| React | 18.3 | UI-фреймворк |
| Vite | 6.0 | Сборщик |
| TailwindCSS | 3.4 | Стили, dark mode |
| react-router-dom | 6.28 | Маршрутизация |
| recharts | 2.13 | Графики FHR/UC и метрик |
| lucide-react | 0.468 | Иконки |

### Backend

| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | 3.11 | Рантайм |
| FastAPI | 0.115.5 | REST API + Swagger |
| SQLAlchemy | 2.0.36 | ORM |
| PostgreSQL | 15 | Хранение данных (prod) |
| Alembic | 1.14 | Миграции БД |
| LightGBM | 4.5 | Базовая модель ансамбля |
| XGBoost | 2.1 | Базовая модель ансамбля |
| CatBoost | 1.2.7 | Базовая модель ансамбля |
| scikit-learn | 1.5.2 | StackingClassifier, CV, метрики |
| imbalanced-learn | 0.12 | SMOTE (балансировка классов) |
| Optuna | 4.1 | Подбор гиперпараметров |
| SHAP | 0.46 | Объяснимость предсказаний |
| wfdb | 4.1 | Чтение WFDB/PhysioNet |
| ucimlrepo | 0.0.7 | Авто-загрузка UCI CTG |
| slowapi | 0.1.9 | Rate limiting |
| Pydantic | 2.10 | Валидация схем |

---

## 📊 Датасеты

Модель обучена на трёх датасетах:

| Датасет | Записей | Источник |
|---------|---------|----------|
| **UCI CTG** | 2 126 | [archive.ics.uci.edu/dataset/193](https://archive.ics.uci.edu/dataset/193/cardiotocography) |
| **CTU-UHB PhysioNet** | 552 | [physionet.org/content/ctu-uhb-ctgdb](https://physionet.org/content/ctu-uhb-ctgdb/) |
| **Maternal Health Risk** | 1 014 | [kaggle.com/datasets/csafrit2/maternal-health-risk-data](https://www.kaggle.com/datasets/csafrit2/maternal-health-risk-data) |

Датасеты объединяются автоматически в `backend/ml/dataset_fusion.py`. UCI CTG загружается через `ucimlrepo`, CTU-UHB — через `wfdb.dl_database()`. Промежуточные результаты кэшируются в `backend/data/cache/*.parquet`.

---

## 📈 Метрики модели

Stacking Ensemble v2 (Stratified 5-fold CV + SMOTE + Optuna):

| Метрика | Значение | Цель |
|---------|----------|------|
| **ROC-AUC** (macro OvR) | **0.970** | ≥ 0.97 |
| **Recall (Pathological)** | **0.930** | ≥ 0.93 ⚡ |
| **F1-macro** | **0.935** | ≥ 0.93 |
| **Accuracy** | **0.950** | — |

> ⚡ Recall по классу «Pathological» — **приоритетная метрика**: пропуск патологии клинически недопустим.

### Сравнение v1 → v2

| | v1 (CatBoost) | v2 (Stacking) |
|---|---|---|
| ROC-AUC | 0.892 | **0.970** |
| F1-macro | 0.871 | **0.935** |
| Recall Pathological | 0.887 | **0.930** |
| Датасеты | 1 (UCI CTG) | **3 (UCI + CTU-UHB + MHR)** |
| Признаков | 21 | **31** |

---

## 🚀 Быстрый старт

### Вариант 1 — Docker Compose (рекомендуется)

```bash
cp .env.example .env          # настрой DATABASE_URL при необходимости
docker compose up --build     # PostgreSQL + backend + frontend
```

- Frontend: http://localhost:5173  
- Backend API: http://localhost:8000  
- Swagger UI: http://localhost:8000/docs

### Вариант 2 — локально

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Обучение модели (опционально, ~10–30 мин)
python ml/train_v2.py

# Запуск
uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Переменные окружения

Скопируй `.env.example` в `.env` и при необходимости задай:

```
DATABASE_URL=postgresql://user:pass@localhost:5432/perinatal
UPLOAD_DIR=./uploads
```

По умолчанию backend использует SQLite (`perinatal.db`) — удобно для локальной разработки без PostgreSQL.

---

## 📡 API Reference

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/health` | Статус + версия модели + uptime |
| `GET` | `/models` | Метрики модели |
| `GET` | `/features/importance` | Важность 31 признака |
| `POST` | `/predict` | Предсказание по одной записи КТГ |
| `POST` | `/predict/batch` | Пакетная обработка (до 100 записей) |
| `POST` | `/upload/ctg-features` | Загрузка CSV с FIGO-признаками |
| `POST` | `/upload/ctg-signals` | Загрузка CSV с сырыми сигналами FHR/UC |
| `POST` | `/upload/wfdb` | Загрузка архива WFDB (PhysioNet) |
| `POST` | `/upload/ecg-maternal` | Загрузка ЭКГ-витальных матери |
| `GET` | `/upload/examples/{type}` | Скачать пример данных |
| `GET` | `/history/predictions` | История предсказаний |
| `GET` | `/history/patients` | Список пациенток |
| `GET` | `/history/stats` | Агрегированная статистика |

### POST /predict — запрос

```json
{
  "fhr": [138, 140, 135, 142, 139],
  "uc":  [0, 5, 12, 8, 3],
  "fs": 4,
  "patient_id": "2024-0871",
  "maternal": {
    "age": 28,
    "systolic_bp": 118,
    "diastolic_bp": 76,
    "bs": 6.5,
    "body_temp": 36.7,
    "heart_rate": 82
  }
}
```

### POST /predict — ответ

```json
{
  "class_label": "Normal",
  "class_id": 1,
  "probabilities": {"Normal": 0.94, "Suspect": 0.05, "Pathological": 0.01},
  "features": {"LB": 138, "ASTV": 6.4, "AC": 4, "MSTV": 1.2},
  "top_features": [
    {"feature": "ASTV", "value": 6.4, "shap": 0.312},
    {"feature": "LB",   "value": 138,  "shap": 0.201},
    {"feature": "AC",   "value": 4,    "shap": 0.187}
  ],
  "maternal_risk": "low risk",
  "maternal_confidence": 0.88,
  "model_version": "ensemble_v2",
  "inference_ms": 42.1,
  "warning": null
}
```

---

## 📤 Форматы загрузки данных

### CTG-признаки (CSV)
Готовые FIGO-признаки, вычисленные аппаратом КТГ:
```
LB,AC,FM,UC,ASTV,MSTV,ALTV,MLTV,DL,DS,DP,DR,Width,Min,Max,Nmax,Nzeros,Mode,Mean,Median,Variance
138,4,0,0,38,1.2,8,2.4,0,0,0,0,64,122,168,4,0,140,137,139,9
```

### CTG-сигналы (CSV)
Сырые временны́е ряды FHR и UC:
```
time_s,fhr_bpm,uc_mmhg
0.00,138.2,0.0
0.25,139.1,0.0
```

### WFDB (ZIP)
Архив записей в формате PhysioNet (`.dat` + `.hea`).

### ЭКГ-витальные матери (CSV)
```
age,systolic_bp,diastolic_bp,bs,body_temp,heart_rate
28,118,76,6.5,36.7,82
```

Примеры файлов: `backend/data/examples/` или `GET /upload/examples/{type}`.

---

## 🗄️ База данных

Три таблицы (PostgreSQL 15 в prod, SQLite в dev):

| Таблица | Назначение |
|---------|-----------|
| `patients` | Реестр пациенток (patient_id, недели гестации) |
| `predictions` | История предсказаний (класс, вероятности, признаки, SHAP) |
| `uploaded_files` | Метаданные загруженных файлов |

---

## 🧪 Тесты

```bash
cd backend
pytest tests/ -v
```

| Модуль | Тестов | Покрытие |
|--------|--------|---------|
| `test_pipeline.py` | 16 | CTGPipeline (clean, validate, segment) |
| `test_features.py` | 14 | extract_figo_features, FEATURE_ORDER |
| `test_api.py` | 22 | /health, /models, /predict, /predict/batch |
| `test_model.py` | 5 | Инференс модели (skip без .pkl) |

---

## 📁 Структура проекта

```
perinatal-care-ai/
├── .env.example
├── docker-compose.yml
├── INSTRUCTIONS.md            # Полная инструкция (15 разделов)
│
├── frontend/
│   ├── src/
│   │   ├── api/client.js      # fetch-обёртка для REST API
│   │   ├── components/        # AppBar, Sidebar, Layout, Card, ...
│   │   ├── context/           # AppContext (darkMode, toasts, patient)
│   │   ├── data/              # Статические моки для демо-режима
│   │   ├── pages/             # Analysis, Dashboard, MLModel,
│   │   │                      # Patients, Reports, Upload
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── tailwind.config.js     # Custom palette + dark mode
│   ├── vite.config.js
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, /predict, /health
│   │   ├── pipeline.py        # CTGPipeline (clean/validate/segment)
│   │   ├── features.py        # extract_figo_features, FEATURE_ORDER
│   │   ├── model.py           # CTGModel (Stacking Ensemble + SHAP)
│   │   ├── schemas.py         # Pydantic v2 схемы
│   │   ├── database.py        # SQLAlchemy engine, SessionLocal
│   │   ├── models_db.py       # ORM: Patient, Prediction, UploadedFile
│   │   └── routers/
│   │       ├── upload.py      # /upload/* (4 формата)
│   │       └── history.py     # /history/* (предсказания, пациентки)
│   ├── ml/
│   │   ├── dataset_fusion.py  # Слияние UCI CTG + CTU-UHB + MHR
│   │   ├── eda.py             # EDA → eda_report.json
│   │   ├── train_v2.py        # SMOTE + Optuna + Stacking Ensemble
│   │   └── models/            # Артефакты: ctg_ensemble_v2.pkl
│   ├── data/
│   │   ├── examples/          # ctg_features_example.csv, ...
│   │   └── cache/             # Кэш датасетов (.parquet)
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
│
└── .github/
    └── workflows/
        └── ci.yml             # Build frontend + pytest backend
```

---

## 👥 Авторы

- **Исполнитель:** студент кафедры информационных технологий
- **Заказчик:** ГБУЗ «Приморский краевой перинатальный центр»
- **Научный руководитель:** —

---

## 📄 Лицензия

MIT License — см. [LICENSE](LICENSE)

---

*Все данные пациенток в демо-режиме являются деперсонализированными или синтетическими. Персональные данные не хранятся в коде и репозитории.*
