import pandas as pd
from src.config import PROCESSED_DIR

def test_demography():
    d=pd.read_parquet(PROCESSED_DIR/"demography.parquet")
    assert (d["population"]>=0).all()
    assert not d.duplicated(["year","age","sex"]).any()

def test_retirement_years():
    d=pd.read_parquet(PROCESSED_DIR/"retirement_baseline.parquet")
    assert set(range(2026,2071)).issubset(set(d["year"].astype(int)))

def test_legal():
    d=pd.read_parquet(PROCESSED_DIR/"legal_aod_dar.parquet")
    assert d["birth_month"].between(1,12).all()
    assert not d.duplicated(["birth_year","birth_month"]).any()
    assert (d["aad_months"]>=d["aod_months"]).all()

def test_benchmark():
    d=pd.read_parquet(PROCESSED_DIR/"institutional_benchmarks.parquet")
    assert (d["min_value"]<=d["max_value"]).all()
