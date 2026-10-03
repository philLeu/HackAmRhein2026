"""Shared control-room styling, sourced from the project's single theme file."""

import tomllib
from pathlib import Path

import streamlit as st

THEME_PATH = Path(__file__).resolve().parents[3] / "config" / "theme.toml"


def apply_theme(theme_path: Path = THEME_PATH) -> dict:
    theme = tomllib.loads(theme_path.read_text(encoding="utf-8"))
    surface = theme["surface"]
    palette = theme["theme"]
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
        </style>""",
        unsafe_allow_html=True,
    )
    return theme
