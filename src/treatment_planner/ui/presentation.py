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
        .pulseshift-brand {{display: flex; justify-content: center; width: 100%;
            max-width: 100%;
            box-sizing: border-box; background: {branding["background"]};
            padding: {branding["padding"]}; margin-bottom: {branding["margin_bottom"]};}}
        .pulseshift-brand-inner {{display: flex; align-items: center; gap: {branding["gap"]};
            width: 100%; max-width: {branding["inner_max_width"]};}}
        .pulseshift-logo {{position: relative; flex: 0 0 auto; width: {branding["width"]}px;
            max-width: {branding["max_width_vw"]}vw;}}
        .pulseshift-logo img {{display: block; width: 100%; height: auto;}}
        .pulseshift-logo-relief {{position: absolute; inset: 0;
            filter: drop-shadow({branding["logo_relief"]});
            clip-path: {branding["logo_relief_clip"]};}}
        .pulseshift-brand-copy {{min-width: 0;}}
        .pulseshift-motto {{color: {branding["motto_color"]};
            font-size: {branding["motto_size"]}; font-weight: {branding["motto_weight"]};
            letter-spacing: {branding["motto_tracking"]};
            line-height: {branding["motto_line_height"]};}}
        @media (max-width: {branding["mobile_breakpoint"]}px)
            {{.pulseshift-brand-inner {{gap: {branding["mobile_gap"]};}}
            .pulseshift-logo {{width: {branding["mobile_width"]}px;}}
            .pulseshift-motto {{font-size: {branding["motto_mobile_size"]};}}}}
        </style>""",
        unsafe_allow_html=True,
    )
    if show_logo:
        logo = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        st.markdown(
            f'<div class="pulseshift-brand"><div class="pulseshift-brand-inner">'
            f'<div class="pulseshift-logo"><img src="data:image/png;base64,{logo}" '
            f'alt="PulseShift company logo"><img class="pulseshift-logo-relief" '
            f'src="data:image/png;base64,{logo}" alt="" aria-hidden="true"></div>'
            f'<div class="pulseshift-brand-copy"><div class="pulseshift-motto">'
            f"{branding['motto']}</div></div></div></div>",
            unsafe_allow_html=True,
        )
    return theme
