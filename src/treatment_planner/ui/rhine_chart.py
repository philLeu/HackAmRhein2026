"""History and ensemble forecast with notebook restriction zones."""

from datetime import UTC, datetime

import altair as alt

from treatment_planner.interfaces import RiverForecastReport, RiverReport
from treatment_planner.rhine_conditions import RULES, assess_conditions
from treatment_planner.ui.formatting import TIMESTAMP_FORMAT, format_timestamp


def _zones(low, high):
    offset = RULES["draft_offset_cm"]
    edges = [r["limit"] for r in RULES["high_thresholds"]]
    edges += [r["limit"] + offset for r in RULES["low_thresholds"]]
    near_edges = [r["limit"] - RULES["margin_cm"] for r in RULES["high_thresholds"]]
    near_edges += [r["limit"] + offset + RULES["margin_cm"] for r in RULES["low_thresholds"]]
    cuts = sorted({low, high, *[e for e in edges + near_edges if low < e < high]})
    rows = []
    for bottom, top in zip(cuts, cuts[1:]):
        a = assess_conditions((bottom + top) / 2)
        crossed = next((f for f in a.findings if f.state == "breached"), None)
        near = next((f for f in a.findings if f.state == "margin"), None)
        label = (
            f"{a.status.value.upper()}: {crossed.consequence}"
            if crossed
            else a.status.value.upper()
        )
        if near:
            label += f"; within {RULES['margin_cm']} cm of next limit"
        rows.append(
            {
                "Bottom": bottom,
                "Top": top,
                "Middle": (bottom + top) / 2,
                "Status": a.status.value,
                "Label": label,
                "Near": near is not None,
            }
        )
    return rows, edges


def _backdrop(zones, edges, y, palette, style, *, full_scale=False):
    color = alt.Color(
        "Status:N", scale=alt.Scale(domain=list(palette), range=list(palette.values())), legend=None
    )
    bands = (
        alt.Chart(alt.Data(values=zones))
        .mark_rect(opacity=style["zone_opacity"])
        .encode(y=y, y2="Top:Q", color=color, tooltip=["Status:N", "Label:N"])
    )
    limits = (
        alt.Chart(alt.Data(values=[{"Bottom": e} for e in edges]))
        .mark_rule(color=style["grid"], opacity=0.7)
        .encode(y=y)
    )
    if full_scale:
        return bands + limits
    labels = (
        alt.Chart(alt.Data(values=zones))
        .mark_text(align="left", baseline="middle", dx=8, color=style["ink"], fontSize=10)
        .encode(x=alt.value(0), y=alt.Y("Middle:Q", scale=y["scale"]), text="Status:N")
    )
    return bands + limits + labels


def rhine_chart(
    history: RiverReport, forecast: RiverForecastReport, now, selected, theme: dict
) -> tuple[alt.LayerChart, alt.LayerChart]:
    """Render solid history, dashed median, bands, near-limit texture and full scale."""
    style = theme["rhine"]
    palette = {s: style[s] for s in ("normal", "watch", "warning", "critical", "unknown")}
    observations = [
        {
            "Time": r.observed_at.astimezone(UTC).isoformat(),
            "Height": round(r.water_level_m * 100, 6),
            "Time display": format_timestamp(r.observed_at),
        }
        for r in history.observations
        if r.water_level_m is not None and r.observed_at <= now
    ]
    future = [
        {
            "Time": p.timestamp.astimezone(UTC).isoformat(),
            "Time display": format_timestamp(p.timestamp),
            "Height": p.median_cm,
            "Min": p.minimum_cm,
            "P25": p.p25_cm,
            "P75": p.p75_cm,
            "Max": p.maximum_cm,
        }
        for p in forecast.points
    ]
    values = [r["Height"] for r in observations] + [r["Height"] for r in future]
    values += [r[k] for r in future for k in ("Min", "Max") if r[k] is not None]
    if not values:
        raise ValueError("No chartable Rhine evidence")
    low, high = min(values) - 10, max(values) + 10
    edges = [r["limit"] for r in RULES["high_thresholds"]]
    edges += [r["limit"] + RULES["draft_offset_cm"] for r in RULES["low_thresholds"]]
    for e in edges:
        if 0 <= min(values) - e < 60:
            low = min(low, e - 8)
        if 0 <= e - max(values) < 60:
            high = max(high, e + 8)
    zones, edges = _zones(low, high)
    y = alt.Y(
        "Bottom:Q", title="Gauge height [cm]", scale=alt.Scale(domain=[low, high], nice=False)
    )
    base = _backdrop(zones, [e for e in edges if low < e < high], y, palette, style)
    x = alt.X(
        "Time:T",
        title="Time (UTC)",
        scale=alt.Scale(type="utc"),
        axis=alt.Axis(format=TIMESTAMP_FORMAT, labelAngle=-20, tickCount=5, labelOverlap=True),
    )
    gauge = alt.Y("Height:Q", title="Gauge height [cm]", scale=y["scale"])
    measured = (
        alt.Chart(alt.Data(values=observations))
        .mark_line(color=style["series"], strokeWidth=2)
        .encode(x=x, y=gauge, tooltip=[alt.Tooltip("Time display:N", title="Time"), "Height:Q"])
    )
    data = alt.Chart(alt.Data(values=future))
    median = data.mark_line(
        color=style["series"], strokeDash=style["forecast_dash"], strokeWidth=2
    ).encode(
        x=x,
        y=gauge,
        tooltip=[
            alt.Tooltip("Time display:N", title="Time"),
            "Height:Q",
            "Min:Q",
            "P25:Q",
            "P75:Q",
            "Max:Q",
        ],
    )
    outer = data.mark_area(color=style["series"], opacity=style["outer_opacity"]).encode(
        x=x, y=alt.Y("Min:Q", scale=y["scale"]), y2="Max:Q"
    )
    inner = data.mark_area(color=style["series"], opacity=style["inner_opacity"]).encode(
        x=x, y=alt.Y("P25:Q", scale=y["scale"]), y2="P75:Q"
    )
    markers = []
    if observations:
        latest = max(observations, key=lambda r: r["Time"])
        markers.append(
            {**latest, "Label": "NOW", "Status": assess_conditions(latest["Height"]).status.value}
        )
    point = next((p for p in forecast.points if p.timestamp == selected), None)
    if point:
        markers.append(
            {
                "Time": point.timestamp.isoformat(),
                "Time display": format_timestamp(point.timestamp),
                "Height": point.median_cm,
                "Label": "SELECTED",
                "Status": assess_conditions(point.median_cm).status.value,
            }
        )
    marks = (
        alt.Chart(alt.Data(values=markers))
        .mark_point(filled=True, size=120)
        .encode(
            x=x,
            y=gauge,
            color=alt.Color(
                "Status:N",
                scale=alt.Scale(domain=list(palette), range=list(palette.values())),
                legend=None,
            ),
            shape=alt.Shape(
                "Status:N",
                scale=alt.Scale(
                    domain=list(palette),
                    range=["circle", "diamond", "triangle-up", "square", "cross"],
                ),
                legend=None,
            ),
            tooltip=[
                "Label:N",
                "Status:N",
                alt.Tooltip("Time display:N", title="Time"),
                "Height:Q",
            ],
        )
    )
    now_line = (
        alt.Chart(alt.Data(values=[{"Time": now.isoformat()}]))
        .mark_rule(color=style["ink"], strokeDash=[3, 3])
        .encode(x=x)
    )
    # Diagonal strokes are a second visual channel for proximity, independent of class.
    hatches = []
    timestamps = [datetime.fromisoformat(r["Time"]) for r in observations + future]
    start, end = min(timestamps), max(timestamps)
    step = (end - start) / 40
    for zone in zones:
        if zone["Near"]:
            for position in range(40):
                hatches.append(
                    {
                        "Time": (start + position * step).isoformat(),
                        "End": (start + (position + 0.7) * step).isoformat(),
                        "Bottom": zone["Bottom"],
                        "Top": zone["Top"],
                    }
                )
    texture = (
        alt.Chart(alt.Data(values=hatches))
        .mark_rule(color=style["ink"], opacity=0.35, clip=True)
        .encode(x=x, x2="End:T", y=y, y2="Top:Q")
    )
    main = (base + texture + outer + inner + measured + median + now_line + marks).properties(
        height=style["height"], title="Basel Rheinhalle: history and forecast"
    )
    s_low, s_high = min(low, 455), max(high, max(edges) + 25)
    scale_zones, _ = _zones(s_low, s_high)
    scale_y = alt.Y(
        "Bottom:Q",
        scale=alt.Scale(domain=[s_low, s_high], nice=False),
        title=None,
        axis=alt.Axis(orient="right"),
    )
    scale = _backdrop(scale_zones, edges, scale_y, palette, style, full_scale=True)
    rules = []
    for r in RULES["high_thresholds"]:
        rules.append({"Bottom": r["limit"], "Text": r["label"]})
    for r in RULES["low_thresholds"]:
        rules.append({"Bottom": r["limit"] + RULES["draft_offset_cm"], "Text": r["label"]})
    labels = (
        alt.Chart(alt.Data(values=rules))
        .mark_text(align="left", dy=-8, dx=4, fontSize=9, color=style["ink"])
        .encode(x=alt.value(0), y=scale_y, text="Text:N")
    )
    viewport = (
        alt.Chart(alt.Data(values=[{"Bottom": low, "Top": high}]))
        .mark_rect(fillOpacity=0, stroke=style["ink"], strokeDash=[3, 3])
        .encode(y=scale_y, y2="Top:Q")
    )
    reference = (scale + labels + viewport).properties(
        width=125, height=style["height"], title="All restriction zones"
    )

    def styled(chart):
        return chart.configure(
            background=theme["theme"]["secondaryBackgroundColor"],
            axis=alt.AxisConfig(
                labelColor=style["ink"], titleColor=style["ink"], gridColor=style["grid"]
            ),
            title=alt.TitleConfig(color=style["ink"]),
        ).configure_view(stroke=None)

    return styled(main), styled(reference)
