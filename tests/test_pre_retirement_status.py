import pandas as pd
import pytest

from src.pre_retirement_status import (
    apply_pre_retirement_status,
    build_pre_retirement_status_rates,
)


def sample_labour():
    return pd.DataFrame(
        {
            "year": [
                2025,
                2025,
            ],
            "age_group": [
                "60-64",
                "60-64",
            ],
            "sex": [
                "F",
                "H",
            ],
            "employment_rate": [
                0.434,
                0.454,
            ],
            "unemployed_share_population": [
                0.024,
                0.028,
            ],
            "inactive_share_population": [
                0.542,
                0.518,
            ],
        }
    )


def test_status_rates_sum_to_one():
    result = build_pre_retirement_status_rates(
        sample_labour()
    )

    total = (
        result[
            "pre_retirement_employment_share"
        ]
        + result[
            "pre_retirement_unemployment_share"
        ]
        + result[
            "pre_retirement_inactivity_share"
        ]
    )

    assert total.tolist() == pytest.approx(
        [
            1.0,
            1.0,
        ]
    )


def test_female_status_rates():
    result = build_pre_retirement_status_rates(
        sample_labour()
    )

    female = result.loc[
        result["sex"] == "F"
    ].iloc[0]

    assert female[
        "pre_retirement_employment_share"
    ] == pytest.approx(
        0.434
    )

    assert female[
        "pre_retirement_unemployment_share"
    ] == pytest.approx(
        0.024
    )

    assert female[
        "pre_retirement_inactivity_share"
    ] == pytest.approx(
        0.542
    )


def test_apply_status_preserves_total():
    stock = pd.DataFrame(
        {
            "year": [
                2030,
                2030,
            ],
            "sex": [
                "F",
                "H",
            ],
            "delayed_stock_persons": [
                1000.0,
                1000.0,
            ],
        }
    )

    rates = build_pre_retirement_status_rates(
        sample_labour()
    )

    result = apply_pre_retirement_status(
        stock,
        rates,
    )

    total = (
        result["previously_employed"]
        + result["previously_unemployed"]
        + result["previously_inactive"]
    )

    assert total.tolist() == pytest.approx(
        [
            1000.0,
            1000.0,
        ]
    )