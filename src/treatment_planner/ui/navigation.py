"""Guided chapters and evidence mode controls; callers own application state."""

import streamlit as st

from treatment_planner.interfaces import EvidenceMode

CHAPTERS = ("Plan", "Routes & conditions", "Sources & assumptions")


def render_navigation(*, key: str = "v2-navigation") -> str:
    """Navigation alone does not modify inputs or confirmation."""
    return st.sidebar.radio("Workspace", CHAPTERS, key=key)


def render_evidence_mode(mode: EvidenceMode, *, key: str = "v2-mode") -> EvidenceMode:
    """Return an explicit mode choice, never an automatic live-data fallback."""
    modes = list(EvidenceMode)
    selected = st.radio(
        "Evidence mode",
        modes,
        index=modes.index(mode),
        format_func=lambda value: value.value.title(),
        horizontal=True,
        key=key,
    )
    st.caption("Simulated evidence" if selected == EvidenceMode.DEMO else "Live source evidence")
    return selected
