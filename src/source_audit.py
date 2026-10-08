"""Comparaisons de valeurs stockees, sans recalcul ni modification des sources."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from numbers import Real

TABLES = {
    'DEMOGRAPHIE': 'demography.parquet',
    'EV65': 'life_expectancy_65.parquet',
    'ACTIVITE_SENIORS': 'activity_rates.parquet',
    'TRAVAIL_2025': 'labour_status_rates.parquet',
    'COR_RETRAITE': 'retirement_baseline.parquet',
    'COR_MACRO': 'macro_baseline.parquet',
    'COR_SENSI_CHOM': 'retirement_sensitivity_unemployment.parquet',
    'COR_SENSI_PROD': 'retirement_sensitivity_productivity.parquet',
    'LEGAL_AOD_DAR': 'legal_aod_dar.parquet',
    'LEGAL_RACL20': 'legal_racl20.parquet',
    'CNAV_LIQ_AGE': 'liquidation_age_counts.parquet',
    'CNAV_LIQ_GROUP': 'liquidation_groups.parquet',
    'BENCH_COR_AOD1': 'institutional_benchmarks.parquet',
}

GROUPS = {
    'depart_droit_commun': 'droit_commun',
    'liq_racl': 'carriere_longue',
    'amiante': 'sante_invalidite_inaptitude',
    'incapacit\u00e9_permanente': 'sante_invalidite_inaptitude',
    'ex_inval1': 'sante_invalidite_inaptitude',
    'ex_inval23': 'sante_invalidite_inaptitude',
    'inaptes': 'sante_invalidite_inaptitude',
    'autres_departs_anticipes': 'autres',
    'autres_departs_txplein': 'autres',
}
SEX = {'Femmes': 'F', 'Hommes': 'H', 'Ensemble': 'T'}


def missing(value):
    return value is None or (isinstance(value, Real) and math.isnan(value))


def equivalent(left, right, atol=1e-10, rtol=1e-12):
    if missing(left) or missing(right):
        return missing(left) and missing(right)
    if isinstance(left, Real) and isinstance(right, Real):
        return math.isclose(left, right, abs_tol=atol, rel_tol=rtol)
    return left == right


def parse_range(value):
    """Bornes publiees; aucune interpolation ou moyenne des modeles."""
    if isinstance(value, Real):
        return float(value), float(value)
    text = str(value).replace(',', '.').replace('\u2212', '-').replace('\u00a0', ' ')
    vals = [float(x.replace(' ', '')) for x in re.findall(r'[+\-]?\s*\d+(?:\.\d+)?', text)]
    if len(vals) == 1:
        return vals[0], vals[0]
    if len(vals) == 2:
        return min(vals), max(vals)
    raise ValueError(f'Fourchette non reconnue : {value!r}')


@dataclass
class Audit:
    checks: list = field(default_factory=list)
    cells: list = field(default_factory=list)

    def compare(self, check_id, table, variable, pairs, source, sheet, transformation='identite', note='', atol=1e-10, rtol=1e-12):
        differences = []
        n = 0
        for key, model, official, address in pairs:
            ok = equivalent(model, official, atol, rtol)
            gap = abs(float(model)-float(official)) if isinstance(model, Real) and isinstance(official, Real) and not missing(model) and not missing(official) else None
            if not ok:
                differences.append((key, model, official))
            self.cells.append({
                'controle':check_id, 'table':table, 'variable':variable,
                'cle':str(key), 'valeur_modele':None if missing(model) else model,
                'valeur_source_transformee':None if missing(official) else official,
                'ecart_absolu':gap, 'concordance':ok, 'fichier_source':source,
                'feuille':sheet, 'cellule':address, 'transformation':transformation,
            })
            n += 1
        gaps=[r['ecart_absolu'] for r in self.cells[-n:] if r['ecart_absolu'] is not None] if n else []
        self.checks.append({
            'controle':check_id, 'table':table, 'variable':variable,
            'statut':'ECART' if differences else ('CONFORME' if n else 'NON_VERIFIE'),
            'valeurs_comparees':n, 'ecarts':len(differences),
            'ecart_max':max(gaps, default=0.0), 'fichier_source':source,
            'feuille':sheet, 'transformation':transformation, 'note':note,
        })
        return differences

    def notice(self, check_id, table, status, note, source='', sheet=''):
        self.checks.append({'controle':check_id,'table':table,'variable':'', 'statut':status,
                            'valeurs_comparees':0,'ecarts':0,'ecart_max':None,
                            'fichier_source':source,'feuille':sheet,'transformation':'','note':note})
