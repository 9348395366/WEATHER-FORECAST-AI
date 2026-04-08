
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.agent import AgentContext, WeatherAgent, get_language_pack
from src.data import summarize_dataset
from src.layout import apply_global_styles, nav_bar, setup_state, sidebar_controls
from src.constants import is_in_india, timezone_for_location
from src.aqi import india_aqi, india_aqi_status
from src.services import (
    cached_air_quality,
    cached_dataset,
    cached_forecast_bundle,
    cached_reverse_geocode,
    load_metrics,
)
from src.weather_api import WeatherApiError
from src.intent_model import predict_intent


st.set_page_config(page_title="AI Weather Forecast - Agent Chat", layout="wide")

setup_state()
sidebar_controls()
apply_global_styles()
nav_bar()

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&display=swap');

    :root {
        --bg: radial-gradient(1200px 700px at 15% 10%, #1b2145 0%, #12162f 45%, #0b0f22 100%);
        --panel: rgba(18, 24, 48, 0.78);
        --panel-border: rgba(130, 150, 220, 0.18);
        --panel-glow: 0 20px 45px rgba(9, 12, 30, 0.45);
        --text: #f1f5ff;
        --subtext: #c7d2fe;
        --accent: #7aa2ff;
        --bubble-agent: rgba(255, 255, 255, 0.08);
        --bubble-user: rgba(104, 126, 255, 0.35);
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--bg) !important;
        color: var(--text);
        font-family: 'Sora', sans-serif;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"] {
        background: transparent;
    }

    .side-card {
        background: var(--panel);
        border: 1px solid var(--panel-border);
        border-radius: 26px;
        padding: 1.4rem;
        box-shadow: var(--panel-glow);
        min-height: 68vh;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .agent-name {
        font-size: 1.8rem;
        font-weight: 700;
    }

    .agent-meta {
        color: var(--subtext);
        font-size: 0.85rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    .agent-meta .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #34d399;
        display: inline-block;
    }

    .side-button {
        background: rgba(255,255,255,0.08);
        border: 1px solid var(--panel-border);
        border-radius: 14px;
        padding: 0.6rem 0.9rem;
        color: var(--text);
        font-weight: 600;
        text-align: center;
    }

    .side-button.primary {
        background: linear-gradient(135deg, rgba(122, 162, 255, 0.85), rgba(70, 85, 160, 0.9));
        border: none;
        box-shadow: 0 10px 30px rgba(79, 96, 180, 0.35);
    }

    .agent-avatar {
        flex: 1;
        border-radius: 24px;
        background:
            radial-gradient(circle at 30% 20%, rgba(255,255,255,0.5), transparent 45%),
            radial-gradient(circle at 70% 30%, rgba(120, 170, 255, 0.35), transparent 55%),
            linear-gradient(160deg, rgba(40, 50, 90, 0.9), rgba(18, 24, 48, 0.9));
        border: 1px solid rgba(120, 140, 200, 0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.2rem;
        position: relative;
        overflow: hidden;
        flex-direction: column;
        gap: 0.6rem;
    }

    .agent-avatar-image {
        width: 100%;
        max-width: 220px;
        height: auto;
        filter: drop-shadow(0 18px 28px rgba(6, 12, 28, 0.55));
        transform-origin: 50% 70%;
        animation: boat-dance 3.6s ease-in-out infinite;
    }

    .agent-avatar-caption {
        font-size: 0.95rem;
        color: var(--subtext);
        letter-spacing: 0.04em;
    }

    .side-card [data-testid="stPopover"] > button,
    .side-card .stPopover > button {
        width: 100%;
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid var(--panel-border) !important;
        border-radius: 18px !important;
        padding: 0.8rem 1rem !important;
        color: var(--text) !important;
        font-weight: 600 !important;
        text-align: left !important;
        box-shadow: none !important;
    }

    .side-card [data-testid="stPopover"] > button:hover,
    .side-card .stPopover > button:hover {
        border-color: rgba(140, 165, 240, 0.45) !important;
        background: rgba(255, 255, 255, 0.12) !important;
    }

    .popover-actions button {
        background: rgba(122, 162, 255, 0.18) !important;
        border: 1px solid rgba(120, 140, 200, 0.45) !important;
        color: var(--text) !important;
        border-radius: 12px !important;
        padding: 0.45rem 0.75rem !important;
        font-weight: 600 !important;
        width: 100% !important;
    }

    @keyframes boat-dance {
        0% { transform: translateY(0) rotate(0deg); }
        25% { transform: translateY(-8px) rotate(-3deg); }
        50% { transform: translateY(4px) rotate(2deg); }
        75% { transform: translateY(-6px) rotate(3deg); }
        100% { transform: translateY(0) rotate(0deg); }
    }

    .chat-panel {
        background: rgba(10, 14, 32, 0.6);
        border: 1px solid var(--panel-border);
        border-radius: 26px;
        padding: 1.4rem;
        box-shadow: var(--panel-glow);
        min-height: 68vh;
    }

    .chat-scroll {
        height: 55vh;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding-right: 6px;
    }

    .bubble-row {
        display: flex;
    }

    .bubble {
        max-width: 72%;
        padding: 0.75rem 1rem;
        border-radius: 18px;
        line-height: 1.4;
        position: relative;
        box-shadow: 0 12px 28px rgba(8, 10, 24, 0.3);
    }

    .bubble.agent {
        background: var(--bubble-agent);
        color: var(--text);
    }

    .bubble.user {
        margin-left: auto;
        background: var(--bubble-user);
        color: #f8fafc;
    }

    .bubble.user::after {
        content: "";
        position: absolute;
        right: -8px;
        top: 16px;
        width: 14px;
        height: 14px;
        background: var(--bubble-user);
        transform: rotate(45deg);
    }

    .bubble.agent::after {
        content: "";
        position: absolute;
        left: -8px;
        top: 16px;
        width: 14px;
        height: 14px;
        background: var(--bubble-agent);
        transform: rotate(45deg);
    }

    [data-testid="stForm"] {
        margin-top: 1rem;
    }

    [data-testid="stForm"] button {
        background: linear-gradient(135deg, rgba(122, 162, 255, 0.85), rgba(70, 85, 160, 0.9)) !important;
        border: none !important;
        color: #fff !important;
        border-radius: 14px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 600;
        box-shadow: 0 10px 24px rgba(79, 96, 180, 0.35);
    }

    [data-testid="stTextInput"] input {
        background: rgba(14, 19, 40, 0.9) !important;
        border: 1px solid rgba(120, 140, 200, 0.25) !important;
        color: var(--text) !important;
        border-radius: 16px !important;
        padding: 0.6rem 1rem !important;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.35);
    }

    @media (max-width: 980px) {
        .side-card {
            min-height: auto;
        }
        .chat-scroll {
            height: 50vh;
        }
    }

    @media (max-width: 720px) {
        .side-card,
        .chat-panel {
            padding: 1rem;
            border-radius: 20px;
        }
        .chat-scroll {
            height: 45vh;
        }
        .bubble {
            max-width: 100%;
        }
        .bubble-row {
            width: 100%;
        }
        .bubble.user::after,
        .bubble.agent::after {
            display: none;
        }
    }
    
    .wake-wave {
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 9999;
        mix-blend-mode: screen;
    }

    .wake-wave .wave-band {
        position: absolute;
        left: -25%;
        right: -25%;
        top: 50%;
        height: 180px;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(255, 40, 120, 0.35), rgba(0, 255, 170, 0.35), rgba(70, 120, 255, 0.35), rgba(255, 60, 210, 0.35));
        filter: blur(18px);
        animation: wave-shift 3.2s ease-in-out infinite, hue-spin 6s linear infinite;
        transform: translateY(-40px) scaleX(1.1);
    }

    .wake-wave .wave-band.wave-2 {
        top: 35%;
        height: 140px;
        animation-delay: 0.4s;
        opacity: 0.7;
    }

    .wake-wave .wave-band.wave-3 {
        top: 65%;
        height: 140px;
        animation-delay: 0.8s;
        opacity: 0.7;
    }

    @keyframes wave-shift {
        0% { transform: translateY(-50px) scaleX(1.05); }
        50% { transform: translateY(40px) scaleX(1.2); }
        100% { transform: translateY(-50px) scaleX(1.05); }
    }

    @keyframes hue-spin {
        0% { filter: blur(18px) hue-rotate(0deg); }
        100% { filter: blur(18px) hue-rotate(360deg); }
    }</style>
    """,
    unsafe_allow_html=True,
)

if "wake_word_enabled" in st.session_state and st.session_state.wake_word_enabled:
    st.markdown(
        """
        <div class="wake-wave">
            <div class="wave-band wave-1"></div>
            <div class="wave-band wave-2"></div>
            <div class="wave-band wave-3"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False
if "voice_rate" not in st.session_state:
    st.session_state.voice_rate = 0.95
if "voice_volume" not in st.session_state:
    st.session_state.voice_volume = 0.6
if "voice_pitch" not in st.session_state:
    st.session_state.voice_pitch = 1.05
if "voice_preset" not in st.session_state:
    st.session_state.voice_preset = "Soft Female"
if "voice_payload" not in st.session_state:
    st.session_state.voice_payload = None
if "language" not in st.session_state:
    st.session_state.language = "English"
if "wake_word_enabled" not in st.session_state:
    st.session_state.wake_word_enabled = False
if "last_wake_message" not in st.session_state:
    st.session_state.last_wake_message = None
if "last_voice_text" not in st.session_state:
    st.session_state.last_voice_text = None

LANGUAGE_OPTIONS = {"English": "en", "Hindi": "hi", "Odia": "or"}
LANGUAGE_SPEECH = {"en": "en-IN", "hi": "hi-IN", "or": "or-IN"}

selected_language = st.session_state.language
language_code = LANGUAGE_OPTIONS.get(selected_language, "en")
ui_text = get_language_pack(language_code)["ui"]

lat = float(st.session_state.lat)
lon = float(st.session_state.lon)
tz_pref = timezone_for_location(lat, lon)
openweather_key = st.session_state.get("openweather_key") or None
prefer_openweather = st.session_state.get("prefer_openweather", False)
if not openweather_key:
    prefer_openweather = False
if not prefer_openweather:
    openweather_key = None
df, source = cached_dataset()
metrics = load_metrics()

if "dataset_summary" not in st.session_state or st.session_state.get("dataset_source") != source:
    st.session_state.dataset_summary = summarize_dataset(df)
    st.session_state.dataset_source = source

dataset_summary = st.session_state.dataset_summary

location_label = None
try:
    location_label = cached_reverse_geocode(lat, lon)
except WeatherApiError:
    location_label = None
if not location_label:
    location_label = f"{lat:.3f}, {lon:.3f}"

avatar_path = Path("assets") / "ai_boat_dance.svg"
avatar_html = "<div class=\"agent-avatar-caption\">DONT WORRY AGENT IS HERE</div>"
if avatar_path.exists():
    svg_text = avatar_path.read_text(encoding="utf-8")
    svg_b64 = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
    avatar_html = (
        f"<img class=\"agent-avatar-image\" "
        f"src=\"data:image/svg+xml;base64,{svg_b64}\" "
        f"alt=\"AI boat companion\" />"
        f"<div class=\"agent-avatar-caption\">DONT WORRY AGENT IS HERE</div>"
    )

if "last_suggested_intent" not in st.session_state:
    st.session_state.last_suggested_intent = None


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def weather_label(code):
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


def direction_to_cardinal(deg):
    if deg is None:
        return "n/a"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
    idx = int((deg + 22.5) // 45)
    return directions[idx]


def tool_current() -> str:
    try:
        bundle = cached_forecast_bundle(
            lat,
            lon,
            2,
            include_daily=False,
            openweather_key=openweather_key,
            prefer_openweather=prefer_openweather,
            timezone=tz_pref,
        )
        current = bundle.get("current", {})
    except WeatherApiError as exc:
        return f"Weather API error: {exc}"

    if not current:
        return "No current weather available right now."

    temp = current.get("temperature_2m", "n/a")
    humidity = current.get("relative_humidity_2m", "n/a")
    wind = current.get("wind_speed_10m", "n/a")
    desc = weather_label(current.get("weather_code"))

    return (
        f"Current conditions: {temp} C, {desc}. "
        f"Humidity {humidity}%, wind {wind} m/s."
    )


def tool_forecast() -> str:
    try:
        bundle = cached_forecast_bundle(
            lat,
            lon,
            2,
            include_daily=False,
            openweather_key=openweather_key,
            prefer_openweather=prefer_openweather,
            timezone=tz_pref,
        )
        hourly = bundle.get("hourly", {})
    except WeatherApiError as exc:
        return f"Weather API error: {exc}"

    if not hourly or "time" not in hourly:
        return "No forecast data available right now."

    frame = pd.DataFrame(hourly)
    frame["time"] = pd.to_datetime(frame["time"])
    upcoming = frame.head(12)
    min_temp = upcoming["temperature_2m"].min()
    max_temp = upcoming["temperature_2m"].max()
    precip_total = upcoming.get("precipitation", pd.Series([0])).sum()

    return (
        f"Next 12 hours: temps between {min_temp:.1f} C and {max_temp:.1f} C. "
        f"Expected precipitation total ~{precip_total:.1f} mm."
    )


def tool_air_quality() -> str:
    try:
        air = cached_air_quality(lat, lon, timezone=tz_pref, openweather_key=openweather_key)
    except WeatherApiError as exc:
        return f"Air quality API error: {exc}"

    if not air:
        return "No air quality data available right now."

    uv = air.get("uv_index")
    pm25 = air.get("pm2_5")
    pm10 = air.get("pm10")

    parts = []
    if is_in_india(lat, lon):
        aqi_val = india_aqi(pm25, pm10)
        label, _, _ = india_aqi_status(aqi_val)
        if aqi_val is not None:
            parts.append(f"AQI {aqi_val:.0f} (IN - {label})")
    else:
        aqi = air.get("us_aqi") or air.get("european_aqi")
        if aqi is not None:
            parts.append(f"AQI {aqi}")
    if pm25 is not None:
        parts.append(f"PM2.5 {pm25} ug/m3")
    if pm10 is not None:
        parts.append(f"PM10 {pm10} ug/m3")
    if uv is not None:
        parts.append(f"UV {uv}")

    return "Air quality: " + ", ".join(parts) if parts else "Air quality data is missing."


def tool_uv() -> str:
    try:
        air = cached_air_quality(lat, lon, timezone=tz_pref, openweather_key=openweather_key)
    except WeatherApiError as exc:
        return f"Air quality API error: {exc}"

    uv = air.get("uv_index") if air else None
    if uv is None:
        return "UV index data is not available right now."
    return f"Current UV index: {uv}."


def tool_wind() -> str:
    try:
        bundle = cached_forecast_bundle(
            lat,
            lon,
            2,
            include_daily=False,
            openweather_key=openweather_key,
            prefer_openweather=prefer_openweather,
            timezone=tz_pref,
        )
        current = bundle.get("current", {})
    except WeatherApiError as exc:
        return f"Weather API error: {exc}"

    speed = safe_float(current.get("wind_speed_10m"))
    direction = safe_float(current.get("wind_direction_10m"))
    if speed is None:
        return "Wind data is not available right now."

    kmh = speed * 3.6
    direction_label = direction_to_cardinal(direction)
    direction_deg = f"{direction:.0f}Â°" if direction is not None else "n/a"

    return f"Wind {kmh:.0f} km/h ({speed:.1f} m/s), direction {direction_label} ({direction_deg})."


def tool_humidity() -> str:
    try:
        bundle = cached_forecast_bundle(
            lat,
            lon,
            2,
            include_daily=False,
            openweather_key=openweather_key,
            prefer_openweather=prefer_openweather,
            timezone=tz_pref,
        )
        current = bundle.get("current", {})
    except WeatherApiError as exc:
        return f"Weather API error: {exc}"

    humidity = current.get("relative_humidity_2m")
    return f"Current humidity: {humidity}%." if humidity is not None else "Humidity data is not available right now."


def tool_visibility() -> str:
    try:
        bundle = cached_forecast_bundle(
            lat,
            lon,
            2,
            include_daily=False,
            openweather_key=openweather_key,
            prefer_openweather=prefer_openweather,
            timezone=tz_pref,
        )
        current = bundle.get("current", {})
    except WeatherApiError as exc:
        return f"Weather API error: {exc}"

    visibility_m = safe_float(current.get("visibility"))
    if visibility_m is None:
        return "Visibility data is not available right now."
    visibility_km = visibility_m / 1000
    return f"Visibility: {visibility_km:.1f} km."


def tool_pressure() -> str:
    try:
        bundle = cached_forecast_bundle(
            lat,
            lon,
            2,
            include_daily=False,
            openweather_key=openweather_key,
            prefer_openweather=prefer_openweather,
            timezone=tz_pref,
        )
        current = bundle.get("current", {})
    except WeatherApiError as exc:
        return f"Weather API error: {exc}"

    pressure = current.get("surface_pressure")
    return f"Surface pressure: {pressure} hPa." if pressure is not None else "Pressure data is not available right now."


def tool_location() -> str:
    try:
        label = cached_reverse_geocode(lat, lon)
    except WeatherApiError:
        label = None

    if label:
        return f"You are near: {label} ({lat:.3f}, {lon:.3f})."
    return f"Location: {lat:.3f}, {lon:.3f}."


def tool_dataset() -> str:
    summary = dataset_summary
    return (
        f"Dataset rows: {summary['rows']}. Range {summary['start']} to {summary['end']}. "
        f"Columns: {', '.join(summary['columns'])}. Source: {source}."
    )


def tool_model() -> str:
    if not metrics:
        return "Model metrics are not available yet. Run scripts/train_model.py first."
    return f"Model MAE: {metrics.get('mae', 'n/a'):.3f} (data source: {metrics.get('source', 'n/a')})."

agent = WeatherAgent(
    {
        "current_weather": tool_current,
        "forecast_summary": tool_forecast,
        "air_quality": tool_air_quality,
        "uv_index": tool_uv,
        "wind": tool_wind,
        "humidity": tool_humidity,
        "visibility": tool_visibility,
        "pressure": tool_pressure,
        "location": tool_location,
        "dataset_summary": tool_dataset,
        "model_summary": tool_model,
    },
    intent_predictor=predict_intent,
    min_confidence=0.45,
    language=language_code,
)

if st.session_state.voice_enabled and st.session_state.voice_payload:
    payload = {
        "text": st.session_state.voice_payload,
        "rate": st.session_state.voice_rate,
        "volume": st.session_state.voice_volume,
        "pitch": st.session_state.voice_pitch,
        "preset": st.session_state.voice_preset,
    }
    safe_payload = json.dumps(payload)
    voice_html = """
    <script>
    (function() {
        const payload = __PAYLOAD__;
        if (!('speechSynthesis' in window)) {
            return;
        }
        const preferFemale = payload.preset === 'Soft Female' || payload.preset === 'female';
        const pickVoice = () => {
            const voices = window.speechSynthesis.getVoices();
            if (!voices || !voices.length) return null;
            let voice = null;
            if (preferFemale) {
                const preferred = [
                    'zira', 'susan', 'samantha', 'victoria', 'karen', 'moira',
                    'fiona', 'female', 'google uk english female', 'google us english'
                ];
                for (const key of preferred) {
                    voice = voices.find(v => v.name.toLowerCase().includes(key));
                    if (voice) break;
                }
            }
            if (!voice) {
                voice = voices.find(v => v.lang && v.lang.toLowerCase().startsWith('en')) || voices[0];
            }
            return voice;
        };
        const speak = () => {
            const utter = new SpeechSynthesisUtterance(payload.text);
            const voice = pickVoice();
            if (voice) utter.voice = voice;
            utter.rate = payload.rate || 0.95;
            utter.pitch = payload.pitch || 1.05;
            utter.volume = payload.volume || 0.6;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utter);
        };
        if (window.speechSynthesis.getVoices().length) {
            speak();
        } else {
            window.speechSynthesis.onvoiceschanged = () => speak();
        }
    })();
    </script>
    """
    voice_html = voice_html.replace("__PAYLOAD__", safe_payload)
    components.html(voice_html, height=0)
    st.session_state.voice_payload = None


def wake_word_listener(enabled: bool, language: str, placeholder: str, send_label: str, wake_message: str) -> None:
    if not enabled:
        return
    payload = {
        "lang": language,
        "placeholder": placeholder,
        "sendLabel": send_label,
        "wakeMessage": wake_message,
    }
    safe_payload = json.dumps(payload)
    html_block = """
    <script>
    (function() {
        const payload = __PAYLOAD__;
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            return;
        }
        const recog = new SpeechRecognition();
        recog.continuous = true;
        recog.interimResults = false;
        recog.lang = payload.lang || "en-IN";
        let active = false;
        let lastSent = "";

        const findInput = () => {
            const direct = document.querySelector(`input[placeholder="${payload.placeholder}"]`);
            if (direct) return direct;
            return document.querySelector('[data-testid="stTextInput"] input');
        };

        const findButton = () => {
            const form = document.querySelector('form');
            if (form) {
                const btn = form.querySelector('button[type="submit"]') || form.querySelector('button');
                if (btn) return btn;
            }
            const buttons = Array.from(document.querySelectorAll('button'));
            const label = (payload.sendLabel || '').trim().toLowerCase();
            return buttons.find(btn => (btn.innerText || '').trim().toLowerCase() === label) || null;
        };

        const sendText = (text) => {
            if (!text) return;
            if (text === lastSent) return;
            const input = findInput();
            const button = findButton();
            if (!input || !button) return;
            input.focus();
            input.value = text;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            button.click();
            lastSent = text;
        };

        const start = () => {
            if (active) return;
            active = true;
            try { recog.start(); } catch (err) {}
        };

        recog.onresult = (event) => {
            const last = event.results[event.results.length - 1][0].transcript || '';
            const text = last.trim();
            if (!text) return;
            const lower = text.toLowerCase();
            const wake = /\\b(hi|hey|hai)?\\s*siri\\b/.test(lower) || lower.includes('siri');
            const message = wake ? payload.wakeMessage : text;
            sendText(message);
        };

        recog.onend = () => {
            active = false;
            setTimeout(start, 600);
        };

        start();
    })();
    </script>
    """
    html_block = html_block.replace("__PAYLOAD__", safe_payload)
    components.html(html_block, height=0)


def handle_message(message: str) -> None:
    if not isinstance(message, str):
        return
    if not message.strip():
        return
    st.session_state.chat_history.append({"role": "user", "content": message})
    context = AgentContext(
        latitude=lat,
        longitude=lon,
        dataset_summary=dataset_summary,
        model_metrics=metrics,
        location_label=location_label,
        last_suggested_intent=st.session_state.last_suggested_intent,
    )
    result = agent.respond(message, context)
    st.session_state.chat_history.append({"role": "agent", "content": result.reply})
    st.session_state.last_suggested_intent = result.suggested_intent
    if st.session_state.voice_enabled:
        st.session_state.voice_payload = result.reply
    st.rerun()


left_col, right_col = st.columns([1, 2.4], gap="large")

with left_col:
    st.markdown('<div class="side-card">', unsafe_allow_html=True)
    st.markdown(
        """
        <div>
            <div class="agent-name">DONT WORRY AGENT IS HERE</div>
            <div class="agent-meta"><span class="dot"></span> LVL 2 - 60 XP - Chatty</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="agent-avatar">{avatar_html}</div>', unsafe_allow_html=True)

    with st.popover(ui_text["vent_label"], use_container_width=True):
        st.markdown('<div class="popover-actions">', unsafe_allow_html=True)
        quick_actions = [
            ("Current temperature", "temperature", "quick_temp"),
            ("Forecast", "forecast", "quick_forecast"),
            ("Air quality", "air quality", "quick_air"),
            ("UV index", "uv", "quick_uv"),
            ("Wind speed", "wind", "quick_wind"),
            ("Humidity", "humidity", "quick_humidity"),
            ("Visibility", "visibility", "quick_visibility"),
            ("Pressure", "pressure", "quick_pressure"),
            ("Location", "location", "quick_location"),
        ]
        for label, message, key in quick_actions:
            if st.button(label, key=key, use_container_width=True):
                handle_message(message)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="side-button primary">{ui_text["choose_conversation"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.selectbox(ui_text["language_label"], options=list(LANGUAGE_OPTIONS.keys()), key="language")
    st.toggle(ui_text["voice_toggle"], key="voice_enabled")
    st.toggle(ui_text["wake_word_toggle"], key="wake_word_enabled")

    speech_lang = LANGUAGE_SPEECH.get(language_code, "en-IN")
    wake_word_listener(
        st.session_state.wake_word_enabled,
        speech_lang,
        ui_text["placeholder"],
        ui_text["send_label"],
        ui_text["wake_word_trigger"],
    )

with right_col:
    chat_html = "<div class=\"chat-panel\"><div class=\"chat-scroll\">"
    if not st.session_state.chat_history:
        chat_html += f"<div class=\"bubble-row\"><div class=\"bubble agent\">{html.escape(ui_text['intro_message'])}</div></div>"
    for item in st.session_state.chat_history:
        role = item.get("role")
        content = html.escape(item.get("content", ""))
        bubble_class = "bubble user" if role == "user" else "bubble agent"
        chat_html += f"<div class=\"bubble-row\"><div class=\"{bubble_class}\">{content}</div></div>"
    chat_html += "</div></div>"
    st.markdown(chat_html, unsafe_allow_html=True)

    submitted = False
    message = ""
    with st.form("chat_form", clear_on_submit=True):
        form_cols = st.columns([6, 1])
        with form_cols[0]:
            message = st.text_input("", placeholder=ui_text["placeholder"], label_visibility="collapsed")
        with form_cols[1]:
            submitted = st.form_submit_button(ui_text["send_label"])

if submitted:
    message = message.strip()
    if message:
        handle_message(message)








