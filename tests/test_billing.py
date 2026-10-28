"""Code-only evals: given the details the agent SHOULD hear, is the superbill
correct? No voice, no network. Run from the project folder:

    .venv/bin/python -m pytest tests -v
"""
import json
import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from diagnoses import DIAGNOSES, search_diagnoses  # noqa: E402
from superbill import build_superbill, units_from_minutes  # noqa: E402

CASES = json.loads((Path(__file__).parent / "cases.json").read_text())
LABEL_BY_CODE = {code: label for label, (code, _) in DIAGNOSES.items()}


def by_id(case):
    return case["id"]


# --- Unit rounding: the rule itself -------------------------------------------

@pytest.mark.parametrize("minutes, units", [
    (0, 0), (7, 0), (8, 1), (15, 1), (22, 1), (23, 2), (30, 2), (37, 2), (38, 3), (45, 3),
])
def test_units_from_minutes(minutes, units):
    assert units_from_minutes(minutes) == units


# --- Diagnosis search: does the PT's phrase find the right code first? -------

@pytest.mark.parametrize("case", CASES, ids=by_id)
def test_diagnosis_search_top_match(case):
    matches, _ = search_diagnoses(case["heard"]["diagnosis_phrase"])
    assert matches, "search returned no matches"
    top_code = DIAGNOSES[matches[0]][0]
    assert top_code == case["expected"]["diagnosis"], f"top matches: {matches[:3]}"


# --- Superbill: given correct details, are lines, units and total right? -----

@pytest.mark.parametrize("case", CASES, ids=by_id)
def test_superbill(case):
    heard, expected = case["heard"], case["expected"]
    bill = build_superbill(
        patient_name="Test Patient",
        service_date=date(2026, 10, 17),
        diagnosis=LABEL_BY_CODE[expected["diagnosis"]],
        eval_level=heard["eval_level"],
        timed_minutes=heard["minutes"],
        estim_unattended=heard["estim_unattended"],
    )
    lines = sorted((l["cpt_code"], l["units"]) for l in bill["line_items"])
    want = sorted((l["code"], l["units"]) for l in expected["lines"])
    assert lines == want
    assert bill["totals"]["total_charges"] == pytest.approx(expected["total"])
    assert len(bill["warnings"]) == expected["warnings"], bill["warnings"]
    assert bill["status"] == "draft"
