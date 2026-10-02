import sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.config import MASTER_PATH,PROCESSED_DIR
TABLES={"DEMOGRAPHIE":"demography.parquet","EV65":"life_expectancy_65.parquet","ACTIVITE_SENIORS":"activity_rates.parquet","TRAVAIL_2025":"labour_status_rates.parquet","COR_RETRAITE":"retirement_baseline.parquet","COR_MACRO":"macro_baseline.parquet","COR_SENSI_CHOM":"retirement_sensitivity_unemployment.parquet","COR_SENSI_PROD":"retirement_sensitivity_productivity.parquet","LEGAL_AOD_DAR":"legal_aod_dar.parquet","LEGAL_RACL20":"legal_racl20.parquet","CNAV_LIQ_AGE":"liquidation_age_counts.parquet","CNAV_LIQ_GROUP":"liquidation_groups.parquet","BENCH_COR_AOD1":"institutional_benchmarks.parquet"}
if not MASTER_PATH.exists(): raise FileNotFoundError(MASTER_PATH)
PROCESSED_DIR.mkdir(parents=True,exist_ok=True)
for sheet,name in TABLES.items():
    df=pd.read_excel(MASTER_PATH,sheet_name=sheet)
    df.to_parquet(PROCESSED_DIR/name,index=False)
    print(f"[OK] {sheet} -> {name} ({len(df)} lignes)")
print(f"\n{len(TABLES)} tables construites")
