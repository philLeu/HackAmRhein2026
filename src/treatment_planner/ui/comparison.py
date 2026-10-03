"""Render shared plans and collect manual inputs without evaluating domain rules.

T9 collects route inputs, calls the engine, and retains the request/environment
used for that comparison. Pass those snapshots to render_comparison so changed
inputs cannot leave a previously selected plan looking current.
"""

import tomllib
from datetime import timedelta
from pathlib import Path

import streamlit as st

from treatment_planner.interfaces import (
    CandidatePlan,
    CheckStatus,
    EnvironmentInputs,
    ResultStatus,
    TreatmentRequest,
)
from treatment_planner.ui.formatting import format_timestamp
from treatment_planner.ui.presentation import apply_theme
from treatment_planner.ui.route_inputs import render_route_inputs as render_route_inputs
from treatment_planner.ui.timeline import timeline_chart

THEME_PATH = Path(__file__).resolve().parents[3] / "config" / "theme.toml"


def _hours(value: timedelta | None) -> float | None:
    return None if value is None else value.total_seconds() / 3600


def _selectable(plan: CandidatePlan) -> bool:
    return (
        plan.status == ResultStatus.CONFIRMED
        and bool(plan.checks)
        and all(check.status == CheckStatus.PASS for check in plan.checks)
    )


def comparison_rows(plans: tuple[CandidatePlan, ...]) -> list[dict]:
    """Display deadline margins without turning missing evidence into a pass."""
    rows = []
    for plan in plans:
        margins = [check.margin for check in plan.checks if check.margin is not None]
        unknown = plan.status == ResultStatus.UNCONFIRMED or any(
            check.status == CheckStatus.UNKNOWN for check in plan.checks
        )
        tightest = min(margins) if margins and not unknown else None
        binding = ", ".join(
            check.constraint
            for check in plan.checks
            if tightest is not None and check.margin == tightest
        )
        rows.append(
            {
                "Plan": plan.title,
                "Result": plan.status.value,
                "Collection shift (h)": _hours(plan.collection_shift),
                "Tightest margin (h)": _hours(tightest),
                "Binding deadline": binding or "Not confirmed",
                "Ingredients": plan.ingredient_mode.value,
                "Outbound": plan.outbound_mode.value,
                "Return": plan.return_mode.value,
            }
        )
    return rows


def _render_details(plan: CandidatePlan, theme: dict, *, current: bool) -> None:
    st.subheader(plan.title)
    label = "Result" if current else "Previous result (inputs changed)"
    st.write(f"**{label}: {plan.status.value}**")
    st.dataframe(
        [
            {
                "Constraint": check.constraint,
                "Check": check.status.value,
                "Margin (h)": _hours(check.margin),
                "Reason": check.reason,
                "Deadline (UTC)": format_timestamp(check.deadline),
            }
            for check in plan.checks
        ],
        hide_index=True,
        width="stretch",
    )
    for check in plan.checks:
        if check.status == CheckStatus.FAIL:
            st.error(f"{check.constraint}: {check.reason}")
        elif check.status == CheckStatus.UNKNOWN:
            st.warning(f"{check.constraint}: {check.reason}")
    if plan.events:
        st.subheader("Full material-flow timeline")
        st.altair_chart(timeline_chart(plan, theme), width="stretch")
        st.subheader("Treatment-period detail")
        st.altair_chart(timeline_chart(plan, theme, detail=True), width="stretch")
        st.dataframe(
            [
                {
                    "Lane": event.lane,
                    "Event": event.label,
                    "Start (UTC)": format_timestamp(event.interval.start),
                    "End (UTC)": format_timestamp(event.interval.end),
                }
                for event in plan.events
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No timeline events supplied for this alternative.")
    if not any(check.deadline for check in plan.checks):
        st.caption("No exact deadline timestamps supplied; inspect the margins above.")
    with st.expander("Plan assumptions", expanded=True):
        for assumption in plan.assumptions:
            st.write(f"- {assumption}")


def _render_evidence(request: TreatmentRequest, environment: EnvironmentInputs) -> None:
    with st.expander("Evidence, coverage and manual checks"):
        for issue in environment.river.issues + environment.weather.issues:
            st.warning(issue)
        for window in environment.weather.windows:
            source = window.provenance
            st.write(
                f"Weather · {source.kind.value} · {source.source} · {window.location} · "
                f"coverage {format_timestamp(window.interval.start)} "
                f"to {format_timestamp(window.interval.end)} · "
                f"maximum temperature {window.maximum_temperature_c} °C · "
                f"snowfall {window.snowfall} · "
                f"source time {format_timestamp(source.source_time)} · "
                f"retrieved {format_timestamp(source.retrieved_at)}"
            )
        for reading in environment.river.observations:
            source = reading.provenance
            st.write(
                f"River · {source.kind.value} · {source.source} · station {reading.station} · "
                f"observed {format_timestamp(reading.observed_at)} · "
                f"water level {reading.water_level_m} m · "
                f"discharge {reading.discharge_m3_s} m³/s · "
                f"retrieved {format_timestamp(source.retrieved_at)}"
            )
        for route in request.routes:
            checked = format_timestamp(route.checked_at)
            st.write(
                f"{route.leg.value} · {route.snow.value} · checked {checked} · "
                f"car {route.car_availability.value} · {route.provenance.kind.value}"
            )


def render_comparison(
    plans: tuple[CandidatePlan, ...],
    *,
    request: TreatmentRequest,
    environment: EnvironmentInputs,
    compared_request: TreatmentRequest,
    compared_environment: EnvironmentInputs,
    key: str = "comparison",
    theme_path: Path = THEME_PATH,
) -> CandidatePlan | None:
    """Inspect alternatives and return a current, explicitly selected plan.

    The caller owns computation and must supply the snapshots used to obtain
    plans. Inputs or outputs changing invalidate selection. Stale results remain
    inspectable, with selection disabled until recomputed by the caller.
    """
    signature = (request, environment, plans, compared_request, compared_environment)
    apply_theme(theme_path)
    if st.session_state.get(f"{key}-signature") != signature:
        st.session_state[f"{key}-selected"] = None
        st.session_state.pop(f"{key}-inspect", None)
        st.session_state[f"{key}-signature"] = signature
    current = request == compared_request and environment == compared_environment
    departure = "pending" if request.decision_time < request.nominal_departure else "departed"
    st.caption(
        f"Decision {format_timestamp(request.decision_time)} · "
        f"Order {format_timestamp(request.order_time)} · "
        f"Original collection {format_timestamp(request.original_collection)} · "
        f"Rotterdam departure {departure}"
    )
    _render_evidence(request, environment)
    st.subheader("Compare alternatives")
    if not current:
        st.warning("Inputs changed. Recompute the comparison before selecting a plan.")
    if not plans:
        st.info("No alternatives supplied. Run a comparison; feasibility is not yet known.")
        return None
    rows = comparison_rows(plans)
    if not current:
        for row in rows:
            row["Result"] += " (previous comparison)"
    st.dataframe(rows, hide_index=True, width="stretch")
    if current and not any(_selectable(plan) for plan in plans):
        if all(plan.status == ResultStatus.INFEASIBLE for plan in plans):
            st.error("No feasible plan within the supplied alternatives.")
        else:
            st.warning("No confirmed plan yet. Inspect missing evidence and reasons.")
    inspected = st.selectbox(
        "Inspect plan",
        range(len(plans)),
        format_func=lambda i: plans[i].title,
        key=f"{key}-inspect",
    )
    plan = plans[inspected]
    if st.button(
        "Select confirmed plan", disabled=not current or not _selectable(plan), key=f"{key}-select"
    ):
        st.session_state[f"{key}-selected"] = plan.plan_id
    selected_id = st.session_state.get(f"{key}-selected")
    selected = next((p for p in plans if p.plan_id == selected_id and _selectable(p)), None)
    if selected and current:
        st.success(f"Selected plan: {selected.title}. Planning choice only; no transport booked.")
    else:
        selected = None
        st.caption("No plan selected.")
    if selected and selected.plan_id != plan.plan_id:
        st.caption(f"Inspecting {plan.title}; the selected plan remains {selected.title}.")
    try:
        theme = tomllib.loads(theme_path.read_text(encoding="utf-8"))["timeline"]
        _render_details(plan, theme, current=current)
        if selected and selected.plan_id != plan.plan_id:
            st.subheader("Selected plan timeline")
            st.altair_chart(timeline_chart(selected, theme), width="stretch")
    except (OSError, KeyError, tomllib.TOMLDecodeError) as error:
        st.error(f"Timeline theme unavailable: {error}")
    return selected
