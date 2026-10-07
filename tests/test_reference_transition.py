import pandas as pd
import pytest

from src.reference_transition import (
    apply_reference_transition,
    build_reference_aod_transition,
)


def sample_legal():
    return pd.DataFrame(
        {
            "birth_year": [
                1960,
                1961,
                1962,
                1963,
                1964,
            ],
            "birth_month": [
                1,
                1,
                1,
                1,
                1,
            ],
            "aod_months": [
                744,
                750,
                756,
                762,
                768,
            ],
        }
    )


def test_transition_factor_is_bounded():
    result = build_reference_aod_transition(
        sample_legal(),
        floor_aod_months=744,
        target_aod_months=768,
    )

    assert result[
        "reference_maturity_factor"
    ].between(
        0.0,
        1.0,
    ).all()


def test_linear_transition_values():
    result = build_reference_aod_transition(
        sample_legal(),
        floor_aod_months=744,
        target_aod_months=768,
    )

    factors = (
        result[
            "reference_maturity_factor"
        ]
        .tolist()
    )

    assert factors == pytest.approx(
        [
            0.00,
            0.25,
            0.50,
            0.75,
            1.00,
        ]
    )


def test_target_aod_has_full_maturity():
    result = build_reference_aod_transition(
        sample_legal(),
        floor_aod_months=744,
        target_aod_months=768,
    )

    maximum = result[
        "reference_maturity_factor"
    ].max()

    assert maximum == pytest.approx(
        1.0
    )


def test_transition_adjusts_stock():
    stock = pd.DataFrame(
        {
            "year": [
                2028,
                2029,
            ],
            "annual_average_delayed_stock": [
                200000.0,
                200000.0,
            ],
        }
    )

    transition = pd.DataFrame(
        {
            "year": [
                2028,
                2029,
            ],
            "reference_maturity_factor": [
                0.5,
                1.0,
            ],
        }
    )

    result = apply_reference_transition(
        stock,
        transition,
    )

    assert result.loc[
        0,
        "annual_average_delayed_stock_transition_adjusted",
    ] == pytest.approx(
        100000.0
    )

    assert result.loc[
        1,
        "annual_average_delayed_stock_transition_adjusted",
    ] == pytest.approx(
        200000.0
    )
    