import pandas as pd
import pytest

from src.reform_trajectory import (
    build_reform_labour_trajectory,
)


def sample_displaced():
    return pd.DataFrame(
        {
            "year": [
                2026,
                2027,
                2028,
            ],
            "movable_liquidations": [
                20000.0,
                30000.0,
                32000.0,
            ],
        }
    )


def test_full_behaviour_full_absorption():
    result = build_reform_labour_trajectory(
        sample_displaced(),
        behavioural_delay_share=1.0,
        absorption_rate=1.0,
    )

    assert result[
        "delta_labour_force_reform"
    ].tolist() == [
        20000,
        30000,
        32000,
    ]

    assert result[
        "delta_employment_reform"
    ].tolist() == [
        20000,
        30000,
        32000,
    ]

    assert (
        result[
            "delta_unemployment_reform"
        ] == 0
    ).all()


def test_partial_behaviour():
    result = build_reform_labour_trajectory(
        sample_displaced(),
        behavioural_delay_share=0.8,
        absorption_rate=1.0,
    )

    assert result.loc[
        0,
        "delta_labour_force_reform",
    ] == pytest.approx(
        16000
    )


def test_partial_absorption():
    result = build_reform_labour_trajectory(
        sample_displaced(),
        behavioural_delay_share=1.0,
        absorption_rate=0.75,
    )

    assert result.loc[
        0,
        "delta_employment_reform",
    ] == pytest.approx(
        15000
    )

    assert result.loc[
        0,
        "delta_unemployment_reform",
    ] == pytest.approx(
        5000
    )


def test_labour_identity():
    result = build_reform_labour_trajectory(
        sample_displaced(),
        behavioural_delay_share=0.8,
        absorption_rate=0.6,
    )

    identity = (
        result[
            "delta_employment_reform"
        ]
        + result[
            "delta_unemployment_reform"
        ]
    )

    pd.testing.assert_series_equal(
        identity,
        result[
            "delta_labour_force_reform"
        ],
        check_names=False,
    )


def test_invalid_behaviour_rejected():
    with pytest.raises(ValueError):
        build_reform_labour_trajectory(
            sample_displaced(),
            behavioural_delay_share=1.2,
            absorption_rate=1.0,
        )


def test_invalid_absorption_rejected():
    with pytest.raises(ValueError):
        build_reform_labour_trajectory(
            sample_displaced(),
            behavioural_delay_share=1.0,
            absorption_rate=-0.1,
        )