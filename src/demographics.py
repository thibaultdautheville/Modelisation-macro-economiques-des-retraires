import numpy as np
import pandas as pd


REQUIRED_DEMOGRAPHY_COLUMNS = {
    "year",
    "age",
    "sex",
    "population",
}

VALID_SEX = {"F", "H"}


def validate_demography(df: pd.DataFrame) -> None:
    missing = REQUIRED_DEMOGRAPHY_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing demography columns: {sorted(missing)}"
        )

    if df.empty:
        raise ValueError("Demography table is empty")

    if df[list(REQUIRED_DEMOGRAPHY_COLUMNS)].isna().any().any():
        raise ValueError("Demography contains missing required values")

    if (df["population"] < 0).any():
        raise ValueError("Population cannot be negative")

    if (df["age"] < 0).any():
        raise ValueError("Age cannot be negative")

    invalid_sex = set(df["sex"].unique()) - VALID_SEX

    if invalid_sex:
        raise ValueError(
            f"Invalid sex codes: {sorted(invalid_sex)}"
        )

    if df.duplicated(["year", "age", "sex"]).any():
        raise ValueError(
            "Duplicate year-age-sex demographic cells"
        )


def filter_simulation_horizon(
    df: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    validate_demography(df)

    if start_year > end_year:
        raise ValueError(
            "start_year must be <= end_year"
        )

    out = df.loc[
        df["year"].between(
            start_year,
            end_year,
        )
    ].copy()

    expected_years = set(
        range(start_year, end_year + 1)
    )

    observed_years = set(
        out["year"].astype(int).unique()
    )

    missing_years = (
        expected_years - observed_years
    )

    if missing_years:
        raise ValueError(
            f"Missing demographic years: "
            f"{sorted(missing_years)}"
        )

    return out


def split_to_monthly_cohorts(
    df: pd.DataFrame,
    convention: str = "uniform_1_12",
) -> pd.DataFrame:
    """
    Split each annual age-sex population cell into
    twelve synthetic monthly birth cohorts.

    Convention:
    - each birth month receives exactly 1/12 of the
      annual age-sex cell;
    - age is observed at 1 January;
    - synthetic birth year is approximated as
      year - age - 1.

    The split is a modelling convention, not an
    observed monthly demographic distribution.
    """
    validate_demography(df)

    if convention != "uniform_1_12":
        raise ValueError(
            f"Unsupported cohort convention: {convention}"
        )

    base = df.copy()

    base["population_annual"] = (
        base["population"].astype(float)
    )

    monthly = base.loc[
        base.index.repeat(12)
    ].reset_index(drop=True)

    monthly["birth_month"] = np.tile(
        np.arange(1, 13),
        len(base),
    )

    monthly["birth_year"] = (
        monthly["year"].astype(int)
        - monthly["age"].astype(int)
        - 1
    )

    monthly["population_monthly"] = (
        monthly["population_annual"] / 12.0
    )

    monthly["cohort_id"] = (
        monthly["birth_year"].astype(str)
        + "-"
        + monthly["birth_month"]
        .astype(str)
        .str.zfill(2)
    )

    return monthly[
        [
            "year",
            "age",
            "sex",
            "birth_year",
            "birth_month",
            "cohort_id",
            "population_annual",
            "population_monthly",
        ]
    ]


def build_monthly_demography(
    df: pd.DataFrame,
    start_year: int,
    end_year: int,
    convention: str = "uniform_1_12",
) -> pd.DataFrame:
    annual = filter_simulation_horizon(
        df,
        start_year,
        end_year,
    )

    return split_to_monthly_cohorts(
        annual,
        convention=convention,
    )