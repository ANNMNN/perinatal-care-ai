"""
Извлечение 21 FIGO-признака из КТГ-сигнала.
Соответствует UCI CTG Dataset feature set.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as scipy_stats

# Canonical feature order (matches UCI CTG dataset columns)
FEATURE_ORDER = [
    "LB", "AC", "FM", "UC", "ASTV", "MSTV", "ALTV", "MLTV",
    "DL", "DS", "DP", "DR", "Width", "Min", "Max",
    "Nmax", "Nzeros", "Mode", "Mean", "Median", "Variance",
]

# ────────────────────────────────────────────────────────────────────── #
#  Вспомогательные функции
# ────────────────────────────────────────────────────────────────────── #

def _baseline_fhr(fhr: np.ndarray) -> float:
    """Базальный ритм: скользящая медиана 10-секундных окон (при fs=4 → 40 отсч.)"""
    window = 40
    if len(fhr) < window:
        return float(np.median(fhr))
    medians = [np.median(fhr[i:i+window]) for i in range(0, len(fhr)-window+1, window//2)]
    return float(np.median(medians))


def _count_accelerations(fhr: np.ndarray, fs: int = 4,
                          amp_thresh: float = 15.0, dur_thresh_s: float = 15.0) -> int:
    """Акцелерации: подъём ≥15 уд/мин длительностью ≥15 сек."""
    baseline = _baseline_fhr(fhr)
    dur_thresh = int(dur_thresh_s * fs)
    above = fhr > (baseline + amp_thresh)
    count = 0
    run = 0
    in_acc = False
    for v in above:
        if v:
            run += 1
            if run >= dur_thresh and not in_acc:
                count += 1
                in_acc = True
        else:
            run = 0
            in_acc = False
    return count


def _fetal_movements(fhr: np.ndarray, fs: int = 4) -> int:
    """Движения плода: число коротких акцелераций (≥10 уд/мин, ≥5 сек)."""
    baseline = _baseline_fhr(fhr)
    dur_thresh = int(5 * fs)
    above = fhr > (baseline + 10)
    count = 0
    run = 0
    in_fm = False
    for v in above:
        if v:
            run += 1
            if run >= dur_thresh and not in_fm:
                count += 1
                in_fm = True
        else:
            run = 0
            in_fm = False
    return count


def _uterine_contractions(uc: np.ndarray, fs: int = 4,
                           amp_thresh: float = 10.0, dur_thresh_s: float = 20.0) -> int:
    """Число маточных сокращений."""
    if uc is None or len(uc) == 0:
        return 0
    dur_thresh = int(dur_thresh_s * fs)
    above = uc > amp_thresh
    count = 0
    run = 0
    in_uc = False
    for v in above:
        if v:
            run += 1
            if run >= dur_thresh and not in_uc:
                count += 1
                in_uc = True
        else:
            run = 0
            in_uc = False
    return count


def _short_term_variability(fhr: np.ndarray, fs: int = 4) -> float:
    """STV: среднее |diff| на интервалах ~0.25 сек."""
    step = max(1, fs // 4)
    diffs = np.abs(np.diff(fhr[::step]))
    return float(np.mean(diffs)) if len(diffs) > 0 else 0.0


def _mean_stv(fhr: np.ndarray, fs: int = 4) -> float:
    """Mean STV: среднее STV по 1-минутным сегментам."""
    seg_len = fs * 60
    if len(fhr) < seg_len:
        return _short_term_variability(fhr, fs)
    stvs = [_short_term_variability(fhr[i:i+seg_len], fs)
            for i in range(0, len(fhr)-seg_len+1, seg_len)]
    return float(np.mean(stvs))


def _long_term_variability(fhr: np.ndarray, fs: int = 4) -> float:
    """LTV: размах (max - min) в 1-минутных скользящих окнах."""
    window = fs * 60
    if len(fhr) < window:
        return float(np.ptp(fhr))
    ranges = [np.ptp(fhr[i:i+window]) for i in range(0, len(fhr)-window+1, window//2)]
    return float(np.mean(ranges))


def _mean_ltv(fhr: np.ndarray, fs: int = 4) -> float:
    """Mean LTV по сегментам."""
    return _long_term_variability(fhr, fs)


def _late_decels(fhr: np.ndarray, uc: np.ndarray, fs: int = 4) -> int:
    """Поздние децелерации: спад ЧСС через ≥20 сек после пика UC."""
    if uc is None or len(uc) < 2 or len(fhr) < 2:
        return 0
    min_len = min(len(fhr), len(uc))
    fhr = fhr[:min_len]
    uc = uc[:min_len]
    lag = int(20 * fs)
    count = 0
    baseline = _baseline_fhr(fhr)
    for i in range(len(uc) - lag):
        if uc[i] > 10 and (i + lag) < len(fhr):
            if fhr[i + lag] < baseline - 15:
                count += 1
    return min(count, 20)


def _severe_decels(fhr: np.ndarray, fs: int = 4,
                   amp_thresh: float = 60.0, dur_thresh_s: float = 2.0) -> int:
    """Тяжёлые децелерации: спад ≥60 уд/мин длительностью ≥2 сек."""
    baseline = _baseline_fhr(fhr)
    dur_thresh = int(dur_thresh_s * fs)
    below = fhr < (baseline - amp_thresh)
    count = 0
    run = 0
    in_dec = False
    for v in below:
        if v:
            run += 1
            if run >= dur_thresh and not in_dec:
                count += 1
                in_dec = True
        else:
            run = 0
            in_dec = False
    return count


def _prolonged_decels(fhr: np.ndarray, fs: int = 4,
                      amp_thresh: float = 15.0, dur_thresh_s: float = 120.0) -> int:
    """Пролонгированные децелерации: ≥15 уд/мин, ≥120 сек."""
    baseline = _baseline_fhr(fhr)
    dur_thresh = int(dur_thresh_s * fs)
    below = fhr < (baseline - amp_thresh)
    count = 0
    run = 0
    in_dec = False
    for v in below:
        if v:
            run += 1
            if run >= dur_thresh and not in_dec:
                count += 1
                in_dec = True
        else:
            run = 0
            in_dec = False
    return count


def _repetitive_decels(fhr: np.ndarray, uc: np.ndarray, fs: int = 4) -> int:
    """Повторяющиеся децелерации: связанные с сокращениями матки."""
    if uc is None or len(uc) < 2:
        return 0
    min_len = min(len(fhr), len(uc))
    fhr = fhr[:min_len]
    uc = uc[:min_len]
    baseline = _baseline_fhr(fhr)
    uc_peaks = (np.diff(uc) < 0) & (uc[:-1] > 10)
    count = 0
    window = int(30 * fs)
    for i in np.where(uc_peaks)[0]:
        segment = fhr[i:min(i+window, len(fhr))]
        if len(segment) > 0 and segment.min() < baseline - 15:
            count += 1
    return count


def _histogram_width(fhr: np.ndarray) -> float:
    """Ширина гистограммы FHR (p95 - p5)."""
    return float(np.percentile(fhr, 95) - np.percentile(fhr, 5))


def _histogram_peaks(fhr: np.ndarray) -> int:
    """Число пиков в гистограмме FHR (грубая оценка)."""
    hist, _ = np.histogram(fhr.astype(int), bins=range(50, 201, 5))
    peaks = 0
    for j in range(1, len(hist)-1):
        if hist[j] > hist[j-1] and hist[j] > hist[j+1] and hist[j] > 2:
            peaks += 1
    return max(1, peaks)


def _histogram_zeros(fhr: np.ndarray) -> int:
    """Число нулевых бинов в гистограмме."""
    hist, _ = np.histogram(fhr.astype(int), bins=range(50, 201, 5))
    return int(np.sum(hist == 0))


# ────────────────────────────────────────────────────────────────────── #
#  Основная функция
# ────────────────────────────────────────────────────────────────────── #

def extract_figo_features(
    fhr: np.ndarray,
    uc: np.ndarray | None = None,
    fs: int = 4,
) -> dict[str, float]:
    """
    Извлекает 21 FIGO-признак из сигналов FHR и UC.

    Args:
        fhr: Массив ЧСС плода (уд/мин)
        uc:  Массив маточной активности (опционально)
        fs:  Частота дискретизации (Гц), по умолчанию 4

    Returns:
        Словарь 21 признака (float)
    """
    fhr = np.asarray(fhr, dtype=float)
    if uc is None or len(uc) == 0:
        uc = np.zeros(len(fhr))
    else:
        uc = np.asarray(uc, dtype=float)

    mode_val = float(
        scipy_stats.mode(fhr.astype(int), keepdims=True).mode[0]
    )

    return {
        "LB":       _baseline_fhr(fhr),
        "AC":       float(_count_accelerations(fhr, fs)),
        "FM":       float(_fetal_movements(fhr, fs)),
        "UC":       float(_uterine_contractions(uc, fs)),
        "ASTV":     _short_term_variability(fhr, fs),
        "MSTV":     _mean_stv(fhr, fs),
        "ALTV":     _long_term_variability(fhr, fs),
        "MLTV":     _mean_ltv(fhr, fs),
        "DL":       float(_late_decels(fhr, uc, fs)),
        "DS":       float(_severe_decels(fhr, fs)),
        "DP":       float(_prolonged_decels(fhr, fs)),
        "DR":       float(_repetitive_decels(fhr, uc, fs)),
        "Width":    _histogram_width(fhr),
        "Min":      float(np.min(fhr)),
        "Max":      float(np.max(fhr)),
        "Nmax":     float(_histogram_peaks(fhr)),
        "Nzeros":   float(_histogram_zeros(fhr)),
        "Mode":     mode_val,
        "Mean":     float(np.mean(fhr)),
        "Median":   float(np.median(fhr)),
        "Variance": float(np.var(fhr)),
    }
