from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402


def test_app_generate_and_changed_settings():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app/streamlit_app.py"))
    app.run(timeout=30)
    assert not app.exception
    assert app.metric[0].label == "Observations"
    assert app.metric[0].value == "1000"
    assert app.metric[1].value == "40"
    digest = app.session_state.population.provenance["population_sha256"]
    app.number_input[0].set_value(100).run(timeout=30)
    assert app.metric[0].value == "1000"
    assert any("Settings changed" in item.value for item in app.warning)
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert app.metric[0].value == "100"
    assert app.session_state.population.provenance["population_sha256"] != digest
    app.button[0].click().run(timeout=30)
    assert app.metric[0].value == "100"
    assert not app.exception
