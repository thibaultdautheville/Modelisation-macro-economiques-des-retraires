from src.baseline_loader import load_baseline_config


def test_baseline_horizon():
    baseline = load_baseline_config()

    assert baseline.anchor_year == 2025
    assert baseline.simulation_start_year == 2026
    assert baseline.simulation_end_year == 2070


def test_baseline_public_receipts_ratio():
    baseline = load_baseline_config()

    assert baseline.public_receipts_gdp_ratio == 0.53


def test_baseline_unemployment():
    baseline = load_baseline_config()

    assert baseline.long_term_unemployment_rate == 0.07


def test_no_official_benchmark_interpolation():
    baseline = load_baseline_config()

    assert baseline.interpolate_official_benchmarks is False


def test_monthly_cohort_convention():
    baseline = load_baseline_config()

    assert baseline.monthly_birth_cohort_split == "uniform_1_12"