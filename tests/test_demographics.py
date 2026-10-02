import pandas as pd
import pytest

from src.demographics import (
    build_monthly_demography,
    split_to_monthly_cohorts,
    validate_demography,
)


def sample_demography():
    return pd.DataFrame(
        {
            "year": [
                2026,
                2026,
                2027,
                2027,
            ],
            "age": [
                64,
                64,
                65,
                65,
            ],
            "sex": [
                "F",
                "H",
                "F",
                "H",
            ],
            "population": [
                1200,
                1080,
                1188,
                1068,
            ],
        }
    )


def test_demography_validation():
    validate_demography(
        sample_demography()
    )


def test_monthly_split_creates_twelve_rows():
    df = sample_demography().iloc[[0]]

    result = split_to_monthly_cohorts(df)

    assert len(result) == 12
    assert set(result["birth_month"]) == set(
        range(1, 13)
    )


def test_monthly_split_preserves_population():
    df = sample_demography()

    result = split_to_monthly_cohorts(df)

    reconstructed = (
        result
        .groupby(
            ["year", "age", "sex"]
        )["population_monthly"]
        .sum()
        .sort_index()
    )

    expected = (
        df
        .set_index(
            ["year", "age", "sex"]
        )["population"]
        .astype(float)
        .sort_index()
    )

    pd.testing.assert_series_equal(
        reconstructed,
        expected,
        check_names=False,
    )


def test_birth_cohort_convention():
    df = sample_demography().iloc[[0]]

    result = split_to_monthly_cohorts(df)

    assert (
        result["birth_year"] == 1961
    ).all()

    assert result.iloc[0]["cohort_id"] == "1961-01"
    assert result.iloc[-1]["cohort_id"] == "1961-12"


def test_negative_population_rejected():
    df = sample_demography()
    df.loc[0, "population"] = -1

    with pytest.raises(ValueError):
        validate_demography(df)


def test_build_monthly_demography_horizon():
    result = build_monthly_demography(
        sample_demography(),
        start_year=2026,
        end_year=2027,
    )

    assert set(result["year"]) == {
        2026,
        2027,
    }

    assert len(result) == 48