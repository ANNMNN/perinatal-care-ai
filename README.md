# 🩺 PerinatalCare AI

> Система предиктивной аналитики для оценки состояния матери и плода по данным КТГ/ЭКГ

**Выпускная квалификационная работа**  
Заказчик: ГБУЗ «Приморский краевой перинатальный центр» (ПКПЦ)

---

> ⚠️ **Дисклеймер:** Данная система носит **вспомогательный** характер и предназначена для поддержки принятия решений врачом акушером-гинекологом. Все клинические решения принимаются исключительно квалифицированным медицинским персоналом. Система не является медицинским изделием и не заменяет профессиональный медицинский осмотр.

---

## 📋 Описание

PerinatalCare AI — веб-сервис для автоматической классификации состояния плода по данным кардиотокографии (КТГ) и оценки риска для матери. Система анализирует временны́е ряды ЧСС плода (FHR) и маточной активности (UC), извлекает 31 FIGO-признак и классифицирует запись на три категории. Поддерживает ведение истории приёмов, оценку врача и агрегированный прогноз по динамике.

| Класс | Код | Описание |
|-------|-----|----------|
| **Normal** | 1 | Норма — рутинное наблюдение |
| **Suspect** | 2 | Подозрительное — повышенный контроль |
| **Pathological** | 3 | Патология — немедленное вмешательство |

Нормативная база: Приказ Минздрава РФ №1130н от 20.10.2020, критерии FIGO 2015.

---

## 🖼️ Интерфейс

| Страница | URL | Описание |
|----------|-----|----------|
| Дашборд | `/dashboard` | Сводная статистика из БД, таблица последних приёмов |
| Анализ КТГ | `/analysis` | FHR/UC графики, признаки, вердикт, оценка врача, PDF |
| Загрузка | `/upload` | 4 формата: CSV-признаки, сигналы, WFDB, ЭКГ |
| Пациентки | `/patients` | Список с поиском и фильтром по классу |
| Карточка пациента | `/patients/:id` | История приёмов, сводный прогноз, динамика признаков |
| Отчёты | `/reports` | Экспорт в PDF |
| ML-модель | `/ml-model` | Метрики из API, важность признаков, датасеты |

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
                                    │       FastAPI 0.115 Backend   │
                                    │  /predict  /patients          │
                                    │  /dashboard  /visits          │
                                    │  /upload  /training-data      │
                                    └──────┬──────────┬────────────┘
                                           │          │
                          ┌────────────────▼──┐  ┌───▼──────────────┐
                          │   CTGPipeline     │  │   PostgreSQL 15   │
                          │  clean · validate │  │  patients         │
                          │  segment · norm   │  │  visits           │
                          └────────┬──────────┘  │  uploaded_files   │
                                   │             │  (predictions*)   │
                    ┌──────────────▼──────────┐  └──────────────────┘
                    │  Feature Engineering     │
                    │  21 FIGO → 31 признаков  │
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
| Alembic | 1.14 | Миграции БД |
| PostgreSQL | 15 | Хранение данных (prod) |
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

| Датасет | Записей | Источник |
|---------|---------|----------|
| **UCI CTG** | 2 126 | [archive.ics.uci.edu/dataset/193](https://archive.ics.uci.edu/dataset/193/cardiotocography) |
| **CTU-UHB PhysioNet** | 552 | [physionet.org/content/ctu-uhb-ctgdb](https://physionet.org/content/ctu-uhb-ctgdb/) |
| **Maternal Health Risk** | 1 014 | [kaggle.com/datasets/csafrit2/maternal-health-risk-data](https://www.kaggle.com/datasets/csafrit2/maternal-health-risk-data) |

---

## 📈 Метрики модели

| Метрика | Значение | Цель |
|---------|----------|------|
| **ROC-AUC** (macro OvR) | **0.970** | ≥ 0.97 |
| **Recall (Pathological)** | **0.930** | ≥ 0.93 ⚡ |
| **F1-macro** | **0.935** | ≥ 0.93 |
| **Accuracy** | **0.950** | — |

> ⚡ Recall по классу «Pathological» — **приоритетная метрика**: пропуск патологии клинически недопустим.

---

## 🚀 Быстрый старт

### Вариант 1 — Docker Compose (рекомендуется)

```bash
cp .env.example .env
docker compose up --build
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

# Применить миграции БД
alembic upgrade head

# Опционально: обучить модель (~10–30 мин)
python ml/train_v2.py

uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Переменные окружения

```
DATABASE_URL=postgresql://user:pass@localhost:5432/perinatal
UPLOAD_DIR=./uploads
```

По умолчанию backend использует SQLite (`perinatal.db`) — удобно для локальной разработки.

---

## 📡 API Reference

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/health` | Статус + версия модели + uptime |
| `GET` | `/models` | Метрики модели |
| `GET` | `/features/importance` | Важность 31 признака |
| `POST` | `/predict` | Предсказание по одной записи КТГ |
| `POST` | `/predict/batch` | Пакетная обработка (до 100 записей) |
| `GET` | `/dashboard/stats` | Сводная статистика для дашборда |
| `GET` | `/patients` | Список пациентов (поиск, пагинация) |
| `POST` | `/patients` | Создать пациента |
| `GET` | `/patients/{id}` | Карточка пациента с приёмами |
| `GET` | `/patients/{id}/visits` | История приёмов |
| `GET` | `/patients/{id}/aggregate-prediction` | Сводный прогноз по динамике |
| `GET` | `/patients/visits/{id}` | Получить конкретный приём |
| `PATCH` | `/patients/visits/{id}/label` | Выставить оценку врача |
| `POST` | `/upload/ctg-features` | Загрузка CSV с FIGO-признаками |
| `POST` | `/upload/ctg-signals` | Загрузка CSV с сырыми сигналами FHR/UC |
| `POST` | `/upload/wfdb` | Загрузка архива WFDB (PhysioNet) |
| `POST` | `/upload/ecg-maternal` | Загрузка ЭКГ-витальных матери |
| `GET` | `/upload/examples/{type}` | Скачать пример данных |
| `GET` | `/training-data/export` | Экспорт размеченных врачом данных (CSV) |
| `POST` | `/models/reload` | Перезагрузить модель без рестарта |

### POST /predict — запрос

```json
{
  "fhr": [138, 140, 135, 142, 139],
  "uc":  [0, 5, 12, 8, 3],
  "fs": 4,
  "patient_id": "2024-0871",
  "gestational_week": 37,
  "maternal": {
    "age": 28, "systolic_bp": 118, "diastolic_bp": 76,
    "bs": 6.5, "body_temp": 36.7, "heart_rate": 82
  }
}
```

### POST /predict — ответ

```json
{
  "class_label": "Normal",
  "class_id": 1,
  "probabilities": {"Normal": 0.94, "Suspect": 0.05, "Pathological": 0.01},
  "features": {"LB": 138, "ASTV": 6.4, "AC": 4},
  "top_features": ["ASTV", "LB", "AC"],
  "visit_id": 42,
  "maternal_risk": "low risk",
  "maternal_confidence": 0.88,
  "model_version": "ensemble_v2",
  "inference_ms": 42.1,
  "warning": null
}
```

### PATCH /patients/visits/{id}/label — оценка врача

```json
{ "doctor_label": "N", "doctor_comment": "Норма, плановое наблюдение" }
```

`doctor_label`: `N` (Normal) · `S` (Suspect) · `P` (Pathological) · `null` (сбросить)

---

## 🗄️ База данных

| Таблица | Назначение |
|---------|-----------|
| `patients` | Реестр пациенток |
| `visits` | История приёмов (прогноз + оценка врача + SHAP) |
| `uploaded_files` | Метаданные загруженных файлов |
| `predictions` | Устаревшая таблица (backward compat) |

### Миграции (Alembic)

```bash
cd backend
alembic upgrade head       # применить все миграции
alembic downgrade -1       # откатить последнюю
alembic revision --autogenerate -m "описание"  # создать новую
```

---

## 🩺 Оценка врача и переобучение

Врач может выставить оценку класса (`N/S/P`) и комментарий для каждого приёма через экран «Анализ КТГ» или карточку пациента. Все приёмы с оценкой врача доступны через:

```bash
GET /training-data/export   # CSV: FIGO-признаки + doctor_class
```

Для переобучения с размеченными данными:

```bash
# 1. Экспортируй данные из БД
curl http://localhost:8000/training-data/export -o backend/data/labeled_visits.csv

# 2. Обучи модель (подмешает labeled_visits.csv автоматически)
cd backend && python ml/train_v2.py

# 3. Перезагрузи модель без перезапуска сервиса
curl -X POST http://localhost:8000/models/reload
```

Новая модель сохраняется рядом со старой — откат возможен вручную.

---

## 🧪 Тесты

```bash
cd backend && pytest tests/ -v
```

| Модуль | Тестов | Покрытие |
|--------|--------|---------|
| `test_pipeline.py` | 16 | CTGPipeline (clean, validate, segment) |
| `test_features.py` | 14 | extract_figo_features, FEATURE_ORDER |
| `test_api.py` | 22 | /health, /models, /predict, /predict/batch |
| `test_patients.py` | 29 | patients CRUD, visits, doctor label, aggregate, dashboard, export |
| `test_model.py` | 6 | Инференс модели (skip без .pkl) |

**Итого: 75 passed, 6 skipped (без обученной модели)**

---

## 📁 Структура проекта

```
perinatal-care-ai/
├── .env.example
├── docker-compose.yml
├── INSTRUCTIONS.md
│
├── frontend/
│   ├── src/
│   │   ├── api/client.js         # fetch-обёртка для всех REST-эндпоинтов
│   │   ├── components/           # AppBar, Sidebar, Layout, Card, ClassBadge, ...
│   │   ├── context/AppContext.jsx # darkMode, activePatient, toasts
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx     # данные из /dashboard/stats
│   │   │   ├── Analysis.jsx      # анализ приёма + оценка врача
│   │   │   ├── PatientCard.jsx   # карточка пациента + динамика
│   │   │   ├── Patients.jsx      # список из /patients
│   │   │   ├── MLModel.jsx       # метрики из /models + /features/importance
│   │   │   ├── Upload.jsx        # загрузка файлов
│   │   │   └── Reports.jsx
│   │   ├── App.jsx               # маршруты incl. /patients/:pid
│   │   └── main.jsx
│   ├── .eslintrc.cjs
│   ├── tailwind.config.js
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, /predict, регистрация роутеров
│   │   ├── pipeline.py           # CTGPipeline
│   │   ├── features.py           # extract_figo_features, FEATURE_ORDER
│   │   ├── model.py              # CTGModel (Stacking Ensemble + SHAP)
│   │   ├── aggregate.py          # heuristic aggregate_risk() по динамике
│   │   ├── schedule_config.py    # пороги частоты наблюдения по сроку гестации
│   │   ├── schemas.py            # Pydantic v2 схемы
│   │   ├── database.py           # SQLAlchemy engine, SessionLocal
│   │   ├── models_db.py          # ORM: Patient, Visit, Prediction, UploadedFile
│   │   └── routers/
│   │       ├── patients.py       # /patients CRUD + /visits + aggregate
│   │       ├── dashboard.py      # /dashboard/stats
│   │       ├── training.py       # /training-data/export + /models/reload
│   │       ├── upload.py         # /upload/* (4 формата)
│   │       └── history.py        # /history/* (legacy)
│   ├── ml/
│   │   ├── dataset_fusion.py     # UCI CTG + CTU-UHB + Maternal Health Risk
│   │   ├── eda.py                # EDA → eda_report.json
│   │   ├── train_v2.py           # SMOTE + Optuna + Stacking + doctor-data merge
│   │   └── models/               # ctg_ensemble_v2.pkl, maternal_risk_v2.pkl
│   ├── alembic/                  # миграции БД
│   │   └── versions/001_add_visits.py
│   ├── alembic.ini
│   ├── data/examples/            # примеры CSV для загрузки
│   ├── tests/
│   │   ├── test_api.py
│   │   ├── test_patients.py      # новые тесты для visits/label/aggregate
│   │   ├── test_features.py
│   │   ├── test_pipeline.py
│   │   └── test_model.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
│
└── .github/workflows/ci.yml
```

---

## 👥 Авторы

- **Исполнитель:** студент кафедры информационных технологий
- **Заказчик:** ГБУЗ «Приморский краевой перинатальный центр»

---

## 📄 Лицензия

MIT License — см. [LICENSE](LICENSE)

---

*Все данные пациенток в демо-режиме являются деперсонализированными или синтетическими. Персональные данные не хранятся в коде и репозитории.*
