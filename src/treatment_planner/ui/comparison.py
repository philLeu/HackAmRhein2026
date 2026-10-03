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
    RecommendationResult,
    ResultStatus,
    RouteSummary,
    TransportMode,
    TreatmentRequest,
)
from treatment_planner.ui.formatting import format_timestamp
from treatment_planner.ui.presentation import apply_theme
from treatment_planner.ui.recommendation import render_recommendation, selectable_plan
from treatment_planner.ui.route_inputs import render_route_inputs as render_route_inputs
from treatment_planner.ui.route_summary import render_route_diagram
from treatment_planner.ui.timeline import timeline_chart

THEME_PATH = Path(__file__).resolve().parents[3] / "config" / "theme.toml"


def _hours(value: timedelta | None) -> float | None:
    return None if value is None else value.total_seconds() / 3600


def _selectable(plan: CandidatePlan) -> bool:
    return selectable_plan(plan)


def comparison_rows(plans: tuple[CandidatePlan, ...]) -> list[dict]:
    """Display deadline margins without turning missing evidence into a pass."""
    rows = []
    for number, plan in enumerate(plans, start=1):
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
                "Plan": f"Generated option {number}",
                "Result": plan.status.value,
                "Sample pickup": _collection_timing_label(plan),
                "Tightest margin (h)": _hours(tightest),
                "Binding deadline": binding or "Not confirmed",
                "Ingredients": plan.ingredient_mode.value,
                "Outbound": plan.outbound_mode.value,
                "Return": plan.return_mode.value,
            }
        )
    return rows


def _find_plan(
    plans: tuple[CandidatePlan, ...],
    ingredients: TransportMode,
    outbound: TransportMode,
    returning: TransportMode,
    shift_hours: int = 0,
) -> CandidatePlan | None:
    return next(
        (
            plan
            for plan in plans
            if plan.ingredient_mode == ingredients
            and plan.outbound_mode == outbound
            and plan.return_mode == returning
            and plan.collection_shift == timedelta(hours=shift_hours)
        ),
        None,
    )


def _key_options(plans: tuple[CandidatePlan, ...]) -> list[CandidatePlan]:
    """Choose a few understandable contrasts before exposing every combination."""
    if not plans:
        return []
    ship, truck, bike, car = (
        TransportMode.SHIP,
        TransportMode.TRUCK,
        TransportMode.BICYCLE,
        TransportMode.CAR,
    )
    baseline = _find_plan(plans, ship, bike, bike) or plans[0]
    options = [baseline]
    failed = {
        check.constraint.lower() for check in baseline.checks if check.status == CheckStatus.FAIL
    }
    uncertain = {
        check.constraint.lower() for check in baseline.checks if check.status == CheckStatus.UNKNOWN
    }

    def add(plan: CandidatePlan | None) -> None:
        if plan is not None and plan not in options:
            options.append(plan)

    # Show the 12-hour recovery only when the current plan misses production.
    if "production completion" in failed:
        recovery = _find_plan(plans, ship, bike, bike, 12)
        if recovery is None:
            recovery = next(
                (
                    plan
                    for plan in plans
                    if plan.ingredient_mode == ship
                    and plan.outbound_mode == bike
                    and plan.return_mode == bike
                    and plan.collection_shift > timedelta(0)
                    and _selectable(plan)
                ),
                None,
            )
        add(recovery)

    # A different ingredient route is a useful contrast when shipment timing fails,
    # and a compact alternative in the baseline case.
    truck_option = _find_plan(plans, truck, bike, bike)
    if "ingredient arrival" in failed or baseline.status == ResultStatus.CONFIRMED:
        add(truck_option)

    weather_or_snow = any(
        term in issue for issue in failed | uncertain for term in ("weather", "snow")
    )
    if weather_or_snow:
        add(_find_plan(plans, ship, bike, car))
        add(_find_plan(plans, ship, car, car))
    elif baseline.status == ResultStatus.CONFIRMED:
        add(_find_plan(plans, ship, bike, car))

    if baseline.status != ResultStatus.CONFIRMED and not any(
        _selectable(option) for option in options
    ):
        add(_find_plan(plans, ship, car, car))
    # The heuristic above is only a compact set of examples. Never let it hide
    # every usable plan when the full generated set contains a confirmed one.
    confirmed = next((plan for plan in plans if _selectable(plan)), None)
    if confirmed is not None and not any(_selectable(option) for option in options):
        if len(options) == 4:
            options[-1] = confirmed
        else:
            options.append(confirmed)
    return options[:4]


def _option_label(plan: CandidatePlan, baseline: CandidatePlan) -> str:
    if plan.plan_id == baseline.plan_id:
        return "Current schedule"
    changes = []
    if plan.ingredient_mode != baseline.ingredient_mode:
        changes.append("Use refrigerated truck for ingredients")
    if plan.outbound_mode != baseline.outbound_mode:
        changes.append("Use car for sample trip")
    if plan.return_mode != baseline.return_mode:
        changes.append("Use car for treatment return")
    if plan.collection_shift:
        hours = int(plan.collection_shift.total_seconds() / 3600)
        changes.append(f"Collect sample {hours} h later")
    return " + ".join(changes) or "Same transport choices"


def _plan_summary_label(plan: CandidatePlan) -> str:
    ingredients = (
        "Rhine ship" if plan.ingredient_mode == TransportMode.SHIP else "refrigerated truck"
    )
    outbound = "bicycle" if plan.outbound_mode == TransportMode.BICYCLE else "car"
    returning = "bicycle" if plan.return_mode == TransportMode.BICYCLE else "car"
    shift = int(plan.collection_shift.total_seconds() / 3600)
    collection = "original pickup time" if shift == 0 else f"pickup {shift} h later"
    return (
        f"{ingredients} · Sample: hospital → factory by {outbound} · "
        f"Treatment: factory → hospital by {returning} · {collection}"
    )


def _collection_timing_label(plan: CandidatePlan) -> str:
    shift = int(plan.collection_shift.total_seconds() / 3600)
    if shift == 0:
        return "Original scheduled pickup time (0 h later)"
    return f"{shift} h later than scheduled"


def _render_material_flow(plan: CandidatePlan, theme: dict, diagram_prefix: str) -> None:
    """Sketch how ingredients and the sample meet at production."""
    ingredients = "ship" if plan.ingredient_mode == TransportMode.SHIP else "refrigerated truck"
    sample = "bicycle" if plan.outbound_mode == TransportMode.BICYCLE else "car"
    treatment = "bicycle" if plan.return_mode == TransportMode.BICYCLE else "car"
    cards = (
        ("1 · INGREDIENTS", "Rotterdam", ingredients, "Factory"),
        ("2 · SAMPLE", "Hospital", sample, "Factory"),
        ("3 · PRODUCTION", "Sample + ingredients", "Production", "Treatment ready"),
        ("4 · TREATMENT", "Factory", treatment, "Hospital"),
    )
    columns = st.columns(4)
    for column, (heading, source, vehicle, destination) in zip(columns, cards, strict=True):
        with column:
            with st.container(border=True):
                st.caption(heading)
                render_route_diagram(
                    heading,
                    source,
                    vehicle,
                    destination,
                    theme,
                    f"{diagram_prefix}-{heading[0]}",
                )
                if heading.startswith("1") and plan.ingredient_mode == TransportMode.SHIP:
                    st.caption("Raw ingredients travel from Rotterdam by ship on the Rhine.")
                elif heading.startswith("1"):
                    st.caption("Raw ingredients travel from Rotterdam by refrigerated truck.")
                elif heading.startswith("2"):
                    st.caption(f"Pickup: {_collection_timing_label(plan)}")
                elif heading.startswith("3"):
                    st.caption("Ingredients and sample are processed together.")
                elif heading.startswith("4"):
                    st.caption("Hospital handling comes before injection.")
    st.caption(
        "The sample pickup shift is measured against its original hospital pickup time. "
        "0 h later means the original time; a later pickup shifts the sample trip and "
        "production timing."
    )


def _plain_deadline(name: str) -> str:
    labels = {
        "Ingredient arrival": "Ingredients arrive at the factory",
        "Sample arrival": "Sample arrives at the factory",
        "Production completion": "Production finishes",
        "Injection": "Treatment at hospital",
        "Collection shift": "Latest allowed sample pickup",
        "Outbound preparation": "Car ready for sample trip",
        "Return preparation": "Car ready for return trip",
        "Outbound weather": "Weather for sample trip",
        "Return weather": "Weather for return trip",
        "Outbound route snow": "Snow on sample route",
        "Return route snow": "Snow on return route",
        "Outbound car availability": "Car available for sample trip",
        "Return car availability": "Car available for return trip",
    }
    return labels.get(name, name)


def _plain_status(plan: CandidatePlan) -> str:
    if plan.status == ResultStatus.UNCONFIRMED:
        return "Cannot confirm — evidence is missing or incomplete"
    margins = [check.margin for check in plan.checks if check.margin is not None]
    if plan.status == ResultStatus.INFEASIBLE:
        failed = [check for check in plan.checks if check.status == CheckStatus.FAIL]
        missed = [
            check.margin
            for check in failed
            if check.margin is not None and check.margin < timedelta(0)
        ]
        causes = []
        failed_names = " ".join(check.constraint.lower() for check in failed)
        if any(term in failed_names for term in ("weather", "snow")):
            causes.append("Weather or route conditions block this plan")
        if "car availability" in failed_names:
            causes.append("Required car is unavailable")
        if missed:
            late = abs(min(missed).total_seconds() / 3600)
            causes.insert(0, f"{late:g} h late")
        elif not causes:
            causes.append("A planning rule blocks this option")
        return " · ".join(causes)
    if not margins:
        return "Deadlines met — exact buffer unavailable"
    tightest = min(margins)
    hours = tightest.total_seconds() / 3600
    if hours == 0:
        return "On time — exactly at a deadline, no buffer"
    return f"On time — {hours:g} h buffer"


def _key_option_rows(plans: tuple[CandidatePlan, ...]) -> list[dict]:
    options = _key_options(plans)
    baseline = options[0] if options else None
    rows = []
    for number, plan in enumerate(options):
        margins = [check.margin for check in plan.checks if check.margin is not None]
        tightest = min(margins) if margins and plan.status != ResultStatus.UNCONFIRMED else None
        binding = ", ".join(
            _plain_deadline(check.constraint)
            for check in plan.checks
            if tightest is not None and check.margin == tightest
        )
        rows.append(
            {
                "Plan": f"Key option {number + 1}",
                "Change from current": _option_label(plan, baseline),
                "Deadline result": _plain_status(plan),
                "Tightest deadline": binding or "Not confirmed",
            }
        )
    return rows


def _render_details(plan: CandidatePlan, theme: dict, *, current: bool) -> None:
    st.subheader(_plan_summary_label(plan))
    label = "Deadline result" if current else "Previous result (inputs changed)"
    st.write(f"**{label}: {_plain_status(plan)}**")
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
    with st.expander("Assumptions behind this plan", expanded=False):
        for assumption in plan.assumptions:
            st.write(f"- {assumption}")


def _render_evidence(
    request: TreatmentRequest,
    environment: EnvironmentInputs,
    *,
    expanded: bool = False,
) -> None:
    with st.expander("Data sources, coverage and manual route checks", expanded=expanded):
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


def render_sources(request: TreatmentRequest, environment: EnvironmentInputs) -> None:
    """Present current evidence on the Sources chapter without changing inputs."""
    st.subheader("Sources & assumptions")
    _render_evidence(request, environment, expanded=True)


def render_comparison(
    plans: tuple[CandidatePlan, ...],
    *,
    request: TreatmentRequest,
    environment: EnvironmentInputs,
    compared_request: TreatmentRequest,
    compared_environment: EnvironmentInputs,
    key: str = "comparison",
    theme_path: Path = THEME_PATH,
    recommendation: RecommendationResult | None = None,
    route_summaries: tuple[RouteSummary, ...] = (),
    confirmation_context: tuple = (),
    baseline_plan: CandidatePlan | None = None,
) -> CandidatePlan | None:
    """Inspect alternatives and return a current, explicitly selected plan.

    The caller owns computation and must supply the snapshots used to obtain
    plans. Inputs or outputs changing invalidate selection. Stale results remain
    inspectable, with selection disabled until recomputed by the caller.
    """
    signature = (request, environment, plans, compared_request, compared_environment)
    theme = apply_theme(theme_path)
    if st.session_state.get(f"{key}-signature") != signature:
        st.session_state[f"{key}-selected"] = None
        st.session_state.pop(f"{key}-inspect", None)
        st.session_state[f"{key}-signature"] = signature
    current = request == compared_request and environment == compared_environment
    departure = "not departed" if request.decision_time < request.nominal_departure else "departed"
    st.caption(
        f"Planning decision {format_timestamp(request.decision_time)} · "
        f"Ingredient order {format_timestamp(request.order_time)} · "
        f"Original sample pickup {format_timestamp(request.original_collection)} · "
        f"Rotterdam ship {departure}"
    )
    _render_evidence(request, environment)
    if recommendation is not None:

        def details(plan: CandidatePlan) -> None:
            _render_material_flow(plan, theme, f"{key}-detail")
            _render_details(plan, theme["timeline"], current=current)

        return render_recommendation(
            plans,
            recommendation,
            route_summaries,
            theme,
            current=current,
            context=(
                request,
                environment,
                compared_request,
                compared_environment,
                confirmation_context,
            ),
            render_details=details,
            original_collection=request.original_collection,
            baseline_plan=baseline_plan,
            key=f"{key}-v2",
        )
    if not plans:
        st.info("No alternatives supplied. Run a comparison; feasibility is not yet known.")
        return None
    st.subheader("Compare options")
    if not current:
        st.warning("Inputs changed. Recompute the comparison before selecting a plan.")
    rows = comparison_rows(plans)
    if not current:
        for row in rows:
            row["Result"] += " (previous comparison)"
    key_rows = _key_option_rows(plans)
    key_options = _key_options(plans)
    baseline = key_options[0] if key_options else plans[0]
    key_tab, all_tab = st.tabs(["Key options", f"All {len(rows)} generated options"])
    with key_tab:
        st.caption(
            "Open an option to trace its route. A zero-hour buffer means a deadline is met "
            "exactly, with no room for delay."
        )
        for number, alternative in enumerate(key_options, start=1):
            title = "Current schedule" if number == 1 else _option_label(alternative, baseline)
            with st.expander(
                f"Key option {number} · {title}",
                expanded=number == 1,
            ):
                _render_material_flow(alternative, theme, f"key-{number}")
                result = key_rows[number - 1]
                st.write(f"**Deadline result:** {result['Deadline result']}")
                st.caption(f"Closest deadline: {result['Tightest deadline']}")
        st.dataframe(
            key_rows,
            hide_index=True,
            width="stretch",
            column_config={
                "Plan": st.column_config.TextColumn("Option"),
                "Change from current": st.column_config.TextColumn("Change from current"),
                "Deadline result": st.column_config.TextColumn("Deadline result"),
                "Tightest deadline": st.column_config.TextColumn("Tightest deadline"),
            },
        )
    with all_tab:
        st.caption(
            "These are every generated combination. They are not ranked; open any one to "
            "see its route sketch."
        )
        with st.expander("Show comparison data for all generated options"):
            st.dataframe(
                rows,
                hide_index=True,
                width="stretch",
                column_config={
                    "Plan": st.column_config.TextColumn("Option"),
                    "Result": st.column_config.TextColumn("Status"),
                    "Sample pickup": st.column_config.TextColumn("Sample pickup timing"),
                    "Tightest margin (h)": st.column_config.NumberColumn(
                        "Buffer at tightest deadline (h)", format="%+.0f"
                    ),
                    "Binding deadline": st.column_config.TextColumn("Tightest deadline"),
                    "Ingredients": st.column_config.TextColumn("Ingredient route"),
                    "Outbound": st.column_config.TextColumn("Sample trip"),
                    "Return": st.column_config.TextColumn("Treatment return"),
                },
            )
        for number, alternative in enumerate(plans, start=1):
            with st.expander(
                f"Generated option {number} · {_plain_status(alternative)}",
                expanded=False,
            ):
                _render_material_flow(alternative, theme, f"all-{number}")
                tightest = _key_option_rows((alternative,))[0]["Tightest deadline"]
                st.caption(f"Closest deadline: {tightest}")
    if current and not any(_selectable(candidate) for candidate in plans):
        if all(candidate.status == ResultStatus.INFEASIBLE for candidate in plans):
            st.error("No feasible plan within the supplied alternatives.")
        else:
            st.warning("No confirmed plan yet. Inspect missing evidence and reasons.")
    inspected = st.selectbox(
        "Choose a plan for deadline checks and timeline",
        range(len(plans)),
        format_func=lambda i: (
            f"Option {i + 1} · "
            f"{plans[i].ingredient_mode.value} · "
            f"{plans[i].outbound_mode.value} outbound · "
            f"{plans[i].return_mode.value} return · "
            f"{_collection_timing_label(plans[i])}"
        ),
        key=f"{key}-inspect",
    )
    plan = plans[inspected]
    if st.button(
        "Select this confirmed plan",
        disabled=not current or not _selectable(plan),
        key=f"{key}-select",
    ):
        st.session_state[f"{key}-selected"] = plan.plan_id
    selected_id = st.session_state.get(f"{key}-selected")
    selected = next((p for p in plans if p.plan_id == selected_id and _selectable(p)), None)
    if selected and current:
        selected_number = next(
            i for i, candidate in enumerate(plans, start=1) if candidate == selected
        )
        st.success(
            f"Selected Option {selected_number}. This is only a planning choice; "
            "no transport is booked."
        )
    else:
        selected = None
        st.caption("No plan selected yet.")
    if selected and selected.plan_id != plan.plan_id:
        inspected_number = next(
            i for i, candidate in enumerate(plans, start=1) if candidate == plan
        )
        selected_number = next(
            i for i, candidate in enumerate(plans, start=1) if candidate == selected
        )
        st.caption(
            f"Inspecting Option {inspected_number}; your selection remains "
            f"Option {selected_number}."
        )
    try:
        timeline_theme = theme["timeline"]
        with st.expander(
            "Detailed checks and timelines",
            expanded=selected is not None and selected.plan_id == plan.plan_id,
        ):
            _render_details(plan, timeline_theme, current=current)
            if selected and selected.plan_id != plan.plan_id:
                st.subheader("Selected plan timeline")
                st.altair_chart(timeline_chart(selected, timeline_theme), width="stretch")
    except (OSError, KeyError, tomllib.TOMLDecodeError) as error:
        st.error(f"Timeline theme unavailable: {error}")
    return selected
