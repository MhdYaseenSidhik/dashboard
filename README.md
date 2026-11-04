# HZL_DEMO inventory pack: partial delivery (S-1)

**Demo scope: PART_001, plant HZL_DEMO_05, top 50 materials.** As-of 2025-12-31. History Jan 2024 to Dec 2025. ZSPR/ZSPN only. IS_BACKCAST_PERIOD='N'. INR. Synthetic POC data, read-only SAP HANA (VEDANTA_POC).

## Status

**Not complete.** This branch holds the verified forecast evaluation and the series evidence. The ten sections, the scorecard, the site, the Excel workbook and the deck are NOT built. The 6-month forward forecast is NOT produced.

## What is here

| Path | Content |
|---|---|
| `queries/demo_net_issue_series.sql` | Steward series, 50 x 24 = 1,200 rows (net issues 261 minus 262, zero-filled). |
| `queries/raw_verification_top50.sql` | RAW recompute: 50 materials, SUM 171,630.000, 1,046 non-zero rows. |
| `data/forecast_evaluation.json` | Engine leaderboard, holdout WAPE and KPI 5, from the earlier run. |
| `data/holdout_predictions.csv` | Engine holdout predictions (300 rows). |
| `data/holdout_predictions_v3.csv` | Same file re-downloaded from ContextFlow transfer 2a3496ff. sha256 6d278122... matches the transfer record and the earlier file. |

## Model (ContextFlow, on-prem engine)

- Experiment `6aeb1d0f2362f14961979898` ("HZL demo forecast v3"), status succeeded.
- Asset `6aeb1cdc9eb9bc04a93bb2f8`, dataset `hzl-demo-net-issue-series-v3.csv`, 1,200 rows, 50 series.
- Preset fast, predictionLength 6, holdoutFraction 0.25, primary metric WQL.
- Best candidate: WeightedEnsemble (WQL 0.757317). Leaderboard as the engine returned it: ETS 0.76902; DirectTabular 0.776294; RecursiveTabular 0.90806; SeasonalNaive 0.918111; Naive 0.918111.
- Engine warning, verbatim: "Holdout diagnostics unavailable: ValueError: 0'th time-series in data must be a dict, got<class 'numpy.ndarray'>".

## Figures

- Holdout WAPE (Jul to Dec 2025, 300 rows): **0.8374**. KPI 5 demand accuracy = 1 minus WAPE = **0.1626** (target 0.90).
- Oct to Dec 2025 sub-window: WAPE 0.8543, 1 minus WAPE 0.1457.
- Share of actuals inside the engine interval: 87.7%.
- Holdout sum actual 61,375; sum predicted 32,236.358.

## Tables, raw vs curated

- **RAW (system of record):** FACT_MATERIAL_MOVEMENT_PART_001 to 004, DIM_MATERIAL (MATERIAL_TYPE), used for the series.
- **Curated:** INVENTORY_KPI_MONTHLY, INVENTORY_CLASSIFICATION, REORDER_RECOMMENDATION. **Not yet read.** No raw-vs-curated reconciliation exists for this branch.

## Gaps (stated, not hidden)

1. **Dataset artifact unavailable.** `contextflow_transfer prepare_download .../dataset` returned verbatim: "The original dataset artifact is unavailable". So predict-batch (6-month forward forecast) was not run. No forecast was hand-rolled.
2. **KPI 6** (inventory forecast accuracy above 90%): not computable on demo scope. Only the demand measure exists.
3. **KPI 7** (NM/SM F1): not computable on demo scope. No NM/SM classifier was run.
4. **12-month figures:** not computable on demo scope. The engine horizon is 6 months.
5. **Curated reconciliation** (INVENTORY_KPI_MONTHLY and the others): not performed.
6. **Sparse series:** 1,046 of 1,200 rows non-zero. PART_001 non-backcast rows end 2024-07-19 per the earlier steward check, so treat as demo only.
7. Ten sections, the 13-KPI scorecard, the static site, the Excel workbook and the deck: not built.
