"""Render supplied intervals and deadlines using the shared theme."""

from datetime import UTC

import altair as alt

from treatment_planner.interfaces import CandidatePlan


def timeline_chart(
    plan: CandidatePlan, theme: dict, *, detail: bool = False
) -> alt.Chart | alt.LayerChart:
    """Use supplied event intervals and deadline timestamps on a common UTC axis."""
    events = tuple(event for event in plan.events if not detail or event.lane != "Ingredients")
    rows = [
        {
            "Lane": event.lane,
            "Event": event.label,
            "Start": event.interval.start.astimezone(UTC).isoformat(),
            "End": event.interval.end.astimezone(UTC).isoformat(),
            "Source": event.provenance.source,
            "Evidence": event.provenance.kind.value,
        }
        for event in events
    ]
    bars = (
        alt.Chart(alt.Data(values=rows))
        .mark_bar(color=theme["event_color"])
        .encode(
            x=alt.X("Start:T", title="UTC", scale=alt.Scale(type="utc")),
            x2="End:T",
            y=alt.Y("Lane:N", sort=None, title=None),
            tooltip=["Event:N", "Start:N", "End:N", "Evidence:N", "Source:N"],
        )
    )
    deadlines = [
        {"Deadline": check.constraint, "Time": check.deadline.astimezone(UTC).isoformat()}
        for check in plan.checks
        if check.deadline is not None
        and (not detail or not check.constraint.startswith("Ingredient"))
    ]
    chart = bars
    if deadlines:
        markers = (
            alt.Chart(alt.Data(values=deadlines))
            .mark_rule(color=theme["deadline_color"])
            .encode(
                x=alt.X("Time:T", scale=alt.Scale(type="utc")), tooltip=["Deadline:N", "Time:N"]
            )
        )
        chart = bars + markers
    return chart.properties(height=theme["height_per_lane"] * max(1, len({e.lane for e in events})))
