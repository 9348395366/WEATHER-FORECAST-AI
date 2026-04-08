from __future__ import annotations

import datetime as dt
from typing import Dict, List, Tuple

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
REVERSE_GEOCODE_URL = "https://nominatim.openstreetmap.org/reverse"
FORWARD_GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
OPENWEATHER_URL = "https://api.openweathermap.org/data/3.0/onecall"
OPENWEATHER_AIR_URL = "https://api.openweathermap.org/data/2.5/air_pollution"


CURRENT_FIELDS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,weather_code,visibility,surface_pressure,cloud_cover"
HOURLY_FIELDS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,weather_code,visibility,surface_pressure,precipitation_probability,cloud_cover"
DAILY_FIELDS = "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max,sunrise,sunset,moonrise,moonset"
DAILY_FIELDS_FALLBACK = "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max,sunrise,sunset"
ASTRO_FIELDS = "sunrise,sunset,moonrise,moonset"

class WeatherApiError(RuntimeError):
    pass




def _openweather_to_wmo(code: int | None) -> int | None:
    if code is None:
        return None
    if 200 <= code < 300:
        return 95
    if 300 <= code < 400:
        return 51
    if 500 <= code < 600:
        return 80 if code >= 520 else 61
    if 600 <= code < 700:
        return 71
    if 700 <= code < 800:
        return 45
    if code == 800:
        return 0
    if code == 801:
        return 1
    if code == 802:
        return 2
    if code >= 803:
        return 3
    return None


def _to_local_iso(ts: int | None, offset_seconds: int) -> str | None:
    if ts is None:
        return None
    tz = dt.timezone(dt.timedelta(seconds=offset_seconds))
    return dt.datetime.fromtimestamp(ts, tz=tz).isoformat()


def _parse_iso(ts: str | None) -> dt.datetime | None:
    if not ts:
        return None
    try:
        return dt.datetime.fromisoformat(ts)
    except ValueError:
        return None


def _merge_current(primary: dict, secondary: dict) -> dict:
    merged = {}
    fields = [
        "time",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
        "wind_direction_10m",
        "weather_code",
        "visibility",
        "surface_pressure",
        "cloud_cover",
    ]
    for key in fields:
        value = primary.get(key)
        if value is None or value == "n/a":
            value = secondary.get(key)
        merged[key] = value
    return merged


def _pick_preferred_bundle(bundle_a: dict, bundle_b: dict) -> dict:
    current_a = bundle_a.get("current") if isinstance(bundle_a, dict) else None
    current_b = bundle_b.get("current") if isinstance(bundle_b, dict) else None
    time_a = _parse_iso(current_a.get("time")) if isinstance(current_a, dict) else None
    time_b = _parse_iso(current_b.get("time")) if isinstance(current_b, dict) else None
    if time_a and time_b:
        return bundle_a if time_a >= time_b else bundle_b
    if time_a and not time_b:
        return bundle_a
    if time_b and not time_a:
        return bundle_b
    return bundle_a


def _merge_bundles(bundle_a: dict, bundle_b: dict) -> dict:
    preferred = _pick_preferred_bundle(bundle_a, bundle_b)
    secondary = bundle_b if preferred is bundle_a else bundle_a
    merged: Dict[str, object] = {}

    current_a = preferred.get("current") if isinstance(preferred, dict) else {}
    current_b = secondary.get("current") if isinstance(secondary, dict) else {}
    if isinstance(current_a, dict) or isinstance(current_b, dict):
        merged["current"] = _merge_current(current_a or {}, current_b or {})

    hourly_a = preferred.get("hourly") if isinstance(preferred, dict) else {}
    hourly_b = secondary.get("hourly") if isinstance(secondary, dict) else {}
    if isinstance(hourly_a, dict) and hourly_a.get("time"):
        merged["hourly"] = hourly_a
    elif isinstance(hourly_b, dict):
        merged["hourly"] = hourly_b

    daily_a = preferred.get("daily") if isinstance(preferred, dict) else {}
    daily_b = secondary.get("daily") if isinstance(secondary, dict) else {}
    if isinstance(daily_a, dict) and daily_a.get("time"):
        merged["daily"] = daily_a
    elif isinstance(daily_b, dict):
        merged["daily"] = daily_b

    return merged

    if ts is None:
        return None
    tz = dt.timezone(dt.timedelta(seconds=offset_seconds))
    return dt.datetime.fromtimestamp(ts, tz=tz).isoformat()


def _openweather_precip(entry: dict) -> float:
    rain = entry.get('rain', {}) if isinstance(entry.get('rain'), dict) else {}
    snow = entry.get('snow', {}) if isinstance(entry.get('snow'), dict) else {}
    rain_val = rain.get('1h') or rain.get('3h') or 0.0
    snow_val = snow.get('1h') or snow.get('3h') or 0.0
    try:
        return float(rain_val) + float(snow_val)
    except (TypeError, ValueError):
        return 0.0


def fetch_openweather_bundle(
    latitude: float,
    longitude: float,
    days: int = 7,
    include_current: bool = True,
    include_hourly: bool = True,
    include_daily: bool = True,
    api_key: str | None = None,
) -> Dict[str, object]:
    if not api_key:
        raise WeatherApiError("OpenWeatherMap API key is missing.")

    exclude_parts = ["minutely", "alerts"]
    if not include_current:
        exclude_parts.append("current")
    if not include_hourly:
        exclude_parts.append("hourly")
    if not include_daily:
        exclude_parts.append("daily")

    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": api_key,
        "units": "metric",
        "exclude": ",".join(exclude_parts),
    }

    data = _request_json(OPENWEATHER_URL, params)
    if not isinstance(data, dict):
        raise WeatherApiError("Unexpected OpenWeatherMap response.")

    offset = int(data.get("timezone_offset") or 0)
    bundle: Dict[str, object] = {}

    if include_current:
        current = data.get("current", {}) if isinstance(data.get("current"), dict) else {}
        weather = (current.get("weather") or [{}])[0] if isinstance(current.get("weather"), list) else {}
        bundle["current"] = {
            "time": _to_local_iso(current.get("dt"), offset),
            "temperature_2m": current.get("temp"),
            "relative_humidity_2m": current.get("humidity"),
            "precipitation": _openweather_precip(current),
            "wind_speed_10m": current.get("wind_speed"),
            "wind_direction_10m": current.get("wind_deg"),
            "weather_code": _openweather_to_wmo(weather.get("id")),
            "visibility": current.get("visibility"),
            "surface_pressure": current.get("pressure"),
            "cloud_cover": current.get("clouds"),
        }

    if include_hourly:
        hourly_list = data.get("hourly", []) if isinstance(data.get("hourly"), list) else []
        hourly_list = hourly_list[: max(0, min(len(hourly_list), days * 24))]
        hourly = {
            "time": [],
            "temperature_2m": [],
            "relative_humidity_2m": [],
            "precipitation": [],
            "wind_speed_10m": [],
            "wind_direction_10m": [],
            "weather_code": [],
            "visibility": [],
            "surface_pressure": [],
            "cloud_cover": [],
            "precipitation_probability": [],
        }
        for entry in hourly_list:
            weather = (entry.get("weather") or [{}])[0] if isinstance(entry.get("weather"), list) else {}
            hourly["time"].append(_to_local_iso(entry.get("dt"), offset))
            hourly["temperature_2m"].append(entry.get("temp"))
            hourly["relative_humidity_2m"].append(entry.get("humidity"))
            hourly["precipitation"].append(_openweather_precip(entry))
            hourly["wind_speed_10m"].append(entry.get("wind_speed"))
            hourly["wind_direction_10m"].append(entry.get("wind_deg"))
            hourly["weather_code"].append(_openweather_to_wmo(weather.get("id")))
            hourly["visibility"].append(entry.get("visibility"))
            hourly["surface_pressure"].append(entry.get("pressure"))
            hourly["cloud_cover"].append(entry.get("clouds"))
            pop = entry.get("pop")
            hourly["precipitation_probability"].append(pop * 100 if isinstance(pop, (int, float)) else None)
        bundle["hourly"] = hourly

    if include_daily:
        daily_list = data.get("daily", []) if isinstance(data.get("daily"), list) else []
        daily_list = daily_list[: max(0, min(len(daily_list), days))]
        daily = {
            "time": [],
            "temperature_2m_max": [],
            "temperature_2m_min": [],
            "weather_code": [],
            "precipitation_probability_max": [],
            "sunrise": [],
            "sunset": [],
            "moonrise": [],
            "moonset": [],
        }
        for entry in daily_list:
            weather = (entry.get("weather") or [{}])[0] if isinstance(entry.get("weather"), list) else {}
            daily["time"].append(_to_local_iso(entry.get("dt"), offset))
            daily["sunrise"].append(_to_local_iso(entry.get("sunrise"), offset))
            daily["sunset"].append(_to_local_iso(entry.get("sunset"), offset))
            daily["moonrise"].append(_to_local_iso(entry.get("moonrise"), offset))
            daily["moonset"].append(_to_local_iso(entry.get("moonset"), offset))
            temp = entry.get("temp") or {}
            daily["temperature_2m_max"].append(temp.get("max"))
            daily["temperature_2m_min"].append(temp.get("min"))
            daily["weather_code"].append(_openweather_to_wmo(weather.get("id")))
            pop = entry.get("pop")
            daily["precipitation_probability_max"].append(pop * 100 if isinstance(pop, (int, float)) else None)
        bundle["daily"] = daily

    return bundle


def fetch_openweather_air_quality(
    latitude: float,
    longitude: float,
    api_key: str | None = None,
) -> Dict[str, object]:
    if not api_key:
        raise WeatherApiError("OpenWeatherMap API key is missing.")

    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": api_key,
    }
    data = _request_json(OPENWEATHER_AIR_URL, params)
    if not isinstance(data, dict):
        raise WeatherApiError("Unexpected OpenWeatherMap air quality response.")

    items = data.get("list") if isinstance(data.get("list"), list) else []
    if not items:
        return {}
    entry = items[0]
    main = entry.get("main") if isinstance(entry.get("main"), dict) else {}
    components = entry.get("components") if isinstance(entry.get("components"), dict) else {}
    ts = entry.get("dt")

    return {
        "time": _to_local_iso(ts, 0) if ts is not None else None,
        "us_aqi": main.get("aqi"),
        "european_aqi": None,
        "uv_index": None,
        "uv_index_clear_sky": None,
        "pm2_5": components.get("pm2_5"),
        "pm10": components.get("pm10"),
    }


def _aqi_score(payload: Dict[str, object]) -> float:
    if not isinstance(payload, dict) or not payload:
        return 0.0
    score = 0.0

    def _has(key: str) -> bool:
        return payload.get(key) is not None

    if _has("us_aqi"):
        score += 3.0
        try:
            val = float(payload.get("us_aqi"))
            if 0 < val <= 5:
                score -= 1.5
        except (TypeError, ValueError):
            pass
    if _has("european_aqi"):
        score += 1.0
    if _has("pm2_5"):
        score += 2.0
    if _has("pm10"):
        score += 1.5
    if _has("uv_index"):
        score += 0.5
    if _has("time"):
        score += 0.25
    return score


def _aqi_source_meta(payload: Dict[str, object], source: str) -> Dict[str, object]:
    meta: Dict[str, object] = {"source": source}
    if not isinstance(payload, dict) or not payload:
        return meta
    if source == "OpenWeather":
        try:
            val = float(payload.get("us_aqi"))
            if 0 < val <= 5:
                meta["aqi_index"] = True
        except (TypeError, ValueError):
            pass
    return meta


def choose_best_air_quality(
    open_meteo: Dict[str, object] | None,
    open_weather: Dict[str, object] | None,
) -> Dict[str, object]:
    open_meteo = open_meteo if isinstance(open_meteo, dict) else {}
    open_weather = open_weather if isinstance(open_weather, dict) else {}

    score_m = _aqi_score(open_meteo)
    score_w = _aqi_score(open_weather)

    if score_m == 0 and score_w == 0:
        best_source = ""
        best = {}
    elif score_m >= score_w:
        best_source = "Open-Meteo"
        best = open_meteo
    else:
        best_source = "OpenWeather"
        best = open_weather

    return {
        "best": best,
        "best_source": best_source,
        "scores": {"Open-Meteo": score_m, "OpenWeather": score_w},
        "sources": {"Open-Meteo": open_meteo, "OpenWeather": open_weather},
        "meta": {
            "Open-Meteo": _aqi_source_meta(open_meteo, "Open-Meteo"),
            "OpenWeather": _aqi_source_meta(open_weather, "OpenWeather"),
        },
    }


def fetch_air_quality_dual(
    latitude: float,
    longitude: float,
    timezone: str = "auto",
    openweather_key: str | None = None,
) -> Dict[str, object]:
    open_meteo = fetch_air_quality_current(latitude, longitude, timezone=timezone)
    open_weather = {}
    if openweather_key:
        try:
            open_weather = fetch_openweather_air_quality(latitude, longitude, api_key=openweather_key)
        except WeatherApiError:
            open_weather = {}

    return choose_best_air_quality(open_meteo, open_weather)

def _fetch_json(
    session: requests.Session,
    url: str,
    params: Dict[str, object],
    headers: Dict[str, str] | None = None,
) -> Dict[str, object] | List[object]:
    response = session.get(url, params=params, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()


def _http_error_message(exc: requests.HTTPError, url: str) -> WeatherApiError:
    response = exc.response
    status = response.status_code if response is not None else None
    detail = None
    if response is not None:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("message") or payload.get("reason") or payload.get("error")
        except ValueError:
            text = response.text.strip()
            if text:
                detail = text[:200]

    if "openweathermap.org" in url:
        provider = "OpenWeatherMap"
    elif "open-meteo.com" in url:
        provider = "Open-Meteo"
    else:
        provider = "Weather API"

    if status in (401, 403) and "openweathermap.org" in url:
        return WeatherApiError(
            "OpenWeatherMap authorization failed. Check the API key or plan, or disable Prefer OpenWeatherMap."
        )
    if status == 429:
        return WeatherApiError(f"{provider} rate limit reached. Try again later.")
    if status is not None:
        message = f"{provider} HTTP {status} error."
        if detail:
            message = f"{message} {detail}"
        return WeatherApiError(message)
    return WeatherApiError(f"{provider} request failed.")



def _request_json(
    url: str,
    params: Dict[str, object],
    headers: Dict[str, str] | None = None,
) -> Dict[str, object] | List[object]:
    session = requests.Session()
    try:
        return _fetch_json(session, url, params, headers=headers)
    except requests.HTTPError as exc:
        raise _http_error_message(exc, url) from exc
    except requests.RequestException:
        session_no_proxy = requests.Session()
        session_no_proxy.trust_env = False
        try:
            return _fetch_json(session_no_proxy, url, params, headers=headers)
        except requests.HTTPError as exc:
            raise _http_error_message(exc, url) from exc
        except requests.RequestException as exc:
            hint = "Network/DNS failure. Check internet, DNS, or proxy settings."
            raise WeatherApiError(f"{exc}. {hint}") from exc


def fetch_current_weather(
    latitude: float,
    longitude: float,
    timezone: str = "auto",
) -> Dict[str, object]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_FIELDS,
        "timezone": timezone,
    }
    data = _request_json(FORECAST_URL, params)
    return data.get("current", {})


def fetch_hourly_forecast(
    latitude: float,
    longitude: float,
    days: int = 7,
    timezone: str = "auto",
) -> Dict[str, List[object]]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY_FIELDS,
        "forecast_days": days,
        "timezone": timezone,
    }
    data = _request_json(FORECAST_URL, params)
    return data.get("hourly", {})


def fetch_forecast_bundle(
    latitude: float,
    longitude: float,
    days: int = 7,
    timezone: str = "auto",
    include_current: bool = True,
    include_hourly: bool = True,
    include_daily: bool = True,
    openweather_key: str | None = None,
    prefer_openweather: bool = False,
    blend_sources: bool = True,
) -> Dict[str, object]:
    params: Dict[str, object] = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
    }
    if include_current:
        params["current"] = CURRENT_FIELDS
    if include_hourly:
        params["hourly"] = HOURLY_FIELDS
    if include_daily:
        params["daily"] = DAILY_FIELDS
    if include_hourly or include_daily:
        params["forecast_days"] = days

    if openweather_key and blend_sources:
        try:
            open_meteo = _request_json(FORECAST_URL, params)
        except WeatherApiError:
            open_meteo = None
        try:
            open_weather = fetch_openweather_bundle(
                latitude,
                longitude,
                days=days,
                include_current=include_current,
                include_hourly=include_hourly,
                include_daily=include_daily,
                api_key=openweather_key,
            )
        except WeatherApiError:
            open_weather = None

        if isinstance(open_meteo, dict) and isinstance(open_weather, dict):
            return _merge_bundles(open_weather, open_meteo)
        if isinstance(open_weather, dict):
            return open_weather
        if isinstance(open_meteo, dict):
            return open_meteo

    if prefer_openweather and openweather_key:
        try:
            return fetch_openweather_bundle(
                latitude,
                longitude,
                days=days,
                include_current=include_current,
                include_hourly=include_hourly,
                include_daily=include_daily,
                api_key=openweather_key,
            )
        except WeatherApiError:
            pass

    try:
        return _request_json(FORECAST_URL, params)
    except WeatherApiError:
        if include_daily and DAILY_FIELDS_FALLBACK != DAILY_FIELDS:
            fallback_params = dict(params)
            fallback_params["daily"] = DAILY_FIELDS_FALLBACK
            try:
                return _request_json(FORECAST_URL, fallback_params)
            except WeatherApiError:
                pass
        if openweather_key:
            return fetch_openweather_bundle(
                latitude,
                longitude,
                days=days,
                include_current=include_current,
                include_hourly=include_hourly,
                include_daily=include_daily,
                api_key=openweather_key,
            )
        raise


def fetch_daily_forecast(
    latitude: float,
    longitude: float,
    days: int = 7,
    timezone: str = "auto",
) -> Dict[str, List[object]]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": DAILY_FIELDS,
        "forecast_days": days,
        "timezone": timezone,
    }
    try:
        data = _request_json(FORECAST_URL, params)
    except WeatherApiError:
        params["daily"] = DAILY_FIELDS_FALLBACK
        data = _request_json(FORECAST_URL, params)
    return data.get("daily", {})


def fetch_astronomy(
    latitude: float,
    longitude: float,
    days: int = 3,
    timezone: str = "auto",
) -> Dict[str, List[object]]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ASTRO_FIELDS,
        "forecast_days": days,
        "timezone": timezone,
    }
    data = _request_json(FORECAST_URL, params)
    return data.get("daily", {})





def fetch_air_quality_best(
    latitude: float,
    longitude: float,
    timezone: str = "auto",
    openweather_key: str | None = None,
) -> Dict[str, object]:
    open_meteo = fetch_air_quality_current(latitude, longitude, timezone=timezone)
    open_weather = None
    if openweather_key:
        try:
            open_weather = fetch_openweather_air_quality(latitude, longitude, api_key=openweather_key)
        except WeatherApiError:
            open_weather = None

    if not isinstance(open_weather, dict):
        return open_meteo

    merged = dict(open_meteo)
    for key in ["us_aqi", "pm2_5", "pm10"]:
        if open_weather.get(key) is not None:
            merged[key] = open_weather.get(key)
    # Keep UV from Open-Meteo (OpenWeather air doesn't provide UV)
    return merged

def fetch_air_quality_current(
    latitude: float,
    longitude: float,
    timezone: str = "auto",
) -> Dict[str, object]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "us_aqi,european_aqi,uv_index,uv_index_clear_sky,pm2_5,pm10",
        "timezone": timezone,
    }
    data = _request_json(AIR_QUALITY_URL, params)
    return data.get("current", {})


def reverse_geocode(
    latitude: float,
    longitude: float,
) -> str | None:
    params = {
        "format": "jsonv2",
        "lat": latitude,
        "lon": longitude,
        "zoom": 10,
    }
    headers = {
        "User-Agent": "GlassWeatherAI/1.0 (local app)",
    }
    data = _request_json(REVERSE_GEOCODE_URL, params, headers=headers)
    address = data.get("address", {}) if isinstance(data, dict) else {}

    city = address.get("city") or address.get("town") or address.get("village") or address.get("hamlet")
    state = address.get("state") or address.get("region")
    country = address.get("country")

    parts = [part for part in [city, state] if part]
    if parts:
        return ", ".join(parts)
    if country:
        return country
    display = data.get("display_name") if isinstance(data, dict) else None
    return display


def forward_geocode(query: str) -> Tuple[float, float] | None:
    params = {
        "format": "jsonv2",
        "q": query,
        "limit": 1,
    }
    headers = {
        "User-Agent": "GlassWeatherAI/1.0 (local app)",
    }
    data = _request_json(FORWARD_GEOCODE_URL, params, headers=headers)
    if isinstance(data, list) and data:
        item = data[0]
        try:
            return float(item.get("lat")), float(item.get("lon"))
        except (TypeError, ValueError, AttributeError):
            return None
    return None


def fetch_historical_archive(
    latitude: float,
    longitude: float,
    start_date: dt.date,
    end_date: dt.date,
    timezone: str = "auto",
) -> Dict[str, List[object]]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "timezone": timezone,
    }
    data = _request_json(ARCHIVE_URL, params)
    return data.get("hourly", {})


def coerce_hourly_payload(payload: Dict[str, List[object]]) -> Tuple[List[dt.datetime], Dict[str, List[float]]]:
    times = payload.get("time", [])
    if not times:
        return [], {}

    timestamps = [dt.datetime.fromisoformat(value) for value in times]
    fields: Dict[str, List[float]] = {}
    for key, values in payload.items():
        if key == "time":
            continue
        fields[key] = [float(v) if v is not None else float("nan") for v in values]

    return timestamps, fields
