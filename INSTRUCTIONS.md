# PerinatalCare AI — Инструкция по эксплуатации

> Версия 2.1 · ГБУЗ «Приморский краевой перинатальный центр»

---

## 1. Описание системы

PerinatalCare AI — вспомогательная система для классификации записей кардиотокографии (КТГ) и оценки риска состояния матери. Система не является медицинским изделием и не принимает клинических решений — все решения принимает врач.

### Классы КТГ

| Класс | Код | Рекомендация |
|-------|-----|-------------|
| **Normal** | 1 | Рутинное наблюдение |
| **Suspect** | 2 | Повышенный контроль, повторная запись |
| **Pathological** | 3 | Немедленное вмешательство |

---

## 2. Архитектура

```
Browser → React SPA → FastAPI Backend → PostgreSQL
                            │
                    CTGPipeline (clean/validate)
                            │
                    Feature Engineering (21 → 31)
                            │
                    Stacking Ensemble
                    (LightGBM + XGBoost + CatBoost)
                            │
                    SHAP explanations
```

**Ключевые модули:**

| Модуль | Назначение |
|--------|-----------|
| `app/pipeline.py` | Предобработка сигнала FHR/UC |
| `app/features.py` | Извлечение 21 FIGO-признака |
| `app/model.py` | Инференс ансамбля + SHAP |
| `app/aggregate.py` | Агрегированный прогноз по динамике приёмов |
| `app/schedule_config.py` | Нормы частоты наблюдения по сроку гестации |
| `ml/train_v2.py` | Полный конвейер обучения |
| `ml/dataset_fusion.py` | Объединение трёх датасетов |

---

## 3. Требования

| Компонент | Требование |
|-----------|-----------|
| Python | 3.9–3.11 |
| Node.js | 18+ |
| RAM | 4 ГБ (8 ГБ рекомендуется для обучения) |
| Диск | 5 ГБ (с кэшем датасетов) |
| Docker | 24+ (для продакшна) |

---

## 4. Структура проекта

```
perinatal-care-ai/
├── .env.example
├── docker-compose.yml
├── INSTRUCTIONS.md
├── README.md
├── frontend/
│   ├── src/
│   │   ├── api/client.js
│   │   ├── components/
│   │   ├── context/AppContext.jsx
│   │   └── pages/
│   │       ├── Dashboard.jsx
│   │       ├── Analysis.jsx
│   │       ├── PatientCard.jsx
│   │       ├── Patients.jsx
│   │       ├── MLModel.jsx
│   │       ├── Upload.jsx
│   │       └── Reports.jsx
│   ├── .eslintrc.cjs
│   └── package.json
└── backend/
    ├── app/
    │   ├── main.py
    │   ├── pipeline.py
    │   ├── features.py
    │   ├── model.py
    │   ├── aggregate.py
    │   ├── schedule_config.py
    │   ├── schemas.py
    │   ├── database.py
    │   ├── models_db.py
    │   └── routers/
    │       ├── patients.py
    │       ├── dashboard.py
    │       ├── training.py
    │       ├── upload.py
    │       └── history.py
    ├── ml/
    │   ├── train_v2.py
    │   ├── dataset_fusion.py
    │   ├── eda.py
    │   └── models/
    ├── alembic/
    │   └── versions/001_add_visits.py
    ├── alembic.ini
    ├── data/examples/
    └── tests/
```

---

## 5. Локальная установка

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Применить миграции
alembic upgrade head

# Запуск
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Переменные окружения (.env)

```
DATABASE_URL=sqlite:///./perinatal.db
UPLOAD_DIR=./uploads
MAX_UPLOAD_MB=50
```

Для PostgreSQL: `DATABASE_URL=postgresql://user:pass@localhost:5432/perinatal`

---

## 6. Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

---

## 7. Миграции БД (Alembic)

```bash
cd backend

alembic upgrade head          # применить все
alembic downgrade -1          # откатить последнюю
alembic history               # история
alembic revision --autogenerate -m "описание"  # создать новую
```

### Схема таблиц

**patients**

| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| patient_id | String(64) unique | Идентификатор пациентки |
| weeks_gestation | Integer | Срок гестации |
| notes | Text | Примечания |
| created_at | DateTime | |

**visits** — основная таблица приёмов

| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| patient_id | FK → patients | |
| visit_date | DateTime | Дата приёма |
| gestational_week | Integer | Срок на момент приёма |
| screening_type | String | КТГ / витальные |
| input_format | String | api / csv_features / csv_signals / wfdb / ecg |
| predicted_class | String | Normal / Suspect / Pathological |
| class_id | Integer | 1 / 2 / 3 |
| probabilities | JSON | {"Normal": 0.94, ...} |
| features | JSON | Словарь FIGO-признаков |
| shap_top | JSON | Top-3 признака (SHAP) |
| maternal_risk | JSON | nullable |
| model_version | String | |
| inference_ms | Float | |
| warning | Text | nullable |
| doctor_label | String(1) | N / S / P / null |
| doctor_comment | Text | nullable |
| labeled_at | DateTime | nullable |
| created_at | DateTime | |

---

## 8. Обучение модели

```bash
cd backend
python ml/train_v2.py
```

Время: 10–30 мин. Артефакты: `ml/models/ctg_ensemble_v2.pkl`, `ml/models/metrics.json`.

### Целевые метрики

| Метрика | Цель |
|---------|------|
| ROC-AUC | ≥ 0.97 |
| Recall (Pathological) | ≥ 0.93 |
| F1-macro | ≥ 0.93 |
| Accuracy | ≥ 0.95 |

### Переобучение на данных врача

```bash
# 1. Экспортировать размеченные приёмы
curl http://localhost:8000/training-data/export -o data/labeled_visits.csv

# 2. Обучить (подмешает labeled_visits.csv автоматически)
python ml/train_v2.py

# 3. Перезагрузить модель без рестарта
curl -X POST http://localhost:8000/models/reload
```

Старая модель не перезаписывается.

---

## 9. Страницы интерфейса

### Дашборд (`/dashboard`)

Данные загружаются из `/dashboard/stats`. Четыре карточки: Пациентов / Норма / Подозрительные / Патология. Таблица последних 10 приёмов. Клик → экран анализа.

### Пациентки (`/patients`)

Список пациентов из `/patients` с поиском и фильтром по классу. Клик → карточка пациента.

### Карточка пациента (`/patients/:id`)

- Сводный прогноз по всем приёмам с трендом (Улучшение / Стабильно / Ухудшение)
- Предупреждение если превышен рекомендуемый интервал КТГ
- График динамики ASTV / LB / DL по датам приёмов
- Таблица всех приёмов (дата, срок, прогноз, оценка врача)

### Анализ КТГ (`/analysis`)

- Графики FHR и UC (воссоздаются из признаков при наличии LB/ASTV)
- Таблица 21 FIGO-признака
- Вердикт с вероятностями
- **Блок «Оценка врача»**: N/S/P + комментарий + кнопка сохранить (→ `PATCH /patients/visits/{id}/label`)
- PDF через `window.print()`

### Загрузка (`/upload`)

Четыре вкладки с формами загрузки файлов.

---

## 10. Форматы данных

### CTG-признаки (CSV)

Заголовок: `LB,AC,FM,UC,ASTV,MSTV,ALTV,MLTV,DL,DS,DP,DR,Width,Min,Max,Nmax,Nzeros,Mode,Mean,Median,Variance`

Пример нормальной записи: `138,4,0,0,38,1.2,8,2.4,0,0,0,0,64,122,168,4,0,140,137,139,9`

### CTG-сигналы (CSV)

```
fhr,uc
138.2,0.0
139.1,0.5
```

Минимум 1200 строк (5 мин при 4 Гц).

### WFDB (ZIP)

ZIP-архив с файлами `<name>.dat` и `<name>.hea` (формат PhysioNet).

### ЭКГ-витальные матери (CSV)

Заголовок: `Age,SystolicBP,DiastolicBP,BS,BodyTemp,HeartRate`

Пример: `28,118,76,6.5,36.7,82`

Скачать примеры: `GET /upload/examples/{ctg_features|ctg_signals|ecg_maternal}`

---

## 11. API Reference

```
GET  /health
GET  /models
GET  /features/importance
POST /predict
POST /predict/batch

GET  /dashboard/stats

GET    /patients
POST   /patients
GET    /patients/{id}
GET    /patients/{id}/visits
GET    /patients/{id}/aggregate-prediction
GET    /patients/visits/{id}
PATCH  /patients/visits/{id}/label    body: {doctor_label, doctor_comment}

POST /upload/ctg-features
POST /upload/ctg-signals
POST /upload/wfdb
POST /upload/ecg-maternal
GET  /upload/examples/{type}

GET  /training-data/export
POST /models/reload
```

---

## 12. Оценка врача

Поля в таблице `visits`:
- `doctor_label`: `N` (Normal) | `S` (Suspect) | `P` (Pathological) | `null`
- `doctor_comment`: текст, до 500 символов
- `labeled_at`: автоматически устанавливается при сохранении оценки

Сброс оценки: `PATCH /patients/visits/{id}/label` с `{"doctor_label": null}`.

---

## 13. Нормы частоты наблюдения

Настройка в `backend/app/schedule_config.py`:

| Срок | Интервал |
|------|---------|
| 12–27 нед. | 30 дней |
| 28–31 нед. | 14 дней |
| 32–36 нед. | 10 дней |
| 37–40 нед. | 7 дней |
| 41–45 нед. | 3 дня |

---

## 14. Тестирование

```bash
cd backend
pytest tests/ -v

# Линтеры
ruff check app/ tests/ --select E,F,W --ignore E501
```

```bash
cd frontend
npm run lint -- --ignore-pattern dist
```

| Файл | Тестов |
|------|--------|
| `test_pipeline.py` | 16 |
| `test_features.py` | 14 |
| `test_api.py` | 22 |
| `test_patients.py` | 29 |
| `test_model.py` | 6 (skip без модели) |

**75 passed, 6 skipped**

---

## 15. Датасеты

| Датасет | Записей | Загрузка |
|---------|---------|---------|
| UCI CTG | 2 126 | Автоматически через `ucimlrepo` |
| CTU-UHB PhysioNet | 552 | Автоматически через `wfdb.dl_database` |
| Maternal Health Risk | 1 014 | Вручную → `data/maternal_health_risk.csv` |

---

## 16. Часто задаваемые вопросы

**Q: Модель не загружена — прогноз работает?**  
A: Да, в режиме mock (возвращает Normal с предупреждением). Запусти `python ml/train_v2.py`.

**Q: Как сменить SQLite на PostgreSQL?**  
A: Задай `DATABASE_URL=postgresql://...` в `.env`, затем `alembic upgrade head`.

**Q: Как откатить версию модели?**  
A: Переименуй нужный `.pkl` в `ctg_ensemble_v2.pkl`, вызови `POST /models/reload`.

**Q: Что значит «тренд: Ухудшение»?**  
A: Алгоритм `aggregate.py` обнаружил снижение ASTV или рост DL между приёмами. Требует внимания врача.

**Q: Как экспортировать размеченные данные?**  
A: `GET /training-data/export` — CSV со всеми приёмами, где врач выставил `doctor_label`.

**Q: Система работает без интернета?**  
A: Да, после первоначальной загрузки датасетов (кэш в `data/cache/`).

---

*Система носит вспомогательный характер. Все клинические решения принимаются врачом.*
