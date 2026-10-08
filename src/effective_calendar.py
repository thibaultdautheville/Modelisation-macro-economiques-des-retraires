"""Diagnostics de date d'effet par cohorte, sans activation juridique implicite.

Cette branche ne modifie pas le moteur de simulation courant.
La date retenue est un parametre d'experience et non une regle universelle.
"""
from datetime import date
import pandas as pd


def build_effective_cohort_calendar(cohort_calendar: pd.DataFrame, effective_date: date) -> pd.DataFrame:
    """Marque les cohortes dont l'eligibilite *de reference* atteint la date d'effet.

    Convention candidate: cohortes dont le droit aurait ete ouvert a compter de
    la date, non les personnes deja eligibles. Elle doit etre validee par texte.
    """
    if not isinstance(effective_date, date):
        raise TypeError("effective_date doit etre une date")
    required = {"birth_year", "birth_month", "baseline_eligibility_year", "baseline_eligibility_month", "delta_aod_months"}
    missing = required - set(cohort_calendar.columns)
    if missing:
        raise ValueError(f"Colonnes absentes : {sorted(missing)}")
    out = cohort_calendar.copy()
    if out.duplicated(["birth_year", "birth_month"]).any():
        raise ValueError("Doublons de cohortes")
    if not out["baseline_eligibility_month"].between(1,12).all() or not out["birth_month"].between(1,12).all():
        raise ValueError("Mois de naissance/eligibilite invalide")
    if out["delta_aod_months"].lt(0).any():
        raise ValueError("Les baisses d'AOD ne sont pas traitees")
    threshold = effective_date.year * 12 + effective_date.month - 1
    idx = out["baseline_eligibility_year"].astype(int)*12 + out["baseline_eligibility_month"].astype(int)-1
    out["reference_eligibility_index"] = idx
    out["effective_date"] = effective_date.isoformat()
    out["eligible_under_date_rule"] = (idx >= threshold) & out["delta_aod_months"].gt(0)
    out["effective_date_rule"] = "baseline_eligibility_on_or_after_date_candidate"
    return out


def compare_effective_date_stocks(
    delayed_stock_detail: pd.DataFrame,
    annual_delayed_stock: pd.DataFrame,
    cohort_effective_calendar: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Compare ancien brut/ajuste et effet brut d'un filtre de cohortes.

    Le facteur annuel historique n'est volontairement PAS re-applique au
    stock filtre. Il est fourni uniquement comme diagnostic de double filtrage.
    """
    required_detail = {"birth_year", "birth_month", "calendar_year", "calendar_month", "delayed_stock_persons"}
    required_annual = {"year", "annual_average_delayed_stock", "annual_average_delayed_stock_transition_adjusted", "reference_maturity_factor"}
    required_cohorts = {"birth_year", "birth_month", "eligible_under_date_rule"}
    for name, data, required in (("detail", delayed_stock_detail, required_detail), ("annuel", annual_delayed_stock, required_annual), ("cohortes", cohort_effective_calendar, required_cohorts)):
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"{name} : colonnes absentes {sorted(missing)}")
    if start_year > end_year:
        raise ValueError("Horizon invalide")
    if cohort_effective_calendar.duplicated(["birth_year", "birth_month"]).any():
        raise ValueError("Cohortes dupliquees")
    if delayed_stock_detail["delayed_stock_persons"].lt(0).any():
        raise ValueError("Stock negatif")
    detail = delayed_stock_detail.merge(
        cohort_effective_calendar[["birth_year", "birth_month", "eligible_under_date_rule"]],
        on=["birth_year", "birth_month"], how="left", validate="many_to_one", indicator=True,
    )
    if detail["_merge"].ne("both").any():
        raise ValueError("Detail mensuel avec cohortes sans calendrier")
    detail["stock_filtre"] = detail["delayed_stock_persons"].where(detail["eligible_under_date_rule"], 0.0)
    monthly = detail.groupby(["calendar_year", "calendar_month"], as_index=False)["stock_filtre"].sum()
    index = pd.MultiIndex.from_product([range(start_year, end_year+1),range(1,13)], names=["calendar_year","calendar_month"])
    monthly = monthly.set_index(["calendar_year","calendar_month"]).reindex(index, fill_value=0.0).reset_index()
    annual = monthly.groupby("calendar_year", as_index=False)["stock_filtre"].mean().rename(columns={"calendar_year":"year","stock_filtre":"annual_average_delayed_stock_date_filtered"})
    out = annual.merge(annual_delayed_stock[list(required_annual)], on="year", how="left", validate="one_to_one")
    if out[list(required_annual - {"year"})].isna().any().any():
        raise ValueError("Annees manquantes dans les stocks de reference")
    out["legacy_vs_filtered_difference"] = out["annual_average_delayed_stock_date_filtered"] - out["annual_average_delayed_stock_transition_adjusted"]
    out["hypothetical_double_filtered_stock"] = out["annual_average_delayed_stock_date_filtered"] * out["reference_maturity_factor"]
    out["date_rule_status"] = "diagnostic_not_validated_for_legal_effect"
    return out.sort_values("year").reset_index(drop=True)
