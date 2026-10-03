"""End-to-end acceptance of generated schedules and offline provider evidence."""

import importlib.util
import socket
from datetime import timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from treatment_planner.interfaces import CheckStatus

ROOT = Path(__file__).resolve().parents[1]


def screen():
    return AppTest.from_file(ROOT / "app.py").run(timeout=20)


def widget(app, label):
    return next(box for box in app.selectbox if box.label == label)


def inspect(app, *, ingredients="ship", outbound="bicycle", returning="bicycle", shift=0):
    rows = app.dataframe[0].value
    matches = rows[
        (rows["Ingredients"] == {"ship": "Rhine ship", "truck": "refrigerated truck"}[ingredients])
        & (rows["Outbound"] == outbound)
        & (rows["Return"] == returning)
        & (rows["Collection shift (h)"] == shift)
    ]
    assert len(matches) == 1
    widget(app, "Inspect plan").select(int(matches.index[0])).run()
    assert not app.exception
    return app.dataframe[1].value.set_index("Constraint")


def test_baseline_deadlines_selection_and_timeline():
    app = screen()
    assert not app.exception
    checks = inspect(app)
    for constraint, margin in [
        ("Ingredient arrival", 96),
        ("Sample arrival", 11),
        ("Production completion", 6),
        ("Injection", 6),
    ]:
        assert checks.loc[constraint, "Margin (h)"] == margin
        assert checks.loc[constraint, "Check"] == "pass"
        assert checks.loc[constraint, "Deadline (UTC)"] != "Unknown"
    app.button[0].click().run()
    first = app.session_state["selected_plan_id"]
    assert first
    events = app.dataframe[2].value
    assert "Outbound bicycle" in events["Event"].tolist()
    inspect(app, ingredients="truck", returning="car")
    app.button[0].click().run()
    assert app.session_state["selected_plan_id"] != first
    assert "Return car preparation" in app.dataframe[2].value["Event"].tolist()
    app.run()
    assert app.session_state["selected_plan_id"]


def test_rhine_delay_recovery_and_selection_invalidation():
    app = screen()
    app.button[0].click().run()
    widget(app, "Scenario").select("Low water").run()
    assert app.session_state["selected_plan_id"] is None
    checks = inspect(app)
    assert checks.loc["Production completion", "Margin (h)"] == -5
    assert app.button[0].disabled
    checks = inspect(app, shift=12)
    assert checks.loc["Production completion", "Margin (h)"] == 6
    assert not app.button[0].disabled
    inspect(app, ingredients="truck")
    assert not app.button[0].disabled
    assert "Truck approval / preparation" in app.dataframe[2].value["Event"].tolist()


@pytest.mark.parametrize("scenario", ["Hot return", "Snow"])
def test_weather_disruptions_require_car_alternatives(scenario):
    app = screen()
    widget(app, "Scenario").select(scenario).run()
    inspect(app)
    assert app.button[0].disabled
    assert any("snowfall or temperature" in message.value for message in app.error)
    inspect(app, outbound="car" if scenario == "Snow" else "bicycle", returning="car")
    assert not app.button[0].disabled
    app.button[0].click().run()
    assert app.session_state["selected_plan_id"]
    events = app.dataframe[2].value.set_index("Event")
    assert (
        events.loc["Return car preparation", "Start (UTC)"] < events.loc["Processing", "End (UTC)"]
    )


def test_route_edits_recompute_and_clear_selection():
    app = screen()
    app.button[0].click().run()
    route = next(box for box in app.selectbox if box.label == "Route snow")
    route.select("snow present").run()
    assert not app.exception
    assert app.session_state["selected_plan_id"] is None
    checks = inspect(app)
    assert checks.loc["Outbound route snow", "Check"] == "fail"
    assert not any("Inputs changed" in w.value for w in app.warning)


def test_missing_weather_is_unknown_and_no_confirmed_plan_is_distinct():
    app = screen()
    widget(app, "Scenario").select("Missing weather").run()
    checks = inspect(app)
    assert checks.loc["Outbound weather", "Check"] == "unknown"
    assert app.button[0].disabled
    # Cars can avoid missing bicycle weather, but unknown availability cannot confirm them.
    for box in app.selectbox:
        if box.label == "Car availability":
            box.select("unknown")
    app.run()
    assert any("No confirmed plan yet" in w.value for w in app.warning)
    assert not any("No feasible plan" in e.value for e in app.error)


def test_saved_providers_work_without_network_and_expose_unknowns(monkeypatch):
    original_connect = socket.socket.connect

    def network_forbidden(connection, address):
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_connect(connection, address)
        raise AssertionError("Replay must not use the network")

    monkeypatch.setattr(socket.socket, "connect", network_forbidden)
    app = screen()
    app.button[0].click().run()
    widget(app, "Evidence mode").select("Saved provider replay").run()
    assert not app.exception
    assert app.session_state["selected_plan_id"] is None
    checks = inspect(app)
    assert checks.loc["Rhine evidence", "Check"] == "unknown"
    assert checks.loc["Outbound weather", "Check"] == "unknown"
    assert app.button[0].disabled
    evidence = " ".join(w.value for w in app.warning) + " ".join(w.value for w in app.markdown)
    assert "MeteoSwiss" in evidence and "Open Data Basel-Stadt" in evidence
    assert "maximum temperature remains unknown" in evidence
    assert "retrieval time" in evidence
    assert "Stale weather" in evidence
    assert "hourly mean" in evidence
    # Both cars can avoid weather checks, but unresolved river evidence stays visible.
    inspect(app, ingredients="truck", outbound="car", returning="car")
    assert not app.exception


def test_missing_replay_files_are_reported(tmp_path):
    spec = importlib.util.spec_from_file_location("demo_app", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    request = module.demo_request(module.MODES[1])
    settings = module.load_settings(ROOT / "config/planning.json")
    env = module.provider_environment(
        request, settings, timedelta(hours=24), timedelta(hours=6), replay_root=tmp_path
    )
    assert env.river.issues and env.weather.issues
    assert not env.river.observations and not env.weather.windows
    plans = module.PlanningComparator().compare(request, env, settings)
    assert any(c.status == CheckStatus.UNKNOWN for plan in plans for c in plan.checks)


def test_all_failed_alternatives_have_no_feasible_message():
    app = screen()
    widget(app, "Scenario").select("Snow").run()
    for box in app.selectbox:
        if box.label == "Car availability":
            box.select("unavailable")
    app.run()
    assert not app.exception
    assert (app.dataframe[0].value["Result"] == "infeasible").all()
    assert any("No feasible plan" in message.value for message in app.error)
    assert app.button[0].disabled
