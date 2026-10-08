from pathlib import Path
import pandas as pd
import pytest

from src.cnav_crossed import (
    load_observed_cnav_cross, reconcile_cnav_cross, compare_allocation_methods
)

SOURCE = Path(__file__).resolve().parents[1] / 'data/derived/cnav_age_group_2024.csv'


def test_real_source_totals_and_open_class():
    d = load_observed_cnav_cross(SOURCE)
    assert len(d) == 144
    open_rows = d[(d['open_age_class']) & d['sex'].isin(['F', 'H'])]
    assert open_rows.groupby('sex')['effectifs'].sum().to_dict() == {'F': 9083, 'H': 6498}
    assert open_rows['age_numeric'].isna().all()
    assert d[d['sex'].isin(['F', 'H'])]['effectifs'].sum() == 648346


def test_reconciliation_with_observed_closed_ages():
    d = load_observed_cnav_cross(SOURCE)
    ages = (d[(d['sex'].isin(['F', 'H'])) & ~d['open_age_class']]
            .groupby(['sex', 'age_numeric'], as_index=False)['effectifs'].sum())
    result = reconcile_cnav_cross(d, ages)
    assert (result['ecart'] == 0).all()
    ages.loc[0, 'effectifs'] += 1
    with pytest.raises(ValueError, match='ne concorde pas'):
        reconcile_cnav_cross(d, ages)


def test_comparison_preserves_original_and_observed():
    d = load_observed_cnav_cross(SOURCE)
    independ = d[d['sex'].isin(['F', 'H']) & ~d['open_age_class']][['sex','age_numeric','group_code','effectifs']].copy()
    independ['allocated_effectifs'] = independ.pop('effectifs') * 0.9
    out = compare_allocation_methods(d, independ)
    assert out['observed_effectifs'].sum() == pytest.approx(632765)
    assert out['independent_effectifs'].sum() == pytest.approx(632765 * .9)
