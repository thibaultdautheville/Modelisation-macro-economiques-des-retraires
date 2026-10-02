from pydantic import BaseModel, Field, model_validator


class ScenarioConfig(BaseModel):
    scenario_id: str
    label: str

    aod_shift_months: int = 0
    aod_target_months: int | None = None

    first_affected_birth_year: int | None = None
    first_affected_birth_month: int = 1

    pace_months_per_generation: int | None = None

    pivot_age_months: int | None = None
    behavioural_delay_share: float = Field(default=1.0, ge=0.0, le=1.0)

    life_expectancy_indexation: bool = False
    lambda_ev: float = Field(default=2 / 3, ge=0.0, le=1.0)

    long_term_unemployment_rate: float = Field(default=0.07, ge=0.0, le=1.0)
    absorption_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    relative_productivity: float = Field(default=1.0, ge=0.0)

    @model_validator(mode="after")
    def validate_scenario(self):
        if not 1 <= self.first_affected_birth_month <= 12:
            raise ValueError("first_affected_birth_month must be between 1 and 12")

        if self.aod_target_months is not None and self.aod_target_months <= 0:
            raise ValueError("aod_target_months must be positive")

        return self

from datetime import date


class BaselineConfig(BaseModel):
    baseline_id: str
    label: str

    anchor_year: int
    simulation_start_year: int
    simulation_end_year: int

    legal_freeze_target_date: date
    legal_freeze_status: str

    demography_source_id: str
    macro_source_id: str
    retirement_source_id: str

    long_term_unemployment_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    relative_productivity: float = Field(
        ge=0.0,
    )

    public_receipts_gdp_ratio: float = Field(
        ge=0.0,
        le=1.0,
    )

    monthly_birth_cohort_split: str

    interpolate_official_benchmarks: bool = False

    @model_validator(mode="after")
    def validate_baseline(self):
        if self.anchor_year >= self.simulation_start_year:
            raise ValueError(
                "anchor_year must precede simulation_start_year"
            )

        if self.simulation_start_year > self.simulation_end_year:
            raise ValueError(
                "simulation_start_year must be <= simulation_end_year"
            )

        if self.monthly_birth_cohort_split != "uniform_1_12":
            raise ValueError(
                "Unsupported monthly birth cohort split"
            )

        return self

    