from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.data import summarize_dataset
from src.layout import apply_global_styles, nav_bar, setup_state, sidebar_controls
from src.services import cached_dataset


st.set_page_config(page_title="AI Weather Forecast - Data Lab", layout="wide")

setup_state()
sidebar_controls()
apply_global_styles()
nav_bar()

st.markdown("## Data Lab")

df, source = cached_dataset()
summary = summarize_dataset(df)

st.markdown(
    """
    <div class="glass-card">
        <p class="subtle">Rows: {rows} | Range: {start} to {end}</p>
        <p class="subtle">Columns: {cols}</p>
        <p class="subtle">Source: {source}</p>
    </div>
    """.format(
        rows=summary["rows"],
        start=summary["start"],
        end=summary["end"],
        cols=", ".join(summary["columns"]),
        source=source,
    ),
    unsafe_allow_html=True,
)

metric_map = {
    "Temperature (C)": "temperature_2m",
    "Humidity (%)": "relative_humidity_2m",
    "Precipitation (mm)": "precipitation",
    "Wind Speed (m/s)": "wind_speed_10m",
}
if "aqi" in df.columns:
    metric_map["AQI (Index)"] = "aqi"

metric_label = st.selectbox("Metric", list(metric_map.keys()))
metric = metric_map[metric_label]

sample = df.tail(500)
fig = px.line(sample, x="time", y=metric, title=f"{metric_label} History")
fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
st.plotly_chart(fig, use_container_width=True)

st.dataframe(df.tail(25), use_container_width=True)
