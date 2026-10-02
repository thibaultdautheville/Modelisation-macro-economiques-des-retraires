import numpy as np
import pandas as pd


SENIOR_AGE_GROUPS = {
    "55-59",
    "60-64",
    "65-69",
}

NON_SENIOR_AGE_GROUPS = {
    "15-19",
    "20-24",
    "25-29",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
}

MODEL_SEX = {
    "F",
    "H",
}


def parse_age_group(age_group: str) -> tuple[int, int]:
    try:
        start, end = age_group.split("-")
        start_age = int(start)
        end_age = int(end)
    except (AttributeError, ValueError) as exc:
        raise ValueError(
            f"Tranche d'âge invalide : {age_group}"
        ) from exc

    if start_age > end_age:
        raise ValueError(
            f"Tranche d'âge incohérente : {age_group}"
        )

    return start_age, end_age


def validate_activity_sources(
    senior_rates: pd.DataFrame,
    labour_2025: pd.DataFrame,
) -> None:
    senior_required = {
        "year",
        "age_group",
        "sex",
        "activity_rate_insee2023",
        "activity_rate_cor2026_anchor",
    }

    labour_required = {
        "year",
        "age_group",
        "sex",
        "activity_rate",
    }

    missing_senior = (
        senior_required - set(senior_rates.columns)
    )

    missing_labour = (
        labour_required - set(labour_2025.columns)
    )

    if missing_senior:
        raise ValueError(
            "Colonnes manquantes dans ACTIVITE_SENIORS : "
            f"{sorted(missing_senior)}"
        )

    if missing_labour:
        raise ValueError(
            "Colonnes manquantes dans TRAVAIL_2025 : "
            f"{sorted(missing_labour)}"
        )

    if senior_rates.empty:
        raise ValueError(
            "La table ACTIVITE_SENIORS est vide"
        )

    if labour_2025.empty:
        raise ValueError(
            "La table TRAVAIL_2025 est vide"
        )


def build_senior_activity_path(
    senior_rates: pd.DataFrame,
    anchor_years: tuple[int, ...] = (
        2025,
        2050,
        2070,
    ),
) -> pd.DataFrame:
    senior = senior_rates.loc[
        senior_rates["sex"].isin(MODEL_SEX)
        & senior_rates["age_group"].isin(
            SENIOR_AGE_GROUPS
        )
    ].copy()

    results = []

    for (
        age_group,
        sex,
    ), group in senior.groupby(
        ["age_group", "sex"]
    ):
        group = (
            group
            .sort_values("year")
            .copy()
        )

        anchors = group.loc[
            group["year"].isin(anchor_years)
            & group[
                "activity_rate_cor2026_anchor"
            ].notna()
        ].copy()

        observed_anchor_years = set(
            anchors["year"].astype(int)
        )

        missing_anchors = (
            set(anchor_years)
            - observed_anchor_years
        )

        if missing_anchors:
            raise ValueError(
                "Ancrages COR manquants pour "
                f"{age_group} / {sex} : "
                f"{sorted(missing_anchors)}"
            )

        anchors["calibration_gap"] = (
            anchors[
                "activity_rate_cor2026_anchor"
            ]
            - anchors[
                "activity_rate_insee2023"
            ]
        )

        interpolated_gap = np.interp(
            group["year"].to_numpy(),
            anchors["year"].to_numpy(),
            anchors[
                "calibration_gap"
            ].to_numpy(),
        )

        group["calibration_gap"] = (
            interpolated_gap
        )

        group["activity_rate_baseline"] = (
            group[
                "activity_rate_insee2023"
            ]
            + group["calibration_gap"]
        ).clip(
            lower=0,
            upper=1,
        )

        group["is_cor_anchor"] = (
            group["year"].isin(anchor_years)
        )

        group["method"] = (
            "insee_path_calibrated_to_cor_anchors"
        )

        results.append(group)

    out = pd.concat(
        results,
        ignore_index=True,
    )

    return out[
        [
            "year",
            "age_group",
            "sex",
            "activity_rate_insee2023",
            "activity_rate_cor2026_anchor",
            "calibration_gap",
            "activity_rate_baseline",
            "is_cor_anchor",
            "method",
        ]
    ]


def build_activity_group_path(
    senior_rates: pd.DataFrame,
    labour_2025: pd.DataFrame,
    start_year: int = 2026,
    end_year: int = 2070,
) -> pd.DataFrame:
    validate_activity_sources(
        senior_rates,
        labour_2025,
    )

    if start_year > end_year:
        raise ValueError(
            "L'année de début doit être "
            "antérieure ou égale à l'année de fin"
        )

    senior_path = build_senior_activity_path(
        senior_rates
    )

    senior_path = senior_path.loc[
        senior_path["year"].between(
            start_year,
            end_year,
        )
    ].copy()

    senior_out = senior_path[
        [
            "year",
            "age_group",
            "sex",
            "activity_rate_baseline",
            "method",
        ]
    ].copy()

    base_2025 = labour_2025.loc[
        (labour_2025["year"] == 2025)
        & labour_2025["sex"].isin(
            MODEL_SEX
        )
        & labour_2025[
            "age_group"
        ].isin(
            NON_SENIOR_AGE_GROUPS
        )
    ][
        [
            "age_group",
            "sex",
            "activity_rate",
        ]
    ].copy()

    years = pd.DataFrame(
        {
            "year": range(
                start_year,
                end_year + 1,
            )
        }
    )

    base_2025["_key"] = 1
    years["_key"] = 1

    non_senior = (
        base_2025
        .merge(
            years,
            on="_key",
        )
        .drop(
            columns="_key",
        )
        .rename(
            columns={
                "activity_rate":
                    "activity_rate_baseline"
            }
        )
    )

    non_senior["method"] = (
        "observed_2025_rate_held_constant"
    )

    non_senior = non_senior[
        [
            "year",
            "age_group",
            "sex",
            "activity_rate_baseline",
            "method",
        ]
    ]

    out = pd.concat(
        [
            non_senior,
            senior_out,
        ],
        ignore_index=True,
    )

    if out.duplicated(
        [
            "year",
            "age_group",
            "sex",
        ]
    ).any():
        raise ValueError(
            "Doublons dans la trajectoire "
            "des taux d'activité"
        )

    return (
        out
        .sort_values(
            [
                "year",
                "age_group",
                "sex",
            ]
        )
        .reset_index(drop=True)
    )


def expand_activity_to_exact_ages(
    group_path: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for row in group_path.itertuples(
        index=False
    ):
        start_age, end_age = (
            parse_age_group(
                row.age_group
            )
        )

        for age in range(
            start_age,
            end_age + 1,
        ):
            rows.append(
                {
                    "year": int(row.year),
                    "age": age,
                    "age_group":
                        row.age_group,
                    "sex": row.sex,
                    "activity_rate_baseline":
                        float(
                            row.activity_rate_baseline
                        ),
                    "method":
                        row.method,
                }
            )

    out = pd.DataFrame(rows)

    if out.duplicated(
        [
            "year",
            "age",
            "sex",
        ]
    ).any():
        raise ValueError(
            "Doublons après passage "
            "aux âges exacts"
        )

    return out


def attach_demography(
    activity_exact: pd.DataFrame,
    demography: pd.DataFrame,
) -> pd.DataFrame:
    required_demography = {
        "year",
        "age",
        "sex",
        "population",
    }

    missing = (
        required_demography
        - set(demography.columns)
    )

    if missing:
        raise ValueError(
            "Colonnes démographiques "
            f"manquantes : {sorted(missing)}"
        )

    out = activity_exact.merge(
        demography[
            [
                "year",
                "age",
                "sex",
                "population",
            ]
        ],
        on=[
            "year",
            "age",
            "sex",
        ],
        how="left",
        validate="one_to_one",
    )

    if out["population"].isna().any():
        raise ValueError(
            "Certaines cellules âge-sexe-année "
            "n'ont pas de population associée"
        )

    out["labour_force_baseline"] = (
        out["population"]
        * out["activity_rate_baseline"]
    )

    return out


def build_activity_baseline(
    senior_rates: pd.DataFrame,
    labour_2025: pd.DataFrame,
    demography: pd.DataFrame,
    start_year: int = 2026,
    end_year: int = 2070,
) -> pd.DataFrame:
    grouped = build_activity_group_path(
        senior_rates=senior_rates,
        labour_2025=labour_2025,
        start_year=start_year,
        end_year=end_year,
    )

    exact = expand_activity_to_exact_ages(
        grouped
    )

    return attach_demography(
        exact,
        demography,
    )