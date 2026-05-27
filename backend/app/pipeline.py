"""
CTGPipeline — предобработка КТГ-сигнала:
  clean()    — удаление артефактов (IQR-выбросы, нулевые сегменты, интерполяция)
  segment()  — нарезка на перекрывающиеся окна
  normalize()— Z-нормализация
  validate() — проверка качества сигнала
"""
import numpy as np
from scipy.interpolate import interp1d


class CTGPipeline:
    FHR_MIN = 50.0
    FHR_MAX = 200.0
    MAX_GAP_RATIO = 0.10  # максимум 10% пропусков

    # ------------------------------------------------------------------ #
    def clean(self, signal: np.ndarray) -> np.ndarray:
        """
        1. Нулевые/отрицательные значения → NaN
        2. IQR-выбросы → NaN
        3. Линейная интерполяция пропусков
        4. Edge NaN → fill с ближайшим значением
        """
        s = signal.astype(float).copy()

        # Нулевые и внедиапазонные значения
        s[(s <= 0) | (s < self.FHR_MIN) | (s > self.FHR_MAX)] = np.nan

        # IQR-выбросы
        q1, q3 = np.nanpercentile(s, [25, 75])
        iqr = q3 - q1
        s[(s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)] = np.nan

        # Интерполяция
        nan_mask = np.isnan(s)
        if nan_mask.any():
            idx = np.arange(len(s))
            valid = ~nan_mask
            if valid.sum() >= 2:
                f = interp1d(idx[valid], s[valid], kind="linear",
                             bounds_error=False, fill_value="extrapolate")
                s[nan_mask] = f(idx[nan_mask])
            else:
                s = np.where(nan_mask, np.nanmean(s) if np.any(~nan_mask) else 140.0, s)

        # Clip после интерполяции
        s = np.clip(s, self.FHR_MIN, self.FHR_MAX)
        return s

    # ------------------------------------------------------------------ #
    def segment(
        self,
        signal: np.ndarray,
        window: int = 240,
        step: int = 120,
    ) -> list[np.ndarray]:
        """
        Нарезка на перекрывающиеся окна.
        window=240 → 4 Гц × 60 сек = 240 отсчётов
        step=120   → 50% перекрытие
        """
        segments = []
        n = len(signal)
        start = 0
        while start + window <= n:
            segments.append(signal[start : start + window])
            start += step
        return segments if segments else [signal]

    # ------------------------------------------------------------------ #
    def normalize(self, signal: np.ndarray) -> np.ndarray:
        """Z-нормализация (μ=0, σ=1)"""
        mu = np.mean(signal)
        sigma = np.std(signal)
        if sigma < 1e-8:
            return signal - mu
        return (signal - mu) / sigma

    # ------------------------------------------------------------------ #
    def validate(self, signal: np.ndarray) -> dict:
        """
        Проверки:
          - длина ≥ 1200 отсчётов (5 мин при 4 Гц)
          - не более 10% пропусков/нулей
          - ЧСС в диапазоне 50–200 уд/мин
        Возвращает: {ok: bool, warnings: list[str], gap_ratio: float}
        """
        warnings = []
        s = np.asarray(signal, dtype=float)

        # 1) Длина
        if len(s) < 1200:
            warnings.append(
                f"Сигнал слишком короткий ({len(s)} отсч.); рекомендуется ≥ 1200 (5 мин при 4 Гц)"
            )

        # 2) Пропуски / нули
        bad = np.sum((s <= 0) | np.isnan(s) | (s < self.FHR_MIN) | (s > self.FHR_MAX))
        gap_ratio = float(bad) / len(s) if len(s) > 0 else 1.0
        if gap_ratio > self.MAX_GAP_RATIO:
            warnings.append(
                f"Доля артефактов/пропусков {gap_ratio:.1%} превышает допустимые 10%"
            )

        # 3) Диапазон ЧСС
        valid = s[(s > 0) & ~np.isnan(s)]
        if len(valid) > 0:
            if valid.min() < self.FHR_MIN:
                warnings.append(f"ЧСС ниже нормы ({valid.min():.0f} < {self.FHR_MIN} уд/мин)")
            if valid.max() > self.FHR_MAX:
                warnings.append(f"ЧСС выше нормы ({valid.max():.0f} > {self.FHR_MAX} уд/мин)")

        return {
            "ok": len(warnings) == 0,
            "warnings": warnings,
            "gap_ratio": gap_ratio,
            "length": len(s),
        }
