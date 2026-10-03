"""Independent typed demo edits; adapters and integration apply their effects."""

from dataclasses import replace
from datetime import UTC, datetime

import streamlit as st

from treatment_planner.interfaces import (
    Availability,
    DemoOverrides,
    EvidenceKind,
    EvidenceMode,
    IngredientRouteOverride,
    Provenance,
    RouteId,
    RouteSnow,
    TimeWindow,
)
from treatment_planner.ui.formatting import DATE_INPUT_FORMAT, format_timestamp

ROUTE_FIELDS = {
    RouteId.INGREDIENTS: ("ingredients", "🚢 Rotterdam → Basel"),
    RouteId.SAMPLE: ("sample", "🚲 Hospital → Production"),
    RouteId.TREATMENT: ("treatment", "🚲 Production → Hospital"),
}


def _window_fields(interval: TimeWindow, prefix: str) -> TimeWindow | None:
    values = []
    for label, value in (("From", interval.start), ("Until", interval.end)):
        instant = value.astimezone(UTC)
        date = st.date_input(
            f"{label} date (UTC)",
            value=instant.date(),
            format=DATE_INPUT_FORMAT,
            key=f"{prefix}-{label}-date",
        )
        time = st.time_input(
            f"{label} time (UTC)",
            value=instant.time(),
            format="24h",
            key=f"{prefix}-{label}-time",
        )
        values.append(datetime.combine(date, time, tzinfo=UTC))
    if values[1] <= values[0]:
        return None
    return TimeWindow(*values)


def render_demo_controls(
    mode: EvidenceMode,
    overrides: DemoOverrides,
    baseline: DemoOverrides,
    *,
    clock: datetime,
    station_label: str,
    key: str = "v2-demo",
) -> tuple[DemoOverrides, bool]:
    """Return updated overrides and a full-reset request, without recomputing.

    Baseline contains all three route templates with explicit journey intervals.
    The caller handles reset of goal, target, clock and confirmation. Live mode
    returns empty overrides. Opening/cancelling panels does not change values.
    """
    state = st.session_state
    signature = (mode, overrides, baseline)
    if state.get(f"{key}-source") != signature:
        for name in list(state):
            if name.startswith(f"{key}-fields-"):
                state.pop(name)
        state[f"{key}-source"] = signature
    if mode == EvidenceMode.LIVE:
        state.pop(f"{key}-active", None)
        return DemoOverrides(), False
    st.caption(f"Simulated conditions · Fixed demo clock: {format_timestamp(clock)}")
    with st.container(horizontal=True):
        for route, (_, label) in ROUTE_FIELDS.items():
            if st.button(label, key=f"{key}-{route.name}"):
                state[f"{key}-active"] = route
        reset = st.button("Reset demo", key=f"{key}-reset")
    if reset:
        state.pop(f"{key}-active", None)
        for name in list(state):
            if name.startswith(f"{key}-fields-"):
                state.pop(name)
        return DemoOverrides(), True
    active = state.get(f"{key}-active")
    if active not in ROUTE_FIELDS:
        return overrides, False
    field, label = ROUTE_FIELDS[active]
    existing = getattr(overrides, field) or getattr(baseline, field)
    if existing is None:
        st.warning("This route needs a baseline journey interval before it can be edited.")
        return overrides, False
    prefix = f"{key}-fields-{active.name}"
    with st.expander(f"Demo controls: {label}", expanded=True), st.form(f"{prefix}-form"):
        st.caption("Simulated inputs apply only to this route. Live evidence is unchanged.")
        if isinstance(existing, IngredientRouteOverride):
            known = st.checkbox(
                "Gauge height known",
                value=existing.gauge_height_cm is not None,
                key=f"{prefix}-known",
            )
            gauge = st.number_input(
                f"{station_label}: gauge height (cm)",
                value=float(existing.gauge_height_cm or 0),
                key=f"{prefix}-gauge",
            )
            st.caption(
                "Station gauge height is not whole-route navigability. "
                "Any delivery-delay effect is a documented simulation assumption."
            )
        else:
            known = st.checkbox(
                "Maximum temperature known",
                value=existing.maximum_temperature_c is not None,
                key=f"{prefix}-known",
            )
            temperature = st.number_input(
                "Simulated maximum temperature (°C)",
                value=float(existing.maximum_temperature_c or 0),
                key=f"{prefix}-temperature",
            )
            snowfall_options = ("No", "Yes", "Unknown")
            snowfall_values = {"No": False, "Yes": True, "Unknown": None}
            snowfall_label = st.selectbox(
                "Forecast snowfall",
                snowfall_options,
                index=tuple(snowfall_values.values()).index(existing.forecast_snowfall),
                key=f"{prefix}-snowfall",
            )
            snowfall = snowfall_values[snowfall_label]
            snow = st.selectbox(
                "Snow on route",
                list(RouteSnow),
                index=list(RouteSnow).index(existing.route_snow),
                format_func=lambda value: value.value.title(),
                key=f"{prefix}-snow",
            )
            car = st.selectbox(
                "Car availability",
                list(Availability),
                index=list(Availability).index(existing.car_availability),
                format_func=lambda value: value.value.title(),
                key=f"{prefix}-car",
            )
            st.caption("Forecast snowfall and snow already on the route are separate inputs.")
        interval = _window_fields(existing.interval, prefix)
        st.caption(
            "If the trip moves, demo conditions carry over with a note. "
            "Old and new trip times remain available in details."
        )
        apply = st.form_submit_button("Apply route conditions")
        cancel = st.form_submit_button("Cancel")
    if cancel:
        state.pop(f"{key}-active", None)
        for name in list(state):
            if name.startswith(prefix):
                state.pop(name)
        st.rerun()
    if not apply:
        return overrides, False
    if interval is None:
        st.error("The end time must be after the start time. No conditions were applied.")
        return overrides, False
    provenance = Provenance(
        f"Coordinator demo override: {active.value}", EvidenceKind.SYNTHETIC, clock, clock
    )
    if isinstance(existing, IngredientRouteOverride):
        edited = replace(
            existing,
            gauge_height_cm=gauge if known else None,
            interval=interval,
            provenance=provenance,
        )
    else:
        edited = replace(
            existing,
            maximum_temperature_c=temperature if known else None,
            forecast_snowfall=snowfall,
            route_snow=snow,
            car_availability=car,
            interval=interval,
            provenance=provenance,
        )
    state.pop(f"{key}-active", None)
    return replace(overrides, **{field: edited}), False
