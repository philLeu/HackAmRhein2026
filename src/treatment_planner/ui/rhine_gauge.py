"""Horizontal Basel gauge scale with notebook threshold explanations."""

from datetime import datetime
from math import ceil, floor

import altair as alt

from treatment_planner.rhine_conditions import RULES, assess_conditions
from treatment_planner.ui.formatting import format_timestamp


def _zone_label(assessment) -> str:
    """Return a compact label for the zone at a level."""
    if not assessment.findings:
        return "Full navigation"
    finding = assessment.findings[0]
    if finding.state == "margin":
        return "Near limit"
    meaning = finding.consequence.lower()
    if "less than 50%" in meaning:
        return "Under 50% load"
    if "max load not possible" in meaning:
        return "Reduced load"
    if "boat length limited to" in meaning:
        length = meaning.partition("to ")[2].partition(" for")[0]
        return f"Max {length}"
    if "limited navigation" in meaning:
        return "Limited navigation"
    if "no navigation" in meaning:
        return "No navigation"
    return finding.consequence


def _zone_rows(minimum: int, maximum: int) -> list[dict]:
    margin = RULES["margin_cm"]
    thresholds = [rule["limit"] + RULES["draft_offset_cm"] for rule in RULES["low_thresholds"]] + [
        rule["limit"] for rule in RULES["high_thresholds"]
    ]
    boundaries = {minimum, maximum}
    for threshold in thresholds:
        boundaries.update(
            edge
            for edge in (threshold - margin, threshold, threshold + margin)
            if minimum < edge < maximum
        )
    cuts = sorted(boundaries)
    zones = []
    for start, end in zip(cuts, cuts[1:]):
        middle = (start + end) / 2
        assessment = assess_conditions(middle)
        finding = assessment.findings[0] if assessment.findings else None
        if finding and finding.state == "margin":
            meaning = (
                f"Within {margin} cm of the {finding.limit_cm:g} cm threshold. "
                f"If crossed: {finding.consequence}."
            )
        elif finding:
            meaning = finding.consequence.capitalize() + "."
        else:
            meaning = "No configured navigation limit is crossed at this water level."
        zones.append(
            {
                "Start": start,
                "End": end,
                "Middle": middle,
                "Band": "Basel gauge",
                "Short label": _zone_label(assessment),
                "Status": assessment.status.value,
                "Meaning": meaning,
                "Range": f"{start:g}–{end:g} cm",
            }
        )
    return zones


def rhine_gauge_chart(
    level_cm: float | None, observed_at: datetime | None, theme: dict
) -> alt.LayerChart:
    """Show current gauge height against proportional, hoverable notebook zones."""
    style = theme["rhine"]
    minimum = min(450, floor(level_cm / 50) * 50) if level_cm is not None else 450
    maximum = max(820, ceil(level_cm / 50) * 50) if level_cm is not None else 820
    zones = _zone_rows(minimum, maximum)
    ticks = list(range(minimum, maximum + 1, 50))
    scale = alt.Scale(domain=[minimum, maximum], nice=False)
    level_axis = alt.Axis(title="Basel water level [cm]", values=ticks, grid=False)
    level_x = alt.X("Start:Q", scale=scale, axis=level_axis)
    band_y = alt.Y("Band:N", axis=None, scale=alt.Scale(domain=["Basel gauge"]))
    colors = {
        status: style[f"gauge_{status}"]
        for status in ("normal", "watch", "warning", "critical", "unknown")
    }
    color = alt.Color(
        "Status:N",
        scale=alt.Scale(domain=list(colors), range=list(colors.values())),
        legend=None,
    )
    data = alt.Chart(alt.Data(values=zones))
    regions = data.mark_bar(
        size=style["gauge_bar_size"],
        opacity=style["gauge_opacity"],
        stroke=style["grid"],
        strokeWidth=0.5,
        cursor="help",
    ).encode(
        x=level_x,
        x2="End:Q",
        y=band_y,
        color=color,
        tooltip=[
            alt.Tooltip("Range:N", title="Gauge range"),
            alt.Tooltip("Short label:N", title="Zone"),
            alt.Tooltip("Status:N", title="Notebook status"),
            alt.Tooltip("Meaning:N", title="Meaning"),
        ],
    )
    label_data = [zone for zone in zones if zone["End"] - zone["Start"] >= 12]
    labels = (
        alt.Chart(alt.Data(values=label_data))
        .mark_text(
            fontSize=style["gauge_label_size"],
            fontWeight="bold",
            color=style["gauge_label_color"],
            limit=95,
            ellipsis="…",
        )
        .encode(
            x=alt.X("Middle:Q", scale=scale, axis=None),
            y=band_y,
            text="Short label:N",
        )
    )
    layers = [regions, labels]
    if level_cm is not None:
        assessment = assess_conditions(level_cm)
        meaning = (
            "; ".join(finding.message for finding in assessment.findings)
            if assessment.findings
            else "No threshold crossed or within the 5 cm margin."
        )
        marker = {
            "Level": level_cm,
            "Status": assessment.status.value,
            "Observed": format_timestamp(observed_at) if observed_at else "Unknown",
            "Meaning": meaning,
        }
        marker_data = alt.Chart(alt.Data(values=[marker]))
        layers.append(
            marker_data.mark_rule(color=style["gauge_marker_halo"], strokeWidth=7).encode(
                x=alt.X("Level:Q", scale=scale)
            )
        )
        layers.append(
            marker_data.mark_rule(color=style["gauge_marker_color"], strokeWidth=3).encode(
                x=alt.X("Level:Q", scale=scale),
                tooltip=[
                    alt.Tooltip("Level:Q", title="Current level", format=".1f"),
                    alt.Tooltip("Status:N", title="Current status"),
                    alt.Tooltip("Observed:N", title="Observed"),
                    alt.Tooltip("Meaning:N", title="Assessment"),
                ],
            )
        )
    return (
        alt.layer(*layers)
        .properties(height=style["gauge_height"], title="Basel Rhine · navigation zones")
        .configure(
            background=theme["theme"]["secondaryBackgroundColor"],
            axis=alt.AxisConfig(labelColor=style["ink"], titleColor=style["ink"]),
            title=alt.TitleConfig(color=style["ink"]),
        )
        .configure_view(stroke=None)
    )
