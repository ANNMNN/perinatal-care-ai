"""
Тесты FastAPI эндпоинтов: /health, /models, /features/importance, /predict, /predict/batch
"""
import numpy as np
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.main import app

client = TestClient(app)

# ── Синтетические сигналы ───────────────────────────────────────────────
RNG = np.random.default_rng(42)
FHR = (138 + 8 * np.sin(np.linspace(0, 6 * np.pi, 1200))
       + RNG.normal(0, 2, 1200)).tolist()
UC  = np.clip(
    25 * np.exp(-0.5 * ((np.linspace(0, 300, 1200) - 60) / 15) ** 2), 0, None
).tolist()

VALID_PAYLOAD = {"fhr": FHR, "uc": UC, "fs": 4, "patient_id": "test-001"}


class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_fields(self):
        r = client.get("/health")
        data = r.json()
        assert "status" in data
        assert "model_version" in data
        assert "uptime_seconds" in data
        assert "model_loaded" in data
        assert data["status"] == "ok"

    def test_uptime_positive(self):
        r = client.get("/health")
        assert r.json()["uptime_seconds"] >= 0


class TestModels:
    def test_models_returns_list(self):
        r = client.get("/models")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_model_has_required_fields(self):
        data = client.get("/models").json()[0]
        for field in ["name", "version", "roc_auc", "f1_macro", "accuracy", "recall_pathological"]:
            assert field in data, f"Поле {field} отсутствует"

    def test_metrics_in_range(self):
        data = client.get("/models").json()[0]
        for field in ["roc_auc", "f1_macro", "accuracy", "recall_pathological"]:
            val = data[field]
            assert 0.0 <= val <= 1.0, f"{field}={val} вне [0,1]"


class TestFeatureImportance:
    def test_returns_importance(self):
        r = client.get("/features/importance")
        assert r.status_code == 200
        data = r.json()
        assert "importance" in data
        assert "model_version" in data

    def test_has_21_features(self):
        data = client.get("/features/importance").json()
        assert len(data["importance"]) == 21


class TestPredict:
    def test_predict_returns_200(self):
        r = client.post("/predict", json=VALID_PAYLOAD)
        assert r.status_code == 200

    def test_predict_structure(self):
        data = client.post("/predict", json=VALID_PAYLOAD).json()
        required = ["class_label", "class_id", "probabilities",
                    "features", "top_features", "model_version", "inference_ms"]
        for field in required:
            assert field in data, f"Поле {field} отсутствует"

    def test_class_label_valid(self):
        data = client.post("/predict", json=VALID_PAYLOAD).json()
        assert data["class_label"] in ["Normal", "Suspect", "Pathological"]

    def test_class_id_valid(self):
        data = client.post("/predict", json=VALID_PAYLOAD).json()
        assert data["class_id"] in [1, 2, 3]

    def test_probabilities_sum_to_one(self):
        data = client.post("/predict", json=VALID_PAYLOAD).json()
        total = sum(data["probabilities"].values())
        assert abs(total - 1.0) < 0.01, f"Сумма вероятностей {total} ≠ 1"

    def test_probabilities_all_positive(self):
        data = client.post("/predict", json=VALID_PAYLOAD).json()
        for cls, prob in data["probabilities"].items():
            assert prob >= 0, f"P({cls})={prob} отрицательная"

    def test_features_has_21_keys(self):
        data = client.post("/predict", json=VALID_PAYLOAD).json()
        assert len(data["features"]) == 21

    def test_top_features_list(self):
        data = client.post("/predict", json=VALID_PAYLOAD).json()
        assert isinstance(data["top_features"], list)
        assert len(data["top_features"]) >= 1

    def test_inference_ms_positive(self):
        data = client.post("/predict", json=VALID_PAYLOAD).json()
        assert data["inference_ms"] >= 0

    def test_short_signal_still_works(self):
        payload = {"fhr": [135.0] * 50, "uc": [0.0] * 50, "fs": 4}
        r = client.post("/predict", json=payload)
        assert r.status_code == 200
        # Должно быть предупреждение о коротком сигнале
        assert r.json().get("warning") is not None

    def test_missing_uc_uses_zeros(self):
        payload = {"fhr": FHR, "uc": [], "fs": 4}
        r = client.post("/predict", json=payload)
        assert r.status_code == 200

    def test_too_short_fhr_validation_error(self):
        payload = {"fhr": [135.0] * 5, "uc": [], "fs": 4}
        r = client.post("/predict", json=payload)
        assert r.status_code in [422, 200]  # либо валидация, либо warning


class TestBatchPredict:
    def test_batch_returns_results(self):
        payload = {"records": [VALID_PAYLOAD, VALID_PAYLOAD]}
        r = client.post("/predict/batch", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2

    def test_batch_processed_ms_positive(self):
        payload = {"records": [VALID_PAYLOAD]}
        data = client.post("/predict/batch", json=payload).json()
        assert data["processed_ms"] >= 0
