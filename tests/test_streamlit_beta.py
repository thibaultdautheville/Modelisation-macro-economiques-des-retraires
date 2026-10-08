
"""Controles de disponibilite de l'interface Streamlit."""

import ast
from pathlib import Path

import pytest


APP_PATH = Path("app/streamlit_app.py")


def test_streamlit_app_exists():
    assert APP_PATH.is_file()


def test_streamlit_app_syntax():
    ast.parse(
        APP_PATH.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "required",
    [
        "run_aod_simulation",
        "transition_method",
        "effective_date",
        "selected_delayed_stock",
        "delta_employment_reform",
    ],
)
def test_streamlit_app_contains_model_connections(required):
    content = APP_PATH.read_text(encoding="utf-8")
    assert required in content

