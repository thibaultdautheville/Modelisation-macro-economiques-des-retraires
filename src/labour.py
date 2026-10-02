import pandas as pd


REQUIRED_LABOUR_RATE_COLUMNS = {
    "year",
    "age_group",
    "sex",
    "activity_rate",
    "employment_rate",
    "unemployment_rate",
    "unemployed_share_population",
    "inactive_share_population",
}


def validate_labour_rates(
    df: pd.DataFrame,
    tolerance: float = 0.01,
) -> None:
    missing = (
        REQUIRED_LABOUR_RATE_COLUMNS
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            f"Missing labour-rate columns: {sorted(missing)}"
        )

    if df.empty:
        raise ValueError(
            "Labour-rate table is empty"
        )

    if df.duplicated(
        ["year", "age_group", "sex"]
    ).any():
        raise ValueError(
            "Duplicate year-age_group-sex rows"
        )

    rate_columns = [
        "activity_rate",
        "employment_rate",
        "unemployment_rate",
        "unemployed_share_population",
        "inactive_share_population",
    ]

    for column in rate_columns:
        if not df[column].between(0, 1).all():
            raise ValueError(
                f"{column} must be between 0 and 1"
            )

    status_sum = (
        df["employment_rate"]
        + df["unemployed_share_population"]
        + df["inactive_share_population"]
    )

    if status_sum.sub(1).abs().max() > tolerance:
        raise ValueError(
            "Employment + unemployment + inactivity "
            "shares do not sum to 1"
        )

    active_share = (
        df["employment_rate"]
        + df["unemployed_share_population"]
    )

    if (
        active_share
        .sub(df["activity_rate"])
        .abs()
        .max()
        > tolerance
    ):
        raise ValueError(
            "Activity rate is inconsistent "
            "with employment and unemployment shares"
        )


def compute_baseline_labour_status(
    df: pd.DataFrame,
    population_col: str = "population",
    activity_rate_col: str = "activity_rate",
    unemployment_rate_col: str = "unemployment_rate",
) -> pd.DataFrame:
    required = {
        population_col,
        activity_rate_col,
        unemployment_rate_col,
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    if (df[population_col] < 0).any():
        raise ValueError(
            "Population cannot be negative"
        )

    for column in [
        activity_rate_col,
        unemployment_rate_col,
    ]:
        if not df[column].between(0, 1).all():
            raise ValueError(
                f"{column} must be between 0 and 1"
            )

    out = df.copy()

    out["labour_force_baseline"] = (
        out[population_col]
        * out[activity_rate_col]
    )

    out["unemployment_baseline"] = (
        out["labour_force_baseline"]
        * out[unemployment_rate_col]
    )

    out["employment_baseline"] = (
        out["labour_force_baseline"]
        - out["unemployment_baseline"]
    )

    out["inactive_baseline"] = (
        out[population_col]
        - out["labour_force_baseline"]
    )

    return out


def simulate_reform_absorption(
    inflows: pd.DataFrame,
    absorption_rate: float,
) -> pd.DataFrame:
    """
    Simulate absorption of additional labour-force inflows.

    new_active_reform is a yearly flow of people remaining
    in, or entering, the labour force because of the reform.

    Additional unemployment is kept separate from baseline
    unemployment.

    With absorption_rate = 1:
    all additional labour supply is absorbed immediately
    into employment.

    With absorption_rate = 0:
    all additional labour supply remains in additional
    unemployment.
    """
    required = {
        "year",
        "new_active_reform",
    }

    missing = required - set(inflows.columns)

    if missing:
        raise ValueError(
            f"Missing reform-flow columns: {sorted(missing)}"
        )

    if not 0 <= absorption_rate <= 1:
        raise ValueError(
            "absorption_rate must be between 0 and 1"
        )

    if inflows["year"].duplicated().any():
        raise ValueError(
            "One reform-flow row per year is required"
        )

    if (inflows["new_active_reform"] < 0).any():
        raise ValueError(
            "new_active_reform cannot be negative"
        )

    ordered = (
        inflows
        .sort_values("year")
        .reset_index(drop=True)
        .copy()
    )

    employment_stock = 0.0
    unemployment_stock = 0.0

    results = []

    for row in ordered.itertuples(index=False):
        new_active = float(
            row.new_active_reform
        )

        available = (
            unemployment_stock
            + new_active
        )

        newly_absorbed = (
            absorption_rate
            * available
        )

        employment_stock += newly_absorbed

        unemployment_stock = (
            available
            - newly_absorbed
        )

        labour_force_stock = (
            employment_stock
            + unemployment_stock
        )

        results.append(
            {
                "year": int(row.year),
                "new_active_reform": new_active,
                "absorption_rate": absorption_rate,
                "newly_absorbed_employment": newly_absorbed,
                "delta_employment_reform": employment_stock,
                "delta_unemployment_reform": unemployment_stock,
                "delta_labour_force_reform": labour_force_stock,
            }
        )

    return pd.DataFrame(results)