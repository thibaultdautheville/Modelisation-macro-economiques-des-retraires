import pandas as pd


def build_pre_retirement_status_rates(
    labour_2025: pd.DataFrame,
    age_group: str = "60-64",
) -> pd.DataFrame:
    """
    Construit les parts de statut pré-retraite par sexe
    à partir des données de marché du travail 2025.

    Calibration provisoire V1 :
    le groupe 60-64 ans sert de proxy au statut des personnes
    concernées par un report de liquidation autour de l'AOD.

    Les trois états sont :
    - emploi ;
    - chômage ;
    - inactivité.

    Cette distribution est une approximation agrégée et
    ne constitue pas une observation individuelle du statut
    juste avant liquidation.
    """
    required = {
        "sex",
        "age_group",
        "employment_rate",
        "unemployed_share_population",
        "inactive_share_population",
    }

    missing = required - set(
        labour_2025.columns
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes : "
            f"{sorted(missing)}"
        )

    out = labour_2025.loc[
        (labour_2025["sex"].isin(["F", "H"]))
        & (labour_2025["age_group"] == age_group)
    ].copy()

    if out.empty:
        raise ValueError(
            f"Aucune donnée disponible pour {age_group}."
        )

    out[
        "pre_retirement_employment_share"
    ] = out[
        "employment_rate"
    ]

    out[
        "pre_retirement_unemployment_share"
    ] = out[
        "unemployed_share_population"
    ]

    out[
        "pre_retirement_inactivity_share"
    ] = out[
        "inactive_share_population"
    ]

    total = (
        out["pre_retirement_employment_share"]
        + out["pre_retirement_unemployment_share"]
        + out["pre_retirement_inactivity_share"]
    )

    if not ((total - 1.0).abs() < 1e-10).all():
        raise ValueError(
            "Les parts de statut ne somment pas à 1."
        )

    out[
        "calibration_status"
    ] = "provisional_calibration"

    out[
        "status_method"
    ] = "labour_force_survey_2025_age_60_64_proxy"

    return out[
        [
            "sex",
            "pre_retirement_employment_share",
            "pre_retirement_unemployment_share",
            "pre_retirement_inactivity_share",
            "calibration_status",
            "status_method",
        ]
    ].reset_index(drop=True)


def apply_pre_retirement_status(
    delayed_stock_by_sex: pd.DataFrame,
    status_rates: pd.DataFrame,
) -> pd.DataFrame:
    """
    Ventile le stock de personnes dont la liquidation est
    retardée selon leur statut pré-retraite approximatif.
    """
    required_stock = {
        "year",
        "sex",
        "delayed_stock_persons",
    }

    missing = required_stock - set(
        delayed_stock_by_sex.columns
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes dans le stock : "
            f"{sorted(missing)}"
        )

    out = delayed_stock_by_sex.merge(
        status_rates,
        on="sex",
        how="left",
        validate="many_to_one",
    )

    if out[
        "pre_retirement_employment_share"
    ].isna().any():
        raise ValueError(
            "Taux de statut manquant pour certains sexes."
        )

    out[
        "previously_employed"
    ] = (
        out["delayed_stock_persons"]
        * out[
            "pre_retirement_employment_share"
        ]
    )

    out[
        "previously_unemployed"
    ] = (
        out["delayed_stock_persons"]
        * out[
            "pre_retirement_unemployment_share"
        ]
    )

    out[
        "previously_inactive"
    ] = (
        out["delayed_stock_persons"]
        * out[
            "pre_retirement_inactivity_share"
        ]
    )

    return out