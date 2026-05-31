"""
Tests for patients CRUD, visits, doctor label, aggregate, dashboard, training export.
"""
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.main import app

client = TestClient(app)

PID = "test-patient-001"
PID2 = "test-patient-002"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    # Delete test patients after each test
    for pid in (PID, PID2):
        try:
            from app.database import SessionLocal
            from app.models_db import Patient
            db = SessionLocal()
            pat = db.query(Patient).filter(Patient.patient_id == pid).first()
            if pat:
                db.delete(pat)
                db.commit()
            db.close()
        except Exception:
            pass


class TestPatientsCRUD:
    def test_list_patients_ok(self):
        r = client.get("/patients")
        assert r.status_code == 200
        data = r.json()
        assert "patients" in data
        assert "total" in data

    def test_create_patient(self):
        r = client.post("/patients", json={"patient_id": PID, "weeks_gestation": 36})
        assert r.status_code == 201
        data = r.json()
        assert data["patient_id"] == PID
        assert data["weeks_gestation"] == 36

    def test_create_patient_duplicate(self):
        client.post("/patients", json={"patient_id": PID2})
        r = client.post("/patients", json={"patient_id": PID2})
        assert r.status_code == 409

    def test_get_patient_not_found(self):
        r = client.get("/patients/nonexistent-xyz")
        assert r.status_code == 404

    def test_get_patient_with_visits(self):
        client.post("/patients", json={"patient_id": PID})
        r = client.get(f"/patients/{PID}")
        assert r.status_code == 200
        data = r.json()
        assert data["patient_id"] == PID
        assert "visits" in data
        assert "expected_interval_days" in data

    def test_search_patients(self):
        client.post("/patients", json={"patient_id": PID})
        r = client.get(f"/patients?search={PID[:6]}")
        assert r.status_code == 200
        pids = [p["patient_id"] for p in r.json()["patients"]]
        assert PID in pids

    def test_list_patients_pagination(self):
        r = client.get("/patients?limit=5&offset=0")
        assert r.status_code == 200
        assert len(r.json()["patients"]) <= 5


class TestVisits:
    def _make_visit(self):
        fhr = [138.0] * 200
        payload = {"fhr": fhr, "uc": [0.0] * 200, "fs": 4, "patient_id": PID}
        return client.post("/predict", json=payload).json()

    def test_predict_creates_visit(self):
        client.post("/patients", json={"patient_id": PID})
        resp = self._make_visit()
        assert "visit_id" in resp
        assert resp["visit_id"] is not None

    def test_get_visit(self):
        client.post("/patients", json={"patient_id": PID})
        pred = self._make_visit()
        vid = pred["visit_id"]
        if vid:
            r = client.get(f"/patients/visits/{vid}")
            assert r.status_code == 200
            assert r.json()["patient_id"] == PID

    def test_get_visit_not_found(self):
        r = client.get("/patients/visits/999999")
        assert r.status_code == 404

    def test_patient_visits_endpoint(self):
        client.post("/patients", json={"patient_id": PID})
        self._make_visit()
        r = client.get(f"/patients/{PID}/visits")
        assert r.status_code == 200
        data = r.json()
        assert "visits" in data
        assert data["total"] >= 1


class TestDoctorLabel:
    def _make_visit(self):
        client.post("/patients", json={"patient_id": PID})
        fhr = [138.0] * 200
        resp = client.post("/predict", json={"fhr": fhr, "uc": [0.0] * 200, "fs": 4, "patient_id": PID}).json()
        return resp.get("visit_id")

    def test_label_visit(self):
        vid = self._make_visit()
        if vid is None:
            pytest.skip("DB unavailable")
        r = client.patch(f"/patients/visits/{vid}/label",
                         json={"doctor_label": "N", "doctor_comment": "Норма"})
        assert r.status_code == 200
        data = r.json()
        assert data["doctor_label"] == "N"
        assert data["doctor_comment"] == "Норма"
        assert data["labeled_at"] is not None

    def test_label_visit_invalid(self):
        vid = self._make_visit()
        if vid is None:
            pytest.skip("DB unavailable")
        r = client.patch(f"/patients/visits/{vid}/label",
                         json={"doctor_label": "X"})
        assert r.status_code == 422

    def test_label_visit_clear(self):
        vid = self._make_visit()
        if vid is None:
            pytest.skip("DB unavailable")
        client.patch(f"/patients/visits/{vid}/label", json={"doctor_label": "S"})
        r = client.patch(f"/patients/visits/{vid}/label", json={"doctor_label": None})
        assert r.status_code == 200
        assert r.json()["doctor_label"] is None

    def test_label_not_found(self):
        r = client.patch("/patients/visits/999999/label", json={"doctor_label": "N"})
        assert r.status_code == 404


class TestAggregatePrediction:
    def test_aggregate_no_visits(self):
        client.post("/patients", json={"patient_id": PID})
        r = client.get(f"/patients/{PID}/aggregate-prediction")
        assert r.status_code == 200
        data = r.json()
        assert "aggregate_class" in data
        assert "trend" in data
        assert "explanation" in data
        assert "visits" in data

    def test_aggregate_not_found(self):
        r = client.get("/patients/nonexistent-xyz/aggregate-prediction")
        assert r.status_code == 404

    def test_aggregate_with_visits(self):
        client.post("/patients", json={"patient_id": PID})
        fhr = [138.0] * 200
        for _ in range(2):
            client.post("/predict", json={"fhr": fhr, "uc": [], "fs": 4, "patient_id": PID})
        r = client.get(f"/patients/{PID}/aggregate-prediction")
        assert r.status_code == 200
        data = r.json()
        assert data["aggregate_class"] in ("Normal", "Suspect", "Pathological")
        assert len(data["explanation"]) >= 1


class TestDashboard:
    def test_dashboard_stats(self):
        r = client.get("/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        for key in ("total_patients", "total_visits", "today_visits", "by_class", "recent_visits"):
            assert key in data

    def test_dashboard_by_class_keys(self):
        data = client.get("/dashboard/stats").json()
        for cls in ("Normal", "Suspect", "Pathological"):
            assert cls in data["by_class"]

    def test_dashboard_recent_visits_list(self):
        data = client.get("/dashboard/stats").json()
        assert isinstance(data["recent_visits"], list)


class TestTrainingExport:
    def test_export_csv_content_type(self):
        r = client.get("/training-data/export")
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")

    def test_export_has_header(self):
        r = client.get("/training-data/export")
        lines = r.text.strip().splitlines()
        if lines:
            assert "doctor_class" in lines[0]
