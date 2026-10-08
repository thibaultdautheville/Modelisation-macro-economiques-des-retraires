
from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.simulation import (
    run_aod_simulation,
    get_simulation_summary,
)


@pytest.fixture(scope="module")
def simulations():
    common = dict(
        scenario_id="benchmark_aod_plus_1",
        baseline_aod_months=768,
        reform_aod_months=780,
        behavioural_delay_share=1.0,
        absorption_rate=1.0,
    )

    historique = run_aod_simulation(**common)

    cohortes = run_aod_simulation(
        **common,
        transition_method="calendrier_cohortes",
        effective_date=date(2026, 9, 1),
    )

    double = run_aod_simulation(
        **common,
        transition_method="double_ajustement",
        effective_date=date(2026, 9, 1),
    )

    return historique, cohortes, double


def test_historical_transition_is_unchanged(simulations):
    historique, _, _ = simulations

    selection = historique["transition_stock_selection"]

    np.testing.assert_allclose(
        selection["selected_delayed_stock"],
        selection[
            "annual_average_delayed_stock_transition_adjusted"
        ],
        rtol=0,
        atol=1e-8,
    )


def test_calendar_transition_uses_filtered_stock(simulations):
    _, cohortes, _ = simulations

    selection = cohortes["transition_stock_selection"]

    np.testing.assert_allclose(
        selection["selected_delayed_stock"],
        selection[
            "annual_average_delayed_stock_date_filtered"
        ],
        rtol=0,
        atol=1e-8,
    )


def test_double_adjustment_is_explicit(simulations):
    _, _, double = simulations

    selection = double["transition_stock_selection"]

    np.testing.assert_allclose(
        selection["selected_delayed_stock"],
        selection["hypothetical_double_filtered_stock"],
        rtol=0,
        atol=1e-8,
    )


def test_labour_effect_uses_selected_stock(simulations):
    for results in simulations:
        selection = results["transition_stock_selection"]
        labour = results["labour_trajectory"]

        comparison = selection[
            ["year", "selected_delayed_stock"]
        ].merge(
            labour[["year", "delta_employment_reform"]],
            on="year",
            validate="one_to_one",
        )

        np.testing.assert_allclose(
            comparison["delta_employment_reform"],
            comparison["selected_delayed_stock"],
            rtol=0,
            atol=1e-8,
        )


def test_reference_stock_remains_unchanged(simulations):
    historique, cohortes, double = simulations

    reference = historique["annual_delayed_stock"]

    for results in [cohortes, double]:
        pd.testing.assert_frame_equal(
            reference,
            results["annual_delayed_stock"],
        )


def test_cohort_transition_requires_date():
    with pytest.raises(ValueError):
        run_aod_simulation(
            scenario_id="benchmark_aod_plus_1",
            baseline_aod_months=768,
            reform_aod_months=780,
            transition_method="calendrier_cohortes",
        )
