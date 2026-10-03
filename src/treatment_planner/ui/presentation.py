"""Shared control-room styling, sourced from the project's single theme file."""

import base64
import tomllib
from pathlib import Path

import streamlit as st

THEME_PATH = Path(__file__).resolve().parents[3] / "config" / "theme.toml"
LOGO_PATH = THEME_PATH.parent.parent / "assets" / "branding" / "pulseshift.png"


def apply_theme(theme_path: Path = THEME_PATH, *, show_logo: bool = True) -> dict:
    theme = tomllib.loads(theme_path.read_text(encoding="utf-8"))
    surface = theme["surface"]
    palette = theme["theme"]
    branding = theme["branding"]
    st.markdown(
        f"""<style>
        .stApp {{background: {palette["backgroundColor"]}; color: {palette["textColor"]};
            font-family: {palette["font"]}; color-scheme: dark;}}
        [data-testid="stHeader"] {{background: {palette["backgroundColor"]};}}
        h1, h2, h3, label, [data-testid="stMarkdownContainer"] {{color: {palette["textColor"]};}}
        [data-testid="stCaptionContainer"] p {{color: {surface["muted"]};}}
        [data-testid="stMetric"] {{background: {palette["secondaryBackgroundColor"]};
            border: 1px solid {surface["border"]}; border-radius: {surface["radius"]};
            padding: {surface["padding"]};}}
        [data-testid="stMetricValue"] {{color: {palette["primaryColor"]};}}
        [data-testid="stVerticalBlockBorderWrapper"] {{border-color: {surface["border"]};}}
        .pulseshift-brand {{width: {branding["width"]}px; max-width: 100%;
            box-sizing: border-box; background: {branding["background"]};
            border-radius: {surface["radius"]}; padding: {branding["padding"]};}}
        .pulseshift-brand img {{display: block; width: 100%; height: auto;}}
        </style>""",
        unsafe_allow_html=True,
    )
    if show_logo:
        logo = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        st.markdown(
            f'<div class="pulseshift-brand"><img src="data:image/png;base64,{logo}" '
            'alt="PulseShift company logo"></div>',
            unsafe_allow_html=True,
        )
    return theme
