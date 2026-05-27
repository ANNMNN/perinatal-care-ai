"""
Тесты CTGPipeline: clean, segment, normalize, validate
"""
import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.pipeline import CTGPipeline


@pytest.fixture
def pipe():
    return CTGPipeline()


@pytest.fixture
def normal_fhr():
    """Нормальный синтетический FHR-сигнал 5 минут при 4 Гц."""
    rng = np.random.default_rng(42)
    base = 138.0
    signal = base + 8 * np.sin(np.linspace(0, 10 * np.pi, 1200)) + rng.normal(0, 2, 1200)
    return np.clip(signal, 100, 170)


class TestClean:
    def test_removes_zeros(self, pipe):
        s = np.array([130.0, 0.0, 0.0, 135.0, 140.0])
        cleaned = pipe.clean(s)
        assert np.all(cleaned > 0), "Нули должны быть удалены"

    def test_removes_outliers(self, pipe):
        s = np.full(50, 135.0)
        s[10] = 300.0   # выброс выше FHR_MAX
        s[20] = 10.0    # выброс ниже FHR_MIN
        cleaned = pipe.clean(s)
        assert cleaned.max() <= pipe.FHR_MAX
        assert cleaned.min() >= pipe.FHR_MIN

    def test_interpolates_gaps(self, pipe):
        s = np.array([130.0, 132.0, np.nan, np.nan, 136.0, 138.0])
        cleaned = pipe.clean(s)
        assert not np.any(np.isnan(cleaned))

    def test_no_nan_after_clean(self, pipe, normal_fhr):
        # Добавляем 10% NaN
        noisy = normal_fhr.copy().astype(float)
        noisy[::10] = np.nan
        cleaned = pipe.clean(noisy)
        assert not np.any(np.isnan(cleaned))

    def test_preserves_length(self, pipe, normal_fhr):
        cleaned = pipe.clean(normal_fhr)
        assert len(cleaned) == len(normal_fhr)


class TestSegment:
    def test_default_window(self, pipe, normal_fhr):
        segs = pipe.segment(normal_fhr)
        assert all(len(s) == 240 for s in segs)

    def test_overlap(self, pipe):
        s = np.arange(600, dtype=float)
        segs = pipe.segment(s, window=240, step=120)
        # Ожидаем: (600-240)//120 + 1 = 4 сегмента
        assert len(segs) == 4

    def test_short_signal_returns_itself(self, pipe):
        s = np.arange(100, dtype=float)
        segs = pipe.segment(s, window=240, step=120)
        assert len(segs) == 1
        assert np.array_equal(segs[0], s)


class TestNormalize:
    def test_zero_mean(self, pipe, normal_fhr):
        normed = pipe.normalize(normal_fhr)
        assert abs(np.mean(normed)) < 1e-6

    def test_unit_std(self, pipe, normal_fhr):
        normed = pipe.normalize(normal_fhr)
        assert abs(np.std(normed) - 1.0) < 1e-6

    def test_constant_signal(self, pipe):
        s = np.full(100, 130.0)
        normed = pipe.normalize(s)
        assert np.all(normed == 0.0)


class TestValidate:
    def test_valid_signal(self, pipe, normal_fhr):
        result = pipe.validate(normal_fhr)
        assert result["ok"] is True
        assert result["warnings"] == []

    def test_too_short(self, pipe):
        s = np.full(500, 135.0)
        result = pipe.validate(s)
        assert not result["ok"]
        assert any("короткий" in w or "short" in w.lower() for w in result["warnings"])

    def test_too_many_gaps(self, pipe):
        s = np.full(1200, 135.0).astype(float)
        s[:200] = 0.0   # 16.7% нулей > 10%
        result = pipe.validate(s)
        assert not result["ok"]
        assert result["gap_ratio"] > 0.10

    def test_out_of_range_fhr(self, pipe):
        s = np.full(1200, 220.0)   # выше 200
        result = pipe.validate(s)
        assert not result["ok"]

    def test_gap_ratio_calculated(self, pipe, normal_fhr):
        result = pipe.validate(normal_fhr)
        assert "gap_ratio" in result
        assert 0.0 <= result["gap_ratio"] <= 1.0
