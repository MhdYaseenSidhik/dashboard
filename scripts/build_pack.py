"""Build dashboard/data/pack.json from verified inputs only.

Inputs (all in this repo):
  data/demo_net_issue_series.csv        Steward series, 1,200 rows (RAW-verified)
  data/raw/forecast_evaluation_download.csv  ContextFlow holdout (sha256 checked)
  data/raw/forward_mean_6m_45of50.csv   ContextFlow predict-batch mean, 45 of 50 series
Outputs: data/pack.json
"""
import json
import pandas as pd

BASE = "dashboard"
SCOPE = "Demo scope: PART_001, plant HZL_DEMO_05, top 50 materials."

series = pd.read_csv(f"{BASE}/data/demo_net_issue_series.csv")
ev = pd.read_csv(f"{BASE}/data/raw/forecast_evaluation_download.csv")
fwd = pd.read_csv(f"{BASE}/data/raw/forward_mean_6m_45of50.csv")

hist = series.groupby("MONTH")["NET_QTY"].sum().sort_index()
history = [{"month": m[:7], "net_qty": float(v)} for m, v in hist.items()]

ho = ev.groupby("timestamp")[["actual", "predicted"]].sum().sort_index()
holdout = [{"month": m[:7], "actual": float(r.actual), "predicted": round(float(r.predicted), 1)} for m, r in ho.iterrows()]

fwd_cols = [c for c in fwd.columns if c != "MATERIAL_PLANT"]
fwd_tot = fwd[fwd_cols].sum()
forward = [{"month": c, "forecast_45_series": round(float(v), 1)} for c, v in fwd_tot.items()]

wape = float(ev.absolute_error.sum() / ev.actual.abs().sum())
acc_6m = 1 - wape
pos = ev[ev.actual > 0]
wape_3m_mask = ev.timestamp >= "2025-10-01"
wape_3m = float(ev[wape_3m_mask].absolute_error.sum() / ev[wape_3m_mask].actual.abs().sum())

raw_check = {
    "n_materials": int(series.MATERIAL_PLANT.nunique()),
    "rows": int(len(series)),
    "months": int(series.MONTH.nunique()),
    "sum_net_qty": float(series.NET_QTY.sum()),
    "nonzero_rows": int((series.NET_QTY != 0).sum()),
    "raw_sum_net_qty": 171630.000,
    "raw_nonzero_rows": 1046,
}

pack = {
    "scope": SCOPE,
    "as_of": "2025-12-31",
    "plant": "HZL_DEMO_05",
    "experiment_id": "6aeb1d0f2362f14961979898",
    "asset_id": "6aeb1cdc9eb9bc04a93bb2f8",
    "upload_file_id": "6aeb29982362f149619798b9",
    "model": {
        "best_candidate": "WeightedEnsemble",
        "primary_metric": "WQL",
        "leaderboard": [
            {"rank": 1, "model": "WeightedEnsemble", "WQL": 0.757317},
            {"rank": 2, "model": "ETS", "WQL": 0.76902},
            {"rank": 3, "model": "DirectTabular", "WQL": 0.776294},
            {"rank": 4, "model": "RecursiveTabular", "WQL": 0.90806},
            {"rank": 5, "model": "SeasonalNaive", "WQL": 0.918111},
            {"rank": 6, "model": "Naive", "WQL": 0.918111},
        ],
        "engine_warning": "Holdout diagnostics unavailable: ValueError: 0'th time-series in data must be a dict, got<class 'numpy.ndarray'>",
    },
    "metrics": {
        "wape_6m": round(wape, 4),
        "accuracy_6m_1_minus_wape": round(acc_6m, 4),
        "wape_3m_oct_dec_2025": round(wape_3m, 4),
        "within_interval_share": round(float(ev.within_interval.mean()), 4),
        "holdout_sum_actual": float(ev.actual.sum()),
        "holdout_sum_predicted": round(float(ev.predicted.sum()), 3),
        "holdout_rows": int(len(ev)),
        "holdout_sha256": "6d27812241fff73ee43a7fa701a4a837f260c7a65c7089a96940846f94e4b5a9",
    },
    "history": history,
    "holdout": holdout,
    "forward": forward,
    "forward_series_count": int(len(fwd)),
    "forward_series_expected": 50,
    "raw_check": raw_check,
}

with open(f"{BASE}/data/pack.json", "w") as f:
    json.dump(pack, f, indent=2)
print(json.dumps({k: pack[k] for k in ("metrics", "raw_check", "forward_series_count")}, indent=2))
