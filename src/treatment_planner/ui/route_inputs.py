"""Collect independent manual route inputs; scheduling remains in the engine."""

from dataclasses import replace
from datetime import UTC, datetime

import streamlit as st

from treatment_planner.interfaces import (
    Availability,
    EvidenceKind,
    LocalRouteInput,
    Provenance,
    RouteSnow,
    TreatmentRequest,
)
from treatment_planner.ui.formatting import DATE_INPUT_FORMAT


def _route_fields(route: LocalRouteInput, decision_time: datetime, key: str) -> LocalRouteInput:
    st.write(f"**{route.leg.value.capitalize()}**")
    snow = st.selectbox(
        "Route snow", list(RouteSnow), index=list(RouteSnow).index(route.snow), key=f"{key}-snow"
    )
    car = st.selectbox(
        "Car availability",
        list(Availability),
        index=list(Availability).index(route.car_availability),
        key=f"{key}-car",
    )
    timestamp_known = st.checkbox(
        "Route check timestamp known", value=route.checked_at is not None, key=f"{key}-known"
    )
    initial = (route.checked_at or decision_time).astimezone(UTC)
    date = st.date_input(
        "Checked on (UTC)", value=initial.date(), format=DATE_INPUT_FORMAT, key=f"{key}-date"
    )
    time = st.time_input("Checked at (UTC)", value=initial.time(), format="24h", key=f"{key}-time")
    checked_at = datetime.combine(date, time, tzinfo=UTC) if timestamp_known else None
    if (snow, car, checked_at) == (route.snow, route.car_availability, route.checked_at):
        return route
    cached = st.session_state.get(f"{key}-manual")
    if cached and (cached.snow, cached.car_availability, cached.checked_at) == (
        snow,
        car,
        checked_at,
    ):
        return cached
    now = datetime.now(UTC)
    edited = replace(
        route,
        snow=snow,
        car_availability=car,
        checked_at=checked_at,
        provenance=Provenance("Coordinator-entered route status", EvidenceKind.MANUAL, now, now),
    )
    st.session_state[f"{key}-manual"] = edited
    return edited


def render_route_inputs(request: TreatmentRequest, *, key: str = "routes") -> TreatmentRequest:
    """Return edited shared inputs; the caller must recompute affected plans.

    Unknown values stay unknown. Explicit replay values retain their provenance
    until edited. Freshness and future-dispatch requirements belong to T5.
    """
    st.subheader("Local route inputs")
    st.caption(
        "The hospital-to-factory route carries the sample. "
        "The factory-to-hospital route carries the finished treatment."
    )
    signature = (request.treatment_id, request.routes)
    if st.session_state.get(f"{key}-source") != signature:
        for route in request.routes:
            for field in ("snow", "car", "known", "date", "time", "manual"):
                st.session_state.pop(f"{key}-{route.leg.name}-{field}", None)
        st.session_state[f"{key}-source"] = signature
    columns = st.columns(len(request.routes))
    routes = []
    for column, route in zip(columns, request.routes, strict=True):
        with column:
            edited = _route_fields(route, request.decision_time, f"{key}-{route.leg.name}")
            routes.append(edited)
            st.caption(f"Input source: {edited.provenance.kind.value} · {edited.provenance.source}")
    st.caption(
        "A forecast does not establish existing route snow. Freshness and renewed "
        "dispatch checks are evaluated by the planning engine. Unknown availability stays unknown."
    )
    return replace(request, routes=tuple(routes))
