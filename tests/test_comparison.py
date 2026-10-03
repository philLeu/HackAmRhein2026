"""Exercise coordinator interactions that must not retain stale confirmations."""

import tomllib
from dataclasses import replace
from datetime import timedelta

from streamlit.testing.v1 import AppTest

from treatment_planner.demo import (
    FixtureComparator,
    fixture_environment,
    fixture_request,
    fixture_settings,
)
from treatment_planner.interfaces import CheckStatus, ResultStatus
from treatment_planner.ui.comparison import (
    THEME_PATH,
    _key_option_rows,
    _key_options,
    _plain_status,
    comparison_rows,
    timeline_chart,
)

APP = """
from dataclasses import replace
import streamlit as st
from treatment_planner.demo import (
    FixtureComparator, fixture_request, fixture_environment, fixture_settings,
)
from treatment_planner.interfaces import Availability, CheckStatus, ResultStatus, RouteSnow
from treatment_planner.ui.comparison import render_route_inputs, render_comparison
scenario = st.selectbox("Sample set", ["Low water", "All failed", "Unknown"])
request = fixture_request()
environment = fixture_environment("Low water")
plans = FixtureComparator("Low water").compare(request, environment, fixture_settings("Low water"))
if scenario == "All failed":
    plans = plans[:1]
elif scenario == "Unknown":
    plan = plans[1]
    check = replace(plan.checks[-1], status=CheckStatus.UNKNOWN, reason="Return coverage missing")
    plans = (replace(plan, status=ResultStatus.UNCONFIRMED, checks=plan.checks[:-1] + (check,)),)
if st.session_state.get("unknown_routes"):
    request = replace(request, routes=tuple(replace(route, snow=RouteSnow.UNKNOWN, checked_at=None,
        car_availability=Availability.UNKNOWN) for route in request.routes))
edited = render_route_inputs(request)
if st.session_state.get("environment_changed"):
    weather = replace(environment.weather, issues=("Updated input",))
    environment = replace(environment, weather=weather)
if st.session_state.get("plans_changed"):
    plans = tuple(replace(plan, title=plan.title + " revised") for plan in plans)
selected = render_comparison(plans, request=edited, environment=environment,
    compared_request=request, compared_environment=fixture_environment("Low water"))
st.session_state["selected_id"] = selected.plan_id if selected else None
st.session_state["edited_request"] = edited
"""


def sample_plans():
    return FixtureComparator("Low water").compare(
        fixture_request(), fixture_environment("Low water"), fixture_settings("Low water")
    )


def test_failure_selection_disabled_and_confirmed_selection_persists():
    app = AppTest.from_string(APP).run(timeout=20)
    assert not app.exception
    assert app.button[0].disabled
    app.selectbox[-1].select(1).run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["selected_id"] == "postpone"
    app.run()
    assert app.session_state["selected_id"] == "postpone"
    app.selectbox[-1].select(0).run()
    assert app.session_state["selected_id"] == "postpone"
    assert any(h.value == "Selected plan timeline" for h in app.subheader)


def test_route_change_clears_selection_and_blocks_stale_comparison():
    app = AppTest.from_string(APP).run(timeout=20)
    app.selectbox[-1].select(1).run()
    app.button[0].click().run()
    app.selectbox[1].select("snow present").run()
    assert not app.exception
    assert app.session_state["selected_id"] is None
    assert app.button[0].disabled
    assert any("Inputs changed" in warning.value for warning in app.warning)
    edited = app.session_state["edited_request"]
    app.run()
    assert app.session_state["edited_request"] == edited  # entry timestamp does not churn


def test_environment_or_result_change_invalidates_selection():
    for change in ("environment_changed", "plans_changed"):
        app = AppTest.from_string(APP).run(timeout=20)
        app.selectbox[-1].select(1).run()
        app.button[0].click().run()
        app.session_state[change] = True
        app.run()
        assert not app.exception
        assert app.session_state["selected_id"] is None


def test_failure_and_missing_evidence_have_distinct_messages():
    app = AppTest.from_string(APP).run(timeout=20)
    app.selectbox[0].select("All failed").run()
    assert any("No feasible plan" in message.value for message in app.error)
    app.selectbox[0].select("Unknown").run()
    assert not app.exception
    assert app.button[0].disabled
    assert any("No confirmed plan yet" in message.value for message in app.warning)
    assert any("Return coverage missing" in message.value for message in app.warning)
    assert app.dataframe[1].value["Tightest margin (h)"].isna().all()


def test_unknown_manual_inputs_remain_unknown():
    app = AppTest.from_string(APP).run(timeout=20)
    app.session_state["unknown_routes"] = True
    app.run()
    assert not app.exception
    assert [box.value for box in app.selectbox[1:5]] == ["unknown"] * 4
    assert all(not checkbox.value for checkbox in app.checkbox)


def test_negative_and_zero_margins_and_supplied_deadline_markers():
    keep, postpone, _ = sample_plans()
    assert comparison_rows((keep,))[0]["Tightest margin (h)"] == -5
    zero = replace(
        postpone.checks[2], margin=timedelta(0), deadline=postpone.events[2].interval.end
    )
    boundary = replace(postpone, checks=postpone.checks[:2] + (zero,) + postpone.checks[3:])
    row = comparison_rows((boundary,))[0]
    assert row["Tightest margin (h)"] == 0
    assert row["Binding deadline"] == "Production completion"
    theme = tomllib.loads(THEME_PATH.read_text())["timeline"]
    chart = timeline_chart(boundary, theme).to_dict()
    assert chart["layer"][1]["mark"]["type"] == "rule"
    detail = timeline_chart(postpone, theme, detail=True).to_dict()
    event_rows = detail["data"]["values"]
    assert all(event["Lane"] != "Ingredients" for event in event_rows)


def test_key_options_explain_late_plan_and_recovery_in_plain_language():
    plans = FixtureComparator("Low water").compare(
        fixture_request(), fixture_environment("Low water"), fixture_settings("Low water")
    )
    rows = _key_option_rows(plans)
    assert len(rows) <= 4
    assert rows[0]["Deadline result"] == "5 h late"
    assert rows[0]["Tightest deadline"] == "Production finishes"
    assert rows[1]["Change from current"] == "Collect sample 12 h later"
    assert rows[1]["Deadline result"] == "On time — 6 h buffer"


def test_key_options_keep_a_confirmed_plan_visible_when_heuristic_options_fail():
    plans = sample_plans()
    confirmed = plans[-1]
    failed_plans = tuple(
        replace(
            plan,
            status=ResultStatus.INFEASIBLE,
            checks=(replace(plan.checks[0], status=CheckStatus.FAIL),) + plan.checks[1:],
        )
        for plan in plans[:-1]
    )

    options = _key_options(failed_plans + (confirmed,))

    assert len(options) <= 4
    assert any(plan.plan_id == confirmed.plan_id for plan in options)
    assert any(plan.status == ResultStatus.CONFIRMED for plan in options)


def test_non_deadline_weather_failure_is_not_reported_as_a_missed_deadline():
    plan = sample_plans()[0]
    weather_failure = replace(
        plan.checks[0],
        constraint="Return weather",
        status=CheckStatus.FAIL,
        margin=None,
        deadline=None,
        reason="Return bicycle blocked by the forecast.",
    )
    infeasible = replace(
        plan,
        status=ResultStatus.INFEASIBLE,
        checks=(weather_failure,)
        + tuple(replace(check, status=CheckStatus.PASS) for check in plan.checks[1:]),
    )

    status = _plain_status(infeasible)

    assert "weather" in status.lower()
    assert "late" not in status.lower()
    assert "deadline" not in status.lower()


def test_collection_timing_failure_uses_a_neutral_rule_message():
    plan = sample_plans()[0]
    collection_failure = replace(
        plan.checks[0],
        constraint="Collection timing",
        status=CheckStatus.FAIL,
        margin=None,
        deadline=None,
        reason="Collection cannot advance or precede the planning decision.",
    )
    infeasible = replace(
        plan,
        status=ResultStatus.INFEASIBLE,
        checks=(collection_failure,)
        + tuple(replace(check, status=CheckStatus.PASS) for check in plan.checks[1:]),
    )

    status = _plain_status(infeasible)

    assert status == "A planning rule blocks this option"
