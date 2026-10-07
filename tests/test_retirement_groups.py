import pandas as pd
import pytest

from src.retirement_groups import (
    allocate_exposure_by_group,
    classify_retirement_groups,
    compute_standard_aod_movable_exposure,
)


def sample_groups():
    return pd.DataFrame(
        {
            "sex": [
                "F",
                "F",
                "H",
                "H",
            ],
            "group_code": [
                "droit_commun",
                "carriere_longue",
                "droit_commun",
                "carriere_longue",
            ],
            "share_within_sex_recomputed": [
                0.75,
                0.25,
                0.60,
                0.40,
            ],
        }
    )


def sample_exposure():
    return pd.DataFrame(
        {
            "sex": ["F", "H"],
            "potential_exposed_effectifs": [
                100,
                200,
            ],
        }
    )


def test_group_classification():
    result = classify_retirement_groups(
        sample_groups()
    )

    droit_commun = result.loc[
        result["group_code"]
        == "droit_commun"
    ]

    assert droit_commun[
        "movable_by_standard_aod"
    ].all()


def test_carriere_longue_is_separate():
    result = classify_retirement_groups(
        sample_groups()
    )

    racl = result.loc[
        result["group_code"]
        == "carriere_longue"
    ]

    assert not racl[
        "movable_by_standard_aod"
    ].any()


def test_exposure_allocation_preserves_total():
    result = allocate_exposure_by_group(
        sample_exposure(),
        sample_groups(),
    )

    totals = (
        result
        .groupby("sex")[
            "allocated_exposed_effectifs"
        ]
        .sum()
    )

    assert totals.loc["F"] == pytest.approx(
        100
    )

    assert totals.loc["H"] == pytest.approx(
        200
    )


def test_movable_exposure_uses_standard_aod_groups_only():
    allocated = allocate_exposure_by_group(
        sample_exposure(),
        sample_groups(),
    )

    result = (
        compute_standard_aod_movable_exposure(
            allocated
        )
    )

    female = result.loc[
        result["sex"] == "F",
        "movable_exposed_effectifs",
    ].iloc[0]

    male = result.loc[
        result["sex"] == "H",
        "movable_exposed_effectifs",
    ].iloc[0]

    assert female == pytest.approx(75)
    assert male == pytest.approx(120)