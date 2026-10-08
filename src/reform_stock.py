import pandas as pd


def build_monthly_delayed_stock(
    cohort_calendar: pd.DataFrame,
    movable_reference: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construit le stock mensuel de personnes dont la liquidation
    est retardée par la réforme.

    Convention provisoire V1 :
    la calibration annuelle CNAV est répartie uniformément
    entre les 12 cohortes mensuelles de naissance.

    Exemple :
    si 32 400 liquidations sont déplaçables sur une année,
    une cohorte mensuelle représente provisoirement
    32 400 / 12 = 2 700 personnes.

    Chaque cohorte reste dans le stock entre sa date
    d'éligibilité de référence et sa date d'éligibilité
    après réforme.

    Cette méthode reste une calibration provisoire :
    elle ne remplace pas une fonction de liquidation
    âge x sexe x catégorie correctement estimée.
    """
    required_calendar = {
        "birth_year",
        "birth_month",
        "delta_aod_months",
        "baseline_eligibility_year",
        "baseline_eligibility_month",
    }

    missing_calendar = (
        required_calendar
        - set(cohort_calendar.columns)
    )

    if missing_calendar:
        raise ValueError(
            "Colonnes manquantes dans le calendrier : "
            f"{sorted(missing_calendar)}"
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
            "Colonnes manquantes dans la calibration : "
            f"{sorted(missing_reference)}"
        )

    if (
        cohort_calendar["delta_aod_months"] < 0
    ).any():
        raise ValueError(
            "Ce module ne traite que les reports positifs de l'AOD"
        )

    if (
        movable_reference["movable_exposed_effectifs"] < 0
    ).any():
        raise ValueError(
            "Les effectifs de référence ne peuvent pas être négatifs"
        )

    reference = movable_reference.copy()

    reference[
        "monthly_cohort_effectif"
    ] = (
        reference[
            "movable_exposed_effectifs"
        ] / 12.0
    )

    rows = []

    affected = cohort_calendar.loc[
        cohort_calendar[
            "delta_aod_months"
        ] > 0
    ]

    for cohort in affected.itertuples(
        index=False
    ):
        start_index = (
            int(
                cohort.baseline_eligibility_year
            )
            * 12
            + int(
                cohort.baseline_eligibility_month
            )
            - 1
        )

        delay_months = int(
            cohort.delta_aod_months
        )

        for ref in reference.itertuples(
            index=False
        ):
            for delay_month in range(
                delay_months
            ):
                calendar_index = (
                    start_index
                    + delay_month
                )

                year = (
                    calendar_index // 12
                )

                month = (
                    calendar_index % 12
                    + 1
                )

                rows.append(
                    {
                        "birth_year":
                            int(
                                cohort.birth_year
                            ),
                        "birth_month":
                            int(
                                cohort.birth_month
                            ),
                        "sex":
                            ref.sex,
                        "calendar_year":
                            int(year),
                        "calendar_month":
                            int(month),
                        "delay_month_number":
                            delay_month + 1,
                        "delayed_stock_persons":
                            float(
                                ref.monthly_cohort_effectif
                            ),
                    }
                )

    return pd.DataFrame(rows, columns=[
        "birth_year", "birth_month", "sex", "calendar_year", "calendar_month",
        "delay_month_number", "delayed_stock_persons",
    ]).astype({
        "birth_year": "int64", "birth_month": "int64", "calendar_year": "int64",
        "calendar_month": "int64", "delay_month_number": "int64",
        "delayed_stock_persons": "float64",
    })


def aggregate_monthly_stock(
    delayed_stock: pd.DataFrame,
) -> pd.DataFrame:
    """
    Agrège les cohortes présentes simultanément dans le stock
    pour obtenir un stock total par mois civil.
    """
    required = {
        "calendar_year",
        "calendar_month",
        "delayed_stock_persons",
    }

    missing = (
        required
        - set(delayed_stock.columns)
    )

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    if delayed_stock.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "month",
                "delayed_stock_persons",
            ]
        )

    return (
        delayed_stock
        .groupby(
            [
                "calendar_year",
                "calendar_month",
            ],
            as_index=False,
        )
        .agg(
            delayed_stock_persons=(
                "delayed_stock_persons",
                "sum",
            )
        )
        .rename(
            columns={
                "calendar_year": "year",
                "calendar_month": "month",
            }
        )
        .sort_values(
            [
                "year",
                "month",
            ]
        )
        .reset_index(drop=True)
    )


def aggregate_annual_stock(
    monthly_stock: pd.DataFrame,
    start_year: int | None = None,
    end_year: int | None = None,
) -> pd.DataFrame:
    """
    Produit le stock annuel moyen de personnes dont la retraite
    est retardée.

    Toutes les années sont complétées avec 12 mois afin qu'une
    année partiellement couverte ne soit pas artificiellement
    surestimée.

    annual_average_delayed_stock :
        moyenne des 12 stocks mensuels.

    delayed_person_years :
        somme des stocks mensuels / 12.
        Numériquement identique au stock annuel moyen lorsque
        l'année comporte exactement 12 mois.
    """
    required = {
        "year",
        "month",
        "delayed_stock_persons",
    }

    missing = (
        required
        - set(monthly_stock.columns)
    )

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    if start_year is not None and end_year is not None and start_year > end_year:
        raise ValueError("L'annee de debut doit preceder l'annee de fin.")

    if monthly_stock.empty and start_year is not None and end_year is not None:
        return pd.DataFrame({
            "year": range(start_year, end_year + 1),
            "annual_average_delayed_stock": 0.0,
            "maximum_monthly_delayed_stock": 0.0,
            "delayed_person_years": 0.0,
        })

    if monthly_stock.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "annual_average_delayed_stock",
                "delayed_person_years",
                "maximum_monthly_delayed_stock",
            ]
        )

    first_year = (
        int(monthly_stock["year"].min())
        if start_year is None
        else int(start_year)
    )

    last_year = (
        int(monthly_stock["year"].max())
        if end_year is None
        else int(end_year)
    )

    complete_calendar = pd.MultiIndex.from_product(
        [
            range(
                first_year,
                last_year + 1,
            ),
            range(1, 13),
        ],
        names=[
            "year",
            "month",
        ],
    ).to_frame(
        index=False
    )

    complete = (
        complete_calendar
        .merge(
            monthly_stock,
            on=[
                "year",
                "month",
            ],
            how="left",
            validate="one_to_one",
        )
    )

    complete[
        "delayed_stock_persons"
    ] = (
        complete[
            "delayed_stock_persons"
        ]
        .fillna(0.0)
    )

    return (
        complete
        .groupby(
            "year",
            as_index=False,
        )
        .agg(
            annual_average_delayed_stock=(
                "delayed_stock_persons",
                "mean",
            ),
            monthly_stock_sum=(
                "delayed_stock_persons",
                "sum",
            ),
            maximum_monthly_delayed_stock=(
                "delayed_stock_persons",
                "max",
            ),
        )
        .assign(
            delayed_person_years=lambda x:
                x["monthly_stock_sum"]
                / 12.0
        )
        .drop(
            columns="monthly_stock_sum"
        )
    )


def build_labour_effect_from_stock(
    annual_stock: pd.DataFrame,
    behavioural_delay_share: float,
    absorption_rate: float,
) -> pd.DataFrame:
    """
    Convertit le stock annuel moyen de personnes retenues
    hors retraite en effet sur le marché du travail.

    Ce bloc distingue :
    - population maintenue hors retraite ;
    - population active supplémentaire ;
    - emploi supplémentaire ;
    - chômage supplémentaire.
    """
    required = {
        "year",
        "annual_average_delayed_stock",
    }

    missing = (
        required
        - set(annual_stock.columns)
    )

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    if not 0 <= behavioural_delay_share <= 1:
        raise ValueError(
            "behavioural_delay_share doit être compris entre 0 et 1"
        )

    if not 0 <= absorption_rate <= 1:
        raise ValueError(
            "absorption_rate doit être compris entre 0 et 1"
        )

    out = annual_stock.copy()

    out[
        "delta_labour_force_reform"
    ] = (
        out[
            "annual_average_delayed_stock"
        ]
        * behavioural_delay_share
    )

    out[
        "delta_employment_reform"
    ] = (
        out[
            "delta_labour_force_reform"
        ]
        * absorption_rate
    )

    out[
        "delta_unemployment_reform"
    ] = (
        out[
            "delta_labour_force_reform"
        ]
        - out[
            "delta_employment_reform"
        ]
    )

    out[
        "behavioural_delay_share"
    ] = behavioural_delay_share

    out[
        "absorption_rate"
    ] = absorption_rate

    return out