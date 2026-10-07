import pandas as pd


def calibrate_displaced_liquidations(
    annual_delay: pd.DataFrame,
    movable_reference: pd.DataFrame,
    steady_state_intensity: float = 144.0,
    reference_year: int = 2024,
) -> pd.DataFrame:
    """
    Convertit l'intensité juridique annuelle du relèvement
    de l'AOD en nombre estimé de liquidations déplacées.

    Calibration V1 :
    - la masse déplaçable observée en année de référence
      correspond au plein effet annuel ;
    - le plein effet d'un relèvement uniforme de 12 mois
      correspond à 144 cohortes-mois par année ;
    - les années de montée en charge sont pondérées
      par leur intensité juridique relative.

    Cette méthode ne constitue pas une projection CNAV
    officielle. Elle ne tient pas encore compte de
    l'évolution future de la taille des générations.
    """
    required_delay = {
        "year",
        "cohort_months_delayed",
    }

    missing_delay = (
        required_delay
        - set(annual_delay.columns)
    )

    if missing_delay:
        raise ValueError(
            "Colonnes manquantes dans le calendrier annuel : "
            f"{sorted(missing_delay)}"
        )

    required_reference = {
        "sex",
        "movable_exposed_effectifs",
    }

    missing_reference = (
        required_reference
        - set(movable_reference.columns)
    )

    if missing_reference:
        raise ValueError(
            "Colonnes manquantes dans la calibration CNAV : "
            f"{sorted(missing_reference)}"
        )

    if steady_state_intensity <= 0:
        raise ValueError(
            "steady_state_intensity doit être strictement positif"
        )

    if (
        annual_delay["cohort_months_delayed"] < 0
    ).any():
        raise ValueError(
            "L'intensité juridique ne peut pas être négative"
        )

    if (
        movable_reference["movable_exposed_effectifs"] < 0
    ).any():
        raise ValueError(
            "La calibration CNAV ne peut pas être négative"
        )

    annual = annual_delay.copy()

    annual["legal_intensity_factor"] = (
        annual["cohort_months_delayed"]
        / steady_state_intensity
    )

    if (
        annual["legal_intensity_factor"] > 1
    ).any():
        raise ValueError(
            "L'intensité juridique dépasse le régime permanent"
        )

    annual["_key"] = 1

    reference = movable_reference.copy()
    reference["_key"] = 1

    out = annual.merge(
        reference,
        on="_key",
        how="inner",
        validate="many_to_many",
    ).drop(
        columns="_key"
    )

    out["movable_liquidations"] = (
        out["movable_exposed_effectifs"]
        * out["legal_intensity_factor"]
    )

    out["reference_year"] = (
        reference_year
    )

    out["calibration_method"] = (
        "cnav_reference_scaled_by_legal_intensity"
    )

    return (
        out
        .sort_values(
            [
                "year",
                "sex",
            ]
        )
        .reset_index(drop=True)
    )


def aggregate_displaced_liquidations(
    displaced: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "year",
        "movable_liquidations",
    }

    missing = required - set(
        displaced.columns
    )

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    return (
        displaced
        .groupby(
            "year",
            as_index=False,
        )
        .agg(
            movable_liquidations=(
                "movable_liquidations",
                "sum",
            ),
            cohort_months_delayed=(
                "cohort_months_delayed",
                "first",
            ),
            legal_intensity_factor=(
                "legal_intensity_factor",
                "first",
            ),
        )
    )