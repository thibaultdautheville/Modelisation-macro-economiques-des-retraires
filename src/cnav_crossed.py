"""CNAV/DREES 2024 : croisement observe age x sexe x categorie.

Ce croisement est historique, et ne constitue pas une distribution
contrefactuelle post-reforme. Le traitement des ages ouverts reste explicite.
"""
from pathlib import Path

import pandas as pd


ALLOWED_GROUPS = {
    "droit_commun", "carriere_longue", "sante_invalidite_inaptitude", "autres"
}


def load_observed_cnav_cross(path: str | Path) -> pd.DataFrame:
    """Lit l'extraction tracable DREES, conserve '>70' sans lui attribuer un age fictif."""
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype={"age_label": str})
    expected = {"year", "sex", "age_label", "group_code", "effectifs"}
    if missing := expected - set(df.columns):
        raise ValueError(f"Colonnes CNAV manquantes : {sorted(missing)}")
    if df.empty or df["effectifs"].isna().any() or (df["effectifs"] < 0).any():
        raise ValueError("Effectifs CNAV invalides")
    if not set(df["sex"]).issubset({"F", "H", "T"}):
        raise ValueError("Sexe CNAV inconnu")
    if not set(df["group_code"]).issubset(ALLOWED_GROUPS):
        raise ValueError("Categorie CNAV inconnue")
    if not (df["year"] == 2024).all():
        raise ValueError("L'extraction disponible concerne uniquement 2024")
    age = pd.to_numeric(df["age_label"], errors="coerce")
    if (age.isna() & df["age_label"].ne(">70")).any():
        raise ValueError("Classe d'age CNAV inconnue")
    if df.duplicated(["year", "sex", "age_label", "group_code"]).any():
        raise ValueError("Doublon CNAV age/sexe/categorie")
    result = df.copy()
    result["age_numeric"] = age
    result["open_age_class"] = result["age_label"].eq(">70")
    return result


def reconcile_cnav_cross(cross: pd.DataFrame, age_totals: pd.DataFrame) -> pd.DataFrame:
    """Verifie les comptes par sexe et age ferme; documente la classe ouverte."""
    observed = cross.loc[cross["sex"].isin(["F", "H"])].copy()
    closed = (observed.loc[~observed["open_age_class"]]
              .groupby(["sex", "age_numeric"], as_index=False)["effectifs"].sum()
              .rename(columns={"effectifs": "cross_effectifs"}))
    ages = (age_totals.loc[age_totals["sex"].isin(["F", "H"]) & age_totals["age_numeric"].notna()]
            .groupby(["sex", "age_numeric"], as_index=False)["effectifs"].sum()
            .rename(columns={"effectifs": "age_effectifs"}))
    comparison = ages.merge(closed, on=["sex", "age_numeric"], how="outer", validate="one_to_one")
    comparison[["age_effectifs", "cross_effectifs"]] = comparison[["age_effectifs", "cross_effectifs"]].fillna(0)
    comparison["ecart"] = comparison["cross_effectifs"] - comparison["age_effectifs"]
    if (comparison["ecart"].abs() > 0.01).any():
        raise ValueError("La table croisee CNAV ne concorde pas avec les effectifs par age")
    return comparison.sort_values(["sex", "age_numeric"]).reset_index(drop=True)


def compare_allocation_methods(cross: pd.DataFrame, independent: pd.DataFrame) -> pd.DataFrame:
    """Diagnostic, sans substitution automatique de la calibration active."""
    observed = (cross.loc[cross["sex"].isin(["F", "H"]) & ~cross["open_age_class"]]
                .groupby(["sex", "age_numeric", "group_code"], as_index=False)["effectifs"].sum()
                .rename(columns={"effectifs": "observed_effectifs"}))
    hypothetical = (independent.groupby(["sex", "age_numeric", "group_code"], as_index=False)
                    ["allocated_effectifs"].sum().rename(columns={"allocated_effectifs": "independent_effectifs"}))
    result = observed.merge(hypothetical, on=["sex", "age_numeric", "group_code"], how="outer").fillna(0)
    result["ecart_observe_moins_independance"] = result["observed_effectifs"] - result["independent_effectifs"]
    return result.sort_values(["sex", "age_numeric", "group_code"]).reset_index(drop=True)
