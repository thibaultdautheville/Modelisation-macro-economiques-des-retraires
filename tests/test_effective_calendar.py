from datetime import date
import pandas as pd
import pytest
from src.effective_calendar import build_effective_cohort_calendar, compare_effective_date_stocks


def sample():
    cal = pd.DataFrame({"birth_year":[1962,1962,1962], "birth_month":[1,2,3], "baseline_eligibility_year":[2026]*3, "baseline_eligibility_month":[8,9,10], "delta_aod_months":[3,3,0]})
    detail = pd.DataFrame({"birth_year":[1962,1962,1962], "birth_month":[1,2,2], "calendar_year":[2026]*3, "calendar_month":[8,9,10], "delayed_stock_persons":[120.,240.,240.]})
    yearly = pd.DataFrame({"year":[2026],"annual_average_delayed_stock":[50.],"annual_average_delayed_stock_transition_adjusted":[25.], "reference_maturity_factor":[0.5]})
    return cal,detail,yearly


def test_gate_by_eligibility_month():
    cal,_,_ = sample()
    result=build_effective_cohort_calendar(cal,date(2026,9,1))
    assert result.eligible_under_date_rule.tolist()==[False,True,False]


def test_annual_stock_twelve_month_denominator():
    cal,detail,yearly=sample()
    gated=build_effective_cohort_calendar(cal,date(2026,9,1))
    result=compare_effective_date_stocks(detail,yearly,gated,2026,2026)
    assert result.loc[0,"annual_average_delayed_stock_date_filtered"] == pytest.approx(40.)
    assert result.loc[0,"hypothetical_double_filtered_stock"] == pytest.approx(20.)
    assert result.loc[0,"legacy_vs_filtered_difference"] == pytest.approx(15.)


def test_empty_months_and_no_affected_cohort():
    cal,detail,yearly=sample()
    gated=build_effective_cohort_calendar(cal,date(2030,1,1))
    result=compare_effective_date_stocks(detail,yearly,gated,2026,2026)
    assert result.loc[0,"annual_average_delayed_stock_date_filtered"] == 0


def test_invalid_calendar_rejected():
    cal,_,_=sample()
    cal.loc[0,"baseline_eligibility_month"]=13
    with pytest.raises(ValueError):
        build_effective_cohort_calendar(cal,date(2026,9,1))


def test_unmatched_cohorts_rejected():
    cal,detail,yearly=sample()
    detail.loc[0,"birth_year"]=1900
    with pytest.raises(ValueError):
        compare_effective_date_stocks(detail,yearly,build_effective_cohort_calendar(cal,date(2026,9,1)),2026,2026)
