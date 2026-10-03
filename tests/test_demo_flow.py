"""End-to-end acceptance of the integrated offline V2 demo."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from treatment_planner.interfaces import EvidenceMode

ROOT = Path(__file__).resolve().parents[1]


def demo_screen():
    screen = AppTest.from_file(ROOT / "app.py")
    screen.session_state["v2-mode"] = EvidenceMode.DEMO
    return screen.run(timeout=30)


def test_demo_opens_plan_with_recommendation_and_explicit_confirmation():
    app = demo_screen()
    assert not app.exception
    assert any(button.label == "Confirm plan" for button in app.button)
    assert any("Planning goal and recommendation" in item.value for item in app.subheader)
    assert "v2-confirmed-plan" in app.session_state


def test_all_three_independent_route_controls_are_available():
    app = demo_screen()
    labels = {button.label for button in app.button}
    assert "🚢 Rotterdam → Basel" in labels
    assert "🚲 Hospital → Production" in labels
    assert "🚲 Production → Hospital" in labels
    assert "Reset demo" in labels


def test_routes_and_sources_chapters_are_reachable_offline():
    app = demo_screen()
    app.radio(key="v2-navigation").set_value("Routes & conditions").run(timeout=30)
    assert not app.exception
    assert any(select.label == "Alternative" for select in app.selectbox)
    app.radio(key="v2-navigation").set_value("Sources & assumptions").run(timeout=30)
    assert not app.exception
    assert any(
        expander.label == "Basel station chart · supporting evidence" for expander in app.expander
    )
