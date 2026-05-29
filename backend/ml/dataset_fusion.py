"""
Загрузка и объединение трёх датасетов:

  1. UCI CTG Dataset (auto-download via ucimlrepo, id=193)
     2 126 записей, 21 FIGO-признак → NSP (1=Normal,2=Suspect,3=Path.)

  2. CTU-UHB Intrapartum CTG Database (PhysioNet WFDB)
     552 записи, сырые сигналы → pH/Apgar → NSP-метки
     Авто-загрузка 10 примеров через wfdb.dl_database()

  3. Maternal Health Risk Dataset (CSV — кладём в data/maternal_health_risk.csv)
     6 058 записей: Age,SystolicBP,DiastolicBP,BS,BodyTemp,HeartRate → RiskLevel
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger("dataset_fusion")

ROOT = Path(__file__).parent.parent
DATA_DIR  = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Константы ─────────────────────────────────────────────────────────
CTG_FEATURES = [
    "LB", "AC", "FM", "UC", "ASTV", "MSTV", "ALTV", "MLTV",
    "DL", "DS", "DP", "DR", "Width", "Min", "Max",
    "Nmax", "Nzeros", "Mode", "Mean", "Median", "Variance",
]
CTG_TARGET = "NSP"

MHR_FEATURES = ["Age", "SystolicBP", "DiastolicBP", "BS", "BodyTemp", "HeartRate"]
MHR_TARGET = "RiskLevel"
MHR_LABEL_MAP = {"low risk": 0, "mid risk": 1, "high risk": 2}


# ═══════════════════════════════════════════════════════════════════════
# 1. UCI CTG
# ═══════════════════════════════════════════════════════════════════════

def load_uci_ctg() -> pd.DataFrame:
    """
    Загрузка UCI CTG Dataset.
    Сначала пробует ucimlrepo (авто-скачивание),
    затем fallback → data/CTG.xls (если файл уже есть).
    """
    cache_path = CACHE_DIR / "uci_ctg.parquet"
    if cache_path.exists():
        logger.info("UCI CTG: из кэша %s", cache_path)
        return pd.read_parquet(cache_path)

    # --- Попытка 1: ucimlrepo ------------------------------------------
    try:
        from ucimlrepo import fetch_ucirepo
        logger.info("UCI CTG: скачивание через ucimlrepo...")
        dataset = fetch_ucirepo(id=193)
        X = dataset.data.features
        y = dataset.data.targets
        df = X.copy()
        df[CTG_TARGET] = y.values.ravel()
    except Exception as e:
        logger.warning("ucimlrepo failed (%s), пробуем XLS...", e)

        # --- Попытка 2: локальный XLS -----------------------------------
        xls_path = DATA_DIR / "CTG.xls"
        if not xls_path.exists():
            raise FileNotFoundError(
                f"Нет ни ucimlrepo, ни файла {xls_path}. "
                "Скачай CTG.xls: https://archive.ics.uci.edu/dataset/193/cardiotocography"
            )
        df = pd.read_excel(xls_path, sheet_name="Raw Data", header=1)

    # Очистка
    df = df.dropna(subset=[CTG_TARGET])
    df = df[df[CTG_TARGET].isin([1, 2, 3])].copy()

    # Приводим признаки к float
    for col in CTG_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[CTG_FEATURES + [CTG_TARGET]].dropna()
    df[CTG_TARGET] = df[CTG_TARGET].astype(int)
    df["source"] = "uci_ctg"

    df.to_parquet(cache_path, index=False)
    logger.info("UCI CTG: %d записей сохранено в кэш", len(df))
    return df


# ═══════════════════════════════════════════════════════════════════════
# 2. CTU-UHB PhysioNet
# ═══════════════════════════════════════════════════════════════════════

def _ph_to_nsp(ph: float) -> int:
    """Конвертация pH пуповинной артерии → NSP-класс."""
    if pd.isna(ph):
        return -1
    if ph < 7.05:
        return 3  # Pathological
    if ph < 7.15:
        return 2  # Suspect
    return 1      # Normal


def load_ctu_uhb(max_records: int = 552) -> pd.DataFrame:
    """
    Загружает CTU-UHB через wfdb.
    Для каждой записи извлекает FIGO-признаки из FHR-сигнала
    и маппит pH → NSP-класс.

    Результат дополняет UCI CTG дополнительными ~380 записями.
    """
    cache_path = CACHE_DIR / "ctu_uhb.parquet"
    if cache_path.exists():
        logger.info("CTU-UHB: из кэша %s", cache_path)
        return pd.read_parquet(cache_path)

    try:
        import wfdb
        from app.features import extract_figo_features
        from app.pipeline import CTGPipeline
    except ImportError as e:
        logger.warning("CTU-UHB: wfdb недоступен (%s). Пропускаем.", e)
        return pd.DataFrame()

    pipe = CTGPipeline()
    DB_NAME = "ctu-uhb-ctgdb"
    records_dir = CACHE_DIR / "ctu_uhb_raw"
    records_dir.mkdir(exist_ok=True)

    logger.info("CTU-UHB: скачивание до %d записей (PhysioNet)...", max_records)
    try:
        record_list = wfdb.get_record_list(DB_NAME)[:max_records]
    except Exception as e:
        logger.warning("Не удалось получить список записей CTU-UHB: %s", e)
        return pd.DataFrame()

    rows = []
    for rec_name in record_list:
        try:
            record = wfdb.rdrecord(rec_name, pn_dir=DB_NAME)
            ann    = wfdb.rdheader(rec_name, pn_dir=DB_NAME)

            # FHR = сигнал 0 (уд/мин), UC = сигнал 1
            sig_names = [s.lower() for s in record.sig_name]
            fhr_idx = next((i for i, s in enumerate(sig_names) if "fhr" in s), 0)
            uc_idx  = next((i for i, s in enumerate(sig_names) if "uc" in s or "toco" in s), 1)

            fhr = record.p_signal[:, fhr_idx].astype(float)
            uc  = record.p_signal[:, uc_idx].astype(float) \
                  if record.p_signal.shape[1] > 1 else np.zeros(len(fhr))

            # Валидация
            val = pipe.validate(fhr)
            if val["gap_ratio"] > 0.20:
                continue

            fhr_clean = pipe.clean(fhr)
            uc_clean  = pipe.clean(uc) if uc.max() > 0 else uc

            feats = extract_figo_features(fhr_clean, uc_clean, fs=record.fs)

            # pH из comments хедера
            ph_val = None
            for comment in (ann.comments or []):
                if "pH" in comment:
                    try:
                        ph_val = float(comment.split("pH")[1].strip().split()[0])
                    except Exception:
                        pass

            nsp = _ph_to_nsp(ph_val) if ph_val else -1
            if nsp == -1:
                continue

            row = {**feats, CTG_TARGET: nsp, "source": "ctu_uhb"}
            rows.append(row)

        except Exception as exc:
            logger.debug("Запись %s пропущена: %s", rec_name, exc)
            continue

    if not rows:
        logger.warning("CTU-UHB: не удалось извлечь ни одной записи.")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df.to_parquet(cache_path, index=False)
    logger.info("CTU-UHB: %d записей сохранено в кэш", len(df))
    return df


# ═══════════════════════════════════════════════════════════════════════
# 3. Maternal Health Risk
# ═══════════════════════════════════════════════════════════════════════

def load_maternal_health_risk() -> pd.DataFrame:
    """
    Загружает Maternal Health Risk Dataset.
    Ищет файл: data/maternal_health_risk.csv
    (скачать с Kaggle: https://www.kaggle.com/datasets/csafrit2/maternal-health-risk-data)

    Если файл не найден → генерирует синтетическую заглушку.
    """
    csv_path = DATA_DIR / "maternal_health_risk.csv"

    if csv_path.exists():
        logger.info("Maternal Health Risk: загрузка из %s", csv_path)
        df = pd.read_csv(csv_path)
    else:
        logger.warning(
            "maternal_health_risk.csv не найден. "
            "Генерируем синтетические данные (1000 записей). "
            "Для реального обучения скачай с Kaggle."
        )
        df = _generate_synthetic_mhr(n=1000)

    # Нормализация названий признаков
    rename = {"RiskLevel": "RiskLevel", "Risk Level": "RiskLevel"}
    df = df.rename(columns=rename)

    for col in MHR_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[MHR_FEATURES + ["RiskLevel"]].dropna()
    df["RiskLevel_enc"] = df["RiskLevel"].str.lower().str.strip().map(MHR_LABEL_MAP)
    df = df.dropna(subset=["RiskLevel_enc"])
    df["RiskLevel_enc"] = df["RiskLevel_enc"].astype(int)

    logger.info("Maternal Health Risk: %d записей", len(df))
    return df


def _generate_synthetic_mhr(n: int = 1000) -> pd.DataFrame:
    """Синтетические данные материнского риска."""
    rng = np.random.default_rng(42)
    rows = []
    for _ in range(n):
        risk = rng.choice(["low risk", "mid risk", "high risk"], p=[0.40, 0.35, 0.25])
        if risk == "low risk":
            row = dict(
                Age=rng.integers(20, 32),
                SystolicBP=rng.integers(90, 120),
                DiastolicBP=rng.integers(60, 80),
                BS=round(rng.uniform(6.0, 7.5), 1),
                BodyTemp=round(rng.uniform(36.5, 37.0), 1),
                HeartRate=rng.integers(65, 80),
                RiskLevel="low risk",
            )
        elif risk == "mid risk":
            row = dict(
                Age=rng.integers(25, 40),
                SystolicBP=rng.integers(120, 140),
                DiastolicBP=rng.integers(80, 95),
                BS=round(rng.uniform(7.5, 11.0), 1),
                BodyTemp=round(rng.uniform(37.0, 37.5), 1),
                HeartRate=rng.integers(76, 90),
                RiskLevel="mid risk",
            )
        else:
            row = dict(
                Age=rng.integers(30, 50),
                SystolicBP=rng.integers(140, 180),
                DiastolicBP=rng.integers(90, 120),
                BS=round(rng.uniform(11.0, 19.0), 1),
                BodyTemp=round(rng.uniform(37.5, 38.5), 1),
                HeartRate=rng.integers(85, 105),
                RiskLevel="high risk",
            )
        rows.append(row)
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# Публичный API
# ═══════════════════════════════════════════════════════════════════════

def load_ctg_combined(use_ctu: bool = True) -> tuple[pd.DataFrame, pd.Series]:
    """
    Объединяет UCI CTG + (опционально) CTU-UHB.
    Возвращает (X, y) готовые к обучению.
    """
    df_uci = load_uci_ctg()
    dfs = [df_uci]

    if use_ctu:
        df_ctu = load_ctu_uhb()
        if not df_ctu.empty:
            # Добавляем только колонки признаков + target
            cols_needed = CTG_FEATURES + [CTG_TARGET]
            df_ctu_filtered = df_ctu[[c for c in cols_needed if c in df_ctu.columns]]
            if CTG_TARGET in df_ctu_filtered.columns:
                dfs.append(df_ctu_filtered)
                logger.info("CTU-UHB добавлен: +%d записей", len(df_ctu_filtered))

    df = pd.concat(dfs, ignore_index=True)
    df = df.dropna(subset=CTG_FEATURES + [CTG_TARGET])

    X = df[CTG_FEATURES].values.astype(float)
    y = df[CTG_TARGET].values.astype(int) - 1  # 0-indexed

    logger.info(
        "CTG combined: %d записей | Классы: Normal=%d Suspect=%d Path.=%d",
        len(y),
        int((y == 0).sum()),
        int((y == 1).sum()),
        int((y == 2).sum()),
    )
    return X, y
