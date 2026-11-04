"""Acceptance checks for the HZL_DEMO pack.

Reads only files in this repository. Nothing here changes product code or writes to SAP.
The RAW comparison uses data/raw/raw_check_live_2026-11-04.json, the result of
queries/raw_verification_top50.sql run live against VEDANTA_POC (SELECT only).
"""
import csv
import glob
import hashlib
import json
import math
import os
import re
import sys

import pytest
from openpyxl import load_workbook
from pptx import Presentation

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import cohort_payload  # noqa: E402
from pack_common import SECTION_IDS, STATUS_TEXT, load_all, sheet_name  # noqa: E402

BANNER = "Demo scope: PART_001, plant HZL_DEMO_05, top 50 materials."
XLSX = os.path.join(ROOT, "pack", "HZL_DEMO_inventory_pack.xlsx")
PPTX = os.path.join(ROOT, "pack", "HZL_DEMO_inventory_pack.pptx")
PAYLOAD = os.path.join(ROOT, "pack", "cohort_dashboard_payload.json")


def p(*parts):
    return os.path.join(ROOT, *parts)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def leaf_numbers(o, skip_keys=("extra",)):
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in skip_keys:
                yield from leaf_numbers(v, skip_keys)
    elif isinstance(o, list):
        for v in o:
            yield from leaf_numbers(v, skip_keys)
    elif is_num(o):
        yield float(o)


@pytest.fixture(scope="module")
def D():
    return load_all()


@pytest.fixture(scope="module")
def series():
    with open(p("data", "demo_net_issue_series.csv")) as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def holdout():
    with open(p("data", "raw", "forecast_evaluation_download.csv")) as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def pack():
    with open(p("data", "pack.json")) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def wb():
    return load_workbook(XLSX, data_only=True)


@pytest.fixture(scope="module")
def prs():
    return Presentation(PPTX)


def sheet_numbers(ws):
    return {repr(float(c.value)) for row in ws.iter_rows() for c in row if is_num(c.value)}


def sheet_text(ws):
    return "\n".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)


# ---- series vs RAW -------------------------------------------------------------

def test_series_has_1200_rows_50_materials_24_months(series):
    assert len(series) == 1200
    assert len({r["MATERIAL_PLANT"] for r in series}) == 50
    months = sorted({r["MONTH"] for r in series})
    assert len(months) == 24 and months[0] == "2024-01-01" and months[-1] == "2025-12-01"
    assert all(re.fullmatch(r"\d{4}-\d{2}-01", m) for m in months)


def test_series_is_zero_filled_not_ragged(series):
    per = {}
    for r in series:
        per.setdefault(r["MATERIAL_PLANT"], []).append(r["MONTH"])
    assert all(len(v) == 24 for v in per.values())


def test_series_sum_matches_live_raw_check(series):
    with open(p("data", "raw", "raw_check_live_2026-11-04.json")) as f:
        raw = json.load(f)["result"]
    assert sum(float(r["NET_QTY"]) for r in series) == pytest.approx(float(raw["SUM_NET_QTY"]), abs=1e-3)
    assert sum(1 for r in series if float(r["NET_QTY"]) != 0) == raw["NONZERO_ROWS"]
    assert len({r["MATERIAL_PLANT"] for r in series}) == raw["N_TOP50_MATERIALS"]


def test_pack_json_raw_check_agrees_with_series(pack, series):
    rc = pack["raw_check"]
    assert rc["rows"] == len(series) == 1200
    assert rc["sum_net_qty"] == pytest.approx(rc["raw_sum_net_qty"], abs=1e-3)
    assert rc["nonzero_rows"] == rc["raw_nonzero_rows"]


def test_site_history_chart_equals_series_monthly_totals(D, series):
    tot = {}
    for r in series:
        tot[r["MONTH"][:7]] = tot.get(r["MONTH"][:7], 0.0) + float(r["NET_QTY"])
    ch = D["sections"]["sec02_demand_forecast"]["charts"][0]
    got = {l: v for l, v in zip(ch["labels"], ch["history"]) if v is not None}
    assert got == pytest.approx(tot)


# ---- WAPE / F1 recomputed from forecast-evaluation ----------------------------

def test_holdout_file_sha256_matches_record(pack):
    with open(p("data", "raw", "forecast_evaluation_download.csv"), "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == pack["metrics"]["holdout_sha256"]


def wape(rows):
    return sum(abs(float(r["actual"]) - float(r["predicted"])) for r in rows) / sum(abs(float(r["actual"])) for r in rows)


def test_wape_6m_recomputed_equals_published_kpi5_kpi6(D, holdout):
    w = wape(holdout)
    assert len(holdout) == 300 and len({r["item_id"] for r in holdout}) == 50
    k = {x["kpi"]: x for x in D["kpis"]}
    acc = f"{(1 - w) * 100:.2f}%"
    assert acc in k[5]["display"] and acc in k[6]["display"]
    assert k[5]["value"] == pytest.approx(round(1 - w, 4), abs=1e-9)
    assert f"WAPE {w:.4f}" in k[5]["detail"]
    tile = D["sections"]["sec02_demand_forecast"]["tiles"][0]
    assert tile["value"] == acc and tile["extra"]["wape"] == pytest.approx(round(w, 4))


def test_wape_3m_recomputed_equals_published_kpi6(D, holdout):
    w3 = wape([r for r in holdout if r["timestamp"] >= "2025-10-01"])
    assert f"{(1 - w3) * 100:.2f}% (last 3 months)" in {x["kpi"]: x for x in D["kpis"]}[6]["display"]


def test_interval_share_recomputed_equals_published(D, holdout):
    share = sum(r["within_interval"] == "True" for r in holdout) / len(holdout)
    tiles = {t["label"]: t["value"] for t in D["sections"]["sec02_demand_forecast"]["tiles"]}
    assert tiles["Actuals inside engine interval"] == f"{share * 100:.2f}%"


def test_kpi7_f1_is_not_published_because_it_is_not_computable(D):
    k7 = {x["kpi"]: x for x in D["kpis"]}[7]
    assert k7["status"] == "not_computable" and k7["value"] is None
    assert k7["display"] == "Not computable on demo scope" and k7["detail"]
    assert not any("F1" in str(v) and re.search(r"F1\s*[=:]?\s*0?\.\d", str(v)) for v in k7.values())


def test_model_is_engine_top_rank_verbatim(D, pack):
    e = D["meta"]["engine"]
    assert e["best_model"] == "WeightedEnsemble" and e["wql"] == 0.757317
    assert e["leaderboard"][0] == {"rank": 1, "model": "WeightedEnsemble", "WQL": 0.757317}
    assert e["leaderboard"] == pack["model"]["leaderboard"]
    assert e["warning"] == pack["model"]["engine_warning"]


def test_forward_forecast_traces_to_engine_output_file(D):
    with open(p("data", "raw", "forward_mean_6m_45of50.csv")) as f:
        fwd = list(csv.DictReader(f))
    assert len(fwd) == 45
    cols = [c for c in fwd[0] if c != "MATERIAL_PLANT"]
    tot = [round(sum(float(r[c]) for r in fwd), 1) for c in cols]
    ch = D["sections"]["sec02_demand_forecast"]["charts"][0]
    assert [v for v in ch["forward"] if v is not None] == pytest.approx(tot, abs=0.051)


# ---- sections and KPIs ---------------------------------------------------------

def test_ten_sections_present_and_ordered(D):
    assert list(D["sections"]) == SECTION_IDS and len(SECTION_IDS) == 10
    assert [s["id"] for s in D["meta"]["sections"]] == SECTION_IDS
    for sid, s in D["sections"].items():
        assert s["id"] == sid and s["title"] and (s["tiles"] or s["tables"] or s["charts"])


def test_thirteen_kpis_each_with_target_period_baseline_definition_status(D):
    ks = D["kpis"]
    assert [k["kpi"] for k in ks] == list(range(1, 14))
    for k in ks:
        for f in ("name", "target", "period", "baseline", "definition", "display", "detail", "drill"):
            assert k[f], (k["kpi"], f)
        assert k["status"] in ("met", "not_met", "not_computable")
        assert k["drill"] in SECTION_IDS
        if k["status"] == "not_computable":
            # KPI 10 shows its unscored candidate count in display; the status carries the verdict.
            assert k["value"] is None and k["detail"].strip()
            assert k["display"] == "Not computable on demo scope" or "not scored" in k["display"]
        else:
            assert k["value"] is not None


def test_kpi_counts_match_statuses(D):
    from collections import Counter
    c = Counter(k["status"] for k in D["kpis"])
    kc = D["meta"]["kpi_counts"]
    assert (kc["met"], kc["not_met"], kc["not_computable"]) == (c["met"], c["not_met"], c["not_computable"])
    assert sum(kc.values()) == 13


def test_scorecard_section_equals_kpis(D):
    rows = D["sections"]["sec01_kpi_scorecard"]["tables"][0]["rows"]
    assert len(rows) == 13
    for r, k in zip(rows, D["kpis"]):
        assert (r["kpi"], r["display"], r["target"], r["period"], r["status"], r["drill"]) == \
               (k["kpi"], k["display"], k["target"], k["period"], k["status"], k["drill"])


def test_banner_exact_on_meta(D):
    assert D["meta"]["banner"] == BANNER


# ---- queries -------------------------------------------------------------------

def strip_comments(sql):
    return "\n".join(l.split("--", 1)[0] for l in sql.splitlines())


QUERY_FILES = sorted(glob.glob(p("queries", "*.sql")))
DML = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|MERGE|GRANT|REVOKE|CALL|EXEC|UPSERT|REPLACE)\b", re.I)


def test_queries_folder_has_the_series_and_verification_queries():
    names = {os.path.basename(f) for f in QUERY_FILES}
    assert {"demo_net_issue_series.sql", "raw_verification_top50.sql"} <= names


@pytest.mark.parametrize("path", QUERY_FILES, ids=os.path.basename)
def test_query_is_select_only(path):
    body = strip_comments(open(path).read())
    stmts = [s.strip() for s in body.split(";") if s.strip()]
    assert stmts
    for s in stmts:
        assert re.match(r"(SELECT|WITH)\b", s, re.I), s[:80]
        assert not DML.search(s), DML.search(s).group(0)


@pytest.mark.parametrize("path", QUERY_FILES, ids=os.path.basename)
def test_query_carries_zspr_zspn_scope(path):
    body = strip_comments(open(path).read())
    assert "'ZSPR'" in body and "'ZSPN'" in body


@pytest.mark.parametrize("path", QUERY_FILES, ids=os.path.basename)
def test_every_fact_statement_filters_backcast_n(path):
    body = strip_comments(open(path).read())
    bad = []
    for s in [x.strip() for x in body.split(";") if x.strip()]:
        if re.search(r"\bFACT_\w+", s, re.I):
            n_filters = len(re.findall(r"IS_BACKCAST_PERIOD\s*=\s*'N'", s, re.I))
            if n_filters < 1:
                bad.append(f"FACT table read with no IS_BACKCAST_PERIOD='N' filter: {s[:70]!r}")
    assert not bad, bad


# ---- xlsx ----------------------------------------------------------------------

def test_xlsx_has_sheet_per_section_plus_scorecard_reconciliation_notes(wb, D):
    exp = ["KPI Scorecard"] + [sheet_name(s) for s in D["sections"].values()] + ["Reconciliation", "Notes"]
    assert wb.sheetnames == exp and len(exp) == 13


def test_xlsx_banner_on_every_sheet_first_cell(wb):
    for ws in wb.worksheets:
        assert ws["A1"].value == BANNER, ws.title


def test_xlsx_scorecard_has_13_kpis_matching_json(wb, D):
    ws = wb["KPI Scorecard"]
    rows = [r for r in ws.iter_rows(min_row=1, values_only=True) if isinstance(r[0], int)]
    assert [r[0] for r in rows] == list(range(1, 14))
    for r, k in zip(rows, D["kpis"]):
        assert (r[1], r[2], r[4], r[5], r[6], r[7]) == \
               (k["name"], k["display"], STATUS_TEXT[k["status"]], k["target"], k["period"], k["baseline"])
        assert r[3] == (k["value"] if k["value"] is not None else "n/a")


@pytest.mark.parametrize("sid", SECTION_IDS)
def test_xlsx_section_sheet_holds_every_json_number_and_tile_text(wb, D, sid):
    sec = D["sections"][sid]
    ws = wb[sheet_name(sec)]
    nums, text = sheet_numbers(ws), sheet_text(ws)
    missing = {repr(v) for v in leaf_numbers({k: sec[k] for k in ("tables", "charts")})} - nums
    assert not missing, sorted(missing)[:10]
    for t in sec["tiles"]:
        assert t["value"] in text and t["definition"] in text and t["source"] in text, t["label"]
        for k, v in (t.get("extra") or {}).items():
            assert f"{k}={v}" in text
    for n in sec["notes"]:
        assert n in text


def test_xlsx_kpi_numbers_match_json(wb, D):
    nums = sheet_numbers(wb["KPI Scorecard"])
    missing = {repr(v) for v in leaf_numbers(D["kpis"])} - nums
    assert not missing, sorted(missing)


def test_xlsx_reconciliation_rows_match_json(wb, D):
    text = sheet_text(wb["Reconciliation"])
    rows = D["reconciliation"]["tables"][0]["rows"]
    assert len(rows) == 11
    for r in rows:
        for k in ("item", "raw", "curated", "result"):
            assert r[k] in text
        assert STATUS_TEXT[r["state"]] in text


def test_xlsx_notes_sheet_has_engine_model_and_every_note(wb, D):
    ws, e = wb["Notes"], D["meta"]["engine"]
    text, nums = sheet_text(ws), sheet_numbers(ws)
    assert e["best_model"] in text and e["warning"] in text and e["experiment_id"] in text
    assert repr(e["wql"]) in nums
    assert {repr(float(m["WQL"])) for m in e["leaderboard"]} <= nums
    for n in D["notes"]["notes"]:
        assert n in text


# ---- pptx ----------------------------------------------------------------------

def slide_text(slide):
    out = []
    for sh in slide.shapes:
        if sh.has_text_frame:
            out.append(sh.text_frame.text)
        if sh.has_table:
            out += [c.text for r in sh.table.rows for c in r.cells]
    return "\n".join(out)


def test_pptx_banner_on_every_slide(prs):
    assert len(prs.slides) == 6
    for i, s in enumerate(prs.slides, 1):
        assert BANNER in slide_text(s), i


def test_pptx_headline_kpis_table_has_all_13_matching_json(prs, D):
    tbl = [sh.table for sh in prs.slides[1].shapes if sh.has_table][0]
    assert len(tbl.rows) == 14
    for r, k in zip(list(tbl.rows)[1:], D["kpis"]):
        c = [x.text for x in r.cells]
        assert c == [str(k["kpi"]), k["name"], k["display"], k["target"] + " | " + STATUS_TEXT[k["status"]]]


def test_pptx_forecast_chart_series_equal_json(prs, D):
    ch = [sh.chart for sh in prs.slides[2].shapes if sh.has_chart][0]
    src = D["sections"]["sec02_demand_forecast"]["charts"][1]
    assert list(ch.plots[0].categories) == src["labels"]
    got = {s.name: list(s.values) for s in ch.plots[0].series}
    assert got == {"History": src["history"], "Holdout actual": src["holdout_actual"],
                   "Holdout predicted (engine)": src["holdout_predicted"], "Forward (engine)": src["forward"]}


def test_pptx_forecast_slide_quotes_tiles_and_model(prs, D):
    t = slide_text(prs.slides[2])
    for tile in D["sections"]["sec02_demand_forecast"]["tiles"]:
        assert f"{tile['label']}: {tile['value']}" in t
    e = D["meta"]["engine"]
    assert f"{e['best_model']}, {e['primary_metric']} {e['wql']}" in t


def test_pptx_alerts_quote_json_text(prs, D):
    t = slide_text(prs.slides[3])
    k = {x["kpi"]: x for x in D["kpis"]}
    for n in (8, 1, 5):
        assert k[n]["display"] in t and k[n]["detail"] in t
    s7 = D["sections"]["sec07_pr_recommendations"]["tiles"]
    assert s7[0]["value"] in t and s7[2]["value"] in t


def test_pptx_actions_table_is_the_json_high_priority_lines(prs, D):
    tbl = [sh.table for sh in prs.slides[4].shapes if sh.has_table][0]
    hi = [r for r in D["sections"]["sec07_pr_recommendations"]["tables"][0]["rows"] if r["high_priority"]]
    assert len(hi) == 13 and len(tbl.rows) == 14
    for r, x in zip(list(tbl.rows)[1:], hi):
        c = [y.text for y in r.cells]
        assert c == [x["material"], x["criticality"], x["shutdown_flag"], x["raise_date"],
                     f"{x['order_qty']:,.0f}", f"{x['order_value_inr']:,.2f}", f"{x['lead_time_days']:,.1f}"]


def test_pptx_every_number_in_deck_exists_in_json(prs, D):
    blob = json.dumps([D["kpis"], D["meta"], D["notes"], D["reconciliation"], D["sections"]], ensure_ascii=False)
    fmt = {f"{float(v):,.2f}" for v in leaf_numbers(D)} | {f"{float(v):,.1f}" for v in leaf_numbers(D)} | \
          {f"{float(v):,.0f}" for v in leaf_numbers(D)}
    unseen = []
    for s in list(prs.slides)[1:]:
        for sh in s.shapes:
            cells = [c.text for r in sh.table.rows for c in r.cells] if sh.has_table else []
            for txt in cells:
                for tok in re.findall(r"\d[\d,]*\.?\d*", txt):
                    tok = tok.rstrip(".,")
                    if tok in blob or tok in fmt:
                        continue
                    unseen.append(tok)
    assert not unseen, unseen[:10]


# ---- cohort_dashboard ----------------------------------------------------------

def test_cohort_payload_file_is_what_the_builder_emits(D):
    with open(PAYLOAD) as f:
        assert json.load(f) == json.loads(json.dumps(cohort_payload.build()))


def test_cohort_metrics_are_the_13_kpis_verbatim(D):
    with open(PAYLOAD) as f:
        pl = json.load(f)
    assert len(pl["metrics"]) == 13 and pl["title"] == BANNER
    for m, k in zip(pl["metrics"], D["kpis"]):
        assert (m["value"], m["target"], m["unit"]) == (k["display"], k["target"], STATUS_TEXT[k["status"]])


def test_cohort_charts_equal_json_series(D):
    with open(PAYLOAD) as f:
        pl = json.load(f)
    by = {c["title"]: c for c in pl["charts"]}
    f45 = D["sections"]["sec02_demand_forecast"]["charts"][1]
    assert by["Demand history, 45 series with a forward forecast (net issues)"]["series"][0]["data"] == \
        [v for v in f45["history"] if v is not None]
    assert by["Forward Jan-Jun 2026, engine monthly means (45 series)"]["series"][0]["data"] == \
        [v for v in f45["forward"] if v is not None]
    sv = D["sections"]["sec03_inventory_health"]["charts"][0]
    assert by[sv["title"]]["series"] == sv["series"]
    pv = D["sections"]["sec10_plan_vs_actual"]["charts"][0]
    assert by[pv["title"]]["series"] == pv["series"]


def test_cohort_insights_quote_engine_warning_and_every_uncomputable_kpi(D):
    with open(PAYLOAD) as f:
        pl = json.load(f)
    det = {i["title"]: i["detail"] for i in pl["insights"]}
    assert det["Engine warning (verbatim)"] == D["meta"]["engine"]["warning"]
    for k in D["kpis"]:
        if k["status"] == "not_computable":
            assert det[f"KPI {k['kpi']} not computable on demo scope"] == k["detail"]


def test_site_data_no_kpi_value_without_target_and_period(D):
    for k in D["kpis"]:
        assert k["target"].strip() and k["period"].strip()
    for sid, s in D["sections"].items():
        for t in s["tiles"]:
            for f in ("definition", "baseline", "period", "refreshed", "source"):
                assert t[f], (sid, t["label"], f)
