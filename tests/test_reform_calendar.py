import pandas as pd

from src.reform_calendar import (
    aggregate_delay_by_year,
    build_cohort_reform_calendar,
    expand_delay_to_calendar_months,
    retirement_date_from_age,
)
from src.schemas import ScenarioConfig


def sample_legal_calendar():
    return pd.DataFrame(
        {
            "birth_year": [
                1965,
                1965,
            ],
            "birth_month": [
                1,
                2,
            ],
            "aod_months": [
                768,
                768,
            ],
            "aod_years": [
                64.0,
                64.0,
            ],
            "dar_quarters": [
                172,
                172,
            ],
            "aad_months": [
                804,
                804,
            ],
            "aad_years": [
                67.0,
                67.0,
            ],
        }
    )


def test_retirement_date_from_age():
    year, month = retirement_date_from_age(
        birth_year=1965,
        birth_month=1,
        age_months=768,
    )

    assert year == 2029
    assert month == 1


def test_one_year_shift():
    scenario = ScenarioConfig(
        scenario_id="test",
        label="Test",
        aod_shift_months=12,
    )

    result = build_cohort_reform_calendar(
        sample_legal_calendar(),
        scenario,
    )

    assert (
        result["delta_aod_months"] == 12
    ).all()

    assert (
        result[
            "reform_eligibility_year"
        ]
        == result[
            "baseline_eligibility_year"
        ] + 1
    ).all()


def test_delay_expansion_creates_12_months_per_cohort():
    scenario = ScenarioConfig(
        scenario_id="test",
        label="Test",
        aod_shift_months=12,
    )

    calendar = build_cohort_reform_calendar(
        sample_legal_calendar(),
        scenario,
    )

    expanded = (
        expand_delay_to_calendar_months(
            calendar
        )
    )

    assert len(expanded) == 24


def test_annual_delay_aggregation():
    scenario = ScenarioConfig(
        scenario_id="test",
        label="Test",
        aod_shift_months=12,
    )

    calendar = build_cohort_reform_calendar(
        sample_legal_calendar(),
        scenario,
    )

    expanded = (
        expand_delay_to_calendar_months(
            calendar
        )
    )

    annual = aggregate_delay_by_year(
        expanded
    )

    assert (
        annual[
            "cohort_months_delayed"
        ].sum()
        == 24
    )