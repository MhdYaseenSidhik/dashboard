"""Build pack/HZL_DEMO_inventory_pack.xlsx from dashboard/dashboard/data/*.json.

Cells carry the JSON values untouched; number formats only change how Excel
displays them, never the stored value.
"""
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from pack_common import OUT, STATUS_TEXT, load_all, sheet_name

FILE = os.path.join(OUT, "HZL_DEMO_inventory_pack.xlsx")
NUMFMT = {"int": "#,##0", "num0": "#,##0", "num1": "#,##0.0", "num2": "#,##0.00", "inr": "#,##0.00"}
BOLD = Font(bold=True)
HEAD = PatternFill("solid", fgColor="DDE6F0")
BANNER = PatternFill("solid", fgColor="FFF2CC")


def put_banner(ws, banner):
    ws["A1"] = banner
    ws["A1"].font = Font(bold=True)
    ws["A1"].fill = BANNER
    return 3


def put_row(ws, r, values, bold=False, fill=None):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=r, column=i, value=v)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if bold:
            c.font = BOLD
        if fill:
            c.fill = fill
    return r + 1


def cell_value(col, v):
    fmt = col.get("fmt")
    if v is None or v == "":
        return "n/a"
    if fmt in ("status", "state"):
        return STATUS_TEXT.get(v, v)
    if fmt == "bool":
        return "Yes" if v else "No"
    if fmt == "link":
        return v
    return v


def extra_fields(t):
    """Row keys the site does not display. Kept in the workbook so every JSON number is present;
    list values are spread across one column per element."""
    shown = {c["key"] for c in t["columns"]}
    order, width = [], {}
    for row in t["rows"]:
        for k, v in row.items():
            if k in shown:
                continue
            if k not in width:
                order.append(k)
            width[k] = max(width.get(k, 1), len(v) if isinstance(v, list) else 1)
    return [(k, width[k]) for k in order]


def put_table(ws, r, t):
    ws.cell(row=r, column=1, value=t["title"]).font = BOLD
    r += 1
    extras = extra_fields(t)
    heads = [c["label"] for c in t["columns"]]
    for k, n in extras:
        heads += [f"[data] {k}"] if n == 1 and not any(isinstance(x.get(k), list) for x in t["rows"]) \
            else [f"[data] {k}[{i}]" for i in range(n)]
    r = put_row(ws, r, heads, bold=True, fill=HEAD)
    for row in t["rows"]:
        for i, col in enumerate(t["columns"], 1):
            c = ws.cell(row=r, column=i, value=cell_value(col, row.get(col["key"])))
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if col.get("fmt") in NUMFMT and isinstance(c.value, (int, float)):
                c.number_format = NUMFMT[col["fmt"]]
        j = len(t["columns"]) + 1
        for k, n in extras:
            v = row.get(k)
            vs = v if isinstance(v, list) else [v] + [None] * (n - 1)
            for x in vs:
                ws.cell(row=r, column=j, value=x)
                j += 1
        r += 1
    return r + 1


def put_tiles(ws, r, tiles):
    ws.cell(row=r, column=1, value="Tiles").font = BOLD
    r += 1
    r = put_row(ws, r, ["Metric", "Value", "Status", "Target", "Period", "Baseline",
                        "Refreshed", "Definition", "Source", "Extra"], bold=True, fill=HEAD)
    for t in tiles:
        target = (t.get("extra") or {}).get("target", "")
        r = put_row(ws, r, [t["label"], t["value"], STATUS_TEXT.get(t.get("status"), ""), target,
                            t["period"], t["baseline"], t["refreshed"], t["definition"], t["source"],
                            "; ".join(f"{k}={v}" for k, v in (t.get("extra") or {}).items())])
    return r + 1


def put_chart(ws, r, c):
    ws.cell(row=r, column=1, value=c["title"]).font = BOLD
    r += 1
    if c["type"] == "forecast":
        keys = ["history", "holdout_actual", "holdout_predicted", "holdout_lower", "holdout_upper", "forward"]
        r = put_row(ws, r, ["Month"] + keys, bold=True, fill=HEAD)
        for i, lab in enumerate(c["labels"]):
            r = put_row(ws, r, [lab] + [c[k][i] for k in keys])
    else:
        r = put_row(ws, r, ["Label"] + [s["name"] for s in c["series"]], bold=True, fill=HEAD)
        for i, lab in enumerate(c["labels"]):
            r = put_row(ws, r, [lab] + [s["data"][i] for s in c["series"]])
    if c.get("note"):
        r = put_row(ws, r, [c["note"]])
    return r + 1


def put_section(wb, banner, sec):
    ws = wb.create_sheet(sheet_name(sec))
    r = put_banner(ws, banner)
    ws.cell(row=r, column=1, value=sec["title"]).font = Font(bold=True, size=14)
    r = put_row(ws, r + 1, [sec["intro"]])
    r += 1
    if sec["tiles"]:
        r = put_tiles(ws, r, sec["tiles"])
    for c in sec["charts"]:
        r = put_chart(ws, r, c)
    for t in sec["tables"]:
        r = put_table(ws, r, t)
    if sec["notes"]:
        ws.cell(row=r, column=1, value="Notes").font = BOLD
        r += 1
        for n in sec["notes"]:
            r = put_row(ws, r, [n])
    return ws


def put_kpi_scorecard(wb, banner, kpis, meta):
    ws = wb.create_sheet("KPI Scorecard")
    r = put_banner(ws, banner)
    k = meta["kpi_counts"]
    ws.cell(row=r, column=1, value="KPI Scorecard (13 KPIs)").font = Font(bold=True, size=14)
    r = put_row(ws, r + 1, [f"Met {k['met']}, not met {k['not_met']}, not computable on demo scope {k['not_computable']}."])
    r += 1
    r = put_row(ws, r, ["#", "KPI", "Value", "Numeric value", "Status", "Target", "Period", "Baseline",
                        "Definition", "Detail", "Drill-down page", "Curated comparison", "Curated value"],
                bold=True, fill=HEAD)
    for x in kpis:
        cur = x.get("curated") or {}
        r = put_row(ws, r, [x["kpi"], x["name"], x["display"], x["value"] if x["value"] is not None else "n/a",
                            STATUS_TEXT[x["status"]], x["target"], x["period"], x["baseline"], x["definition"],
                            x["detail"], x["drill"] + ".html",
                            (cur.get("label", "") + ": " + cur.get("display", "")) if cur else "n/a",
                            cur.get("value") if cur and cur.get("value") is not None else "n/a"])
    return ws


def put_reconciliation(wb, banner, rec):
    ws = wb.create_sheet("Reconciliation")
    r = put_banner(ws, banner)
    ws.cell(row=r, column=1, value=rec["title"]).font = Font(bold=True, size=14)
    r = put_row(ws, r + 1, [rec["intro"]])
    r += 1
    for t in rec["tables"]:
        r = put_table(ws, r, t)
    for n in rec["notes"]:
        r = put_row(ws, r, [n])
    return ws


def put_notes(wb, banner, notes, meta):
    ws = wb.create_sheet("Notes")
    r = put_banner(ws, banner)
    ws.cell(row=r, column=1, value=notes["title"]).font = Font(bold=True, size=14)
    r = put_row(ws, r + 1, [notes["intro"]])
    r += 1
    e = meta["engine"]
    r = put_row(ws, r, ["Engine", e["name"]])
    r = put_row(ws, r, ["Experiment", e["experiment_id"]])
    r = put_row(ws, r, ["Asset", e["asset_id"]])
    r = put_row(ws, r, ["Best model (engine, verbatim)", e["best_model"]])
    r = put_row(ws, r, [e["primary_metric"], e["wql"]])
    r = put_row(ws, r, ["Engine warning", e["warning"]])
    r = put_row(ws, r, ["Refreshed", meta["refreshed"]])
    r += 1
    r = put_row(ws, r, ["Rank", "Model", e["primary_metric"]], bold=True, fill=HEAD)
    for m in e["leaderboard"]:
        r = put_row(ws, r, [m["rank"], m["model"], m["WQL"]])
    r += 1
    ws.cell(row=r, column=1, value="Notes").font = BOLD
    r += 1
    for n in notes["notes"]:
        r = put_row(ws, r, [n])
    return ws


def widths(ws):
    for i in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(i)].width = 22
    ws.column_dimensions["A"].width = 34


def main():
    d = load_all()
    banner = d["meta"]["banner"]
    wb = Workbook()
    wb.remove(wb.active)
    put_kpi_scorecard(wb, banner, d["kpis"], d["meta"])
    for sid, sec in d["sections"].items():
        put_section(wb, banner, sec)
    put_reconciliation(wb, banner, d["reconciliation"])
    put_notes(wb, banner, d["notes"], d["meta"])
    for ws in wb.worksheets:
        widths(ws)
    os.makedirs(OUT, exist_ok=True)
    wb.save(FILE)
    print("wrote", FILE, [w.title for w in wb.worksheets])


if __name__ == "__main__":
    main()
