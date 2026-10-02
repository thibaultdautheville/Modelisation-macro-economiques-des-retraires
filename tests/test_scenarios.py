import pytest

from src.scenario_loader import (
    get_scenario_definition,
    list_scenarios,
    load_default_scenario,
    load_scenario_catalog,
    load_scenario_config,
)


def test_catalog_contains_six_scenarios():
    catalog = load_scenario_catalog()

    assert len(catalog["scenarios"]) == 6


def test_default_scenario_is_statu_quo():
    scenario = load_default_scenario()

    assert scenario.scenario_id == "statu_quo"
    assert scenario.aod_shift_months == 0


def test_runnable_scenarios():
    runnable = list_scenarios(
        include_disabled=False
    )

    assert "statu_quo" in runnable
    assert "benchmark_aod_plus_1" in runnable
    assert "custom" in runnable

    assert "medef_option_1" not in runnable
    assert "medef_option_2" not in runnable
    assert "medef_option_3" not in runnable


def test_benchmark_configuration():
    scenario = load_scenario_config(
        "benchmark_aod_plus_1"
    )

    assert scenario.aod_shift_months == 12
    assert scenario.pace_months_per_generation is None


def test_uncalibrated_medef_scenario_is_blocked():
    definition = get_scenario_definition(
        "medef_option_1"
    )

    assert (
        definition["metadata"]["status"]
        == "to_calibrate"
    )

    with pytest.raises(RuntimeError):
        load_scenario_config(
            "medef_option_1"
        )


def test_unknown_scenario_is_rejected():
    with pytest.raises(KeyError):
        load_scenario_config(
            "scenario_inexistant"
        )