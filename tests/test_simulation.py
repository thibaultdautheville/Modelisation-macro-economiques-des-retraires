import pytest

from src.simulation import (
    get_simulation_summary,
    run_aod_simulation,
)


@pytest.fixture(scope="module")
def benchmark_results():
    return run_aod_simulation(
        scenario_id="benchmark_aod_plus_1",
        baseline_aod_months=768,
        reform_aod_months=780,
        behavioural_delay_share=1.0,
        absorption_rate=1.0,
    )


def test_simulation_returns_expected_blocks(
    benchmark_results,
):
    expected = {
        "cohort_calendar",
        "monthly_delay",
        "annual_delay",
        "age_distribution",
        "gross_exposure",
        "group_distribution",
        "allocated_exposure",
        "observed_movable_reference",
        "displaced_by_sex",
        "displaced_annual",
        "labour_trajectory",
        "delayed_stock_detail",
        "monthly_delayed_stock",
        "annual_delayed_stock",
        "observed_movable_reference",
        "reference_liquidation_detail",
"reference_liquidation_distribution",
    }

def test_steady_state_stock_matches_reference(
    benchmark_results,
):
    reference = benchmark_results[
        "movable_reference"
    ][
        "movable_exposed_effectifs"
    ].sum()

    annual = benchmark_results[
        "annual_delayed_stock"
    ]

    steady_state = annual.loc[
        annual["year"] == 2040,
        "annual_average_delayed_stock",
    ].iloc[0]

    assert steady_state == pytest.approx(
        reference,
        abs=1e-6,
    )


def test_reference_exposure_is_larger_than_observed_proxy(
    benchmark_results,
):
    observed = benchmark_results[
        "observed_movable_reference"
    ][
        "movable_exposed_effectifs"
    ].sum()

    reconstructed = benchmark_results[
        "movable_reference"
    ][
        "movable_exposed_effectifs"
    ].sum()

    assert reconstructed > observed


def test_full_absorption_has_no_extra_unemployment(
    benchmark_results,
):
    labour = benchmark_results[
        "labour_trajectory"
    ]

    assert (
        labour[
            "delta_unemployment_reform"
        ].abs()
        < 1e-10
    ).all()


def test_labour_accounting_identity(
    benchmark_results,
):
    labour = benchmark_results[
        "labour_trajectory"
    ]

    gap = (
        labour[
            "delta_labour_force_reform"
        ]
        - labour[
            "delta_employment_reform"
        ]
        - labour[
            "delta_unemployment_reform"
        ]
    )

    assert gap.abs().max() < 1e-10


def test_summary_horizon(
    benchmark_results,
):
    summary = get_simulation_summary(
        benchmark_results
    )

    assert summary["year"].min() == 2026
    assert summary["year"].max() == 2070

def test_observed_reference_approximately_32174(
    benchmark_results,
):
    reference = benchmark_results[
        "observed_movable_reference"
    ]

    total = reference[
        "movable_exposed_effectifs"
    ].sum()

    assert total == pytest.approx(
        32174,
        abs=5,
    )


def test_reconstructed_reference_approximately_231023(
    benchmark_results,
):
    reference = benchmark_results[
        "movable_reference"
    ]

    total = reference[
        "movable_exposed_effectifs"
    ].sum()

    assert total == pytest.approx(
        231023,
        abs=10,
    )

def test_reference_exposure_approximately_231000(
    benchmark_results,
):
    total = benchmark_results[
        "movable_reference"
    ][
        "movable_exposed_effectifs"
    ].sum()

    assert total == pytest.approx(
        231023,
        abs=10,
    )

def test_reference_transition_is_applied(
    benchmark_results,
):
    annual = benchmark_results[
        "annual_delayed_stock"
    ]

    factor_2026 = annual.loc[
        annual["year"] == 2026,
        "reference_maturity_factor",
    ].iloc[0]

    factor_2033 = annual.loc[
        annual["year"] == 2033,
        "reference_maturity_factor",
    ].iloc[0]

    assert factor_2026 < 1.0
    assert factor_2033 == pytest.approx(
        1.0
    )

    