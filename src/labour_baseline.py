import pandas as pd

from src.activity import parse_age_group


def build_unemployment_profile_2025(
    labour_2025: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "year",
        "age_group",
        "sex",
        "unemployment_rate",
    }

    missing = required - set(labour_2025.columns)

    if missing:
        raise ValueError(
            "Colonnes manquantes pour le profil de chômage : "
            f"{sorted(missing)}"
        )

    base = labour_2025.loc[
        (labour_2025["year"] == 2025)
        & labour_2025["sex"].isin(["F", "H"])
    ].copy()

    if base.empty:
        raise ValueError(
            "Aucune donnée de chômage F/H pour 2025"
        )

    rows = []

    for row in base.itertuples(index=False):
        start_age, end_age = parse_age_group(
            row.age_group
        )

        for age in range(start_age, end_age + 1):
            rows.append(
                {
                    "age": age,
                    "sex": row.sex,
                    "unemployment_rate_2025":
                        float(row.unemployment_rate),
                    "unemployment_profile_method":
                        "observed_2025_age_group",
                }
            )

    profile = pd.DataFrame(rows)

    for sex in ["F", "H"]:
        reference = profile.loc[
            (profile["age"] == 64)
            & (profile["sex"] == sex)
        ]

        if len(reference) != 1:
            raise ValueError(
                f"Profil 60-64 introuvable pour le sexe {sex}"
            )

        rate = float(
            reference.iloc[0][
                "unemployment_rate_2025"
            ]
        )

        for age in range(65, 70):
            rows.append(
                {
                    "age": age,
                    "sex": sex,
                    "unemployment_rate_2025": rate,
                    "unemployment_profile_method":
                        "proxy_60_64_for_65_69",
                }
            )

    profile = pd.DataFrame(rows)

    if profile.duplicated(
        ["age", "sex"]
    ).any():
        raise ValueError(
            "Doublons dans le profil âge-sexe de chômage"
        )

    return (
        profile
        .sort_values(["age", "sex"])
        .reset_index(drop=True)
    )


def build_baseline_employment(
    activity_baseline: pd.DataFrame,
    macro_baseline: pd.DataFrame,
    labour_2025: pd.DataFrame,
    macro_rate_col: str = "unemployment_rate_ref",
) -> pd.DataFrame:
    profile = build_unemployment_profile_2025(
        labour_2025
    )

    out = activity_baseline.merge(
        profile,
        on=["age", "sex"],
        how="left",
        validate="many_to_one",
    )

    if out[
        "unemployment_rate_2025"
    ].isna().any():
        raise ValueError(
            "Profil de chômage manquant pour certaines cellules"
        )

    macro = macro_baseline[
        ["year", macro_rate_col]
    ].copy()

    out = out.merge(
        macro,
        on="year",
        how="left",
        validate="many_to_one",
    )

    if out[macro_rate_col].isna().any():
        raise ValueError(
            "Cible macro de chômage manquante"
        )

    out["unemployment_rate_baseline"] = 0.0
    out["unemployment_calibration_factor"] = 0.0

    for year, indexes in out.groupby("year").groups.items():
        group = out.loc[indexes]

        labour_force = group[
            "labour_force_baseline"
        ]

        total_labour_force = labour_force.sum()

        raw_rate = (
            (
                labour_force
                * group["unemployment_rate_2025"]
            ).sum()
            / total_labour_force
        )

        target_rate = float(
            group[macro_rate_col].iloc[0]
        )

        factor = target_rate / raw_rate

        calibrated = (
            group["unemployment_rate_2025"]
            * factor
        )

        if (calibrated > 1).any():
            raise ValueError(
                f"Taux de chômage > 100 % en {year}"
            )

        out.loc[
            indexes,
            "unemployment_rate_baseline",
        ] = calibrated

        out.loc[
            indexes,
            "unemployment_calibration_factor",
        ] = factor

    out["unemployment_baseline"] = (
        out["labour_force_baseline"]
        * out["unemployment_rate_baseline"]
    )

    out["employment_baseline"] = (
        out["labour_force_baseline"]
        - out["unemployment_baseline"]
    )

    out["inactive_baseline"] = (
        out["population"]
        - out["labour_force_baseline"]
    )

    return (
        out
        .sort_values(["year", "age", "sex"])
        .reset_index(drop=True)
    )