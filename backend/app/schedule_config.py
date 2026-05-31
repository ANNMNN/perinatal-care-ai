from __future__ import annotations

# Recommended days between CTG screenings, keyed by (week_from, week_to) inclusive.
SCREENING_INTERVALS: dict[tuple[int, int], int] = {
    (12, 27): 30,
    (28, 31): 14,
    (32, 36): 10,
    (37, 40): 7,
    (41, 45): 3,
}

DEFAULT_INTERVAL_DAYS = 14


def expected_interval(gestational_week: int | None) -> int:
    if gestational_week is None:
        return DEFAULT_INTERVAL_DAYS
    for (lo, hi), days in SCREENING_INTERVALS.items():
        if lo <= gestational_week <= hi:
            return days
    return DEFAULT_INTERVAL_DAYS
