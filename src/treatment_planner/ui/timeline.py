"""Render supplied intervals and deadlines using the shared theme."""

from datetime import UTC

import altair as alt

from treatment_planner.interfaces import CandidatePlan
from treatment_planner.ui.formatting import TIMESTAMP_FORMAT, format_timestamp


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
            "Start display": format_timestamp(event.interval.start),
            "End display": format_timestamp(event.interval.end),
            "Description": (
                f"{event.label}: {format_timestamp(event.interval.start)} "
                f"to {format_timestamp(event.interval.end)}"
            ),
            "Source": event.provenance.source,
            "Evidence": event.provenance.kind.value,
        }
        for event in events
    ]
    bars = (
        alt.Chart(alt.Data(values=rows))
        .mark_bar(color=theme["event_color"], cornerRadius=theme["event_radius"])
        .encode(
            x=alt.X(
                "Start:T",
                title=None,
                scale=alt.Scale(type="utc"),
                axis=alt.Axis(
                    format=TIMESTAMP_FORMAT,
                    tickCount=theme["axis_tick_count"],
                    labelOverlap=True,
                    labelLimit=0,
                    labelAngle=theme["axis_label_angle"],
                ),
            ),
            x2="End:T",
            y=alt.Y("Lane:N", sort=None, title=None),
            description="Description:N",
            tooltip=[
                "Event:N",
                alt.Tooltip("Start display:N", title="Start"),
                alt.Tooltip("End display:N", title="End"),
                "Evidence:N",
                "Source:N",
            ],
        )
    )
    deadlines = [
        {
            "Deadline": check.constraint,
            "Time": check.deadline.astimezone(UTC).isoformat(),
            "Time display": format_timestamp(check.deadline),
        }
        for check in plan.checks
        if check.deadline is not None
        and (not detail or not check.constraint.startswith("Ingredient"))
    ]
    chart = bars
    if deadlines:
        markers = (
            alt.Chart(alt.Data(values=deadlines))
            .mark_rule(color=theme["deadline_color"], strokeDash=theme["deadline_dash"])
            .encode(
                x=alt.X("Time:T", scale=alt.Scale(type="utc")),
                tooltip=["Deadline:N", alt.Tooltip("Time display:N", title="Time")],
            )
        )
        chart = bars + markers
    return chart.properties(height=theme["height_per_lane"] * max(1, len({e.lane for e in events})))
