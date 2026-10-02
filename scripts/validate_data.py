import sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.config import MASTER_PATH

def ok(c,m):
    if not c: raise AssertionError(m)
    print(f"[PASS] {m}")

ok(MASTER_PATH.exists(),"MASTER present")
xls=pd.ExcelFile(MASTER_PATH)
required={"COR_MACRO","COR_RETRAITE","DEMOGRAPHIE","EV65","ACTIVITE_SENIORS","TRAVAIL_2025","LEGAL_AOD_DAR","LEGAL_RACL20","CNAV_LIQ_AGE","CNAV_LIQ_GROUP","BENCH_COR_AOD1"}
ok(required.issubset(xls.sheet_names),"feuilles requises presentes")
qc=pd.read_excel(MASTER_PATH,sheet_name="QC")
ok(not qc["status"].fillna("").astype(str).str.upper().eq("FAIL").any(),"QC sans FAIL")
for s in ["COR_MACRO","COR_RETRAITE","COR_SENSI_CHOM","COR_SENSI_PROD"]:
    y=set(pd.read_excel(MASTER_PATH,sheet_name=s,usecols=["year"])["year"].dropna().astype(int))
    ok(set(range(2025,2071)).issubset(y),f"{s} 2025-2070 complet")
d=pd.read_excel(MASTER_PATH,sheet_name="DEMOGRAPHIE")
ok((d["population"]>=0).all(),"demographie non negative")
ok(not d.duplicated(["year","age","sex"]).any(),"cle demographie unique")
t=pd.read_excel(MASTER_PATH,sheet_name="TRAVAIL_2025")
s=t["employment_rate"]+t["unemployed_share_population"]+t["inactive_share_population"]
ok(s.sub(1).abs().max()<=0.005,"parts travail coherentes")
l=pd.read_excel(MASTER_PATH,sheet_name="LEGAL_AOD_DAR")
ok(l["birth_month"].between(1,12).all(),"mois juridiques valides")
ok(not l.duplicated(["birth_year","birth_month"]).any(),"cohortes juridiques uniques")
ok((l["aad_months"]>=l["aod_months"]).all(),"AAD >= AOD")
b=pd.read_excel(MASTER_PATH,sheet_name="BENCH_COR_AOD1")
ok((b["min_value"]<=b["max_value"]).all(),"bornes benchmark coherentes")
print("\nVALIDATION MASTER : OK")
