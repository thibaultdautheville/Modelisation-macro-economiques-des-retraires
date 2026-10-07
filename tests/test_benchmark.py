import pandas as pd
import pytest

from src.benchmark import (
    compare_employment_to_benchmark,
    implied_employment_scaling_factor,
)


def sample_trajectory():
    return pd.DataFrame(
        {
            "year": [
                2026,
                2027,
                2030,
                2035,
                2045,
            ],
            "delta_employment_reform": [
                29_000,
                71_000,
                100_000,
                150_000,
                200_000,
            ],
        }
    )


def test_first_horizon():
    result = compare_employment_to_benchmark(
        sample_trajectory(),
        start_year=2026,
    )

    row = result.loc[
        result["horizon_years"] == 1
    ].iloc[0]

    assert row[
        "model_employment"
    ] == pytest.approx(
        29_000
    )

    assert row[
        "model_to_benchmark_ratio"
    ] == pytest.approx(
        1.0
    )


def test_scaling_factor():
    result = compare_employment_to_benchmark(
        sample_trajectory(),
        start_year=2026,
    )

    factor = implied_employment_scaling_factor(
        result,
        horizon_years=2,
    )

    assert factor == pytest.approx(
        2.0
    )
    