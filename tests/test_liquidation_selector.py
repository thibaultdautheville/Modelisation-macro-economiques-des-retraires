
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import PROCESSED_DIR
from src.cnav_crossed import load_observed_cnav_cross

from src.liquidation import build_age_distribution


from src.liquidation_selector import (
    select_liquidation_distribution,
)


from src.liquidation import (
    build_age_distribution,
    build_group_distribution,
)

from src.liquidation_reference import (
    build_reference_liquidation_distribution,
    aggregate_reference_distribution,
    compute_reference_aod_exposure,
)


CROSS_PATH = Path(
    "data/derived/cnav_age_group_2024.csv"
)


@pytest.fixture(scope="module")
def inputs():
    age = build_age_distribution(
        pd.read_parquet(
            PROCESSED_DIR / "liquidation_age_counts.parquet"
        )
    )

    groups = build_group_distribution(
        pd.read_parquet(
            PROCESSED_DIR / "liquidation_groups.parquet"
        )
    )

    return age, groups


def test_historical_method_unchanged(inputs):
    age, groups = inputs

    original = build_reference_liquidation_distribution(
        age,
        groups,
        reference_aod_months=768,
        observed_standard_age_floor_months=744,
    )

    selected = select_liquidation_distribution(
        age,
        groups,
        method="independance",
        reference_aod_months=768,
        observed_standard_age_floor_months=744,
    )

    pd.testing.assert_frame_equal(
        original,
        selected,
    )


def test_observed_method_preserves_effectifs(inputs):
    age, groups = inputs

    selected = select_liquidation_distribution(
        age,
        groups,
        method="cnav_observee",
        observed_cross_path=CROSS_PATH,
    )

    source = load_observed_cnav_cross(CROSS_PATH)
    source = source.loc[
        source["sex"].isin(["F", "H"])
        & ~source["open_age_class"]
    ]

    assert selected["allocated_effectifs"].sum() == pytest.approx(
        source["effectifs"].sum()
    )


def test_observed_method_preserves_exceptions(inputs):
    age, groups = inputs

    result = select_liquidation_distribution(
        age,
        groups,
        method="cnav_observee",
        observed_cross_path=CROSS_PATH,
    )

    exceptions = result.loc[
        result["group_code"].ne("droit_commun")
    ]

    assert np.allclose(
        exceptions["age_numeric"],
        exceptions["reference_age_numeric"],
    )


def test_observed_method_moves_only_standard_departures(inputs):
    age, groups = inputs

    result = select_liquidation_distribution(
        age,
        groups,
        method="cnav_observee",
        observed_cross_path=CROSS_PATH,
    )

    shifted = result.loc[
        result["shifted_to_reference_aod"]
    ]

    assert shifted["group_code"].eq("droit_commun").all()
    assert shifted["age_numeric"].between(
        62, 63
    ).all()
    assert shifted["reference_age_numeric"].eq(64).all()


def test_observed_reference_is_usable_for_exposure(inputs):
    age, groups = inputs

    result = select_liquidation_distribution(
        age,
        groups,
        method="cnav_observee",
        observed_cross_path=CROSS_PATH,
    )

    reference = aggregate_reference_distribution(result)

    exposure = compute_reference_aod_exposure(
        reference,
        baseline_aod_months=768,
        reform_aod_months=780,
    )

    assert set(exposure["sex"]) == {"F", "H"}
    assert (exposure["movable_exposed_effectifs"] > 0).all()


def test_observed_method_requires_source(inputs):
    age, groups = inputs

    with pytest.raises(ValueError):
        select_liquidation_distribution(
            age,
            groups,
            method="cnav_observee",
        )


def test_invalid_method_rejected(inputs):
    age, groups = inputs

    with pytest.raises(ValueError):
        select_liquidation_distribution(
            age,
            groups,
            method="inconnue",
        )


def test_observed_method_rejects_inconsistent_ages(inputs):
    age, groups = inputs

    corrupted = age.copy()

    mask = (
        corrupted["sex"].eq("F")
        & corrupted["age_numeric"].eq(64)
    )

    corrupted.loc[mask, "effectifs"] += 100

    with pytest.raises(ValueError):
        select_liquidation_distribution(
            corrupted,
            groups,
            method="cnav_observee",
            observed_cross_path=CROSS_PATH,
        )
