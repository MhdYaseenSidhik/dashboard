"""Shared loading for the Office pack: one reader of dashboard/dashboard/data/*.json.

The xlsx, the pptx and the cohort_dashboard payload are all derived from this
module so no figure is recomputed or re-rounded on the way out.
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "dashboard", "data")
OUT = os.path.join(ROOT, "pack")

SECTION_IDS = [
    "sec01_kpi_scorecard", "sec02_demand_forecast", "sec03_inventory_health",
    "sec04_over_understock", "sec05_nm_sm_prediction", "sec06_shutdown_maintenance",
    "sec07_pr_recommendations", "sec08_mrp_rop", "sec09_duplicate_skus", "sec10_plan_vs_actual",
]
STATUS_TEXT = {
    "met": "Met", "not_met": "Not met", "not_computable": "Not computable on demo scope",
    "diverges": "Diverges", "match": "Match",
}


def load(name):
    with open(os.path.join(DATA, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def load_all():
    return {
        "meta": load("meta"),
        "kpis": load("kpis"),
        "notes": load("notes"),
        "reconciliation": load("reconciliation"),
        "sections": {sid: load(sid) for sid in SECTION_IDS},
    }


def sheet_name(section):
    """Excel sheet names: max 31 chars, none of []:*?/\\ ."""
    n = section["id"].split("_", 1)[0].replace("sec", "S") + " " + section["nav"]
    for ch in "[]:*?/\\":
        n = n.replace(ch, "-")
    return n[:31]
