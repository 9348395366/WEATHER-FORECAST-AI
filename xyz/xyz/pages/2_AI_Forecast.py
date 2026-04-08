from __future__ import annotations

import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit.components.v1 import html as st_html

from src.layout import apply_global_styles, nav_bar, setup_state, sidebar_controls
from src.modeling import predict_next_hours, predict_next_hours_aqi
from src.services import cached_aqi_model, cached_current, cached_dataset, cached_model


@st.cache_data(ttl=3600)
def cached_monthly_overview(df: pd.DataFrame, year: int, month: int) -> tuple[dict, pd.DataFrame]:
    month_df = df[(df["time"].dt.year == year) & (df["time"].dt.month == month)]
    daily = (
        month_df
        .set_index("time")
        .resample("D")
        .agg(
            temp_mean=("temperature_2m", "mean"),
            humidity_mean=("relative_humidity_2m", "mean"),
            precip_sum=("precipitation", "sum"),
        )
        .dropna(how="all")
    )

    def classify_day(row):
        if pd.isna(row["temp_mean"]) or pd.isna(row["precip_sum"]) or pd.isna(row["humidity_mean"]):
            return "Unknown"
        if row["precip_sum"] >= 1.0 and row["temp_mean"] <= 2.0:
            return "Snowy"
        if row["precip_sum"] >= 1.0:
            return "Rainy"
        if row["humidity_mean"] >= 75:
            return "Cloudy"
        return "Sunny"

    if not daily.empty:
        daily = daily.copy()
        daily["category"] = daily.apply(classify_day, axis=1)
        counts = daily["category"].value_counts().to_dict()
    else:
        counts = {}
    return counts, daily


@st.cache_data(ttl=3600)
def build_donut_svg(values, colors):
    total = sum(values)
    if total <= 0:
        total = 1
    radius = 46
    circ = 2 * math.pi * radius
    start = 0.0
    segs = []
    for idx, (value, color) in enumerate(zip(values, colors)):
        dash = (value / total) * circ
        offset = -start
        delay = idx * 0.12
        segs.append(
            f"<circle class='donut-seg' cx='60' cy='60' r='{radius}' style='--dash:{dash:.2f}; --offset:{offset:.2f}; --delay:{delay:.2f}s; stroke:{color};'></circle>"
        )
        start += dash
    svg = (
        "<div class='donut-wrap'>"
        f"<svg class='donut-svg' viewBox='0 0 120 120' style='--circ:{circ:.2f};' aria-label='Monthly weather overview'>"
        "<circle class='donut-ring' cx='60' cy='60' r='46'></circle>"
        + "".join(segs)
        + "</svg></div>"
    )
    return svg


def cached_daily_history(df: pd.DataFrame) -> pd.DataFrame:
    agg_map = {
        "temp_max": ("temperature_2m", "max"),
        "temp_min": ("temperature_2m", "min"),
        "precip_sum": ("precipitation", "sum"),
        "humidity_mean": ("relative_humidity_2m", "mean"),
        "wind_mean": ("wind_speed_10m", "mean"),
    }
    if "aqi" in df.columns:
        agg_map["aqi_mean"] = ("aqi", "mean")

    daily_hist = (
        df.set_index("time")
        .resample("D")
        .agg(**agg_map)
        .dropna()
    )
    return daily_hist.tail(365)


st.set_page_config(page_title="AI Weather Forecast - AI Forecast", layout="wide")

setup_state()
sidebar_controls()
apply_global_styles()
nav_bar()

st.markdown(
    """
    <style>
    .ai-section-title { font-size: 1.15rem; font-weight: 600; margin: 0.5rem 0 0.75rem; }
    .overview-card { background: rgba(18, 25, 40, 0.88); border: 1px solid rgba(148,163,184,0.25); border-radius: 24px; padding: 1.2rem 1.4rem; box-shadow: 0 18px 40px rgba(8,12,24,0.45); }
    .overview-title { font-size: 1.6rem; font-weight: 600; margin-bottom: 0.6rem; }
    .overview-sub { color: #cbd5f5; margin-bottom: 0.4rem; }
    .overview-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 1.2rem; align-items: center; }
    .overview-counts { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; }
    .count-card { display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 0.8rem; border-radius: 14px; background: rgba(255,255,255,0.06); border: 1px solid rgba(148,163,184,0.25); }
    .count-label { display: flex; align-items: center; gap: 0.5rem; font-weight: 600; }
    .count-chip { min-width: 46px; text-align: center; font-weight: 700; padding: 0.35rem 0.6rem; border-radius: 10px; }
    .chip-sun { background: #f97316; color: #1f2937; }
    .chip-cloud { background: #94a3ff; color: #0f172a; }
    .chip-rain { background: #3b82f6; color: #e2e8f0; }
    .chip-snow { background: #22d3ee; color: #0f172a; }
    .trend-card { background: rgba(18, 25, 40, 0.8); border: 1px solid rgba(148,163,184,0.2); border-radius: 18px; padding: 0.8rem 1rem; }
    .ai-hero { text-align: center; margin: 0.6rem 0 1.2rem; }
    .ai-hero h2 { font-size: 2.2rem; margin-bottom: 0.4rem; }
    .ai-hero-line
    .ai-hero-card { position: relative; margin: 0.6rem auto 1.4rem; padding: 1.4rem 1.8rem; border-radius: 22px; text-align: center; background: rgba(17, 24, 39, 0.75); backdrop-filter: blur(16px); }
    .ai-hero-card::before { content: ""; position: absolute; inset: -2px; border-radius: 24px; padding: 2px; background: linear-gradient(90deg, #f97316, #38bdf8, #a855f7, #22c55e, #f97316); -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude; filter: drop-shadow(0 0 14px rgba(56,189,248,0.7)); }
    .ai-hero-title { font-size: 2.1rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
    .ai-hero-sub { margin-top: 0.35rem; color: #cbd5f5; font-size: 0.95rem; }
 { width: 220px; height: 4px; margin: 0 auto; border-radius: 999px; background: linear-gradient(90deg, #f97316, #38bdf8, #a855f7, #22c55e, #f97316); box-shadow: 0 0 14px rgba(56,189,248,0.6); }
    .donut-wrap { display: grid; place-items: center; }
    .donut-svg { width: 220px; height: 220px; }
    .donut-ring { fill: none; stroke: rgba(255,255,255,0.22); stroke-width: 14; }
    .donut-seg { fill: none; stroke-width: 14; stroke-linecap: butt; transform: rotate(-90deg); transform-origin: 50% 50%; stroke-dasharray: 0 var(--circ); stroke-dashoffset: var(--offset); animation: donutGrow 1.1s ease forwards; animation-delay: var(--delay); }
    .donut-seg + .donut-seg { filter: drop-shadow(0 2px 4px rgba(0,0,0,0.25)); }
    @keyframes donutGrow { to { stroke-dasharray: var(--dash) var(--circ); } }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("""<div class="ai-hero"><h2>AI Weather Forecast</h2><div class="ai-hero-line"></div></div>""", unsafe_allow_html=True)

df, source = cached_dataset()
model = cached_model()
aqi_model = cached_aqi_model()

tabs = st.tabs(["Forecast", "Data Analysis"])

with tabs[0]:
    if model is None:
        st.markdown(
            """
            <div class="glass-card">
                <p class="subtle">No trained model found yet.</p>
                <p>Run <code>python scripts/train_model.py</code> to build the model.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time")

    st.markdown("### Monthly Weather Overview")

    if df.empty:
        st.info("No data available to build the overview.")
    else:
        month_options = (
            df["time"].dt.to_period("M").dropna().sort_values().unique()
        )
        month_labels = [str(p) for p in month_options]
        default_idx = len(month_labels) - 1 if month_labels else 0
        month_choice = st.selectbox("Select Month", month_labels, index=default_idx)
        period = pd.Period(month_choice)

        counts, daily = cached_monthly_overview(df, period.year, period.month)
        sunny = counts.get("Sunny", 0)
        cloudy = counts.get("Cloudy", 0)
        rainy = counts.get("Rainy", 0)
        snowy = counts.get("Snowy", 0)

        labels = ["Sunny", "Cloudy", "Rainy", "Snowy"]
        values = [sunny, cloudy, rainy, snowy]
        colors = ["#f97316", "#94a3ff", "#3b82f6", "#22d3ee"]
        donut_svg = build_donut_svg(values, colors)

        pie_fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.35,
                    marker=dict(colors=colors, line=dict(color="rgba(255,255,255,0.5)", width=1)),
                    textinfo="none",
                )
            ]
        )
        pie_fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=240,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        summary = (
            f"The monthly overview for {period.strftime('%B %Y')} shows {sunny} sunny days, "
            f"{cloudy} cloudy days, {rainy} rainy days, and {snowy} snowy days."
        )

        st.markdown(
            """
            <div class='overview-card'>
              <div class='overview-title'>{title}</div>
              <div class='overview-sub'>{subtitle}</div>
              <div class='overview-grid'>
                <div>{pie}</div>
                <div>
                  <div class='overview-sub'>No. of days:</div>
                  <div class='overview-counts'>
                    <div class='count-card'>
                      <div class='count-label'>??? Sunny</div>
                      <div class='count-chip chip-sun'>{sunny}</div>
                    </div>
                    <div class='count-card'>
                      <div class='count-label'>?? Cloudy</div>
                      <div class='count-chip chip-cloud'>{cloudy}</div>
                    </div>
                    <div class='count-card'>
                      <div class='count-label'>??? Rainy</div>
                      <div class='count-chip chip-rain'>{rainy}</div>
                    </div>
                    <div class='count-card'>
                      <div class='count-label'>?? Snowy</div>
                      <div class='count-chip chip-snow'>{snowy}</div>
                    </div>
                  </div>
                  <p style='margin-top:0.8rem; color:#cbd5f5;'>{summary}</p>
                </div>
              </div>
            </div>
            """.format(
                title=f"{period.strftime('%B')} Weather Overview",
                subtitle=period.strftime('%B %Y'),
                pie=donut_svg,
                sunny=sunny,
                cloudy=cloudy,
                rainy=rainy,
                snowy=snowy,
                summary=summary,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("### AI Forecast (Next 24 Hours)")
    st.caption("Auto-updates every 60s using the latest current conditions for the selected location.")
    if not st.session_state.get("performance_mode"):
        st_html("<meta http-equiv='refresh' content='60'>", height=0)
    else:
        st.caption("Performance Mode is on ? auto-refresh paused.")
    lat = st.session_state.get("lat")
    lon = st.session_state.get("lon")
    current = {}
    if lat is not None and lon is not None:
        try:
            current = cached_current(float(lat), float(lon))
        except Exception:
            current = {}

    history = df.tail(168).copy()
    history["time"] = pd.to_datetime(history["time"], errors="coerce")
    history = history.dropna(subset=["time"]).sort_values("time")

    if current:
        cur_time = pd.to_datetime(current.get("time"), errors="coerce")
        if cur_time is pd.NaT or cur_time is None:
            cur_time = pd.Timestamp.now()
        if history.empty:
            history = pd.DataFrame([{
                "time": cur_time,
                "temperature_2m": float(current.get("temperature_2m", 0.0)),
                "relative_humidity_2m": float(current.get("relative_humidity_2m", 0.0)),
                "precipitation": float(current.get("precipitation", 0.0)),
                "wind_speed_10m": float(current.get("wind_speed_10m", 0.0)),
            }])
        else:
            last = history.iloc[-1]
            current_row = {
                "time": cur_time,
                "temperature_2m": float(current.get("temperature_2m", last["temperature_2m"])),
                "relative_humidity_2m": float(current.get("relative_humidity_2m", last["relative_humidity_2m"])),
                "precipitation": float(current.get("precipitation", last["precipitation"])),
                "wind_speed_10m": float(current.get("wind_speed_10m", last["wind_speed_10m"])),
            }
            if cur_time > last["time"]:
                history = pd.concat([history, pd.DataFrame([current_row])], ignore_index=True)
            else:
                for key, value in current_row.items():
                    history.loc[history.index[-1], key] = value

    if len(history) < 48:
        st.warning("Need at least 48 hours of history to run AI prediction.")
        st.stop()

    try:
        forecast_96 = predict_next_hours(model, history, hours=96)
        forecast_24 = forecast_96.head(24)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    history_plot = history.tail(72).copy()
    history_plot["series"] = "History"
    forecast_plot = forecast_24.copy()
    forecast_plot["series"] = "AI Forecast"
    combined = pd.concat(
        [history_plot[["time", "temperature_2m", "series"]], forecast_plot],
        ignore_index=True,
    )

    fig = px.line(
        combined,
        x="time",
        y="temperature_2m",
        color="series",
        title="History vs AI Forecast (Next 24 Hours)",
        labels={"temperature_2m": "Temp (C)", "time": ""},
    )
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### AI AQI Forecast (Next 24 Hours)")
    if "aqi" not in df.columns:
        st.info("AQI history not found in the dataset yet.")
    elif aqi_model is None:
        st.markdown(
            """
            <div class="glass-card">
                <p class="subtle">No trained AQI model found yet.</p>
                <p>Run <code>python scripts/train_model.py</code> to build it.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        aqi_history = df.tail(168).copy()
        aqi_history["time"] = pd.to_datetime(aqi_history["time"], errors="coerce")
        aqi_history = aqi_history.dropna(subset=["time"]).sort_values("time")

        if len(aqi_history) < 48:
            st.warning("Need at least 48 hours of AQI history to run AI prediction.")
        else:
            try:
                aqi_forecast = predict_next_hours_aqi(aqi_model, aqi_history, hours=24)
            except ValueError as exc:
                st.error(str(exc))
            else:
                aqi_history_plot = aqi_history.tail(72).copy()
                aqi_history_plot["series"] = "History"
                aqi_forecast_plot = aqi_forecast.copy()
                aqi_forecast_plot["series"] = "AI Forecast"
                combined_aqi = pd.concat(
                    [aqi_history_plot[["time", "aqi", "series"]], aqi_forecast_plot],
                    ignore_index=True,
                )

                fig_aqi = px.line(
                    combined_aqi,
                    x="time",
                    y="aqi",
                    color="series",
                    title="AQI History vs AI Forecast (Next 24 Hours)",
                    labels={"aqi": "AQI", "time": ""},
                )
                fig_aqi.update_layout(margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_aqi, use_container_width=True)

    st.markdown("### AI Forecast (Next 4 Days)")
    forecast_96["date"] = pd.to_datetime(forecast_96["time"]).dt.date
    daily_pred = (
        forecast_96.groupby("date")["temperature_2m"]
        .agg(["min", "max", "mean"])
        .reset_index()
        .head(4)
    )

    if not daily_pred.empty:
        fig_days = go.Figure()
        fig_days.add_trace(
            go.Scatter(
                x=daily_pred["date"],
                y=daily_pred["max"],
                name="Daily high",
                line=dict(color="#f97316", width=2),
            )
        )
        fig_days.add_trace(
            go.Scatter(
                x=daily_pred["date"],
                y=daily_pred["min"],
                name="Daily low",
                line=dict(color="#60a5fa", width=2),
                fill="tonexty",
                fillcolor="rgba(96,165,250,0.18)",
            )
        )
        fig_days.add_trace(
            go.Scatter(
                x=daily_pred["date"],
                y=daily_pred["mean"],
                name="Daily mean",
                line=dict(color="rgba(255,255,255,0.85)", width=1.5, dash="dot"),
            )
        )
        fig_days.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=30, b=10),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
        )
        st.plotly_chart(fig_days, use_container_width=True)
    else:
        st.info("Not enough data to build the 4 day forecast yet.")

    st.markdown("### Weather Trends")

    metric_map = {
        "Temperature": "temperature_2m",
        "Precipitation": "precipitation",
        "Humidity": "relative_humidity_2m",
        "Wind": "wind_speed_10m",
    }
    if "aqi" in df.columns:
        metric_map["AQI"] = "aqi"
    metric_choice = st.radio("Metric", list(metric_map.keys()), horizontal=True)

    daily_hist = cached_daily_history(df)

    if metric_choice == "Temperature":
        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Scatter(
                x=daily_hist.index,
                y=daily_hist["temp_max"],
                name="Daily high",
                line=dict(color="#ef4444", width=1.5),
            )
        )
        fig_trend.add_trace(
            go.Scatter(
                x=daily_hist.index,
                y=daily_hist["temp_min"],
                name="Daily low",
                line=dict(color="#3b82f6", width=1.5),
                fill="tonexty",
                fillcolor="rgba(59,130,246,0.12)",
            )
        )

        show_30d_band = st.checkbox("Show 30 day AI band (slower)", value=False)
        daily_hist["high_ma"] = daily_hist["temp_max"].rolling(30, min_periods=1).mean()
        daily_hist["low_ma"] = daily_hist["temp_min"].rolling(30, min_periods=1).mean()
        fig_trend.add_trace(
            go.Scatter(
                x=daily_hist.index,
                y=daily_hist["high_ma"],
                name="Historical daily high",
                line=dict(color="rgba(255,255,255,0.8)", width=1.5, dash="dot"),
            )
        )
        fig_trend.add_trace(
            go.Scatter(
                x=daily_hist.index,
                y=daily_hist["low_ma"],
                name="Historical daily low",
                line=dict(color="rgba(255,255,255,0.8)", width=1.5, dash="dot"),
            )
        )

        if show_30d_band:
            try:
                forecast_30d = predict_next_hours(model, df.tail(240), hours=24 * 30)
                forecast_30d["date"] = pd.to_datetime(forecast_30d["time"]).dt.date
                forecast_daily = forecast_30d.groupby("date")["temperature_2m"].agg(["max", "min"]).reset_index()
                fig_trend.add_trace(
                    go.Scatter(
                        x=forecast_daily["date"],
                        y=forecast_daily["max"],
                        name="30 day forecast (high)",
                        line=dict(color="#f97316", width=2, dash="dot"),
                    )
                )
                fig_trend.add_trace(
                    go.Scatter(
                        x=forecast_daily["date"],
                        y=forecast_daily["min"],
                        name="30 day forecast (low)",
                        line=dict(color="#60a5fa", width=2, dash="dot"),
                    )
                )
            except Exception:
                pass

        fig_trend.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=30, b=10),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        metric_col = {
            "Precipitation": "precip_sum",
            "Humidity": "humidity_mean",
            "Wind": "wind_mean",
            "AQI": "aqi_mean",
        }[metric_choice]
        series = daily_hist[metric_col]
        roll = series.rolling(30, min_periods=1).mean()
        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Scatter(
                x=daily_hist.index,
                y=series,
                name=metric_choice,
                line=dict(color="#60a5fa", width=2),
            )
        )
        fig_trend.add_trace(
            go.Scatter(
                x=daily_hist.index,
                y=roll,
                name="Historical average",
                line=dict(color="rgba(255,255,255,0.8)", width=1.5, dash="dot"),
            )
        )
        fig_trend.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=30, b=10),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        if metric_choice != "AQI":
            st.caption("AI forecast is currently available for temperature only.")

    st.caption(f"Training data source: {source}")

with tabs[1]:
    st.markdown("### Data Analysis")

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

    window = st.slider("Rolling Window (hours)", min_value=6, max_value=72, value=24, step=6)

    analysis = df.tail(500).copy()
    analysis["time"] = pd.to_datetime(analysis["time"])
    analysis["rolling_mean"] = analysis[metric].rolling(window=window).mean()

    fig_trend = px.line(
        analysis,
        x="time",
        y=[metric, "rolling_mean"],
        title=f"{metric_label} Trend (last 500 hours)",
        labels={"value": metric_label, "time": ""},
    )
    fig_trend.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_trend, use_container_width=True)

    fig_hist = px.histogram(
        df,
        x=metric,
        nbins=30,
        title=f"{metric_label} Distribution",
        labels={metric: metric_label},
    )
    fig_hist.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_hist, use_container_width=True)
