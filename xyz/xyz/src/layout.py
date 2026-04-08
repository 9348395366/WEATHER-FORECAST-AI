from __future__ import annotations

import os
import streamlit as st

from .constants import (
    INDIA_STATES,
    LOCATIONS,
    LOCATION_QUERIES,
    NAV_LINKS,
    ODISHA_COORDS,
    ODISHA_DISTRICTS,
    ODISHA_LABEL,
)
from .services import cached_forward_geocode
from .ui import inject_click_sound, inject_theme


def setup_state() -> None:
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    if "unit" not in st.session_state:
        st.session_state.unit = "C"
    if "performance_mode" not in st.session_state:
        st.session_state.performance_mode = False
    if "openweather_key" not in st.session_state:
        secret_key = st.secrets.get("OPENWEATHER_API_KEY", "") if hasattr(st, "secrets") else ""
        st.session_state.openweather_key = secret_key or os.getenv("OPENWEATHER_API_KEY", "")
    if "prefer_openweather" not in st.session_state:
        st.session_state.prefer_openweather = False
    if "odisha_only" not in st.session_state:
        st.session_state.odisha_only = False
    if "prev_lat" not in st.session_state:
        st.session_state.prev_lat = None
    if "prev_lon" not in st.session_state:
        st.session_state.prev_lon = None
    if "prev_preset" not in st.session_state:
        st.session_state.prev_preset = None
    if "gps_enabled" not in st.session_state:
        st.session_state.gps_enabled = False
    if "gps_has_location" not in st.session_state:
        st.session_state.gps_has_location = False
    if "gps_accuracy_m" not in st.session_state:
        st.session_state.gps_accuracy_m = None
    if "gps_error" not in st.session_state:
        st.session_state.gps_error = None
        st.session_state.gps_pending = False

    if "gps_last_ts" not in st.session_state:
        st.session_state.gps_last_ts = None
    if "gps_pending" not in st.session_state:
        st.session_state.gps_pending = False
    if "lat" not in st.session_state:
        st.session_state.lat = ODISHA_COORDS[0]
    if "lon" not in st.session_state:
        st.session_state.lon = ODISHA_COORDS[1]

    if st.session_state.prev_lat is None:
        st.session_state.prev_lat = st.session_state.lat
    if st.session_state.prev_lon is None:
        st.session_state.prev_lon = st.session_state.lon
    if "preset_location" not in st.session_state:
        st.session_state.preset_location = ODISHA_LABEL
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_pending" not in st.session_state:
        st.session_state.chat_pending = False

    if "area_state" not in st.session_state:
        st.session_state.area_state = "Odisha"
    if "area_district_odisha" not in st.session_state:
        st.session_state.area_district_odisha = ODISHA_DISTRICTS[0] if ODISHA_DISTRICTS else ""
    if "area_district_other" not in st.session_state:
        st.session_state.area_district_other = ""
    if "area_query" not in st.session_state:
        st.session_state.area_query = ""
    if "area_status" not in st.session_state:
        st.session_state.area_status = None
    if "area_status_ok" not in st.session_state:
        st.session_state.area_status_ok = None

    if "pending_lat" not in st.session_state:
        st.session_state.pending_lat = None
    if "pending_lon" not in st.session_state:
        st.session_state.pending_lon = None


def apply_odisha_toggle() -> None:
    if st.session_state.odisha_only:
        st.session_state.prev_lat = st.session_state.lat
        st.session_state.prev_lon = st.session_state.lon
        st.session_state.prev_preset = st.session_state.preset_location
        st.session_state.lat, st.session_state.lon = ODISHA_COORDS
        st.session_state.preset_location = ODISHA_LABEL
        st.session_state.gps_enabled = False
        st.session_state.gps_has_location = False
        st.session_state.gps_error = None
        st.session_state.gps_pending = False
    else:
        if st.session_state.prev_lat is not None and st.session_state.prev_lon is not None:
            st.session_state.lat = st.session_state.prev_lat
            st.session_state.lon = st.session_state.prev_lon
        st.session_state.preset_location = st.session_state.prev_preset or 'Custom'


def apply_preset() -> None:
    if st.session_state.odisha_only:
        st.session_state.preset_location = ODISHA_LABEL
        st.session_state.lat, st.session_state.lon = ODISHA_COORDS
        return

    preset = st.session_state.preset_location
    if preset == 'Custom':
        return
    if preset == ODISHA_LABEL:
        st.session_state.lat, st.session_state.lon = ODISHA_COORDS
        return

    lat_lon = LOCATIONS.get(preset)
    if lat_lon:
        st.session_state.lat, st.session_state.lon = lat_lon
        return

    query = LOCATION_QUERIES.get(preset)
    if not query:
        return
    coords = cached_forward_geocode(query)
    if coords:
        st.session_state.lat, st.session_state.lon = coords


def _normalize_area_part(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def _normalize_district(state: str, district: str | None) -> str | None:
    cleaned = _normalize_area_part(district)
    if not cleaned:
        return None
    if state == "Odisha":
        cleaned = cleaned.split(" (", 1)[0].strip()
    return cleaned if cleaned else None


def _build_area_query(state: str, district: str | None, area: str | None) -> str:
    parts: list[str] = []
    area_clean = _normalize_area_part(area)
    if area_clean:
        parts.append(area_clean)
    district_clean = _normalize_district(state, district)
    if district_clean:
        parts.append(district_clean)
    if state:
        parts.append(state)
    parts.append("India")
    return ", ".join(parts)


def apply_area_search(state: str, district: str | None, area: str | None) -> None:
    if st.session_state.odisha_only:
        st.session_state.area_status = "Search is disabled right now."
        st.session_state.area_status_ok = False
        return

    query = _build_area_query(state, district, area)
    coords = cached_forward_geocode(query)
    if coords:
        st.session_state.pending_lat, st.session_state.pending_lon = coords
        st.session_state.area_status = f"Location set: {query}"
        st.session_state.area_status_ok = True
        st.rerun()
    else:
        st.session_state.area_status = "No matching location found. Try a different spelling."
        st.session_state.area_status_ok = False


def _apply_pending_location() -> None:
    pending_lat = st.session_state.get("pending_lat")
    pending_lon = st.session_state.get("pending_lon")
    if pending_lat is None or pending_lon is None:
        return
    st.session_state.lat = float(pending_lat)
    st.session_state.lon = float(pending_lon)
    st.session_state.preset_location = "Custom"
    st.session_state.pending_lat = None
    st.session_state.pending_lon = None


def sidebar_controls() -> None:

    _apply_pending_location()

    with st.sidebar:
        st.markdown("### Controls")
        dark_mode = st.toggle("Dark Mode", value=st.session_state.theme == "dark")
        st.session_state.theme = "dark" if dark_mode else "light"

        st.toggle("Performance Mode", key="performance_mode", help="Reduce animations and heavy effects for smoother performance.")

        st.markdown("---")
        st.markdown("### Data Sources")
        has_openweather_key = bool(st.session_state.openweather_key)
        st.toggle(
            "Prefer OpenWeatherMap",
            key="prefer_openweather",
            disabled=not has_openweather_key,
            help="Requires an OpenWeather One Call 3.0 plan. When off, the app uses Open-Meteo only.",
        )
        if not has_openweather_key:
            st.caption("Add OPENWEATHER_API_KEY in .streamlit/secrets.toml to enable OpenWeather.")

        st.markdown("---")
        st.selectbox(
            "Quick Location",
            options=list(LOCATIONS.keys()),
            key="preset_location",
            on_change=apply_preset,
            disabled=st.session_state.odisha_only,
        )
        st.number_input("Latitude", key="lat", format="%.4f", disabled=st.session_state.odisha_only)
        st.number_input("Longitude", key="lon", format="%.4f", disabled=st.session_state.odisha_only)
        st.caption("Tip: Use a preset, then fine-tune coordinates.")

        st.markdown("---")
        st.markdown("### Area Search")
        state = st.selectbox(
            "State",
            options=INDIA_STATES,
            key="area_state",
            disabled=st.session_state.odisha_only,
        )
        if state == "Odisha":
            district = st.selectbox(
                "District",
                options=ODISHA_DISTRICTS,
                key="area_district_odisha",
                disabled=st.session_state.odisha_only,
            )
        else:
            district = st.text_input(
                "District (optional)",
                key="area_district_other",
                disabled=st.session_state.odisha_only,
                placeholder="e.g., Pune",
            )
        area = st.text_input(
            "Area / City",
            key="area_query",
            disabled=st.session_state.odisha_only,
            placeholder="e.g., Sector 62",
        )
        if st.button("Search Area", use_container_width=True, disabled=st.session_state.odisha_only):
            apply_area_search(state, district, area)

        status = st.session_state.area_status
        if status:
            if st.session_state.area_status_ok:
                st.success(status)
            else:
                st.warning(status)
        if st.session_state.odisha_only:
            st.caption("Search is disabled right now.")


def apply_global_styles() -> None:
    inject_theme(st.session_state.theme)
    inject_click_sound()


def nav_bar() -> None:
    cols = st.columns(len(NAV_LINKS))
    for col, (label, path) in zip(cols, NAV_LINKS):
        with col:
            if st.button(label, key=f"nav_{label}"):
                st.switch_page(path)


def hero() -> None:
    st.markdown(
        """
        <div class="glass-hero">
            <h1 class="hero-title-3d">AI Weather Forecast</h1>
            <p class="subtle">Real-time conditions, AI forecasting, and a glassmorphism UI with ambient glow.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
