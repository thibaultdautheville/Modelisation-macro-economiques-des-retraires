import yaml

from src.config import BASELINE_PATH
from src.schemas import BaselineConfig


def load_baseline_config() -> BaselineConfig:
    if not BASELINE_PATH.exists():
        raise FileNotFoundError(
            f"Baseline configuration not found: {BASELINE_PATH}"
        )

    with BASELINE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "Invalid baseline YAML"
        )

    if "baseline" not in data:
        raise ValueError(
            "Missing 'baseline' section"
        )

    return BaselineConfig(
        **data["baseline"]
    )