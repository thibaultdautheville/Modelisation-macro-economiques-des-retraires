from math import isfinite
from datetime import date
import pandas as pd

from src.config import (
    PROCESSED_DIR,
    START_YEAR,
    END_YEAR,
)
from src.scenario_loader import load_scenario_config

from src.reform_calendar import (
    build_cohort_reform_calendar,
    expand_delay_to_calendar_months,
    aggregate_delay_by_year,
)

from src.liquidation import (
    build_age_distribution,
    build_group_distribution,
    expand_age_distribution_to_months,
    compute_potentially_exposed_liquidations,
)

from src.retirement_groups import (
    allocate_exposure_by_group,
    compute_standard_aod_movable_exposure,
)

from src.transition_by_sex import (
    select_transition_stock_by_sex,
)

from src.liquidation_reference import (
    build_reference_liquidation_distribution,
    aggregate_reference_distribution,
    compute_reference_aod_exposure,
)

from src.reform_liquidations import (
    calibrate_displaced_liquidations,
    aggregate_displaced_liquidations,
)

from src.reform_stock import (
    build_monthly_delayed_stock,
    aggregate_monthly_stock,
    aggregate_annual_stock,
    build_labour_effect_from_stock,
)

from src.reference_transition import (
    build_reference_aod_transition,
    apply_reference_transition,
)

from src.transition_selector import select_transition_stock

from src.pre_retirement_status import (
    build_pre_retirement_status_rates,
)

from src.labour_behaviour import (
    aggregate_annual_delayed_stock_by_sex,
    apply_reference_transition_by_sex,
    build_status_stock,
    build_labour_effect_by_status,
)

from src.transition_by_sex import select_transition_stock_by_sex
# Calibration provisoire :
# âge plancher utilisé pour reconstruire la montée vers un AOD à 64 ans.
REFERENCE_FLOOR_AOD_MONTHS = 744  # 62 ans


def load_simulation_inputs() -> dict[str, pd.DataFrame]:
    """
    Charge les données transformées nécessaires
    au moteur de simulation retraite.
    """
    return {
        "legal": pd.read_parquet(
            PROCESSED_DIR / "legal_aod_dar.parquet"
        ),
        "liquidation_age": pd.read_parquet(
            PROCESSED_DIR / "liquidation_age_counts.parquet"
        ),
        "liquidation_groups": pd.read_parquet(
            PROCESSED_DIR / "liquidation_groups.parquet"
        ),
    }


def run_aod_simulation(
    scenario_id: str,
    baseline_aod_months: int,
    reform_aod_months: int,
    behavioural_delay_share: float = 1.0,
    absorption_rate: float = 1.0,
    steady_state_intensity: float = 144.0,
    transition_method: str = "historique",
    effective_date: date | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Exécute la chaîne V1 d'un scénario de relèvement
    de l'âge d'ouverture des droits.

    Chaîne principale :
    calendrier juridique
        -> exposition observée historique
        -> reconstruction du scénario de référence
        -> population potentiellement exposée
        -> stock mensuel de personnes dont la liquidation est retardée
        -> montée en charge de l'AOD de référence
        -> population active / emploi / chômage.

    Important :
    la distribution de liquidation de référence est actuellement
    reconstruite de manière provisoire à partir de données CNAV
    agrégées.

    Elle repose notamment sur :
    - une hypothèse d'indépendance entre âge de liquidation
      et catégorie de départ, conditionnellement au sexe ;
    - une reconstruction des départs de droit commun sous
      un AOD de référence stabilisé ;
    - un facteur transitoire dérivé du calendrier juridique.

    Ces éléments constituent des calibrations provisoires et
    doivent rester identifiables séparément des données observées.
    """
    if reform_aod_months < baseline_aod_months:
        raise ValueError(
            "La V1 de ce moteur ne traite pour l'instant "
            "que les relèvements de l'AOD."
        )

    for value, name in ((behavioural_delay_share, "behavioural_delay_share"),
                        (absorption_rate, "absorption_rate")):
        if not isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} doit etre fini et compris entre 0 et 1.")
    if not isfinite(steady_state_intensity) or steady_state_intensity <= 0:
        raise ValueError("L'intensite de reference doit etre finie et positive.")
    for value in (baseline_aod_months, reform_aod_months):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("Les AOD doivent etre des entiers positifs en mois.")

    inputs = load_simulation_inputs()

    scenario = load_scenario_config(
        scenario_id
    )

    # ------------------------------------------------------------------
    # 1. Calendrier juridique du scénario
    # ------------------------------------------------------------------

    cohort_calendar = (
        build_cohort_reform_calendar(
            inputs["legal"],
            scenario,
        )
    )

    if scenario.life_expectancy_indexation or scenario.pivot_age_months is not None:
        raise NotImplementedError("Pivot et indexation EV ne sont pas encore implementes dans ce moteur AOD.")

    calendar_changes = cohort_calendar["delta_aod_months"].ne(0).any()
    if reform_aod_months == baseline_aod_months and calendar_changes:
        raise ValueError(
            "AOD de calibration identiques mais scenario juridique non neutre. "
            "Pour le statu quo, utiliser scenario_id='statu_quo' avec 768, 768."
        )
    if reform_aod_months != baseline_aod_months and not calendar_changes:
        raise ValueError("Le calendrier est neutre mais les AOD de calibration different.")
    if (cohort_calendar["delta_aod_months"] < 0).any():
        raise NotImplementedError("Les baisses d'AOD ne sont pas implementees dans ce moteur.")
    if scenario.pace_months_per_generation in (None, 0) and scenario.aod_target_months is None:
        if reform_aod_months - baseline_aod_months != scenario.aod_shift_months:
            raise ValueError("Le decalage de calibration differe du decalage du scenario juridique.")
    neutral = not calendar_changes

    monthly_delay = (
        expand_delay_to_calendar_months(
            cohort_calendar
        )
    )

    annual_delay = (
        aggregate_delay_by_year(
            monthly_delay
        )
    )

    if neutral:
        annual_delay = pd.DataFrame({
            "year": range(START_YEAR, END_YEAR + 1),
            "cohort_months_delayed": 0,
        })

    # ------------------------------------------------------------------
    # 2. Distribution observée des âges de liquidation
    # ------------------------------------------------------------------

    age_distribution = (
        build_age_distribution(
            inputs["liquidation_age"]
        )
    )

    monthly_age_distribution = (
        expand_age_distribution_to_months(
            age_distribution
        )
    )

    gross_exposure = (
        compute_potentially_exposed_liquidations(
            monthly_age_distribution,
            baseline_aod_months,
            reform_aod_months,
        )
    )

    if neutral:
        gross_exposure = pd.DataFrame({
            "sex": sorted(age_distribution["sex"].unique()),
            "potential_exposed_effectifs": 0.0,
            "potential_exposed_share": 0.0,
        })

    # 3. Ancienne méthode :
    # ------------------------------------------------------------------
    #    exposition observée à l'âge de référence
    #    Conservée uniquement comme diagnostic historique.
    # ------------------------------------------------------------------

    group_distribution = (
        build_group_distribution(
            inputs["liquidation_groups"]
        )
    )

    allocated_exposure = (
        allocate_exposure_by_group(
            gross_exposure,
            group_distribution,
        )
    )

    observed_movable_reference = (
        compute_standard_aod_movable_exposure(
            allocated_exposure
        )
    )

    # ------------------------------------------------------------------
    # 4. Reconstruction provisoire du scénario de référence
    # ------------------------------------------------------------------

    reference_liquidation_detail = (
        build_reference_liquidation_distribution(
            age_distribution,
            group_distribution,
            reference_aod_months=(
                baseline_aod_months
            ),
            observed_standard_age_floor_months=(
                REFERENCE_FLOOR_AOD_MONTHS
            ),
        )
    )

    reference_liquidation_distribution = (
        aggregate_reference_distribution(
            reference_liquidation_detail
        )
    )

    # Population exposée utilisée par le moteur.
    movable_reference = (
        compute_reference_aod_exposure(
            reference_liquidation_distribution,
            baseline_aod_months=(
                baseline_aod_months
            ),
            reform_aod_months=(
                reform_aod_months
            ),
        )
    )

    # 5. Diagnostic annuel des liquidations déplacées
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------

    displaced_by_sex = (
        calibrate_displaced_liquidations(
            annual_delay,
            movable_reference,
            steady_state_intensity=(
                steady_state_intensity
            ),
        )
    )

    displaced_annual = (
        aggregate_displaced_liquidations(
            displaced_by_sex
        )
    )

    # ------------------------------------------------------------------
    # 6. Stock mensuel des personnes dont la liquidation est retardée
    # ------------------------------------------------------------------

    delayed_stock_detail = (
        build_monthly_delayed_stock(
            cohort_calendar,
            movable_reference,
        )
    )

    monthly_delayed_stock = (
        aggregate_monthly_stock(
            delayed_stock_detail
        )
    )

    annual_delayed_stock = (
        aggregate_annual_stock(
            monthly_delayed_stock,
            start_year=START_YEAR,
            end_year=END_YEAR,
        )
    )

    # ------------------------------------------------------------------
    # 7. Montée en charge du scénario de référence vers l'AOD cible
    # ------------------------------------------------------------------

    if neutral and baseline_aod_months <= REFERENCE_FLOOR_AOD_MONTHS:
        reference_transition = pd.DataFrame({
            "year": range(START_YEAR, END_YEAR + 1),
            "reference_maturity_factor": 1.0,
            "transition_method": "neutral_no_adjustment",
            "calibration_status": "neutral",
        })
    else:
        reference_transition = (
            build_reference_aod_transition(
                inputs["legal"],
                floor_aod_months=(
                    REFERENCE_FLOOR_AOD_MONTHS
                ),
                target_aod_months=(
                    baseline_aod_months
                ),
            )
        )
    annual_delayed_stock = (
        apply_reference_transition(
            annual_delayed_stock,
            reference_transition,
        )
    )

    annual_delayed_stock["delayed_person_years_transition_adjusted"] = (
        annual_delayed_stock["annual_average_delayed_stock_transition_adjusted"]
    )
    # ---------------------------------------------------------
    # 7 bis. Selection explicite de la methode de transition
    # ---------------------------------------------------------
    # Historique par defaut : maintien des anciens resultats.
    # Les autres methodes restent experimentales.

    transition_stock_selection = select_transition_stock(
        cohort_calendar=cohort_calendar,
        delayed_stock_detail=delayed_stock_detail,
        annual_delayed_stock=annual_delayed_stock,
        method=transition_method,
        effective_date=effective_date,
    )

    # Le stock historique demeure inchange dans
    # annual_delayed_stock pour les audits.
    # Seule la copie transmise au calcul d'emploi change.

    labour_stock_input = transition_stock_selection.copy()

    labour_stock_input[
        "annual_average_delayed_stock"
    ] = labour_stock_input[
        "selected_delayed_stock"
    ]
    # ------------------------------------------------------------------
    # 8. Effet sur le marché du travail
    # ------------------------------------------------------------------

    labour_trajectory = (
        build_labour_effect_from_stock(
            labour_stock_input,
            behavioural_delay_share=(
                behavioural_delay_share
            ),
            absorption_rate=(
                absorption_rate
            ),
        )
    )

    # ---------------------------------------------------------
    # Diagnostic complementaire du marche du travail
    # ---------------------------------------------------------
    # Cette branche ne remplace pas labour_trajectory.
    # Les comportements restent provisoires et parametrables.

    annual_delayed_stock_by_sex = (
        select_transition_stock_by_sex(
            cohort_calendar=cohort_calendar,
            delayed_stock_detail=delayed_stock_detail,
            reference_transition=reference_transition,
            transition_stock_selection=transition_stock_selection,
            start_year=START_YEAR,
            end_year=END_YEAR,
            method=transition_method,
            effective_date=effective_date,
        )
    )

    annual_delayed_stock_by_sex = select_transition_stock_by_sex(
        cohort_calendar=cohort_calendar,
        delayed_stock_detail=delayed_stock_detail,
        reference_transition=reference_transition,
        transition_stock_selection=transition_stock_selection,
        start_year=START_YEAR,
        end_year=END_YEAR,
        method=transition_method,
        effective_date=effective_date,
    )

    labour_status_2025 = pd.read_parquet(
        PROCESSED_DIR / "labour_status_rates.parquet"
    )

    pre_retirement_rates = (
        build_pre_retirement_status_rates(
            labour_status_2025,
            age_group="60-64",
        )
    )

    pre_retirement_status_stock = build_status_stock(
        annual_delayed_stock_by_sex,
        pre_retirement_rates,
    )

    labour_behaviour_trajectory = (
        build_labour_effect_by_status(
            pre_retirement_status_stock,
            employment_retention_rate=1.0,
            unemployed_activity_retention_rate=1.0,
            unemployed_job_entry_rate=0.0,
            inactive_activation_rate=0.0,
            inactive_employment_rate=0.0,
        )
    )


    return {
        "cohort_calendar":
            cohort_calendar,
        "monthly_delay":
            monthly_delay,
        "annual_delay":
            annual_delay,

        "age_distribution":
            age_distribution,
        "gross_exposure":
            gross_exposure,
        "group_distribution":
            group_distribution,
        "allocated_exposure":
            allocated_exposure,

        "observed_movable_reference":
            observed_movable_reference,

        "reference_liquidation_detail":
            reference_liquidation_detail,
        "reference_liquidation_distribution":
            reference_liquidation_distribution,
        "movable_reference":
            movable_reference,

        "displaced_by_sex":
            displaced_by_sex,
        "displaced_annual":
            displaced_annual,

        "delayed_stock_detail":
            delayed_stock_detail,
        "monthly_delayed_stock":
            monthly_delayed_stock,
        "annual_delayed_stock":
            annual_delayed_stock,

        "reference_transition":
            reference_transition,

        "labour_trajectory":
            labour_trajectory,
        "annual_delayed_stock_by_sex":
            annual_delayed_stock_by_sex,

        "pre_retirement_status_stock":
            pre_retirement_status_stock,

        "labour_behaviour_trajectory":
            labour_behaviour_trajectory,
        "transition_stock_selection":
            transition_stock_selection,
    }


def get_simulation_summary(
    results: dict[str, pd.DataFrame],
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
) -> pd.DataFrame:
    """
    Produit le tableau synthétique annuel destiné
    aux modules macroéconomiques et, plus tard, à l'interface.

    Le tableau conserve séparément :
    - le stock avant correction transitoire ;
    - le facteur de maturité juridique ;
    - le stock après correction ;
    - les effets marché du travail.
    """
    stock = results[
        "annual_delayed_stock"
    ].copy()

    labour = results[
        "labour_trajectory"
    ][
        [
            "year",
            "delta_labour_force_reform",
            "delta_employment_reform",
            "delta_unemployment_reform",
        ]
    ].copy()

    summary = stock.merge(
        labour,
        on="year",
        how="left",
        validate="one_to_one",
    )

    summary = summary.loc[
        summary["year"].between(
            start_year,
            end_year,
        )
    ]

    columns = [
        "year",
        "reference_maturity_factor",
        "annual_average_delayed_stock",
        "annual_average_delayed_stock_transition_adjusted",
        "maximum_monthly_delayed_stock",
        "delayed_person_years",
        "delayed_person_years_transition_adjusted",
        "delta_labour_force_reform",
        "delta_employment_reform",
        "delta_unemployment_reform",
    ]

    missing = set(columns) - set(summary.columns)
    if missing:
        raise ValueError(f"Colonnes de synthese manquantes : {sorted(missing)}")
    if start_year > end_year:
        raise ValueError("Horizon de synthese inverse.")
    return summary[columns].sort_values("year").reset_index(drop=True)
