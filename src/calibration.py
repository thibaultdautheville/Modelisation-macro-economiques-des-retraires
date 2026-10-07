import pandas as pd


def prepare_institutional_benchmarks(
    benchmarks: pd.DataFrame,
) -> pd.DataFrame:
    """
    Nettoie et valide les benchmarks institutionnels.

    Les benchmarks restent des bornes externes de validation.
    Ils ne sont pas utilisés ici pour forcer ou recalibrer
    automatiquement le modèle.
    """
    required = {
        "horizon_years",
        "metric",
        "min_value",
        "max_value",
        "unit",
        "source",
    }

    missing = required - set(
        benchmarks.columns
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes dans les benchmarks : "
            f"{sorted(missing)}"
        )

    out = benchmarks.copy()

    if (
        out["min_value"]
        > out["max_value"]
    ).any():
        raise ValueError(
            "Certaines bornes minimales dépassent "
            "les bornes maximales"
        )

    return (
        out
        .sort_values(
            [
                "metric",
                "horizon_years",
            ]
        )
        .reset_index(drop=True)
    )


def compare_employment_to_institutional_range(
    simulation: pd.DataFrame,
    benchmarks: pd.DataFrame,
    start_year: int = 2026,
) -> pd.DataFrame:
    """
    Compare l'emploi supplémentaire produit par le moteur
    aux fourchettes institutionnelles COR.

    Convention :
    horizon 2 ans avec start_year=2026 -> année 2027.

    Le modèle travaille en personnes.
    Le benchmark employment_thousands est converti
    en personnes.
    """
    required_simulation = {
        "year",
        "delta_employment_reform",
    }

    missing = (
        required_simulation
        - set(simulation.columns)
    )

    if missing:
        raise ValueError(
            "Colonnes manquantes dans la simulation : "
            f"{sorted(missing)}"
        )

    institutional = (
        prepare_institutional_benchmarks(
            benchmarks
        )
    )

    employment_benchmarks = (
        institutional.loc[
            institutional["metric"]
            == "employment_thousands"
        ]
        .copy()
    )

    rows = []

    for benchmark in (
        employment_benchmarks
        .itertuples(index=False)
    ):
        horizon = int(
            benchmark.horizon_years
        )

        target_year = (
            start_year
            + horizon
            - 1
        )

        model_row = simulation.loc[
            simulation["year"]
            == target_year
        ]

        if model_row.empty:
            continue

        model_value = float(
            model_row.iloc[0][
                "delta_employment_reform"
            ]
        )

        min_persons = (
            float(benchmark.min_value)
            * 1000.0
        )

        max_persons = (
            float(benchmark.max_value)
            * 1000.0
        )

        midpoint_persons = (
            min_persons
            + max_persons
        ) / 2.0

        if model_value < min_persons:
            position = "below_range"
        elif model_value > max_persons:
            position = "above_range"
        else:
            position = "within_range"

        rows.append(
            {
                "horizon_years":
                    horizon,
                "calendar_year":
                    target_year,
                "model_employment":
                    model_value,
                "benchmark_min_employment":
                    min_persons,
                "benchmark_max_employment":
                    max_persons,
                "benchmark_midpoint_employment":
                    midpoint_persons,
                "gap_to_min":
                    model_value
                    - min_persons,
                "gap_to_max":
                    model_value
                    - max_persons,
                "ratio_to_min":
                    model_value
                    / min_persons
                    if min_persons != 0
                    else float("nan"),
                "ratio_to_midpoint":
                    model_value
                    / midpoint_persons
                    if midpoint_persons != 0
                    else float("nan"),
                "position":
                    position,
                "source":
                    benchmark.source,
            }
        )

    return pd.DataFrame(rows)


def build_employment_calibration_diagnostic(
    simulation: pd.DataFrame,
    benchmarks: pd.DataFrame,
    start_year: int = 2026,
) -> pd.DataFrame:
    """
    Produit le diagnostic de calibration emploi.

    Aucun coefficient de recalage n'est appliqué.
    """
    comparison = (
        compare_employment_to_institutional_range(
            simulation=simulation,
            benchmarks=benchmarks,
            start_year=start_year,
        )
    )

    if comparison.empty:
        return comparison

    comparison[
        "requires_investigation"
    ] = (
        comparison["position"]
        != "within_range"
    )

    return comparison