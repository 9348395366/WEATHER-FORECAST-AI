from __future__ import annotations

import math
import os
import json
from datetime import datetime, timedelta, timezone

import folium
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import streamlit.components.v1 as components
from folium.plugins import Fullscreen, LocateControl, MeasureControl, MiniMap, MousePosition
from streamlit_folium import st_folium

from src.layout import apply_global_styles, nav_bar, setup_state, sidebar_controls
from src.constants import is_in_india, timezone_for_location
from src.aqi import india_aqi, india_aqi_color_rgba
from src.services import cached_air_quality_dual, cached_dataset, cached_forecast_bundle
from src.weather_api import WeatherApiError


st.set_page_config(page_title="AI Weather Forecast - Live Weather", layout="wide")

setup_state()
sidebar_controls()
apply_global_styles()
nav_bar()


def render_metric_pills(current: dict) -> None:
    if not current:
        st.markdown("<div class='glass-card'>No current data available.</div>", unsafe_allow_html=True)
        return

    temp = current.get("temperature_2m", "n/a")
    humidity = current.get("relative_humidity_2m", "n/a")
    wind = current.get("wind_speed_10m", "n/a")
    precip = current.get("precipitation", "n/a")
    time = current.get("time", "n/a")

    st.markdown(
        """
        <div class="glass-card">
            <span class="metric-pill">Temp: {temp} C</span>
            <span class="metric-pill">Humidity: {humidity} %</span>
            <span class="metric-pill">Wind: {wind} m/s</span>
            <span class="metric-pill">Precip: {precip} mm</span>
            <p class="subtle">Last update: {time}</p>
        </div>
        """.format(
            temp=temp,
            humidity=humidity,
            wind=wind,
            precip=precip,
            time=time,
        ),
        unsafe_allow_html=True,
    )


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def aqi_from_air(air: dict) -> tuple[float | None, str]:
    if not isinstance(air, dict):
        return None, ""
    pm25 = safe_float(air.get("pm2_5"))
    pm10 = safe_float(air.get("pm10"))
    aqi_value = india_aqi(pm25, pm10)
    aqi_scale = "IN"

    us_aqi = safe_float(air.get("us_aqi"))
    eu_aqi = safe_float(air.get("european_aqi"))
    if us_aqi is not None:
        aqi_value = us_aqi
        aqi_scale = "US"
    elif eu_aqi is not None:
        aqi_value = eu_aqi
        aqi_scale = "EU"

    if aqi_value is None:
        aqi_scale = ""
    return aqi_value, aqi_scale


def format_aqi_label(value: float | None, scale: str) -> str:
    if value is None:
        return "n/a"
    label = f"{value:.0f}"
    return f"{label} {scale}" if scale else label


def weather_label(code) -> str:
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


def temp_color(temp_c):
    if temp_c is None:
        return "#94a3b8"
    if temp_c <= 0:
        return "#38bdf8"
    if temp_c <= 15:
        return "#60a5fa"
    if temp_c <= 25:
        return "#22c55e"
    if temp_c <= 32:
        return "#f59e0b"
    return "#ef4444"


def wind_endpoint(lat, lon, speed_ms, direction_deg):
    if speed_ms is None or direction_deg is None:
        return None
    wind_kmh = speed_ms * 3.6
    length_km = max(5.0, min(20.0, wind_kmh))
    bearing = (direction_deg + 180) % 360
    bearing_rad = math.radians(bearing)
    lat_rad = math.radians(lat)
    delta_lat = (length_km / 111.0) * math.cos(bearing_rad)
    delta_lon = (length_km / (111.0 * max(0.2, math.cos(lat_rad)))) * math.sin(bearing_rad)
    return lat + delta_lat, lon + delta_lon, bearing

@st.cache_data(ttl=600)
def rainviewer_latest_timestamp() -> int | None:
    url = "https://api.rainviewer.com/public/weather-maps.json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    radar = data.get("radar", {}) if isinstance(data, dict) else {}
    frames = radar.get("nowcast") or radar.get("past") or []
    if not frames:
        return None
    frame = frames[-1]
    try:
        return int(frame.get("time"))
    except (TypeError, ValueError, AttributeError):
        return None


def get_query_param(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0]
    return value




st.markdown("## Live Weather Core")

if not st.session_state.gps_enabled:
    st.session_state.gps_has_location = False
    st.session_state.gps_error = None
    st.session_state.gps_pending = False

location_name = st.session_state.preset_location
if location_name == "Custom":
    location_name = f"{st.session_state.lat:.3f}, {st.session_state.lon:.3f}"

gps_col_left, gps_col_right = st.columns([5, 1])
with gps_col_left:
    st.markdown(f"<div class='summary-location'>{location_name}</div>", unsafe_allow_html=True)
with gps_col_right:
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

if st.session_state.gps_enabled:
    if st.session_state.gps_accuracy_m:
        st.caption(f"GPS accuracy ~{st.session_state.gps_accuracy_m} m")
    elif st.session_state.gps_error:
        st.caption("GPS permission denied")

lat = float(st.session_state.lat)
lon = float(st.session_state.lon)
tz_pref = timezone_for_location(lat, lon)
openweather_key = st.session_state.get("openweather_key") or None
prefer_openweather = st.session_state.get("prefer_openweather", False)
if not openweather_key:
    prefer_openweather = False
if not prefer_openweather:
    openweather_key = None
mapbox_key = ""
if hasattr(st, "secrets"):
    mapbox_key = st.secrets.get("MAPBOX_API_KEY", "")
if not mapbox_key:
    mapbox_key = os.getenv("MAPBOX_API_KEY", "")

try:
    bundle = cached_forecast_bundle(
        lat,
        lon,
        5,
        include_daily=False,
        openweather_key=openweather_key,
        prefer_openweather=prefer_openweather,
        timezone=tz_pref,
    )
    current = bundle.get("current", {})
    hourly = bundle.get("hourly", {})
    try:
        air_bundle = cached_air_quality_dual(lat, lon, timezone=tz_pref, openweather_key=openweather_key)
    except WeatherApiError:
        air_bundle = {}

    if isinstance(air_bundle, dict):
        air = air_bundle.get("best", {}) or {}
        air_sources = air_bundle.get("sources", {}) or {}
        air_meta = air_bundle.get("meta", {}) or {}
        air_scores = air_bundle.get("scores", {}) or {}
        best_source = air_bundle.get("best_source", "") or ""
    else:
        air = {}
        air_sources = {}
        air_meta = {}
        air_scores = {}
        best_source = ""
except WeatherApiError as exc:
    st.error(f"Weather API error: {exc}")
    st.stop()
render_metric_pills(current)

aqi_value, aqi_scale = aqi_from_air(air)
aqi_value_text = f"{aqi_value:.0f}" if aqi_value is not None else "n/a"
if aqi_scale:
    aqi_label = f"{aqi_value_text} {aqi_scale}"
else:
    aqi_label = aqi_value_text
aqi_rgba = india_aqi_color_rgba(aqi_value)
aqi_color = f"#{aqi_rgba[0]:02x}{aqi_rgba[1]:02x}{aqi_rgba[2]:02x}"
aqi_opacity = aqi_rgba[3] / 255

open_meteo = air_sources.get("Open-Meteo", {}) if isinstance(air_sources, dict) else {}
open_weather = air_sources.get("OpenWeather", {}) if isinstance(air_sources, dict) else {}

om_value, om_scale = aqi_from_air(open_meteo)
ow_value, ow_scale = aqi_from_air(open_weather)
if air_meta.get("OpenWeather", {}).get("aqi_index"):
    ow_scale = "Index (1-5)"

om_label = format_aqi_label(om_value, om_scale)
ow_label = format_aqi_label(ow_value, ow_scale)

with st.expander("AQI Source Comparison", expanded=False):
    st.markdown(f"Best source: {best_source or 'n/a'}")
    st.caption(f"Open-Meteo AQI: {om_label}")
    st.caption(f"OpenWeather AQI: {ow_label}")
    if air_scores:
        score_m = air_scores.get("Open-Meteo", 0)
        score_w = air_scores.get("OpenWeather", 0)
        st.caption(f"Quality score: Open-Meteo {score_m:.2f} | OpenWeather {score_w:.2f}")
    if air_meta.get("OpenWeather", {}).get("aqi_index"):
        st.caption("OpenWeather AQI uses a 1-5 index.")


st.markdown("## 3D Live Map")

# MapLibre-based 3D map (free tiles + free terrain)

temp_val = current.get("temperature_2m", "n/a")
wind_val = current.get("wind_speed_10m", "n/a")
uv_val = None
try:
    uv_val = air.get("uv_index") if isinstance(air, dict) else None
except Exception:
    uv_val = None

hover_payload = {
    "temp": temp_val,
    "wind": wind_val,
    "uv": uv_val if uv_val is not None else "n/a",
    "aqi": aqi_label,
}
base_date = datetime.now(timezone.utc).date().isoformat()


html = '''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
  <script src="https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.js"></script>
  <link href="https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.css" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/@turf/turf@6/turf.min.js"></script>
  <style>
    html, body { height: 100%; margin: 0; background: #0b0f1e; }
    #map { width: 100%; height: 520px; border-radius: 18px; overflow: hidden; box-shadow: 0 18px 45px rgba(4, 8, 20, 0.6); }
    #miniMap {
      position: absolute;
      right: 18px;
      bottom: 18px;
      width: 180px;
      height: 120px;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid rgba(148, 163, 184, 0.3);
      box-shadow: 0 12px 24px rgba(4, 8, 20, 0.55);
      z-index: 4;
    }
    .map-overlay {
      position: absolute;
      top: 16px;
      left: 16px;
      background: rgba(8, 12, 24, 0.85);
      color: #e2e8f0;
      padding: 10px 12px;
      border-radius: 12px;
      font-family: 'Sora', sans-serif;
      font-size: 12px;
      border: 1px solid rgba(148, 163, 184, 0.3);
      backdrop-filter: blur(8px);
      z-index: 5;
    }
    .hover-card {
      position: absolute;
      bottom: 18px;
      left: 18px;
      background: rgba(8, 12, 24, 0.9);
      color: #e2e8f0;
      padding: 10px 12px;
      border-radius: 12px;
      font-family: 'Sora', sans-serif;
      font-size: 12px;
      border: 1px solid rgba(148, 163, 184, 0.3);
      min-width: 190px;
      z-index: 5;
    }
    .measure-box {
      position: absolute;
      bottom: 154px;
      right: 18px;
      background: rgba(8, 12, 24, 0.9);
      color: #e2e8f0;
      padding: 10px 12px;
      border-radius: 12px;
      font-family: 'Sora', sans-serif;
      font-size: 12px;
      border: 1px solid rgba(148, 163, 184, 0.3);
      min-width: 170px;
      text-align: right;
      z-index: 5;
    }
    .tool-bar {
      position: absolute;
      top: 12px;
      right: 12px;
      display: flex;
      gap: 8px;
      z-index: 6;
    }
    .tool-btn {
      background: rgba(8, 12, 24, 0.85);
      color: #e2e8f0;
      border: 1px solid rgba(148, 163, 184, 0.3);
      padding: 8px 10px;
      border-radius: 10px;
      font-family: 'Sora', sans-serif;
      font-size: 12px;
      cursor: pointer;
    }
    .tool-btn.active {
      border-color: #38bdf8;
      color: #38bdf8;
    }
    .search-box {
      position: absolute;
      top: 12px;
      left: 12px;
      z-index: 6;
      display: flex;
      gap: 6px;
    }
    .search-box input {
      background: rgba(8, 12, 24, 0.85);
      color: #e2e8f0;
      border: 1px solid rgba(148, 163, 184, 0.3);
      padding: 8px 10px;
      border-radius: 10px;
      min-width: 220px;
      font-family: 'Sora', sans-serif;
      font-size: 12px;
    }
    .search-box button {
      background: rgba(8, 12, 24, 0.85);
      color: #e2e8f0;
      border: 1px solid rgba(148, 163, 184, 0.3);
      padding: 8px 10px;
      border-radius: 10px;
      font-family: 'Sora', sans-serif;
      font-size: 12px;
      cursor: pointer;
    }
    .history-bar {
      position: absolute;
      top: 58px;
      left: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(8, 12, 24, 0.85);
      color: #e2e8f0;
      border: 1px solid rgba(148, 163, 184, 0.3);
      padding: 6px 10px;
      border-radius: 10px;
      font-family: 'Sora', sans-serif;
      font-size: 12px;
      z-index: 6;
    }
    .history-bar input { width: 140px; }
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="miniMap"></div>
  <div class="map-overlay">3D Live Map - Search - GPS - Measure</div>
  <div class="hover-card" id="hoverCard">Hover for live info</div>
  <div class="measure-box" id="measureBox">Measure: draw a line or polygon</div>
  <div class="search-box">
    <input id="searchInput" placeholder="Search location" />
    <button id="searchBtn">Search</button>
  </div>
  <div class="history-bar">
    <span>Historical</span>
    <input id="historyRange" type="range" min="0" max="30" value="0" />
    <span id="historyLabel">Today</span>
  </div>
  <div class="tool-bar">
    <button class="tool-btn" id="labelsBtn">Labels</button>
    <button class="tool-btn" id="gpsBtn">GPS</button>
    <button class="tool-btn" id="lineBtn">Measure Line</button>
    <button class="tool-btn" id="polyBtn">Measure Area</button>
    <button class="tool-btn" id="clearBtn">Clear</button>
  </div>
  <script>
    const center = [__LON__, __LAT__];
    const weather = __WEATHER__;
    const baseDate = new Date('__BASE_DATE__T00:00:00Z');

    const styleMain = {
      "version": 8,
      "sources": {
        "satellite": {
          "type": "raster",
          "tiles": ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
          "tileSize": 256,
          "attribution": "Esri"
        },
        "labels": {
          "type": "raster",
          "tiles": ["https://tiles.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png"],
          "tileSize": 256,
          "attribution": "Carto"
        },
        "gibs": {
          "type": "raster",
          "tiles": ["https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/__BASE_DATE__/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"],
          "tileSize": 256
        },
        "terrain": {
          "type": "raster-dem",
          "tiles": ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
          "tileSize": 256,
          "encoding": "terrarium"
        }
      },
      "layers": [
        { "id": "satellite", "type": "raster", "source": "satellite" },
        { "id": "gibs", "type": "raster", "source": "gibs", "layout": { "visibility": "none" } },
        { "id": "labels", "type": "raster", "source": "labels" }
      ],
      "terrain": { "source": "terrain", "exaggeration": 1.4 }
    };

    const styleMini = {
      "version": 8,
      "sources": {
        "satellite": {
          "type": "raster",
          "tiles": ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
          "tileSize": 256
        },
        "labels": {
          "type": "raster",
          "tiles": ["https://tiles.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png"],
          "tileSize": 256
        }
      },
      "layers": [
        { "id": "satellite", "type": "raster", "source": "satellite" },
        { "id": "labels", "type": "raster", "source": "labels" }
      ]
    };

    const map = new maplibregl.Map({
      container: 'map',
      style: styleMain,
      center: center,
      zoom: 11.5,
      pitch: 58,
      bearing: -10,
      antialias: true
    });

    const miniMap = new maplibregl.Map({
      container: 'miniMap',
      style: styleMini,
      center: center,
      zoom: 6,
      pitch: 0,
      bearing: 0,
      interactive: false
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 100, unit: 'metric' }));

    const marker = new maplibregl.Marker({ color: '#38bdf8' })
      .setLngLat(center)
      .addTo(map);

    const hoverCard = document.getElementById('hoverCard');
    map.on('mousemove', (e) => {
      hoverCard.innerHTML = `Lat ${e.lngLat.lat.toFixed(4)}, Lon ${e.lngLat.lng.toFixed(4)}<br>` +
        `Temp: ${weather.temp} C | AQI: ${weather.aqi} | UV: ${weather.uv} | Wind: ${weather.wind} m/s`;
    });

    map.on('move', () => {
      const c = map.getCenter();
      miniMap.jumpTo({ center: [c.lng, c.lat], zoom: Math.max(map.getZoom() - 5, 2) });
    });

    // Search (Nominatim)
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchInput');
    const doSearch = async () => {
      const q = searchInput.value.trim();
      if (!q) return;
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}`;
      const res = await fetch(url);
      const data = await res.json();
      if (data && data.length) {
        const item = data[0];
        const lng = parseFloat(item.lon);
        const lat = parseFloat(item.lat);
        map.flyTo({ center: [lng, lat], zoom: 13, essential: true });
        marker.setLngLat([lng, lat]);
      }
    };
    searchBtn.addEventListener('click', doSearch);
    searchInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });

    // GPS
    const gpsBtn = document.getElementById('gpsBtn');
    gpsBtn.addEventListener('click', () => {
      if (!navigator.geolocation) return;
      navigator.geolocation.getCurrentPosition((pos) => {
        const lng = pos.coords.longitude;
        const lat = pos.coords.latitude;
        map.flyTo({ center: [lng, lat], zoom: 14, essential: true });
        marker.setLngLat([lng, lat]);
      });
    });

    // Labels toggle
    const labelsBtn = document.getElementById('labelsBtn');
    let labelsOn = true;
    labelsBtn.classList.add('active');
    labelsBtn.addEventListener('click', () => {
      labelsOn = !labelsOn;
      map.setLayoutProperty('labels', 'visibility', labelsOn ? 'visible' : 'none');
      if (labelsOn) { labelsBtn.classList.add('active'); } else { labelsBtn.classList.remove('active'); }
    });

    // Historical imagery (GIBS)
    const historyRange = document.getElementById('historyRange');
    const historyLabel = document.getElementById('historyLabel');
    const formatDate = (d) => {
      const y = d.getUTCFullYear();
      const m = String(d.getUTCMonth() + 1).padStart(2, '0');
      const day = String(d.getUTCDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    };
    const setHistorical = (daysAgo) => {
      const d = new Date(baseDate);
      d.setUTCDate(d.getUTCDate() - daysAgo);
      const dateStr = formatDate(d);
      historyLabel.textContent = daysAgo === 0 ? 'Today' : dateStr;
      const gibs = map.getSource('gibs');
      if (gibs && gibs.setTiles) {
        gibs.setTiles([`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${dateStr}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`]);
      }
      map.setLayoutProperty('gibs', 'visibility', daysAgo === 0 ? 'none' : 'visible');
      map.setLayoutProperty('satellite', 'visibility', daysAgo === 0 ? 'visible' : 'none');
    };
    historyRange.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10) || 0;
      setHistorical(val);
    });
    setHistorical(0);

    // Simple measure tools (click to draw)
    let mode = null;
    let points = [];
    const lineId = 'measure-line';
    const polyId = 'measure-poly';

    const setMode = (m) => {
      mode = m;
      points = [];
      document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
      if (m === 'line') document.getElementById('lineBtn').classList.add('active');
      if (m === 'poly') document.getElementById('polyBtn').classList.add('active');
      if (labelsOn) labelsBtn.classList.add('active');
    };

    document.getElementById('lineBtn').addEventListener('click', () => setMode('line'));
    document.getElementById('polyBtn').addEventListener('click', () => setMode('poly'));

    const clearMeasure = () => {
      points = [];
      mode = null;
      if (map.getLayer(lineId)) map.removeLayer(lineId);
      if (map.getSource(lineId)) map.removeSource(lineId);
      if (map.getLayer(polyId)) map.removeLayer(polyId);
      if (map.getSource(polyId)) map.removeSource(polyId);
      document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
      if (labelsOn) labelsBtn.classList.add('active');
      document.getElementById('measureBox').textContent = 'Measure: draw a line or polygon';
    };
    document.getElementById('clearBtn').addEventListener('click', clearMeasure);

    const updateMeasure = () => {
      const measureBox = document.getElementById('measureBox');
      if (mode === 'line' && points.length >= 2) {
        const line = turf.lineString(points);
        const length = turf.length(line, { units: 'kilometers' });
        measureBox.textContent = `Distance: ${length.toFixed(2)} km`;
      } else if (mode === 'poly' && points.length >= 3) {
        const poly = turf.polygon([points.concat([points[0]])]);
        const area = turf.area(poly) / 1e6;
        measureBox.textContent = `Area: ${area.toFixed(2)} km^2`;
      }
    };

    map.on('click', (e) => {
      if (!mode) return;
      points.push([e.lngLat.lng, e.lngLat.lat]);

      if (mode === 'line') {
        if (map.getSource(lineId)) {
          map.getSource(lineId).setData({ type: 'Feature', geometry: { type: 'LineString', coordinates: points } });
        } else {
          map.addSource(lineId, { type: 'geojson', data: { type: 'Feature', geometry: { type: 'LineString', coordinates: points } } });
          map.addLayer({ id: lineId, type: 'line', source: lineId, paint: { 'line-color': '#38bdf8', 'line-width': 3 } });
        }
      }

      if (mode === 'poly') {
        if (points.length >= 3) {
          const coords = points.concat([points[0]]);
          if (map.getSource(polyId)) {
            map.getSource(polyId).setData({ type: 'Feature', geometry: { type: 'Polygon', coordinates: [coords] } });
          } else {
            map.addSource(polyId, { type: 'geojson', data: { type: 'Feature', geometry: { type: 'Polygon', coordinates: [coords] } } });
            map.addLayer({ id: polyId, type: 'fill', source: polyId, paint: { 'fill-color': '#22c55e', 'fill-opacity': 0.25 } });
            map.addLayer({ id: polyId + '-outline', type: 'line', source: polyId, paint: { 'line-color': '#22c55e', 'line-width': 2 } });
          }
        }
      }

      updateMeasure();
    });
  </script>
</body>
</html>'''

html = html.replace("__LAT__", f"{lat}")
html = html.replace("__LON__", f"{lon}")
html = html.replace("__WEATHER__", json.dumps(hover_payload))
html = html.replace("__BASE_DATE__", base_date)

components.html(html, height=540, scrolling=False)

st.markdown("## Satellite & Weather Map")

aqi_layer_on = st.checkbox("Show AQI layer", value=True)

current_temp = current.get("temperature_2m")
current_precip = current.get("precipitation")
current_wind = current.get("wind_speed_10m")
current_wind_dir = current.get("wind_direction_10m")
current_code = current.get("weather_code")
current_desc = weather_label(current_code)

location_label = st.session_state.preset_location
if location_label == "Custom":
    location_label = f"{lat:.3f}, {lon:.3f}"

color = temp_color(current_temp)
precip_value = float(current_precip) if current_precip not in (None, "n/a") else 0.0
radius = 2000 + min(precip_value * 2000, 12000)

popup_html = f"""
<div style="font-family: 'Space Grotesk', sans-serif; min-width: 220px;">
  <h4 style="margin: 0 0 6px 0;">{location_label}</h4>
  <div style="margin-bottom: 6px; color:#475569;">{current_desc}</div>
  <div><strong>Temp:</strong> {current_temp} C</div>
  <div><strong>Humidity:</strong> {current.get('relative_humidity_2m', 'n/a')}%</div>
  <div><strong>Wind:</strong> {current_wind} m/s</div>
  <div><strong>Precip:</strong> {current_precip} mm</div>
  <div><strong>AQI:</strong> {aqi_label}</div>
</div>
"""

gibs_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
gibs_tiles = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    f"MODIS_Terra_CorrectedReflectance_TrueColor/default/{gibs_date}/"
    "GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"
)

weather_map = folium.Map(location=[lat, lon], zoom_start=5, tiles=None, control_scale=True, prefer_canvas=True)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    name="Satellite (Esri)",
    attr="Esri",
    control=True,
    show=True,
).add_to(weather_map)
folium.TileLayer(
    tiles=gibs_tiles,
    name="Satellite (NASA GIBS)",
    attr="NASA GIBS",
    overlay=False,
    max_zoom=9,
    show=False,
).add_to(weather_map)
folium.TileLayer(
    "OpenStreetMap",
    name="Streets",
    control=True,
    show=False,
).add_to(weather_map)

folium.TileLayer(
    "CartoDB Positron",
    name="Light",
    control=True,
    show=False,
).add_to(weather_map)
folium.TileLayer(
    "CartoDB DarkMatter",
    name="Dark",
    control=True,
    show=False,
).add_to(weather_map)
folium.TileLayer(
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    name="Terrain (OpenTopo)",
    attr="OpenTopoMap",
    control=True,
    show=False,
).add_to(weather_map)

radar_time = rainviewer_latest_timestamp()
if radar_time:
    radar_tiles = (
        "https://tilecache.rainviewer.com/v2/radar/"
        f"{radar_time}/256/{{z}}/{{x}}/{{y}}/2/1_1.png"
    )
    folium.TileLayer(
        tiles=radar_tiles,
        name="Radar (RainViewer)",
        attr="RainViewer",
        overlay=True,
        opacity=0.6,
    ).add_to(weather_map)

folium.Circle(
    location=[lat, lon],
    radius=radius,
    color=color,
    weight=2,
    fill=True,
    fill_opacity=0.15,
).add_to(weather_map)

folium.CircleMarker(
    location=[lat, lon],
    radius=9,
    color=color,
    fill=True,
    fill_color=color,
    fill_opacity=0.85,
).add_to(weather_map)

if aqi_layer_on and aqi_value is not None:
    aqi_radius = 1400 + min(aqi_value, 320) * 18
    folium.Circle(
        location=[lat, lon],
        radius=aqi_radius,
        color=aqi_color,
        weight=2,
        fill=True,
        fill_color=aqi_color,
        fill_opacity=max(0.18, aqi_opacity),
    ).add_to(weather_map)
    folium.CircleMarker(
        location=[lat, lon],
        radius=7,
        color=aqi_color,
        fill=True,
        fill_color=aqi_color,
        fill_opacity=0.9,
    ).add_to(weather_map)

gps_accuracy_m = st.session_state.get("gps_accuracy_m")
if st.session_state.gps_enabled and gps_accuracy_m:
    folium.Circle(
        location=[lat, lon],
        radius=float(gps_accuracy_m),
        color="#38bdf8",
        weight=1,
        fill=True,
        fill_opacity=0.08,
        dash_array="4,4",
    ).add_to(weather_map)

folium.Marker(
    [lat, lon],
    tooltip=f"{location_label} | {current_desc}",
    popup=folium.Popup(popup_html, max_width=320),
).add_to(weather_map)

wind_target = wind_endpoint(lat, lon, current_wind, current_wind_dir)
if wind_target:
    target_lat, target_lon, bearing = wind_target
    folium.PolyLine(
        [(lat, lon), (target_lat, target_lon)],
        color="#38bdf8",
        weight=3,
        opacity=0.85,
    ).add_to(weather_map)
    folium.RegularPolygonMarker(
        location=[target_lat, target_lon],
        number_of_sides=3,
        radius=6,
        rotation=bearing,
        color="#38bdf8",
        fill=True,
        fill_color="#38bdf8",
    ).add_to(weather_map)

MiniMap(toggle_display=True).add_to(weather_map)
Fullscreen(position="topleft").add_to(weather_map)
MeasureControl(position="topright", primary_length_unit="kilometers").add_to(weather_map)
MousePosition(position="bottomright").add_to(weather_map)
folium.LatLngPopup().add_to(weather_map)
folium.LayerControl(collapsed=True).add_to(weather_map)

st_folium(weather_map, height=520, use_container_width=True)
st.caption(
    f"Satellite imagery: Esri (default) with NASA GIBS optional. Radar: RainViewer. Base maps: OSM, Carto, OpenTopo. AQI source: {best_source or 'n/a'}."
)

st.markdown("## Forecast Charts")
chart_choice = st.radio(
    "Graph",
    ["Temperature (72h Forecast)", "AQI (Dataset History)"],
    horizontal=True,
)

if chart_choice == "Temperature (72h Forecast)":
    if hourly and "time" in hourly:
        hourly_df = pd.DataFrame(hourly)
        hourly_df["time"] = pd.to_datetime(hourly_df["time"])
        hourly_df = hourly_df.head(72)
        fig = px.line(
            hourly_df,
            x="time",
            y="temperature_2m",
            title="Next 72 Hours Temperature",
            labels={"temperature_2m": "Temp (C)", "time": ""},
        )
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hourly forecast available for temperature.")
else:
    dataset_df, dataset_source = cached_dataset()
    if "aqi" not in dataset_df.columns:
        st.info("AQI history is not yet available in the dataset.")
    else:
        aqi_df = dataset_df.tail(240).copy()
        aqi_df["time"] = pd.to_datetime(aqi_df["time"], errors="coerce")
        aqi_df = aqi_df.dropna(subset=["time"]).sort_values("time")
        fig = px.line(
            aqi_df,
            x="time",
            y="aqi",
            title="AQI History (Last 240 Hours)",
            labels={"aqi": "AQI", "time": ""},
        )
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"AQI source: {dataset_source}")
