from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import Patient, Visit
from app.schemas import DashboardStatsOut

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStatsOut)
def dashboard_stats(db: Session = Depends(get_db)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_patients = db.query(Patient).count()
    total_visits   = db.query(Visit).count()
    today_visits   = db.query(Visit).filter(Visit.visit_date >= today_start).count()

    by_class: dict[str, int] = {}
    for cls in ("Normal", "Suspect", "Pathological"):
        by_class[cls] = db.query(Visit).filter(Visit.predicted_class == cls).count()

    recent = (
        db.query(Visit)
        .order_by(Visit.visit_date.desc())
        .limit(10)
        .all()
    )
    recent_list = []
    for v in recent:
        d = v.to_dict()
        # Attach patient info when available
        if v.patient_id:
            pat = db.query(Patient).filter(
                Patient.patient_id == v.patient_id).first()
            d["weeks_gestation"] = pat.weeks_gestation if pat else None
        else:
            d["weeks_gestation"] = None
        recent_list.append(d)

    return DashboardStatsOut(
        total_patients=total_patients,
        total_visits=total_visits,
        today_visits=today_visits,
        by_class=by_class,
        recent_visits=recent_list,
    )
