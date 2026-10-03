"""Agreed V2-1 arithmetic examples and real-planner acceptance scenarios."""

import json
from dataclasses import replace
from datetime import timedelta, timezone
from pathlib import Path

import pytest

from treatment_planner.demo import EVIDENCE, ORDER, fixture_request
from treatment_planner.interfaces import (
    Availability,
    CheckStatus,
    CourierLeg,
    EnvironmentInputs,
    EvidenceMode,
    PlanningGoal,
    RecommendationEngine,
    ResultStatus,
    RiverReport,
    RouteId,
    RouteStatus,
    RouteSummary,
    TimeWindow,
    TransportMode,
    WeatherReport,
    WeatherWindow,
)
from treatment_planner.planning import PlanningComparator, load_settings
from treatment_planner.recommendations import GoalRecommendationEngine

H = timedelta(hours=1)
MINUTE = timedelta(minutes=1)
INJECTION = PlanningGoal.INJECTION_TIMING
DELIVERY = PlanningGoal.INGREDIENT_DELIVERY
RISK = PlanningGoal.LOWER_DISRUPTION_RISK


@pytest.fixture
def engine():
    return GoalRecommendationEngine()


@pytest.fixture
def settings():
    return load_settings(Path(__file__).resolve().parents[1] / "config/planning.json")


def environment(*, outbound_snow=False, return_heat=False, missing=False):
    windows = tuple(
        WeatherWindow(
            leg.value,
            TimeWindow(ORDER, ORDER + 400 * H),
            30.1 if return_heat and leg == CourierLeg.RETURN else 20,
            outbound_snow and leg == CourierLeg.OUTBOUND,
            EVIDENCE,
        )
        for leg in CourierLeg
    )
    return EnvironmentInputs(RiverReport(()), WeatherReport(() if missing else windows))


@pytest.fixture
def baseline(settings):
    return PlanningComparator(t4_replay=True).evaluate(
        fixture_request(),
        environment(),
        settings,
        TransportMode.SHIP,
        TransportMode.BICYCLE,
        TransportMode.BICYCLE,
        timedelta(),
    )


def changed(plan, plan_id, *, injection=None, arrival=None, margin=None):
    checks = tuple(
        replace(
            check,
            actual_time=(
                injection
                if check.constraint == "Injection" and injection is not None
                else arrival
                if check.constraint == "Ingredient arrival" and arrival is not None
                else check.actual_time
            ),
            margin=margin
            if check.constraint == "Injection" and margin is not None
            else check.margin,
        )
        for check in plan.checks
    )
    return replace(plan, plan_id=plan_id, checks=checks)


def summary(plan, route=RouteId.SAMPLE, status=RouteStatus.NORMAL):
    event_id = (
        "sample"
        if route == RouteId.SAMPLE
        else "return"
        if route == RouteId.TREATMENT
        else "ingredients"
    )
    return RouteSummary(
        plan.plan_id,
        route,
        next(e.interval for e in plan.events if e.event_id == event_id),
        plan.outbound_mode if route == RouteId.SAMPLE else plan.return_mode,
        EvidenceMode.DEMO,
        status,
        "Synthetic source warning" if status == RouteStatus.AT_RISK else "Checks pass",
        (EVIDENCE,),
    )


def test_protocol_and_baseline_ties(engine, settings):
    assert isinstance(engine, RecommendationEngine)
    plans = PlanningComparator(t4_replay=True).compare(fixture_request(), environment(), settings)
    result = engine.recommend(plans, INJECTION, ORDER + 165 * H, ())
    assert len(result.winner_plan_ids) > 1
    assert all(
        s.injection_penalty_minutes == 0
        for s in result.scores
        if s.plan_id in result.winner_plan_ids
    )
    assert "no automatic preselection" in result.reason
    assert result == engine.recommend(tuple(reversed(plans)), INJECTION, ORDER + 165 * H, ())


def test_early_late_arithmetic_and_timezone_equivalence(engine, baseline):
    target = ORDER + 165 * H
    early = changed(baseline, "A", injection=target - 30 * MINUTE)
    late = changed(baseline, "B", injection=target + 30 * MINUTE)
    result = engine.recommend((late, early), INJECTION, target, ())
    assert result.winner_plan_ids == ("A",)
    assert [s.injection_penalty_minutes for s in result.scores] == [30, 60]
    assert "30 minutes early" in result.reason
    assert (
        engine.recommend((late, early), INJECTION, target.astimezone(timezone(2 * H)), ()) == result
    )


def test_ingredient_arrival_is_the_delivery_metric(engine, baseline):
    a = changed(baseline, "A", arrival=ORDER + 10 * H, injection=ORDER + 200 * H)
    b = changed(baseline, "B", arrival=ORDER + 11 * H, injection=ORDER + 100 * H)
    result = engine.recommend((b, a), DELIVERY, None, ())
    assert result.winner_plan_ids == ("A",)
    assert result.scores[0].ingredient_arrival == ORDER + 10 * H
    assert "arrival at production" in result.reason


def test_equal_weighted_penalties_remain_tied_even_on_opposite_sides(engine, baseline):
    target = ORDER + 165 * H
    early = changed(baseline, "A", injection=target - 30 * MINUTE)
    late = changed(baseline, "B", injection=target + 15 * MINUTE)
    result = engine.recommend((late, early), INJECTION, target, ())
    assert result.winner_plan_ids == ("A", "B")
    assert [s.injection_penalty_minutes for s in result.scores] == [30, 30]
    assert "example tied winner" in result.reason


def test_risk_margin_precedes_warning_count_and_excludes_preparation(engine, baseline):
    a, b = changed(baseline, "A", margin=6 * H), changed(baseline, "B", margin=5 * H)
    result = engine.recommend((b, a), RISK, None, (summary(a, status=RouteStatus.AT_RISK),))
    assert result.winner_plan_ids == ("A",)
    assert result.scores[0].limiting_margin == 6 * H
    assert result.scores[0].at_risk_routes == 1
    assert "Production completion" in result.reason
    assert "Tie-break" not in result.reason


def test_risk_warning_tie_break_counts_distinct_local_routes(engine, baseline):
    a, b = changed(baseline, "A"), changed(baseline, "B")
    warning = summary(a, status=RouteStatus.AT_RISK)
    summaries = (warning, warning, summary(b), summary(b, RouteId.INGREDIENTS, RouteStatus.AT_RISK))
    result = engine.recommend((a, b), RISK, None, summaries)
    assert result.winner_plan_ids == ("B",)
    assert [s.at_risk_routes for s in result.scores] == [0, 1]
    assert "Tie-break" in result.reason
    tied = engine.recommend((b, a), RISK, None, ())
    assert tied.winner_plan_ids == ("A", "B")


@pytest.mark.parametrize("goal", list(PlanningGoal))
def test_hard_check_status_precedes_scores(engine, baseline, goal):
    failed = replace(baseline, plan_id="failed", status=ResultStatus.INFEASIBLE)
    unknown = replace(baseline, plan_id="unknown", status=ResultStatus.UNCONFIRMED)
    dishonest = replace(
        baseline,
        plan_id="inconsistent",
        checks=(replace(baseline.checks[0], status=CheckStatus.FAIL),),
    )
    result = engine.recommend((failed, unknown, dishonest, baseline), goal, ORDER + 165 * H, ())
    assert result.winner_plan_ids == (baseline.plan_id,)
    empty = engine.recommend((failed, unknown), goal, ORDER + 165 * H, ())
    assert not empty.winner_plan_ids and not empty.scores
    assert "infeasible" in empty.reason and "unconfirmed" in empty.reason


@pytest.mark.parametrize("status", [RouteStatus.UNKNOWN, RouteStatus.BLOCKED])
def test_supplied_route_uncertainty_never_scores_as_safe(engine, baseline, status):
    result = engine.recommend((baseline,), RISK, None, (summary(baseline, status=status),))
    assert result.winner_plan_ids == ()
    assert "blocked or unknown" in result.reason


def test_warning_requires_evidence(engine, baseline):
    warning = replace(summary(baseline, status=RouteStatus.AT_RISK), evidence=())
    assert not engine.recommend((baseline,), RISK, None, (warning,)).scores


def test_missing_target_and_score_inputs_are_explicit(engine, baseline):
    assert "Enter a target" in engine.recommend((baseline,), INJECTION, None, ()).reason
    with pytest.raises(ValueError, match="timezone-aware"):
        engine.recommend((baseline,), INJECTION, ORDER.replace(tzinfo=None), ())
    for goal, name, field in [
        (INJECTION, "Injection", "actual_time"),
        (DELIVERY, "Ingredient arrival", "actual_time"),
        (RISK, "Injection", "margin"),
    ]:
        incomplete = replace(
            baseline,
            checks=tuple(
                replace(c, **{field: None}) if c.constraint == name else c for c in baseline.checks
            ),
        )
        result = engine.recommend((incomplete,), goal, ORDER, ())
        assert not result.scores and "missing required" in result.reason
    assert not engine.recommend((), RISK, None, ()).winner_plan_ids
    with pytest.raises(ValueError, match="unique"):
        engine.recommend((baseline, baseline), RISK, None, ())


def test_low_water_goals_follow_agreed_fixture(engine, settings):
    settings = replace(settings, river_delay=12 * H)
    plans = PlanningComparator(t4_replay=True).compare(fixture_request(), environment(), settings)
    timing = engine.recommend(plans, INJECTION, ORDER + 177 * H, ())
    winners = [p for p in plans if p.plan_id in timing.winner_plan_ids]
    assert any(
        p.ingredient_mode == TransportMode.SHIP and p.collection_shift == 12 * H for p in winners
    )
    assert all(
        s.injection_penalty_minutes == 0
        for s in timing.scores
        if s.plan_id in timing.winner_plan_ids
    )
    delivery = engine.recommend(plans, DELIVERY, None, ())
    assert all(
        p.ingredient_mode == TransportMode.TRUCK
        for p in plans
        if p.plan_id in delivery.winner_plan_ids
    )
    assert delivery.scores[0].ingredient_arrival == ORDER + 54 * H


def test_hot_return_only_recommends_confirmed_car_return(engine, settings):
    plans = PlanningComparator(t4_replay=True).compare(
        fixture_request(), environment(return_heat=True), settings
    )
    result = engine.recommend(plans, RISK, None, ())
    assert result.winner_plan_ids
    assert all(
        p.return_mode == TransportMode.CAR for p in plans if p.plan_id in result.winner_plan_ids
    )


@pytest.mark.parametrize("river_delay", [0, 12])
def test_mixed_transport_survives_outbound_snow_and_combined_disruption(
    engine, settings, river_delay
):
    request = fixture_request()
    request = replace(
        request,
        routes=tuple(
            replace(r, car_availability=Availability.UNAVAILABLE)
            if r.leg == CourierLeg.RETURN
            else r
            for r in request.routes
        ),
    )
    plans = PlanningComparator(t4_replay=True).compare(
        request, environment(outbound_snow=True), replace(settings, river_delay=river_delay * H)
    )
    result = engine.recommend(plans, RISK, None, ())
    assert result.winner_plan_ids
    assert all(
        p.outbound_mode == TransportMode.CAR and p.return_mode == TransportMode.BICYCLE
        for p in plans
        if p.plan_id in result.winner_plan_ids
    )


def test_no_feasible_plan_and_missing_evidence(engine, settings):
    request = fixture_request()
    request = replace(
        request,
        decision_time=ORDER + 136 * H,
        routes=tuple(replace(r, checked_at=ORDER + 136 * H) for r in request.routes),
    )
    plans = PlanningComparator(t4_replay=True).compare(
        request, environment(), replace(settings, river_delay=48 * H)
    )
    result = engine.recommend(plans, RISK, None, ())
    assert not result.scores and "Production completion" in result.reason
    unknown = PlanningComparator(t4_replay=True).compare(
        fixture_request(), environment(missing=True), settings
    )
    result = engine.recommend(unknown, RISK, None, ())
    assert result.winner_plan_ids
    assert all(
        p.outbound_mode == p.return_mode == TransportMode.CAR
        for p in unknown
        if p.plan_id in result.winner_plan_ids
    )
    # Confirmed cars need no bicycle forecast, so the missing-evidence fixture
    # must also remove car availability before asserting no recommendation.
    request = replace(
        fixture_request(),
        routes=tuple(
            replace(r, car_availability=Availability.UNKNOWN) for r in fixture_request().routes
        ),
    )
    unknown = PlanningComparator(t4_replay=True).compare(
        request, environment(missing=True), settings
    )
    assert not engine.recommend(unknown, RISK, None, ()).scores


@pytest.mark.parametrize("weight", [0, -1, True, "2", float("inf")])
def test_invalid_config_weights(tmp_path, weight):
    path = tmp_path / "recommendations.json"
    path.write_text(json.dumps({"injection_early_weight": weight, "injection_late_weight": 2}))
    with pytest.raises(ValueError, match="finite positive"):
        GoalRecommendationEngine(path)


def test_does_not_modify_inputs(engine, baseline):
    summaries = (summary(baseline),)
    before = repr((baseline, summaries))
    engine.recommend((baseline,), RISK, None, summaries)
    assert repr((baseline, summaries)) == before
