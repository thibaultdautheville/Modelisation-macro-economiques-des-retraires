"""Integration du statu quo; pas d'ajustement des cibles economiques."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.simulation import get_simulation_summary, run_aod_simulation


@pytest.fixture(scope="module")
def neutral():
    return run_aod_simulation("statu_quo", 768, 768)


def test_statu_quo_has_all_45_years(neutral):
    summary = get_simulation_summary(neutral)
    assert summary["year"].tolist() == list(range(2026, 2071))
    assert not summary.isna().any().any()


def test_statu_quo_has_zero_stocks_and_labour_deltas(neutral):
    summary = get_simulation_summary(neutral)
    columns = [c for c in summary if c not in ("year", "reference_maturity_factor")]
    assert (summary[columns] == 0).all().all()
    assert (neutral["cohort_calendar"]["delta_aod_months"] == 0).all()
    assert (neutral["displaced_annual"]["movable_liquidations"] == 0).all()


def test_statu_quo_empty_monthly_detail_has_schema(neutral):
    detail = neutral["delayed_stock_detail"]
    assert detail.empty
    assert {"sex", "calendar_year", "calendar_month", "delayed_stock_persons"}.issubset(detail.columns)


def test_statu_quo_preserves_sex_diagnostic(neutral):
    result = neutral["labour_behaviour_trajectory"]
    assert len(result) == 90
    assert set(result["sex"]) == {"F", "H"}
    assert (result[["delta_labour_force_reform", "delta_employment_reform", "delta_unemployment_reform"]] == 0).all().all()


def test_statu_quo_at_floor_has_zero_effects():
    result = run_aod_simulation("statu_quo", 744, 744)
    assert (get_simulation_summary(result)["delta_employment_reform"] == 0).all()


def test_plus_one_is_not_neutral_even_when_calibration_ages_equal():
    with pytest.raises(ValueError, match="juridique non neutre"):
        run_aod_simulation("benchmark_aod_plus_1", 768, 768)


def test_statu_quo_rejects_nonzero_calibration_shift():
    with pytest.raises(ValueError, match="calendrier est neutre"):
        run_aod_simulation("statu_quo", 768, 780)


def test_uniform_calendar_and_calibration_shift_must_agree():
    with pytest.raises(ValueError, match="decalage de calibration"):
        run_aod_simulation("benchmark_aod_plus_1", 768, 792)


@pytest.mark.parametrize("name,value", [
    ("absorption_rate", float("nan")),
    ("behavioural_delay_share", float("inf")),
    ("steady_state_intensity", 0),
])
def test_invalid_scalar_rejected(name, value):
    with pytest.raises(ValueError):
        run_aod_simulation("statu_quo", 768, 768, **{name: value})


def test_original_benchmark_summary_is_unchanged():
    before = pd.read_csv(Path(__file__).parent / "fixtures/benchmark_summary_before_audit.csv")
    result = run_aod_simulation("benchmark_aod_plus_1", 768, 780)
    after = get_simulation_summary(result)
    pd.testing.assert_frame_equal(after[before.columns], before, check_dtype=False, atol=1e-7, rtol=1e-12)
    assert np.allclose(after["delayed_person_years_transition_adjusted"], after["annual_average_delayed_stock_transition_adjusted"])


def test_original_behaviour_diagnostic_is_unchanged():
    before = pd.read_csv(Path(__file__).parent / "fixtures/behaviour_before_audit.csv")
    result = run_aod_simulation("benchmark_aod_plus_1", 768, 780)
    after = result["labour_behaviour_trajectory"]
    pd.testing.assert_frame_equal(after[before.columns], before, check_dtype=False, atol=1e-7, rtol=1e-12)


def test_summary_rejects_missing_columns(neutral):
    malformed = {**neutral, "annual_delayed_stock": neutral["annual_delayed_stock"].drop(columns="reference_maturity_factor")}
    with pytest.raises(ValueError, match="manquantes"):
        get_simulation_summary(malformed)


def test_summary_rejects_reversed_horizon(neutral):
    with pytest.raises(ValueError):
        get_simulation_summary(neutral, 2070, 2026)
