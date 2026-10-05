import pandas as pd
import pytest


from src.labour_baseline import (
    build_baseline_employment,
    build_unemployment_profile_2025,
)

def sample_labour_2025():
    return pd.DataFrame(
        {
            "year": [
                2025,
                2025,
                2025,
            ],
            "age_group": [
                "60-64",
                "60-64",
                "60-64",
            ],
            "sex": [
                "F",
                "H",
                "T",
            ],
            "unemployment_rate": [
                0.10,
                0.20,
                0.15,
            ],
        }
    )


def sample_activity():
    return pd.DataFrame(
        {
            "year": [
                2026,
                2026,
                2026,
                2026,
            ],
            "age": [
                60,
                65,
                60,
                65,
            ],
            "sex": [
                "F",
                "F",
                "H",
                "H",
            ],
            "population": [
                1000,
                1000,
                1000,
                1000,
            ],
            "activity_rate_baseline": [
                0.5,
                0.5,
                0.5,
                0.5,
            ],
            "labour_force_baseline": [
                500,
                500,
                500,
                500,
            ],
        }
    )


def sample_macro():
    return pd.DataFrame(
        {
            "year": [2026],
            "unemployment_rate_ref": [0.12],
        }
    )


def test_total_sex_is_excluded():
    profile = build_unemployment_profile_2025(
        sample_labour_2025()
    )

    assert set(
        profile["sex"]
    ) == {
        "F",
        "H",
    }


def test_65_69_uses_60_64_proxy():
    profile = build_unemployment_profile_2025(
        sample_labour_2025()
    )

    female_64 = profile.loc[
        (profile["age"] == 64)
        & (profile["sex"] == "F"),
        "unemployment_rate_2025",
    ].iloc[0]

    female_65 = profile.loc[
        (profile["age"] == 65)
        & (profile["sex"] == "F"),
        "unemployment_rate_2025",
    ].iloc[0]

    assert female_64 == female_65


def test_macro_unemployment_target_is_reproduced():
    result = build_baseline_employment(
        sample_activity(),
        sample_macro(),
        sample_labour_2025(),
    )

    realized = (
        result[
            "unemployment_baseline"
        ].sum()
        / result[
            "labour_force_baseline"
        ].sum()
    )

    assert abs(
        realized - 0.12
    ) < 1e-12


def test_labour_force_identity():
    result = build_baseline_employment(
        sample_activity(),
        sample_macro(),
        sample_labour_2025(),
    )

    identity = (
        result["employment_baseline"]
        + result["unemployment_baseline"]
    )

    pd.testing.assert_series_equal(
        identity,
        result["labour_force_baseline"].astype(float),
        check_names=False,
    )


def test_population_identity():
    result = build_baseline_employment(
        sample_activity(),
        sample_macro(),
        sample_labour_2025(),
    )

    identity = (
        result["employment_baseline"]
        + result["unemployment_baseline"]
        + result["inactive_baseline"]
    )

    pd.testing.assert_series_equal(
        identity,
        result["population"].astype(float),
        check_names=False,
    )


def test_invalid_macro_rate_is_rejected():
    macro = sample_macro()
    macro.loc[0, "unemployment_rate_ref"] = 1.2

    with pytest.raises(ValueError):
        build_baseline_employment(
            sample_activity(),
            macro,
            sample_labour_2025(),
        )