"""Write pack/cohort_dashboard_payload.json: the exact arguments published with cohort_dashboard.

Values are copied from dashboard/dashboard/data/*.json without recomputation or re-rounding.
"""
import json
import os

from pack_common import OUT, STATUS_TEXT, load_all


def lab(c, key):
    return [l for l, v in zip(c["labels"], c[key]) if v is not None]


def vals(c, key):
    return [v for v in c[key] if v is not None]


def build():
    d = load_all()
    kpis, meta, secs = d["kpis"], d["meta"], d["sections"]
    metrics = []
    for k in kpis:
        metrics.append({
            "label": f"KPI {k['kpi']} {k['name']}",
            "value": k["display"],
            "target": k["target"],
            "unit": STATUS_TEXT[k["status"]],
            "good": "up",
        })
    f = secs["sec02_demand_forecast"]["charts"][1]
    ch = secs["sec03_inventory_health"]["charts"][0]
    pv = secs["sec10_plan_vs_actual"]["charts"][0]
    charts = [
        {"title": "Demand history, 45 series with a forward forecast (net issues)", "type": "line",
         "labels": lab(f, "history"), "series": [{"name": "History", "data": vals(f, "history")}]},
        {"title": "Holdout Jul-Dec 2025, actual vs engine prediction (45 series)", "type": "line",
         "labels": lab(f, "holdout_actual"),
         "series": [{"name": "Holdout actual", "data": vals(f, "holdout_actual")},
                    {"name": "Holdout predicted", "data": vals(f, "holdout_predicted")}]},
        {"title": "Forward Jan-Jun 2026, engine monthly means (45 series)", "type": "bar",
         "labels": lab(f, "forward"), "series": [{"name": "Forward", "data": vals(f, "forward")}]},
        {"title": ch["title"], "type": "line", "labels": ch["labels"], "series": ch["series"]},
        {"title": pv["title"], "type": "bar", "labels": pv["labels"], "series": pv["series"]},
    ]
    insights = [
        {"title": "No KPI is met", "severity": "critical",
         "detail": f"{meta['kpi_counts']['met']} met, {meta['kpi_counts']['not_met']} not met, "
                   f"{meta['kpi_counts']['not_computable']} not computable on demo scope."},
        {"title": "Engine warning (verbatim)", "severity": "warn", "detail": meta["engine"]["warning"]},
    ] + [{"title": f"KPI {k['kpi']} not computable on demo scope", "severity": "info", "detail": k["detail"]}
         for k in kpis if k["status"] == "not_computable"]
    return {"title": meta["banner"], "metrics": metrics, "charts": charts, "insights": insights}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "cohort_dashboard_payload.json")
    json.dump(build(), open(p, "w"), indent=1)
    print("wrote", p)
