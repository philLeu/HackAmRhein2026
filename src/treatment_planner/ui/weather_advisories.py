"""Display non-blocking trip-day reminders beside the inspected plan."""

import re
from datetime import date

import streamlit as st

from treatment_planner.interfaces import CandidatePlan, CourierLeg, WeatherReport
from treatment_planner.ui.formatting import format_date
from treatment_planner.weather_advisories import weather_recheck_warnings


def render_weather_recheck_warnings(plan: CandidatePlan, weather: WeatherReport) -> None:
    """Show each courier trip's temperature reminder with its actual journey date."""
    for event_id, leg, label in (
        ("sample", CourierLeg.OUTBOUND, "Sample trip"),
        ("return", CourierLeg.RETURN, "Treatment return"),
    ):
        event = next((event for event in plan.events if event.event_id == event_id), None)
        if event is None:
            continue
        # V1 fixtures use a shared point label; V2 reports use independent leg labels.
        locations = (
            (leg.value,)
            if any(window.location == leg.value for window in weather.windows)
            else tuple(
                dict.fromkeys(
                    window.location
                    for window in weather.windows
                    if window.location not in {route.value for route in CourierLeg}
                )
            )
        )
        for location in locations:
            for warning in weather_recheck_warnings(
                weather, event.interval, location=location, trip_label=label
            ):
                st.warning(
                    re.sub(
                        r"\b\d{4}-\d{2}-\d{2}\b",
                        lambda match: format_date(date.fromisoformat(match.group())),
                        warning,
                    )
                )
