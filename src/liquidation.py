import numpy as np
import pandas as pd


VALID_SEX = {"F", "H"}


def validate_liquidation_age_counts(
    df: pd.DataFrame,
) -> None:
    required = {
        "year",
        "sex",
        "age_numeric",
        "effectifs",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Colonnes manquantes dans CNAV_LIQ_AGE : "
            f"{sorted(missing)}"
        )

    if df.empty:
        raise ValueError(
            "CNAV_LIQ_AGE est vide"
        )

    if (df["effectifs"] < 0).any():
        raise ValueError(
            "Les effectifs de liquidation "
            "ne peuvent pas être négatifs"
        )

    if (df["age_numeric"] < 0).any():
        raise ValueError(
            "L'âge de liquidation "
            "ne peut pas être négatif"
        )


def validate_liquidation_groups(
    df: pd.DataFrame,
) -> None:
    required = {
        "year",
        "sex",
        "group_code",
        "effectifs",
        "share_total",
        "avg_monthly_pension_eur",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Colonnes manquantes dans CNAV_LIQ_GROUP : "
            f"{sorted(missing)}"
        )

    if df.empty:
        raise ValueError(
            "CNAV_LIQ_GROUP est vide"
        )

    if (df["effectifs"] < 0).any():
        raise ValueError(
            "Les effectifs par groupe "
            "ne peuvent pas être négatifs"
        )

    if not df["share_total"].between(0, 1).all():
        raise ValueError(
            "Les parts de groupes doivent "
            "être comprises entre 0 et 1"
        )


def build_age_distribution(
    df: pd.DataFrame,
    year: int | None = None,
) -> pd.DataFrame:
    validate_liquidation_age_counts(df)

    if year is None:
        year = int(df["year"].max())

    selected = df.loc[
        (df["year"] == year)
        & df["sex"].isin(VALID_SEX)
    ].copy()

    if selected.empty:
        raise ValueError(
            f"Aucune liquidation disponible pour {year}"
        )

    grouped = (
        selected
        .groupby(
            ["year", "sex", "age_numeric"],
            as_index=False,
        )
        .agg(
            effectifs=("effectifs", "sum")
        )
    )

    totals = (
        grouped
        .groupby("sex")["effectifs"]
        .transform("sum")
    )

    if (totals <= 0).any():
        raise ValueError(
            "Effectifs totaux nuls pour un sexe"
        )

    grouped[
        "share_within_sex"
    ] = (
        grouped["effectifs"]
        / totals
    )

    return grouped.sort_values(
        ["sex", "age_numeric"]
    ).reset_index(drop=True)


def build_group_distribution(
    df: pd.DataFrame,
    year: int | None = None,
) -> pd.DataFrame:
    validate_liquidation_groups(df)

    if year is None:
        year = int(df["year"].max())

    selected = df.loc[
        (df["year"] == year)
        & df["sex"].isin(VALID_SEX)
    ].copy()

    if selected.empty:
        raise ValueError(
            f"Aucun groupe disponible pour {year}"
        )

    totals = (
        selected
        .groupby("sex")["effectifs"]
        .transform("sum")
    )

    selected[
        "share_within_sex_recomputed"
    ] = (
        selected["effectifs"]
        / totals
    )

    selected[
        "share_gap_vs_source"
    ] = (
        selected[
            "share_within_sex_recomputed"
        ]
        - selected["share_total"]
    )

    return selected.sort_values(
        ["sex", "group_code"]
    ).reset_index(drop=True)


def expand_age_distribution_to_months(
    age_distribution: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "year",
        "sex",
        "age_numeric",
        "effectifs",
        "share_within_sex",
    }

    missing = required - set(
        age_distribution.columns
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes pour "
            "la mensualisation : "
            f"{sorted(missing)}"
        )

    repeated = (
        age_distribution
        .loc[
            age_distribution.index.repeat(12)
        ]
        .reset_index(drop=True)
    )

    repeated[
        "month_within_age"
    ] = np.tile(
        np.arange(12),
        len(age_distribution),
    )

    repeated[
        "age_months"
    ] = (
        repeated["age_numeric"].astype(int)
        * 12
        + repeated["month_within_age"]
    )

    repeated[
        "effectifs_monthly"
    ] = (
        repeated["effectifs"]
        / 12.0
    )

    repeated[
        "share_monthly"
    ] = (
        repeated["share_within_sex"]
        / 12.0
    )

    repeated[
        "monthly_split_method"
    ] = "uniform_within_integer_age"

    return repeated


def compute_potentially_exposed_liquidations(
    monthly_distribution: pd.DataFrame,
    baseline_aod_months: int,
    reform_aod_months: int,
) -> pd.DataFrame:
    """
    Calcule la masse de liquidations située entre
    l'ancien et le nouvel AOD.

    Il s'agit d'une masse POTENTIELLEMENT exposée,
    et non encore du nombre final de liquidations
    déplacées.

    Les départs anticipés, carrières longues,
    inaptitude, handicap, etc. ne peuvent pas être
    distingués avec la seule distribution marginale
    CNAV par âge.
    """
    if reform_aod_months < baseline_aod_months:
        raise ValueError(
            "Cette fonction V1 traite uniquement "
            "un relèvement de l'AOD"
        )

    required = {
        "sex",
        "age_months",
        "effectifs_monthly",
        "share_monthly",
    }

    missing = required - set(
        monthly_distribution.columns
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes : "
            f"{sorted(missing)}"
        )

    exposed = monthly_distribution.loc[
        monthly_distribution[
            "age_months"
        ].between(
            baseline_aod_months,
            reform_aod_months - 1,
        )
    ].copy()

    if exposed.empty:
        return pd.DataFrame(
            columns=[
                "sex",
                "potential_exposed_effectifs",
                "potential_exposed_share",
            ]
        )

    result = (
        exposed
        .groupby(
            "sex",
            as_index=False,
        )
        .agg(
            potential_exposed_effectifs=(
                "effectifs_monthly",
                "sum",
            ),
            potential_exposed_share=(
                "share_monthly",
                "sum",
            ),
        )
    )

    return result


def build_liquidation_diagnostics(
    age_counts: pd.DataFrame,
    group_counts: pd.DataFrame,
    year: int | None = None,
) -> dict:
    age_distribution = (
        build_age_distribution(
            age_counts,
            year=year,
        )
    )

    group_distribution = (
        build_group_distribution(
            group_counts,
            year=year,
        )
    )

    monthly_distribution = (
        expand_age_distribution_to_months(
            age_distribution
        )
    )

    return {
        "age_distribution":
            age_distribution,
        "group_distribution":
            group_distribution,
        "monthly_distribution":
            monthly_distribution,
    }