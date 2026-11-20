# RESULTS SUMMARY

Run `44676187131`, preset `probe`, commit `3394ead04d`. Every number below is read from a file in this package or in the unit shards; none is typed by hand. Surrogate quantities appear only where labelled `Surrogate`. Anchors and synthetic scenarios are reported separately in the tables.

## Headline numbers

| Quantity | Value | Unit | Source file | Row | Column |
|---|---|---|---|---|---|
| Nominal SEC (smr) | 0.339 | kWh/kg | `tables/T5_nominal_designs.csv` | cycle=smr | SEC_kWh_per_kg |
| Nominal LNG N2 content (smr) | 0.1538 | mol % | `tables/T5_nominal_designs.csv` | cycle=smr | LNG_N2_mol_pct |
| Nominal UA (smr) | 1078 | kW/K | `tables/T5_nominal_designs.csv` | cycle=smr | UA_kW_per_K |
| Nominal SEC (n2_single) | 0.9379 | kWh/kg | `tables/T5_nominal_designs.csv` | cycle=n2_single | SEC_kWh_per_kg |
| Nominal LNG N2 content (n2_single) | 0.1631 | mol % | `tables/T5_nominal_designs.csv` | cycle=n2_single | LNG_N2_mol_pct |
| Nominal UA (n2_single) | 129.8 | kW/K | `tables/T5_nominal_designs.csv` | cycle=n2_single | UA_kW_per_K |
| Nominal SEC (n2_dual) | 0.9515 | kWh/kg | `tables/T5_nominal_designs.csv` | cycle=n2_dual | SEC_kWh_per_kg |
| Nominal LNG N2 content (n2_dual) | 0.143 | mol % | `tables/T5_nominal_designs.csv` | cycle=n2_dual | LNG_N2_mol_pct |
| Nominal UA (n2_dual) | 71.46 | kW/K | `tables/T5_nominal_designs.csv` | cycle=n2_dual | UA_kW_per_K |
| CVaR0.9 nominal (smr) | 0.5175 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=nominal | CVaR_0p9_kWh_per_kg |
| Feasible fraction nominal (smr) | 1 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=nominal | feasible_fraction |
| PoR at z0, cvar_iso (smr) | 83.76 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_iso | PoR_z0_pct |
| PoR scenario mean 95% CI low, cvar_iso (smr) | 63.63 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_iso | PoR_scenario_mean_lo95_pct |
| PoR scenario mean 95% CI high, cvar_iso (smr) | 126.4 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_iso | PoR_scenario_mean_hi95_pct |
| CVaR0.9 cvar_iso (smr) | 1.147 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_iso | CVaR_0p9_kWh_per_kg |
| Feasible fraction cvar_iso (smr) | 1 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_iso | feasible_fraction |
| PoR at z0, cvar_125 (smr) | 83.76 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_125 | PoR_z0_pct |
| PoR scenario mean 95% CI low, cvar_125 (smr) | 63.63 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_125 | PoR_scenario_mean_lo95_pct |
| PoR scenario mean 95% CI high, cvar_125 (smr) | 126.4 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_125 | PoR_scenario_mean_hi95_pct |
| CVaR0.9 cvar_125 (smr) | 1.147 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_125 | CVaR_0p9_kWh_per_kg |
| Feasible fraction cvar_125 (smr) | 1 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=cvar_125 | feasible_fraction |
| CVaR0.9 worst_iso (smr) | 1.147 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=worst_iso | CVaR_0p9_kWh_per_kg |
| Feasible fraction worst_iso (smr) | 1 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=smr, design=worst_iso | feasible_fraction |
| CVaR0.9 nominal (n2_single) | 2 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=nominal | CVaR_0p9_kWh_per_kg |
| Feasible fraction nominal (n2_single) | 0.5 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=nominal | feasible_fraction |
| PoR at z0, cvar_iso (n2_single) | 0 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_iso | PoR_z0_pct |
| PoR scenario mean 95% CI low, cvar_iso (n2_single) | 0 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_iso | PoR_scenario_mean_lo95_pct |
| PoR scenario mean 95% CI high, cvar_iso (n2_single) | 0 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_iso | PoR_scenario_mean_hi95_pct |
| CVaR0.9 cvar_iso (n2_single) | 2 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_iso | CVaR_0p9_kWh_per_kg |
| Feasible fraction cvar_iso (n2_single) | 0.8333 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_iso | feasible_fraction |
| PoR at z0, cvar_125 (n2_single) | -0.8427 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_125 | PoR_z0_pct |
| PoR scenario mean 95% CI low, cvar_125 (n2_single) | -2.068 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_125 | PoR_scenario_mean_lo95_pct |
| PoR scenario mean 95% CI high, cvar_125 (n2_single) | -0.8427 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_125 | PoR_scenario_mean_hi95_pct |
| CVaR0.9 cvar_125 (n2_single) | 2 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_125 | CVaR_0p9_kWh_per_kg |
| Feasible fraction cvar_125 (n2_single) | 0.8333 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=cvar_125 | feasible_fraction |
| CVaR0.9 worst_iso (n2_single) | 2 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=worst_iso | CVaR_0p9_kWh_per_kg |
| Feasible fraction worst_iso (n2_single) | 0.8333 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_single, design=worst_iso | feasible_fraction |
| CVaR0.9 nominal (n2_dual) | 2 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=nominal | CVaR_0p9_kWh_per_kg |
| Feasible fraction nominal (n2_dual) | 0.1667 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=nominal | feasible_fraction |
| PoR at z0, cvar_iso (n2_dual) | 0 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_iso | PoR_z0_pct |
| PoR scenario mean 95% CI low, cvar_iso (n2_dual) | nan | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_iso | PoR_scenario_mean_lo95_pct |
| PoR scenario mean 95% CI high, cvar_iso (n2_dual) | nan | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_iso | PoR_scenario_mean_hi95_pct |
| CVaR0.9 cvar_iso (n2_dual) | 2 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_iso | CVaR_0p9_kWh_per_kg |
| Feasible fraction cvar_iso (n2_dual) | 0 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_iso | feasible_fraction |
| PoR at z0, cvar_125 (n2_dual) | -57.87 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_125 | PoR_z0_pct |
| PoR scenario mean 95% CI low, cvar_125 (n2_dual) | -14.54 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_125 | PoR_scenario_mean_lo95_pct |
| PoR scenario mean 95% CI high, cvar_125 (n2_dual) | -14.54 | % | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_125 | PoR_scenario_mean_hi95_pct |
| CVaR0.9 cvar_125 (n2_dual) | 2 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_125 | CVaR_0p9_kWh_per_kg |
| Feasible fraction cvar_125 (n2_dual) | 0.5 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=cvar_125 | feasible_fraction |
| CVaR0.9 worst_iso (n2_dual) | 2 | kWh/kg | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=worst_iso | CVaR_0p9_kWh_per_kg |
| Feasible fraction worst_iso (n2_dual) | 0 | - | `tables/T6_nominal_cvar_worst_designs.csv` | cycle=n2_dual, design=worst_iso | feasible_fraction |
| Surrogate FFR overall, gradient boosting (smr) | 22.95 | % | `tables/T7_surrogate_performance.csv` | cycle=smr, model=gradient_boosting, output=feasibility | FFR_pct |
| Surrogate FFR near MITA limit, gradient boosting (smr) | 33.33 | % | `tables/T7_surrogate_performance.csv` | cycle=smr, model=gradient_boosting, output=feasibility | FFR_near_pct |
| Surrogate FFR overall, gradient boosting (n2_single) | 16 | % | `tables/T7_surrogate_performance.csv` | cycle=n2_single, model=gradient_boosting, output=feasibility | FFR_pct |
| Surrogate FFR near MITA limit, gradient boosting (n2_single) | 50 | % | `tables/T7_surrogate_performance.csv` | cycle=n2_single, model=gradient_boosting, output=feasibility | FFR_near_pct |
| Surrogate FFR overall, gradient boosting (n2_dual) | 18.6 | % | `tables/T7_surrogate_performance.csv` | cycle=n2_dual, model=gradient_boosting, output=feasibility | FFR_pct |
| Surrogate FFR near MITA limit, gradient boosting (n2_dual) | 0 | % | `tables/T7_surrogate_performance.csv` | cycle=n2_dual, model=gradient_boosting, output=feasibility | FFR_near_pct |
| Surrogate SEC MAE, gradient boosting (n2_single) | 0.158 | kWh/kg | `tables/T7_surrogate_performance.csv` | cycle=n2_single, model=gradient_boosting, output=SEC | MAE |
| Surrogate SEC MAE, gradient boosting (n2_dual) | 0.1284 | kWh/kg | `tables/T7_surrogate_performance.csv` | cycle=n2_dual, model=gradient_boosting, output=SEC | MAE |
| Cells with a ranking reversal | 0 | cells | `tables/TS_ranking_reversal_cells.csv` | all rows | reversal |
| Cells total | 8 | cells | `tables/TS_ranking_reversal_cells.csv` | all rows | cell |

## Unit status

- `unit-across-n2_dual`: complete
- `unit-across-n2_single`: complete
- `unit-across-smr`: complete
- `unit-nominal-n2_dual`: complete
- `unit-nominal-n2_single`: complete
- `unit-nominal-smr`: complete
- `unit-reversal-n2_dual-nominal`: complete
- `unit-reversal-n2_dual-robust`: complete
- `unit-reversal-n2_single-nominal`: complete
- `unit-reversal-n2_single-robust`: complete
- `unit-reversal-smr-nominal`: complete
- `unit-reversal-smr-robust`: complete
- `unit-robust-n2_dual-cvar_125-s1`: complete
- `unit-robust-n2_dual-cvar_125-s2`: complete
- `unit-robust-n2_dual-cvar_125-s3`: complete
- `unit-robust-n2_dual-cvar_iso-s1`: complete
- `unit-robust-n2_dual-cvar_iso-s2`: complete
- `unit-robust-n2_dual-cvar_iso-s3`: complete
- `unit-robust-n2_dual-worst_iso-s1`: complete
- `unit-robust-n2_dual-worst_iso-s2`: complete
- `unit-robust-n2_dual-worst_iso-s3`: complete
- `unit-robust-n2_single-cvar_125-s1`: complete
- `unit-robust-n2_single-cvar_125-s2`: complete
- `unit-robust-n2_single-cvar_125-s3`: complete
- `unit-robust-n2_single-cvar_iso-s1`: complete
- `unit-robust-n2_single-cvar_iso-s2`: complete
- `unit-robust-n2_single-cvar_iso-s3`: complete
- `unit-robust-n2_single-worst_iso-s1`: complete
- `unit-robust-n2_single-worst_iso-s2`: complete
- `unit-robust-n2_single-worst_iso-s3`: complete
- `unit-robust-smr-cvar_125-s1`: complete
- `unit-robust-smr-cvar_125-s2`: complete
- `unit-robust-smr-cvar_125-s3`: complete
- `unit-robust-smr-cvar_iso-s1`: complete
- `unit-robust-smr-cvar_iso-s2`: complete
- `unit-robust-smr-cvar_iso-s3`: complete
- `unit-robust-smr-worst_iso-s1`: complete
- `unit-robust-smr-worst_iso-s2`: complete
- `unit-robust-smr-worst_iso-s3`: complete
- `unit-sample-n2_dual`: complete
- `unit-sample-n2_single`: complete
- `unit-sample-smr`: complete
- `unit-sens-n2_dual-alpha080`: complete
- `unit-sens-n2_dual-alpha095`: complete
- `unit-sens-n2_dual-cool30`: complete
- `unit-sens-n2_dual-cool40`: complete
- `unit-sens-n2_dual-eff070`: complete
- `unit-sens-n2_dual-eff080`: complete
- `unit-sens-n2_dual-fieldD`: complete
- `unit-sens-n2_dual-fieldE_secondary`: complete
- `unit-sens-n2_dual-kappa_x0.5`: complete
- `unit-sens-n2_dual-kappa_x2`: complete
- `unit-sens-n2_dual-mita2`: complete
- `unit-sens-n2_dual-mita5`: complete
- `unit-sens-n2_dual-pen150`: complete
- `unit-sens-n2_dual-pen300`: complete
- `unit-sens-n2_single-alpha080`: complete
- `unit-sens-n2_single-alpha095`: complete
- `unit-sens-n2_single-cool30`: complete
- `unit-sens-n2_single-cool40`: complete
- `unit-sens-n2_single-eff070`: complete
- `unit-sens-n2_single-eff080`: complete
- `unit-sens-n2_single-fieldD`: complete
- `unit-sens-n2_single-fieldE_secondary`: complete
- `unit-sens-n2_single-kappa_x0.5`: complete
- `unit-sens-n2_single-kappa_x2`: complete
- `unit-sens-n2_single-mita2`: complete
- `unit-sens-n2_single-mita5`: complete
- `unit-sens-n2_single-pen150`: complete
- `unit-sens-n2_single-pen300`: complete
- `unit-sens-smr-alpha080`: complete
- `unit-sens-smr-alpha095`: complete
- `unit-sens-smr-cool30`: complete
- `unit-sens-smr-cool40`: INCOMPLETE_no_feasible_nominal
- `unit-sens-smr-eff070`: complete
- `unit-sens-smr-eff080`: complete
- `unit-sens-smr-fieldD`: complete
- `unit-sens-smr-fieldE_secondary`: complete
- `unit-sens-smr-kappa_x0.5`: complete
- `unit-sens-smr-kappa_x2`: complete
- `unit-sens-smr-mita2`: complete
- `unit-sens-smr-mita5`: INCOMPLETE_no_feasible_nominal
- `unit-sens-smr-pen150`: complete
- `unit-sens-smr-pen300`: complete
- `unit-sobol-n2_dual`: complete
- `unit-sobol-n2_single`: complete
- `unit-sobol-smr`: complete
- `unit-sobol_pref`: complete
- `unit-surrogate-n2_dual`: complete
- `unit-surrogate-n2_single`: complete
- `unit-surrogate-smr`: complete

## INCOMPLETE

- `unit-sens-smr-cool40`: INCOMPLETE_no_feasible_nominal
- `unit-sens-smr-mita5`: INCOMPLETE_no_feasible_nominal

## Files

Tables: T3_benchmark_reproduction.csv, T4_feed_compositions.csv, T5_nominal_designs.csv, T6_nominal_cvar_worst_designs.csv, T7_surrogate_performance.csv, TS_oat_confirmation.csv, TS_ranking_reversal_cells.csv, TS_sensitivity_cases.csv, TS_sobol_indices.csv, TS_sobol_preference.csv, TS_surrogate_vs_rigorous_at_optima.csv

Figures: Figure_1.pdf, Figure_1.png, Figure_2.pdf, Figure_2.png, Figure_3.pdf, Figure_3.png, Figure_4.pdf, Figure_4.png, Figure_5.pdf, Figure_5.png, Figure_6.pdf, Figure_6.png, Figure_7.pdf, Figure_7.png, Figure_8.pdf, Figure_8.png, Figure_9.pdf, Figure_9.png