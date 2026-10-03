"""PulseShift application entry point for guided treatment planning."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import streamlit as st

from treatment_planner.data.weather import WeatherLiveProvider
from treatment_planner.demo import ORDER
from treatment_planner.interfaces import (
    DemoOverrides,
    EvidenceMode,
    PlanningGoal,
    TransportMode,
)
from treatment_planner.planning import load_settings
from treatment_planner.recommendations import GoalRecommendationEngine
from treatment_planner.ui.comparison import render_comparison, render_route_inputs
from treatment_planner.ui.comparison import render_sources as render_evidence_sources
from treatment_planner.ui.demo_controls import render_demo_controls
from treatment_planner.ui.navigation import render_evidence_mode, render_navigation
from treatment_planner.ui.presentation import apply_theme
from treatment_planner.ui.recommendation import render_goal
from treatment_planner.ui.rhine import render_rhine_conditions
from treatment_planner.ui.route_summary import render_route_summaries
from treatment_planner.v2_flow import FORECAST_AGE, baseline_overrides, build_flow, live_request

ROOT = Path(__file__).resolve().parent


def render_sources(mode: EvidenceMode) -> None:
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
            "The finite alternative set is goal-ranked but is not exhaustive optimisation."
        )
        if mode == EvidenceMode.DEMO:
            st.write(
                "Demo mode uses a fixed clock and simulated Rhine, weather and route inputs. "
                "The low-water-to-delay rule is illustrative; clear synthetic route checks "
                "are assumed renewed at dispatch."
            )
        else:
            st.write(
                "Live evidence comes from current public provider responses. MeteoSwiss "
                "hourly mean temperature is never treated as a journey maximum. Future "
                "manual route checks remain unknown until renewed. Provider failures and "
                "coverage gaps do not trigger a simulated fallback."
            )


def main() -> None:
    """Present V2 planning with explicit live evidence and a fixed demo clock."""
    st.set_page_config(page_title="PulseShift · Treatment planner", layout="wide")
    theme = apply_theme()
    st.caption("OPERATIONS PREVIEW / MATERIAL FLOW")
    st.title("PulseShift · Treatment material-flow planner")
    st.warning(
        "Synthetic treatment demo — planning choices only; no transport or treatment booked."
    )
    state = st.session_state
    chapter = render_navigation()
    mode = render_evidence_mode(state.get("v2-mode-value", EvidenceMode.LIVE))
    previous_mode = state.get("v2-mode-value")
    if previous_mode is not None and mode != previous_mode:
        state["v2-overrides"] = DemoOverrides()
        state.pop("v2-live-flow", None)
        state.pop("v2-live-request", None)
        state.pop("comparison-v2-confirmed", None)
        state["v2-confirmed-id"] = None
    state["v2-mode-value"] = mode
    settings = load_settings(ROOT / "config" / "planning.json")
    baseline = baseline_overrides(settings)
    overrides = state.get("v2-overrides", DemoOverrides())
    overrides, reset = render_demo_controls(
        mode,
        overrides,
        baseline,
        clock=ORDER,
        station_label="Basel Rhine gauge (station level)",
    )
    if reset:
        overrides = DemoOverrides()
        state["v2-goal-value"] = PlanningGoal.LOWER_DISRUPTION_RISK
        state["v2-target-value"] = datetime(2026, 11, 8, 5, tzinfo=UTC)
        state["v2-reset-generation"] = state.get("v2-reset-generation", 0) + 1
        for name in tuple(state):
            if name.startswith(("v2-goal", "comparison-v2", "v2-demo-fields-")):
                state.pop(name, None)
        state["v2-confirmed-id"] = None
    if overrides != state.get("v2-overrides"):
        state["v2-overrides"] = overrides
        state["v2-confirmed-id"] = None
        state.pop("comparison-v2-confirmed", None)
    goal = state.get("v2-goal-value", PlanningGoal.LOWER_DISRUPTION_RISK)
    target = state.get("v2-target-value", datetime(2026, 11, 8, 5, tzinfo=UTC))
    if chapter == "Plan":
        goal, target = render_goal(goal, target)
        state["v2-goal-value"], state["v2-target-value"] = goal, target
    if mode == EvidenceMode.DEMO:
        flow = build_flow(mode, settings, overrides, baseline)
    else:
        if "v2-live-request" not in state:
            state["v2-live-request"] = live_request(datetime.now(UTC))
        request = render_route_inputs(state["v2-live-request"])
        if request != state["v2-live-request"]:
            state["v2-live-request"] = request
            state.pop("v2-live-flow", None)
        if st.button("Refresh live evidence"):
            request = replace(request, decision_time=datetime.now(UTC))
            state["v2-live-request"] = request
            state.pop("v2-live-flow", None)
            state.pop("v2-live-weather", None)
        if "v2-live-weather" not in state:
            state["v2-live-weather"] = WeatherLiveProvider(FORECAST_AGE)
        if "v2-live-flow" not in state:
            with st.spinner("Loading current Rhine and weather evidence"):
                state["v2-live-flow"] = build_flow(
                    mode,
                    settings,
                    DemoOverrides(),
                    baseline,
                    request=request,
                    weather=state["v2-live-weather"],
                )
        flow = state["v2-live-flow"]
        if flow.environment.river.issues or flow.environment.weather.issues:
            st.info("Live evidence has gaps or limits. Switch to Demo for an offline walkthrough.")
    context = (
        goal,
        target,
        mode,
        overrides,
        flow.request,
        flow.environment,
        state.get("v2-reset-generation", 0),
    )
    if state.get("v2-confirmation-context") != context:
        state["v2-confirmation-context"] = context
        state["v2-confirmed-id"] = None
        state.pop("comparison-v2-confirmed", None)
    recommendation = GoalRecommendationEngine().recommend(flow.plans, goal, target, flow.summaries)
    baseline_plan = next(
        (
            plan
            for plan in flow.plans
            if plan.ingredient_mode == TransportMode.SHIP
            and plan.outbound_mode == plan.return_mode == TransportMode.BICYCLE
            and plan.collection_shift == timedelta()
        ),
        None,
    )
    if chapter == "Plan":
        selected = render_comparison(
            flow.plans,
            request=flow.request,
            environment=flow.environment,
            compared_request=flow.request,
            compared_environment=flow.environment,
            recommendation=recommendation,
            route_summaries=flow.summaries,
            confirmation_context=context,
            baseline_plan=baseline_plan,
        )
        state["v2-confirmed-id"] = selected.plan_id if selected else None
    elif chapter == "Routes & conditions":
        plan_id = state.get("v2-confirmed-id") or state.get("comparison-v2-picked")
        if plan_id:
            render_route_summaries(flow.summaries, plan_id, theme)
        else:
            st.info("Choose a plan on the Plan chapter to inspect its routes.")
    else:
        render_evidence_sources(flow.request, flow.environment)
        render_sources(mode)
        render_rhine_conditions(ROOT, theme)
    st.caption(
        "Planning preview only. No patient records, clinical decisions or transport bookings."
    )


if __name__ == "__main__":
    main()
