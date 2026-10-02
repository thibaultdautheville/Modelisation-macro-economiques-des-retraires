import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = ROOT / "config"
SCENARIOS_PATH = CONFIG_DIR / "scenarios.yaml"
BASELINE_PATH = CONFIG_DIR / "baseline.yaml"

MASTER_PATH = Path(
    os.getenv(
        "MASTER_FILE",
        ROOT / "data" / "MASTER_DATA_RETRAITES_V1.xlsx",
    )
)

PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"

START_YEAR = 2026
END_YEAR = 2070