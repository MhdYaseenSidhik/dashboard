"""Build pack/HZL_DEMO_inventory_pack.pptx from dashboard/dashboard/data/*.json.

Slides: title, headline KPIs (all 13), demand forecast chart, top alerts,
recommended actions, engine and notes. The scope banner is on every slide.
Numbers are the JSON strings/values as published; nothing is recomputed.
"""
import os

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Inches, Pt

from pack_common import OUT, STATUS_TEXT, load_all

FILE = os.path.join(OUT, "HZL_DEMO_inventory_pack.pptx")
INK = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x6B, 0x72, 0x80)
STATUS_COL = {"met": RGBColor(0x16, 0x7A, 0x3E), "not_met": RGBColor(0xB4, 0x23, 0x18),
              "not_computable": RGBColor(0x6B, 0x72, 0x80)}


def text(slide, x, y, w, h, s, size=14, bold=False, color=INK):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = s
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    return tf


def add_para(tf, s, size=12, bold=False, color=INK):
    p = tf.add_paragraph()
    p.text = s
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    return p


def new_slide(prs, banner, title):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 0.4, 0.15, 12.5, 0.4, banner, size=11, bold=True, color=MUTED)
    text(s, 0.4, 0.55, 12.5, 0.7, title, size=26, bold=True)
    return s


def kpi_table(slide, kpis, x, y, w):
    rows = len(kpis) + 1
    tbl = slide.shapes.add_table(rows, 4, Inches(x), Inches(y), Inches(w), Inches(0.3 * rows)).table
    for i, wd in enumerate([0.4, 2.6, 4.6, 4.8]):
        tbl.columns[i].width = Inches(wd)
    for i, h in enumerate(["#", "KPI", "Value", "Target / status"]):
        tbl.cell(0, i).text = h
    for r, k in enumerate(kpis, 1):
        vals = [str(k["kpi"]), k["name"], k["display"], k["target"] + " | " + STATUS_TEXT[k["status"]]]
        for c, v in enumerate(vals):
            tbl.cell(r, c).text = v
    for r in range(rows):
        for c in range(4):
            for p in tbl.cell(r, c).text_frame.paragraphs:
                p.font.size = Pt(9)
                if r > 0 and c == 3:
                    p.font.color.rgb = STATUS_COL[kpis[r - 1]["status"]]


def main():
    d = load_all()
    meta, kpis, secs = d["meta"], d["kpis"], d["sections"]
    banner = meta["banner"]
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 0.6, 0.4, 12, 0.5, banner, size=14, bold=True, color=MUTED)
    text(s, 0.6, 2.2, 12, 1.2, "HZL_DEMO inventory pack", size=40, bold=True)
    tf = text(s, 0.6, 3.5, 12, 0.5, f"As-of {meta['as_of']} | plant {meta['plant']} | {meta['currency']} | ZSPR/ZSPN", size=18)
    add_para(tf, meta["refreshed"], size=12, color=MUTED)
    k = meta["kpi_counts"]
    add_para(tf, f"13 KPIs: {k['met']} met, {k['not_met']} not met, {k['not_computable']} not computable on demo scope.", size=14, bold=True)

    s = new_slide(prs, banner, "Headline KPIs: all 13 against target")
    kpi_table(s, kpis, 0.4, 1.3, 12.4)

    f = secs["sec02_demand_forecast"]
    s = new_slide(prs, banner, "Demand forecast: history, holdout, forward")
    ch = f["charts"][1]  # same-basis view: history, holdout and forward all on the 45 series that have a forecast
    cd = CategoryChartData()
    cd.categories = ch["labels"]
    for key, name in [("history", "History"), ("holdout_actual", "Holdout actual"),
                      ("holdout_predicted", "Holdout predicted (engine)"), ("forward", "Forward (engine)")]:
        cd.add_series(name, ch[key])
    gf = s.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(0.4), Inches(1.3), Inches(8.4), Inches(5.6), cd)
    gf.chart.has_legend = True
    gf.chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    gf.chart.legend.include_in_layout = False
    gf.chart.legend.font.size = Pt(10)
    tf = text(s, 9.0, 1.3, 4.0, 5.6, "Accuracy and model", size=14, bold=True)
    for t in f["tiles"]:
        add_para(tf, f"{t['label']}: {t['value']}", size=12, bold=True)
        add_para(tf, f"{t['period']}; {t['baseline']}", size=10, color=MUTED)
    e = meta["engine"]
    add_para(tf, f"Model (engine): {e['best_model']}, {e['primary_metric']} {e['wql']}", size=11, bold=True)
    add_para(tf, ch["title"], size=9, color=MUTED)
    add_para(tf, ch["note"], size=9, color=MUTED)

    s = new_slide(prs, banner, "Top alerts")
    tf = text(s, 0.4, 1.3, 12.5, 5.6, "", size=13)
    s4, s7 = secs["sec04_over_understock"], secs["sec07_pr_recommendations"]
    alerts = [
        ("KPI 8 critical spares availability: " + kpis[7]["display"], kpis[7]["detail"]),
        ("KPI 1 gross inventory reduction: " + kpis[0]["display"], kpis[0]["detail"]),
        ("KPI 5 and 6 demand accuracy: " + kpis[4]["display"], kpis[4]["detail"]),
        (s7["tiles"][0]["label"] + ": " + s7["tiles"][0]["value"],
         s7["tiles"][1]["label"] + " " + s7["tiles"][1]["value"] + "; " + s7["tiles"][2]["label"] + " " + s7["tiles"][2]["value"]),
        (s4["tiles"][0]["label"] + ": " + s4["tiles"][0]["value"], s4["tiles"][1]["label"] + " " + s4["tiles"][1]["value"]),
    ]
    first = True
    for head, det in alerts:
        if first:
            tf.paragraphs[0].text = head
            tf.paragraphs[0].font.size = Pt(15)
            tf.paragraphs[0].font.bold = True
            first = False
        else:
            add_para(tf, head, size=15, bold=True)
        add_para(tf, det, size=11, color=MUTED)

    s = new_slide(prs, banner, "Recommended actions")
    hi = [r for r in s7["tables"][0]["rows"] if r["high_priority"]]
    tbl = s.shapes.add_table(len(hi) + 1, 7, Inches(0.4), Inches(1.3), Inches(12.5), Inches(0.3 * (len(hi) + 1))).table
    heads = ["Material", "Criticality", "Shutdown", "PR date", "Order qty", "Order INR", "Lead time d"]
    for i, h in enumerate(heads):
        tbl.cell(0, i).text = h
    for r, x in enumerate(hi, 1):
        vals = [x["material"], x["criticality"], x["shutdown_flag"], x["raise_date"],
                f"{x['order_qty']:,.0f}", f"{x['order_value_inr']:,.2f}", f"{x['lead_time_days']:,.1f}"]
        for c, v in enumerate(vals):
            tbl.cell(r, c).text = v
    for r in range(len(hi) + 1):
        for c in range(7):
            for p in tbl.cell(r, c).text_frame.paragraphs:
                p.font.size = Pt(10)
    text(s, 0.4, 1.4 + 0.3 * (len(hi) + 1), 12.5, 1.2,
         "High-priority PR lines (raise now and VITAL, or position at or below safety stock). " + s7["tiles"][3]["label"] + ": " + s7["tiles"][3]["value"]
         + ". Recommendations go to a human for approval; nothing is written to SAP.", size=11, color=MUTED)

    s = new_slide(prs, banner, "Engine, reconciliation and what is not computable")
    tf = text(s, 0.4, 1.3, 12.5, 5.6, f"Engine: {meta['engine']['name']}, experiment {meta['engine']['experiment_id']}", size=13, bold=True)
    add_para(tf, "Best model as returned: " + meta["engine"]["best_model"] + ", " + meta["engine"]["primary_metric"] + " " + str(meta["engine"]["wql"]), size=12)
    add_para(tf, "Engine warning: " + meta["engine"]["warning"], size=10, color=MUTED)
    for n in d["reconciliation"]["notes"]:
        add_para(tf, n, size=12)
    for k in kpis:
        if k["status"] == "not_computable":
            add_para(tf, f"KPI {k['kpi']} {k['name']}: Not computable on demo scope. {k['detail']}", size=10, color=MUTED)

    os.makedirs(OUT, exist_ok=True)
    prs.save(FILE)
    print("wrote", FILE, len(prs.slides), "slides")


if __name__ == "__main__":
    main()
