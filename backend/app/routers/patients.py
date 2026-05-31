from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.aggregate import aggregate_risk
from app.database import get_db
from app.models_db import Patient, Visit
from app.schedule_config import expected_interval
from app.schemas import (
    AggregatePredictionOut, DoctorLabelIn,
    PatientCreate, PatientOut, VisitOut,
)

router = APIRouter(prefix="/patients", tags=["Patients"])


def _patient_or_404(patient_id: str, db: Session) -> Patient:
    pat = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not pat:
        raise HTTPException(404, f"Пациент {patient_id!r} не найден")
    return pat


# ── Patients CRUD ──────────────────────────────────────────────────────

@router.get("", response_model=dict)
def list_patients(
    search: Optional[str] = Query(None, description="Поиск по patient_id"),
    limit:  int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db:     Session = Depends(get_db),
):
    q = db.query(Patient)
    if search:
        q = q.filter(Patient.patient_id.ilike(f"%{search}%"))
    total = q.count()
    patients = q.order_by(Patient.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for pat in patients:
        d = pat.to_dict()
        last_visit = (
            db.query(Visit)
            .filter(Visit.patient_id == pat.patient_id)
            .order_by(Visit.visit_date.desc())
            .first()
        )
        d["last_visit"]   = last_visit.to_dict() if last_visit else None
        d["visits_count"] = db.query(Visit).filter(
            Visit.patient_id == pat.patient_id).count()
        result.append(d)

    return {"total": total, "offset": offset, "limit": limit, "patients": result}


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(body: PatientCreate, db: Session = Depends(get_db)):
    if db.query(Patient).filter(Patient.patient_id == body.patient_id).first():
        raise HTTPException(409, f"Пациент {body.patient_id!r} уже существует")
    pat = Patient(
        patient_id=body.patient_id,
        weeks_gestation=body.weeks_gestation,
        notes=body.notes,
    )
    db.add(pat)
    db.commit()
    db.refresh(pat)
    return pat.to_dict()


@router.get("/{patient_id}", response_model=dict)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    pat = _patient_or_404(patient_id, db)
    d = pat.to_dict()
    d["visits"] = [v.to_dict() for v in pat.visits]
    d["files"]  = [f.to_dict() for f in pat.files]

    # Schedule analysis
    if pat.visits:
        last = pat.visits[-1]
        interval = expected_interval(last.gestational_week or pat.weeks_gestation)
        d["expected_interval_days"] = interval
        last_date = last.visit_date or last.created_at
        if last_date:
            delta = (datetime.utcnow() - last_date).days
            d["days_since_last_visit"] = delta
            d["overdue"] = delta > interval
        else:
            d["days_since_last_visit"] = None
            d["overdue"] = False
    else:
        d["expected_interval_days"] = None
        d["days_since_last_visit"]  = None
        d["overdue"]                = False

    return d


@router.get("/{patient_id}/visits", response_model=dict)
def get_patient_visits(
    patient_id: str,
    limit:  int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db:     Session = Depends(get_db),
):
    _patient_or_404(patient_id, db)
    q = db.query(Visit).filter(Visit.patient_id == patient_id)
    total = q.count()
    visits = q.order_by(Visit.visit_date.desc()).offset(offset).limit(limit).all()

    result = []
    for v in visits:
        d = v.to_dict()
        week = v.gestational_week
        interval = expected_interval(week)
        d["expected_interval_days"] = interval
        result.append(d)

    return {"total": total, "visits": result}


@router.get("/{patient_id}/aggregate-prediction",
            response_model=AggregatePredictionOut)
def get_aggregate(patient_id: str, db: Session = Depends(get_db)):
    _patient_or_404(patient_id, db)
    visits = (
        db.query(Visit)
        .filter(Visit.patient_id == patient_id)
        .order_by(Visit.visit_date.asc())
        .all()
    )
    agg = aggregate_risk(visits)
    return AggregatePredictionOut(
        patient_id=patient_id,
        **agg,
    )


# ── Visits ─────────────────────────────────────────────────────────────

@router.get("/visits/{visit_id}", response_model=VisitOut)
def get_visit(visit_id: int, db: Session = Depends(get_db)):
    v = db.query(Visit).filter(Visit.id == visit_id).first()
    if not v:
        raise HTTPException(404, f"Приём #{visit_id} не найден")
    return v.to_dict()


@router.patch("/visits/{visit_id}/label")
def label_visit(
    visit_id: int,
    body: DoctorLabelIn,
    db: Session = Depends(get_db),
):
    v = db.query(Visit).filter(Visit.id == visit_id).first()
    if not v:
        raise HTTPException(404, f"Приём #{visit_id} не найден")

    v.doctor_label   = body.doctor_label
    v.doctor_comment = body.doctor_comment
    v.labeled_at     = datetime.now(timezone.utc) if body.doctor_label else None
    db.commit()
    db.refresh(v)
    return v.to_dict()
