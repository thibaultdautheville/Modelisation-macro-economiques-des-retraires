import pandas as pd
import pytest

from src.reform_liquidations import (
    aggregate_displaced_liquidations,
    calibrate_displaced_liquidations,
)


def sample_delay():
    return pd.DataFrame(
        {
            "year": [
                2026,
                2027,
                2028,
            ],
            "cohort_months_delayed": [
                72,
                144,
                36,
            ],
        }
    )


def sample_reference():
    return pd.DataFrame(
        {
            "sex": [
                "F",
                "H",
            ],
            "movable_exposed_effectifs": [
                18000,
                14000,
            ],
        }
    )


def test_full_intensity_reproduces_reference():
    result = calibrate_displaced_liquidations(
        sample_delay(),
        sample_reference(),
    )

    full = result.loc[
        result["year"] == 2027
    ]

    assert full[
        "movable_liquidations"
    ].sum() == pytest.approx(
        32000
    )


def test_half_intensity():
    result = calibrate_displaced_liquidations(
        sample_delay(),
        sample_reference(),
    )

    half = result.loc[
        result["year"] == 2026
    ]

    assert half[
        "movable_liquidations"
    ].sum() == pytest.approx(
        16000
    )


def test_quarter_intensity():
    result = calibrate_displaced_liquidations(
        sample_delay(),
        sample_reference(),
    )

    quarter = result.loc[
        result["year"] == 2028
    ]

    assert quarter[
        "movable_liquidations"
    ].sum() == pytest.approx(
        8000
    )


def test_sex_structure_is_preserved():
    result = calibrate_displaced_liquidations(
        sample_delay(),
        sample_reference(),
    )

    female = result.loc[
        (result["year"] == 2027)
        & (result["sex"] == "F"),
        "movable_liquidations",
    ].iloc[0]

    assert female == pytest.approx(
        18000
    )


def test_aggregation():
    result = calibrate_displaced_liquidations(
        sample_delay(),
        sample_reference(),
    )

    annual = aggregate_displaced_liquidations(
        result
    )

    assert annual.loc[
        annual["year"] == 2027,
        "movable_liquidations",
    ].iloc[0] == pytest.approx(
        32000
    )


def test_intensity_above_steady_state_rejected():
    delay = pd.DataFrame(
        {
            "year": [2026],
            "cohort_months_delayed": [145],
        }
    )

    with pytest.raises(ValueError):
        calibrate_displaced_liquidations(
            delay,
            sample_reference(),
        )