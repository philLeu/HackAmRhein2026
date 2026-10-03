"""T1 read-only synthetic examples; T8/T9 replace this foundation screen."""

import streamlit as st

from treatment_planner.demo import (
    SCENARIOS,
    FixtureComparator,
    fixture_environment,
    fixture_request,
    fixture_settings,
)
from treatment_planner.interfaces import CandidatePlan
from treatment_planner.ui.formatting import format_timestamp
from treatment_planner.ui.presentation import apply_theme
from treatment_planner.ui.timeline import timeline_chart


def comparison_rows(plans: tuple[CandidatePlan, ...]) -> list[dict]:
    return [
        {
            "Plan": plan.title,
            "Fixture result": plan.status.value,
            "Collection shift (h)": plan.collection_shift.total_seconds() / 3600,
            "Ingredients": plan.ingredient_mode.value,
            "Outbound": plan.outbound_mode.value,
            "Return": plan.return_mode.value,
        }
        for plan in plans
    ]


def render_timeline(plan: CandidatePlan, detail: bool = False) -> None:
    theme = apply_theme()["timeline"]
    events = tuple(event for event in plan.events if not detail or event.lane != "Ingredients")
    rows = [
        {
            "Lane": event.lane,
            "Event": event.label,
            "Start": format_timestamp(event.interval.start),
            "End": format_timestamp(event.interval.end),
        }
        for event in events
    ]
    st.altair_chart(timeline_chart(plan, theme, detail=detail), width="stretch")
    if not detail:
        st.dataframe(rows, hide_index=True, width="stretch")


def main() -> None:
    st.set_page_config(page_title="Treatment material-flow planner", layout="wide")
    apply_theme()
    st.caption("OPERATIONS PREVIEW / MATERIAL FLOW")
    st.title("Treatment material-flow planner")
    st.write(
        "Compare transport options, inspect constraints and follow every stage of the journey."
    )
    st.warning(
        "Synthetic foundation demo — these are fixed, authored T4 examples. "
        "No live data or generated recommendations yet."
    )
    scenario = st.selectbox("Authored scenario", SCENARIOS)
    request = fixture_request()
    environment = fixture_environment(scenario)
    plans = FixtureComparator(scenario).compare(request, environment, fixture_settings(scenario))
    st.caption(
        f"Invented treatment · order {format_timestamp(request.order_time)} · "
        f"original collection {format_timestamp(request.original_collection)}"
    )
    overview = st.columns(3)
    overview[0].metric("Example plans", len(plans))
    overview[1].metric("Scenario", scenario.replace("-", " ").title())
    overview[2].metric("Time reference", "UTC")
    st.divider()
    st.subheader("Compare example plans")
    st.dataframe(comparison_rows(plans), hide_index=True, width="stretch")
    selected = st.selectbox(
        "Inspect example plan",
        range(len(plans)),
        format_func=lambda i: plans[i].title,
        key=f"inspection-{scenario}",
    )
    plan = plans[selected]
    st.subheader(plan.title)
    status_message = f"Authored fixture result: {plan.status.value}"
    if plan.status.value == "confirmed":
        st.success(status_message)
    elif plan.status.value == "infeasible":
        st.error(status_message)
    else:
        st.info(status_message)
    st.dataframe(
        [
            {
                "Constraint": check.constraint,
                "Fixture check": check.status.value,
                "Margin (h)": None if check.margin is None else check.margin.total_seconds() / 3600,
                "Reason": check.reason,
            }
            for check in plan.checks
        ],
        hide_index=True,
        width="stretch",
    )
    st.subheader("Full material-flow timeline")
    render_timeline(plan)
    st.subheader("Treatment-period detail")
    render_timeline(plan, detail=True)
    with st.expander("Synthetic assumptions and evidence", expanded=True):
        for assumption in plan.assumptions:
            st.write(f"- {assumption}")
        st.write("Manual clear-route entries at order time require renewed checks at dispatch.")
        st.write(
            "The fixed results assume those future checks succeed; they are not live evidence."
        )
        for issue in environment.river.issues + environment.weather.issues:
            st.caption(issue)
    st.caption(
        "Planning preview only. No patient records, clinical decisions or transport bookings."
    )


if __name__ == "__main__":
    main()
