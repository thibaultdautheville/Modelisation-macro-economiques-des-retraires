
from datetime import date

import numpy as np
import pytest

from src.simulation import run_aod_simulation


@pytest.fixture(scope="module")
def scenario_results():
    common = {
        "scenario_id": "benchmark_aod_plus_1",
        "baseline_aod_months": 768,
        "reform_aod_months": 780,
    }

    return {
        "historique": run_aod_simulation(
            **common,
        ),
        "calendrier_cohortes": run_aod_simulation(
            **common,
            transition_method="calendrier_cohortes",
            effective_date=date(2026, 9, 1),
        ),
        "double_ajustement": run_aod_simulation(
            **common,
            transition_method="double_ajustement",
            effective_date=date(2026, 9, 1),
        ),
    }


@pytest.mark.parametrize(
    "method",
    [
        "historique",
        "calendrier_cohortes",
        "double_ajustement",
    ],
)
def test_selected_stock_is_conserved_by_sex(
    scenario_results,
    method,
):
    results = scenario_results[method]

    by_sex = results[
        "annual_delayed_stock_by_sex"
    ]

    selected = results[
        "transition_stock_selection"
    ]

    totals = by_sex.groupby("year")[
        "selected_delayed_stock_by_sex"
    ].sum()

    expected = selected.set_index("year")[
        "selected_delayed_stock"
    ]

    np.testing.assert_allclose(
        totals.loc[expected.index],
        expected,
        rtol=1e-10,
        atol=1e-6,
    )


@pytest.mark.parametrize(
    "method",
    [
        "historique",
        "calendrier_cohortes",
        "double_ajustement",
    ],
)
def test_status_decomposition_is_conserved(
    scenario_results,
    method,
):
    status = scenario_results[method][
        "pre_retirement_status_stock"
    ]

    total = (
        status["previously_employed"]
        + status["previously_unemployed"]
        + status["previously_inactive"]
    )

    np.testing.assert_allclose(
        total,
        status["annual_average_delayed_stock_adjusted"],
        rtol=1e-10,
        atol=1e-6,
    )


@pytest.mark.parametrize(
    "method",
    [
        "historique",
        "calendrier_cohortes",
        "double_ajustement",
    ],
)
def test_labour_accounting_identity(
    scenario_results,
    method,
):
    behaviour = scenario_results[method][
        "labour_behaviour_trajectory"
    ]

    np.testing.assert_allclose(
        behaviour["delta_labour_force_reform"],
        behaviour["delta_employment_reform"]
        + behaviour["delta_unemployment_reform"],
        rtol=1e-10,
        atol=1e-6,
    )


def test_historical_employment_benchmark_is_preserved(
    scenario_results,
):
    results = scenario_results["historique"]

    labour = results["labour_trajectory"]

    value = labour.loc[
        labour["year"].eq(2035),
        "delta_employment_reform",
    ].iloc[0]

    assert value == pytest.approx(
        231022.763576,
        abs=0.01,
    )
