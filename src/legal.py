import pandas as pd

from src.schemas import ScenarioConfig


REQUIRED_LEGAL_COLUMNS = {
    "birth_year",
    "birth_month",
    "aod_months",
    "aod_years",
    "dar_quarters",
    "aad_months",
    "aad_years",
}


def cohort_index(year: int, month: int) -> int:
    if not 1 <= month <= 12:
        raise ValueError("birth_month must be between 1 and 12")
    return year * 12 + month - 1


def validate_legal_calendar(df: pd.DataFrame) -> None:
    missing = REQUIRED_LEGAL_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(f"Missing legal columns: {sorted(missing)}")

    if not df["birth_month"].between(1, 12).all():
        raise ValueError("Invalid birth month")

    if df.duplicated(["birth_year", "birth_month"]).any():
        raise ValueError("Duplicate monthly birth cohorts")

    if (df["aod_months"] <= 0).any():
        raise ValueError("AOD must be positive")

    if (df["aad_months"] < df["aod_months"]).any():
        raise ValueError("AAD cannot be below AOD")


def get_legal_rule(
    df: pd.DataFrame,
    birth_year: int,
    birth_month: int,
) -> dict:
    validate_legal_calendar(df)

    mask = (
        (df["birth_year"] == birth_year)
        & (df["birth_month"] == birth_month)
    )

    rows = df.loc[mask]

    if len(rows) != 1:
        raise KeyError(
            f"No unique legal rule for {birth_year}-{birth_month:02d}"
        )

    return rows.iloc[0].to_dict()


def apply_aod_scenario(
    df: pd.DataFrame,
    scenario: ScenarioConfig,
) -> pd.DataFrame:
    validate_legal_calendar(df)

    out = df.copy()

    out["aod_months_baseline"] = out["aod_months"].astype(int)
    out["aod_months_reform"] = out["aod_months_baseline"]

    affected = pd.Series(True, index=out.index)

    if scenario.first_affected_birth_year is not None:
        threshold = cohort_index(
            scenario.first_affected_birth_year,
            scenario.first_affected_birth_month,
        )

        cohort = (
            out["birth_year"].astype(int) * 12
            + out["birth_month"].astype(int)
            - 1
        )

        affected = cohort >= threshold

    if scenario.pace_months_per_generation not in (None, 0):
        if scenario.first_affected_birth_year is None:
            raise ValueError(
                "first_affected_birth_year is required for progressive pace"
            )

        shift = progressive_aod_shift(
            out["birth_year"],
            scenario.first_affected_birth_year,
            scenario.pace_months_per_generation,
        )
    else:
        shift = scenario.aod_shift_months

    shifted = out["aod_months_baseline"] + shift

    if scenario.aod_target_months is not None:
        if scenario.pace_months_per_generation not in (None, 0):
            shifted = shifted.clip(
                upper=scenario.aod_target_months
            )
        elif scenario.aod_shift_months >= 0:
            shifted = shifted.clip(
                upper=scenario.aod_target_months
            )
        else:
            shifted = shifted.clip(
                lower=scenario.aod_target_months
            )

    out.loc[affected, "aod_months_reform"] = shifted.loc[affected]

    out["delta_aod_months"] = (
        out["aod_months_reform"] - out["aod_months_baseline"]
    )

    out["aod_years_reform"] = out["aod_months_reform"] / 12

    return out


def progressive_aod_shift(
    birth_year: pd.Series,
    first_birth_year: int,
    pace_months_per_generation: int,
) -> pd.Series:
    """Additional AOD months by birth generation."""
    step = (
        birth_year.astype(int)
        - first_birth_year
        + 1
    ).clip(lower=0)

    return step * pace_months_per_generation