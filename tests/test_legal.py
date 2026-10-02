import pandas as pd
import pytest

from src.legal import (
    apply_aod_scenario,
    cohort_index,
    get_legal_rule,
    validate_legal_calendar,
)
from src.schemas import ScenarioConfig


def sample_calendar():
    return pd.DataFrame(
        {
            "birth_year": [1964, 1965, 1965],
            "birth_month": [12, 1, 2],
            "aod_months": [756, 768, 771],
            "aod_years": [63.0, 64.0, 64.25],
            "dar_quarters": [171, 172, 172],
            "aad_months": [804, 804, 804],
            "aad_years": [67.0, 67.0, 67.0],
        }
    )


def test_cohort_index_is_monthly():
    assert cohort_index(1965, 1) + 1 == cohort_index(1965, 2)


def test_calendar_validation():
    validate_legal_calendar(sample_calendar())


def test_rule_lookup():
    rule = get_legal_rule(sample_calendar(), 1965, 1)
    assert rule["aod_months"] == 768


def test_uniform_shift_from_first_cohort_with_cap():
    df = sample_calendar()

    scenario = ScenarioConfig(
        scenario_id="test_aod_plus_1",
        label="Test +1 year",
        aod_shift_months=12,
        aod_target_months=780,
        first_affected_birth_year=1965,
        first_affected_birth_month=1,
    )

    result = apply_aod_scenario(df, scenario)

    assert result.loc[0, "delta_aod_months"] == 0
    assert result.loc[1, "delta_aod_months"] == 12
    assert result.loc[2, "aod_months_reform"] == 780
    assert df.loc[1, "aod_months"] == 768


def test_progressive_pace_not_implemented_yet():
    scenario = ScenarioConfig(
        scenario_id="progressive",
        label="Progressive",
        aod_shift_months=12,
        pace_months_per_generation=3,
    )

    with pytest.raises(NotImplementedError):
        apply_aod_scenario(sample_calendar(), scenario)
