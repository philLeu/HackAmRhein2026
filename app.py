"""T9 connects offline evidence, the planning engine and coordinator screen."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import streamlit as st

from treatment_planner.data.rhine import RhineReplayProvider
from treatment_planner.data.weather import WeatherReplayProvider
from treatment_planner.demo import ORDER, SyntheticWeatherProvider, fixture_request
from treatment_planner.interfaces import (
    EnvironmentInputs,
    PlanningSettings,
    RiverReport,
    TimeWindow,
    TreatmentRequest,
    WeatherReport,
)
from treatment_planner.planning import PlanningComparator, load_settings
from treatment_planner.ui.comparison import render_comparison, render_route_inputs
from treatment_planner.ui.presentation import apply_theme
from treatment_planner.ui.rhine import render_rhine_conditions

ROOT = Path(__file__).resolve().parent
SCENARIOS = ("Baseline", "Low water", "Hot return", "Snow", "Missing weather")
MODES = ("Synthetic walkthrough", "Saved provider replay")
ARCHIVE_ORDER = datetime(2026, 10, 3, 11, 30, tzinfo=UTC)
LOCATION = "Basel 4056 forecast point"


def demo_request(mode: str) -> TreatmentRequest:
    """Keep invented treatment offsets, using capture dates for provider replay."""
    request = fixture_request()
    if mode == MODES[0]:
        return request
    offset = ARCHIVE_ORDER - ORDER
    return replace(
        request,
        order_time=ARCHIVE_ORDER,
        original_collection=request.original_collection + offset,
        nominal_departure=request.nominal_departure + offset,
        decision_time=ARCHIVE_ORDER,
        routes=tuple(
            replace(
                route,
                checked_at=ARCHIVE_ORDER,
                provenance=replace(
                    route.provenance, source_time=ARCHIVE_ORDER, retrieved_at=ARCHIVE_ORDER
                ),
            )
            for route in request.routes
        ),
    )


def synthetic_environment(scenario: str) -> EnvironmentInputs:
    """Supply labelled T4 weather; the engine calculates every alternative."""
    weather = SyntheticWeatherProvider(scenario == "Hot return").load(
        "Invented Basel route", TimeWindow(ORDER, ORDER + timedelta(hours=200))
    )
    if scenario == "Snow":
        weather = replace(
            weather, windows=tuple(replace(w, snowfall=True) for w in weather.windows)
        )
    elif scenario == "Missing weather":
        weather = WeatherReport((), ("Synthetic missing-weather example: no journey coverage.",))
    # The explicit t4_replay engine mode labels the synthetic delay assumption.
    return EnvironmentInputs(RiverReport(()), weather)


def provider_environment(
    request: TreatmentRequest,
    settings: PlanningSettings,
    forecast_age: timedelta,
    observation_age: timedelta,
    *,
    replay_root: Path = ROOT / "data" / "replay",
) -> EnvironmentInputs:
    """Load saved providers offline at a historical clock, preserving all issues.

    Probe the engine for candidate journey envelopes before loading weather.
    Issues anywhere in these envelopes conservatively affect bicycle plans.
    """
    river = RhineReplayProvider(
        replay_root / "rhine", observation_age, clock=lambda: request.decision_time
    ).load(
        TimeWindow(
            datetime(2026, 10, 3, 8, 30, tzinfo=UTC),
            datetime(2026, 10, 3, 8, 55, tzinfo=UTC),
        )
    )
    provider = WeatherReplayProvider(
        replay_root / "weather" / "capture-20261003T112609Z", forecast_age
    )
    probe = PlanningComparator(weather_location=LOCATION).compare(
        request, EnvironmentInputs(river, WeatherReport(())), settings
    )
    windows, issues = [], []
    for event_id, leg in (("sample", "outbound"), ("return", "return")):
        journeys = [
            event.interval for plan in probe for event in plan.events if event.event_id == event_id
        ]
        envelope = TimeWindow(min(w.start for w in journeys), max(w.end for w in journeys))
        report = provider.load(leg, envelope)
        windows.extend(report.windows)
        issues.extend(report.issues)
    return EnvironmentInputs(river, WeatherReport(tuple(windows), tuple(dict.fromkeys(issues))))


def render_sources(mode: str) -> None:
    """Keep provider attribution and deliberate simplifications visible."""
    with st.expander("Sources and demo limits", expanded=True):
        st.markdown(
            "[Source: MeteoSwiss · CC BY 4.0]"
            "(https://opendatadocs.meteoswiss.ch/general/terms-of-use) · "
            "[FOEN/BAFU via Open Data Basel-Stadt · CC0 1.0]"
            "(https://data.bs.ch/explore/dataset/100089/)"
        )
        st.write(
            "Invented treatment and transport/process durations. Rhine delays are synthetic "
            "scenario inputs, never inferred from the Basel gauge or proof of route navigability. "
            "The finite alternative set is unranked and is not exhaustive optimisation."
        )
        if mode == MODES[0]:
            st.write(
                "Synthetic walkthrough: weather maxima and snowfall are invented. Unedited "
                "synthetic route entries assume renewed clear-route checks at dispatch. "
                "Edited manual entries require renewed checks and may remain unconfirmed."
            )
        else:
            st.write(
                "Historical provider replay, evaluated at 03.10.2026 · 11:30 UTC. "
                "Saved weather is hourly mean; maximum temperature remains unknown. "
                "Rhine original retrieval time is unknown. Synthetic route/car inputs remain "
                "labelled; future route checks are required. Freshness values are inspection "
                "controls, not an approved operational policy. Any weather issue within the "
                "candidate journey envelopes conservatively affects bicycle alternatives."
            )


def main() -> None:
    st.set_page_config(page_title="Treatment material-flow planner", layout="wide")
    theme = apply_theme()
    st.caption("OPERATIONS PREVIEW / MATERIAL FLOW")
    st.title("Treatment material-flow planner")
    st.write("Compare generated transport alternatives, inspect constraints and select a plan.")
    st.warning(
        "Synthetic treatment demo — planning choices only; no transport or treatment booked."
    )
    mode = st.selectbox("Evidence mode", MODES)
    settings = load_settings(ROOT / "config" / "planning.json")
    if mode == MODES[0]:
        scenario = st.selectbox("Scenario", SCENARIOS)
        settings = replace(
            settings, river_delay=timedelta(hours=12 if scenario == "Low water" else 0)
        )
        environment = synthetic_environment(scenario)
    else:
        forecast_age = st.number_input(
            "Inspect maximum forecast age (hours)", min_value=1, value=24
        )
        observation_age = st.number_input(
            "Inspect maximum observation age (hours)", min_value=1, value=6
        )
    request = render_route_inputs(demo_request(mode))
    if mode == MODES[1]:
        environment = provider_environment(
            request, settings, timedelta(hours=forecast_age), timedelta(hours=observation_age)
        )
    comparator = PlanningComparator(
        weather_location="Invented Basel route" if mode == MODES[0] else LOCATION,
        t4_replay=mode == MODES[0],
    )
    plans = comparator.compare(request, environment, settings)
    render_sources(mode)
    render_rhine_conditions(ROOT, theme)
    selected = render_comparison(
        plans,
        request=request,
        environment=environment,
        compared_request=request,
        compared_environment=environment,
    )
    st.session_state["selected_plan_id"] = selected.plan_id if selected else None
    st.caption(
        "Planning preview only. No patient records, clinical decisions or transport bookings."
    )


if __name__ == "__main__":
    main()
