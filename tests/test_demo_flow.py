"""End-to-end V2 checks using the same fixed demo flow as the screen."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from treatment_planner.interfaces import (
    Availability,
    DemoOverrides,
    EvidenceMode,
    PlanningGoal,
    ResultStatus,
    RouteSnow,
    RouteStatus,
    TransportMode,
)
from treatment_planner.planning import load_settings
from treatment_planner.recommendations import GoalRecommendationEngine
from treatment_planner.v2_flow import baseline_overrides, build_flow, live_request

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = load_settings(ROOT / "config/planning.json")


def screen():
    """Open a deterministic, network-free demo screen."""
    with patch("urllib.request.urlopen", side_effect=AssertionError("Demo used network")):
        app = AppTest.from_file(ROOT / "app.py")
        app.session_state["v2-mode-value"] = EvidenceMode.DEMO
        return app.run(timeout=30)


def button(app, label):
    return next(item for item in app.button if item.label == label)


def selectbox(app, label):
    return next(item for item in app.selectbox if item.label == label)


def demo_flow(overrides=DemoOverrides()):
    return build_flow(EvidenceMode.DEMO, SETTINGS, overrides, baseline_overrides(SETTINGS))


def test_default_demo_offline_has_ranked_checked_alternatives():
    flow = demo_flow()
    assert len(flow.plans) == 16
    assert all(plan.status == ResultStatus.CONFIRMED for plan in flow.plans)
    assert len(flow.summaries) == len(flow.plans) * 3
    result = GoalRecommendationEngine().recommend(
        flow.plans, PlanningGoal.LOWER_DISRUPTION_RISK, None, flow.summaries
    )
    assert result.winner_plan_ids
    assert len(result.scores) == len(flow.plans)
    app = screen()
    assert not app.exception
    assert button(app, "Confirm plan").disabled  # Equal winners require a choice.


def test_independent_snow_and_heat_edits_change_recommended_transport():
    baseline = baseline_overrides(SETTINGS)
    snowy = replace(baseline.sample, forecast_snowfall=True, route_snow=RouteSnow.PRESENT)
    hot = replace(baseline.treatment, maximum_temperature_c=30.1)
    flow = demo_flow(DemoOverrides(sample=snowy, treatment=hot))
    assert any(
        p.status == ResultStatus.CONFIRMED and p.outbound_mode == p.return_mode == TransportMode.CAR
        for p in flow.plans
    )
    assert all(
        p.status != ResultStatus.CONFIRMED
        for p in flow.plans
        if p.outbound_mode == TransportMode.BICYCLE or p.return_mode == TransportMode.BICYCLE
    )
    result = GoalRecommendationEngine().recommend(
        flow.plans, PlanningGoal.INGREDIENT_DELIVERY, None, flow.summaries
    )
    assert result.winner_plan_ids
    assert all(
        next(p for p in flow.plans if p.plan_id == plan_id).outbound_mode == TransportMode.CAR
        for plan_id in result.winner_plan_ids
    )


def test_unknown_rhine_level_never_confirms_ship_delivery():
    baseline = baseline_overrides(SETTINGS)
    flow = demo_flow(DemoOverrides(ingredients=replace(baseline.ingredients, gauge_height_cm=None)))
    assert all(
        p.status == ResultStatus.UNCONFIRMED
        for p in flow.plans
        if p.ingredient_mode == TransportMode.SHIP
    )
    assert any(
        p.status == ResultStatus.CONFIRMED
        for p in flow.plans
        if p.ingredient_mode == TransportMode.TRUCK
    )


def test_low_water_and_outbound_snow_keep_mixed_transport_available():
    baseline = baseline_overrides(SETTINGS)
    changed = DemoOverrides(
        ingredients=replace(baseline.ingredients, gauge_height_cm=250),
        sample=replace(baseline.sample, route_snow=RouteSnow.PRESENT),
        treatment=replace(baseline.treatment, car_availability=Availability.UNAVAILABLE),
    )
    flow = demo_flow(changed)
    assert any(
        p.status == ResultStatus.CONFIRMED
        and p.outbound_mode == TransportMode.CAR
        and p.return_mode == TransportMode.BICYCLE
        for p in flow.plans
    )
    assert all(
        p.status != ResultStatus.CONFIRMED
        for p in flow.plans
        if p.outbound_mode == TransportMode.BICYCLE
    )
    assert any(
        s.route.value == "Rotterdam to production"
        and s.status == RouteStatus.AT_RISK
        and s.possible_delay.total_seconds() == 12 * 3600
        for s in flow.summaries
    )


def test_screen_goal_route_edits_and_reset_clear_confirmation():
    app = screen()
    choice = selectbox(app, "Plan to confirm")
    choice.select(choice.options[0]).run()
    button(app, "Confirm plan").click().run()
    assert app.session_state["v2-confirmed-id"] is not None
    app.radio(key="v2-navigation").set_value("Sources & assumptions").run()
    app.radio(key="v2-navigation").set_value("Plan").run()
    assert app.session_state["v2-confirmed-id"] is not None
    app.radio(key="v2-goal").set_value(PlanningGoal.INGREDIENT_DELIVERY).run()
    assert app.session_state["v2-confirmed-id"] is None
    button(app, "🚲 Hospital → Production").click().run()
    selectbox(app, "Snow on route").select(RouteSnow.PRESENT)
    button(app, "Apply route conditions").click().run()
    assert app.session_state["v2-overrides"].sample.route_snow == RouteSnow.PRESENT
    assert app.session_state["v2-overrides"].treatment is None
    button(app, "Reset demo").click().run()
    assert app.session_state["v2-overrides"] == DemoOverrides()
    assert app.session_state["v2-confirmed-id"] is None
    assert app.radio(key="v2-goal").value == PlanningGoal.LOWER_DISRUPTION_RISK


def test_live_failure_stays_explicit_and_does_not_use_demo_evidence():
    from treatment_planner.interfaces import RiverForecastReport, RiverReport, WeatherReport
    from treatment_planner.rhine_demo import assess_live_evidence

    now = datetime(2026, 10, 3, 12, tzinfo=UTC)
    baseline = baseline_overrides(SETTINGS)

    class FailedWeather:
        def load(self, location, window):
            return WeatherReport((), ("Live weather unavailable: test failure",))

    def failed_rhine(interval, *, evaluated_at):
        return assess_live_evidence(
            interval,
            evaluated_at,
            RiverReport((), ("Rhine retrieval failed: test failure",)),
            RiverForecastReport(),
        )

    with patch("treatment_planner.v2_flow.load_live_rhine_evidence", failed_rhine):
        flow = build_flow(
            EvidenceMode.LIVE,
            SETTINGS,
            DemoOverrides(),
            baseline,
            request=live_request(now),
            weather=FailedWeather(),
        )
    assert all(p.status != ResultStatus.CONFIRMED for p in flow.plans)
    assert "retrieval failed" in " ".join(flow.environment.river.issues)
    assert "unavailable" in " ".join(flow.environment.weather.issues)


def test_application_opens_in_live_without_a_synthetic_fallback():
    from treatment_planner.interfaces import EnvironmentInputs, RiverReport, WeatherReport

    missing = EnvironmentInputs(
        RiverReport((), ("Live Rhine unavailable",)),
        WeatherReport((), ("Live weather unavailable",)),
    )
    with patch("treatment_planner.v2_flow._live_inputs", return_value=missing):
        app = AppTest.from_file(ROOT / "app.py").run(timeout=30)
    assert not app.exception
    assert app.radio(key="v2-mode").value == EvidenceMode.LIVE
    assert not any(item.label == "Reset demo" for item in app.button)
    assert button(app, "Confirm plan").disabled
    assert any("Switch to Demo" in item.value for item in app.info)
