from __future__ import annotations

import math
import html
import datetime as dt

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

from src.layout import apply_global_styles, hero, nav_bar, setup_state, sidebar_controls
from src.aqi import india_aqi, india_aqi_status
from src.services import (
    cached_air_quality,
    cached_astronomy,
    cached_forecast_bundle,
    cached_reverse_geocode,
)
from src.weather_api import WeatherApiError
from src.constants import is_in_india, timezone_for_location


st.set_page_config(page_title="AI Weather Forecast", layout="wide")

setup_state()
sidebar_controls()
apply_global_styles()
nav_bar()


def render_clock_pill(location_label: str, theme: str) -> None:
    location_safe = html.escape(location_label)
    if theme == "dark":
        pill_bg = "rgba(15, 23, 42, 0.75)"
        pill_border = "rgba(148, 163, 184, 0.35)"
        text_color = "#f8fafc"
        sub_color = "#cbd5e1"
        shadow = "0 18px 40px rgba(15, 23, 42, 0.35)"
    else:
        pill_bg = "rgba(255, 255, 255, 0.92)"
        pill_border = "rgba(148, 163, 184, 0.35)"
        text_color = "#0f172a"
        sub_color = "#475569"
        shadow = "0 18px 40px rgba(148, 163, 184, 0.35)"

    components.html(
        f"""
        <div class="clock-wrap">
            <div class="clock-pill">
                <span id="clock-time">--:--:--</span>
                <span id="clock-tz">Loading</span>
            </div>
            <div class="clock-loc">{location_safe}</div>
        </div>
        <style>
            .clock-wrap {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 6px;
                font-family: 'Space Grotesk', sans-serif;
            }}
            .clock-pill {{
                display: inline-flex;
                align-items: center;
                gap: 16px;
                padding: 10px 22px;
                border-radius: 999px;
                background: {pill_bg};
                border: 1px solid {pill_border};
                box-shadow: {shadow};
                color: {text_color};
                font-weight: 600;
            }}
            #clock-time {{
                font-size: 1.05rem;
                letter-spacing: 0.06em;
            }}
            #clock-tz {{
                font-size: 0.85rem;
                color: {sub_color};
            }}
            .clock-loc {{
                font-size: 0.85rem;
                color: {sub_color};
            }}

            @media (max-width: 900px) {{
                .clock-pill {{
                    padding: 8px 16px;
                    gap: 10px;
                }}
                #clock-time {{
                    font-size: 0.95rem;
                }}
                #clock-tz {{
                    font-size: 0.75rem;
                }}
                .clock-loc {{
                    font-size: 0.75rem;
                    text-align: center;
                }}
            }}
        </style>
        <script>
            const timeEl = document.getElementById('clock-time');
            const tzEl = document.getElementById('clock-tz');
            function updateClock() {{
                const now = new Date();
                timeEl.textContent = now.toLocaleTimeString([], {{
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                }});
                const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
                tzEl.textContent = zone;
            }}
            updateClock();
            setInterval(updateClock, 1000);
        </script>
        """,
        height=110,
    )


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def to_unit(value_c: float | None, unit: str) -> float | None:
    if value_c is None:
        return None
    if unit == "F":
        return value_c * 9 / 5 + 32
    return value_c


def format_temp(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0f} {unit}"


def weather_label(code: float | None) -> str:
    if code is None:
        return "n/a"
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "n/a"
    if code == 0:
        return "Clear"
    if code in (1, 2):
        return "Mostly clear"
    if code == 3:
        return "Cloudy"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55):
        return "Drizzle"
    if code in (56, 57):
        return "Freezing drizzle"
    if code in (61, 63, 65):
        return "Rain"
    if code in (66, 67):
        return "Freezing rain"
    if code in (71, 73, 75):
        return "Snow"
    if code == 77:
        return "Snow grains"
    if code in (80, 81, 82):
        return "Showers"
    if code in (85, 86):
        return "Snow showers"
    if code == 95:
        return "Thunderstorm"
    if code in (96, 99):
        return "Thunderstorm hail"
    return "n/a"


def visibility_status(km: float | None):
    if km is None:
        return "n/a", 0.0, "#94a3b8"
    if km >= 10:
        return "Excellent", 1.0, "#22c55e"
    if km >= 5:
        return "Good", 0.7, "#22c55e"
    if km >= 2:
        return "Moderate", 0.4, "#f59e0b"
    return "Poor", 0.2, "#ef4444"

def direction_to_cardinal(deg: float | None) -> str:
    if deg is None:
        return "n/a"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
    idx = int((deg + 22.5) // 45)
    return directions[idx]




def pressure_status(values):
    if not values or len(values) < 2:
        return "Steady", "#94a3b8"
    delta = values[-1] - values[0]
    if delta > 1.5:
        return "Rising", "#38bdf8"
    if delta > 0.3:
        return "Rising slowly", "#60a5fa"
    if delta < -1.5:
        return "Falling", "#f97316"
    if delta < -0.3:
        return "Falling slowly", "#f59e0b"
    return "Steady", "#94a3b8"


def wind_status(value_ms: float | None):
    if value_ms is None:
        return "n/a", "#94a3b8", None
    if value_ms < 1:
        return "Calm", "#22c55e", 6.0
    if value_ms < 5:
        return "Light breeze", "#38bdf8", 4.5
    if value_ms < 10:
        return "Breezy", "#f59e0b", 3.0
    if value_ms < 15:
        return "Windy", "#f97316", 2.2
    if value_ms < 20:
        return "Strong", "#ef4444", 1.6
    return "Storm", "#b91c1c", 1.0


def aqi_status(value: float | None):
    if value is None:
        return "n/a", 0.0, "#94a3b8"
    if value <= 50:
        return "Good", clamp(value / 50), "#22c55e"
    if value <= 100:
        return "Moderate", clamp(value / 100), "#f59e0b"
    if value <= 150:
        return "Unhealthy SG", clamp(value / 150), "#f97316"
    if value <= 200:
        return "Unhealthy", clamp(value / 200), "#ef4444"
    if value <= 300:
        return "Very Unhealthy", clamp(value / 300), "#a855f7"
    return "Hazardous", 1.0, "#7f1d1d"


def uv_status(value: float | None):
    if value is None:
        return "n/a", 0.0, "#94a3b8"
    if value <= 2:
        return "Low", clamp(value / 2), "#22c55e"
    if value <= 5:
        return "Moderate", clamp(value / 5), "#f59e0b"
    if value <= 7:
        return "High", clamp(value / 7), "#f97316"
    if value <= 10:
        return "Very High", clamp(value / 10), "#ef4444"
    return "Extreme", 1.0, "#7c3aed"

def humidity_status(value: float | None):
    if value is None:
        return "n/a"
    if value < 30:
        return "Low moisture level possible."
    if value < 60:
        return "Comfortable range."
    if value < 80:
        return "Humid conditions."
    return "Very humid air."


def aqi_description(label: str):
    if not label or label == "n/a":
        return "No data available."
    base = label.split(" (")[0].lower()
    if base.startswith("good"):
        return "Clean air."
    if base.startswith("moderate"):
        return "Acceptable air."
    if base.startswith("unhealthy sg"):
        return "Sensitive groups should limit exposure."
    if base.startswith("unhealthy"):
        return "Reduce prolonged outdoor activity."
    if base.startswith("very unhealthy"):
        return "Health warnings possible."
    if base.startswith("hazardous"):
        return "Serious risk for everyone."
    return "Air quality update."


    if value is None:
        return "n/a", 0.0, "#94a3b8"
    if value <= 2:
        return "Low", clamp(value / 2), "#22c55e"
    if value <= 5:
        return "Moderate", clamp(value / 5), "#f59e0b"
    if value <= 7:
        return "High", clamp(value / 7), "#f97316"
    if value <= 10:
        return "Very High", clamp(value / 10), "#ef4444"
    return "Extreme", 1.0, "#7c3aed"


def parse_time(value):
    if value is None:
        return None
    try:
        return pd.to_datetime(value)
    except (TypeError, ValueError):
        return None


def resolve_timezone(bundle, *times):
    tz = None
    if isinstance(bundle, dict):
        tz = bundle.get("timezone") or None
        if tz:
            return tz
        offset = bundle.get("utc_offset_seconds")
        if offset is not None:
            try:
                return dt.timezone(dt.timedelta(seconds=int(offset)))
            except (TypeError, ValueError, OSError):
                pass
    for ts in times:
        if isinstance(ts, pd.Timestamp) and ts.tzinfo is not None:
            return ts.tzinfo
    return None


def normalize_to_tz(ts: pd.Timestamp | None, tz):
    if ts is None or tz is None:
        return ts
    try:
        if ts.tzinfo is None:
            return ts.tz_localize(tz)
        return ts.tz_convert(tz)
    except Exception:
        return ts


def now_in_timezone(tz, fallback: pd.Timestamp | None = None) -> pd.Timestamp:
    if tz:
        try:
            return pd.Timestamp.now(tz=tz)
        except Exception:
            pass
    return fallback or pd.Timestamp.now()


def daily_index_for_now(daily: dict, now_ts: pd.Timestamp | None) -> int:
    if not daily or "time" not in daily:
        return 0
    times = daily.get("time") or []
    if not times:
        return 0
    try:
        dates = pd.to_datetime(times)
    except (TypeError, ValueError):
        return 0

    target = now_ts
    if target is None:
        target = pd.Timestamp.now()

    tz = getattr(dates, "tz", None)
    if tz is not None:
        if target.tzinfo is None:
            target = target.tz_localize(tz)
        else:
            target = target.tz_convert(tz)

    target_date = target.date()
    for idx, dt_val in enumerate(dates):
        if dt_val.date() == target_date:
            return idx
    return 0


def pick_daily_value(daily: dict, key: str, idx: int) -> object | None:
    if not daily:
        return None
    values = daily.get(key) or []
    if not values:
        return None
    if idx < len(values):
        return values[idx]
    return values[0]


def format_time(ts: pd.Timestamp | None) -> str:
    if ts is None:
        return "n/a"
    return ts.strftime("%I:%M %p").lstrip("0").lower()


def pick_now(fallback: pd.Timestamp | None, ref: pd.Timestamp | None) -> pd.Timestamp:
    if fallback is not None:
        return fallback
    if ref is not None and ref.tzinfo is not None:
        return pd.Timestamp.now(tz=ref.tzinfo)
    return pd.Timestamp.now()


def progress_between(now: pd.Timestamp | None, start: pd.Timestamp | None, end: pd.Timestamp | None) -> float | None:
    if now is None or start is None or end is None:
        return None

    if start.tzinfo is not None and now.tzinfo is None:
        now = now.tz_localize(start.tzinfo)
    if start.tzinfo is None and now.tzinfo is not None:
        now = now.tz_convert(None)
    if start.tzinfo is not None and end.tzinfo is None:
        end = end.tz_localize(start.tzinfo)
    if start.tzinfo is None and end.tzinfo is not None:
        end = end.tz_convert(None)

    end_adj = end
    now_adj = now
    if end_adj <= start:
        end_adj = end_adj + pd.Timedelta(days=1)
        if now_adj < start:
            now_adj = now_adj + pd.Timedelta(days=1)

    if now_adj <= start:
        return 0.0
    if now_adj >= end_adj:
        return 1.0
    return float((now_adj - start) / (end_adj - start))


def percent_value(value: float | None) -> int | None:
    if value is None:
        return None
    return int(clamp(value) * 100)


def orb_position(percent: int | None) -> int:
    if percent is None:
        return 2
    return max(2, min(98, percent))


def arc_point(percent: int | None, radius: float = 100, cx: float = 120, cy: float = 100):
    if percent is None:
        return (10.0, 90.0)
    angle = math.pi * (percent / 100)
    x = cx - radius * math.cos(angle)
    y = cy - radius * math.sin(angle)
    return (x, y)


def format_duration(delta):
    if delta is None:
        return "n/a"
    try:
        total_seconds = int(delta.total_seconds())
    except Exception:
        return "n/a"
    if total_seconds < 0:
        total_seconds = 0
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def nearest_time_index(times, target_ts):
    if not times:
        return None
    try:
        ts_list = pd.to_datetime(times)
    except (TypeError, ValueError):
        return None

    target = target_ts
    if target is None:
        return len(ts_list) - 1

    ts_tz = getattr(ts_list, "tz", None)
    if ts_tz is not None and target.tzinfo is None:
        target = target.tz_localize(ts_tz)
    elif ts_tz is None and target.tzinfo is not None:
        target = target.tz_convert(None)

    try:
        deltas = (ts_list - target).abs()
        return int(deltas.argmin())
    except Exception:
        return len(ts_list) - 1


def window_average(values, idx, window=3):
    if idx is None or not values:
        return None
    half = max(1, window // 2)
    start = max(0, idx - half)
    end = min(len(values), idx + half + 1)
    picks = [safe_float(values[i]) for i in range(start, end) if safe_float(values[i]) is not None]
    if not picks:
        return None
    return sum(picks) / len(picks)


def window_series(values, idx, count=4):
    if idx is None or not values:
        return []
    start = max(0, idx - count + 1)
    picks = [safe_float(v) for v in values[start:idx + 1] if safe_float(v) is not None]
    return picks


def smooth_value(key: str, new_value: float | None, alpha: float = 0.35) -> float | None:
    prev = st.session_state.get(key)
    if new_value is None:
        return prev
    if prev is None:
        st.session_state[key] = new_value
        return new_value
    smoothed = prev + alpha * (new_value - prev)
    st.session_state[key] = smoothed
    return smoothed



def render_bar_card(title: str, value: str, subtitle: str, percent: float, color: str) -> str:
    width = int(clamp(percent) * 100)
    return (
        "<div class='mini-card'>"
        f"<div class='mini-title'>{title}</div>"
        f"<div class='mini-value'>{value}</div>"
        f"<div class='mini-sub'>{subtitle}</div>"
        "<div class='mini-meter'>"
        f"<span style='width:{width}%; background:{color};'></span>"
        "</div>"
        "</div>"
    )


def render_ring_card(title: str, value: str, subtitle: str, percent: float, color: str) -> str:
    angle = int(clamp(percent) * 360)
    return (
        "<div class='mini-card'>"
        "<div class='mini-row'>"
        "<div>"
        f"<div class='mini-title'>{title}</div>"
        f"<div class='mini-value'>{value}</div>"
        f"<div class='mini-sub'>{subtitle}</div>"
        "</div>"
        f"<div class='mini-ring' style='--ring-angle:{angle}deg; --ring-color:{color};'></div>"
        "</div>"
        "</div>"
    )


def render_wind_card(value: str, subtitle: str, detail: str, color: str, duration: float | None) -> str:
    if duration is None:
        rotor_style = "animation-duration:6s; opacity:0.35;"
    else:
        rotor_style = f"animation-duration:{duration:.2f}s;"
    return (
        "<div class='mini-card wind-card'>"
        "<div class='mini-title'>Wind Speed</div>"
        "<div class='mini-row'>"
        "<div>"
        f"<div class='mini-value'>{value}</div>"
        f"<div class='mini-sub'>{subtitle}</div>"
        f"<div class='mini-sub'>{detail}</div>"
        "</div>"
        f"<div class='wind-fan' style='--wind-color:{color};'>"
        f"<div class='wind-rotor' style='{rotor_style}'>"
        "<span class='wind-blade blade-1'></span>"
        "<span class='wind-blade blade-2'></span>"
        "<span class='wind-blade blade-3'></span>"
        "</div>"
        "<div class='wind-core'></div>"
        "</div>"
        "</div>"
        "</div>"
    )


def get_query_param(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0]
    return value


lat = float(st.session_state.lat)
lon = float(st.session_state.lon)
tz_pref = timezone_for_location(lat, lon)
unit = st.session_state.unit
openweather_key = st.session_state.get("openweather_key") or None
prefer_openweather = st.session_state.get("prefer_openweather", False)
if not openweather_key:
    prefer_openweather = False
if not prefer_openweather:
    openweather_key = None

if not st.session_state.gps_enabled:
    st.session_state.gps_has_location = False
    st.session_state.gps_error = None
    st.session_state.gps_pending = False

location_name = st.session_state.preset_location
if location_name == "Custom":
    location_name = f"{lat:.3f}, {lon:.3f}"

unit_col_left, unit_col_mid, unit_col_right = st.columns([5, 1, 1])
with unit_col_left:
    st.markdown(f"<div class='summary-location'>{location_name}</div>", unsafe_allow_html=True)
with unit_col_mid:
    st.radio("Unit", ["C", "F"], key="unit", horizontal=True, label_visibility="collapsed")
with unit_col_right:
    st.toggle("GPS", key="gps_enabled")

if st.session_state.gps_enabled and not st.session_state.gps_has_location and not st.session_state.gps_pending:
    st.session_state.gps_pending = True
    components.html(
        """
        <script>
        (function() {
            if (!navigator.geolocation) {
                return;
            }
            let best = null;
            let attempts = 0;
            let done = false;
            const opts = { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 };
            const targetAcc = 35;
            const maxAttempts = 12;
            const maxWaitMs = 20000;
            const started = Date.now();

            const send = (pick) => {
                const params = new URLSearchParams(window.parent.location.search);
                params.set('gps_lat', pick.coords.latitude.toFixed(6));
                params.set('gps_lon', pick.coords.longitude.toFixed(6));
                params.set('gps_acc', Math.round(pick.coords.accuracy || 0));
                params.set('gps_ts', Date.now().toString());
                window.parent.location.search = params.toString();
            };

            const sendError = (err) => {
                const params = new URLSearchParams(window.parent.location.search);
                params.set('gps_err', err.code ? err.code.toString() : '1');
                params.set('gps_ts', Date.now().toString());
                window.parent.location.search = params.toString();
            };

            const handle = (pos) => {
                if (done) {
                    return;
                }
                attempts += 1;
                if (!best || pos.coords.accuracy < best.coords.accuracy) {
                    best = pos;
                }
                const acc = best && best.coords ? best.coords.accuracy : 0;
                const elapsed = Date.now() - started;
                const good = acc && acc <= targetAcc;
                if (good || attempts >= maxAttempts || elapsed >= maxWaitMs) {
                    done = true;
                    send(best || pos);
                    if (watchId !== null) {
                        navigator.geolocation.clearWatch(watchId);
                    }
                }
            };

            const handleError = (err) => {
                if (done) {
                    return;
                }
                done = true;
                sendError(err);
                if (watchId !== null) {
                    navigator.geolocation.clearWatch(watchId);
                }
            };

            let watchId = null;
            navigator.geolocation.getCurrentPosition(handle, handleError, opts);
            watchId = navigator.geolocation.watchPosition(handle, handleError, opts);
        })();
        </script>
        """,
        height=0,
    )

if st.session_state.gps_enabled:
    gps_lat = get_query_param("gps_lat")
    gps_lon = get_query_param("gps_lon")
    gps_acc = get_query_param("gps_acc")
    gps_err = get_query_param("gps_err")
    gps_ts = get_query_param("gps_ts")

    if gps_lat and gps_lon:
        if gps_ts and st.session_state.gps_last_ts == gps_ts:
            pass
        else:
            st.session_state.gps_last_ts = gps_ts
            st.session_state.pending_lat = float(gps_lat)
            st.session_state.pending_lon = float(gps_lon)
            st.session_state.gps_accuracy_m = int(gps_acc) if gps_acc else None
            st.session_state.gps_has_location = True
            st.session_state.gps_error = None
            st.session_state.gps_pending = False
            st.rerun()
    elif gps_err:
        if gps_ts and st.session_state.gps_last_ts == gps_ts:
            pass
        else:
            st.session_state.gps_last_ts = gps_ts
            st.session_state.gps_error = gps_err
            st.session_state.gps_has_location = True
            st.session_state.gps_pending = False

lat = float(st.session_state.lat)
lon = float(st.session_state.lon)
tz_pref = timezone_for_location(lat, lon)
location_name = st.session_state.preset_location
if location_name == "Custom":
    location_name = f"{lat:.3f}, {lon:.3f}"

geo_label = None
try:
    geo_label = cached_reverse_geocode(st.session_state.lat, st.session_state.lon)
except WeatherApiError:
    geo_label = None

if not geo_label:
    geo_label = location_name

render_clock_pill(geo_label, st.session_state.theme)

hero()
st.write("")

try:
    forecast_bundle = cached_forecast_bundle(
        lat,
        lon,
        7,
        openweather_key=openweather_key,
        prefer_openweather=prefer_openweather,
        timezone=tz_pref,
    )
    current = forecast_bundle.get("current", {})
    hourly = forecast_bundle.get("hourly", {})
    daily = forecast_bundle.get("daily", {})
    air = cached_air_quality(lat, lon, timezone=tz_pref, openweather_key=openweather_key)
except WeatherApiError as exc:
    st.error(f"Weather API error: {exc}")
    current = {}
    hourly = {}
    daily = {}
    air = {}

current_time = None
current_time_raw = current.get("time") or (daily.get("time", [""])[0] if daily else "")
if current_time_raw:
    current_time = pd.to_datetime(current_time_raw)
    time_label = current_time.strftime("%I:%M %p").lstrip("0")
    date_label = current_time.strftime("%a %d").replace(" 0", " ")
    updated_label = f"Updated at {date_label} {time_label}"
else:
    updated_label = "Updated recently"

status_bits = [updated_label]
if st.session_state.gps_enabled:
    if st.session_state.gps_accuracy_m:
        status_bits.append(f"GPS accuracy ~{st.session_state.gps_accuracy_m} m")
    elif st.session_state.gps_error:
        status_bits.append("GPS permission denied")

st.markdown(
    f"<div class='summary-updated'>{' | '.join(status_bits)}</div>",
    unsafe_allow_html=True,
)

current_temp_c = safe_float(current.get("temperature_2m"))
current_temp = to_unit(current_temp_c, unit)
current_code = safe_float(current.get("weather_code"))

high_c = None
low_c = None
if daily and daily.get("temperature_2m_max"):
    high_c = safe_float(daily.get("temperature_2m_max", [None])[0])
    low_c = safe_float(daily.get("temperature_2m_min", [None])[0])
else:
    temps = [safe_float(v) for v in hourly.get("temperature_2m", [])[:24]]
    temps = [v for v in temps if v is not None]
    if temps:
        high_c = max(temps)
        low_c = min(temps)

current_desc = weather_label(current_code)
summary_html = (
    "<div class='glass-card summary-card'>"
    "<div class='summary-top'>"
    "<div class='summary-stack'>"
    f"<div class='summary-temp'>{format_temp(current_temp, unit)}</div>"
    f"<div class='summary-desc'>{current_desc}</div>"
    f"<div class='summary-hilo'>H {format_temp(to_unit(high_c, unit), unit)} | L {format_temp(to_unit(low_c, unit), unit)}</div>"
    "</div>"
    "</div>"
)

chips_html = ""
if daily and daily.get("time"):
    for idx, day in enumerate(daily.get("time", [])[:6]):
        day_dt = pd.to_datetime(day)
        day_label = "Today" if idx == 0 else day_dt.strftime("%a %d").replace(" 0", " ")
        day_code = safe_float(daily.get("weather_code", [None])[idx]) if daily.get("weather_code") else None
        day_desc = weather_label(day_code)
        day_high = to_unit(safe_float(daily.get("temperature_2m_max", [None])[idx]), unit)
        day_low = to_unit(safe_float(daily.get("temperature_2m_min", [None])[idx]), unit)
        day_class = "forecast-chip active" if idx == 0 else "forecast-chip"
        chips_html += (
            f"<div class='{day_class}'>"
            f"<div class='forecast-day'>{day_label}</div>"
            f"<div class='forecast-desc'>{day_desc}</div>"
            f"<div class='forecast-temps'>{format_temp(day_high, unit)} / {format_temp(day_low, unit)}</div>"
            "</div>"
        )

summary_html += f"<div class='forecast-strip'>{chips_html}</div></div>"

st.markdown(summary_html, unsafe_allow_html=True)

hourly_times = hourly.get("time", [])
hourly_temp_c = hourly.get("temperature_2m", [])
hourly_precip = hourly.get("precipitation_probability", [])

hourly_index = nearest_time_index(hourly_times, current_time)

precip_now = safe_float(current.get("precipitation"))
precip_now_text = f"{precip_now:.1f} mm" if precip_now is not None else "n/a"
precip_prob_now = None
if hourly_precip and hourly_index is not None and hourly_index < len(hourly_precip):
    precip_prob_now = safe_float(hourly_precip[hourly_index])
precip_prob_text = f"{precip_prob_now:.0f}%" if precip_prob_now is not None else "n/a"

if hourly_times and hourly_temp_c:
    df = pd.DataFrame(
        {
            "time": pd.to_datetime(hourly_times),
            "temp": [to_unit(safe_float(v), unit) for v in hourly_temp_c],
            "precip": [safe_float(v) for v in hourly_precip] if hourly_precip else None,
        }
    ).head(12)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["temp"],
            mode="lines+markers",
            line=dict(color="#7aa2ff", width=3),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(122, 162, 255, 0.2)",
            name="Temp",
        ),
        secondary_y=False,
    )

    if hourly_precip:
        fig.add_trace(
            go.Bar(
                x=df["time"],
                y=df["precip"],
                opacity=0.35,
                marker_color="#38bdf8",
                name="Precip %",
            ),
            secondary_y=True,
        )

    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=25, b=10),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        title="Next 12 Hours",
    )
    fig.update_yaxes(title_text=f"Temp ({unit})", secondary_y=False)
    fig.update_yaxes(title_text="Precip %", secondary_y=True, range=[0, 100])

    st.plotly_chart(fig, use_container_width=True)

visibility_m = safe_float(current.get("visibility"))
visibility_values = hourly.get("visibility", [])
if visibility_m is None:
    visibility_m = window_average(visibility_values, hourly_index, window=3)

visibility_km = visibility_m / 1000 if visibility_m is not None else None
visibility_km = smooth_value("smooth_visibility_km", visibility_km, alpha=0.3)
vis_label, vis_pct, vis_color = visibility_status(visibility_km)
vis_value = f"{visibility_km:.1f} km" if visibility_km is not None else "n/a"


cloud_value = safe_float(current.get("cloud_cover"))
cloud_values = hourly.get("cloud_cover", [])
if cloud_value is None:
    cloud_value = window_average(cloud_values, hourly_index, window=3)
cloud_value = smooth_value("smooth_cloud", cloud_value, alpha=0.35)
cloud_pct = clamp((cloud_value or 0) / 100) if cloud_value is not None else 0.0
cloud_value_text = f"{cloud_value:.0f} %" if cloud_value is not None else "n/a"

pressure_value = safe_float(current.get("surface_pressure"))
pressure_values = hourly.get("surface_pressure", [])
if pressure_value is None:
    pressure_value = window_average(pressure_values, hourly_index, window=3)

pressure_window = window_series(pressure_values, hourly_index, count=4)
pressure_label, pressure_color = pressure_status(pressure_window)
pressure_value = smooth_value("smooth_pressure", pressure_value, alpha=0.35)
pressure_percent = clamp(((pressure_value or 0) - 980) / 60) if pressure_value else 0.0
pressure_value_text = f"{pressure_value:.0f} hPa" if pressure_value is not None else "n/a"

wind_value_ms = safe_float(current.get("wind_speed_10m"))
wind_values = hourly.get("wind_speed_10m", [])
if wind_value_ms is None:
    wind_value_ms = window_average(wind_values, hourly_index, window=3)

wind_value_ms = smooth_value("smooth_wind_ms", wind_value_ms, alpha=0.35)
wind_label, wind_color, wind_duration = wind_status(wind_value_ms)


wind_dir_deg = safe_float(current.get("wind_direction_10m"))
wind_dir_values = hourly.get("wind_direction_10m", [])
if wind_dir_deg is None:
    wind_dir_deg = window_average(wind_dir_values, hourly_index, window=3)
wind_dir_label = direction_to_cardinal(wind_dir_deg)
wind_dir_text = f"{wind_dir_deg:.0f}? {wind_dir_label}" if wind_dir_deg is not None else "n/a"

gust_value_ms = wind_value_ms * 1.4 if wind_value_ms is not None else None
gust_value_text = f"{gust_value_ms:.2f} m/s" if gust_value_ms is not None else "n/a"
if wind_value_ms is None:
    wind_value = "n/a"
    wind_detail = "No wind data"
else:
    wind_kmh = wind_value_ms * 3.6
    wind_mph = wind_value_ms * 2.237
    wind_value = f"{wind_kmh:.0f} km/h"
    wind_detail = f"{wind_value_ms:.1f} m/s | {wind_kmh:.0f} km/h"

pm25_value = safe_float(air.get("pm2_5"))
pm10_value = safe_float(air.get("pm10"))

if is_in_india(lat, lon):
    aqi_value_raw = india_aqi(pm25_value, pm10_value)
    aqi_scale = "IN"
else:
    us_aqi = safe_float(air.get("us_aqi"))
    eu_aqi = safe_float(air.get("european_aqi"))
    if us_aqi is not None:
        aqi_value_raw = us_aqi
        aqi_scale = "US"
    else:
        aqi_value_raw = eu_aqi
        aqi_scale = "EU" if eu_aqi is not None else ""

aqi_value = smooth_value("smooth_aqi", aqi_value_raw, alpha=0.4)
if aqi_scale == "IN":
    aqi_label, aqi_pct, aqi_color = india_aqi_status(aqi_value)
else:
    aqi_label, aqi_pct, aqi_color = aqi_status(aqi_value)

aqi_value_text = f"{aqi_value:.0f}" if aqi_value is not None else "n/a"
if aqi_scale:
    aqi_label = f"{aqi_label} ({aqi_scale})"

uv_value = safe_float(air.get("uv_index"))
uv_value = smooth_value("smooth_uv", uv_value, alpha=0.4)
uv_label, uv_pct, uv_color = uv_status(uv_value)
uv_value_text = f"{uv_value:.0f}" if uv_value is not None else "n/a"

humidity_values = hourly.get("relative_humidity_2m", [])
humidity_value = safe_float(current.get("relative_humidity_2m"))
if humidity_value is None:
    humidity_value = window_average(humidity_values, hourly_index, window=3)
humidity_value_text = f"{humidity_value:.0f}%" if humidity_value is not None else "n/a"
humidity_desc = humidity_status(humidity_value)
aqi_desc = aqi_description(aqi_label)

st.markdown("## Today Highlights")

feature_html = f"""
<div class='feature-grid'>
  <div class='feature-card wind-card'>
    <div class='feature-title'>Wind</div>
    <div class='wind-row'>
      <div class='compass' style='--wind-deg:{wind_dir_deg or 0}deg;'>
        <span class='compass-letter n'>N</span>
        <span class='compass-letter e'>E</span>
        <span class='compass-letter s'>S</span>
        <span class='compass-letter w'>W</span>
        <div class='compass-needle'></div>
        <div class='compass-core'>{wind_dir_label}</div>
      </div>
      <div class='feature-stack'>
        <div class='feature-value'>{wind_dir_text}</div>
        <div class='feature-sub'>Direction</div>
        <div class='feature-value'>{wind_value}</div>
        <div class='feature-sub'>Wind Speed</div>
      </div>
    </div>
  </div>

  <div class='feature-card gust-card'>
    <div class='feature-title'>Gust Speed</div>
    <div class='feature-icon gust-icon'></div>
    <div class='feature-value'>{gust_value_text}</div>
    <div class='feature-sub'>Estimated gusts</div>
  </div>

  <div class='feature-card cloud-card'>
    <div class='feature-title'>Cloud + Visibility</div>
    <div class='feature-icon cloud-icon'>
      <span class='cloud-anim'></span>
    </div>
    <div class='feature-row'>
      <div>
        <div class='feature-value'>{cloud_value_text}</div>
        <div class='feature-sub'>Cloud Cover</div>
      </div>
      <div>
        <div class='feature-value'>{vis_value}</div>
        <div class='feature-sub'>Visibility</div>
      </div>
    </div>
    <div class='feature-meter'>
      <span style='width:{int(clamp(cloud_pct) * 100)}%;'></span>
    </div>
  </div>

  <div class='feature-card aqi-card'>
    <div class='feature-title'>Air Quality</div>
    <div class='aqi-row'>
      <div class='aqi-gauge' style='--aqi-angle:{int(clamp(aqi_pct) * 180 - 90)}deg;'></div>
      <div class='feature-stack'>
        <div class='feature-value'>{aqi_value_text} AQI</div>
        <div class='feature-sub'>{aqi_label}</div>
        <div class='feature-sub'>{aqi_desc}</div>
      </div>
    </div>
  </div>

  <div class='feature-card humidity-card'>
    <div class='feature-title'>Humidity</div>
    <div class='feature-row'>
      <div class='humidity-icon'></div>
      <div>
        <div class='feature-value'>{humidity_value_text}</div>
        <div class='feature-sub'>{humidity_desc}</div>
      </div>
    </div>
  </div>

  <div class='feature-card precip-card'>
    <div class='feature-title'>Precipitation</div>
    <div class='feature-icon precip-icon'></div>
    <div class='feature-row'>
      <div>
        <div class='feature-value'>{precip_now_text}</div>
        <div class='feature-sub'>Now</div>
      </div>
      <div>
        <div class='feature-value'>{precip_prob_text}</div>
        <div class='feature-sub'>Chance</div>
      </div>
    </div>
    <div class='feature-sub'>Current precipitation and probability</div>
  </div>

  <div class='feature-card pressure-card'>
    <div class='feature-title'>Pressure</div>
    <div class='feature-icon pressure-icon'></div>
    <div class='feature-row'>
      <div>
        <div class='feature-value'>{pressure_value_text}</div>
        <div class='feature-sub'>{pressure_label}</div>
      </div>
      <div class='pressure-dial' style='--pressure-angle:{int(clamp(pressure_percent) * 180)}deg;'></div>
    </div>
    <div class='feature-meter gradient'>
      <span style='width:{int(clamp(pressure_percent) * 100)}%;'></span>
    </div>
  </div>

  <div class='feature-card uv-card'>
    <div class='feature-title'>UV Index</div>
    <div class='feature-icon uv-icon'></div>
    <div class='feature-value'>{uv_value_text}</div>
    <div class='feature-sub'>{uv_label}</div>
    <div class='uv-track'>
      <span style='left:{int(clamp(uv_pct) * 100)}%;'></span>
    </div>
  </div>
</div>
"""

st.markdown(feature_html, unsafe_allow_html=True)
