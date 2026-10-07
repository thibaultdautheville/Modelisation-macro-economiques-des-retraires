import pandas as pd
import pytest

from src.calibration import (
    build_employment_calibration_diagnostic,
    compare_employment_to_institutional_range,
    prepare_institutional_benchmarks,
)


def sample_simulation():
    return pd.DataFrame(
        {
            "year": [
                2026,
                2027,
                2035,
                2045,
            ],
            "delta_employment_reform": [
                30000.0,
                60000.0,
                180000.0,
                220000.0,
            ],
        }
    )


def sample_benchmarks():
    return pd.DataFrame(
        {
            "horizon_years": [
                2,
                10,
                20,
            ],
            "metric": [
                "employment_thousands",
                "employment_thousands",
                "employment_thousands",
            ],
            "min_value": [
                50.0,
                160.0,
                200.0,
            ],
            "max_value": [
                140.0,
                250.0,
                240.0,
            ],
            "unit": [
                "thousand_persons",
                "thousand_persons",
                "thousand_persons",
            ],
            "source": [
                "test",
                "test",
                "test",
            ],
        }
    )


def test_prepare_benchmarks():
    result = prepare_institutional_benchmarks(
        sample_benchmarks()
    )

    assert len(result) == 3


def test_unit_conversion_to_persons():
    result = compare_employment_to_institutional_range(
        sample_simulation(),
        sample_benchmarks(),
        start_year=2026,
    )

    row = result.loc[
        result["horizon_years"] == 2
    ].iloc[0]

    assert row[
        "benchmark_min_employment"
    ] == pytest.approx(
        50000.0
    )


def test_value_inside_range():
    result = compare_employment_to_institutional_range(
        sample_simulation(),
        sample_benchmarks(),
        start_year=2026,
    )

    row = result.loc[
        result["horizon_years"] == 2
    ].iloc[0]

    assert row["position"] == "within_range"


def test_long_term_inside_range():
    result = compare_employment_to_institutional_range(
        sample_simulation(),
        sample_benchmarks(),
        start_year=2026,
    )

    row = result.loc[
        result["horizon_years"] == 20
    ].iloc[0]

    assert row["position"] == "within_range"


def test_diagnostic_flag():
    simulation = sample_simulation()

    simulation.loc[
        simulation["year"] == 2035,
        "delta_employment_reform",
    ] = 30000.0

    result = build_employment_calibration_diagnostic(
        simulation,
        sample_benchmarks(),
        start_year=2026,
    )

    row = result.loc[
        result["horizon_years"] == 10
    ].iloc[0]

    assert bool(
        row["requires_investigation"]
    )