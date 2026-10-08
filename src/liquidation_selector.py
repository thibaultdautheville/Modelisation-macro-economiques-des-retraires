
"""Selection de la calibration des liquidations CNAV.

Deux methodes :
- independance : reconstruction historique du prototype ;
- cnav_observee : croisement age x sexe x categorie, DREES 2024.

La distribution de reference reste une construction contrefactuelle.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.cnav_crossed import (
    load_observed_cnav_cross,
    reconcile_cnav_cross,
)
from src.liquidation_reference import (
    build_reference_liquidation_distribution,
)


SUPPORTED_LIQUIDATION_METHODS = {
    "independance",
    "cnav_observee",
}


def select_liquidation_distribution(
    age_distribution: pd.DataFrame,
    group_distribution: pd.DataFrame,
    method: str = "independance",
    observed_cross_path: str | Path | None = None,
    reference_aod_months: int = 768,
    observed_standard_age_floor_months: int = 744,
) -> pd.DataFrame:
    """
    Construit la distribution des liquidations de reference.

    Seuls les departs de droit commun sont deplaces vers
    l'AOD de reference. Les autres groupes restent inchanges.

    Les ages ouverts (>70) sont exclus de la grille par age
    exact ; ils ne sont pas assimiles a l'age de 70 ans.
    """

    if method not in SUPPORTED_LIQUIDATION_METHODS:
        raise ValueError(
            f"Methode de liquidation inconnue : {method}"
        )

    if (
        reference_aod_months <= 0
        or observed_standard_age_floor_months <= 0
        or reference_aod_months % 12 != 0
        or observed_standard_age_floor_months % 12 != 0
    ):
        raise ValueError(
            "Les ages de calibration doivent etre "
            "des multiples de 12 mois strictement positifs."
        )

    reference_age = reference_aod_months / 12
    observed_floor = observed_standard_age_floor_months / 12

    if observed_floor > reference_age:
        raise ValueError(
            "Le plancher observe depasse l'AOD de reference."
        )

    if method == "independance":
        if observed_cross_path is not None:
            raise ValueError(
                "La methode historique ne requiert "
                "pas le fichier CNAV croise."
            )

        return build_reference_liquidation_distribution(
            age_distribution,
            group_distribution,
            reference_aod_months=reference_aod_months,
            observed_standard_age_floor_months=(
                observed_standard_age_floor_months
            ),
        )

    if observed_cross_path is None:
        raise ValueError(
            "Le fichier CNAV croise est obligatoire."
        )

    cross = load_observed_cnav_cross(observed_cross_path)

    # Verifie que les effectifs croises reproduisent
    # les totaux d'age des donnees CNAV du prototype.
    reconcile_cnav_cross(cross, age_distribution)

    closed = cross.loc[
        cross["sex"].isin(["F", "H"])
        & ~cross["open_age_class"],
        [
            "sex",
            "age_numeric",
            "group_code",
            "effectifs",
        ],
    ].copy()

    if closed.empty:
        raise ValueError(
            "Aucune liquidation CNAV par age ferme."
        )

    if (
        closed["effectifs"].isna().any()
        or closed["age_numeric"].isna().any()
        or (closed["effectifs"] < 0).any()
    ):
        raise ValueError(
            "Donnees CNAV observees invalides."
        )

    out = closed.rename(
        columns={"effectifs": "allocated_effectifs"}
    )

    out["reference_age_numeric"] = out["age_numeric"]

    shift = (
        out["group_code"].eq("droit_commun")
        & out["age_numeric"].ge(observed_floor)
        & out["age_numeric"].lt(reference_age)
    )

    out.loc[
        shift, "reference_age_numeric"
    ] = reference_age

    out["shifted_to_reference_aod"] = shift

    out["allocation_method"] = (
        "observed_cnav_drees_cross_2024"
    )
    out["reference_method"] = (
        "observed_cross_provisional_standard_age_bunching"
    )
    out["calibration_status"] = (
        "observed_2024_provisional_counterfactual"
    )

    if not np.isclose(
        out["allocated_effectifs"].sum(),
        closed["effectifs"].sum(),
        rtol=0,
        atol=1e-8,
    ):
        raise ValueError(
            "La reconstruction modifie les effectifs CNAV."
        )

    return (
        out.sort_values(
            ["sex", "age_numeric", "group_code"]
        )
        .reset_index(drop=True)
    )
