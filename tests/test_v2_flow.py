"""Application integration for live evidence, demo controls and recommendations."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

import app
from treatment_planner.demo import ORDER, fixture_request
from treatment_planner.interfaces import (
    Availability,
    DemoOverrides,
    EvidenceKind,
    EvidenceMode,
    PlanningGoal,
    Provenance,
    ResultStatus,
    RiverForecastReport,
    RiverObservation,
    RiverReport,
    RouteId,
    RouteSnow,
    RouteStatus,
    TimeWindow,
    TransportMode,
    WeatherReport,
    WeatherWindow,
)
from treatment_planner.planning import load_settings
from treatment_planner.recommendations import GoalRecommendationEngine
from treatment_planner.rhine_demo import RhineEvidenceState, RhineRouteEvidence
from treatment_planner.v2_flow import _event

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 3, 12, tzinfo=UTC)


def demo_parts(overrides=DemoOverrides()):
    settings = load_settings(ROOT / "config" / "planning.json")
    baseline = app._demo_baseline_templates(settings)
    request = app._request_with_demo_routes(fixture_request(), overrides)
    environment, settings, plans = app._demo_environment(request, settings, overrides, baseline)
    summaries = app.build_route_summaries(
        plans,
        request,
        environment,
        EvidenceMode.DEMO,
        settings,
        overrides=overrides,
        baseline=baseline,
    )
    recommendation = GoalRecommendationEngine().recommend(
        plans,
        PlanningGoal.LOWER_DISRUPTION_RISK,
        ORDER + app.DEFAULT_INJECTION_OFFSET,
        summaries,
    )
    return baseline, request, environment, settings, plans, summaries, recommendation


def test_demo_builds_three_evidence_backed_routes_and_recommends_a_confirmed_plan():
    _, _, _, _, plans, summaries, recommendation = demo_parts()
    assert len(summaries) == len(plans) * 3
    assert recommendation.winner_plan_ids
    winners = {plan.plan_id for plan in plans if plan.status == ResultStatus.CONFIRMED}
    assert set(recommendation.winner_plan_ids) <= winners
    assert all(
        len([item for item in summaries if item.plan_id == plan_id]) == 3
        for plan_id in recommendation.winner_plan_ids
    )


def test_low_water_demo_input_changes_ship_timing_and_marks_only_its_route_at_risk():
    settings = load_settings(ROOT / "config" / "planning.json")
    baseline = app._demo_baseline_templates(settings)
    low_water = replace(baseline.ingredients, gauge_height_cm=475.0)
    overrides = DemoOverrides(ingredients=low_water)
    _, _, _, settings, plans, summaries, _ = demo_parts(overrides)
    ship_plans = [plan for plan in plans if plan.ingredient_mode == TransportMode.SHIP]
    assert ship_plans
    assert all(settings.river_delay == timedelta(hours=12) for _ in ship_plans)
    assert all(
        next(
            item
            for item in summaries
            if item.plan_id == plan.plan_id and item.route == RouteId.INGREDIENTS
        ).status
        == RouteStatus.AT_RISK
        for plan in ship_plans
    )
    arrival = _event(ship_plans[0], "ingredients").interval.end
    assert arrival == fixture_request().order_time + timedelta(hours=156)


def test_unknown_demo_gauge_keeps_ship_plans_unconfirmed_and_unranked():
    settings = load_settings(ROOT / "config" / "planning.json")
    baseline = app._demo_baseline_templates(settings)
    overrides = DemoOverrides(ingredients=replace(baseline.ingredients, gauge_height_cm=None))
    _, _, _, _, plans, summaries, recommendation = demo_parts(overrides)
    ship_ids = {plan.plan_id for plan in plans if plan.ingredient_mode == TransportMode.SHIP}
    assert ship_ids
    assert all(plan.status != ResultStatus.CONFIRMED for plan in plans if plan.plan_id in ship_ids)
    assert all(
        next(
            item
            for item in summaries
            if item.plan_id == plan_id and item.route == RouteId.INGREDIENTS
        ).status
        == RouteStatus.UNKNOWN
        for plan_id in ship_ids
    )
    assert all(
        plan.ingredient_mode != TransportMode.SHIP
        for plan in plans
        if plan.plan_id in recommendation.winner_plan_ids
    )


def test_outbound_snow_and_unavailable_return_car_keep_confirmed_car_bicycle_option():
    settings = load_settings(ROOT / "config" / "planning.json")
    baseline = app._demo_baseline_templates(settings)
    outbound = replace(baseline.sample, route_snow=RouteSnow.PRESENT)
    returning = replace(baseline.treatment, car_availability=Availability.UNAVAILABLE)
    overrides = DemoOverrides(sample=outbound, treatment=returning)
    _, _, _, _, plans, summaries, recommendation = demo_parts(overrides)

    candidates = [
        plan
        for plan in plans
        if plan.outbound_mode == TransportMode.CAR
        and plan.return_mode == TransportMode.BICYCLE
        and plan.status == ResultStatus.CONFIRMED
    ]
    assert candidates
    assert set(recommendation.winner_plan_ids) & {plan.plan_id for plan in candidates}
    for plan in candidates:
        route_summaries = [item for item in summaries if item.plan_id == plan.plan_id]
        assert len(route_summaries) == 3


def test_live_failure_stays_unknown_without_demo_or_replay_fallback(monkeypatch):
    interval = app.TimeWindow(NOW + timedelta(hours=6), NOW + timedelta(days=6))
    rhine = RhineRouteEvidence(
        interval,
        NOW,
        RiverReport((), ("Rhine request failed.",)),
        RiverForecastReport(issues=("BAFU forecast unavailable.",)),
        RhineEvidenceState.MISSING,
        None,
        ("Live Rhine evidence missing.",),
    )
    monkeypatch.setattr(app, "_cached_live_rhine", lambda *args: rhine)

    class FailedWeatherProvider:
        def load(self, location, window):
            return WeatherReport((), (f"Live weather unavailable for {location}.",))

    request = app._live_request(NOW)
    settings = load_settings(ROOT / "config" / "planning.json")
    providers = {postcode: FailedWeatherProvider() for postcode in app.LIVE_WEATHER_POINTS}
    environment, settings, plans, loaded = app._live_environment(
        request, settings, NOW, providers, lambda *_: rhine
    )
    summaries = app.build_route_summaries(
        plans, request, environment, EvidenceMode.LIVE, settings, rhine=loaded
    )
    assert loaded.state is RhineEvidenceState.MISSING
    assert all("unavailable" in issue.lower() for issue in environment.weather.issues)
    assert all(
        next(
            item
            for item in summaries
            if item.plan_id == plan.plan_id and item.route == RouteId.INGREDIENTS
        ).status
        == RouteStatus.UNKNOWN
        for plan in plans
    )
    assert all(
        window.provenance.kind != EvidenceKind.SYNTHETIC for window in environment.weather.windows
    )
    assert settings.car_preparation == timedelta(hours=1)


def test_live_uses_both_sites_snow_only_bicycle_rule_and_basel_gauge_model():
    settings = load_settings(ROOT / "config" / "planning.json")
    request = app._live_request(NOW)
    provenance = Provenance("Coordinator", EvidenceKind.MANUAL, NOW, NOW)
    request = replace(
        request,
        routes=tuple(
            replace(
                route,
                snow=RouteSnow.CLEAR,
                checked_at=NOW,
                provenance=provenance,
            )
            for route in request.routes
        ),
    )
    observed = RiverObservation(
        "Basel gauge", NOW - timedelta(minutes=5), provenance, water_level_m=4.75
    )
    rhine = RhineRouteEvidence(
        TimeWindow(NOW, NOW + timedelta(days=10)),
        NOW,
        RiverReport((observed,)),
        RiverForecastReport(),
        RhineEvidenceState.AVAILABLE,
        NOW + timedelta(days=10),
    )

    class EndpointWeather:
        def __init__(self, postal_code):
            self.postal_code = postal_code
            self.calls = []

        def load(self, location, window):
            self.calls.append(location)
            source = f"MeteoSwiss {self.postal_code}"
            forecast_source = Provenance(source, EvidenceKind.FORECAST, NOW, NOW)
            return WeatherReport(
                (WeatherWindow(location, window, 29.0, False, forecast_source, 45.0, 1),)
            )

    providers = {code: EndpointWeather(code) for code in app.LIVE_WEATHER_POINTS}
    environment, live_settings, plans, loaded = app._live_environment(
        request, settings, NOW, providers, lambda *_: rhine
    )

    assert loaded is rhine
    assert live_settings.car_preparation == timedelta(hours=1)
    assert live_settings.river_delay == timedelta(hours=12)
    assert all(
        app.LIVE_WEATHER_POINTS[code] in {window.location for window in environment.weather.windows}
        for code in providers
    )
    assert all("hospital to factory" in provider.calls for provider in providers.values())
    assert all("factory to hospital" in provider.calls for provider in providers.values())
    bicycle_plans = [
        plan for plan in plans if TransportMode.BICYCLE in (plan.outbound_mode, plan.return_mode)
    ]
    assert bicycle_plans
    for plan in bicycle_plans:
        weather_checks = [check for check in plan.checks if "weather" in check.constraint.lower()]
        assert weather_checks
        assert all(check.status.value == "pass" for check in weather_checks)


def test_streamlit_app_opens_offline_demo_and_keeps_route_chapters_available():
    screen = AppTest.from_file(str(ROOT / "app.py"))
    screen.session_state["v2-mode"] = EvidenceMode.DEMO
    screen.run(timeout=30)
    assert not screen.exception
    assert any(button.label == "Confirm plan" for button in screen.button)
    screen.radio(key="v2-navigation").set_value("Routes & conditions").run(timeout=30)
    assert not screen.exception
    assert any(select.label == "Alternative" for select in screen.selectbox)
    screen.radio(key="v2-navigation").set_value("Sources & assumptions").run(timeout=30)
    assert not screen.exception


def test_live_screen_shows_both_forecasts_and_route_status_inputs(monkeypatch):
    interval = TimeWindow(NOW, NOW + timedelta(days=7))
    rhine = RhineRouteEvidence(
        interval,
        NOW,
        RiverReport((), ("No current gauge observation.",)),
        RiverForecastReport(),
        RhineEvidenceState.MISSING,
        None,
        ("No current gauge observation.",),
    )

    class FakeWeatherProvider:
        def __init__(self, maximum_forecast_age, *, postal_code):
            self.postal_code = postal_code

        def load(self, location, window):
            provenance = Provenance(
                f"MeteoSwiss {self.postal_code}", EvidenceKind.FORECAST, NOW, NOW
            )
            return WeatherReport(
                (WeatherWindow(location, window, 29.0, False, provenance, 18.0, 1),)
            )

        def refresh(self):
            pass

    monkeypatch.setattr(app, "WeatherLiveProvider", FakeWeatherProvider)
    monkeypatch.setattr(app, "_cached_live_rhine", lambda *args: rhine)
    screen = AppTest.from_file(str(ROOT / "app.py"))
    screen.session_state["v2-live-as-of"] = NOW
    screen.run(timeout=30)

    assert not screen.exception
    assert any("Live conditions at both Basel sites" in item.value for item in screen.subheader)
    assert any("PulseShift production site, Basel" in item.value for item in screen.markdown)
    assert any("University Hospital Basel" in item.value for item in screen.markdown)
    assert sum(select.label == "Snow on this road?" for select in screen.selectbox) == 2
    screen.radio(key="v2-navigation").set_value("Routes & conditions").run(timeout=30)
    assert not screen.exception
    assert sum(select.label == "Snow on this road?" for select in screen.selectbox) == 2
    captions = [item.value for item in screen.caption]
    assert any(
        "University Hospital Basel → PulseShift production site" in value for value in captions
    )
    assert any(
        "PulseShift production site → University Hospital Basel" in value for value in captions
    )
