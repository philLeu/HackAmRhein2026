"""Clickable Rhine evidence summary, independent of synthetic planning delays."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import streamlit as st

from treatment_planner.data.rhine import RhineObservationProvider
from treatment_planner.data.rhine_forecast import load_forecast_replay, load_live_forecast
from treatment_planner.interfaces import RiverAssessment, TimeWindow
from treatment_planner.rhine_conditions import (
    assess_conditions,
    forecast_usable,
    summarize_conditions,
)
from treatment_planner.ui.formatting import format_timestamp
from treatment_planner.ui.rhine_chart import rhine_chart


@st.cache_data(ttl=300, show_spinner=False)
def _live_evidence():
    now = datetime.now(UTC)
    history = RhineObservationProvider(timedelta(hours=6)).load(
        TimeWindow(now - timedelta(days=2), now)
    )
    return history, load_live_forecast()


@st.cache_data(show_spinner=False)
def _replay_evidence(directory: str):
    return load_forecast_replay(Path(directory))


def _findings(assessment: RiverAssessment, label: str):
    st.markdown(f"**{label}: {assessment.status.value.upper()}**")
    if assessment.gauge_height_cm is not None:
        st.write(
            f"Gauge height {assessment.gauge_height_cm:.1f} cm; "
            f"notebook available draft {assessment.draft_cm:.1f} cm."
        )
    if assessment.status.value == "normal":
        st.write("No threshold crossed or within the 5 cm margin.")
    for finding in assessment.findings:
        st.write(f"{'CROSSED' if finding.state == 'breached' else 'NEAR'}: {finding.message}")


def render_rhine_conditions(root: Path, theme: dict) -> None:
    """Keep the summary visible; open the notebook-style evidence chart inline."""
    mode = st.selectbox(
        "Rhine chart evidence",
        ("Saved forecast replay", "Live Rhine conditions"),
        key="rhine_evidence_mode",
    )
    if mode == "Saved forecast replay":
        history, forecast, now = _replay_evidence(str(root / "data/replay/rhine/forecast-capture"))
        st.caption(
            f"Saved Rhine evidence · evaluated at {format_timestamp(now)}. "
            "Independent of the synthetic planning scenario."
        )
    else:
        with st.spinner("Loading public Rhine observations and BAFU forecast…"):
            history, forecast = _live_evidence()
        now = datetime.now(UTC)
        st.caption("Live station evidence. Treatment planning still uses the selected demo mode.")
    days = st.number_input(
        "Rhine forecast window (days)",
        min_value=1,
        max_value=10,
        value=5,
        key="rhine_forecast_days",
    )
    summary = summarize_conditions(
        history, forecast, now, days, timedelta(hours=6), timedelta(hours=24)
    )
    future_label = summary.forecast.status.value.upper()
    if not summary.complete:
        future_label += " within coverage; remainder UNKNOWN"
    header = (
        f"Basel Rhine conditions · {summary.current.status.value.upper()} now → "
        f"{future_label} · View history and forecast"
    )
    if summary.current.findings:
        st.caption(f"Now: {summary.current.findings[0].consequence}.")
    if summary.first_at:
        st.caption(
            f"Worst future median class first occurs at {format_timestamp(summary.first_at)}. "
            f"Coverage ends {format_timestamp(summary.covered_until)}."
        )
    issued = forecast.provenance.source_time if forecast.provenance else None
    with st.expander(header):
        st.caption(
            f"Forecast issued {format_timestamp(issued)}. "
            "Solid blue: measured · dashed blue: forecast median · "
            "light band: min–max · darker band: 25th–75th percentiles. "
            "Diagonal texture: within 5 cm of the next threshold."
        )
        for issue in summary.issues:
            st.warning(issue)
        date_origin = now.replace(minute=0, second=0, microsecond=0)
        dates = [date_origin + timedelta(days=i) for i in range(1, 11)]
        selected_date = st.selectbox(
            "Inspect Rhine forecast date",
            dates,
            index=days - 1,
            format_func=format_timestamp,
            key=f"rhine_date_{mode}",
        )
        usable = forecast_usable(forecast, now, timedelta(hours=24))
        selected = None
        if (
            usable
            and forecast.points[0].timestamp <= selected_date <= forecast.points[-1].timestamp
        ):
            selected = min(forecast.points, key=lambda p: abs(p.timestamp - selected_date))
        if history.observations or forecast.points:
            main_chart, reference = rhine_chart(
                history, forecast, now, selected.timestamp if selected else None, theme
            )
            main_column, reference_column = st.columns([5, 1.5])
            with main_column:
                st.altair_chart(main_chart, width="stretch")
            with reference_column:
                st.altair_chart(reference, width="stretch")
        else:
            st.info("No Rhine history or forecast available to plot.")
        _findings(summary.current, "Current conditions")
        if selected:
            _findings(
                assess_conditions(selected.median_cm),
                f"Forecast median at {format_timestamp(selected.timestamp)}",
            )
            st.caption("Hourly forecast point nearest the selected time, within source coverage.")
        else:
            st.info("UNKNOWN: forecast unavailable for the selected date. No extrapolation.")
        st.caption(
            "Notebook rules for Basel Rheinhalle, including reference-vessel assumptions. "
            "These classes do not establish Rotterdam–Basel navigability or delivery delay."
        )
        st.markdown(
            "[Observations: Open Data Basel-Stadt · CC0 1.0]"
            "(https://data.bs.ch/explore/dataset/100089/) · "
            "[Forecast: Hydrology Division, FOEN/BAFU · free use with recommended attribution]"
            "(https://www.hydrodaten.admin.ch/en/questions) · Reference date: 03.10.2026"
        )
