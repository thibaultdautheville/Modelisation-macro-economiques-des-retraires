import pandas as pd

from src.legal import apply_aod_scenario
from src.schemas import ScenarioConfig


def retirement_date_from_age(
    birth_year: int,
    birth_month: int,
    age_months: int,
) -> tuple[int, int]:
    """
    Convertit une cohorte mensuelle et un âge en mois
    en année/mois calendaire d'atteinte de cet âge.
    """
    if not 1 <= birth_month <= 12:
        raise ValueError(
            "Le mois de naissance doit être compris entre 1 et 12"
        )

    if age_months < 0:
        raise ValueError(
            "L'âge en mois doit être positif"
        )

    total_month = (
        birth_year * 12
        + birth_month - 1
        + age_months
    )

    year = total_month // 12
    month = total_month % 12 + 1

    return int(year), int(month)


def build_cohort_reform_calendar(
    legal_calendar: pd.DataFrame,
    scenario: ScenarioConfig,
) -> pd.DataFrame:
    """
    Construit le calendrier de déplacement de l'AOD
    pour chaque cohorte mensuelle.
    """
    legal = apply_aod_scenario(
        legal_calendar,
        scenario,
    )

    rows = []

    for row in legal.itertuples(index=False):
        baseline_year, baseline_month = (
            retirement_date_from_age(
                int(row.birth_year),
                int(row.birth_month),
                int(row.aod_months_baseline),
            )
        )

        reform_year, reform_month = (
            retirement_date_from_age(
                int(row.birth_year),
                int(row.birth_month),
                int(row.aod_months_reform),
            )
        )

        rows.append(
            {
                "birth_year": int(row.birth_year),
                "birth_month": int(row.birth_month),
                "aod_months_baseline":
                    int(row.aod_months_baseline),
                "aod_months_reform":
                    int(row.aod_months_reform),
                "delta_aod_months":
                    int(row.delta_aod_months),
                "baseline_eligibility_year":
                    baseline_year,
                "baseline_eligibility_month":
                    baseline_month,
                "reform_eligibility_year":
                    reform_year,
                "reform_eligibility_month":
                    reform_month,
            }
        )

    return pd.DataFrame(rows)


def expand_delay_to_calendar_months(
    cohort_calendar: pd.DataFrame,
) -> pd.DataFrame:
    """
    Transforme chaque report d'AOD en mois calendaires
    effectivement situés entre l'ancienne et la nouvelle
    date d'éligibilité.

    Une ligne = une cohorte de naissance x un mois de report.
    """
    required = {
        "birth_year",
        "birth_month",
        "delta_aod_months",
        "baseline_eligibility_year",
        "baseline_eligibility_month",
    }

    missing = required - set(
        cohort_calendar.columns
    )

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    rows = []

    affected = cohort_calendar.loc[
        cohort_calendar[
            "delta_aod_months"
        ] > 0
    ]

    for row in affected.itertuples(index=False):
        start_index = (
            int(row.baseline_eligibility_year) * 12
            + int(row.baseline_eligibility_month)
            - 1
        )

        for delay_month in range(
            int(row.delta_aod_months)
        ):
            calendar_index = (
                start_index + delay_month
            )

            calendar_year = (
                calendar_index // 12
            )

            calendar_month = (
                calendar_index % 12 + 1
            )

            rows.append(
                {
                    "birth_year":
                        int(row.birth_year),
                    "birth_month":
                        int(row.birth_month),
                    "calendar_year":
                        int(calendar_year),
                    "calendar_month":
                        int(calendar_month),
                    "delay_month_number":
                        delay_month + 1,
                }
            )

    return pd.DataFrame(rows)


def aggregate_delay_by_year(
    monthly_delays: pd.DataFrame,
) -> pd.DataFrame:
    """
    Produit un indicateur annuel de cohortes-mois reportées.

    Il ne s'agit PAS encore d'un nombre de personnes.
    """
    if monthly_delays.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "cohort_months_delayed",
            ]
        )

    result = (
        monthly_delays
        .groupby(
            "calendar_year",
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "calendar_year": "year",
                "size": "cohort_months_delayed",
            }
        )
    )

    return result