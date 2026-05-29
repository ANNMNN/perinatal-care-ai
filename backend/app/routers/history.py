"""
Роутер истории предсказаний и управления пациентками.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import Patient, Prediction, UploadedFile

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/predictions")
def list_predictions(
    patient_id: Optional[str] = Query(None, description="Фильтр по ID пациентки"),
    class_label: Optional[str] = Query(None, description="Фильтр по классу Normal|Suspect|Pathological"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Список предсказаний с пагинацией и фильтрацией."""
    q = db.query(Prediction)
    if patient_id:
        q = q.filter(Prediction.patient_id == patient_id)
    if class_label:
        q = q.filter(Prediction.class_label == class_label)
    total = q.count()
    preds = q.order_by(Prediction.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "predictions": [p.to_dict() for p in preds],
    }


@router.get("/predictions/{pred_id}")
def get_prediction(pred_id: int, db: Session = Depends(get_db)):
    """Получить конкретное предсказание по ID."""
    p = db.query(Prediction).filter(Prediction.id == pred_id).first()
    if not p:
        raise HTTPException(404, f"Предсказание #{pred_id} не найдено")
    return p.to_dict()


@router.delete("/predictions/{pred_id}")
def delete_prediction(pred_id: int, db: Session = Depends(get_db)):
    p = db.query(Prediction).filter(Prediction.id == pred_id).first()
    if not p:
        raise HTTPException(404, f"Предсказание #{pred_id} не найдено")
    db.delete(p)
    db.commit()
    return {"status": "deleted", "id": pred_id}


@router.get("/patients")
def list_patients(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Список пациенток."""
    total = db.query(Patient).count()
    patients = (db.query(Patient)
                .order_by(Patient.created_at.desc())
                .offset(offset).limit(limit).all())
    result = []
    for pat in patients:
        d = pat.to_dict()
        # Последнее предсказание
        last_pred = (db.query(Prediction)
                     .filter(Prediction.patient_id == pat.patient_id)
                     .order_by(Prediction.created_at.desc())
                     .first())
        d["last_prediction"] = last_pred.to_dict() if last_pred else None
        d["predictions_count"] = (db.query(Prediction)
                                   .filter(Prediction.patient_id == pat.patient_id)
                                   .count())
        result.append(d)
    return {"total": total, "patients": result}


@router.get("/patients/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    pat = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not pat:
        raise HTTPException(404, f"Пациентка {patient_id} не найдена")
    d = pat.to_dict()
    d["predictions"] = [p.to_dict() for p in pat.predictions]
    d["files"]       = [f.to_dict() for f in pat.files]
    return d


@router.post("/patients")
def create_patient(
    patient_id: str,
    weeks_gestation: Optional[int] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
):
    existing = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if existing:
        raise HTTPException(409, f"Пациентка {patient_id} уже существует")
    pat = Patient(
        patient_id=patient_id,
        weeks_gestation=weeks_gestation,
        notes=notes,
    )
    db.add(pat)
    db.commit()
    db.refresh(pat)
    return pat.to_dict()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Сводная статистика по базе данных."""
    total = db.query(Prediction).count()
    by_class = {}
    for cls in ["Normal", "Suspect", "Pathological"]:
        by_class[cls] = db.query(Prediction).filter(Prediction.class_label == cls).count()
    return {
        "total_predictions": total,
        "by_class":          by_class,
        "total_patients":    db.query(Patient).count(),
        "total_files":       db.query(UploadedFile).count(),
    }


@router.get("/files")
def list_files(
    patient_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(UploadedFile)
    if patient_id:
        q = q.filter(UploadedFile.patient_id == patient_id)
    files = q.order_by(UploadedFile.created_at.desc()).limit(limit).all()
    return {"files": [f.to_dict() for f in files]}
