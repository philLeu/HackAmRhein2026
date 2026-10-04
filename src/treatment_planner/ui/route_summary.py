"""Present supplied route verdicts without evaluating eligibility or risk."""

from html import escape

import streamlit as st

from treatment_planner.interfaces import RouteId, RouteStatus, RouteSummary, TransportMode
from treatment_planner.ui.formatting import format_timestamp

ROUTES = {
    RouteId.INGREDIENTS: ("Ingredients", "Rotterdam", "PulseShift Basel"),
    RouteId.SAMPLE: ("Sample", "University Hospital Basel", "PulseShift Basel"),
    RouteId.TREATMENT: ("Finished treatment", "PulseShift Basel", "University Hospital Basel"),
}
TRANSPORT_ICONS = {
    TransportMode.SHIP: "🚢",
    TransportMode.TRUCK: "🚚",
    TransportMode.BICYCLE: "🚲",
    TransportMode.CAR: "🚗",
}
STATUS_ICONS = {
    RouteStatus.NORMAL: "✓",
    RouteStatus.AT_RISK: "⚠",
    RouteStatus.BLOCKED: "⛔",
    RouteStatus.UNKNOWN: "?",
}


def render_route_diagram(
    heading: str,
    source: str,
    vehicle: str,
    destination: str,
    theme: dict,
    diagram_id: str,
) -> None:
    """Reuse the adopted three-node route sketch, reading all colours from theme."""
    palette, surface = theme["theme"], theme["surface"]
    accent, background = palette["primaryColor"], palette["secondaryBackgroundColor"]
    marker = escape(f"arrow-{diagram_id}", quote=True)

    def label(center: int, text: str, color: str) -> str:
        lines = {
            "Refrigerated truck": ("Refrigerated", "truck"),
            "Sample + ingredients": ("Sample +", "ingredients"),
            "Treatment ready": ("Treatment", "ready"),
            "PulseShift Basel": ("PulseShift", "Basel"),
            "University Hospital Basel": ("University", "Hospital", "Basel"),
            "University Hospital": ("University", "Hospital"),
        }.get(text, (text,))
        first = 43 if len(lines) == 3 else 50 if len(lines) == 2 else 59
        spans = "".join(
            f'<tspan x="{center}" y="{first + i * 16}">{escape(line)}</tspan>'
            for i, line in enumerate(lines)
        )
        size = theme.get("route", {}).get("label_font_size", 13)
        return f'<text text-anchor="middle" fill="{color}" font-size="{size}">{spans}</text>'

    title = escape(f"{heading}: {source} to {destination} via {vehicle}", quote=True)
    st.markdown(
        f'''<svg viewBox="0 0 440 108" role="img" aria-label="{title}"
        style="width:100%;height:auto;font-family:sans-serif">
        <defs><marker id="{marker}" markerWidth="8" markerHeight="8" refX="7" refY="4"
        orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{accent}" /></marker></defs>
        <rect x="4" y="18" width="116" height="70" rx="10"
        fill="{background}" stroke="{surface["border"]}" />
        <rect x="162" y="18" width="116" height="70" rx="10"
        fill="{background}" stroke="{accent}" />
        <rect x="320" y="18" width="116" height="70" rx="10"
        fill="{background}" stroke="{surface["border"]}" />
        <path d="M124 53 H152 M282 53 H310" stroke="{accent}" stroke-width="3"
        marker-end="url(#{marker})" />
        {label(62, source, surface["muted"])}
        {label(220, vehicle.title(), palette["textColor"])}
        {label(378, destination, surface["muted"])}</svg>''',
        unsafe_allow_html=True,
    )


def render_route_summaries(
    summaries: tuple[RouteSummary, ...],
    plan_id: str,
    theme: dict,
    *,
    key: str = "v2-routes",
) -> None:
    """Always show all three routes; absent summaries stay explicitly unknown."""
    supplied = {item.route: item for item in summaries if item.plan_id == plan_id}
    st.subheader("Routes & conditions")
    with st.container(horizontal=True):
        for route, (name, source, destination) in ROUTES.items():
            with st.container(border=True, width=theme["route"]["card_width"]):
                st.caption(name)
                summary = supplied.get(route)
                if summary is None:
                    st.write(f"{source} → {destination}")
                    st.write("Unknown · Route summary unavailable")
                    st.caption("Delay unknown")
                    continue
                render_route_diagram(
                    name,
                    source,
                    summary.transport.value,
                    destination,
                    theme,
                    f"{key}-{route.name}",
                )
                st.write(f"{TRANSPORT_ICONS[summary.transport]} {summary.transport.value}")
                st.write(
                    f"{STATUS_ICONS[summary.status]} **{summary.status.value.title()}** · "
                    f"{summary.reason}"
                )
                st.caption(f"Evidence: {summary.evidence_mode.value.title()}")
                delay = summary.possible_delay
                st.caption(
                    "Delay unknown"
                    if delay is None
                    else f"Possible delay: {delay.total_seconds() / 3600:g} h"
                )
                if summary.carried_from is not None:
                    st.caption("Demo conditions carried over from the previous trip time")
                with st.expander(f"{name}: evidence & checks", expanded=False):
                    st.write(
                        f"Journey: {format_timestamp(summary.interval.start)} → "
                        f"{format_timestamp(summary.interval.end)}"
                    )
                    if summary.carried_from is not None:
                        st.write(
                            f"Previous trip: {format_timestamp(summary.carried_from.start)} → "
                            f"{format_timestamp(summary.carried_from.end)}"
                        )
                    for evidence in summary.evidence:
                        st.write(f"{evidence.kind.value} · {evidence.source}")
                        st.caption(
                            f"Source {format_timestamp(evidence.source_time)} · "
                            f"Retrieved {format_timestamp(evidence.retrieved_at)}"
                        )
                    for issue in summary.issues:
                        st.warning(issue)
