import pandas as pd


def _age_from_months(age_months: int) -> float:
    """
    Convertit un âge en mois en âge annuel.

    La calibration provisoire actuelle utilise des classes
    d'âge annuelles. Elle ne peut donc traiter que des âges
    correspondant à un nombre entier d'années.
    """
    if age_months <= 0:
        raise ValueError(
            "L'âge en mois doit être strictement positif."
        )

    if age_months % 12 != 0:
        raise ValueError(
            "La calibration provisoire par âge annuel "
            "nécessite un âge multiple de 12 mois."
        )

    return age_months / 12.0


def validate_reference_inputs(
    age_distribution: pd.DataFrame,
    group_distribution: pd.DataFrame,
) -> None:
    required_age = {
        "sex",
        "age_numeric",
        "effectifs",
    }

    required_groups = {
        "sex",
        "group_code",
        "share_within_sex_recomputed",
    }

    missing_age = (
        required_age
        - set(age_distribution.columns)
    )

    if missing_age:
        raise ValueError(
            "Colonnes manquantes dans la distribution par âge : "
            f"{sorted(missing_age)}"
        )

    missing_groups = (
        required_groups
        - set(group_distribution.columns)
    )

    if missing_groups:
        raise ValueError(
            "Colonnes manquantes dans la distribution par groupe : "
            f"{sorted(missing_groups)}"
        )

    if (
        age_distribution["effectifs"] < 0
    ).any():
        raise ValueError(
            "Les effectifs par âge ne peuvent pas être négatifs."
        )

    if (
        group_distribution[
            "share_within_sex_recomputed"
        ] < 0
    ).any():
        raise ValueError(
            "Les parts par groupe ne peuvent pas être négatives."
        )


def allocate_observed_age_by_group(
    age_distribution: pd.DataFrame,
    group_distribution: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construit une distribution provisoire âge x sexe x groupe.

    Hypothèse :
    indépendance entre âge de liquidation et groupe de départ,
    conditionnellement au sexe.

    Cette distribution est modélisée et non observée.
    """
    validate_reference_inputs(
        age_distribution,
        group_distribution,
    )

    ages = age_distribution.loc[
        age_distribution["sex"].isin(
            ["F", "H"]
        ),
        [
            "sex",
            "age_numeric",
            "effectifs",
        ],
    ].copy()

    groups = group_distribution.loc[
        group_distribution["sex"].isin(
            ["F", "H"]
        ),
        [
            "sex",
            "group_code",
            "share_within_sex_recomputed",
        ],
    ].copy()

    out = ages.merge(
        groups,
        on="sex",
        how="inner",
        validate="many_to_many",
    )

    out["allocated_effectifs"] = (
        out["effectifs"]
        * out[
            "share_within_sex_recomputed"
        ]
    )

    out["allocation_method"] = (
        "independence_age_group_conditional_on_sex"
    )

    return out


def build_reference_liquidation_distribution(
    age_distribution: pd.DataFrame,
    group_distribution: pd.DataFrame,
    reference_aod_months: int = 768,
    observed_standard_age_floor_months: int = 744,
) -> pd.DataFrame:
    """
    Reconstruit une distribution provisoire des liquidations
    sous un AOD de référence stabilisé.

    Convention provisoire :
    - AOD observé minimal pertinent = 62 ans par défaut ;
    - AOD de référence = 64 ans par défaut ;
    - seuls les départs classés "droit_commun" compris
      entre ces deux âges sont déplacés vers l'AOD
      de référence ;
    - les carrières longues, santé/inaptitude et autres
      catégories conservent leur âge observé.

    Cette méthode sert de calibration V1 transparente.
    Elle ne remplace pas une fonction de liquidation
    âge x sexe x catégorie issue de données individuelles
    ou de tableaux croisés DREES/CNAV.
    """
    reference_age = _age_from_months(
        reference_aod_months
    )

    observed_floor = _age_from_months(
        observed_standard_age_floor_months
    )

    if observed_floor > reference_age:
        raise ValueError(
            "L'âge plancher observé ne peut pas dépasser "
            "l'AOD de référence."
        )

    out = allocate_observed_age_by_group(
        age_distribution,
        group_distribution,
    )

    out["reference_age_numeric"] = (
        out["age_numeric"]
    )

    shift_mask = (
        (
            out["group_code"]
            == "droit_commun"
        )
        & (
            out["age_numeric"]
            >= observed_floor
        )
        & (
            out["age_numeric"]
            < reference_age
        )
    )

    out.loc[
        shift_mask,
        "reference_age_numeric",
    ] = reference_age

    out[
        "shifted_to_reference_aod"
    ] = shift_mask

    out[
        "reference_method"
    ] = (
        "provisional_standard_age_bunching"
    )

    out[
        "calibration_status"
    ] = (
        "provisional_calibration"
    )

    return out


def aggregate_reference_distribution(
    reference_detail: pd.DataFrame,
) -> pd.DataFrame:
    """
    Agrège la distribution contrefactuelle par
    sexe x âge de référence x catégorie.
    """
    required = {
        "sex",
        "reference_age_numeric",
        "group_code",
        "allocated_effectifs",
    }

    missing = (
        required
        - set(reference_detail.columns)
    )

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    return (
        reference_detail
        .groupby(
            [
                "sex",
                "reference_age_numeric",
                "group_code",
            ],
            as_index=False,
        )
        .agg(
            effectifs=(
                "allocated_effectifs",
                "sum",
            )
        )
        .sort_values(
            [
                "sex",
                "reference_age_numeric",
                "group_code",
            ]
        )
        .reset_index(drop=True)
    )


def compute_reference_aod_exposure(
    reference_distribution: pd.DataFrame,
    baseline_aod_months: int = 768,
    reform_aod_months: int = 780,
) -> pd.DataFrame:
    """
    Calcule la masse de départs de droit commun exposée
    au passage de l'AOD de référence à l'AOD réformé.

    Exemple :
    64 -> 65 ans :
    toutes les liquidations de droit commun situées
    dans [64 ; 65[ sont considérées exposées.
    """
    baseline_age = _age_from_months(
        baseline_aod_months
    )

    reform_age = _age_from_months(
        reform_aod_months
    )

    if reform_age < baseline_age:
        raise ValueError(
            "L'AOD reforme doit etre superieur ou egal "
            "à l'AOD de référence."
        )

    required = {
        "sex",
        "reference_age_numeric",
        "group_code",
        "effectifs",
    }

    missing = (
        required
        - set(reference_distribution.columns)
    )

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    if reform_age == baseline_age:
        sexes = sorted(set(reference_distribution["sex"]) & {"F", "H"})
        return pd.DataFrame({
            "sex": sexes,
            "movable_exposed_effectifs": 0.0,
            "calibration_status": "neutral",
            "exposure_method": "no_aod_change",
        })

    exposed = reference_distribution.loc[
        (
            reference_distribution[
                "group_code"
            ]
            == "droit_commun"
        )
        & (
            reference_distribution[
                "reference_age_numeric"
            ]
            >= baseline_age
        )
        & (
            reference_distribution[
                "reference_age_numeric"
            ]
            < reform_age
        )
    ].copy()

    result = (
        exposed
        .groupby(
            "sex",
            as_index=False,
        )
        .agg(
            movable_exposed_effectifs=(
                "effectifs",
                "sum",
            )
        )
    )

    result[
        "calibration_status"
    ] = (
        "provisional_calibration"
    )

    result[
        "exposure_method"
    ] = (
        "reference_liquidation_distribution"
    )

    return result