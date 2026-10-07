import pandas as pd
import pytest

from src.liquidation import (
    build_age_distribution,
    build_group_distribution,
    compute_potentially_exposed_liquidations,
    expand_age_distribution_to_months,
)


def sample_age_counts():
    return pd.DataFrame(
        {
            "year": [
                2024,
                2024,
                2024,
                2024,
            ],
            "sex": [
                "F",
                "F",
                "H",
                "H",
            ],
            "age_numeric": [
                63,
                64,
                63,
                64,
            ],
            "effectifs": [
                120,
                80,
                90,
                110,
            ],
        }
    )


def sample_groups():
    return pd.DataFrame(
        {
            "year": [
                2024,
                2024,
                2024,
                2024,
            ],
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
            "effectifs": [
                160,
                40,
                150,
                50,
            ],
            "share_total": [
                0.8,
                0.2,
                0.75,
                0.25,
            ],
            "avg_monthly_pension_eur": [
                900,
                1100,
                950,
                1150,
            ],
        }
    )


def test_age_distribution_sums_to_one():
    result = build_age_distribution(
        sample_age_counts()
    )

    sums = (
        result
        .groupby("sex")[
            "share_within_sex"
        ]
        .sum()
    )

    assert sums.round(12).tolist() == [
        1.0,
        1.0,
    ]


def test_group_distribution_recomputed():
    result = build_group_distribution(
        sample_groups()
    )

    sums = (
        result
        .groupby("sex")[
            "share_within_sex_recomputed"
        ]
        .sum()
    )

    assert sums.round(12).tolist() == [
        1.0,
        1.0,
    ]


def test_monthly_expansion_preserves_effectifs():
    annual = build_age_distribution(
        sample_age_counts()
    )

    monthly = (
        expand_age_distribution_to_months(
            annual
        )
    )

    assert len(monthly) == len(annual) * 12

    assert abs(
        monthly["effectifs_monthly"].sum()
        - annual["effectifs"].sum()
    ) < 1e-12


def test_monthly_expansion_preserves_shares():
    annual = build_age_distribution(
        sample_age_counts()
    )

    monthly = (
        expand_age_distribution_to_months(
            annual
        )
    )

    shares = (
        monthly
        .groupby("sex")[
            "share_monthly"
        ]
        .sum()
    )

    assert shares.round(12).tolist() == [
        1.0,
        1.0,
    ]


def test_potential_exposure_for_six_month_shift():
    annual = build_age_distribution(
        sample_age_counts()
    )

    monthly = (
        expand_age_distribution_to_months(
            annual
        )
    )

    result = (
        compute_potentially_exposed_liquidations(
            monthly,
            baseline_aod_months=63 * 12,
            reform_aod_months=63 * 12 + 6,
        )
    )

    female = result.loc[
        result["sex"] == "F"
    ].iloc[0]

    assert female[
        "potential_exposed_effectifs"
    ] == pytest.approx(60.0)

    assert female[
        "potential_exposed_share"
    ] == pytest.approx(0.30)


def test_lower_reform_aod_rejected():
    annual = build_age_distribution(
        sample_age_counts()
    )

    monthly = (
        expand_age_distribution_to_months(
            annual
        )
    )

    with pytest.raises(ValueError):
        compute_potentially_exposed_liquidations(
            monthly,
            baseline_aod_months=768,
            reform_aod_months=756,
        )