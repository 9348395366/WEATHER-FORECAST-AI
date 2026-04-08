from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from .data import enrich_features

FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "precipitation",
    "hour",
    "day_of_year",
    "month",
    "lag_1",
    "lag_24",
    "rolling_24h",
]

AQI_FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "precipitation",
    "hour",
    "day_of_year",
    "month",
    "aqi_lag_1",
    "aqi_lag_24",
    "aqi_rolling_24h",
]


def make_supervised(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    data = enrich_features(df)
    data["target_next"] = data["temperature_2m"].shift(-1)
    data = data.dropna().reset_index(drop=True)
    return data[FEATURES], data["target_next"]


def make_aqi_supervised(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    if "aqi" not in df.columns:
        raise ValueError("AQI column not found in dataset.")

    data = df.copy()
    data["time"] = pd.to_datetime(data["time"], errors="coerce")
    data = data.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    data["hour"] = data["time"].dt.hour
    data["day_of_year"] = data["time"].dt.dayofyear
    data["month"] = data["time"].dt.month
    data["aqi_lag_1"] = data["aqi"].shift(1)
    data["aqi_lag_24"] = data["aqi"].shift(24)
    data["aqi_rolling_24h"] = data["aqi"].rolling(24).mean()
    data["target_next"] = data["aqi"].shift(-1)

    data = data.dropna().reset_index(drop=True)
    return data[AQI_FEATURES], data["target_next"]


def train_model(df: pd.DataFrame) -> Tuple[HistGradientBoostingRegressor, Dict[str, float]]:
    features, target = make_supervised(df)
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, random_state=42, shuffle=False
    )
    model = HistGradientBoostingRegressor(
        learning_rate=0.08,
        max_depth=6,
        max_iter=250,
        l2_regularization=0.3,
    )
    model.fit(x_train, y_train)
    preds = model.predict(x_test)
    mae = mean_absolute_error(y_test, preds)
    return model, {"mae": float(mae)}


def train_aqi_model(df: pd.DataFrame) -> Tuple[HistGradientBoostingRegressor, Dict[str, float]]:
    features, target = make_aqi_supervised(df)
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, random_state=42, shuffle=False
    )
    model = HistGradientBoostingRegressor(
        learning_rate=0.07,
        max_depth=5,
        max_iter=220,
        l2_regularization=0.25,
    )
    model.fit(x_train, y_train)
    preds = model.predict(x_test)
    mae = mean_absolute_error(y_test, preds)
    return model, {"mae": float(mae)}


def save_model(model: HistGradientBoostingRegressor, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: Path) -> HistGradientBoostingRegressor | None:
    if not path.exists():
        return None
    return joblib.load(path)


def predict_next_hours(
    model: HistGradientBoostingRegressor,
    history: pd.DataFrame,
    hours: int = 24,
) -> pd.DataFrame:
    history = history.sort_values("time").reset_index(drop=True)
    if len(history) < 48:
        raise ValueError("Need at least 48 hours of history to forecast.")

    forecast_rows: List[Dict[str, float]] = []
    working = history.copy()

    for _ in range(hours):
        last_row = working.iloc[-1]
        next_time = last_row["time"] + dt.timedelta(hours=1)

        candidate = {
            "time": next_time,
            "temperature_2m": float(last_row["temperature_2m"]),
            "relative_humidity_2m": float(last_row["relative_humidity_2m"]),
            "wind_speed_10m": float(last_row["wind_speed_10m"]),
            "precipitation": float(last_row["precipitation"]),
        }

        temp_series = pd.concat(
            [working["temperature_2m"], pd.Series([candidate["temperature_2m"]])],
            ignore_index=True,
        )
        lag_1 = float(temp_series.iloc[-2])
        lag_24 = float(temp_series.iloc[-25])
        rolling_24h = float(temp_series.iloc[-24:].mean())

        features = {
            "temperature_2m": candidate["temperature_2m"],
            "relative_humidity_2m": candidate["relative_humidity_2m"],
            "wind_speed_10m": candidate["wind_speed_10m"],
            "precipitation": candidate["precipitation"],
            "hour": next_time.hour,
            "day_of_year": next_time.timetuple().tm_yday,
            "month": next_time.month,
            "lag_1": lag_1,
            "lag_24": lag_24,
            "rolling_24h": rolling_24h,
        }

        pred = float(model.predict(pd.DataFrame([features]))[0])
        candidate["temperature_2m"] = pred
        forecast_rows.append({"time": next_time, "temperature_2m": pred})

        working = pd.concat([working, pd.DataFrame([candidate])], ignore_index=True)

    return pd.DataFrame(forecast_rows)


def predict_next_hours_aqi(
    model: HistGradientBoostingRegressor,
    history: pd.DataFrame,
    hours: int = 24,
) -> pd.DataFrame:
    history = history.sort_values("time").reset_index(drop=True)
    if len(history) < 48:
        raise ValueError("Need at least 48 hours of AQI history to forecast.")

    if "aqi" not in history.columns:
        raise ValueError("AQI column not found in history.")

    forecast_rows: List[Dict[str, float]] = []
    working = history.copy()

    for _ in range(hours):
        last_row = working.iloc[-1]
        next_time = last_row["time"] + dt.timedelta(hours=1)

        candidate = {
            "time": next_time,
            "temperature_2m": float(last_row["temperature_2m"]),
            "relative_humidity_2m": float(last_row["relative_humidity_2m"]),
            "wind_speed_10m": float(last_row["wind_speed_10m"]),
            "precipitation": float(last_row["precipitation"]),
            "aqi": float(last_row["aqi"]),
        }

        aqi_series = pd.concat(
            [working["aqi"], pd.Series([candidate["aqi"]])],
            ignore_index=True,
        )
        lag_1 = float(aqi_series.iloc[-2])
        lag_24 = float(aqi_series.iloc[-25])
        rolling_24h = float(aqi_series.iloc[-24:].mean())

        features = {
            "temperature_2m": candidate["temperature_2m"],
            "relative_humidity_2m": candidate["relative_humidity_2m"],
            "wind_speed_10m": candidate["wind_speed_10m"],
            "precipitation": candidate["precipitation"],
            "hour": next_time.hour,
            "day_of_year": next_time.timetuple().tm_yday,
            "month": next_time.month,
            "aqi_lag_1": lag_1,
            "aqi_lag_24": lag_24,
            "aqi_rolling_24h": rolling_24h,
        }

        pred = float(model.predict(pd.DataFrame([features]))[0])
        candidate["aqi"] = pred
        forecast_rows.append({"time": next_time, "aqi": pred})

        working = pd.concat([working, pd.DataFrame([candidate])], ignore_index=True)

    return pd.DataFrame(forecast_rows)
