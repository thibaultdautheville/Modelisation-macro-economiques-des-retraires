import pandas as pd
import pytest

from src.liquidation_reference import (
    aggregate_reference_distribution,
    allocate_observed_age_by_group,
    build_reference_liquidation_distribution,
    compute_reference_aod_exposure,
)


def sample_ages():
    return pd.DataFrame(
        {
            "sex": [
                "F",
                "F",
                "F",
                "F",
            ],
            "age_numeric": [
                61.0,
                62.0,
                63.0,
                64.0,
            ],
            "effectifs": [
                100.0,
                100.0,
                100.0,
                100.0,
            ],
        }
    )


def sample_groups():
    return pd.DataFrame(
        {
            "sex": [
                "F",
                "F",
            ],
            "group_code": [
                "droit_commun",
                "carriere_longue",
            ],
            "share_within_sex_recomputed": [
                0.70,
                0.30,
            ],
        }
    )


def test_age_group_allocation_preserves_total():
    result = allocate_observed_age_by_group(
        sample_ages(),
        sample_groups(),
    )

    assert result[
        "allocated_effectifs"
    ].sum() == pytest.approx(
        400.0
    )


def test_standard_departures_62_63_shift_to_64():
    result = build_reference_liquidation_distribution(
        sample_ages(),
        sample_groups(),
        reference_aod_months=768,
        observed_standard_age_floor_months=744,
    )

    shifted = result.loc[
        result["shifted_to_reference_aod"]
    ]

    assert set(
        shifted["age_numeric"]
    ) == {
        62.0,
        63.0,
    }

    assert (
        shifted[
            "reference_age_numeric"
        ] == 64.0
    ).all()


def test_age_61_is_not_shifted():
    result = build_reference_liquidation_distribution(
        sample_ages(),
        sample_groups(),
        reference_aod_months=768,
        observed_standard_age_floor_months=744,
    )

    age_61 = result.loc[
        result["age_numeric"] == 61.0
    ]

    assert not age_61[
        "shifted_to_reference_aod"
    ].any()


def test_early_retirement_group_is_not_shifted():
    result = build_reference_liquidation_distribution(
        sample_ages(),
        sample_groups(),
        reference_aod_months=768,
        observed_standard_age_floor_months=744,
    )

    racl = result.loc[
        result["group_code"]
        == "carriere_longue"
    ]

    assert not racl[
        "shifted_to_reference_aod"
    ].any()


def test_reference_exposure_includes_bunched_standard_departures():
    detail = build_reference_liquidation_distribution(
        sample_ages(),
        sample_groups(),
        reference_aod_months=768,
        observed_standard_age_floor_months=744,
    )

    reference = (
        aggregate_reference_distribution(
            detail
        )
    )

    exposure = (
        compute_reference_aod_exposure(
            reference,
            baseline_aod_months=768,
            reform_aod_months=780,
        )
    )

    value = exposure.loc[
        exposure["sex"] == "F",
        "movable_exposed_effectifs",
    ].iloc[0]

    # droit commun :
    # âge 62 = 70
    # âge 63 = 70
    # âge 64 déjà observé = 70
    # total sous référence AOD=64 = 210
    assert value == pytest.approx(
        210.0
    )


def test_non_annual_age_rejected():
    with pytest.raises(ValueError):
        build_reference_liquidation_distribution(
            sample_ages(),
            sample_groups(),
            reference_aod_months=774,
            observed_standard_age_floor_months=744,
        )