"""
Тесты extract_figo_features на синтетических данных
"""
import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.features import extract_figo_features, FEATURE_ORDER


@pytest.fixture
def normal_fhr():
    rng = np.random.default_rng(0)
    base = 138.0
    s = base + 8 * np.sin(np.linspace(0, 6 * np.pi, 1200))
    s += rng.normal(0, 2, 1200)
    return np.clip(s, 110, 165)


@pytest.fixture
def flat_fhr():
    """Монотонный сигнал — нет акцелераций/децелераций."""
    return np.full(1200, 135.0)


@pytest.fixture
def uc_signal():
    """UC: 2 гауссовы волны."""
    t = np.linspace(0, 300, 1200)
    return (25 * np.exp(-0.5 * ((t - 60) / 15) ** 2) +
            22 * np.exp(-0.5 * ((t - 200) / 12) ** 2))


class TestFeatureExtraction:
    def test_returns_all_21_features(self, normal_fhr, uc_signal):
        feats = extract_figo_features(normal_fhr, uc_signal)
        assert len(feats) == 21, f"Ожидаем 21 признак, получили {len(feats)}"

    def test_all_feature_keys_present(self, normal_fhr, uc_signal):
        feats = extract_figo_features(normal_fhr, uc_signal)
        for key in FEATURE_ORDER:
            assert key in feats, f"Признак {key} отсутствует"

    def test_all_float_values(self, normal_fhr, uc_signal):
        feats = extract_figo_features(normal_fhr, uc_signal)
        for k, v in feats.items():
            assert isinstance(v, float), f"{k}: ожидается float, получили {type(v)}"

    def test_no_nan_or_inf(self, normal_fhr, uc_signal):
        feats = extract_figo_features(normal_fhr, uc_signal)
        for k, v in feats.items():
            assert np.isfinite(v), f"{k} = {v} не является конечным числом"

    def test_baseline_in_range(self, normal_fhr):
        feats = extract_figo_features(normal_fhr)
        assert 50 <= feats["LB"] <= 200, f"LB={feats['LB']} вне допустимого диапазона"

    def test_mean_close_to_baseline(self, flat_fhr):
        feats = extract_figo_features(flat_fhr)
        assert abs(feats["Mean"] - 135.0) < 1.0
        assert abs(feats["LB"]  - 135.0) < 5.0
        assert abs(feats["Median"] - 135.0) < 1.0

    def test_zero_variance_flat(self, flat_fhr):
        feats = extract_figo_features(flat_fhr)
        assert feats["Variance"] < 1.0

    def test_accelerations_nonnegative(self, normal_fhr):
        feats = extract_figo_features(normal_fhr)
        assert feats["AC"] >= 0

    def test_decelerations_nonnegative(self, normal_fhr, uc_signal):
        feats = extract_figo_features(normal_fhr, uc_signal)
        for key in ["DL", "DS", "DP", "DR"]:
            assert feats[key] >= 0, f"{key} отрицательный"

    def test_histogram_width_positive(self, normal_fhr):
        feats = extract_figo_features(normal_fhr)
        assert feats["Width"] >= 0

    def test_min_less_than_max(self, normal_fhr):
        feats = extract_figo_features(normal_fhr)
        assert feats["Min"] <= feats["Max"]

    def test_works_without_uc(self, normal_fhr):
        feats = extract_figo_features(normal_fhr)
        assert len(feats) == 21

    def test_works_with_empty_uc(self, normal_fhr):
        feats = extract_figo_features(normal_fhr, uc=np.array([]))
        assert len(feats) == 21

    def test_mode_in_fhr_range(self, normal_fhr):
        feats = extract_figo_features(normal_fhr)
        assert 50 <= feats["Mode"] <= 200
