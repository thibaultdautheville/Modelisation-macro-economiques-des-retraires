import pandas as pd

REQUIRED_LABOUR_RATE_COLUMNS = {
    "year",
    "age_group",
    "sex",
    "activity_rate",
    "employment_rate",
    "unemployment_rate",
    "unemployed_share_population",
    "inactive_share_population",
}


def validate_labour_rates(
    df: pd.DataFrame,
    tolerance: float = 0.01,
) -> None:
    missing = REQUIRED_LABOUR_RATE_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    if df.empty:
        raise ValueError(
            "La table des taux du marché du travail est vide."
        )

    if df.duplicated(["year", "age_group", "sex"]).any():
        raise ValueError(
            "Doublons année-tranche d'âge-sexe."
        )

    rate_columns = [
        "activity_rate",
        "employment_rate",
        "unemployment_rate",
        "unemployed_share_population",
        "inactive_share_population",
    ]

    for column in rate_columns:
        if not df[column].between(0, 1).all():
            raise ValueError(
                f"{column} doit être compris entre 0 et 1."
            )

    status_sum = (
        df["employment_rate"]
        + df["unemployed_share_population"]
        + df["inactive_share_population"]
    )

    if status_sum.sub(1).abs().max() > tolerance:
        raise ValueError(
            "Les parts emploi, chômage et inactivité "
            "ne somment pas à 1."
        )

    active_share = (
        df["employment_rate"]
        + df["unemployed_share_population"]
    )

    if active_share.sub(
        df["activity_rate"]
    ).abs().max() > tolerance:
        raise ValueError(
            "Le taux d'activité est incohérent avec "
            "les parts emploi et chômage."
        )

from src.activity import parse_age_group

def compute_baseline_labour_status(
    df: pd.DataFrame,
    population_col: str = "population",
    activity_rate_col: str = "activity_rate",
    unemployment_rate_col: str = "unemployment_rate",
) -> pd.DataFrame:
    required = {
        population_col,
        activity_rate_col,
        unemployment_rate_col,
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    if (df[population_col] < 0).any():
        raise ValueError(
            "Population cannot be negative"
        )

    for column in [
        activity_rate_col,
        unemployment_rate_col,
    ]:
        if not df[column].between(0, 1).all():
            raise ValueError(
                f"{column} must be between 0 and 1"
            )

    out = df.copy()

    out["labour_force_baseline"] = (
        out[population_col]
        * out[activity_rate_col]
    )

    out["unemployment_baseline"] = (
        out["labour_force_baseline"]
        * out[unemployment_rate_col]
    )

    out["employment_baseline"] = (
        out["labour_force_baseline"]
        - out["unemployment_baseline"]
    )

    out["inactive_baseline"] = (
        out[population_col]
        - out["labour_force_baseline"]
    )

    return out


def simulate_reform_absorption(
    inflows: pd.DataFrame,
    absorption_rate: float,
) -> pd.DataFrame:
    required = {
        "year",
        "new_active_reform",
    }

    missing = required - set(inflows.columns)

    if missing:
        raise ValueError(
            f"Missing reform-flow columns: {sorted(missing)}"
        )

    if not 0 <= absorption_rate <= 1:
        raise ValueError(
            "absorption_rate must be between 0 and 1"
        )

    if inflows["year"].duplicated().any():
        raise ValueError(
            "One reform-flow row per year is required"
        )

    if (inflows["new_active_reform"] < 0).any():
        raise ValueError(
            "new_active_reform cannot be negative"
        )

    ordered = (
        inflows
        .sort_values("year")
        .reset_index(drop=True)
        .copy()
    )

    employment_stock = 0.0
    unemployment_stock = 0.0
    results = []

    for row in ordered.itertuples(index=False):
        new_active = float(
            row.new_active_reform
        )

        available = (
            unemployment_stock
            + new_active
        )

        newly_absorbed = (
            absorption_rate
            * available
        )

        employment_stock += newly_absorbed

        unemployment_stock = (
            available
            - newly_absorbed
        )

        results.append(
            {
                "year": int(row.year),
                "new_active_reform": new_active,
                "absorption_rate": absorption_rate,
                "newly_absorbed_employment": newly_absorbed,
                "delta_employment_reform": employment_stock,
                "delta_unemployment_reform": unemployment_stock,
                "delta_labour_force_reform":
                    employment_stock
                    + unemployment_stock,
            }
        )

    return pd.DataFrame(results)


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

        for age in range(
            start_age,
            end_age + 1,
        ):
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

    # TRAVAIL_2025 s'arrête à 60-64 ans.
    # Hypothèse V1 : pour 65-69 ans, reprise du taux
    # observé des 60-64 ans du même sexe.
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
                    "unemployment_rate_2025":
                        rate,
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

    if not profile[
        "unemployment_rate_2025"
    ].between(0, 1).all():
        raise ValueError(
            "Taux de chômage 2025 hors de [0,1]"
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
    """
    Construit emploi et chômage de référence.

    Le profil relatif âge-sexe de chômage est ancré sur 2025.
    Chaque année, ce profil est multiplié par un coefficient
    commun afin que le taux de chômage agrégé du périmètre
    modélisé corresponde exactement à la trajectoire macro COR.

    Cette calibration est une hypothèse de modélisation :
    les taux âge-sexe projetés ne sont pas des projections COR.
    """
    required_activity = {
        "year",
        "age",
        "sex",
        "population",
        "activity_rate_baseline",
        "labour_force_baseline",
    }

    missing = (
        required_activity
        - set(activity_baseline.columns)
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes dans l'activité de référence : "
            f"{sorted(missing)}"
        )

    required_macro = {
        "year",
        macro_rate_col,
    }

    missing_macro = (
        required_macro
        - set(macro_baseline.columns)
    )

    if missing_macro:
        raise ValueError(
            "Colonnes macroéconomiques manquantes : "
            f"{sorted(missing_macro)}"
        )

    macro = macro_baseline[
        [
            "year",
            macro_rate_col,
        ]
    ].copy()

    if macro["year"].duplicated().any():
        raise ValueError(
            "Une seule cible de chômage par année est requise"
        )

    if not macro[
        macro_rate_col
    ].between(0, 1).all():
        raise ValueError(
            "La cible macro de chômage doit être comprise entre 0 et 1"
        )

    profile = build_unemployment_profile_2025(
        labour_2025
    )

    out = activity_baseline.merge(
        profile,
        on=[
            "age",
            "sex",
        ],
        how="left",
        validate="many_to_one",
    )

    if out[
        "unemployment_rate_2025"
    ].isna().any():
        missing_cells = (
            out.loc[
                out[
                    "unemployment_rate_2025"
                ].isna(),
                ["age", "sex"],
            ]
            .drop_duplicates()
        )

        raise ValueError(
            "Profil de chômage manquant pour certaines "
            "cellules âge-sexe : "
            f"{missing_cells.to_dict('records')}"
        )

    out = out.merge(
        macro,
        on="year",
        how="left",
        validate="many_to_one",
    )

    if out[macro_rate_col].isna().any():
        raise ValueError(
            "Cible macro de chômage manquante "
            "pour certaines années"
        )

    out[
        "unemployment_rate_baseline"
    ] = 0.0

    out[
        "unemployment_calibration_factor"
    ] = 0.0

    for year, indexes in out.groupby(
        "year"
    ).groups.items():
        group = out.loc[indexes]

        labour_force = group[
            "labour_force_baseline"
        ]

        total_labour_force = (
            labour_force.sum()
        )

        if total_labour_force <= 0:
            raise ValueError(
                f"Population active nulle en {year}"
            )

        raw_rate = (
            (
                labour_force
                * group[
                    "unemployment_rate_2025"
                ]
            ).sum()
            / total_labour_force
        )

        target_rate = float(
            group[
                macro_rate_col
            ].iloc[0]
        )

        if raw_rate <= 0:
            raise ValueError(
                f"Profil de chômage nul en {year}"
            )

        factor = (
            target_rate / raw_rate
        )

        calibrated = (
            group[
                "unemployment_rate_2025"
            ]
            * factor
        )

        if (calibrated > 1).any():
            raise ValueError(
                "Le recalage produit un taux de chômage "
                f"supérieur à 100 % en {year}"
            )

        out.loc[
            indexes,
            "unemployment_rate_baseline",
        ] = calibrated

        out.loc[
            indexes,
            "unemployment_calibration_factor",
        ] = factor

    out[
        "unemployment_baseline"
    ] = (
        out["labour_force_baseline"]
        * out["unemployment_rate_baseline"]
    )

    out[
        "employment_baseline"
    ] = (
        out["labour_force_baseline"]
        - out["unemployment_baseline"]
    )

    out[
        "inactive_baseline"
    ] = (
        out["population"]
        - out["labour_force_baseline"]
    )

    out[
        "employment_rate_baseline"
    ] = (
        out["employment_baseline"]
        / out["population"]
    )

    out[
        "unemployed_share_population_baseline"
    ] = (
        out["unemployment_baseline"]
        / out["population"]
    )

    annual = (
        out
        .groupby("year", as_index=False)
        .agg(
            labour_force=(
                "labour_force_baseline",
                "sum",
            ),
            unemployment=(
                "unemployment_baseline",
                "sum",
            ),
            target=(
                macro_rate_col,
                "first",
            ),
        )
    )

    annual[
        "realized_rate"
    ] = (
        annual["unemployment"]
        / annual["labour_force"]
    )

    max_gap = (
        annual["realized_rate"]
        - annual["target"]
    ).abs().max()

    if max_gap > 1e-10:
        raise ValueError(
            "La calibration ne reproduit pas exactement "
            "la trajectoire macro de chômage"
        )

    return (
        out
        .sort_values(
            [
                "year",
                "age",
                "sex",
            ]
        )
        .reset_index(drop=True)
    )



