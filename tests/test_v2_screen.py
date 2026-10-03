"""Exercise the V2 UI against supplied contracts, without ranking or adapters."""

from streamlit.testing.v1 import AppTest

from treatment_planner.interfaces import EvidenceMode, PlanningGoal, RouteSnow

APP = """
from datetime import timedelta
import streamlit as st
from treatment_planner.demo import (
    ORDER, EVIDENCE, FixtureComparator, fixture_request, fixture_environment, fixture_settings,
)
from treatment_planner.interfaces import (
    Availability, CourierLeg, DemoOverrides, EvidenceMode, IngredientRouteOverride,
    LocalRouteOverride, PlanningGoal, RecommendationResult, RecommendationScore,
    ResultStatus, RouteId, RouteSnow, RouteStatus, RouteSummary, TimeWindow,
)
from treatment_planner.ui.comparison import render_comparison, render_sources
from treatment_planner.ui.demo_controls import render_demo_controls
from treatment_planner.ui.navigation import render_evidence_mode, render_navigation
from treatment_planner.ui.recommendation import render_goal
from treatment_planner.ui.route_summary import render_route_summaries
from treatment_planner.ui.presentation import apply_theme
window = TimeWindow(ORDER, ORDER + timedelta(hours=2))
baseline = DemoOverrides(
    IngredientRouteOverride(400., window, EVIDENCE),
    LocalRouteOverride(CourierLeg.OUTBOUND, window, 20., False, RouteSnow.CLEAR,
                       Availability.AVAILABLE, EVIDENCE),
    LocalRouteOverride(CourierLeg.RETURN, window, 21., False, RouteSnow.CLEAR,
                       Availability.AVAILABLE, EVIDENCE),
)
state = st.session_state
chapter = render_navigation()
mode = render_evidence_mode(EvidenceMode.DEMO)
old = state.get('overrides', DemoOverrides())
overrides, reset = render_demo_controls(mode, old, baseline, clock=ORDER,
                                       station_label='Basel fixture gauge')
state['overrides'] = overrides
state['reset'] = reset
if reset:
    for name in list(state):
        if name.startswith('v2-goal') or name.startswith('comparison-v2'):
            state.pop(name)
    state['reset_count'] = state.get('reset_count', 0) + 1
    state['goal'] = PlanningGoal.LOWER_DISRUPTION_RISK
    state['target'] = ORDER + timedelta(days=7)
if overrides != old and not reset:
    st.rerun()
goal = state.get('goal', PlanningGoal.LOWER_DISRUPTION_RISK)
target = state.get('target', ORDER + timedelta(days=7))
if chapter == 'Plan':
    goal, target = render_goal(goal, target)
    state['goal'], state['target'] = goal, target
request = fixture_request()
environment = fixture_environment('Low water')
plans = FixtureComparator('Low water').compare(request, environment, fixture_settings('Low water'))
if state.get('warm'):
    from dataclasses import replace
    environment = replace(environment, weather=replace(environment.weather,
        windows=tuple(replace(w, maximum_temperature_c=29.)
                      for w in environment.weather.windows)))
eligible = tuple(p for p in plans if p.status == ResultStatus.CONFIRMED)
scores = tuple(RecommendationScore(p.plan_id, limiting_margin=timedelta(hours=6),
                                  at_risk_routes=0) for p in eligible)
winners = (eligible[0].plan_id,)
if state.get('tie'):
    winners = tuple(p.plan_id for p in eligible)
if state.get('none'):
    winners = ()
if state.get('invalid'):
    winners = (plans[0].plan_id,)
    scores += (RecommendationScore(plans[0].plan_id),)
recommendation = RecommendationResult(goal, winners, scores, 'Contract example; not engine-ranked.')
summaries = tuple(
    RouteSummary(p.plan_id, route, window, transport, mode,
                 RouteStatus.UNKNOWN if state.get('unknown_summary') else RouteStatus.NORMAL,
                 'Evidence missing' if state.get('unknown_summary') else 'Fixture checks pass',
                 (EVIDENCE,), carried_from=TimeWindow(ORDER - timedelta(hours=2), ORDER)
                 if mode == EvidenceMode.DEMO and state.get('carry') else None)
    for p in plans for route, transport in (
        (RouteId.INGREDIENTS, p.ingredient_mode), (RouteId.SAMPLE, p.outbound_mode),
        (RouteId.TREATMENT, p.return_mode))
)
if state.get('missing_summary'):
    summaries = tuple(item for item in summaries if not
        (item.plan_id == eligible[0].plan_id and item.route == RouteId.INGREDIENTS))
if state.get('changed_inputs'):
    from dataclasses import replace
    request = replace(request, decision_time=request.decision_time + timedelta(minutes=1))
if chapter == 'Plan':
    selected = render_comparison(plans, request=request, environment=environment,
        compared_request=fixture_request(), compared_environment=environment,
        recommendation=recommendation, route_summaries=summaries,
        confirmation_context=(goal, target, mode, overrides, state.get('reset_count', 0)))
    state['confirmed_id'] = selected.plan_id if selected else None
elif chapter == 'Routes & conditions':
    picked = state.get('comparison-v2-picked')
    if picked:
        render_route_summaries(summaries, picked, apply_theme())
    else:
        st.info('Choose a plan on the Plan chapter to inspect its routes.')
else:
    render_sources(request, environment)
"""


def app():
    return AppTest.from_string(APP).run(timeout=30)


def button(screen, label):
    return next(value for value in screen.button if value.label == label)


def selectbox(screen, label):
    return next(value for value in screen.selectbox if value.label == label)


def test_unique_winner_is_preselected_but_needs_confirmation_and_optional_details():
    screen = app()
    assert not screen.exception
    assert selectbox(screen, "Plan to confirm").value == "postpone"
    assert screen.session_state["confirmed_id"] is None
    button(screen, "Confirm plan").click().run()
    assert screen.session_state["confirmed_id"] == "postpone"
    assert all(not expander.proto.expanded for expander in screen.expander)
    screen.run()
    assert screen.session_state["confirmed_id"] == "postpone"


def test_tied_leaders_require_a_choice_and_empty_or_invalid_result_cannot_confirm():
    screen = app()
    screen.session_state["tie"] = True
    screen.run()
    assert selectbox(screen, "Plan to confirm").value is None
    assert button(screen, "Confirm plan").disabled
    selectbox(screen, "Plan to confirm").select("truck").run()
    button(screen, "Confirm plan").click().run()
    assert screen.session_state["confirmed_id"] == "truck"
    screen.radio(key="v2-navigation").set_value("Routes & conditions").run()
    screen.radio(key="v2-navigation").set_value("Plan").run()
    assert selectbox(screen, "Plan to confirm").value == "truck"
    assert screen.session_state["confirmed_id"] == "truck"
    for flag in ("none", "invalid"):
        screen = app()
        screen.session_state[flag] = True
        screen.run()
        assert not screen.exception
        assert button(screen, "Confirm plan").disabled
        assert screen.session_state["confirmed_id"] is None


def test_navigation_preserves_confirmation_but_goal_and_stale_inputs_clear_it():
    screen = app()
    button(screen, "Confirm plan").click().run()
    screen.radio(key="v2-navigation").set_value("Sources & assumptions").run()
    screen.radio(key="v2-navigation").set_value("Plan").run()
    assert screen.session_state["confirmed_id"] == "postpone"
    screen.radio(key="v2-goal").set_value(PlanningGoal.INGREDIENT_DELIVERY).run()
    assert screen.session_state["confirmed_id"] is None
    button(screen, "Confirm plan").click().run()
    screen.session_state["changed_inputs"] = True
    screen.run()
    assert button(screen, "Confirm plan").disabled
    assert screen.session_state["confirmed_id"] is None


def test_local_demo_edits_are_independent_and_unknown_snow_is_not_clear():
    screen = app()
    button(screen, "🚲 Hospital → Production").click().run()
    selectbox(screen, "Forecast snowfall").select("Unknown")
    selectbox(screen, "Snow on route").select(RouteSnow.PRESENT)
    button(screen, "Apply route conditions").click().run()
    assert not screen.exception
    overrides = screen.session_state["overrides"]
    assert overrides.sample.forecast_snowfall is None
    assert overrides.sample.route_snow.value == "snow present"
    assert overrides.treatment is None and overrides.ingredients is None
    button(screen, "🚲 Production → Hospital").click().run()
    assert selectbox(screen, "Snow on route").value == "clear"
    selectbox(screen, "Snow on route").select(RouteSnow.PRESENT)
    button(screen, "Cancel").click().run()
    assert screen.session_state["overrides"] == overrides


def test_demo_reset_restores_goal_and_live_removes_overrides_and_confirmation():
    screen = app()
    button(screen, "🚢 Rotterdam → Basel").click().run()
    screen.number_input[0].set_value(250.0)
    button(screen, "Apply route conditions").click().run()
    assert screen.session_state["overrides"].ingredients.gauge_height_cm == 250.0
    screen.radio(key="v2-goal").set_value(PlanningGoal.INJECTION_TIMING).run()
    button(screen, "Confirm plan").click().run()
    button(screen, "Reset demo").click().run()
    assert not screen.exception
    assert screen.radio(key="v2-goal").value == "lower disruption risk"
    assert screen.session_state["overrides"].ingredients is None
    assert screen.session_state["confirmed_id"] is None
    button(screen, "Confirm plan").click().run()
    screen.radio(key="v2-mode").set_value(EvidenceMode.LIVE).run()
    assert screen.session_state["overrides"].sample is None
    assert screen.session_state["confirmed_id"] is None
    assert not any("Reset demo" == item.label for item in screen.button)


def test_missing_summary_and_carry_over_are_visible_with_unknown_delay():
    screen = app()
    screen.session_state["unknown_summary"] = True
    screen.session_state["carry"] = True
    screen.run()
    assert not screen.exception
    assert any("Unknown" in text.value for text in screen.markdown)
    assert any("Delay unknown" in text.value for text in screen.caption)
    assert any("carried over" in text.value for text in screen.caption)
    assert any("Previous trip:" in text.value for text in screen.markdown)
    screen.session_state["missing_summary"] = True
    screen.run()
    assert any("Route summary unavailable" in text.value for text in screen.markdown)
    assert button(screen, "Confirm plan").disabled


def test_target_change_invalidates_confirmation_even_when_supplied_scores_stay_equal():
    screen = app()
    screen.radio(key="v2-goal").set_value(PlanningGoal.INJECTION_TIMING).run()
    button(screen, "Confirm plan").click().run()
    from datetime import time

    screen.time_input(key="v2-goal-time").set_value(time(9, 0)).run()
    assert screen.session_state["confirmed_id"] is None


def test_invalid_demo_interval_does_not_apply_a_route_edit():
    from datetime import time

    screen = app()
    button(screen, "🚲 Hospital → Production").click().run()
    screen.time_input(key="v2-demo-fields-SAMPLE-Until-time").set_value(time(7, 0))
    button(screen, "Apply route conditions").click().run()
    assert not screen.exception
    assert screen.session_state["overrides"].sample is None
    assert any("end time must be after" in message.value for message in screen.error)


def test_integrated_trip_day_advisory_is_visible_and_does_not_change_confirmation():
    screen = app()
    screen.session_state["warm"] = True
    screen.run()
    reminders = [
        message.value for message in screen.warning if "warning threshold" in message.value
    ]
    assert reminders
    assert any("08.11.2026 UTC" in message for message in reminders)
    assert not any("2026-11-08" in message for message in reminders)
    assert not button(screen, "Confirm plan").disabled
    button(screen, "Confirm plan").click().run()
    assert screen.session_state["confirmed_id"] == "postpone"
