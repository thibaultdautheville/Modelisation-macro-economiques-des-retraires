
"""Selection de la transition par sexe.

Ce module raccorde les stocks par cohorte et par sexe
au stock annuel selectionne par le moteur principal.
Aucune calibration economique n'est introduite ici.
"""

from datetime import date

import numpy as np
import pandas as pd

from src.effective_calendar import build_effective_cohort_calendar
from src.labour_behaviour import (
    aggregate_annual_delayed_stock_by_sex,
    apply_reference_transition_by_sex,
)


def select_transition_stock_by_sex(
    cohort_calendar: pd.DataFrame,
    delayed_stock_detail: pd.DataFrame,
    reference_transition: pd.DataFrame,
    transition_stock_selection: pd.DataFrame,
    start_year: int,
    end_year: int,
    method: str = "historique",
    effective_date: date | None = None,
) -> pd.DataFrame:
    """Construit le stock selectionne par annee et sexe."""

    methods = {
        "historique",
        "calendrier_cohortes",
        "double_ajustement",
    }
    if method not in methods:
        raise ValueError(f"Methode inconnue : {method}")

    if start_year > end_year:
        raise ValueError("Horizon annuel invalide")

    required = {
        "birth_year",
        "birth_month",
        "calendar_year",
        "calendar_month",
        "sex",
        "delayed_stock_persons",
    }
    missing = required - set(delayed_stock_detail.columns)
    if missing:
        raise ValueError(
            f"Colonnes du detail manquantes : {sorted(missing)}"
        )

    detail = delayed_stock_detail.copy()

    if detail["sex"].isna().any():
        raise ValueError("Sexe manquant")

    if not detail["sex"].isin(["F", "H"]).all():
        raise ValueError("Sexe autre que F ou H")

    if (
        detail["delayed_stock_persons"].isna().any()
        or (detail["delayed_stock_persons"] < 0).any()
    ):
        raise ValueError("Stock mensuel manquant ou negatif")

    if method == "historique":
        if effective_date is not None:
            raise ValueError(
                "La methode historique n'utilise pas de date"
            )

        annual = aggregate_annual_delayed_stock_by_sex(
            detail,
            start_year=start_year,
            end_year=end_year,
        )

        out = apply_reference_transition_by_sex(
            annual,
            reference_transition,
        )

        out["selected_delayed_stock_by_sex"] = out[
            "annual_average_delayed_stock_adjusted"
        ]

    else:
        if not isinstance(effective_date, date):
            raise ValueError(
                "Date d'effet obligatoire pour cette methode"
            )

        calendar = build_effective_cohort_calendar(
            cohort_calendar,
            effective_date,
        )

        filtered = detail.merge(
            calendar[
                [
                    "birth_year",
                    "birth_month",
                    "eligible_under_date_rule",
                ]
            ],
            on=["birth_year", "birth_month"],
            how="left",
            validate="many_to_one",
            indicator=True,
        )

        if filtered["_merge"].ne("both").any():
            raise ValueError(
                "Des cohortes n'ont pas de regle d'application"
            )

        filtered["selected_monthly_stock"] = filtered[
            "delayed_stock_persons"
        ].where(
            filtered["eligible_under_date_rule"],
            0.0,
        )

        monthly = filtered.groupby(
            ["calendar_year", "calendar_month", "sex"],
            as_index=False,
        )["selected_monthly_stock"].sum()

        full_index = pd.MultiIndex.from_product(
            [
                range(start_year, end_year + 1),
                range(1, 13),
                ["F", "H"],
            ],
            names=["calendar_year", "calendar_month", "sex"],
        )

        monthly = (
            monthly.set_index(
                ["calendar_year", "calendar_month", "sex"]
            )
            .reindex(full_index, fill_value=0.0)
            .reset_index()
        )

        out = (
            monthly.groupby(
                ["calendar_year", "sex"],
                as_index=False,
            )["selected_monthly_stock"]
            .mean()
            .rename(
                columns={
                    "calendar_year": "year",
                    "selected_monthly_stock":
                        "selected_delayed_stock_by_sex",
                }
            )
        )

        if method == "double_ajustement":
            transition = reference_transition[
                ["year", "reference_maturity_factor"]
            ]

            out = out.merge(
                transition,
                on="year",
                how="left",
                validate="many_to_one",
            )

            if out["reference_maturity_factor"].isna().any():
                raise ValueError(
                    "Facteur historique manquant"
                )

            out["selected_delayed_stock_by_sex"] *= out[
                "reference_maturity_factor"
            ]

    # Nom attendu par le module des statuts professionnels.
    out["annual_average_delayed_stock_adjusted"] = out[
        "selected_delayed_stock_by_sex"
    ]

    out["transition_method_selected"] = method

    # Controle obligatoire de conservation avec le moteur.
    totals = (
        out.groupby("year", as_index=False)[
            "selected_delayed_stock_by_sex"
        ]
        .sum()
        .merge(
            transition_stock_selection[
                ["year", "selected_delayed_stock"]
            ],
            on="year",
            how="outer",
            validate="one_to_one",
        )
    )

    if totals.isna().any().any():
        raise ValueError(
            "Annees manquantes entre les deux branches"
        )

    if not np.allclose(
        totals["selected_delayed_stock_by_sex"],
        totals["selected_delayed_stock"],
        rtol=1e-10,
        atol=1e-6,
    ):
        raise ValueError(
            "La somme des stocks par sexe ne correspond "
            "pas au stock selectionne par le moteur"
        )

    return out.sort_values(
        ["year", "sex"]
    ).reset_index(drop=True)
