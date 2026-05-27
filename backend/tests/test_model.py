"""
Тест модели: если модель обучена — проверяем Recall(Pathological) ≥ 0.88.
Если модель не обучена — тест пропускается (не блокирует CI).
"""
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

METRICS_PATH = Path(__file__).parent.parent / "ml" / "models" / "metrics.json"
MODEL_PATH   = Path(__file__).parent.parent / "ml" / "models" / "catboost_v1.cbm"


@pytest.fixture(scope="module")
def metrics():
    if not METRICS_PATH.exists():
        pytest.skip("metrics.json не найден — запусти ml/train.py")
    with open(METRICS_PATH) as f:
        return json.load(f)


class TestModelMetrics:
    def test_model_file_exists(self):
        if not MODEL_PATH.exists():
            pytest.skip("Модель не обучена — запусти ml/train.py")
        assert MODEL_PATH.stat().st_size > 0, "Файл модели пустой"

    def test_recall_pathological_target(self, metrics):
        """ПРИОРИТЕТ: Recall(Pathological) ≥ 0.88"""
        recall = metrics.get("recall_pathological", 0.0)
        assert recall >= 0.88, (
            f"Recall(Pathological) = {recall:.4f} < 0.88 (целевой порог). "
            "Пропуск патологии клинически недопустим!"
        )

    def test_roc_auc_target(self, metrics):
        roc_auc = metrics.get("roc_auc", 0.0)
        assert roc_auc >= 0.89, f"ROC-AUC = {roc_auc:.4f} < 0.89"

    def test_f1_macro_target(self, metrics):
        f1 = metrics.get("f1_macro", 0.0)
        assert f1 >= 0.85, f"F1-macro = {f1:.4f} < 0.85"

    def test_accuracy_reasonable(self, metrics):
        acc = metrics.get("accuracy", 0.0)
        assert acc >= 0.80, f"Accuracy = {acc:.4f} подозрительно низкая"

    def test_metrics_all_present(self, metrics):
        for key in ["roc_auc", "f1_macro", "accuracy", "recall_pathological"]:
            assert key in metrics, f"Метрика {key} отсутствует в metrics.json"
