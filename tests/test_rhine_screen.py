"""Screen checks for notebook evidence, coverage and offline behaviour."""

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from treatment_planner.interfaces import EvidenceMode

ROOT = Path(__file__).resolve().parents[1]


def screen():
    with patch("urllib.request.urlopen", side_effect=AssertionError("Offline mode used network")):
        app = AppTest.from_file(ROOT / "app.py")
        app.session_state["v2-mode-value"] = EvidenceMode.DEMO
        app.session_state["v2-navigation"] = "Sources & assumptions"
        return app.run(timeout=25)


def test_summary_chart_and_outside_horizon():
    app = screen()
    assert not app.exception
    summary = next(e for e in app.expander if e.label.startswith("Basel Rhine conditions"))
    assert "WARNING now" in summary.label
    assert "CRITICAL within coverage; remainder UNKNOWN" in summary.label
    assert any("not fully covered" in w.value for w in app.warning)
    assert any("forecast unavailable for the selected date" in i.value for i in app.info)
    assert app.get("vega_lite_chart")
    day = next(w for w in app.selectbox if w.label == "Inspect Rhine forecast date")
    day.select(day.options[0]).run()
    assert not app.exception
    assert any("Forecast median at" in m.value for m in app.markdown)
    next(w for w in app.number_input if w.label == "Rhine forecast window (days)").set_value(
        1
    ).run()
    summary = next(e for e in app.expander if e.label.startswith("Basel Rhine conditions"))
    assert "remainder UNKNOWN" not in summary.label


def test_missing_capture_keeps_dashboard_working():
    from treatment_planner.data.rhine_forecast import load_forecast_replay
    from treatment_planner.ui.rhine import _replay_evidence

    missing = load_forecast_replay(ROOT / "data/replay/not-present")
    _replay_evidence.clear()
    with patch("treatment_planner.ui.rhine._replay_evidence", return_value=missing):
        app = screen()
    assert not app.exception
    assert any("UNKNOWN now" in e.label for e in app.expander)
    assert any("No Rhine history or forecast" in i.value for i in app.info)
    _replay_evidence.clear()
