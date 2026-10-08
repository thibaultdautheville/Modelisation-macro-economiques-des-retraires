
from datetime import date

import pandas as pd

from src.effective_calendar import (
    build_effective_cohort_calendar,
    compare_effective_date_stocks,
)


SUPPORTED_TRANSITION_METHODS = {
    "historique",
    "calendrier_cohortes",
    "double_ajustement",
}


def select_transition_stock(
    cohort_calendar: pd.DataFrame,
    delayed_stock_detail: pd.DataFrame,
    annual_delayed_stock: pd.DataFrame,
    method: str = "historique",
    effective_date: date | None = None,
) -> pd.DataFrame:
    """
    Selectionne le stock utilise pour le diagnostic
    du marche du travail.

    historique :
        Conserve le stock corrige par le facteur
        de maturite annuel du prototype.

    calendrier_cohortes :
        Utilise le stock filtre par date d'effet,
        sans appliquer le facteur de maturite.

    double_ajustement :
        Diagnostic uniquement, non recommande
        comme methode centrale.

    La date d'effet ne constitue pas une validation
    juridique de l'applicabilite aux cohortes.
    """

    if method not in SUPPORTED_TRANSITION_METHODS:
        raise ValueError(
            f"Methode inconnue : {method}"
        )

    required = {
        "year",
        "annual_average_delayed_stock",
        "annual_average_delayed_stock_transition_adjusted",
        "reference_maturity_factor",
    }

    missing = required - set(annual_delayed_stock.columns)

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    if method == "historique":
        if effective_date is not None:
            raise ValueError(
                "La methode historique n'utilise "
                "pas de date d'effet."
            )

        out = annual_delayed_stock.copy()

        out["selected_delayed_stock"] = out[
            "annual_average_delayed_stock_transition_adjusted"
        ]

    else:
        if not isinstance(effective_date, date):
            raise ValueError(
                "Une date d'effet est obligatoire "
                "pour cette methode."
            )

        calendar = build_effective_cohort_calendar(
            cohort_calendar,
            effective_date,
        )

        diagnostic = compare_effective_date_stocks(
            delayed_stock_detail,
            annual_delayed_stock,
            calendar,
            start_year=int(annual_delayed_stock["year"].min()),
            end_year=int(annual_delayed_stock["year"].max()),
        )

        out = annual_delayed_stock.merge(
            diagnostic[
                [
                    "year",
                    "annual_average_delayed_stock_date_filtered",
                    "hypothetical_double_filtered_stock",
                ]
            ],
            on="year",
            how="left",
            validate="one_to_one",
        )

        column = (
            "annual_average_delayed_stock_date_filtered"
            if method == "calendrier_cohortes"
            else "hypothetical_double_filtered_stock"
        )

        out["selected_delayed_stock"] = out[column]

    if out["selected_delayed_stock"].isna().any():
        raise ValueError(
            "Stocks selectionnes manquants."
        )

    if (out["selected_delayed_stock"] < 0).any():
        raise ValueError(
            "Stocks selectionnes negatifs."
        )

    out["transition_method_selected"] = method

    return out
