from __future__ import annotations

import streamlit as st

from src.layout import apply_global_styles, nav_bar, setup_state, sidebar_controls


st.set_page_config(page_title="AI Weather Forecast - About", layout="wide")

setup_state()
sidebar_controls()
apply_global_styles()
nav_bar()

st.markdown("## About")
st.markdown(
    """
    <div class="glass-card">
        <p>AI Weather Forecast blends real-time weather data, a local ML model, and a glassmorphism UI.</p>
        <ul>
            <li>Live core data from Open-Meteo.</li>
            <li>Offline-ready synthetic data generator for big-data experiments.</li>
            <li>Agent chat routes queries to data, forecast, and model tools.</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True,
)
