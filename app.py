"""V2 guided treatment-material planning demo and integration entry point."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import streamlit as st

from treatment_planner.data.weather_live import WeatherLiveProvider
from treatment_planner.demo import ORDER, fixture_request
from treatment_planner.interfaces import (
    DemoOverrides,
    EnvironmentInputs,
    EvidenceMode,
    PlanningGoal,
    TimeWindow,
    TreatmentRequest,
)
from treatment_planner.planning import load_settings
from treatment_planner.recommendations import GoalRecommendationEngine
from treatment_planner.rhine_demo import RhineRouteEvidence, load_live_rhine_evidence
from treatment_planner.route_summaries import build_route_summaries
from treatment_planner.ui.comparison import render_comparison, render_sources
from treatment_planner.ui.demo_controls import render_demo_controls
from treatment_planner.ui.navigation import render_evidence_mode, render_navigation
from treatment_planner.ui.presentation import apply_theme
from treatment_planner.ui.recommendation import render_goal
from treatment_planner.ui.rhine import render_rhine_conditions
from treatment_planner.ui.rhine_gauge import rhine_gauge_chart
from treatment_planner.ui.route_inputs import render_route_inputs
from treatment_planner.ui.route_summary import render_route_summaries
from treatment_planner.v2_flow import (
    DEFAULT_INJECTION_OFFSET,
    LIVE_RHINE_LOCATION,
    LIVE_WEATHER_POINTS,
    _baseline_plan,
    _demo_baseline_templates,
    _demo_environment,
    _live_environment,
    _live_request,
    _request_with_demo_routes,
    _target_for,
)

ROOT = Path(__file__).resolve().parent
THEME_PATH = ROOT / "config" / "theme.toml"
LIVE_WEATHER_MAX_AGE = timedelta(hours=24)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_live_rhine(interval: TimeWindow, evaluated_at: datetime) -> RhineRouteEvidence:
    """Keep one explicit live evidence snapshot stable across page reruns."""
    return load_live_rhine_evidence(interval, evaluated_at=evaluated_at)


def _clear_confirmation_state() -> None:
    """Clear V2 selection state without changing navigation."""
    for key in list(st.session_state):
        if key.startswith(("comparison", "v2-recommendation")):
            st.session_state.pop(key, None)


def _clear_demo_reset_state() -> None:
    for key in list(st.session_state):
        if key.startswith(("v2-goal", "comparison", "v2-demo-fields-")):
            st.session_state.pop(key, None)


def _render_sources_chapter(
    request: TreatmentRequest,
    environment: EnvironmentInputs,
    mode: EvidenceMode,
    rhine: RhineRouteEvidence | None,
    theme: dict,
) -> None:
    render_sources(request, environment)
    st.markdown("### Data sources and limits")
    st.markdown(
        "- [MeteoSwiss forecast · CC BY 4.0](https://opendatadocs.meteoschweiz.ch/general/terms-of-use)\n"
        "- [Basel Rhine observations · CC0 1.0](https://data.bs.ch/explore/dataset/100089/)\n"
        "- [FOEN/BAFU forecast · free use with recommended attribution](https://www.hydrodaten.admin.ch/en/questions)"
    )
    st.write(
        "Treatment timings, vehicle durations and disruption effects are synthetic. "
        "The Basel gauge is a route-wide model proxy, not proof of Rotterdam–Basel "
        "navigability or a measured delivery time. MeteoSwiss hourly mean and daily "
        "maximum are separate forecast values. The planner does not book transport "
        "or make clinical decisions."
    )
    if mode == EvidenceMode.LIVE and rhine is not None:
        coverage = rhine.covered_until.isoformat() if rhine.covered_until else "unknown"
        st.caption(
            f"BAFU station-chart forecast coverage through {coverage} "
            f"({rhine.state.value}); shipping uses the current Basel gauge proxy."
        )
    with st.expander("Basel station chart · supporting evidence"):
        st.caption(
            "This chart is a station view for inspection. It does not change the "
            "ingredient-route evidence or simulated shipping delay."
        )
        render_rhine_conditions(ROOT, theme)


def _weather_icon(code: int | None, snowfall: bool | None) -> str:
    if snowfall is True:
        return "❄️"
    if code is None:
        return "❔"
    if code == 133:
        return "❔"
    if code in {
        8,
        11,
        16,
        19,
        22,
        30,
        34,
        37,
        39,
        42,
        108,
        111,
        116,
        119,
        122,
        130,
        134,
        137,
        139,
        142,
    }:
        return "❄️"
    if code in {7, 10, 15, 18, 21, 31, 107, 110, 115, 118, 121, 131}:
        return "🌨️"
    if code in {6, 9, 14, 17, 20, 29, 32, 33, 38, 106, 109, 114, 117, 120, 129, 132, 138}:
        return "🌧️"
    if code in {12, 13, 23, 24, 25, 36, 40, 41, 112, 113, 123, 124, 125, 136, 140, 141}:
        return "⛈️"
    if code in {27, 28, 127, 128}:
        return "🌫️"
    return "🌤️" if code % 100 < 20 else "☁️"


def _render_live_conditions(environment: EnvironmentInputs, settings, theme: dict) -> None:
    st.subheader("Live conditions at both Basel sites")
    weather_columns = st.columns(2)
    for column, location in zip(
        weather_columns,
        ("PulseShift production site, Basel", "University Hospital Basel"),
        strict=True,
    ):
        current = next(
            (window for window in environment.weather.windows if window.location == location),
            None,
        )
        with column:
            st.markdown(f"**{location}**")
            if current is None:
                st.metric("Current forecast", "Unavailable")
                issues = [issue for issue in environment.weather.issues if location in issue]
                for issue in issues:
                    st.caption(issue)
                continue
            temperature = current.hourly_mean_temperature_c
            label = f"{temperature:.1f} °C" if temperature is not None else "Unknown"
            icon = _weather_icon(current.weather_code, current.snowfall)
            st.metric("Temperature · current forecast", f"{icon} {label}")
            maximum = current.maximum_temperature_c
            maximum_label = f"Daily maximum: {maximum:.1f} °C" if maximum is not None else "Unknown"
            st.caption(maximum_label)
            st.caption(
                "Snowfall indicated"
                if current.snowfall is True
                else "No snowfall indicated"
                if current.snowfall is False
                else "Snowfall status unknown"
            )
            st.caption(current.provenance.source)

    st.markdown("**Basel Rhine gauge · route-wide model proxy**")
    observation = (
        max(environment.river.observations, key=lambda item: item.observed_at)
        if environment.river.observations
        else None
    )
    level_m = observation.water_level_m if observation else None
    level_cm = level_m * 100 if level_m is not None else None
    st.altair_chart(
        rhine_gauge_chart(
            level_cm,
            observation.observed_at if observation and level_cm is not None else None,
            theme,
        ),
        width="stretch",
    )
    st.caption(
        "The colored bands follow the notebook thresholds. Hover over a band for its range "
        "and meaning. "
        "The current level is marked on the scale."
    )
    if level_m is not None:
        st.caption(
            f"Gauge height {level_m:.3f} m · "
            f"observed {observation.observed_at:%Y-%m-%d %H:%M UTC}. "
            "Model assumption: Basel level applies along the whole ship route."
        )
        st.caption(
            f"Simplified shipping delay model: "
            f"{settings.river_delay.total_seconds() / 3600:g} h. "
            "This is a model output, not a measured delivery time."
        )
        if environment.river.issues:
            st.warning("; ".join(environment.river.issues))
    else:
        st.info("Current Rhine gauge reading unavailable; ship timing remains unconfirmed.")


def main() -> None:
    st.set_page_config(page_title="Treatment material-flow planner", layout="wide")
    theme = apply_theme(THEME_PATH)
    st.title("Treatment material-flow planner")
    st.caption("Compare ingredient, sample and treatment routes before confirming a plan.")
    st.warning("Planning preview only. No treatment or transport is booked.")

    state = st.session_state
    settings = load_settings(ROOT / "config" / "planning.json")
    chapter = render_navigation()
    previous_mode = state.get("v2-active-mode")
    selected_mode = render_evidence_mode(
        previous_mode or EvidenceMode.LIVE,
        key="v2-mode",
    )
    if previous_mode is None:
        state["v2-active-mode"] = selected_mode
    elif selected_mode != previous_mode:
        state["v2-active-mode"] = selected_mode
        state["v2-overrides"] = DemoOverrides()
        state["v2-reset-generation"] = state.get("v2-reset-generation", 0) + 1
        _clear_confirmation_state()
        for key in list(state):
            if key.startswith("v2-goal"):
                state.pop(key, None)

        if selected_mode == EvidenceMode.DEMO:
            state["v2-goal-value"] = PlanningGoal.LOWER_DISRUPTION_RISK
            state["v2-target"] = ORDER + DEFAULT_INJECTION_OFFSET
            state["v2-demo-clock"] = ORDER
        state["v2-inputs-changed"] = True

    demo_clock = state.get("v2-demo-clock", ORDER)
    baseline_templates = _demo_baseline_templates(settings)
    overrides = state.get("v2-overrides", DemoOverrides())
    new_overrides, reset_requested = render_demo_controls(
        selected_mode,
        overrides,
        baseline_templates,
        clock=demo_clock,
        station_label=LIVE_RHINE_LOCATION,
        key="v2-demo",
    )
    if reset_requested:
        state["v2-overrides"] = DemoOverrides()
        state["v2-goal-value"] = PlanningGoal.LOWER_DISRUPTION_RISK
        state.pop("v2-goal", None)
        state["v2-target"] = ORDER + DEFAULT_INJECTION_OFFSET
        state["v2-target-mode"] = EvidenceMode.DEMO
        state["v2-demo-clock"] = ORDER
        state["v2-reset-generation"] = state.get("v2-reset-generation", 0) + 1
        _clear_demo_reset_state()
        state["v2-inputs-changed"] = True
        st.rerun()
    if new_overrides != overrides:
        state["v2-overrides"] = new_overrides
        state["v2-reset-generation"] = state.get("v2-reset-generation", 0) + 1
        st.rerun()
    overrides = state.get("v2-overrides", DemoOverrides())

    if selected_mode == EvidenceMode.LIVE:
        if st.button("Refresh live evidence", key="v2-refresh-live"):
            state["v2-live-as-of"] = datetime.now(UTC)
            state["v2-reset-generation"] = state.get("v2-reset-generation", 0) + 1
            providers = state.get("v2-weather-providers", {})
            for provider in providers.values():
                provider.refresh()
            _cached_live_rhine.clear()
            st.rerun()
        now = state.setdefault("v2-live-as-of", datetime.now(UTC))
        request = state.get("v2-live-request")
        if request is None or request.decision_time != now:
            previous_routes = request.routes if request is not None else None
            request = _live_request(now)
            if previous_routes is not None:
                request = replace(request, routes=previous_routes)
            state["v2-live-request"] = request
        request = render_route_inputs(request, key="v2-live-routes", live_mode=True)
        state["v2-live-request"] = request
        providers = state.get("v2-weather-providers")
        if providers is None:
            providers = {
                postcode: WeatherLiveProvider(LIVE_WEATHER_MAX_AGE, postal_code=postcode)
                for postcode in LIVE_WEATHER_POINTS
            }
            state["v2-weather-providers"] = providers
        with st.spinner("Loading Rhine and endpoint weather evidence…"):
            environment, settings_for_run, plans, rhine = _live_environment(
                request, settings, now, providers, _cached_live_rhine
            )
        _render_live_conditions(environment, settings_for_run, theme)
    else:
        state.pop("v2-live-request", None)
        request = fixture_request()
        request = _request_with_demo_routes(request, overrides)
        environment, settings_for_run, plans = _demo_environment(
            request, settings, overrides, baseline_templates
        )
        rhine = None

    summaries = build_route_summaries(
        plans,
        request,
        environment,
        selected_mode,
        settings_for_run,
        overrides=overrides if selected_mode == EvidenceMode.DEMO else DemoOverrides(),
        baseline=baseline_templates if selected_mode == EvidenceMode.DEMO else DemoOverrides(),
        rhine=rhine,
    )
    goal = state.get("v2-goal-value", PlanningGoal.LOWER_DISRUPTION_RISK)
    default_target = (
        ORDER + DEFAULT_INJECTION_OFFSET
        if selected_mode == EvidenceMode.DEMO
        else _target_for(request)
    )
    if state.get("v2-target-mode") != selected_mode:
        state["v2-target"] = default_target
        state["v2-target-mode"] = selected_mode
    target = state.get(
        "v2-target",
        default_target,
    )
    if chapter == "Plan":
        goal, target = render_goal(goal, target, key="v2-goal")
        state["v2-goal-value"], state["v2-target"] = goal, target

    recommendation = GoalRecommendationEngine().recommend(plans, goal, target, summaries)
    baseline_plan = _baseline_plan(plans)
    context = (
        selected_mode,
        goal,
        target,
        overrides if selected_mode == EvidenceMode.DEMO else request.routes,
        environment,
        state.get("v2-reset-generation", 0),
    )
    previous_context = state.get("v2-planning-context")
    if previous_context is not None and previous_context != context:
        _clear_confirmation_state()
        state["v2-inputs-changed"] = True
    state["v2-planning-context"] = context

    if chapter == "Plan":
        if state.pop("v2-inputs-changed", False):
            st.info(
                "Planning inputs or evidence changed. Review and confirm the updated plan again."
            )
        st.subheader("Planning goal and recommendation")
        selected = render_comparison(
            plans,
            request=request,
            environment=environment,
            compared_request=request,
            compared_environment=environment,
            key="comparison",
            theme_path=THEME_PATH,
            recommendation=recommendation,
            route_summaries=summaries,
            confirmation_context=context,
            baseline_plan=baseline_plan,
        )
        state["v2-confirmed-plan"] = selected.plan_id if selected else None
    elif chapter == "Routes & conditions":
        st.subheader("Inspect a route for an alternative")
        plan_ids = [plan.plan_id for plan in plans]
        winner_ids = recommendation.winner_plan_ids
        default_plan = (
            winner_ids[0]
            if len(winner_ids) == 1
            else (
                state.get("v2-route-plan")
                if state.get("v2-route-plan") in plan_ids
                else plan_ids[0]
            )
        )
        route_plan = st.selectbox(
            "Alternative",
            plan_ids,
            index=plan_ids.index(default_plan) if default_plan in plan_ids else 0,
            format_func=lambda plan_id: next(
                f"{plan.title} · {plan.status.value}" for plan in plans if plan.plan_id == plan_id
            ),
            key="v2-route-plan",
        )
        render_route_summaries(summaries, route_plan, theme, key="v2-route-details")
        if selected_mode == EvidenceMode.LIVE:
            st.caption(
                "Manual route and vehicle checks are coordinator inputs; "
                "snowfall blocks bicycles. Cars are always available and need one hour "
                "of preparation. A 28°C forecast prompts a weather recheck on the trip day."
            )
    else:
        _render_sources_chapter(request, environment, selected_mode, rhine, theme)


if __name__ == "__main__":
    main()
