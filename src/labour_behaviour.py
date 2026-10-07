import pandas as pd


def _validate_rate(
    value: float,
    name: str,
) -> None:
    """
    Vérifie qu'un paramètre comportemental
    appartient à l'intervalle [0, 1].
    """
    if not 0 <= value <= 1:
        raise ValueError(
            f"{name} doit être compris entre 0 et 1."
        )


def aggregate_annual_delayed_stock_by_sex(
    delayed_stock_detail: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """
    Agrège le stock mensuel de personnes dont la liquidation
    est retardée en stock annuel moyen par sexe.

    Les mois sans stock sont explicitement réintroduits à zéro,
    de sorte que la moyenne annuelle porte toujours sur 12 mois.
    """
    required = {
        "calendar_year",
        "calendar_month",
        "sex",
        "delayed_stock_persons",
    }

    missing = required - set(
        delayed_stock_detail.columns
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes : "
            f"{sorted(missing)}"
        )

    detail = delayed_stock_detail.loc[
        delayed_stock_detail[
            "calendar_year"
        ].between(
            start_year,
            end_year,
        )
        & delayed_stock_detail[
            "sex"
        ].isin(["F", "H"])
    ].copy()

    monthly = (
        detail.groupby(
            [
                "calendar_year",
                "calendar_month",
                "sex",
            ],
            as_index=False,
        )["delayed_stock_persons"]
        .sum()
    )

    full_index = pd.MultiIndex.from_product(
        [
            range(
                start_year,
                end_year + 1,
            ),
            range(1, 13),
            ["F", "H"],
        ],
        names=[
            "calendar_year",
            "calendar_month",
            "sex",
        ],
    )

    monthly = (
        monthly.set_index(
            [
                "calendar_year",
                "calendar_month",
                "sex",
            ]
        )
        .reindex(
            full_index,
            fill_value=0.0,
        )
        .reset_index()
    )

    annual = (
        monthly.groupby(
            [
                "calendar_year",
                "sex",
            ],
            as_index=False,
        )["delayed_stock_persons"]
        .mean()
        .rename(
            columns={
                "calendar_year": "year",
                "delayed_stock_persons":
                    "annual_average_delayed_stock",
            }
        )
    )

    return annual


def apply_reference_transition_by_sex(
    annual_stock_by_sex: pd.DataFrame,
    reference_transition: pd.DataFrame,
) -> pd.DataFrame:
    """
    Applique le facteur annuel de montée en charge juridique
    au stock annuel moyen de chaque sexe.
    """
    required_stock = {
        "year",
        "sex",
        "annual_average_delayed_stock",
    }

    required_transition = {
        "year",
        "reference_maturity_factor",
    }

    missing_stock = (
        required_stock
        - set(annual_stock_by_sex.columns)
    )

    missing_transition = (
        required_transition
        - set(reference_transition.columns)
    )

    if missing_stock:
        raise ValueError(
            "Colonnes manquantes dans le stock : "
            f"{sorted(missing_stock)}"
        )

    if missing_transition:
        raise ValueError(
            "Colonnes manquantes dans la transition : "
            f"{sorted(missing_transition)}"
        )

    transition = reference_transition[
        [
            "year",
            "reference_maturity_factor",
        ]
    ].copy()

    out = annual_stock_by_sex.merge(
        transition,
        on="year",
        how="left",
        validate="many_to_one",
    )

    if out[
        "reference_maturity_factor"
    ].isna().any():
        raise ValueError(
            "Facteur de maturité juridique manquant "
            "pour certaines années."
        )

    out[
        "annual_average_delayed_stock_adjusted"
    ] = (
        out[
            "annual_average_delayed_stock"
        ]
        * out[
            "reference_maturity_factor"
        ]
    )

    return out


def build_status_stock(
    adjusted_stock_by_sex: pd.DataFrame,
    status_rates: pd.DataFrame,
) -> pd.DataFrame:
    """
    Ventile le stock ajusté selon le statut pré-retraite :
    emploi, chômage et inactivité.
    """
    required_stock = {
        "year",
        "sex",
        "annual_average_delayed_stock_adjusted",
    }

    required_rates = {
        "sex",
        "pre_retirement_employment_share",
        "pre_retirement_unemployment_share",
        "pre_retirement_inactivity_share",
    }

    missing_stock = (
        required_stock
        - set(adjusted_stock_by_sex.columns)
    )

    missing_rates = (
        required_rates
        - set(status_rates.columns)
    )

    if missing_stock:
        raise ValueError(
            "Colonnes manquantes dans le stock : "
            f"{sorted(missing_stock)}"
        )

    if missing_rates:
        raise ValueError(
            "Colonnes manquantes dans les taux : "
            f"{sorted(missing_rates)}"
        )

    out = adjusted_stock_by_sex.merge(
        status_rates,
        on="sex",
        how="left",
        validate="many_to_one",
    )

    if out[
        "pre_retirement_employment_share"
    ].isna().any():
        raise ValueError(
            "Taux de statut pré-retraite manquant."
        )

    stock = out[
        "annual_average_delayed_stock_adjusted"
    ]

    out["previously_employed"] = (
        stock
        * out[
            "pre_retirement_employment_share"
        ]
    )

    out["previously_unemployed"] = (
        stock
        * out[
            "pre_retirement_unemployment_share"
        ]
    )

    out["previously_inactive"] = (
        stock
        * out[
            "pre_retirement_inactivity_share"
        ]
    )

    return out


def build_labour_effect_by_status(
    status_stock: pd.DataFrame,
    employment_retention_rate: float = 1.0,
    unemployed_activity_retention_rate: float = 1.0,
    unemployed_job_entry_rate: float = 1.0,
    inactive_activation_rate: float = 1.0,
    inactive_employment_rate: float = 1.0,
) -> pd.DataFrame:
    """
    Convertit le stock ventilé par statut pré-retraite
    en effets sur population active, emploi et chômage.

    Paramètres
    ----------
    employment_retention_rate :
        part des personnes précédemment en emploi qui
        restent en emploi lorsque leur retraite est retardée.

    unemployed_activity_retention_rate :
        part des personnes précédemment au chômage qui
        restent dans la population active.

    unemployed_job_entry_rate :
        part des personnes précédemment au chômage qui
        accèdent à l'emploi.

    inactive_activation_rate :
        part des personnes précédemment inactives qui
        entrent ou restent dans la population active.

    inactive_employment_rate :
        parmi les inactifs activés, part qui accède
        effectivement à l'emploi.
    """
    for value, name in [
        (
            employment_retention_rate,
            "employment_retention_rate",
        ),
        (
            unemployed_activity_retention_rate,
            "unemployed_activity_retention_rate",
        ),
        (
            unemployed_job_entry_rate,
            "unemployed_job_entry_rate",
        ),
        (
            inactive_activation_rate,
            "inactive_activation_rate",
        ),
        (
            inactive_employment_rate,
            "inactive_employment_rate",
        ),
    ]:
        _validate_rate(
            value,
            name,
        )

    if (
        unemployed_job_entry_rate
        > unemployed_activity_retention_rate
    ):
        raise ValueError(
            "Le taux d'accès à l'emploi des chômeurs "
            "ne peut pas dépasser leur taux de maintien "
            "dans la population active."
        )

    required = {
        "year",
        "sex",
        "previously_employed",
        "previously_unemployed",
        "previously_inactive",
    }

    missing = required - set(
        status_stock.columns
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes : "
            f"{sorted(missing)}"
        )

    out = status_stock.copy()

    # Personnes déjà en emploi :
    # leur maintien constitue directement un effet emploi.
    out[
        "employment_from_employed"
    ] = (
        out["previously_employed"]
        * employment_retention_rate
    )

    # Personnes initialement au chômage :
    # certaines restent actives et certaines trouvent un emploi.
    out[
        "labour_force_from_unemployed"
    ] = (
        out["previously_unemployed"]
        * unemployed_activity_retention_rate
    )

    out[
        "employment_from_unemployed"
    ] = (
        out["previously_unemployed"]
        * unemployed_job_entry_rate
    )

    # Personnes initialement inactives :
    # seule une fraction est activée.
    out[
        "labour_force_from_inactive"
    ] = (
        out["previously_inactive"]
        * inactive_activation_rate
    )

    out[
        "employment_from_inactive"
    ] = (
        out["labour_force_from_inactive"]
        * inactive_employment_rate
    )

    out[
        "delta_employment_reform"
    ] = (
        out["employment_from_employed"]
        + out["employment_from_unemployed"]
        + out["employment_from_inactive"]
    )

    out[
        "delta_labour_force_reform"
    ] = (
        out["employment_from_employed"]
        + out["labour_force_from_unemployed"]
        + out["labour_force_from_inactive"]
    )

    out[
        "delta_unemployment_reform"
    ] = (
        out["delta_labour_force_reform"]
        - out["delta_employment_reform"]
    )

    out[
        "employment_retention_rate"
    ] = employment_retention_rate

    out[
        "unemployed_activity_retention_rate"
    ] = unemployed_activity_retention_rate

    out[
        "unemployed_job_entry_rate"
    ] = unemployed_job_entry_rate

    out[
        "inactive_activation_rate"
    ] = inactive_activation_rate

    out[
        "inactive_employment_rate"
    ] = inactive_employment_rate

    return out


def aggregate_labour_effect(
    labour_effect_by_sex: pd.DataFrame,
) -> pd.DataFrame:
    """
    Agrège les effets F/H pour produire la trajectoire
    annuelle macroéconomique.
    """
    columns = [
        "delta_labour_force_reform",
        "delta_employment_reform",
        "delta_unemployment_reform",
        "employment_from_employed",
        "employment_from_unemployed",
        "employment_from_inactive",
    ]

    return (
        labour_effect_by_sex.groupby(
            "year",
            as_index=False,
        )[columns]
        .sum()
    )

