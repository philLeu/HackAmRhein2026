"""Temperature reminders appear at 28°C without changing transport eligibility."""

from dataclasses import replace
from datetime import timedelta

import pytest
from streamlit.testing.v1 import AppTest

from treatment_planner.demo import EVIDENCE, ORDER
from treatment_planner.interfaces import (
    CourierLeg,
    EvidenceKind,
    TimeWindow,
    WeatherReport,
    WeatherWindow,
)
from treatment_planner.weather_advisories import weather_recheck_warnings

SAMPLE = TimeWindow(ORDER + timedelta(hours=1), ORDER + timedelta(hours=2))
RETURN = TimeWindow(ORDER + timedelta(days=3), ORDER + timedelta(days=3, hours=1))


def warnings(temperature, *, hourly_mean=False):
    window = WeatherWindow(
        CourierLeg.RETURN.value,
        RETURN,
        None if hourly_mean else temperature,
        False,
        replace(EVIDENCE, kind=EvidenceKind.FORECAST),
        temperature if hourly_mean else None,
    )
    return weather_recheck_warnings(
        WeatherReport((window,)),
        RETURN,
        location=CourierLeg.RETURN.value,
        trip_label="Treatment return",
    )


@pytest.mark.parametrize("temperature, expected", [(27.9, False), (28, True), (30, True)])
def test_warning_threshold_includes_exactly_28(temperature, expected):
    messages = warnings(temperature)
    assert bool(messages) == expected
    if messages:
        assert "Treatment return" in messages[0]
        assert "warning threshold: 28 °C" in messages[0]
        assert "2026-11-04 UTC" in messages[0]
        assert "recheck whether the plan is still feasible before departure" in messages[0]


def test_hourly_mean_warning_does_not_claim_to_be_a_maximum():
    messages = warnings(28, hourly_mean=True)
    assert "forecast hourly mean temperature reaches 28 °C" in messages[0]
    assert "maximum" not in messages[0]


@pytest.mark.parametrize("temperature", [None, float("nan"), float("inf")])
def test_unknown_or_invalid_temperature_does_not_create_a_known_heat_warning(temperature):
    assert not warnings(temperature)


def test_warnings_are_scoped_to_the_actual_leg_and_journey():
    report = WeatherReport(
        (
            WeatherWindow(CourierLeg.OUTBOUND.value, SAMPLE, 29, False, EVIDENCE),
            WeatherWindow(CourierLeg.RETURN.value, RETURN, 20, False, EVIDENCE),
            WeatherWindow(CourierLeg.RETURN.value, SAMPLE, 40, False, EVIDENCE),
        )
    )
    assert not weather_recheck_warnings(
        report, RETURN, location=CourierLeg.RETURN.value, trip_label="Treatment return"
    )
    messages = weather_recheck_warnings(
        report, SAMPLE, location=CourierLeg.OUTBOUND.value, trip_label="Sample trip"
    )
    assert "simulated maximum temperature reaches 29 °C" in messages[0]


def test_reminder_is_visible_and_28_degree_plan_can_still_be_confirmed():
    app = AppTest.from_string("""
from dataclasses import replace
import streamlit as st
from treatment_planner.demo import fixture_request, fixture_environment, fixture_settings
from treatment_planner.planning import PlanningComparator
from treatment_planner.ui.comparison import render_comparison
request = fixture_request()
environment = fixture_environment('Baseline')
weather = replace(environment.weather, windows=tuple(
    replace(w, maximum_temperature_c=28) for w in environment.weather.windows))
environment = replace(environment, weather=weather)
plans = PlanningComparator(t4_replay=True).compare(request, environment, fixture_settings())
selected = render_comparison(plans, request=request, environment=environment,
    compared_request=request, compared_environment=environment)
st.session_state['selected_id'] = selected.plan_id if selected else None
""").run(timeout=20)
    assert not app.exception
    assert any(
        "Sample trip: simulated maximum temperature reaches 28 °C" in w.value for w in app.warning
    )
    assert any(
        "Treatment return: simulated maximum temperature reaches 28 °C" in w.value
        for w in app.warning
    )
    assert not app.button[0].disabled
    app.button[0].click().run()
    assert app.session_state["selected_id"]
