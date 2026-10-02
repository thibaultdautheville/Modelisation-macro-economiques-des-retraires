import numpy as np
import pandas as pd
import pytest

from src.activity import (
    build_activity_group_path,
    build_senior_activity_path,
    expand_activity_to_exact_ages,
    parse_age_group,
)


def sample_senior_rates():
    rows = []

    for year in [
        2025,
        2026,
        2050,
        2070,
    ]:
        insee = {
            2025: 0.50,
            2026: 0.52,
            2050: 0.60,
            2070: 0.65,
        }[year]

        cor = {
            2025: 0.51,
            2050: 0.58,
            2070: 0.62,
        }.get(
            year,
            np.nan,
        )

        for sex in ["F", "H"]:
            rows.append(
                {
                    "year": year,
                    "age_group": "55-59",
                    "sex": sex,
                    "activity_rate_insee2023":
                        insee,
                    "activity_rate_cor2026_anchor":
                        cor,
                }
            )

    return pd.DataFrame(rows)


def sample_labour_2025():
    return pd.DataFrame(
        {
            "year": [2025, 2025],
            "age_group": [
                "50-54",
                "50-54",
            ],
            "sex": [
                "F",
                "H",
            ],
            "activity_rate": [
                0.85,
                0.90,
            ],
        }
    )


def test_parse_age_group():
    assert parse_age_group(
        "55-59"
    ) == (
        55,
        59,
    )


def test_senior_path_hits_cor_anchors():
    result = build_senior_activity_path(
        sample_senior_rates(),
        anchor_years=(
            2025,
            2050,
            2070,
        ),
    )

    anchors = result.loc[
        result["is_cor_anchor"]
    ]

    assert np.allclose(
        anchors[
            "activity_rate_baseline"
        ],
        anchors[
            "activity_rate_cor2026_anchor"
        ],
    )


def test_calibration_gap_is_interpolated():
    result = build_senior_activity_path(
        sample_senior_rates()
    )

    row = result.loc[
        (result["year"] == 2026)
        & (result["sex"] == "F")
    ].iloc[0]

    assert (
        row["activity_rate_baseline"]
        != row["activity_rate_insee2023"]
    )


def test_non_senior_2025_rate_is_held_constant():
    senior = sample_senior_rates()

    labour = sample_labour_2025()

    result = build_activity_group_path(
        senior,
        labour,
        start_year=2026,
        end_year=2027,
    )

    rows = result.loc[
        (result["age_group"] == "50-54")
        & (result["sex"] == "F")
    ]

    assert rows[
        "activity_rate_baseline"
    ].tolist() == [
        0.85,
        0.85,
    ]


def test_exact_age_expansion():
    grouped = pd.DataFrame(
        {
            "year": [2026],
            "age_group": ["55-59"],
            "sex": ["F"],
            "activity_rate_baseline": [0.80],
            "method": ["test"],
        }
    )

    result = expand_activity_to_exact_ages(
        grouped
    )

    assert result[
        "age"
    ].tolist() == [
        55,
        56,
        57,
        58,
        59,
    ]

    assert (
        result[
            "activity_rate_baseline"
        ] == 0.80
    ).all()


def test_total_sex_is_not_used_in_engine():
    df = sample_senior_rates()

    extra = df.iloc[[0]].copy()
    extra["sex"] = "T"

    result = build_senior_activity_path(
        pd.concat(
            [df, extra],
            ignore_index=True,
        )
    )

    assert set(
        result["sex"].unique()
    ) == {
        "F",
        "H",
    }


def test_missing_anchor_is_rejected():
    df = sample_senior_rates()

    mask = (
        (df["year"] == 2050)
        & (df["sex"] == "F")
    )

    df.loc[
        mask,
        "activity_rate_cor2026_anchor",
    ] = np.nan

    with pytest.raises(ValueError):
        build_senior_activity_path(df)