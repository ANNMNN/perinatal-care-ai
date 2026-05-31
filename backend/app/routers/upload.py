"""
Роутер загрузки файлов КТГ и ЭКГ.

Поддерживаемые форматы:
  csv_features  — CSV с 21 FIGO-признаком (прямой predict)
  csv_signals   — CSV с колонками fhr,uc (временные ряды) → extract_features → predict
  wfdb_zip      — ZIP с .dat + .hea PhysioNet-записью → WFDB parse → predict
  ecg_csv       — CSV с колонками Age,SystolicBP,DiastolicBP,BS,BodyTemp,HeartRate
                  → maternal risk predict
"""
from __future__ import annotations

import io
import logging
import os
import time
import uuid
import zipfile
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.features import extract_figo_features, FEATURE_ORDER
from app.model import get_model
from app.models_db import Patient, Visit, UploadedFile
from app.pipeline import CTGPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_SIZE_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))

pipe = CTGPipeline()

# ── Разрешённые расширения ─────────────────────────────────────────────
ALLOWED_EXT = {".csv", ".zip", ".dat", ".hea"}


def _save_upload(file: UploadFile) -> tuple[Path, bytes]:
    """Сохраняет загруженный файл на диск, возвращает (path, content)."""
    content = file.file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"Файл превышает {MAX_SIZE_MB} МБ")

    ext = Path(file.filename or "file").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, f"Недопустимый тип файла: {ext}")

    uid = uuid.uuid4().hex[:12]
    dest = UPLOAD_DIR / f"{uid}{ext}"
    dest.write_bytes(content)
    return dest, content


def _save_file_record(db: Session, original_name: str, saved_path: Path,
                      file_type: str, file_size: int,
                      patient_id: Optional[str], parsed_rows: int) -> UploadedFile:
    """Создаёт запись об uploaded-файле в БД."""
    rec = UploadedFile(
        filename=saved_path.name,
        original_name=original_name,
        file_type=file_type,
        file_size=file_size,
        patient_id=patient_id,
        parsed_rows=parsed_rows,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def _save_visit(db: Session, result: dict,
                patient_id: Optional[str], source: str) -> Visit:
    if patient_id:
        pat = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not pat:
            pat = Patient(patient_id=patient_id)
            db.add(pat)
            db.flush()

    mhr_data = None
    if result.get("maternal_risk"):
        mhr_data = {
            "risk":       result.get("maternal_risk"),
            "confidence": result.get("maternal_confidence"),
        }

    visit = Visit(
        patient_id=patient_id,
        screening_type="КТГ",
        input_format=source,
        predicted_class=result["class_label"],
        class_id=result["class_id"],
        probabilities=result.get("probabilities", {}),
        features=result.get("features", {}),
        shap_top=result.get("top_features", []),
        maternal_risk=mhr_data,
        model_version=result.get("model_version"),
        inference_ms=result.get("inference_ms"),
        warning=result.get("warning"),
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


# ── Endpoints ──────────────────────────────────────────────────────────

@router.post("/ctg-features")
async def upload_ctg_features(
    file: UploadFile = File(..., description="CSV с 21 FIGO-признаком"),
    patient_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Загрузка CSV с предвычисленными FIGO-признаками.

    Ожидаемые колонки (в любом порядке):
      LB,AC,FM,UC,ASTV,MSTV,ALTV,MLTV,DL,DS,DP,DR,Width,Min,Max,
      Nmax,Nzeros,Mode,Mean,Median,Variance

    Опционально: NSP (1/2/3) — для верификации.
    Опционально: patient_id — привяжет к карточке пациентки.
    """
    saved_path, content = _save_upload(file)
    t0 = time.perf_counter()

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(422, f"Не удалось разобрать CSV: {e}")

    missing = [c for c in FEATURE_ORDER if c not in df.columns]
    if missing:
        raise HTTPException(
            422,
            f"В CSV отсутствуют обязательные колонки: {missing}. "
            f"Скачай пример: /upload/examples/ctg_features"
        )

    model  = get_model()
    results = []
    warnings_list = []

    for i, row in df.iterrows():
        features = {f: float(row[f]) for f in FEATURE_ORDER}
        # Базовая валидация
        val = pipe.validate(np.array([features.get("LB", 135)] * 1200))
        warning = None
        if not val["ok"]:
            warning = "; ".join(val["warnings"])
            warnings_list.append(f"Строка {i}: {warning}")

        result = model.predict_ctg(features, warning=warning)
        pred   = _save_visit(db, result, patient_id, source="csv_features")
        result["visit_id"] = pred.id
        results.append(result)

    _save_file_record(db, file.filename or "upload.csv", saved_path,
                      "csv_features", len(content), patient_id, len(results))

    return {
        "status":        "ok",
        "parsed_rows":   len(results),
        "results":       results,
        "warnings":      warnings_list,
        "processing_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


@router.post("/ctg-signals")
async def upload_ctg_signals(
    file: UploadFile = File(..., description="CSV с колонками fhr,uc (временные ряды)"),
    patient_id: Optional[str] = Form(None),
    fs: int = Form(4, description="Частота дискретизации (Гц)"),
    db: Session = Depends(get_db),
):
    """
    Загрузка CSV с сырыми сигналами FHR и UC.

    Ожидаемые колонки: fhr, uc  (в уд/мин и отн.ед. соответственно)
    Минимум 1200 отсчётов (5 мин при 4 Гц).
    """
    saved_path, content = _save_upload(file)

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(422, f"Не удалось разобрать CSV: {e}")

    # Ищем колонки (case-insensitive)
    col_map = {c.lower(): c for c in df.columns}
    fhr_col = col_map.get("fhr") or col_map.get("fhr_bpm") or col_map.get("heart_rate")
    uc_col  = col_map.get("uc")  or col_map.get("toco") or col_map.get("uterine")

    if not fhr_col:
        raise HTTPException(
            422,
            "Нет колонки fhr. Ожидаемые: fhr, fhr_bpm. "
            "Скачай пример: /upload/examples/ctg_signals"
        )

    fhr = df[fhr_col].values.astype(float)
    uc  = df[uc_col].values.astype(float) if uc_col else np.zeros(len(fhr))

    val = pipe.validate(fhr)
    warning = ("; ".join(val["warnings"])) if not val["ok"] else None

    fhr_clean = pipe.clean(fhr)
    uc_clean  = pipe.clean(uc) if uc_col else uc

    features = extract_figo_features(fhr_clean, uc_clean, fs=fs)

    model  = get_model()
    result = model.predict_ctg(features, warning=warning)
    pred   = _save_visit(db, result, patient_id, source="csv_signals")
    result["visit_id"] = pred.id

    _save_file_record(db, file.filename or "signals.csv", saved_path,
                      "csv_signals", len(content), patient_id, 1)

    return {"status": "ok", "result": result, "n_samples": len(fhr)}


@router.post("/wfdb")
async def upload_wfdb(
    file: UploadFile = File(..., description="ZIP-архив с .dat + .hea файлами WFDB"),
    patient_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Загрузка записи в формате PhysioNet WFDB.
    Архив ZIP должен содержать: <name>.dat и <name>.hea
    """
    saved_path, content = _save_upload(file)

    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise HTTPException(422, "Ожидается ZIP-архив с .dat и .hea файлами")

    import tempfile
    import wfdb

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            zf.extractall(tmpdir)

        tmpdir_p = Path(tmpdir)
        dat_files = list(tmpdir_p.rglob("*.dat"))
        hea_files = list(tmpdir_p.rglob("*.hea"))

        if not dat_files or not hea_files:
            raise HTTPException(422, "ZIP не содержит .dat и .hea файлов")

        rec_name = str(dat_files[0].with_suffix(""))

        try:
            record = wfdb.rdrecord(rec_name)
        except Exception as e:
            raise HTTPException(422, f"Ошибка чтения WFDB: {e}")

        sig_names = [s.lower() for s in record.sig_name]
        fhr_idx = next((i for i, s in enumerate(sig_names) if "fhr" in s), 0)
        uc_idx  = next((i for i, s in enumerate(sig_names)
                        if "uc" in s or "toco" in s), 1)

        fhr = record.p_signal[:, fhr_idx].astype(float)
        uc  = (record.p_signal[:, uc_idx].astype(float)
               if record.p_signal.shape[1] > 1 else np.zeros(len(fhr)))

    val       = pipe.validate(fhr)
    warning   = ("; ".join(val["warnings"])) if not val["ok"] else None
    fhr_clean = pipe.clean(fhr)
    uc_clean  = pipe.clean(uc)

    features  = extract_figo_features(fhr_clean, uc_clean, fs=record.fs)
    model     = get_model()
    result    = model.predict_ctg(features, warning=warning)
    pred      = _save_visit(db, result, patient_id, source="wfdb_upload")
    result["visit_id"] = pred.id

    _save_file_record(db, file.filename or "record.zip", saved_path,
                      "wfdb", len(content), patient_id, 1)

    return {
        "status":   "ok",
        "result":   result,
        "n_samples": int(len(fhr)),
        "fs":       record.fs,
        "signals":  record.sig_name,
    }


@router.post("/ecg-maternal")
async def upload_ecg_maternal(
    file: UploadFile = File(..., description="CSV с ЭКГ/витальными показателями матери"),
    patient_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Загрузка CSV с показателями материнского здоровья.

    Ожидаемые колонки:
      Age, SystolicBP, DiastolicBP, BS (blood sugar), BodyTemp, HeartRate
    """
    saved_path, content = _save_upload(file)
    t0 = time.perf_counter()

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(422, f"Не удалось разобрать CSV: {e}")

    required = ["Age", "SystolicBP", "DiastolicBP", "BS", "BodyTemp", "HeartRate"]
    # Case-insensitive mapping
    col_map = {c.lower(): c for c in df.columns}
    mapped  = {r: col_map.get(r.lower()) for r in required}
    missing = [r for r, c in mapped.items() if c is None]
    if missing:
        raise HTTPException(
            422,
            f"Отсутствуют колонки: {missing}. "
            "Скачай пример: /upload/examples/ecg_maternal"
        )

    model   = get_model()
    results = []

    for i, row in df.iterrows():
        mhr = model.predict_maternal(
            age=float(row[mapped["Age"]]),
            systolic_bp=float(row[mapped["SystolicBP"]]),
            diastolic_bp=float(row[mapped["DiastolicBP"]]),
            bs=float(row[mapped["BS"]]),
            body_temp=float(row[mapped["BodyTemp"]]),
            heart_rate=float(row[mapped["HeartRate"]]),
        )
        result = {
            "row": i,
            "maternal_risk": mhr["risk"],
            "maternal_confidence": mhr["confidence"],
            "probabilities": mhr.get("probabilities", {}),
        }
        results.append(result)

    _save_file_record(db, file.filename or "ecg.csv", saved_path,
                      "ecg", len(content), patient_id, len(results))

    return {
        "status":        "ok",
        "parsed_rows":   len(results),
        "results":       results,
        "processing_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


# ── Примеры данных ─────────────────────────────────────────────────────

@router.get("/examples/{example_type}")
async def get_example(example_type: str):
    """
    Скачать пример данных для загрузки.
    Типы: ctg_features | ctg_signals | ecg_maternal
    """
    from fastapi.responses import PlainTextResponse

    examples = {
        "ctg_features": _ctg_features_example(),
        "ctg_signals":  _ctg_signals_example(),
        "ecg_maternal": _ecg_maternal_example(),
    }
    if example_type not in examples:
        raise HTTPException(404, f"Неизвестный тип примера: {example_type}. "
                            f"Доступны: {list(examples)}")

    return PlainTextResponse(
        content=examples[example_type],
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={example_type}_example.csv"},
    )


def _ctg_features_example() -> str:
    """CSV с 3 примерами: Normal, Suspect, Pathological."""
    header = ",".join(FEATURE_ORDER + ["NSP"])
    rows = [
        # Normal (типичная норма)
        "133,0,0,0,27,0.9,27,6.8,0,0,0,0,64,62,126,2,18,120,137,121,73,1",
        # Suspect (сниженная вариабельность, единичные децелерации)
        "148,0,1,0,14,0.4,14,3.2,1,0,0,0,40,75,155,4,32,145,147,146,19,2",
        # Pathological (брадикардия, отсутствие акцелераций, поздние децелерации)
        "107,0,0,0,8,0.2,8,1.1,3,1,0,1,28,60,120,1,48,108,109,110,6,3",
    ]
    return header + "\n" + "\n".join(rows) + "\n"


def _ctg_signals_example() -> str:
    """CSV с 1500 отсчётами FHR и UC (сигналы Normal)."""
    rng = np.random.default_rng(42)
    n = 1500
    t = np.linspace(0, n / 4, n)  # 4 Гц → 375 секунд
    fhr = (138 + 10 * np.sin(t / 8) + rng.normal(0, 2, n)).clip(110, 165)
    uc  = np.maximum(0,
        30 * np.exp(-0.5 * ((t - 60) / 15) ** 2) +
        28 * np.exp(-0.5 * ((t - 200) / 12) ** 2) +
        25 * np.exp(-0.5 * ((t - 310) / 14) ** 2)
    )
    lines = ["fhr,uc"] + [f"{fhr[i]:.1f},{uc[i]:.2f}" for i in range(n)]
    return "\n".join(lines) + "\n"


def _ecg_maternal_example() -> str:
    """CSV с 5 примерами материнских показателей."""
    header = "Age,SystolicBP,DiastolicBP,BS,BodyTemp,HeartRate,RiskLevel"
    rows = [
        "25,110,70,7.0,36.6,72,low risk",
        "32,130,85,9.5,37.1,80,mid risk",
        "38,150,100,13.0,37.8,88,high risk",
        "28,118,76,7.8,36.8,75,low risk",
        "41,160,110,15.5,38.2,95,high risk",
    ]
    return header + "\n" + "\n".join(rows) + "\n"
