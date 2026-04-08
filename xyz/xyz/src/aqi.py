from __future__ import annotations

from typing import Iterable, Tuple


def _aqi_subindex(value: float | None, breakpoints: Iterable[Tuple[float, float, int, int]]) -> float | None:
    if value is None:
        return None
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= val <= c_high:
            if c_high == c_low:
                return float(i_high)
            return ((i_high - i_low) / (c_high - c_low)) * (val - c_low) + i_low
    last = list(breakpoints)[-1]
    return float(last[3])


_PM25_BREAKPOINTS = [
    (0, 30, 0, 50),
    (31, 60, 51, 100),
    (61, 90, 101, 200),
    (91, 120, 201, 300),
    (121, 250, 301, 400),
    (251, 500, 401, 500),
]

_PM10_BREAKPOINTS = [
    (0, 50, 0, 50),
    (51, 100, 51, 100),
    (101, 250, 101, 200),
    (251, 350, 201, 300),
    (351, 430, 301, 400),
    (431, 600, 401, 500),
]


def india_aqi(pm25: float | None, pm10: float | None) -> float | None:
    sub25 = _aqi_subindex(pm25, _PM25_BREAKPOINTS)
    sub10 = _aqi_subindex(pm10, _PM10_BREAKPOINTS)
    if sub25 is None and sub10 is None:
        return None
    values = [v for v in (sub25, sub10) if v is not None]
    return max(values) if values else None


def india_aqi_status(value: float | None) -> tuple[str, float, str]:
    if value is None:
        return "n/a", 0.0, "#94a3b8"
    if value <= 50:
        return "Good", value / 500, "#22c55e"
    if value <= 100:
        return "Satisfactory", value / 500, "#16a34a"
    if value <= 200:
        return "Moderate", value / 500, "#f59e0b"
    if value <= 300:
        return "Poor", value / 500, "#f97316"
    if value <= 400:
        return "Very Poor", value / 500, "#ef4444"
    return "Severe", min(value / 500, 1.0), "#7f1d1d"


def india_aqi_color_rgba(value: float | None) -> list[int]:
    if value is None:
        return [148, 163, 184, 180]
    if value <= 50:
        return [34, 197, 94, 190]
    if value <= 100:
        return [22, 163, 74, 190]
    if value <= 200:
        return [245, 158, 11, 200]
    if value <= 300:
        return [249, 115, 22, 210]
    if value <= 400:
        return [239, 68, 68, 210]
    return [127, 29, 29, 220]
