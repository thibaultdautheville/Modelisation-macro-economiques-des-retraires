
from datetime import date

import pandas as pd
import pytest

from src.transition_selector import select_transition_stock


@pytest.fixture
def sample_data():
    calendar = pd.DataFrame({
        "birth_year": [1962, 1962],
        "birth_month": [1, 2],
        "baseline_eligibility_year": [2026, 2026],
        "baseline_eligibility_month": [8, 9],
        "delta_aod_months": [3, 3],
    })

    detail = pd.DataFrame({
        "birth_year": [1962, 1962],
        "birth_month": [1, 2],
        "calendar_year": [2026, 2026],
        "calendar_month": [8, 9],
        "delayed_stock_persons": [120.0, 240.0],
    })

    annual = pd.DataFrame({
        "year": [2026],
        "annual_average_delayed_stock": [30.0],
        "annual_average_delayed_stock_transition_adjusted": [15.0],
        "reference_maturity_factor": [0.5],
    })

    return calendar, detail, annual


def test_historical_method_preserved(sample_data):
    calendar, detail, annual = sample_data

    result = select_transition_stock(
        calendar, detail, annual,
    )

    assert result.loc[0, "selected_delayed_stock"] == 15.0


def test_cohort_calendar_without_double_adjustment(sample_data):
    calendar, detail, annual = sample_data

    result = select_transition_stock(
        calendar,
        detail,
        annual,
        method="calendrier_cohortes",
        effective_date=date(2026, 9, 1),
    )

    assert result.loc[
        0, "selected_delayed_stock"
    ] == pytest.approx(20.0)


def test_double_adjustment_is_explicit(sample_data):
    calendar, detail, annual = sample_data

    result = select_transition_stock(
        calendar,
        detail,
        annual,
        method="double_ajustement",
        effective_date=date(2026, 9, 1),
    )

    assert result.loc[
        0, "selected_delayed_stock"
    ] == pytest.approx(10.0)


def test_unknown_method_rejected(sample_data):
    calendar, detail, annual = sample_data

    with pytest.raises(ValueError):
        select_transition_stock(
            calendar, detail, annual,
            method="inconnue",
        )


def test_cohort_method_requires_date(sample_data):
    calendar, detail, annual = sample_data

    with pytest.raises(ValueError):
        select_transition_stock(
            calendar,
            detail,
            annual,
            method="calendrier_cohortes",
        )
