import pandas as pd
import pytest

from src.reform_stock import (
    aggregate_annual_stock,
    aggregate_monthly_stock,
    build_labour_effect_from_stock,
    build_monthly_delayed_stock,
)


def sample_reference():
    return pd.DataFrame(
        {
            "sex": [
                "F",
                "H",
            ],
            "movable_exposed_effectifs": [
                1200.0,
                1200.0,
            ],
        }
    )


def two_year_cohort_calendar():
    rows = []

    for birth_year in [
        1965,
        1966,
    ]:
        for birth_month in range(
            1,
            13,
        ):
            baseline_year = (
                birth_year + 64
            )

            rows.append(
                {
                    "birth_year":
                        birth_year,
                    "birth_month":
                        birth_month,
                    "delta_aod_months":
                        12,
                    "baseline_eligibility_year":
                        baseline_year,
                    "baseline_eligibility_month":
                        birth_month,
                }
            )

    return pd.DataFrame(rows)


def test_reference_is_split_over_12_cohorts():
    stock = build_monthly_delayed_stock(
        two_year_cohort_calendar(),
        sample_reference(),
    )

    first = stock.iloc[0]

    assert first[
        "delayed_stock_persons"
    ] == pytest.approx(
        100.0
    )


def test_each_cohort_sex_has_12_delay_months():
    stock = build_monthly_delayed_stock(
        two_year_cohort_calendar(),
        sample_reference(),
    )

    counts = (
        stock
        .groupby(
            [
                "birth_year",
                "birth_month",
                "sex",
            ]
        )
        .size()
    )

    assert (
        counts == 12
    ).all()


def test_monthly_stock_builds_up():
    stock = build_monthly_delayed_stock(
        two_year_cohort_calendar(),
        sample_reference(),
    )

    monthly = aggregate_monthly_stock(
        stock
    )

    january_2029 = monthly.loc[
        (monthly["year"] == 2029)
        & (monthly["month"] == 1),
        "delayed_stock_persons",
    ].iloc[0]

    december_2029 = monthly.loc[
        (monthly["year"] == 2029)
        & (monthly["month"] == 12),
        "delayed_stock_persons",
    ].iloc[0]

    assert january_2029 == pytest.approx(
        200.0
    )

    assert december_2029 == pytest.approx(
        2400.0
    )


def test_steady_state_stock_equals_annual_reference():
    stock = build_monthly_delayed_stock(
        two_year_cohort_calendar(),
        sample_reference(),
    )

    monthly = aggregate_monthly_stock(
        stock
    )

    january_2030 = monthly.loc[
        (monthly["year"] == 2030)
        & (monthly["month"] == 1),
        "delayed_stock_persons",
    ].iloc[0]

    assert january_2030 == pytest.approx(
        2400.0
    )


def test_annual_stock_uses_all_12_months():
    stock = build_monthly_delayed_stock(
        two_year_cohort_calendar(),
        sample_reference(),
    )

    monthly = aggregate_monthly_stock(
        stock
    )

    annual = aggregate_annual_stock(
        monthly,
        start_year=2029,
        end_year=2030,
    )

    value = annual.loc[
        annual["year"] == 2030,
        "annual_average_delayed_stock",
    ].iloc[0]

    assert value == pytest.approx(
        2400.0
    )


def test_full_absorption_identity():
    annual = pd.DataFrame(
        {
            "year": [
                2030,
            ],
            "annual_average_delayed_stock": [
                32000.0,
            ],
        }
    )

    result = build_labour_effect_from_stock(
        annual,
        behavioural_delay_share=1.0,
        absorption_rate=1.0,
    )

    assert result.loc[
        0,
        "delta_labour_force_reform",
    ] == pytest.approx(
        32000.0
    )

    assert result.loc[
        0,
        "delta_employment_reform",
    ] == pytest.approx(
        32000.0
    )

    assert result.loc[
        0,
        "delta_unemployment_reform",
    ] == pytest.approx(
        0.0
    )


def test_partial_absorption_accounting():
    annual = pd.DataFrame(
        {
            "year": [
                2030,
            ],
            "annual_average_delayed_stock": [
                10000.0,
            ],
        }
    )

    result = build_labour_effect_from_stock(
        annual,
        behavioural_delay_share=0.8,
        absorption_rate=0.75,
    )

    assert result.loc[
        0,
        "delta_labour_force_reform",
    ] == pytest.approx(
        8000.0
    )

    assert result.loc[
        0,
        "delta_employment_reform",
    ] == pytest.approx(
        6000.0
    )

    assert result.loc[
        0,
        "delta_unemployment_reform",
    ] == pytest.approx(
        2000.0
    )