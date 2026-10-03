"""Display supplied recommendations and collect explicit plan confirmation."""

from collections.abc import Callable
from datetime import UTC, datetime

import streamlit as st

from treatment_planner.interfaces import (
    CandidatePlan,
    CheckStatus,
    PlanningGoal,
    RecommendationResult,
    ResultStatus,
    RouteId,
    RouteStatus,
    RouteSummary,
)
from treatment_planner.ui.formatting import DATE_INPUT_FORMAT, format_timestamp
from treatment_planner.ui.route_summary import render_route_summaries


def selectable_plan(plan: CandidatePlan) -> bool:
    """Defend the confirmation boundary; this does not rank or recompute checks."""
    return (
        plan.status == ResultStatus.CONFIRMED
        and bool(plan.checks)
        and all(check.status == CheckStatus.PASS for check in plan.checks)
    )


def render_goal(
    goal: PlanningGoal,
    target_injection: datetime | None,
    *,
    key: str = "v2-goal",
) -> tuple[PlanningGoal, datetime | None]:
    """Return goal/target inputs for the caller to recompute recommendations."""
    goals = list(PlanningGoal)
    selected = st.radio(
        "Planning goal",
        goals,
        index=goals.index(goal),
        format_func=lambda value: value.value.title(),
        horizontal=True,
        key=key,
    )
    if selected != PlanningGoal.INJECTION_TIMING:
        return selected, target_injection
    if target_injection is None:
        st.warning("Enter a target injection time before requesting this recommendation.")
        known = st.checkbox("Set target injection time", key=f"{key}-target-known")
        if not known:
            return selected, None
    initial = target_injection.astimezone(UTC) if target_injection else None
    date = st.date_input(
        "Target injection date (UTC)",
        value=initial.date() if initial else None,
        format=DATE_INPUT_FORMAT,
        key=f"{key}-date",
    )
    time = st.time_input(
        "Target injection time (UTC)",
        value=initial.time() if initial else None,
        format="24h",
        key=f"{key}-time",
    )
    target = datetime.combine(date, time, tzinfo=UTC) if date and time is not None else None
    return selected, target


def _plan_label(plan: CandidatePlan) -> str:
    hours = plan.collection_shift.total_seconds() / 3600
    pickup = "original sample pickup" if hours == 0 else f"sample pickup {hours:g} h later"
    return (
        f"{plan.title} · {plan.ingredient_mode.value} · "
        f"{plan.outbound_mode.value} outbound · {plan.return_mode.value} return · {pickup}"
    )


def _route_details_ready(summaries: tuple[RouteSummary, ...], plan_id: str | None) -> bool:
    routes = tuple(item for item in summaries if item.plan_id == plan_id)
    return (
        len(routes) == len(RouteId)
        and {item.route for item in routes} == set(RouteId)
        and all(item.status in (RouteStatus.NORMAL, RouteStatus.AT_RISK) for item in routes)
    )


def render_recommendation(
    plans: tuple[CandidatePlan, ...],
    result: RecommendationResult,
    summaries: tuple[RouteSummary, ...],
    theme: dict,
    *,
    current: bool,
    context: tuple,
    render_details: Callable[[CandidatePlan], None],
    original_collection: datetime | None = None,
    baseline_plan: CandidatePlan | None = None,
    render_advisories: Callable[[CandidatePlan], None] | None = None,
    key: str = "v2-recommendation",
) -> CandidatePlan | None:
    """Return only explicit confirmation of a current, fully checked candidate.

    Context must include the current goal/target, evidence mode and overrides.
    Navigation must not be part of context. Integration owns recomputation.
    """
    signature = (plans, result, summaries, context, current)
    state = st.session_state
    changed = state.get(f"{key}-signature") != signature
    had_confirmation = state.get(f"{key}-confirmed") is not None
    eligible = {p.plan_id: p for p in plans if selectable_plan(p)}
    winners = tuple(pid for pid in result.winner_plan_ids if pid in eligible)
    valid_result = winners == result.winner_plan_ids
    if changed:
        state[f"{key}-confirmed"] = None
        state[f"{key}-picked"] = winners[0] if len(winners) == 1 and valid_result else None
        for suffix in ("choice", "inspect"):
            state.pop(f"{key}-{suffix}", None)
        state[f"{key}-signature"] = signature
        if had_confirmation:
            st.info("Planning inputs or evidence changed. Confirm the updated plan again.")
    st.subheader("Recommended plan" if current else "Previous recommendation (inputs changed)")
    st.caption(f"Goal: {result.goal.value.title()}")
    summary, excluded, _ = result.reason.partition(" Excluded from ranking: ")
    st.write(summary)
    if excluded:
        count = len(plans) - len(result.scores)
        st.caption(
            f"{count} generated alternatives excluded from ranking; inspect their checks below."
        )
    if not current:
        st.warning("Inputs changed. Recompute the recommendation before confirming.")
    if not valid_result:
        st.error("The supplied recommendation includes a plan that cannot be confirmed.")
        winners = ()
    if not winners:
        st.warning("No recommendation available. Inspect the failed or missing checks below.")
    elif len(winners) > 1:
        st.info("Equal best scores: choose a tied plan explicitly. None is preselected.")
    else:
        st.caption(f"Recommended: {_plan_label(eligible[winners[0]])}")

    chosen = None
    if winners:
        ids = tuple(eligible)
        previous = state.get(f"{key}-picked")
        default = ids.index(previous) if previous in ids else None
        picked = st.selectbox(
            "Plan to confirm",
            ids,
            index=default,
            format_func=lambda pid: (
                ("Recommended · " if pid in winners else "Alternative · ")
                + _plan_label(eligible[pid])
            ),
            key=f"{key}-choice",
            disabled=not current,
        )
        chosen = eligible.get(picked)
        state[f"{key}-picked"] = picked
    if chosen is not None:
        if current and render_advisories is not None:
            render_advisories(chosen)
        with st.container(border=True):
            st.write(_plan_label(chosen))
            events = {event.event_id: event.interval.end for event in chosen.events}
            for column, (label, instant) in zip(
                st.columns(3),
                (
                    (
                        "Sample pickup",
                        original_collection + chosen.collection_shift
                        if original_collection is not None
                        else None,
                    ),
                    ("Ingredient arrival", events.get("ingredients")),
                    ("Injection", events.get("handling")),
                ),
                strict=True,
            ):
                column.caption(label)
                column.write(format_timestamp(instant))
            for score in result.scores:
                if score.plan_id != chosen.plan_id:
                    continue
                if score.injection_penalty_minutes is not None:
                    st.caption(
                        f"Weighted injection deviation: {score.injection_penalty_minutes:g} min"
                    )
                if score.ingredient_arrival is not None:
                    st.caption(f"Ingredient arrival: {format_timestamp(score.ingredient_arrival)}")
                if score.limiting_margin is not None:
                    st.caption(
                        f"Smallest scored deadline margin: "
                        f"{score.limiting_margin.total_seconds() / 3600:g} h · "
                        f"At risk local routes: "
                        f"{score.at_risk_routes if score.at_risk_routes is not None else 'Unknown'}"
                    )
        render_route_summaries(summaries, chosen.plan_id, theme, key=key)
    route_ready = _route_details_ready(summaries, chosen.plan_id if chosen else None)
    if chosen is not None and not route_ready:
        st.warning("Route summaries are missing, unknown or blocked. Recompute before confirming.")
    if st.button(
        "Confirm plan",
        key=f"{key}-confirm",
        type="primary",
        disabled=not current or chosen is None or not route_ready,
    ):
        state[f"{key}-confirmed"] = chosen.plan_id
    confirmed_id = state.get(f"{key}-confirmed")
    confirmed = (
        eligible.get(confirmed_id)
        if current and _route_details_ready(summaries, confirmed_id)
        else None
    )
    if confirmed is not None:
        st.success(f"Your confirmed plan: {_plan_label(confirmed)}. No transport is booked.")
        if chosen is not None and confirmed.plan_id != chosen.plan_id:
            st.caption("You are reviewing a different plan; confirm it to replace your choice.")
    else:
        st.caption("No plan confirmed yet.")
    with st.expander("Original baseline · Reference timetable", expanded=False):
        if baseline_plan is None:
            st.caption("Original baseline timetable not supplied.")
        else:
            render_details(baseline_plan)
    with st.expander("Other alternatives, checks & timelines", expanded=False):
        if plans:
            plan_ids = tuple(p.plan_id for p in plans)
            by_id = {p.plan_id: p for p in plans}
            inspected = st.selectbox(
                "Inspect alternative",
                plan_ids,
                format_func=lambda pid: f"{by_id[pid].status.value} · {_plan_label(by_id[pid])}",
                key=f"{key}-inspect",
            )
            render_details(by_id[inspected])
            if not winners:
                render_route_summaries(summaries, inspected, theme, key=f"{key}-inspect")
    return confirmed
