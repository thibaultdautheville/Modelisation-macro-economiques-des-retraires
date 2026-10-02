import pandas as pd
import pytest

from src.labour import (
    compute_baseline_labour_status,
    simulate_reform_absorption,
    validate_labour_rates,
)


def sample_labour_rates():
    return pd.DataFrame(
        {
            "year": [2025, 2025],
            "age_group": ["60-64", "65-69"],
            "sex": ["F", "F"],
            "activity_rate": [0.50, 0.15],
            "employment_rate": [0.46, 0.14],
            "unemployment_rate": [0.08, 0.0667],
            "unemployed_share_population": [0.04, 0.01],
            "inactive_share_population": [0.50, 0.85],
        }
    )


def test_labour_rates_validation():
    validate_labour_rates(
        sample_labour_rates()
    )


def test_baseline_labour_accounting():
    df = pd.DataFrame(
        {
            "population": [1000],
            "activity_rate": [0.60],
            "unemployment_rate": [0.10],
        }
    )

    result = compute_baseline_labour_status(df)

    assert result.loc[
        0, "labour_force_baseline"
    ] == 600

    assert result.loc[
        0, "unemployment_baseline"
    ] == 60

    assert result.loc[
        0, "employment_baseline"
    ] == 540

    assert result.loc[
        0, "inactive_baseline"
    ] == 400


def test_full_absorption_creates_no_extra_unemployment():
    inflows = pd.DataFrame(
        {
            "year": [2026, 2027, 2028],
            "new_active_reform": [100, 100, 100],
        }
    )

    result = simulate_reform_absorption(
        inflows,
        absorption_rate=1.0,
    )

    assert (
        result["delta_unemployment_reform"]
        == 0
    ).all()

    assert result[
        "delta_employment_reform"
    ].tolist() == [
        100,
        200,
        300,
    ]


def test_zero_absorption_creates_only_unemployment():
    inflows = pd.DataFrame(
        {
            "year": [2026, 2027],
            "new_active_reform": [100, 100],
        }
    )

    result = simulate_reform_absorption(
        inflows,
        absorption_rate=0.0,
    )

    assert result[
        "delta_employment_reform"
    ].tolist() == [
        0,
        0,
    ]

    assert result[
        "delta_unemployment_reform"
    ].tolist() == [
        100,
        200,
    ]


def test_partial_absorption_carries_unemployment():
    inflows = pd.DataFrame(
        {
            "year": [2026, 2027],
            "new_active_reform": [100, 100],
        }
    )

    result = simulate_reform_absorption(
        inflows,
        absorption_rate=0.5,
    )

    assert result.loc[
        0, "delta_employment_reform"
    ] == 50

    assert result.loc[
        0, "delta_unemployment_reform"
    ] == 50

    assert result.loc[
        1, "delta_employment_reform"
    ] == 125

    assert result.loc[
        1, "delta_unemployment_reform"
    ] == 75


def test_reform_labour_force_identity():
    inflows = pd.DataFrame(
        {
            "year": [2026, 2027, 2028],
            "new_active_reform": [100, 80, 60],
        }
    )

    result = simulate_reform_absorption(
        inflows,
        absorption_rate=0.6,
    )

    identity = (
        result["delta_employment_reform"]
        + result["delta_unemployment_reform"]
    )

    pd.testing.assert_series_equal(
        identity,
        result["delta_labour_force_reform"],
        check_names=False,
    )


def test_invalid_absorption_rate_rejected():
    inflows = pd.DataFrame(
        {
            "year": [2026],
            "new_active_reform": [100],
        }
    )

    with pytest.raises(ValueError):
        simulate_reform_absorption(
            inflows,
            absorption_rate=1.2,
        )