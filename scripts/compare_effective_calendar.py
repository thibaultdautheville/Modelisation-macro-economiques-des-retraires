"""Produit la comparaison non active du filtrage des cohortes par date d'effet."""
from datetime import date
from pathlib import Path
import argparse
from src.simulation import run_aod_simulation
from src.effective_calendar import build_effective_cohort_calendar, compare_effective_date_stocks
from src.config import START_YEAR, END_YEAR


def main():
    parser = argparse.ArgumentParser(description="Diagnostic de date d'effet par cohorte")
    parser.add_argument("--date-effet", default="2026-09-01", help="Hypothese candidate AAAA-MM-JJ, non validee juridiquement")
    parser.add_argument("--sortie", default="data/audit/etape_e/calendrier_effectif_diagnostic.csv")
    args = parser.parse_args()
    effective_date = date.fromisoformat(args.date_effet)
    results = run_aod_simulation("benchmark_aod_plus_1", 768, 780, 1., 1.)
    cohort = build_effective_cohort_calendar(results["cohort_calendar"], effective_date)
    table = compare_effective_date_stocks(results["delayed_stock_detail"], results["annual_delayed_stock"], cohort, START_YEAR, END_YEAR)
    dest = Path(args.sortie)
    dest.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(dest,index=False,encoding="utf-8-sig")
    print("DATE CANDIDATE, NON VALIDEE JURIDIQUEMENT :", effective_date)
    print("CALIBRATION DU MODELE PRINCIPAL : INCHANGEE")
    print(table.loc[table.year.isin([2026,2027,2030,2035,2045]),["year","annual_average_delayed_stock","annual_average_delayed_stock_transition_adjusted","annual_average_delayed_stock_date_filtered","hypothetical_double_filtered_stock"]].to_string(index=False))
    print("CSV :",dest)

if __name__ == "__main__":
    main()
