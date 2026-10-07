import pandas as pd


DG_TRESOR_EMPLOYMENT_BENCHMARK = {
    1: 29_000,
    2: 142_000,
    5: 142_000,
    10: 198_000,
    20: 210_000,
}


def compare_employment_to_benchmark(
    reform_trajectory: pd.DataFrame,
    start_year: int,
) -> pd.DataFrame:
    required = {
        "year",
        "delta_employment_reform",
    }

    missing = required - set(
        reform_trajectory.columns
    )

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    rows = []

    for horizon, benchmark in (
        DG_TRESOR_EMPLOYMENT_BENCHMARK.items()
    ):
        target_year = (
            start_year + horizon - 1
        )

        observed = reform_trajectory.loc[
            reform_trajectory["year"]
            == target_year,
            "delta_employment_reform",
        ]

        if observed.empty:
            continue

        model_value = float(
            observed.iloc[0]
        )

        gap = (
            model_value
            - benchmark
        )

        ratio = (
            model_value / benchmark
            if benchmark != 0
            else float("nan")
        )

        rows.append(
            {
                "horizon_years": horizon,
                "calendar_year": target_year,
                "model_employment": model_value,
                "benchmark_employment": benchmark,
                "gap_employment": gap,
                "model_to_benchmark_ratio": ratio,
            }
        )

    return pd.DataFrame(rows)


def implied_employment_scaling_factor(
    comparison: pd.DataFrame,
    horizon_years: int,
) -> float:
    row = comparison.loc[
        comparison["horizon_years"]
        == horizon_years
    ]

    if len(row) != 1:
        raise ValueError(
            "Horizon de benchmark introuvable"
        )

    model_value = float(
        row.iloc[0][
            "model_employment"
        ]
    )

    benchmark_value = float(
        row.iloc[0][
            "benchmark_employment"
        ]
    )

    if model_value <= 0:
        raise ValueError(
            "L'emploi simulé doit être positif"
        )

    return (
        benchmark_value
        / model_value
    )