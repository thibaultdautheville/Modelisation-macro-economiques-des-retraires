import pandas as pd
import pytest

from src.labour_behaviour import (
    aggregate_annual_delayed_stock_by_sex,
    apply_reference_transition_by_sex,
    build_status_stock,
    build_labour_effect_by_status,
    aggregate_labour_effect,
)


def test_annual_stock_uses_twelve_month_average():
    detail = pd.DataFrame(
        {
            "calendar_year": [
                2030,
                2030,
            ],
            "calendar_month": [
                1,
                2,
            ],
            "sex": [
                "F",
                "F",
            ],
            "delayed_stock_persons": [
                120.0,
                120.0,
            ],
        }
    )

    result = (
        aggregate_annual_delayed_stock_by_sex(
            detail,
            start_year=2030,
            end_year=2030,
        )
    )

    female = result.loc[
        result["sex"] == "F"
    ].iloc[0]

    assert female[
        "annual_average_delayed_stock"
    ] == pytest.approx(
        20.0
    )


def test_reference_transition_by_sex():
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
            "annual_average_delayed_stock": [
                100.0,
                200.0,
            ],
        }
    )

    transition = pd.DataFrame(
        {
            "year": [
                2030,
            ],
            "reference_maturity_factor": [
                0.5,
            ],
        }
    )

    result = apply_reference_transition_by_sex(
        stock,
        transition,
    )

    assert result[
        "annual_average_delayed_stock_adjusted"
    ].tolist() == pytest.approx(
        [
            50.0,
            100.0,
        ]
    )


def test_status_stock_preserves_adjusted_stock():
    stock = pd.DataFrame(
        {
            "year": [
                2030,
            ],
            "sex": [
                "F",
            ],
            "annual_average_delayed_stock_adjusted": [
                1000.0,
            ],
        }
    )

    rates = pd.DataFrame(
        {
            "sex": [
                "F",
            ],
            "pre_retirement_employment_share": [
                0.434,
            ],
            "pre_retirement_unemployment_share": [
                0.024,
            ],
            "pre_retirement_inactivity_share": [
                0.542,
            ],
        }
    )

    result = build_status_stock(
        stock,
        rates,
    )

    total = (
        result["previously_employed"]
        + result["previously_unemployed"]
        + result["previously_inactive"]
    )

    assert total.iloc[0] == pytest.approx(
        1000.0
    )


def test_full_behaviour_reproduces_full_employment():
    status = pd.DataFrame(
        {
            "year": [
                2030,
            ],
            "sex": [
                "F",
            ],
            "previously_employed": [
                434.0,
            ],
            "previously_unemployed": [
                24.0,
            ],
            "previously_inactive": [
                542.0,
            ],
        }
    )

    result = build_labour_effect_by_status(
        status,
        employment_retention_rate=1.0,
        unemployed_activity_retention_rate=1.0,
        unemployed_job_entry_rate=1.0,
        inactive_activation_rate=1.0,
        inactive_employment_rate=1.0,
    )

    assert result[
        "delta_labour_force_reform"
    ].iloc[0] == pytest.approx(
        1000.0
    )

    assert result[
        "delta_employment_reform"
    ].iloc[0] == pytest.approx(
        1000.0
    )

    assert result[
        "delta_unemployment_reform"
    ].iloc[0] == pytest.approx(
        0.0
    )


def test_partial_behaviour_creates_unemployment():
    status = pd.DataFrame(
        {
            "year": [
                2030,
            ],
            "sex": [
                "F",
            ],
            "previously_employed": [
                400.0,
            ],
            "previously_unemployed": [
                100.0,
            ],
            "previously_inactive": [
                500.0,
            ],
        }
    )

    result = build_labour_effect_by_status(
        status,
        employment_retention_rate=1.0,
        unemployed_activity_retention_rate=1.0,
        unemployed_job_entry_rate=0.5,
        inactive_activation_rate=0.2,
        inactive_employment_rate=0.5,
    )

    assert result[
        "delta_labour_force_reform"
    ].iloc[0] == pytest.approx(
        600.0
    )

    assert result[
        "delta_employment_reform"
    ].iloc[0] == pytest.approx(
        500.0
    )

    assert result[
        "delta_unemployment_reform"
    ].iloc[0] == pytest.approx(
        100.0
    )


def test_aggregate_labour_effect():
    data = pd.DataFrame(
        {
            "year": [
                2030,
                2030,
            ],
            "sex": [
                "F",
                "H",
            ],
            "delta_labour_force_reform": [
                100.0,
                200.0,
            ],
            "delta_employment_reform": [
                80.0,
                150.0,
            ],
            "delta_unemployment_reform": [
                20.0,
                50.0,
            ],
            "employment_from_employed": [
                50.0,
                100.0,
            ],
            "employment_from_unemployed": [
                10.0,
                20.0,
            ],
            "employment_from_inactive": [
                20.0,
                30.0,
            ],
        }
    )

    result = aggregate_labour_effect(
        data
    )

    assert result[
        "delta_labour_force_reform"
    ].iloc[0] == pytest.approx(
        300.0
    )

    assert result[
        "delta_employment_reform"
    ].iloc[0] == pytest.approx(
        230.0
    )

    assert result[
        "delta_unemployment_reform"
    ].iloc[0] == pytest.approx(
        70.0
    )


def test_invalid_unemployed_job_entry_rate():
    status = pd.DataFrame(
        {
            "year": [2030],
            "sex": ["F"],
            "previously_employed": [400.0],
            "previously_unemployed": [100.0],
            "previously_inactive": [500.0],
        }
    )

    with pytest.raises(
        ValueError
    ):
        build_labour_effect_by_status(
            status,
            unemployed_activity_retention_rate=0.5,
            unemployed_job_entry_rate=0.8,
        )

