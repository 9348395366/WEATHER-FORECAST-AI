from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from .data import load_or_generate_dataset
from .modeling import load_model
from .weather_api import (
    fetch_astronomy,
    fetch_air_quality_current,
    fetch_air_quality_best,
    fetch_air_quality_dual,
    fetch_current_weather,
    fetch_daily_forecast,
    fetch_forecast_bundle,
    fetch_hourly_forecast,
    forward_geocode,
    reverse_geocode,
)

DATA_PATH = Path("data/historical_weather.csv")
MODEL_PATH = Path("models/temperature_model.pkl")
METRICS_PATH = Path("models/metrics.json")
AQI_MODEL_PATH = Path("models/aqi_model.pkl")
AQI_METRICS_PATH = Path("models/aqi_metrics.json")


@st.cache_data(ttl=60)
def cached_current(lat: float, lon: float) -> dict:
    return fetch_current_weather(lat, lon)


@st.cache_data(ttl=300)
def cached_hourly(lat: float, lon: float, days: int) -> dict:
    return fetch_hourly_forecast(lat, lon, days)


@st.cache_data(ttl=300)
def cached_daily(lat: float, lon: float, days: int) -> dict:
    return fetch_daily_forecast(lat, lon, days)


@st.cache_data(ttl=60)
def cached_air_quality(lat: float, lon: float, timezone: str = "auto", openweather_key: str | None = None) -> dict:
    return fetch_air_quality_best(lat, lon, timezone=timezone, openweather_key=openweather_key)

@st.cache_data(ttl=60)
def cached_air_quality_dual(lat: float, lon: float, timezone: str = "auto", openweather_key: str | None = None) -> dict:
    return fetch_air_quality_dual(lat, lon, timezone=timezone, openweather_key=openweather_key)


@st.cache_data(ttl=1800)
def cached_astronomy(lat: float, lon: float, timezone: str = "auto") -> dict:
    return fetch_astronomy(lat, lon, timezone=timezone)


@st.cache_data(ttl=60)
def cached_forecast_bundle(
    lat: float,
    lon: float,
    days: int = 7,
    include_current: bool = True,
    include_hourly: bool = True,
    include_daily: bool = True,
    openweather_key: str | None = None,
    prefer_openweather: bool = False,
    timezone: str = "auto",
    blend_sources: bool = True,
) -> dict:
    return fetch_forecast_bundle(
        lat,
        lon,
        days=days,
        include_current=include_current,
        include_hourly=include_hourly,
        include_daily=include_daily,
        openweather_key=openweather_key,
        prefer_openweather=prefer_openweather,
        timezone=timezone,
        blend_sources=blend_sources,
    )


@st.cache_data(ttl=21600)
def cached_reverse_geocode(lat: float, lon: float) -> str | None:
    return reverse_geocode(lat, lon)


@st.cache_data(ttl=21600)
def cached_forward_geocode(query: str) -> tuple[float, float] | None:
    return forward_geocode(query)


@st.cache_data(ttl=3600)
def cached_dataset() -> tuple[pd.DataFrame, str]:
    return load_or_generate_dataset(DATA_PATH)


@st.cache_resource
def cached_model():
    return load_model(MODEL_PATH)


@st.cache_resource
def cached_aqi_model():
    return load_model(AQI_MODEL_PATH)


def load_metrics() -> dict | None:
    if not METRICS_PATH.exists():
        return None
    return json.loads(METRICS_PATH.read_text())


def load_aqi_metrics() -> dict | None:
    if not AQI_METRICS_PATH.exists():
        return None
    return json.loads(AQI_METRICS_PATH.read_text())
