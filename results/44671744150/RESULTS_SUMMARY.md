# RESULTS SUMMARY

Run `44671744150`, preset `probe`, commit `b5615905ba`. Every number below is read from a file in this package or in the unit shards; none is typed by hand. Surrogate quantities appear only where labelled `Surrogate`. Anchors and synthetic scenarios are reported separately in the tables.

## Headline numbers

| Quantity | Value | Unit | Source file | Row | Column |
|---|---|---|---|---|---|
| Nominal SEC (n2_single) | 1.028 | kWh/kg | `tables/T5_nominal_designs.csv` | cycle=n2_single | SEC_kWh_per_kg |
| Nominal LNG N2 content (n2_single) | 0.2219 | mol % | `tables/T5_nominal_designs.csv` | cycle=n2_single | LNG_N2_mol_pct |
| Nominal UA (n2_single) | 84.51 | kW/K | `tables/T5_nominal_designs.csv` | cycle=n2_single | UA_kW_per_K |
| Nominal SEC (n2_dual) | 0.8517 | kWh/kg | `tables/T5_nominal_designs.csv` | cycle=n2_dual | SEC_kWh_per_kg |
| Nominal LNG N2 content (n2_dual) | 0.1601 | mol % | `tables/T5_nominal_designs.csv` | cycle=n2_dual | LNG_N2_mol_pct |
| Nominal UA (n2_dual) | 150.7 | kW/K | `tables/T5_nominal_designs.csv` | cycle=n2_dual | UA_kW_per_K |
| Surrogate FFR overall, gradient boosting (smr) | 7.937 | % | `tables/T7_surrogate_performance.csv` | cycle=smr, model=gradient_boosting, output=feasibility | FFR_pct |
| Surrogate FFR near MITA limit, gradient boosting (smr) | 14.29 | % | `tables/T7_surrogate_performance.csv` | cycle=smr, model=gradient_boosting, output=feasibility | FFR_near_pct |
| Surrogate FFR overall, gradient boosting (n2_single) | 19.23 | % | `tables/T7_surrogate_performance.csv` | cycle=n2_single, model=gradient_boosting, output=feasibility | FFR_pct |
| Surrogate FFR near MITA limit, gradient boosting (n2_single) | 66.67 | % | `tables/T7_surrogate_performance.csv` | cycle=n2_single, model=gradient_boosting, output=feasibility | FFR_near_pct |
| Surrogate FFR overall, gradient boosting (n2_dual) | 28 | % | `tables/T7_surrogate_performance.csv` | cycle=n2_dual, model=gradient_boosting, output=feasibility | FFR_pct |
| Surrogate FFR near MITA limit, gradient boosting (n2_dual) | 75 | % | `tables/T7_surrogate_performance.csv` | cycle=n2_dual, model=gradient_boosting, output=feasibility | FFR_near_pct |
| Surrogate SEC MAE, gradient boosting (n2_single) | 0.2086 | kWh/kg | `tables/T7_surrogate_performance.csv` | cycle=n2_single, model=gradient_boosting, output=SEC | MAE |
| Surrogate SEC MAE, gradient boosting (n2_dual) | 0.1478 | kWh/kg | `tables/T7_surrogate_performance.csv` | cycle=n2_dual, model=gradient_boosting, output=SEC | MAE |

## Unit status

- `unit-nominal-n2_dual`: complete
- `unit-nominal-n2_single`: complete
- `unit-nominal-smr`: INCOMPLETE_no_feasible_design
- `unit-robust-n2_dual-cvar_125-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_dual-cvar_iso-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_dual-worst_iso-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_single-cvar_125-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_single-cvar_iso-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_single-worst_iso-s1`: INCOMPLETE_no_done_json
- `unit-sample-n2_dual`: complete
- `unit-sample-n2_single`: complete
- `unit-sample-smr`: complete
- `unit-sobol-n2_dual`: complete
- `unit-sobol-n2_single`: complete
- `unit-surrogate-n2_dual`: complete
- `unit-surrogate-n2_single`: complete
- `unit-surrogate-smr`: complete

## INCOMPLETE

- `unit-nominal-smr`: INCOMPLETE_no_feasible_design
- `unit-robust-n2_dual-cvar_125-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_dual-cvar_iso-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_dual-worst_iso-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_single-cvar_125-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_single-cvar_iso-s1`: INCOMPLETE_no_done_json
- `unit-robust-n2_single-worst_iso-s1`: INCOMPLETE_no_done_json

## Files

Tables: T3_benchmark_reproduction.csv, T4_feed_compositions.csv, T5_nominal_designs.csv, T7_surrogate_performance.csv, TS_oat_confirmation.csv, TS_sobol_indices.csv

Figures: Figure_1.pdf, Figure_1.png, Figure_2.pdf, Figure_2.png, Figure_3.pdf, Figure_3.png, Figure_4.pdf, Figure_4.png, Figure_5.pdf, Figure_5.png, Figure_8.pdf, Figure_8.png, Figure_9.pdf, Figure_9.png