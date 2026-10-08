"""Tests de l'audit; aucune modification des classeurs sources."""
from pathlib import Path
from zipfile import ZipFile
import math

import pandas as pd
import pytest

from src.source_audit import Audit, GROUPS, TABLES, equivalent, parse_range
from src.xlsx_audit import XlsxValues

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("left,right,expected", [
    (None, float("nan"), True), (0, None, False),
    (0.3, 0.1 + 0.2, True), (1, 2, False), ("F", "H", False),
])
def test_value_comparison(left, right, expected):
    assert equivalent(left, right) is expected


@pytest.mark.parametrize("text,expected", [
    ("0,1 / 0,5", (0.1, 0.5)), ("50 / 140", (50, 140)),
    ("-0,3 / -0,1", (-0.3, -0.1)), ("0,4", (0.4, 0.4)),
])
def test_ranges_are_not_interpolated(text, expected):
    assert parse_range(text) == expected


def test_invalid_range_is_rejected():
    with pytest.raises(ValueError):
        parse_range("absent")


def test_audit_records_discrepancies_and_cell_addresses():
    audit = Audit()
    audit.compare("test", "table", "value", [(2026, 2, 3, "B5")], "source.xlsx", "Feuille")
    assert audit.checks[0]["statut"] == "ECART"
    assert audit.cells[0]["cellule"] == "B5"
    assert audit.checks[0]["ecarts"] == 1


def test_empty_comparison_is_not_called_conformant():
    audit = Audit()
    audit.compare("test", "table", "value", [], "source.xlsx", "Feuille")
    assert audit.checks[0]["statut"] == "NON_VERIFIE"


def test_drees_groups_exclude_overlapping_attributes():
    assert "mico" not in GROUPS
    assert "Cpte Perso Penibilite" not in GROUPS
    assert len(GROUPS) == 9


@pytest.mark.parametrize("sheet,filename", list(TABLES.items()))
def test_master_parquet_values_match(sheet, filename):
    with XlsxValues(ROOT / "data/MASTER_DATA_RETRAITES_V1.xlsx") as master:
        columns, rows = master.table(sheet)
    parquet = pd.read_parquet(ROOT / "data/processed" / filename)
    assert list(parquet.columns) == columns
    assert len(parquet) == len(rows)
    for source, current in zip(rows, parquet.to_dict("records")):
        for column in columns:
            assert equivalent(source[column], current[column]), (sheet, column, source, current)


def test_joint_table_retains_open_age_class():
    joint = pd.read_csv(ROOT / "data/derived/cnav_age_group_2024.csv", sep=";")
    assert len(joint) == 144
    assert not joint.duplicated(["year", "sex", "age_label", "group_code"]).any()
    assert joint.loc[joint.sex.isin(["F", "H"]), "effectifs"].sum() == 648346
    assert joint.loc[joint.sex.isin(["F", "H"]) & joint.age_label.eq(">70"), "effectifs"].sum() == 15581


def test_joint_table_reproduces_group_margins():
    joint = pd.read_csv(ROOT / "data/derived/cnav_age_group_2024.csv", sep=";")
    with XlsxValues(ROOT / "data/MASTER_DATA_RETRAITES_V1.xlsx") as master:
        _, groups = master.table("CNAV_LIQ_GROUP")
    totals = joint.groupby(["sex", "group_code"])["effectifs"].sum()
    for row in groups:
        assert totals[row["sex"], row["group_code"]] == row["effectifs"]


def test_observed_cross_tabulation_is_not_a_future_forecast():
    joint = pd.read_csv(ROOT / "data/derived/cnav_age_group_2024.csv", sep=";")
    dc = joint.loc[joint.sex.isin(["F", "H"]) & joint.group_code.eq("droit_commun")]
    assert dc.loc[dc.age_label.eq("64"), "effectifs"].sum() == 46606
    assert dc.loc[dc.age_label.isin(["62", "63", "64"]), "effectifs"].sum() == 220814
    assert joint["method_status"].eq("observed_grouped_not_active").all()
