import pandas as pd
import pytest
from src.reform_calendar import expand_delay_to_calendar_months
from src.reform_stock import aggregate_annual_stock, aggregate_monthly_stock, build_monthly_delayed_stock


def calendar():
    return pd.DataFrame({"birth_year": [1965], "birth_month": [1], "delta_aod_months": [0],
                         "baseline_eligibility_year": [2029], "baseline_eligibility_month": [1]})


def test_empty_delay_keeps_schema():
    result = expand_delay_to_calendar_months(calendar())
    assert result.empty
    assert "calendar_year" in result


def test_empty_stock_has_complete_annual_calendar():
    reference = pd.DataFrame({"sex": ["F", "H"], "movable_exposed_effectifs": [0.0, 0.0]})
    detail = build_monthly_delayed_stock(calendar(), reference)
    monthly = aggregate_monthly_stock(detail)
    annual = aggregate_annual_stock(monthly, 2026, 2070)
    assert annual.year.tolist() == list(range(2026, 2071))
    assert (annual.drop(columns="year") == 0).all().all()


def test_empty_stock_rejects_reversed_horizon():
    monthly = pd.DataFrame(columns=["year", "month", "delayed_stock_persons"])
    with pytest.raises(ValueError):
        aggregate_annual_stock(monthly, 2070, 2026)
