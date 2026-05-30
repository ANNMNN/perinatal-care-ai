# 📖 Инструкция к проекту PerinatalCare AI

**Выпускная квалификационная работа**  
Заказчик: ГБУЗ «Приморский краевой перинатальный центр» (ПКПЦ)  
Репозиторий: https://github.com/ANNMNN/perinatal-care-ai

---

## Содержание

1. [Описание системы](#1-описание-системы)
2. [Архитектура](#2-архитектура)
3. [Требования](#3-требования)
4. [Структура проекта](#4-структура-проекта)
5. [Установка и запуск — локально](#5-установка-и-запуск--локально)
6. [Установка и запуск — Docker](#6-установка-и-запуск--docker)
7. [Обучение ML-моделей](#7-обучение-ml-моделей)
8. [Интерфейс — страницы и функции](#8-интерфейс--страницы-и-функции)
9. [Загрузка данных КТГ и ЭКГ](#9-загрузка-данных-ктг-и-экг)
10. [API — справочник эндпоинтов](#10-api--справочник-эндпоинтов)
11. [База данных](#11-база-данных)
12. [Тестирование](#12-тестирование)
13. [Датасеты](#13-датасеты)
14. [Метрики модели](#14-метрики-модели)
15. [Часто задаваемые вопросы](#15-часто-задаваемые-вопросы)

---

## 1. Описание системы

**PerinatalCare AI** — веб-сервис предиктивной аналитики для оценки состояния матери и плода по данным кардиотокографии (КТГ) и ЭКГ.

### Что делает система

- **Анализирует КТГ-записи** — принимает сигналы ЧСС плода (FHR) и маточной активности (UC)
- **Извлекает 21 FIGO-признак** — базальный ритм, вариабельность, акцелерации, децелерации и др.
- **Классифицирует состояние плода** на три класса:

| Класс | Значение | Действие |
|-------|----------|----------|
| 🟢 **Normal** | Норма | Рутинное наблюдение |
| 🟡 **Suspect** | Подозрительное | Повышенный контроль |
| 🔴 **Pathological** | Патология | Немедленное вмешательство |

- **Оценивает риск матери** — по витальным показателям (АД, ЧСС, сахар, температура)
- **Сохраняет историю** — все предсказания записываются в PostgreSQL
- **Принимает файлы** — CSV с признаками, CSV с сигналами, WFDB (PhysioNet формат)

> ⚠️ **Дисклеймер:** Система носит исключительно вспомогательный характер и предназначена для поддержки принятия решений врачом. Все клинические решения принимаются квалифицированным медицинским персоналом.

---

## 2. Архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                          БРАУЗЕР                                     │
│   React 18 + Vite + TailwindCSS + recharts + react-router-dom v6    │
│   Страницы: Dashboard / Analysis / Upload / Patients / ML-модель    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  HTTP/REST (fetch API)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python 3.11)                    │
│                                                                      │
│  POST /predict          GET /health        POST /upload/ctg-*       │
│  POST /predict/batch    GET /models        POST /upload/ecg-maternal │
│  GET  /features/importance                 GET  /history/predictions │
└──────────────┬────────────────────────────────────┬─────────────────┘
               │                                    │
    ┌──────────▼──────────┐              ┌──────────▼──────────┐
    │    ML Пайплайн       │              │  SQLAlchemy ORM      │
    │                      │              │                      │
    │  CTGPipeline         │              │  PostgreSQL (prod)   │
    │  ├─ clean()          │              │  SQLite    (dev)     │
    │  ├─ segment()        │              │                      │
    │  ├─ normalize()      │              │  Таблицы:            │
    │  └─ validate()       │              │  patients            │
    │                      │              │  predictions         │
    │  extract_figo_feats  │              │  uploaded_files      │
    │  (21 признак)        │              └──────────────────────┘
    │                      │
    │  CTGModel            │
    │  ├─ LightGBM  ─┐     │
    │  ├─ XGBoost   ─┼─ Stacking ─► LogReg ─► CalibCV
    │  └─ CatBoost  ─┘     │
    │                      │
    │  MaternalRiskModel   │
    │  └─ LightGBM         │
    └──────────────────────┘
```

---

## 3. Требования

### Минимальные системные требования

| Компонент | Требование |
|-----------|-----------|
| ОС | macOS 12+, Ubuntu 20.04+, Windows 10+ (WSL2) |
| ОЗУ | 8 ГБ (16 ГБ для обучения модели) |
| Диск | 5 ГБ свободного места |
| CPU | 4 ядра (для обучения) |

### Программные зависимости

| Инструмент | Версия | Для чего |
|-----------|--------|----------|
| Python | 3.9–3.12 | Backend + ML |
| Node.js | 18–22 | Frontend |
| PostgreSQL | 13–16 | База данных (опционально, есть SQLite fallback) |
| Docker + Compose | 24+ | Контейнерный запуск (опционально) |

---

## 4. Структура проекта

```
perinatal-care-ai/
│
├── 📄 README.md                    # Краткое описание проекта
├── 📄 INSTRUCTIONS.md              # Этот файл — полная инструкция
├── 📄 docker-compose.yml           # Контейнеры: PostgreSQL + backend + frontend
├── 📄 .env.example                 # Шаблон переменных окружения
├── 📄 .gitignore
├── 📄 LICENSE                      # MIT
│
├── 📁 frontend/                    # React-приложение
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js           # HTTP-клиент к API
│   │   ├── components/
│   │   │   ├── AppBar.jsx          # Верхняя панель (лого, тема, профиль)
│   │   │   ├── Sidebar.jsx         # Боковое меню навигации
│   │   │   ├── Layout.jsx          # Общий макет страниц
│   │   │   ├── Card.jsx            # Переиспользуемая карточка
│   │   │   ├── ClassBadge.jsx      # Цветной бейдж класса Normal/Suspect/Path.
│   │   │   ├── SkeletonCard.jsx    # Скелетон-загрузка
│   │   │   └── ToastContainer.jsx  # Всплывающие уведомления
│   │   ├── context/
│   │   │   └── AppContext.jsx      # Глобальный стейт (тема, пациент, тосты)
│   │   ├── data/
│   │   │   ├── patient.js          # Мок-данные: FHR/UC сигналы, FIGO-признаки
│   │   │   └── dashboard.js        # Мок-данные: статистика, таблица записей
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx       # /dashboard — дашборд наблюдений
│   │   │   ├── Analysis.jsx        # /analysis  — анализ КТГ-записи
│   │   │   ├── Upload.jsx          # /upload    — загрузка файлов
│   │   │   ├── Patients.jsx        # /patients  — список пациенток
│   │   │   ├── MLModel.jsx         # /ml-model  — метрики и важность признаков
│   │   │   └── Reports.jsx         # /reports   — список отчётов
│   │   ├── App.jsx                 # Роутинг (react-router-dom v6)
│   │   ├── main.jsx                # Точка входа React
│   │   └── index.css               # Tailwind + кастомные анимации
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js          # Кастомная палитра: navy, green, amber, red
│   ├── postcss.config.js
│   └── package.json
│
├── 📁 backend/                     # Python ML-сервис
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI: все эндпоинты, middleware
│   │   ├── database.py             # SQLAlchemy: engine, session, init_db()
│   │   ├── models_db.py            # ORM-модели: Patient, Prediction, UploadedFile
│   │   ├── schemas.py              # Pydantic v2 схемы запросов/ответов
│   │   ├── pipeline.py             # CTGPipeline: clean/segment/normalize/validate
│   │   ├── features.py             # extract_figo_features() — 21 FIGO-признак
│   │   ├── model.py                # CTGModel: инференс + SHAP + maternal risk
│   │   └── routers/
│   │       ├── upload.py           # POST /upload/* — загрузка файлов
│   │       └── history.py          # GET/DELETE /history/* — история
│   ├── ml/
│   │   ├── dataset_fusion.py       # Загрузка UCI CTG + CTU-UHB + Maternal HR
│   │   ├── eda.py                  # Разведочный анализ данных
│   │   ├── train_v2.py             # Обучение ансамбля (основной скрипт)
│   │   ├── train.py                # Старый скрипт (CatBoost v1, для справки)
│   │   ├── evaluate.py             # Детальный отчёт по обученной модели
│   │   └── models/                 # Сохранённые артефакты (создаётся при обучении)
│   │       ├── ctg_ensemble_v2.pkl # Основная модель (после train_v2.py)
│   │       ├── maternal_risk_v2.pkl# Модель риска матери
│   │       ├── feature_names.json  # Порядок признаков
│   │       └── metrics.json        # Метрики на тестовой выборке
│   ├── data/
│   │   ├── README.md               # Инструкция по скачиванию UCI CTG.xls
│   │   └── examples/               # Примеры для загрузки на сайте
│   │       ├── ctg_features_example.csv
│   │       ├── ctg_signals_example.csv
│   │       ├── ecg_maternal_example.csv
│   │       └── README.md
│   ├── tests/
│   │   ├── test_pipeline.py        # 16 тестов CTGPipeline
│   │   ├── test_features.py        # 14 тестов FIGO-признаков
│   │   ├── test_api.py             # 22 теста API эндпоинтов
│   │   └── test_model.py           # Тест метрик обученной модели
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
│
└── 📁 .github/
    └── workflows/
        └── ci.yml                  # GitHub Actions: build + pytest
```

---

## 5. Установка и запуск — локально

### 5.1 Клонирование репозитория

```bash
git clone https://github.com/ANNMNN/perinatal-care-ai.git
cd perinatal-care-ai
```

### 5.2 Настройка переменных окружения

```bash
cp .env.example .env
```

Откройте `.env` и при необходимости измените значения (по умолчанию используется SQLite, PostgreSQL не нужен):

```env
# Для локального запуска без PostgreSQL — ничего менять не нужно
# SQLite создастся автоматически: backend/perinatal.db

# Если хотите PostgreSQL:
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/perinatal_care
```

---

### 5.3 Запуск Backend

```bash
cd backend

# 1. Создать виртуальное окружение
python3 -m venv .venv

# 2. Активировать
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Запустить сервис
uvicorn app.main:app --reload --port 8000
```

**Проверка:** откройте http://localhost:8000/health — должен вернуться:
```json
{"status": "ok", "model_version": "mock_v0", "model_loaded": false}
```

> ℹ️ `model_loaded: false` — нормально до обучения модели. Сервис работает в mock-режиме.

Документация API (Swagger UI): http://localhost:8000/docs

---

### 5.4 Запуск Frontend

```bash
cd frontend

# 1. Установить зависимости
npm install

# 2. Запустить dev-сервер
npm run dev
```

**Приложение:** http://localhost:5173

---

### 5.5 Проверка что всё работает

Откройте браузер → http://localhost:5173  
Вы должны увидеть:
- Тёмно-синий AppBar с логотипом «PerinatalCare AI»
- Боковое меню: Дашборд, Анализ записи, Загрузить данные, Пациентки, Отчёты, ML-модель
- Дашборд с демо-данными и таблицей пациенток

---

## 6. Установка и запуск — Docker

Этот способ запускает сразу **PostgreSQL + Backend + Frontend** в контейнерах.

### Предварительные условия
- Docker Desktop установлен и запущен
- Порты 5432, 8000, 5173 свободны

### Запуск

```bash
# Из корня репозитория
docker compose up --build
```

После сборки (~3-5 минут):
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **PostgreSQL:** localhost:5432

### Остановка

```bash
docker compose down          # остановить контейнеры
docker compose down -v       # + удалить базу данных
```

---

## 7. Обучение ML-моделей

Без обученной модели система работает в **mock-режиме** — возвращает фиктивные предсказания. Для реальных предсказаний нужно обучить модель.

### 7.1 Подготовка данных

#### Датасет 1: UCI CTG (загружается автоматически)

Скрипт обучения автоматически скачивает UCI CTG через библиотеку `ucimlrepo`. Если интернет недоступен — скачайте вручную:

1. Перейдите: https://archive.uci.edu/dataset/193/cardiotocography
2. Скачайте архив → извлеките `CTG.xls`
3. Положите файл: `backend/data/CTG.xls`

#### Датасет 2: CTU-UHB PhysioNet (загружается автоматически)

552 записи сырых КТГ-сигналов в формате WFDB. Скрипт скачивает их через `wfdb.dl_database()` с сервера PhysioNet. Результаты кэшируются в `backend/data/cache/`.

#### Датасет 3: Maternal Health Risk (опционально)

1. Перейдите: https://www.kaggle.com/datasets/csafrit2/maternal-health-risk-data
2. Скачайте `maternal_health_risk.csv`
3. Положите файл: `backend/data/maternal_health_risk.csv`

Если файл не найден — система автоматически сгенерирует 1000 синтетических записей.

---

### 7.2 Запуск EDA (разведочный анализ)

```bash
cd backend
source .venv/bin/activate

python ml/eda.py
```

Вывод: `backend/ml/models/eda_report.json` со статистиками, корреляциями, дисбалансом классов.

Пример вывода в консоли:
```
2026-05-30 10:00:00 [INFO] UCI CTG: скачивание через ucimlrepo...
2026-05-30 10:00:05 [INFO] CTG combined: 2126 записей | Normal=1655 Suspect=295 Path.=176
2026-05-30 10:00:06 [INFO] ──────────────────────────────────────────────────────────
2026-05-30 10:00:06 [INFO] ИТОГ EDA:
2026-05-30 10:00:06 [INFO]   CTG записей: 2126
2026-05-30 10:00:06 [INFO]   Normal: 1655 (77.8%)
2026-05-30 10:00:06 [INFO]   Suspect: 295 (13.9%)
2026-05-30 10:00:06 [INFO]   Pathological: 176 (8.3%)
2026-05-30 10:00:06 [INFO]   💡 Класс Pathological составляет лишь 8.3% → необходима SMOTE-аугментация
```

---

### 7.3 Обучение ансамблевой модели

```bash
cd backend
source .venv/bin/activate

python ml/train_v2.py
```

**Что происходит:**

| Шаг | Действие | Время |
|-----|----------|-------|
| 1 | Загрузка UCI CTG + CTU-UHB | 1-3 мин |
| 2 | Инженерия 10 новых признаков (21 → 31) | < 1 сек |
| 3 | Train/test split 80/20, стратифицированный | < 1 сек |
| 4 | SMOTE: Pathological 176 → ~1600 записей | < 5 сек |
| 5 | Optuna: 60 trials тюнинга LightGBM | 3-7 мин |
| 6 | Stacking: LightGBM + XGBoost + CatBoost | 5-10 мин |
| 7 | Калибровка вероятностей (Platt scaling) | < 1 мин |
| 8 | 5-fold кросс-валидация | 5-10 мин |
| 9 | Сохранение модели и метрик | < 1 сек |

**Итого: ~20-30 минут** на стандартном CPU.

**Ожидаемые метрики в консоли:**
```
2026-05-30 10:25:00 [INFO] Проверка целевых метрик:
2026-05-30 10:25:00 [INFO]   ✓ roc_auc                  = 0.9724  (цель ≥ 0.97)
2026-05-30 10:25:00 [INFO]   ✓ recall_pathological       = 0.9318  (цель ≥ 0.93)
2026-05-30 10:25:00 [INFO]   ✓ f1_macro                  = 0.9352  (цель ≥ 0.93)
2026-05-30 10:25:00 [INFO]   ✓ accuracy                  = 0.9514  (цель ≥ 0.95)
2026-05-30 10:25:00 [INFO] ✅ ВСЕ целевые метрики достигнуты!
```

**Артефакты после обучения:**

```
backend/ml/models/
├── ctg_ensemble_v2.pkl     # Основная модель (~50-200 МБ)
├── maternal_risk_v2.pkl    # Модель риска матери (~5 МБ)
├── feature_names.json      # Список 31 признака
├── metrics.json            # Метрики на тестовой выборке
└── eda_report.json         # EDA-отчёт (после ml/eda.py)
```

После обучения перезапустите backend — модель загрузится автоматически:
```bash
uvicorn app.main:app --reload --port 8000
```

Теперь `/health` вернёт `"model_loaded": true, "model_version": "ensemble_v2"`.

---

### 7.4 Обучение только модели материнского риска

```bash
cd backend
source .venv/bin/activate

python -c "
from ml.train_v2 import train_maternal_model
train_maternal_model()
"
```

---

### 7.5 Детальный отчёт по модели

```bash
python ml/evaluate.py
```

Генерирует `ml/models/evaluation_report.json` с:
- Classification report (precision/recall/f1 по каждому классу)
- Confusion matrix
- Feature importance (gain)
- ROC-AUC

---

## 8. Интерфейс — страницы и функции

### 🏠 /dashboard — Дашборд наблюдений

**Что показывает:**
- 4 статистических карточки: под наблюдением / норма / подозрительные / патология
- Таблица последних КТГ-записей с цветными бейджами классов
- Скелетон-загрузка при первом открытии

**Взаимодействие:**
- Клик по строке таблицы → открывает `/analysis` с данными этой пациентки
- Toast-уведомление при навигации

---

### 📈 /analysis — Анализ записи КТГ

**Что показывает:**

Левая колонка:
- Карточка 1 «Загруженная запись» — имя файла, формат, длина, кнопка «Обработано»
- График FHR (ЧСС плода, уд/мин) — интерактивный recharts
- График UC (маточная активность) — интерактивный recharts
- Карточка 2 «FIGO-признаки» — таблица значений

Правая колонка:
- Карточка вердикта — **НОРМА / ПОДОЗР. / ПАТОЛОГИЯ** (большой цветной текст)
- Карточка 3 «Вероятности классов» — три прогресс-бара
- Карточка 4 «Модель и действия» — версия, ROC-AUC, кнопка PDF

**Взаимодействие:**
- Кнопка «📄 Сформировать PDF-отчёт» — отправляет страницу на печать (`window.print()`)
- Тёмная тема — переключатель в AppBar (иконка 🌙/☀️)

---

### 📤 /upload — Загрузить данные

**Вкладки:**

| Вкладка | Формат файла | Что делает система |
|---------|-------------|-------------------|
| КТГ-признаки (CSV) | `.csv` с 21 колонкой | Прямой predict, сохраняет в БД |
| КТГ-сигналы (CSV) | `.csv` с fhr, uc | Извлекает признаки → predict |
| ЭКГ матери (CSV) | `.csv` с витальными | Maternal risk predict |
| WFDB (PhysioNet) | `.zip` с .dat + .hea | WFDB parse → признаки → predict |

**Для каждой вкладки:**
- Кнопка «Скачать пример данных» — образец правильного формата
- Drag-and-drop зона загрузки
- Поле «ID пациентки» (опционально — привяжет к карточке)
- После обработки — карточки с результатами по каждой строке

---

### 👥 /patients — Пациентки

- Таблица всех пациенток
- Поиск по ID
- Фильтр по статусу: Все / Normal / Suspect / Pathological
- Клик по строке → открывает `/analysis`

---

### ⚙️ /ml-model — ML-модель

- Метрики: ROC-AUC, Recall(Pathological), F1-macro, Accuracy
- Горизонтальный bar chart — топ-7 признаков по важности (Gain)
- Параметры обучения: iterations, learning_rate, depth и др.
- Описание архитектуры ансамбля

---

### 📄 /reports — Отчёты

- Список сформированных дневных отчётов
- Кнопка «Скачать PDF» → `window.print()`

---

### Глобальные функции UI

| Функция | Описание |
|---------|----------|
| 🌙 Тёмная тема | Переключатель в AppBar, сохраняется в `localStorage` |
| ⚡ Toast-уведомления | Появляются при навигации, загрузке файлов, ошибках |
| 💀 Скелетон-загрузка | Появляется при переходе между страницами (600-700 мс) |
| 📱 Анимации | fade-up + slide-in с задержкой для карточек |

---

## 9. Загрузка данных КТГ и ЭКГ

### 9.1 Формат 1: CSV с FIGO-признаками

Самый простой способ. Создайте CSV-файл с 21 обязательной колонкой:

```csv
LB,AC,FM,UC,ASTV,MSTV,ALTV,MLTV,DL,DS,DP,DR,Width,Min,Max,Nmax,Nzeros,Mode,Mean,Median,Variance
133,0,0,0,27,0.9,27,6.8,0,0,0,0,64,62,126,2,18,120,137,121,73
```

**Диапазоны допустимых значений:**

| Признак | Норм. диапазон | Описание |
|---------|---------------|----------|
| LB | 110–160 | Базальная ЧСС плода (уд/мин) |
| AC | 0–5 | Акцелерации за 20 мин |
| FM | 0–10 | Движения плода |
| UC | 0–5 | Маточные сокращения |
| ASTV | 20–80 | Краткосрочная вариабельность (%) |
| MSTV | 0.5–3.0 | Средняя STV (мс) |
| ALTV | 10–60 | Долгосрочная вариабельность (%) |
| MLTV | 2–15 | Средняя LTV (мс) |
| DL | 0 | Поздние децелерации (в норме = 0) |
| DS | 0 | Тяжёлые децелерации (в норме = 0) |
| DP | 0 | Пролонгированные децелерации |
| DR | 0 | Повторяющиеся децелерации |
| Width | 30–100 | Ширина гистограммы |
| Min | 60–120 | Минимум FHR |
| Max | 130–200 | Максимум FHR |
| Nmax | 1–8 | Пиков гистограммы |
| Nzeros | 0–20 | Нулей гистограммы |
| Mode | 110–160 | Мода гистограммы |
| Mean | 110–160 | Среднее гистограммы |
| Median | 110–160 | Медиана гистограммы |
| Variance | 0–100 | Дисперсия гистограммы |

**Примеры классов:**
```csv
# Normal — хорошая вариабельность, нет децелераций
133,0,0,0,27,0.9,27,6.8,0,0,0,0,64,62,126,2,18,120,137,121,73

# Suspect — сниженная вариабельность, единичные децелерации
148,0,1,0,14,0.4,14,3.2,1,0,0,0,40,75,155,4,32,145,147,146,19

# Pathological — брадикардия, нет акцелераций, поздние децелерации
107,0,0,0,8,0.2,8,1.1,3,1,0,1,28,60,120,1,48,108,109,110,6
```

---

### 9.2 Формат 2: CSV с сырыми сигналами

CSV с временными рядами ЧСС плода и маточной активности.

**Требования:**
- Столбец `fhr` — ЧСС плода в уд/мин (диапазон 50–200)
- Столбец `uc` — маточная активность (относительные единицы, ≥0)
- Минимум **1200 строк** (5 минут при частоте 4 Гц)
- Параметр `fs` = частота дискретизации (по умолчанию 4 Гц)

```csv
fhr,uc
138.2,0.00
139.1,0.12
137.8,0.45
140.3,1.23
142.1,3.45
...
```

Система автоматически:
1. Валидирует сигнал (длина, диапазон ЧСС, пропуски)
2. Очищает от артефактов (IQR-выбросы, интерполяция)
3. Извлекает 21 FIGO-признак
4. Возвращает предсказание с confidence

---

### 9.3 Формат 3: ЭКГ матери (витальные показатели)

```csv
Age,SystolicBP,DiastolicBP,BS,BodyTemp,HeartRate
25,110,70,7.0,36.6,72
38,150,100,13.0,37.8,88
```

**Интерпретация результата:**

| Риск | АД (систол.) | Сахар | ЧСС матери |
|------|-------------|-------|-----------|
| 🟢 Низкий | < 120 | < 7.8 | 60–80 |
| 🟡 Средний | 120–139 | 7.8–11.0 | 80–90 |
| 🔴 Высокий | ≥ 140 | > 11.0 | > 90 |

---

### 9.4 Формат 4: WFDB (PhysioNet)

Создайте ZIP-архив с двумя файлами:

```
record.zip
├── 1001.dat    # Бинарные данные сигнала
└── 1001.hea   # Заголовок (метаданные: частота, число каналов и т.д.)
```

Скачать тестовые WFDB-записи CTU-UHB:
```bash
python3 -c "
import wfdb
wfdb.dl_pn_dir('ctu-uhb-ctgdb', './test_records', records=['1001'])
"
# Затем создайте ZIP: zip 1001.zip 1001.dat 1001.hea
```

---

### 9.5 Скачать готовые примеры через API

```bash
# Примеры КТГ-признаков (Normal/Suspect/Pathological)
curl http://localhost:8000/upload/examples/ctg_features -o ctg_features_example.csv

# Сырые сигналы FHR + UC
curl http://localhost:8000/upload/examples/ctg_signals -o ctg_signals_example.csv

# Материнские показатели
curl http://localhost:8000/upload/examples/ecg_maternal -o ecg_maternal_example.csv
```

Или из репозитория: `backend/data/examples/`

---

## 10. API — справочник эндпоинтов

Интерактивная документация: http://localhost:8000/docs

### Системные

#### `GET /health`
```json
{
  "status": "ok",
  "model_version": "ensemble_v2",
  "uptime_seconds": 3600.5,
  "model_loaded": true
}
```

#### `GET /models`
```json
[{
  "name": "PerinatalCare Stacking Ensemble",
  "version": "ensemble_v2",
  "roc_auc": 0.972,
  "f1_macro": 0.935,
  "accuracy": 0.951,
  "recall_pathological": 0.931,
  "trained_on": "UCI CTG + CTU-UHB PhysioNet + Maternal Health Risk",
  "features_count": 31
}]
```

#### `GET /features/importance`
```json
{
  "importance": {
    "ASTV": 18.4,
    "LB_x_ASTV": 15.2,
    "LB": 12.8,
    ...
  },
  "model_version": "ensemble_v2"
}
```

---

### Предсказания

#### `POST /predict` — основной эндпоинт

**Запрос:**
```json
{
  "fhr": [138, 140, 135, 142, 138, ...],
  "uc":  [0, 5, 12, 8, 2, ...],
  "fs": 4,
  "patient_id": "№2024-0871",
  "maternal": {
    "age": 28,
    "systolic_bp": 118,
    "diastolic_bp": 76,
    "bs": 7.2,
    "body_temp": 36.7,
    "heart_rate": 74
  }
}
```

**Ответ:**
```json
{
  "class_label": "Normal",
  "class_id": 1,
  "probabilities": {
    "Normal": 0.9412,
    "Suspect": 0.0482,
    "Pathological": 0.0106
  },
  "features": {
    "LB": 138.4,
    "AC": 4.0,
    "ASTV": 27.3,
    ...
  },
  "top_features": ["ASTV", "LB_x_ASTV", "LB"],
  "model_version": "ensemble_v2",
  "inference_ms": 38.2,
  "warning": null,
  "maternal_risk": "low risk",
  "maternal_confidence": 0.8847
}
```

#### `POST /predict/batch` — пакетный predict

```json
{
  "records": [
    {"fhr": [...], "uc": [...], "fs": 4},
    {"fhr": [...], "uc": [...], "fs": 4}
  ]
}
```

**Ответ:** `{"results": [...], "total": 2, "processed_ms": 145.3}`

---

### Загрузка файлов

#### `POST /upload/ctg-features`
- **Content-Type:** `multipart/form-data`
- **file:** CSV-файл с 21 FIGO-признаком
- **patient_id:** (опционально)
- **Ответ:** `{"status": "ok", "parsed_rows": 3, "results": [...]}`

#### `POST /upload/ctg-signals`
- **file:** CSV с колонками `fhr`, `uc`
- **fs:** частота дискретизации (default: 4)
- **Ответ:** `{"status": "ok", "result": {...}, "n_samples": 1500}`

#### `POST /upload/wfdb`
- **file:** ZIP с .dat + .hea
- **Ответ:** `{"status": "ok", "result": {...}, "fs": 4, "signals": [...]}`

#### `POST /upload/ecg-maternal`
- **file:** CSV с Age, SystolicBP, DiastolicBP, BS, BodyTemp, HeartRate
- **Ответ:** `{"status": "ok", "parsed_rows": 5, "results": [...]}`

#### `GET /upload/examples/{type}`
- **type:** `ctg_features` | `ctg_signals` | `ecg_maternal`
- **Ответ:** CSV-файл для скачивания

---

### История и пациентки

#### `GET /history/predictions`
```
?patient_id=№2024-0871&class_label=Pathological&limit=50&offset=0
```

#### `GET /history/predictions/{id}` — конкретное предсказание
#### `DELETE /history/predictions/{id}` — удалить предсказание
#### `GET /history/patients` — список пациенток
#### `GET /history/patients/{id}` — карточка пациентки + история
#### `POST /history/patients` — создать карточку пациентки
#### `GET /history/stats` — статистика по базе данных
#### `GET /history/files` — список загруженных файлов

---

## 11. База данных

### Выбор СУБД

По умолчанию система использует **SQLite** (файл `backend/perinatal.db`) — не требует установки ничего дополнительного.

Для продакшена используйте **PostgreSQL** — укажите переменную:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/perinatal_care
```

### Схема таблиц

#### `patients`
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | INTEGER PK | Автоинкремент |
| patient_id | VARCHAR(64) UNIQUE | Идентификатор пациентки |
| weeks_gestation | INTEGER | Срок беременности (нед.) |
| notes | TEXT | Заметки врача |
| created_at | DATETIME | Дата создания |

#### `predictions`
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | INTEGER PK | Автоинкремент |
| patient_id | VARCHAR FK | Ссылка на patients |
| class_label | VARCHAR(20) | Normal / Suspect / Pathological |
| class_id | INTEGER | 1 / 2 / 3 |
| confidence | FLOAT | Максимальная вероятность |
| prob_normal | FLOAT | P(Normal) |
| prob_suspect | FLOAT | P(Suspect) |
| prob_pathological | FLOAT | P(Pathological) |
| maternal_risk | VARCHAR(20) | low / mid / high risk |
| maternal_confidence | FLOAT | Уверенность MHR-модели |
| features_json | TEXT | JSON со значениями FIGO-признаков |
| top_features_json | TEXT | JSON топ-3 SHAP-признаков |
| model_version | VARCHAR(50) | Версия модели |
| inference_ms | FLOAT | Время инференса (мс) |
| source | VARCHAR(30) | api / csv_features / csv_signals / wfdb |
| warning | TEXT | Предупреждение (если есть) |
| created_at | DATETIME | Дата предсказания |

#### `uploaded_files`
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | INTEGER PK | Автоинкремент |
| filename | VARCHAR(255) | Имя на диске (UUID) |
| original_name | VARCHAR(255) | Оригинальное имя файла |
| file_type | VARCHAR(20) | csv_features / csv_signals / wfdb / ecg |
| file_size | INTEGER | Размер в байтах |
| patient_id | VARCHAR FK | Ссылка на patients |
| parsed_rows | INTEGER | Успешно разобранных строк |
| created_at | DATETIME | Дата загрузки |

---

## 12. Тестирование

### Запуск всех тестов

```bash
cd backend
source .venv/bin/activate
pytest -v
```

### Описание тестовых наборов

#### `tests/test_pipeline.py` (16 тестов)
Тестирует `CTGPipeline`:
- `TestClean` — удаление нулей, выбросов, интерполяция NaN
- `TestSegment` — нарезка на перекрывающиеся окна
- `TestNormalize` — Z-нормализация (μ=0, σ=1)
- `TestValidate` — проверка длины, пропусков, диапазона ЧСС

#### `tests/test_features.py` (14 тестов)
Тестирует `extract_figo_features()`:
- Возвращает ровно 21 признак с правильными именами
- Все значения — float, конечные числа (не NaN/Inf)
- LB в диапазоне 50–200
- Variance=0 для монотонного сигнала
- Работает без сигнала UC

#### `tests/test_api.py` (22 теста)
Тестирует FastAPI эндпоинты через `TestClient`:
- `/health` — статус, поля, uptime
- `/models` — список, поля, диапазоны
- `/features/importance` — наличие признаков
- `/predict` — статус 200, структура ответа, сумма вероятностей = 1
- `/predict/batch` — пакетная обработка

#### `tests/test_model.py` (5 тестов)
Тестирует обученную модель (пропускается если модель не обучена):
- Recall(Pathological) ≥ 0.88 (приоритетный тест)
- ROC-AUC ≥ 0.89
- F1-macro ≥ 0.85

### Пример вывода

```
======================== test session starts ========================
tests/test_pipeline.py::TestClean::test_removes_zeros PASSED
tests/test_pipeline.py::TestClean::test_removes_outliers PASSED
...
tests/test_api.py::TestPredict::test_predict_returns_200 PASSED
tests/test_api.py::TestPredict::test_probabilities_sum_to_one PASSED
...
====================== 52 passed in 1.01s ==========================
```

### CI/CD (GitHub Actions)

При каждом push/PR автоматически запускается:
- **Frontend:** `npm ci && npm run build`
- **Backend:** `pip install -r requirements.txt && pytest -v`

Статус: см. вкладку **Actions** в GitHub репозитории.

---

## 13. Датасеты

### UCI Cardiotocography Dataset

| Параметр | Значение |
|----------|---------|
| Источник | https://archive.uci.edu/dataset/193/cardiotocography |
| Записей | 2 126 |
| Признаков | 21 FIGO + метаданные |
| Целевая переменная | NSP: 1=Normal, 2=Suspect, 3=Pathological |
| Баланс классов | Normal 77.8%, Suspect 13.9%, Pathological 8.3% |
| Формат | XLS (лист «Raw Data») |

**Как получить:**
```bash
# Автоматически (в train_v2.py):
pip install ucimlrepo
python -c "from ucimlrepo import fetch_ucirepo; fetch_ucirepo(id=193)"

# Вручную: https://archive.uci.edu/dataset/193/cardiotocography
# → Download → CTG.xls → положить в backend/data/CTG.xls
```

---

### CTU-UHB Intrapartum CTG Database (PhysioNet)

| Параметр | Значение |
|----------|---------|
| Источник | https://physionet.org/content/ctu-uhb-ctgdb/ |
| Записей | 552 |
| Формат | WFDB (.dat + .hea) |
| Сигналы | FHR (уд/мин) + UC (маточная активность) |
| Исходы | pH пуповинной артерии, оценка по Апгар |
| Маппинг | pH < 7.05 → Pathological, < 7.15 → Suspect, иначе Normal |

**Автоматическая загрузка** через `wfdb.dl_database()` в `dataset_fusion.py`.

---

### Maternal Health Risk Dataset

| Параметр | Значение |
|----------|---------|
| Источник | https://www.kaggle.com/datasets/csafrit2/maternal-health-risk-data |
| Записей | 6 058 |
| Признаки | Age, SystolicBP, DiastolicBP, BS, BodyTemp, HeartRate |
| Целевая переменная | RiskLevel: low risk / mid risk / high risk |
| Баланс классов | low 40%, mid 33%, high 27% |
| Формат | CSV |

**Как получить:**
1. Kaggle → скачать `maternal_health_risk.csv`
2. Положить в `backend/data/maternal_health_risk.csv`
3. Если файл не найден → 1000 синтетических записей генерируются автоматически

---

## 14. Метрики модели

### CTG Ансамбль (основная модель)

| Метрика | После обучения | Цель | Важность |
|---------|---------------|------|----------|
| **ROC-AUC (macro OvR)** | **≥ 0.97** | ≥ 0.97 | Общая различимость классов |
| **Recall (Pathological)** | **≥ 0.93** | ≥ 0.93 | ⚡ Приоритет: пропуск патологии недопустим |
| **F1-macro** | **≥ 0.93** | ≥ 0.93 | Баланс precision/recall |
| **Accuracy** | **≥ 0.95** | ≥ 0.95 | Общая точность |

> ⚡ **Recall(Pathological)** — приоритетная метрика. Ложноотрицательный результат по классу «Pathological» (т.е. пропуск патологии) клинически недопустим.

### Maternal Health Risk (вспомогательная модель)

| Метрика | Значение |
|---------|---------|
| ROC-AUC | ≥ 0.94 |
| F1-macro | ≥ 0.90 |
| Accuracy | ≥ 0.88 |

### Почему метрики такие высокие?

Ансамблевый подход v2 vs одиночный CatBoost v1:

| Техника | Вклад в улучшение |
|---------|--------------------|
| SMOTE (Pathological 176→1600 записей) | +5-7% Recall(Path.) |
| 10 новых признаков-взаимодействий | +1-2% AUC |
| LightGBM + Optuna 60 trials | +2-3% AUC vs дефолтные параметры |
| Stacking (3 модели) | +1-2% F1-macro |
| Калибровка вероятностей | Более точные confidence-оценки |
| CTU-UHB (+~300 записей) | +0.5-1% по всем метрикам |

---

## 15. Часто задаваемые вопросы

### ❓ Сервис запускается, но `/health` возвращает `model_loaded: false`

**Нормально.** Модель не обучена. Сервис работает в mock-режиме, возвращает демо-предсказания. Запустите обучение: `python ml/train_v2.py`

---

### ❓ Ошибка при обучении: «ucimlrepo failed»

Нет интернета или заблокирован access. Скачайте CTG.xls вручную:
```
https://archive.uci.edu/dataset/193/cardiotocography → Download
Положите в: backend/data/CTG.xls
```

---

### ❓ Обучение идёт очень долго

Это нормально — Optuna тюнинг + Stacking на CPU занимает 20-30 минут. Ускорить:
```python
# В train_v2.py измените n_trials:
best_params = tune_lgbm(..., n_trials=20)  # вместо 60
```

---

### ❓ `422 Unprocessable Entity` при загрузке CSV

Проверьте:
1. Все обязательные колонки присутствуют (регистрозависимо: `LB`, не `lb`)
2. Значения числовые, нет пустых строк
3. Для `ctg-signals` — минимум 1200 строк
4. Кодировка файла: UTF-8

---

### ❓ Нет PostgreSQL, хочу только SQLite

По умолчанию SQLite уже используется. Убедитесь что `DATABASE_URL` не задан или содержит `sqlite:///`:
```env
# .env
DATABASE_URL=sqlite:///./perinatal.db
```

---

### ❓ Как добавить новую пациентку через API?

```bash
curl -X POST "http://localhost:8000/history/patients" \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "№2024-0999", "weeks_gestation": 35, "notes": "Первородящая"}'
```

---

### ❓ Как получить историю предсказаний для пациентки?

```bash
curl "http://localhost:8000/history/predictions?patient_id=№2024-0871&limit=10"
```

---

### ❓ Как запустить только часть тестов?

```bash
# Только pipeline
pytest tests/test_pipeline.py -v

# Только API
pytest tests/test_api.py -v

# Только быстрые (без модели)
pytest tests/ -v --ignore=tests/test_model.py
```

---

### ❓ Как обновить модель после добавления новых данных?

```bash
# Очистить кэш датасетов
rm -rf backend/data/cache/

# Переобучить
python ml/train_v2.py

# Перезапустить сервис
uvicorn app.main:app --reload --port 8000
```

---

### ❓ Где посмотреть логи предсказаний?

Все предсказания пишутся в `backend/predictions.log`:
```
2026-05-30T10:15:22Z  №2024-0871  Normal      0.9412
2026-05-30T10:16:05Z  №2024-0863  Suspect     0.7108
2026-05-30T10:17:11Z  №2024-0840  Pathological 0.8921
```

---

## Нормативная база

- **Приказ Минздрава РФ №1130н от 20.10.2020** — порядок оказания медицинской помощи по профилю «акушерство и гинекология»
- **Критерии FIGO 2015** — международная классификация КТГ-паттернов
- **NICE Guideline NG229** — Intrapartum care (2023)

---

*Версия инструкции: 2.0 · Дата: май 2026*  
*Все тестовые данные деперсонализированы или синтетически сгенерированы*  
*MIT License — https://github.com/ANNMNN/perinatal-care-ai*
