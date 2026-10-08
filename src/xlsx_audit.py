"""Lecture des valeurs OOXML en cache, reservee a l'audit (sans modification).

Les formules ne sont pas recalculees. Les formats de dates ne sont pas interpretes.
Les tables du MASTER utilisees ici commencent a la premiere ligne.
"""
from __future__ import annotations

import posixpath
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def column_number(reference: str) -> int:
    number = 0
    for char in reference.upper():
        if char.isalpha():
            number = number * 26 + ord(char) - 64
    return number


class XlsxValues:
    """Lecteur en lecture seule; cellules identifiees par leur adresse Excel."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.z = ZipFile(self.path)
        relations = ET.fromstring(self.z.read("xl/_rels/workbook.xml.rels"))
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in relations}
        workbook = ET.fromstring(self.z.read("xl/workbook.xml"))
        self.sheets = {}
        for sheet in workbook.find(MAIN + "sheets"):
            target = targets[sheet.attrib[REL + "id"]]
            self.sheets[sheet.attrib["name"]] = (
                target.lstrip("/") if target.startswith("/")
                else posixpath.normpath("xl/" + target)
            )
        self.strings = []
        if "xl/sharedStrings.xml" in self.z.namelist():
            with self.z.open("xl/sharedStrings.xml") as stream:
                for _, element in ET.iterparse(stream, events=("end",)):
                    if element.tag == MAIN + "si":
                        self.strings.append("".join(
                            node.text or "" for node in element.iter(MAIN + "t")
                        ))
                        element.clear()

    def rows(self, sheet: str, start: int = 1, end: int | None = None):
        if start < 1 or (end is not None and end < start):
            raise ValueError("Intervalle de lignes Excel invalide.")
        if sheet not in self.sheets:
            raise KeyError(f"Feuille absente : {sheet}")
        with self.z.open(self.sheets[sheet]) as stream:
            for _, element in ET.iterparse(stream, events=("end",)):
                if element.tag != MAIN + "row":
                    continue
                row_number = int(element.attrib["r"])
                if end is not None and row_number > end:
                    break
                if row_number < start:
                    element.clear()
                    continue
                row = {}
                for cell in element.findall(MAIN + "c"):
                    value_element = cell.find(MAIN + "v")
                    kind = cell.attrib.get("t")
                    value = value_element.text if value_element is not None else None
                    if kind == "s" and value is not None:
                        value = self.strings[int(value)]
                    elif kind == "inlineStr":
                        value = "".join(node.text or "" for node in cell.iter(MAIN + "t"))
                    elif kind == "b" and value is not None:
                        value = value == "1"
                    elif kind not in ("str", "e") and value is not None:
                        try:
                            number = float(value)
                            value = int(number) if number.is_integer() else number
                        except ValueError:
                            pass
                    if value is not None:
                        row[cell.attrib["r"]] = value
                yield row_number, row
                element.clear()

    def cells(self, sheet: str, start: int = 1, end: int | None = None) -> dict:
        return {
            address: value
            for _, row in self.rows(sheet, start, end)
            for address, value in row.items()
        }

    def table(self, sheet: str) -> tuple[list, list[dict]]:
        rows = iter(self.rows(sheet))
        first = next(rows, None)
        if first is None:
            raise ValueError(f"Feuille vide : {sheet}")
        columns = {column_number(k): v for k, v in first[1].items()}
        if len(set(columns.values())) != len(columns):
            raise ValueError(f"En-tetes dupliques : {sheet}")
        records = []
        for _, row in rows:
            values = {column_number(k): v for k, v in row.items()}
            records.append({name: values.get(i) for i, name in columns.items()})
        return list(columns.values()), records

    def close(self) -> None:
        self.z.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
