import pandas as pd


def build_reform_labour_trajectory(
    displaced_liquidations: pd.DataFrame,
    behavioural_delay_share: float,
    absorption_rate: float,
) -> pd.DataFrame:
    """
    Transforme un stock annuel estimé de liquidations déplacées
    en effets annuels sur la population active, l'emploi et le chômage.

    Attention :
    movable_liquidations est interprété ici comme un stock annuel
    de personnes concernées par le report de liquidation, et non
    comme un flux à cumuler indéfiniment d'une année sur l'autre.

    behavioural_delay_share :
        part des liquidations déplacées qui se traduit effectivement
        par un maintien dans la population active.

    absorption_rate :
        part de cette population active supplémentaire absorbée
        en emploi au cours de l'année.
    """
    required = {
        "year",
        "movable_liquidations",
    }

    missing = required - set(
        displaced_liquidations.columns
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes : "
            f"{sorted(missing)}"
        )

    if not 0 <= behavioural_delay_share <= 1:
        raise ValueError(
            "behavioural_delay_share doit être compris entre 0 et 1"
        )

    if not 0 <= absorption_rate <= 1:
        raise ValueError(
            "absorption_rate doit être compris entre 0 et 1"
        )

    if (
        displaced_liquidations[
            "movable_liquidations"
        ] < 0
    ).any():
        raise ValueError(
            "Les liquidations déplacées ne peuvent pas être négatives"
        )

    if displaced_liquidations[
        "year"
    ].duplicated().any():
        raise ValueError(
            "Une seule observation par année est requise"
        )

    out = (
        displaced_liquidations
        .sort_values("year")
        .reset_index(drop=True)
        .copy()
    )

    out[
        "delta_labour_force_reform"
    ] = (
        out["movable_liquidations"]
        * behavioural_delay_share
    )

    out[
        "delta_employment_reform"
    ] = (
        out["delta_labour_force_reform"]
        * absorption_rate
    )

    out[
        "delta_unemployment_reform"
    ] = (
        out["delta_labour_force_reform"]
        - out["delta_employment_reform"]
    )

    out[
        "behavioural_delay_share"
    ] = behavioural_delay_share

    out[
        "absorption_rate"
    ] = absorption_rate

    identity_gap = (
        out["delta_labour_force_reform"]
        - out["delta_employment_reform"]
        - out["delta_unemployment_reform"]
    ).abs().max()

    if identity_gap > 1e-10:
        raise ValueError(
            "Identité population active = emploi + chômage non respectée"
        )

    return out