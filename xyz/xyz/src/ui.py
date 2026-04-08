from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def inject_theme(theme: str) -> None:
    dark = theme == "dark"
    reduce_motion = bool(st.session_state.get("performance_mode"))
    reduce_motion_css = ""
    if reduce_motion:
        reduce_motion_css = """
    * {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
    }

    .glass-card, .glass-hero, .mini-card, [data-testid="stPlotlyChart"] > div {
        box-shadow: none !important;
        backdrop-filter: none !important;
    }

    .astro-orb, .cloud-anim, .wind-rotor {
        animation: none !important;
    }

    """
    if dark:
        extra_css = ""
    else:
        extra_css = """
    /* Light mode glassmorphism + ambient glow */
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        inset: -10% -10% -20% -10%;
        background:
            radial-gradient(400px 280px at 10% 20%, rgba(255, 198, 236, 0.55), transparent 60%),
            radial-gradient(420px 300px at 85% 10%, rgba(120, 211, 255, 0.45), transparent 60%),
            radial-gradient(520px 360px at 60% 80%, rgba(110, 231, 183, 0.35), transparent 65%);
        pointer-events: none;
        z-index: 0;
    }

    [data-testid="stAppViewContainer"] > div:first-child {
        position: relative;
        z-index: 1;
    }


    /* Light mode text contrast */
    .glass-card *, .glass-hero *, .mini-card * {
        color: var(--text) !important;
    }

    .subtle {
        color: var(--subtext) !important;
    }

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: var(--text) !important;
    }


    /* Plotly text contrast */
    [data-testid="stPlotlyChart"] text {
        fill: var(--text) !important;
    }
    [data-testid="stPlotlyChart"] .xtick text,
    [data-testid="stPlotlyChart"] .ytick text,
    [data-testid="stPlotlyChart"] .legend text {
        fill: var(--subtext) !important;
    }

            .glass-card, .glass-hero, .mini-card, [data-testid="stPlotlyChart"] > div {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, rgba(255,255,255,0.72), rgba(230, 240, 255, 0.45));
        border: 1px solid rgba(99, 102, 241, 0.22);
        box-shadow: 0 20px 45px rgba(99, 102, 241, 0.18), 0 0 0 1px rgba(255,255,255,0.6) inset;
    }

    .glass-card::before, .glass-hero::before, .mini-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(120deg, rgba(255,255,255,0.7), rgba(255,255,255,0.05));
        opacity: 0.45;
        pointer-events: none;
    }

    button, button[kind="primary"] {
        background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(214, 232, 255, 0.9));
        border: 1px solid rgba(59, 130, 246, 0.25) !important;
        box-shadow: 0 12px 24px rgba(59, 130, 246, 0.16), inset 0 1px 0 rgba(255,255,255,0.7);
    }

    button:hover {
        box-shadow: 0 18px 36px rgba(59, 130, 246, 0.2), inset 0 1px 0 rgba(255,255,255,0.8);
    }

    input, textarea, select {
        background: rgba(255,255,255,0.95) !important;
        border: 1px solid rgba(99, 102, 241, 0.25) !important;
        box-shadow: inset 0 0 18px rgba(255,255,255,0.6);
    }

    [data-testid="stSidebar"] > div {
        background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(232, 240, 255, 0.9));
    }

    """
    if dark:
        bg_gradient = "radial-gradient(1200px 700px at 10% 10%, #1a2b3f 0%, #0b111a 45%, #06080c 100%)"
        card_bg = "rgba(17, 24, 39, 0.66)"
        border = "rgba(120, 180, 255, 0.35)"
        glow = "0 0 36px rgba(90, 160, 255, 0.28)"
        text = "#f8fafc"
        subtext = "#cbd5e1"
        accent = "#7aa2ff"
        sidebar_bg = "rgba(10, 14, 20, 0.92)"
        input_bg = "rgba(12, 18, 28, 0.7)"
        button_bg = "linear-gradient(135deg, rgba(36, 52, 75, 0.92), rgba(18, 26, 40, 0.9))"
        button_text = "#f8fafc"
        button_hover = "0 0 0 2px rgba(122, 162, 255, 0.35), var(--glow)"
    else:
        bg_gradient = "radial-gradient(1200px 700px at 12% 8%, rgba(255, 230, 244, 0.9) 0%, rgba(232, 242, 255, 0.95) 45%, rgba(225, 235, 250, 1) 100%)"
        card_bg = "rgba(255, 255, 255, 0.62)"
        border = "rgba(99, 102, 241, 0.28)"
        glow = "0 18px 40px rgba(99, 102, 241, 0.18), 0 0 26px rgba(56, 189, 248, 0.18)"
        text = "#0f172a"
        subtext = "#334155"
        accent = "#2563eb"
        sidebar_bg = "linear-gradient(180deg, rgba(255,255,255,0.92), rgba(236, 242, 255, 0.9))"
        input_bg = "rgba(255, 255, 255, 0.92)"
        button_bg = "linear-gradient(135deg, rgba(255,255,255,0.95), rgba(222, 234, 255, 0.9))"
        button_text = "#0f172a"
        button_hover = "0 0 0 2px rgba(59, 130, 246, 0.25), 0 14px 32px rgba(59, 130, 246, 0.18)"

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Space+Grotesk:wght@300;400;500;600&display=swap');

    :root {{
        --bg: {bg_gradient};
        --card: {card_bg};
        --border: {border};
        --glow: {glow};
        --text: {text};
        --subtext: {subtext};
        --accent: {accent};
        --sidebar-bg: {sidebar_bg};
        --input-bg: {input_bg};
        --btn-bg: {button_bg};
        --btn-text: {button_text};
        --btn-hover: {button_hover};
    }}

    {extra_css}

    {reduce_motion_css}

    html, body, [data-testid="stAppViewContainer"] {{
        background: var(--bg);
        color: var(--text);
        font-family: 'Space Grotesk', sans-serif;
    }}

    [data-testid="stHeader"], [data-testid="stToolbar"] {{
        background: transparent;
    }}

    [data-testid="stSidebar"] > div {{
        background: var(--sidebar-bg);
        border-right: 1px solid var(--border);
    }}

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {{
        color: var(--text) !important;
    }}

    [data-testid="stSidebarNav"] a {{
        color: var(--text) !important;
        opacity: 0.95;
    }}

    [data-testid="stSidebarNav"] a:hover {{
        color: var(--accent) !important;
    }}

    .glass-card {{
        background: var(--card);
        border: 1px solid var(--border);
        box-shadow: var(--glow);
        border-radius: 18px;
        padding: 1.2rem 1.4rem;
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
    }}

    .glass-hero {{
        padding: 1.4rem 1.6rem;
        border-radius: 22px;
        background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04));
        border: 1px solid var(--border);
        box-shadow: var(--glow);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }}

    h1, h2, h3, h4 {{
        font-family: 'Instrument Serif', serif;
        color: var(--text);
        letter-spacing: 0.4px;
    }}

    .hero-title-3d {{
        font-size: 2.6rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        text-shadow:
            0 1px 0 rgba(15, 23, 42, 0.8),
            0 2px 0 rgba(15, 23, 42, 0.6),
            0 4px 10px rgba(0, 0, 0, 0.35);
    }}

    .hero-title-3d {{
        background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(189,214,255,0.85));
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }}

    [data-theme="light"] .hero-title-3d {{
        background: linear-gradient(180deg, rgba(15,23,42,0.95), rgba(45,83,150,0.85));
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        text-shadow:
            0 1px 0 rgba(255,255,255,0.7),
            0 4px 12px rgba(15, 23, 42, 0.25);
    }}

    p, label, span, div {{
        color: var(--text);
    }}

    .subtle {{
        color: var(--subtext);
    }}

    button, button[kind="primary"] {{
        background: var(--btn-bg);
        border: 1px solid var(--border) !important;
        box-shadow: var(--glow);
        border-radius: 999px;
        padding: 0.45rem 1.2rem;
        color: var(--btn-text) !important;
        font-weight: 600;
        transition: transform 140ms ease, box-shadow 160ms ease;
        backdrop-filter: blur(16px);
    }}

    button:hover {{
        transform: translateY(-2px) scale(1.01);
        box-shadow: var(--btn-hover);
    }}

    button:active {{
        transform: translateY(0px) scale(0.995);
    }}

    .nav-row button {{
        margin-right: 0.5rem;
        margin-bottom: 0.3rem;
    }}

    input, textarea, select {{
        background: var(--input-bg) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 12px !important;
    }}

    /* Sidebar widgets (fix light inputs in dark mode) */
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] select {{
        background: var(--input-bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        box-shadow: none !important;
    }}

    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="select"] > div > div,
    [data-testid="stSidebar"] div[data-baseweb="select"] input {{
        background: var(--input-bg) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
        box-shadow: none !important;
    }}

    [data-testid="stSidebar"] div[data-baseweb="select"] span {{
        color: var(--text) !important;
    }}

    [data-testid="stSidebar"] div[data-baseweb="input"] > div {{
        background: var(--input-bg) !important;
        border-color: var(--border) !important;
        box-shadow: none !important;
    }}

    input::placeholder, textarea::placeholder {{
        color: var(--subtext) !important;
    }}

    .metric-pill {{
        display: inline-block;
        padding: 0.2rem 0.8rem;
        border-radius: 999px;
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.08);
        margin-right: 0.6rem;
        font-size: 0.9rem;
    }}

    [data-testid="stPlotlyChart"] > div {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 0.5rem;
        box-shadow: var(--glow);
    }}

    .mini-card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 0.9rem 1.1rem;
        box-shadow: var(--glow);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
    }}

    .mini-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
    }}

    .mini-title {{
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-size: 0.68rem;
        color: var(--subtext);
        margin-bottom: 0.35rem;
    }}

    .mini-value {{
        font-size: 1.6rem;
        font-weight: 600;
        margin-bottom: 0.2rem;
    }}

    .mini-sub {{
        font-size: 0.9rem;
        color: var(--subtext);
        margin-bottom: 0.6rem;
    }}

    .mini-meter {{
        height: 6px;
        background: rgba(255,255,255,0.12);
        border-radius: 999px;
        overflow: hidden;
    }}

    .mini-meter span {{
        display: block;
        height: 100%;
        border-radius: 999px;
    }}

    .mini-ring {{
        width: 58px;
        height: 58px;
        border-radius: 50%;
        background: conic-gradient(var(--ring-color) var(--ring-angle), rgba(255,255,255,0.12) 0deg);
        display: grid;
        place-items: center;
    }}

    .mini-ring::after {{
        content: "";
        width: 70%;
        height: 70%;
        border-radius: 50%;
        background: var(--card);
        border: 1px solid var(--border);
    }}

    .wind-card .mini-sub {{
        margin-bottom: 0.35rem;
    }}

    .wind-fan {{
        position: relative;
        width: 64px;
        height: 64px;
        border-radius: 50%;
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.06);
        display: grid;
        place-items: center;
    }}

    .wind-rotor {{
        position: absolute;
        inset: 0;
        animation: wind-spin linear infinite;
    }}

    .wind-blade {{
        position: absolute;
        top: 8px;
        left: 50%;
        width: 8px;
        height: 20px;
        border-radius: 999px;
        background: var(--wind-color, var(--accent));
        transform-origin: 50% 22px;
        transform: translateX(-50%);
    }}

    .wind-blade.blade-2 {{
        transform: translateX(-50%) rotate(120deg);
    }}

    .wind-blade.blade-3 {{
        transform: translateX(-50%) rotate(240deg);
    }}

    .wind-core {{
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--card);
        border: 1px solid var(--border);
        position: relative;
        z-index: 2;
    }}

    @keyframes wind-spin {{
        from {{ transform: rotate(0deg); }}
        to {{ transform: rotate(360deg); }}
    }}

    .summary-card {{
        padding: 1.4rem 1.6rem;
    }}

    .summary-top {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1.4rem;
        flex-wrap: wrap;
    }}

    .summary-location {{
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.2rem;
    }}

    .summary-updated {{
        font-size: 0.85rem;
        color: var(--subtext);
    }}

    .summary-temp {{
        font-size: 3rem;
        font-weight: 700;
        line-height: 1.1;
    }}

    .summary-desc {{
        font-size: 1rem;
        color: var(--subtext);
    }}

    .summary-hilo {{
        font-size: 0.95rem;
        color: var(--subtext);
    }}

    .summary-stack {{
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }}

    .forecast-strip {{
        display: flex;
        gap: 0.6rem;
        overflow-x: auto;
        padding-top: 0.9rem;
    }}

    .forecast-chip {{
        min-width: 86px;
        padding: 0.6rem 0.7rem;
        border-radius: 14px;
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.08);
        text-align: center;
    }}

    .forecast-chip.active {{
        background: rgba(125, 211, 252, 0.14);
        border-color: rgba(125, 211, 252, 0.35);
    }}

    .forecast-day {{
        font-size: 0.85rem;
        color: var(--subtext);
        margin-bottom: 0.2rem;
    }}

    .forecast-desc {{
        font-size: 0.8rem;
        color: var(--subtext);
        margin-bottom: 0.25rem;
    }}

    .forecast-temps {{
        font-size: 0.95rem;
        font-weight: 600;
    }}

    .feature-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem;
        margin-top: 1.2rem;
    }}

    .feature-card {{
        background: linear-gradient(145deg, rgba(22, 30, 45, 0.85), rgba(10, 14, 24, 0.75));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 1.1rem 1.2rem;
        box-shadow: var(--glow);
        position: relative;
        overflow: hidden;
        min-height: 160px;
    }}

    .feature-card.gust-card {{
        background: linear-gradient(155deg, rgba(18, 32, 44, 0.92), rgba(10, 20, 28, 0.85));
    }}

    .feature-card.precip-card {{
        background: linear-gradient(155deg, rgba(28, 36, 60, 0.92), rgba(14, 20, 36, 0.85));
    }}

    .feature-card.uv-card {{
        background: linear-gradient(160deg, rgba(64, 58, 24, 0.9), rgba(112, 82, 12, 0.8));
    }}

    .feature-card.aqi-card {{
        background: linear-gradient(155deg, rgba(40, 40, 44, 0.92), rgba(24, 26, 34, 0.85));
    }}

    .feature-card.humidity-card {{
        background: linear-gradient(155deg, rgba(40, 44, 52, 0.92), rgba(22, 26, 34, 0.85));
    }}

    .feature-title {{
        text-transform: uppercase;
        font-size: 0.72rem;
        letter-spacing: 0.16em;
        color: var(--subtext);
        margin-bottom: 0.6rem;
    }}

    .feature-value {{
        font-size: 1.6rem;
        font-weight: 600;
    }}

    .feature-sub {{
        font-size: 0.85rem;
        color: var(--subtext);
        margin-top: 0.2rem;
    }}

    .feature-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
    }}

    .aqi-row {{
        display: flex;
        align-items: center;
        gap: 1rem;
    }}

    .feature-stack {{
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }}

    .wind-row {{
        display: flex;
        align-items: center;
        gap: 1rem;
    }}

    .compass {{
        width: 120px;
        height: 120px;
        border-radius: 50%;
        border: 1px dashed rgba(148, 163, 184, 0.45);
        position: relative;
        flex: 0 0 auto;
    }}

    .compass-needle {{
        position: absolute;
        left: 50%;
        top: 50%;
        width: 2px;
        height: 46px;
        background: #38bdf8;
        transform-origin: bottom;
        transform: translate(-50%, -100%) rotate(var(--wind-deg));
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.7);
    }}

    .compass-core {{
        position: absolute;
        left: 50%;
        top: 50%;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(148, 163, 184, 0.35);
        color: var(--text);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        transform: translate(-50%, -50%);
    }}

    .compass-letter {{
        position: absolute;
        font-size: 0.75rem;
        color: var(--subtext);
    }}

    .compass-letter.n {{ top: 6px; left: 50%; transform: translateX(-50%); }}
    .compass-letter.s {{ bottom: 6px; left: 50%; transform: translateX(-50%); }}
    .compass-letter.e {{ right: 8px; top: 50%; transform: translateY(-50%); }}
    .compass-letter.w {{ left: 8px; top: 50%; transform: translateY(-50%); }}

    .feature-meter {{
        margin-top: 0.9rem;
        height: 8px;
        border-radius: 999px;
        background: rgba(148, 163, 184, 0.2);
        overflow: hidden;
    }}

    .feature-meter span {{
        display: block;
        height: 100%;
        background: linear-gradient(90deg, #38bdf8, #22c55e);
    }}

    .feature-meter.gradient span {{
        background: linear-gradient(90deg, #14b8a6, #f59e0b, #ef4444);
    }}

    .pressure-dial {{
        width: 78px;
        height: 78px;
        border-radius: 50%;
        border: 1px solid rgba(148, 163, 184, 0.35);
        position: relative;
        background: rgba(15, 23, 42, 0.4);
    }}

    .pressure-dial::after {{
        content: "";
        position: absolute;
        left: 50%;
        top: 50%;
        width: 4px;
        height: 32px;
        background: #f97316;
        transform-origin: bottom;
        transform: translate(-50%, -100%) rotate(var(--pressure-angle));
        border-radius: 6px;
        box-shadow: 0 0 10px rgba(249, 115, 22, 0.7);
    }}

    .uv-track {{
        margin-top: 0.9rem;
        height: 10px;
        border-radius: 999px;
        background: linear-gradient(90deg, #22c55e, #eab308, #f97316, #ef4444, #8b5cf6);
        position: relative;
        overflow: hidden;
    }}

    .uv-track span {{
        position: absolute;
        top: -2px;
        height: 14px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.85);
        width: 10px;
        transform: translateX(-5px);
    }}

    .gust-icon {{
        width: 44px;
        height: 44px;
        border-radius: 12px;
        background: radial-gradient(circle at 30% 30%, rgba(56, 189, 248, 0.8), transparent 55%),
            radial-gradient(circle at 70% 70%, rgba(148, 163, 184, 0.35), transparent 50%);
        border: 1px solid rgba(148, 163, 184, 0.3);
        margin-bottom: 0.6rem;
    }}

    .feature-icon {{
        width: 44px;
        height: 44px;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.3);
        margin-bottom: 0.6rem;
    }}

    .aqi-gauge {{
        width: 120px;
        height: 60px;
        border-radius: 120px 120px 0 0;
        background: conic-gradient(from 180deg, #22c55e 0deg, #eab308 60deg, #f97316 120deg, #ef4444 180deg);
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.35);
    }}

    .aqi-gauge::after {{
        content: "";
        position: absolute;
        left: 10px;
        right: 10px;
        top: 10px;
        bottom: -6px;
        background: rgba(10, 14, 24, 0.9);
        border-radius: 100px 100px 0 0;
    }}

    .aqi-gauge::before {{
        content: "";
        position: absolute;
        left: 50%;
        bottom: 6px;
        width: 6px;
        height: 34px;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 999px;
        transform-origin: bottom;
        transform: translateX(-50%) rotate(var(--aqi-angle));
        box-shadow: 0 0 10px rgba(255, 255, 255, 0.6);
    }}

    .humidity-icon {{
        width: 44px;
        height: 44px;
        border-radius: 50%;
        border: 1px solid rgba(148, 163, 184, 0.3);
        background: radial-gradient(circle at 45% 35%, rgba(56, 189, 248, 0.9), transparent 60%),
            radial-gradient(circle at 60% 70%, rgba(125, 211, 252, 0.4), transparent 60%),
            linear-gradient(145deg, rgba(14, 30, 50, 0.9), rgba(10, 20, 36, 0.85));
    }}

    
    .cloud-anim {{
        position: absolute;
        inset: 6px;
        border-radius: 14px;
        overflow: hidden;
        pointer-events: none;
    }}

    .cloud-anim::before {{
        content: "";
        position: absolute;
        width: 36px;
        height: 22px;
        left: -10px;
        top: 10px;
        border-radius: 999px;
        background:
            radial-gradient(circle at 30% 45%, rgba(255, 255, 255, 0.95), rgba(226, 232, 240, 0.85) 60%, transparent 72%),
            radial-gradient(circle at 65% 35%, rgba(255, 255, 255, 0.9), rgba(226, 232, 240, 0.7) 60%, transparent 75%);
        box-shadow: 0 6px 12px rgba(15, 23, 42, 0.35);
        animation: cloudDrift 6.5s linear infinite;
    }}

    .cloud-anim::after {{
        content: "";
        position: absolute;
        width: 28px;
        height: 18px;
        left: -18px;
        top: 26px;
        border-radius: 999px;
        background:
            radial-gradient(circle at 30% 45%, rgba(255, 255, 255, 0.9), rgba(226, 232, 240, 0.8) 60%, transparent 75%);
        box-shadow: 0 5px 10px rgba(15, 23, 42, 0.3);
        opacity: 0.8;
        animation: cloudDrift 8.5s linear infinite;
    }}

    @keyframes cloudDrift {{
        0% {{
            transform: translateX(-10px) translateY(0);
            opacity: 0;
        }}
        10% {{
            opacity: 1;
        }}
        90% {{
            opacity: 1;
        }}
        100% {{
            transform: translateX(70px) translateY(-2px);
            opacity: 0;
        }}
    }}

    .cloud-icon {{
        background: radial-gradient(circle at 35% 40%, rgba(226, 232, 240, 0.9), transparent 58%),
            radial-gradient(circle at 65% 45%, rgba(148, 163, 184, 0.6), transparent 60%),
            linear-gradient(145deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.85));
    }}

    .precip-icon {{
        background: radial-gradient(circle at 35% 40%, rgba(56, 189, 248, 0.85), transparent 55%),
            radial-gradient(circle at 65% 45%, rgba(125, 211, 252, 0.6), transparent 60%),
            linear-gradient(145deg, rgba(14, 30, 50, 0.9), rgba(10, 20, 36, 0.85));
    }}

    .pressure-icon {{
        background: radial-gradient(circle at 40% 40%, rgba(249, 115, 22, 0.85), transparent 55%),
            linear-gradient(145deg, rgba(30, 30, 46, 0.9), rgba(14, 18, 30, 0.85));
    }}

    .uv-icon {{
        background: radial-gradient(circle at 40% 40%, rgba(250, 204, 21, 0.9), transparent 55%),
            linear-gradient(145deg, rgba(80, 60, 20, 0.9), rgba(40, 28, 10, 0.85));
    }}

    @media (max-width: 900px) {{
        .feature-grid {{
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        }}
        .compass {{
            width: 96px;
            height: 96px;
        }}
        .feature-value {{
            font-size: 1.4rem;
        }}
    }}

    [data-testid="stRadio"] > div {{
        flex-direction: row;
        gap: 0.35rem;
    }}

    [data-testid="stRadio"] label {{
        margin: 0;
    }}

    [data-testid="stRadio"] div[data-baseweb="radio"] {{
        background: rgba(255,255,255,0.08);
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 0.2rem 0.7rem;
    }}

    [data-testid="stRadio"] input {{
        display: none;
    }}

    [data-testid="stRadio"] input:checked + div {{
        background: var(--btn-bg);
        color: var(--btn-text);
    }}

    .chat-bubble {{
        padding: 0.8rem 1rem;
        border-radius: 16px;
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.08);
        margin-bottom: 0.6rem;
    }}

    .chat-user {{
        background: rgba(125, 211, 252, 0.18);
    }}

    .chat-agent {{
        background: rgba(255, 255, 255, 0.12);
    }}

    .astro-card {{
        position: relative;
        margin-top: 1rem;
        padding: 1.1rem 1.4rem;
        border-radius: 20px;
        background: var(--card);
        border: 1px solid var(--border);
        box-shadow: var(--glow);
        overflow: hidden;
    }}

    .astro-card::before {{
        content: "";
        position: absolute;
        inset: -30% -10% auto -10%;
        height: 160%;
        background:
            radial-gradient(600px 220px at 20% 10%, rgba(255, 0, 128, 0.18), transparent 60%),
            radial-gradient(600px 220px at 80% 10%, rgba(0, 255, 255, 0.18), transparent 60%),
            radial-gradient(700px 240px at 50% 100%, rgba(130, 90, 255, 0.12), transparent 60%);
        opacity: 0.6;
        filter: blur(10px);
        pointer-events: none;
    }}

    .astro-card::after {{
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(
            120deg,
            rgba(255, 0, 128, 0.06),
            rgba(0, 255, 255, 0.05),
            rgba(130, 90, 255, 0.06)
        );
        mix-blend-mode: screen;
        opacity: 0.6;
        animation: rgb-drift 12s linear infinite;
        pointer-events: none;
    }}

    .astro-head {{
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.6rem;
    }}

    .astro-head-title {{
        text-transform: uppercase;
        letter-spacing: 0.2em;
        font-size: 0.75rem;
        color: var(--subtext);
    }}

    .astro-now {{
        font-size: 0.8rem;
        color: var(--subtext);
    }}

    .astro-row {{
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.7rem 0;
    }}


    .astro-row.compact {{
        align-items: center;
        gap: 0.9rem;
        padding: 0.6rem 0;
    }}

    .astro-inline {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 150px;
        white-space: nowrap;
    }}

    .astro-inline.right {{
        justify-content: flex-end;
    }}

    .astro-inline-text {{
        display: flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.9rem;
    }}

    .astro-time-inline {{
        font-weight: 600;
    }}

    .astro-track.compact {{
        flex: 1;
    }}

    .astro-progress-label {{
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        color: var(--text);
        opacity: 0.75;
    }}
    .astro-progress-label:empty {{
        display: none;
    }}


    .astro-row + .astro-row {{
        border-top: 1px solid var(--border);
    }}

    .astro-label {{
        min-width: 120px;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }}

    .astro-label.right {{
        align-items: flex-end;
        text-align: right;
    }}

    .astro-sub {{
        font-size: 0.7rem;
        color: var(--subtext);
        text-transform: uppercase;
        letter-spacing: 0.18em;
    }}

    .astro-time {{
        font-size: 1.5rem;
        font-weight: 600;
    }}

    .astro-icon {{
        width: 34px;
        height: 34px;
        display: grid;
        place-items: center;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid var(--border);
        box-shadow: inset 0 0 12px rgba(255, 255, 255, 0.08), 0 8px 20px rgba(0, 0, 0, 0.3);
    }}

    .astro-icon svg {{
        width: 20px;
        height: 20px;
    }}

    .astro-icon.sun svg {{
        stroke: #fbbf24;
        fill: none;
        stroke-width: 1.6;
    }}

    .astro-icon.sun svg circle {{
        fill: #fbbf24;
        stroke: none;
    }}

    .astro-icon.moon svg {{
        fill: #c7d2fe;
    }}

    .astro-track {{
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
    }}

    .astro-track-line {{
        position: relative;
        height: 16px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.14);
        box-shadow: inset 0 0 12px rgba(0, 0, 0, 0.45);
        overflow: hidden;
    }}

    .astro-track-line.disabled {{
        opacity: 0.4;
    }}

    .astro-progress {{
        position: absolute;
        inset: 0 auto 0 0;
        border-radius: 999px;
    }}

    .astro-progress.sun {{
        background: linear-gradient(90deg, rgba(255, 214, 102, 0.2), rgba(255, 159, 28, 0.7), rgba(255, 238, 209, 0.9));
        box-shadow: 0 0 16px rgba(255, 176, 0, 0.6), 0 0 30px rgba(255, 0, 128, 0.25), 0 0 40px rgba(0, 255, 255, 0.25);
    }}

    .astro-progress.moon {{
        background: linear-gradient(90deg, rgba(148, 163, 255, 0.25), rgba(99, 102, 241, 0.7), rgba(226, 232, 240, 0.9));
        box-shadow: 0 0 16px rgba(129, 140, 248, 0.55), 0 0 30px rgba(56, 189, 248, 0.25);
    }}

    .astro-orb {{
        position: absolute;
        top: 50%;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        transform: translate(-50%, -50%);
        border: 1px solid rgba(255, 255, 255, 0.55);
    }}

    .astro-orb.sun {{
        background: radial-gradient(circle at 30% 30%, #fff4cc, #ffd166 45%, #f59e0b 70%, #f97316 100%);
        box-shadow: 0 0 18px rgba(255, 184, 0, 0.75), 0 0 36px rgba(255, 94, 0, 0.45), 0 0 44px rgba(0, 255, 255, 0.3);
    }}

    .astro-orb.moon {{
        background: radial-gradient(circle at 35% 30%, #f8fafc, #c7d2fe 50%, #94a3b8 82%);
        box-shadow: 0 0 18px rgba(148, 163, 255, 0.6), 0 0 36px rgba(56, 189, 248, 0.2);
    }}

    .astro-orb.disabled {{
        opacity: 0.35;
    }}

    .astro-track-legend {{
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        font-size: 0.75rem;
        color: var(--subtext);
    }}

    .astro-track-legend span:nth-child(2) {{
        justify-self: center;
        font-weight: 600;
        color: var(--text);
    }}

    @keyframes rgb-drift {{
        from {{
            filter: hue-rotate(0deg);
        }}
        to {{
            filter: hue-rotate(360deg);
        }}
    }}


    /* Responsive tweaks */
    .block-container {{
        padding-top: 1.2rem;
        padding-left: 2.2rem;
        padding-right: 2.2rem;
    }}

    @media (max-width: 900px) {{

        [data-testid="stRadio"] > div {{
            flex-direction: column;
            align-items: stretch;
        }}

        [data-testid="stRadio"] div[data-baseweb="radio"] {{
            width: 100%;
            justify-content: space-between;
        }}

        .metric-pill {{
            display: block;
            margin-bottom: 0.35rem;
        }}

        iframe[title="streamlit_folium.st_folium"] {{
            height: 320px !important;
        }}
        .block-container {{
            padding-left: 1rem;
            padding-right: 1rem;
        }}

        h1 {{
            font-size: 1.8rem;
        }}

        h2 {{
            font-size: 1.3rem;
        }}

        .glass-hero {{
            padding: 1rem 1.1rem;
        }}

        .summary-card {{
            padding: 1.1rem 1.2rem;
        }}

        .summary-temp {{
            font-size: 2.4rem;
        }}

        .forecast-strip {{
            gap: 0.4rem;
            padding-top: 0.6rem;
        }}

        .forecast-chip {{
            min-width: 72px;
            padding: 0.5rem 0.55rem;
        }}

        [data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap;
            gap: 0.7rem;
        }}

        [data-testid="stHorizontalBlock"] > div {{
            flex: 1 1 100% !important;
            width: 100% !important;
        }}

        .mini-card {{
            width: 100%;
        }}

        button, button[kind="primary"], .stButton > button {{
            width: 100% !important;
        }}

        [data-testid="stPlotlyChart"] > div {{
            padding: 0.2rem;
        }}

        iframe[title="streamlit_folium.st_folium"] {{
            height: 320px !important;
        }}

        .astro-row {{
            flex-direction: column;
            align-items: stretch;
        }}

        .astro-row.compact {{
            flex-direction: row;
            flex-wrap: wrap;
            gap: 0.6rem;
        }}

        .astro-track.compact {{
            width: 100%;
        }}

        .astro-inline {{
            min-width: auto;
        }}

        .astro-label,
        .astro-label.right {{
            align-items: flex-start;
            text-align: left;
        }}
    }}


    
    /* 3d-astro-override */
    .astro-card {{
        position: relative;
        margin-top: 1rem;
        padding: 1.2rem 1.6rem 1.6rem;
        border-radius: 24px;
        background: linear-gradient(160deg, rgba(17, 26, 44, 0.95), rgba(8, 12, 24, 0.9));
        border: 1px solid var(--border);
        box-shadow: 0 18px 40px rgba(8, 12, 24, 0.55);
        overflow: hidden;
        perspective: 900px;
    }}

    .astro-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.2rem;
    }}

    .astro-head-title {{
        font-size: 1.1rem;
        font-weight: 600;
        text-transform: none;
        letter-spacing: 0.02em;
    }}

    .astro-now {{
        font-size: 0.85rem;
        color: var(--subtext);
    }}

    .astro-row {{
        display: grid;
        grid-template-columns: 1fr minmax(200px, 1.6fr) 1fr;
        gap: 0.7rem;
        align-items: center;
        margin-bottom: 1.2rem;
    }}

    .astro-row:last-child {{
        margin-bottom: 0;
    }}

    .astro-side {{
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }}

    .astro-side.right {{
        text-align: right;
        align-items: flex-end;
    }}

    .astro-label {{
        text-transform: uppercase;
        letter-spacing: 0.2em;
        font-size: 0.62rem;
        color: var(--subtext);
    }}

    .astro-time {{
        font-size: 1.5rem;
        font-weight: 600;
    }}

    .astro-arc {{
        text-align: center;
    }}

    .astro-arc-track {{
        position: relative;
        height: 130px;
        display: flex;
        align-items: flex-end;
        justify-content: center;
        transform: rotateX(18deg);
        transform-style: preserve-3d;
    }}

    .astro-arc-svg {{
        width: 260px;
        height: 130px;
    }}

    .astro-arc-bg {{
        fill: none;
        stroke: rgba(148, 163, 184, 0.25);
        stroke-width: 12;
        filter: drop-shadow(0 6px 12px rgba(0, 0, 0, 0.4));
    }}

    .astro-arc-fill {{
        fill: none;
        stroke-width: 12;
        stroke-linecap: round;
        filter: drop-shadow(0 6px 16px rgba(0, 0, 0, 0.6));
    }}

    .astro-arc-fill.sun {{
        stroke: url(#sun-gradient);
    }}

    .astro-arc-fill.moon {{
        stroke: url(#moon-gradient);
    }}

    .astro-orb {{
        position: absolute;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        left: var(--orb-x);
        top: var(--orb-y);
        transform: translate(-50%, -50%);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.6);
        animation: orbFloat 3.6s ease-in-out infinite;
    }}

    .astro-orb.sun {{
        background: radial-gradient(circle at 30% 30%, #fde68a, #f97316 60%, #b45309 100%);
        box-shadow: 0 0 20px rgba(251, 191, 36, 0.8);
    }}

    .astro-orb.moon {{
        background: radial-gradient(circle at 30% 30%, #e2e8f0, #94a3b8 60%, #475569 100%);
        box-shadow: 0 0 18px rgba(148, 163, 184, 0.7);
    }}

    .astro-orb.disabled {{
        opacity: 0.35;
        filter: grayscale(1);
    }}

    .astro-duration {{
        margin-top: -0.3rem;
        font-size: 0.95rem;
        color: var(--text);
    }}

    .astro-icon svg {{
        width: 24px;
        height: 24px;
    }}

    .astro-icon.sun {{
        color: #fbbf24;
    }}

    .astro-icon.moon {{
        color: #93c5fd;
    }}

    @keyframes orbFloat {{
        0%, 100% {{
            transform: translate(-50%, -50%) translateZ(0);
        }}
        50% {{
            transform: translate(-50%, -56%) translateZ(10px);
        }}
    }}

    @media (max-width: 900px) {{
        .astro-row {{
            grid-template-columns: 1fr;
            text-align: center;
        }}
        .astro-side, .astro-side.right {{
            align-items: center;
            text-align: center;
        }}
        .astro-arc-track {{
            transform: rotateX(12deg);
        }}
    }}

</style>
    """
    st.markdown(css, unsafe_allow_html=True)


def inject_click_sound() -> None:
    components.html(
        """
        <script>
        (function() {
            if (window.__glassClickSound) return;
            window.__glassClickSound = true;

            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const play = () => {
                const now = audioCtx.currentTime;
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(840, now);
                gain.gain.setValueAtTime(0.0, now);
                gain.gain.linearRampToValueAtTime(0.18, now + 0.01);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start(now);
                osc.stop(now + 0.09);
            };

            document.addEventListener('click', (event) => {
                const btn = event.target.closest('button');
                if (!btn) return;
                if (audioCtx.state === 'suspended') {
                    audioCtx.resume().then(play);
                } else {
                    play();
                }
            }, true);
        })();
        </script>
        """,
        height=0,
    )
