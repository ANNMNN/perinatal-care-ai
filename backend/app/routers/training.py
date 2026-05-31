from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.features import FEATURE_ORDER
from app.model import get_model
from app.models_db import Visit

router = APIRouter(tags=["Training"])

LABEL_MAP = {"N": "Normal", "S": "Suspect", "P": "Pathological"}


@router.get("/training-data/export")
def export_labeled_visits(db: Session = Depends(get_db)):
    """
    Export visits with doctor labels as CSV for retraining.
    Columns: 21 FIGO features + doctor_class (Normal/Suspect/Pathological).
    """
    visits = (
        db.query(Visit)
        .filter(Visit.doctor_label.isnot(None))
        .order_by(Visit.visit_date.asc())
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(FEATURE_ORDER + ["doctor_class", "visit_id"])

    for v in visits:
        feats = v.features or {}
        row = [feats.get(f, "") for f in FEATURE_ORDER]
        row.append(LABEL_MAP.get(v.doctor_label or "", v.doctor_label or ""))
        row.append(v.id)
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=labeled_visits.csv"},
    )


@router.post("/models/reload")
def reload_model():
    """Reload the ML model from disk without restarting the service."""
    import app.model as m
    m._model_instance = None
    model = get_model()
    return {
        "status":  "reloaded",
        "version": model.version,
        "loaded":  model.is_loaded,
    }
