from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from .weather_api import WeatherApiError, coerce_hourly_payload, fetch_historical_archive


def _safe_series(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    series = pd.to_numeric(df.get(column), errors="coerce")
    if series is None:
        return pd.Series([default] * len(df))
    if not isinstance(series, pd.Series):
        series = pd.Series([series] * len(df))
    if series.isna().all():
        return pd.Series([default] * len(df))
    return series.fillna(series.median())


def estimate_aqi_from_weather(df: pd.DataFrame, seed: int = 42) -> pd.Series:
    time_raw = df.get("time")
    if time_raw is None:
        time = pd.Series([pd.NaT] * len(df))
    else:
        time = pd.to_datetime(time_raw, errors="coerce")
    if not isinstance(time, pd.Series):
        time = pd.Series([time] * len(df))
    if time.isna().all():
        time = pd.date_range(dt.datetime.utcnow(), periods=len(df), freq="H")

    day_of_year = time.dt.dayofyear.fillna(180).to_numpy()
    hour = time.dt.hour.fillna(12).to_numpy()

    temp = _safe_series(df, "temperature_2m", 20).to_numpy()
    humidity = _safe_series(df, "relative_humidity_2m", 55).to_numpy()
    wind = _safe_series(df, "wind_speed_10m", 3).to_numpy()
    precip = _safe_series(df, "precipitation", 0).to_numpy()

    seasonal = 12 * np.sin(2 * np.pi * (day_of_year / 365.25))
    daily = 8 * np.cos(2 * np.pi * ((hour - 6) / 24))
    rs = np.random.RandomState(seed)
    noise = rs.normal(0, 7, size=len(df))

    aqi = (
        70
        + 0.45 * temp
        + 0.35 * humidity
        - 1.8 * wind
        - 2.4 * precip
        + seasonal
        + daily
        + noise
    )
    return pd.Series(np.clip(aqi, 15, 320))


def ensure_aqi_column(df: pd.DataFrame) -> pd.DataFrame:
    if "aqi" in df.columns:
        return df
    enriched = df.copy()
    enriched["aqi"] = estimate_aqi_from_weather(enriched)
    return enriched


def generate_synthetic_weather(
    start: dt.datetime,
    end: dt.datetime,
    freq: str = "H",
    seed: int = 42,
) -> pd.DataFrame:
    rng = pd.date_range(start, end, freq=freq, inclusive="left")
    rs = np.random.RandomState(seed)

    day_of_year = rng.dayofyear.values
    hour = rng.hour.values

    seasonal = 12 + 14 * np.sin(2 * np.pi * (day_of_year / 365.25))
    daily = 5 * np.sin(2 * np.pi * ((hour - 5) / 24))
    noise = rs.normal(0, 2.5, size=len(rng))

    temperature = seasonal + daily + noise
    humidity = np.clip(60 - 0.25 * temperature + rs.normal(0, 8, size=len(rng)), 15, 100)
    wind_speed = np.clip(4 + rs.gamma(2.0, 1.2, size=len(rng)), 0, 20)

    precip_chance = np.clip(0.15 + 0.2 * np.sin(2 * np.pi * (day_of_year / 365.25) + 1.5), 0.02, 0.6)
    precipitation = rs.gamma(1.2, 1.5, size=len(rng)) * (rs.rand(len(rng)) < precip_chance)

    df = pd.DataFrame(
        {
            "time": rng,
            "temperature_2m": temperature,
            "relative_humidity_2m": humidity,
            "wind_speed_10m": wind_speed,
            "precipitation": precipitation,
        }
    )

    df = ensure_aqi_column(df)
    return df


def load_or_generate_dataset(
    path: Path,
    latitude: float = 28.6139,
    longitude: float = 77.2090,
    years: int = 8,
    source: str = "auto",
) -> Tuple[pd.DataFrame, str]:
    if path.exists():
        df = pd.read_csv(path, parse_dates=["time"])
        if "aqi" not in df.columns:
            df = ensure_aqi_column(df)
            df.to_csv(path, index=False)
            return df, "loaded+aqi"
        return df, "loaded"

    end_date = dt.datetime.utcnow().date() - dt.timedelta(days=1)
    start_date = end_date - dt.timedelta(days=365 * min(years, 5))

    if source in {"auto", "archive"}:
        try:
            payload = fetch_historical_archive(latitude, longitude, start_date, end_date)
            times, fields = coerce_hourly_payload(payload)
            if times:
                df = pd.DataFrame({"time": times, **fields})
                df = ensure_aqi_column(df)
                df.to_csv(path, index=False)
                return df, "archive"
        except WeatherApiError:
            if source == "archive":
                raise

    start = dt.datetime.utcnow() - dt.timedelta(days=365 * years)
    df = generate_synthetic_weather(start, dt.datetime.utcnow())
    df = ensure_aqi_column(df)
    df.to_csv(path, index=False)
    return df, "synthetic"


def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data = data.sort_values("time").reset_index(drop=True)
    data["hour"] = data["time"].dt.hour
    data["day_of_year"] = data["time"].dt.dayofyear
    data["month"] = data["time"].dt.month
    data["lag_1"] = data["temperature_2m"].shift(1)
    data["lag_24"] = data["temperature_2m"].shift(24)
    data["rolling_24h"] = data["temperature_2m"].rolling(24).mean()
    data = data.dropna().reset_index(drop=True)
    return data


def summarize_dataset(df: pd.DataFrame) -> Dict[str, object]:
    return {
        "rows": len(df),
        "start": df["time"].min(),
        "end": df["time"].max(),
        "columns": list(df.columns),
    }
