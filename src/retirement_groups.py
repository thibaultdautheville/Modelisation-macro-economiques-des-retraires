import pandas as pd


GROUP_TREATMENT = {
    "droit_commun": {
        "treatment": "affected",
        "label_fr": "Droit commun",
        "movable_by_standard_aod": True,
    },
    "carriere_longue": {
        "treatment": "separate",
        "label_fr": "Carrière longue",
        "movable_by_standard_aod": False,
    },
    "sante_invalidite_inaptitude": {
        "treatment": "protected",
        "label_fr": "Santé, invalidité et inaptitude",
        "movable_by_standard_aod": False,
    },
    "autres": {
        "treatment": "separate",
        "label_fr": "Autres départs",
        "movable_by_standard_aod": False,
    },
}


def validate_group_codes(
    group_distribution: pd.DataFrame,
) -> None:
    required = {
        "sex",
        "group_code",
        "share_within_sex_recomputed",
    }

    missing = required - set(
        group_distribution.columns
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes pour les groupes de départ : "
            f"{sorted(missing)}"
        )

    unknown = (
        set(group_distribution["group_code"])
        - set(GROUP_TREATMENT)
    )

    if unknown:
        raise ValueError(
            "Groupes de départ non paramétrés : "
            f"{sorted(unknown)}"
        )


def classify_retirement_groups(
    group_distribution: pd.DataFrame,
) -> pd.DataFrame:
    validate_group_codes(
        group_distribution
    )

    out = group_distribution.copy()

    out["treatment"] = out[
        "group_code"
    ].map(
        lambda x: GROUP_TREATMENT[x][
            "treatment"
        ]
    )

    out["label_fr"] = out[
        "group_code"
    ].map(
        lambda x: GROUP_TREATMENT[x][
            "label_fr"
        ]
    )

    out["movable_by_standard_aod"] = out[
        "group_code"
    ].map(
        lambda x: GROUP_TREATMENT[x][
            "movable_by_standard_aod"
        ]
    )

    return out


def allocate_exposure_by_group(
    potential_exposure: pd.DataFrame,
    group_distribution: pd.DataFrame,
) -> pd.DataFrame:
    """
    Ventile l'exposition brute à l'AOD entre groupes
    de départ en appliquant les parts par sexe.

    Hypothèse V1 :
    indépendance entre l'âge de liquidation et le groupe
    de départ, conditionnellement au sexe.

    Cette ventilation est modélisée et non observée.
    """
    classified = classify_retirement_groups(
        group_distribution
    )

    required_exposure = {
        "sex",
        "potential_exposed_effectifs",
    }

    missing = (
        required_exposure
        - set(potential_exposure.columns)
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes dans l'exposition : "
            f"{sorted(missing)}"
        )

    out = classified.merge(
        potential_exposure[
            [
                "sex",
                "potential_exposed_effectifs",
            ]
        ],
        on="sex",
        how="inner",
        validate="many_to_one",
    )

    out[
        "allocated_exposed_effectifs"
    ] = (
        out[
            "potential_exposed_effectifs"
        ]
        * out[
            "share_within_sex_recomputed"
        ]
    )

    out[
        "allocation_method"
    ] = (
        "independence_age_group_conditional_on_sex"
    )

    return out


def compute_standard_aod_movable_exposure(
    allocated_exposure: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "sex",
        "group_code",
        "movable_by_standard_aod",
        "allocated_exposed_effectifs",
    }

    missing = (
        required
        - set(allocated_exposure.columns)
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes : "
            f"{sorted(missing)}"
        )

    movable = allocated_exposure.loc[
        allocated_exposure[
            "movable_by_standard_aod"
        ]
    ].copy()

    return (
        movable
        .groupby(
            "sex",
            as_index=False,
        )
        .agg(
            movable_exposed_effectifs=(
                "allocated_exposed_effectifs",
                "sum",
            )
        )
    )