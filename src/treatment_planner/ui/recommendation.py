"""Display supplied recommendations and collect explicit plan confirmation."""

from collections import defaultdict
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
    TransportMode,
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
    ingredient = (
        "Rhine ship" if plan.ingredient_mode == TransportMode.SHIP else "Refrigerated truck"
    )
    return (
        f"{ingredient} · {plan.outbound_mode.value} outbound · "
        f"{plan.return_mode.value} return · {pickup}"
    )


def _mode_display(mode) -> tuple[str, str]:
    labels = {
        TransportMode.SHIP: ("🚢", "Rhine ship"),
        TransportMode.TRUCK: ("🚚", "Refrigerated truck"),
        TransportMode.BICYCLE: ("🚲", "Bicycle"),
        TransportMode.CAR: ("🚗", "Car"),
    }
    return labels.get(mode, ("", mode.value.title()))


def _render_plan_routes(plan: CandidatePlan) -> None:
    routes = (
        (
            "INGREDIENTS",
            "Rotterdam → PulseShift production site, Basel",
            plan.ingredient_mode,
        ),
        (
            "SAMPLE · OUTBOUND",
            "University Hospital Basel → PulseShift production site",
            plan.outbound_mode,
        ),
        (
            "TREATMENT · RETURN",
            "PulseShift production site → University Hospital Basel",
            plan.return_mode,
        ),
    )
    for column, (route, direction, mode) in zip(st.columns(3), routes, strict=True):
        icon, label = _mode_display(mode)
        with column.container(border=True):
            st.caption(route)
            st.write(direction)
            st.markdown(f"### {icon} {label}")


def _render_schedule(plan: CandidatePlan, original_collection: datetime | None) -> None:
    events = {event.event_id: event for event in plan.events}
    ingredients = events.get("ingredients")
    sample = events.get("sample")
    processing = events.get("processing")
    returning = events.get("return")
    handling = events.get("handling")
    collection = (
        original_collection + plan.collection_shift if original_collection is not None else None
    )
    ingredient_mode = _mode_display(plan.ingredient_mode)[1]
    steps = (
        (
            f"{ingredient_mode} · ingredients",
            "Departs Rotterdam",
            ingredients.interval.start if ingredients else None,
            "Arrives at PulseShift",
            ingredients.interval.end if ingredients else None,
        ),
        (
            "Sample",
            "Collected at University Hospital",
            collection,
            "Arrives at PulseShift",
            sample.interval.end if sample else None,
        ),
        (
            "Production",
            "Starts",
            processing.interval.start if processing else None,
            "Finished",
            processing.interval.end if processing else None,
        ),
        (
            f"Finished treatment · {plan.return_mode.value}",
            "Leaves PulseShift",
            returning.interval.start if returning else None,
            "Arrives at University Hospital",
            returning.interval.end if returning else None,
        ),
        (
            "Patient",
            "Treatment ready at hospital",
            handling.interval.end if handling else None,
            "",
            None,
        ),
    )
    st.markdown("**Schedule · all times UTC**")
    st.caption(
        "Uses configured demo travel durations. The Basel gauge can switch the Rhine "
        "scenario between 0 h and 12 h delay; live feeds do not provide actual arrival estimates."
    )
    for step, from_label, start, to_label, end in steps:
        first, origin, arrow, destination = st.columns([1.1, 1, 0.12, 1])
        first.markdown(f"**{step}**")
        origin.caption(from_label)
        origin.write(format_timestamp(start))
        if to_label:
            arrow.markdown("→")
            destination.caption(to_label)
            destination.write(format_timestamp(end))
    if processing is not None:
        duration = processing.interval.end - processing.interval.start
        st.caption(f"Production duration: {duration.total_seconds() / 3600:g} hours")


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
    reason, separator, excluded_text = result.reason.partition("\nExcluded from ranking:\n")
    st.write(reason)
    if separator:
        exclusions: dict[str, list[str]] = defaultdict(list)
        for line in excluded_text.splitlines():
            plan_id, delimiter, issue = line.removeprefix("- ").partition(": ")
            if delimiter:
                exclusions[issue].append(plan_id)
        with st.expander(f"Excluded plans · {sum(map(len, exclusions.values()))}"):
            for issue, plan_ids in sorted(exclusions.items()):
                st.markdown(f"**{len(plan_ids)} plans · {issue}**")
                st.caption(", ".join(plan_ids))
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
            st.markdown("**Route and transport**")
            _render_plan_routes(chosen)
            _render_schedule(chosen, original_collection)
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
