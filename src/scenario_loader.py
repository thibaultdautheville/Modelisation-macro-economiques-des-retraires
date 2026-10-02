from pathlib import Path

import yaml

from src.config import SCENARIOS_PATH
from src.schemas import ScenarioConfig


def load_scenario_catalog(
    path: Path = SCENARIOS_PATH,
) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Scenario configuration not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError("Invalid scenarios YAML")

    if "scenarios" not in data:
        raise ValueError("Missing 'scenarios' section")

    if "default_scenario" not in data:
        raise ValueError("Missing 'default_scenario'")

    return data


def list_scenarios(
    include_disabled: bool = True,
) -> list[str]:
    catalog = load_scenario_catalog()

    scenarios = catalog["scenarios"]

    if include_disabled:
        return list(scenarios)

    return [
        scenario_id
        for scenario_id, definition in scenarios.items()
        if definition["metadata"].get("runnable", False)
    ]


def get_scenario_definition(
    scenario_id: str,
) -> dict:
    catalog = load_scenario_catalog()

    scenarios = catalog["scenarios"]

    if scenario_id not in scenarios:
        raise KeyError(
            f"Unknown scenario: {scenario_id}"
        )

    return scenarios[scenario_id]


def load_scenario_config(
    scenario_id: str,
    require_runnable: bool = True,
) -> ScenarioConfig:
    definition = get_scenario_definition(
        scenario_id
    )

    metadata = definition.get("metadata", {})

    if (
        require_runnable
        and not metadata.get("runnable", False)
    ):
        raise RuntimeError(
            f"Scenario '{scenario_id}' is not runnable. "
            f"Status: {metadata.get('status', 'unknown')}"
        )

    parameters = definition.get(
        "parameters",
        {}
    )

    config = ScenarioConfig(
        **parameters
    )

    if config.scenario_id != scenario_id:
        raise ValueError(
            "Scenario key and scenario_id differ: "
            f"{scenario_id} != {config.scenario_id}"
        )

    return config


def load_default_scenario() -> ScenarioConfig:
    catalog = load_scenario_catalog()

    return load_scenario_config(
        catalog["default_scenario"]
    )