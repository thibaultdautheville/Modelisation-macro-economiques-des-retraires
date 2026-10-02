import pandas as pd

from src.config import MASTER_PATH


def load_sheet(sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(MASTER_PATH, sheet_name=sheet_name)


def list_sheets() -> list[str]:
    return pd.ExcelFile(MASTER_PATH).sheet_names
