"""Display UTC consistently without changing instants used by the timeline."""

import tomllib
from datetime import UTC, datetime, timedelta, timezone

import pytest

from treatment_planner.demo import (
    FixtureComparator,
    fixture_environment,
    fixture_request,
    fixture_settings,
)
from treatment_planner.ui.formatting import format_timestamp
from treatment_planner.ui.presentation import THEME_PATH
from treatment_planner.ui.timeline import timeline_chart


def test_timestamp_converts_to_utc_and_preserves_unknown():
    instant = datetime(2026, 10, 3, 16, 30, tzinfo=timezone(timedelta(hours=2)))
    assert format_timestamp(instant) == "03.10.2026 · 14:30 UTC"
    assert format_timestamp(None) == "Unknown"
    with pytest.raises(ValueError, match="timezone-aware"):
        format_timestamp(datetime(2026, 10, 3, 14, 30))


def test_timeline_has_human_labels_and_machine_instants():
    plan = FixtureComparator("Baseline").compare(
        fixture_request(), fixture_environment("Baseline"), fixture_settings("Baseline")
    )[0]
    theme = tomllib.loads(THEME_PATH.read_text())["timeline"]
    spec = timeline_chart(plan, theme).to_dict()
    row = spec["data"]["values"][0]
    assert row["Start"] == plan.events[0].interval.start.astimezone(UTC).isoformat()
    assert row["Start display"] == format_timestamp(plan.events[0].interval.start)
