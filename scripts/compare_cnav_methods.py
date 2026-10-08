"""Diagnostic CNAV/DREES observe vs independance du prototype, sans toucher au moteur."""
from pathlib import Path
import pandas as pd
from src.cnav_crossed import load_observed_cnav_cross, compare_allocation_methods

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/derived/cnav_age_group_2024.csv'
OUT = ROOT / 'data/audit/etape_e'


def run():
    observed = load_observed_cnav_cross(SOURCE)
    both = observed[observed['sex'].isin(['F', 'H'])].copy()
    # Parts par sexe sur l'ensemble des classes, y compris >70 :
    # correspond a la logique de la calibration historique CNAV.
    group = both.groupby(['sex', 'group_code'])['effectifs'].sum().reset_index()
    group['share'] = group['effectifs'] / group.groupby('sex')['effectifs'].transform('sum')
    closed = both[~both['open_age_class']]
    age = closed.groupby(['sex', 'age_numeric'])['effectifs'].sum().reset_index()
    independent = age.merge(group[['sex', 'group_code', 'share']], on='sex', validate='many_to_many')
    independent['allocated_effectifs'] = independent['effectifs'] * independent['share']
    comparison = compare_allocation_methods(observed, independent)
    OUT.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(OUT / 'comparaison_age_sexe_groupe.csv', index=False, encoding='utf-8-sig')
    summary = (comparison.groupby(['sex', 'group_code'], as_index=False)
               [['observed_effectifs', 'independent_effectifs', 'ecart_observe_moins_independance']].sum())
    summary.to_csv(OUT / 'synthese_groupes.csv', index=False, encoding='utf-8-sig')
    # La reconstruction a l'AOD 64 reporte les droits communs 62-63 a 64.
    # Ceci est une sensibilite indicative, non une nouvelle projection.
    exposure = comparison[comparison['group_code'].eq('droit_commun') & comparison['age_numeric'].isin([62., 63., 64.])]
    exp_summary = (exposure.groupby('sex', as_index=False)[['observed_effectifs','independent_effectifs']].sum())
    exp_summary['ecart_observe_moins_independance'] = exp_summary['observed_effectifs'] - exp_summary['independent_effectifs']
    exp_summary.to_csv(OUT / 'sensibilite_exposition_64_ans.csv', index=False, encoding='utf-8-sig')
    print('LIGNES_CROISEMENT', len(observed))
    print('TOTAL_F_H', both['effectifs'].sum())
    print('CLASSE_OUVERTE', both.loc[both['open_age_class'], 'effectifs'].sum())
    print('SENSIBILITE_DROIT_COMMUN_62_64')
    print(exp_summary.to_string(index=False))
    print('AUCUNE MODIFICATION DE LA CALIBRATION ACTIVE')


if __name__ == '__main__':
    run()
