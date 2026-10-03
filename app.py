"""T1 read-only synthetic examples; T8/T9 replace this foundation screen."""

import tomllib
from pathlib import Path

import altair as alt
import streamlit as st

from treatment_planner.demo import (
    SCENARIOS,
    FixtureComparator,
    fixture_environment,
    fixture_request,
    fixture_settings,
)
from treatment_planner.interfaces import CandidatePlan


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
    theme_path = Path(__file__).parent / "config" / "theme.toml"
    theme = tomllib.loads(theme_path.read_text(encoding="utf-8"))["timeline"]
    events = tuple(event for event in plan.events if not detail or event.lane != "Ingredients")
    rows = [
        {
            "Lane": event.lane,
            "Event": event.label,
            "Start": event.interval.start.isoformat(),
            "End": event.interval.end.isoformat(),
        }
        for event in events
    ]
    chart = (
        alt.Chart(alt.Data(values=rows))
        .mark_bar(color=theme["event_color"])
        .encode(
            x=alt.X("Start:T", title="UTC", scale=alt.Scale(type="utc")),
            x2="End:T",
            y=alt.Y("Lane:N", sort=None, title=None),
            tooltip=["Event:N", "Start:N", "End:N"],
        )
        .properties(height=theme["height_per_lane"] * len({event.lane for event in events}))
    )
    st.altair_chart(chart, width="stretch")
    if not detail:
        st.dataframe(rows, hide_index=True, width="stretch")


def main() -> None:
    st.set_page_config(page_title="Treatment material-flow planner", layout="wide")
    st.title("Treatment material-flow planner")
    st.warning(
        "Synthetic foundation demo — these are fixed, authored T4 examples. "
        "No live data or generated recommendations yet."
    )
    scenario = st.selectbox("Authored scenario", SCENARIOS)
    request = fixture_request()
    environment = fixture_environment(scenario)
    plans = FixtureComparator(scenario).compare(request, environment, fixture_settings(scenario))
    st.caption(
        f"Invented treatment · order {request.order_time:%d %b %Y %H:%M} UTC · "
        f"original collection {request.original_collection:%d %b %Y %H:%M} UTC"
    )
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
    st.write(f"**Authored fixture result: {plan.status.value}**")
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
