import pandas as pd


def build_reference_aod_transition(
    legal_calendar: pd.DataFrame,
    floor_aod_months: int = 744,
    target_aod_months: int = 768,
) -> pd.DataFrame:
    """
    Construit un facteur annuel de montée en charge de l'AOD
    de référence.

    Le facteur mesure la part du chemin juridique parcouru
    entre un AOD plancher et l'AOD cible.

    Exemple :
    62 ans = 0
    63 ans = 0,50
    63 ans 6 mois = 0,75
    64 ans = 1

    Il s'agit d'une approximation de calibration transitoire :
    le facteur juridique ne constitue pas directement une
    probabilité observée de liquidation.
    """
    required = {
        "birth_year",
        "birth_month",
        "aod_months",
    }

    missing = required - set(
        legal_calendar.columns
    )

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    if target_aod_months <= floor_aod_months:
        raise ValueError(
            "L'AOD cible doit être supérieur "
            "à l'AOD plancher."
        )

    out = legal_calendar.copy()

    birth_index = (
        out["birth_year"] * 12
        + out["birth_month"] - 1
    )

    eligibility_index = (
        birth_index
        + out["aod_months"]
    )

    out["eligibility_year"] = (
        eligibility_index // 12
    ).astype(int)

    out["cohort_reference_maturity"] = (
        (
            out["aod_months"]
            - floor_aod_months
        )
        / (
            target_aod_months
            - floor_aod_months
        )
    ).clip(
        lower=0.0,
        upper=1.0,
    )

    transition = (
        out
        .groupby(
            "eligibility_year",
            as_index=False,
        )
        .agg(
            cohorts_total=(
                "birth_month",
                "size",
            ),
            mean_aod_months=(
                "aod_months",
                "mean",
            ),
            reference_maturity_factor=(
                "cohort_reference_maturity",
                "mean",
            ),
        )
        .rename(
            columns={
                "eligibility_year": "year",
            }
        )
    )

    transition[
        "transition_method"
    ] = (
        "linear_legal_progress_from_floor_to_target"
    )

    transition[
        "calibration_status"
    ] = (
        "provisional_calibration"
    )

    return transition


def apply_reference_transition(
    annual_stock: pd.DataFrame,
    transition: pd.DataFrame,
) -> pd.DataFrame:
    """
    Applique le facteur de montée en charge juridique
    au stock calculé sous un AOD stabilisé à 64 ans.

    Le niveau de long terme reste inchangé.
    Seule la phase transitoire est ajustée.
    """
    required_stock = {
        "year",
        "annual_average_delayed_stock",
    }

    missing_stock = (
        required_stock
        - set(annual_stock.columns)
    )

    if missing_stock:
        raise ValueError(
            "Colonnes manquantes dans le stock : "
            f"{sorted(missing_stock)}"
        )

    required_transition = {
        "year",
        "reference_maturity_factor",
    }

    missing_transition = (
        required_transition
        - set(transition.columns)
    )

    if missing_transition:
        raise ValueError(
            "Colonnes manquantes dans la transition : "
            f"{sorted(missing_transition)}"
        )

    out = annual_stock.merge(
        transition[
            [
                "year",
                "reference_maturity_factor",
            ]
        ],
        on="year",
        how="left",
    )

    out[
        "reference_maturity_factor"
    ] = (
        out[
            "reference_maturity_factor"
        ]
        .ffill()
        .fillna(0.0)
        .clip(0.0, 1.0)
    )

    out[
        "annual_average_delayed_stock_transition_adjusted"
    ] = (
        out[
            "annual_average_delayed_stock"
        ]
        * out[
            "reference_maturity_factor"
        ]
    )

    return out

