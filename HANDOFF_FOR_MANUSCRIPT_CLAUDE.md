# Briefing for the Claude that writes the manuscript

Paste this whole file at the start of the manuscript session. The engine session updates it whenever something changes. Read `STATUS.md` after it.

## UPDATE 2026-11-21 (later): requests 20 and 21

- `results/44906558014` now also holds the redrawn Figure_7, Figure_8, Figure_9 and `tables/TS_cost_screening.csv` (commit 242d80b, run 44929081983). `provenance.json` has a `post_processing` entry. No existing table changed.
- `TS_cost_screening.csv` equals `manuscript/analysis/TS_cost_screening.csv` (no difference above 1e-9), so the Table 8 numbers match the package. Shaft power per scenario is not stored, so the fixed compressor/expander ratio for the nitrogen cycles stays.
- Zenodo archive built, not uploaded: branch `archive/v1.0`, see STATUS section 9.

## UPDATE 2026-11-21 (engine session 4, requests 12 to 19)

- New results branch: **`results/44906558014`** (run https://github.com/Gidoty/lng-robust-design/actions/runs/44906558014). It replaces the across, reversal, sensitivity and package outputs of `results/44682889025`. Quote numbers from the new branch only. The robust searches and the nominal, surrogate and Sobol units are unchanged and come from run 44682889025.
- Request 12 fixed: every nominal design is feasible at its own anchor A4. Nominal anchors feasible: SMR 5/6, single N2 2/6, dual N2 1/6; feasible fractions 0.86, 0.22, 0.14, so the nominal design still misses the 0.95 chance constraint in all three cycles.
- Request 13 done by selection from the existing archives (no new search): `TS_selection_table.csv`. The reported `cvar_iso` and `worst_iso` designs are now the same design in each cycle. The N2 iso-UA designs now meet the chance constraint (feasible fraction 1.00). SMR `cvar_iso` and `worst_iso` chains remain partial (generation 8 and 5): state that the design is the best found within the budget, not a proven optimum.
- New tables: `TS_failure_codes.csv`, `TS_across_per_scenario.csv`, `TS_robust_convergence.csv` (+ `Figure_S1`), `TS_selection_table.csv`, `TS_robust_chain_status.csv`; T6 has the z0 search spread columns. `PoR_scenario_mean` with interval exists for dual N2.
- Request 18 answer: the z0 search spread (0.002 to 0.67 %) does not explain the negative iso-UA PoR_z0 of the N2 cycles (-0.26 %, -0.44 %); the column `PoR_z0_within_z0_search_spread` is False. Report it as found. The nominal CVaR of 2.0 kWh/kg is the SEC_pen value charged for infeasible scenarios.
- Order of the older items below still applies. Items 7 (nominal feasibility) is superseded by the figures above.

## UPDATE 2026-11-20 (engine session 3)

- The engine now lives in **https://github.com/Gidoty/lng-robust-design** (public; code MIT, data CC BY 4.0). The old branch `ccr-0a266400-jmatdr` of the ScholarAI repository holds a mirror of this file, `STATUS.md`, `CLAUDE.md` and `manuscript/`.
- All of your requests 1 to 9 and 11 are applied (STATUS section 1). The register is the primary source (Ebrunu and Akpoturi 2025, Tables 4 to 10), Field D is outside the main envelope,
  and kappa and the nominal anchor are recomputed: **kappa = 178.7, nominal composition = A4 (Field C)**, scenario set = 6 anchors + 44 synthetic (S = 50), seed 20260101.
  Table 4 of your draft should match `lng_robust/data/feeds.csv` (printed sums 100.01, 100.01, 100.00, 99.63, 100.76, 99.98, 99.00 for Fields A to G).
- Phases 5 to 9 are built and tested. The full study finished on 2026-11-21 (run 44682889025). Its package exists, **but the SMR `cvar_iso` (generation 8 of 10) and SMR `worst_iso` (generation 5 of 10) chains are incomplete**. Write nothing final that depends on those two SMR designs. Everything else is complete. Read STATUS section 9 first.
- Results branch: `results/44682889025`. Full study run: https://github.com/Gidoty/lng-robust-design/actions/runs/44682889025. Quote numbers only from `results/<run_id>/` (tables, `RESULTS_SUMMARY.md` with file and row for each headline number). Probe runs are timing runs; their numbers are not results.

## What you may describe now, with the file as the source

| Topic | Source file |
|---|---|
| Benchmark validation (Jensen and Skogestad 2009 PASS; Austbo 2015 dual N2 PASS; Austbo single N2 FAIL on strict reading, input-precision limited) with the caveats in STATUS section 4 | `lng_robust/runs/validation_report.md`, `validation_summary.md` |
| Discretisation study, N = 100. UA changes -0.107 % (N = 100) and -0.025 % (N = 200) relative to N = 400; SEC at fixed MITA -0.118 % and -0.066 %. Use these CSV values, not the earlier STATUS text | `runs/mshe_convergence_smr.csv` |
| PR against GERG-2008, the vapour-fraction explanation of the 42.87 % point, volume translation (+0.55 to +0.58 % SEC), NeqSim cross-check | `runs/gerg_check_summary.csv`, `phase3_density_point.csv`, `phase3_translation.csv`, `neqsim_crosscheck_*.csv` |
| Feed register, kappa, nominal composition, scenario method, sensitivity envelopes | `lng_robust/data/feeds.csv`, `lng_robust/results/envelopes/` |
| The method of every unit: active-learning sampler, grouped validation, FFR with Wilson intervals, two-stage CVaR with a checkpointed GA, hybrid second stage, price of robustness, ranking reversal, Sobol with additive log-ratio composition, sensitivity protocol | STATUS section 3 and the code |
| Efficiency: equal results after caching (1e-9, 20 cases), solver comparison, CVaR convergence at S = 25, 50, 100 (S = 50 kept), budget | STATUS section 2, `runs/inner_solver_*.csv`, `cvar_convergence*.csv`, `budget_estimate_v2.csv` |
| Library versions and citations | STATUS section 7 (some entries marked AUTHOR TO VERIFY) |

## Things to state exactly as the engine does them

1. **Second stage.** The specified test (equal or lower SEC with fewer evaluations than the old method) was **not met**. State the second-stage solver as: penalised Nelder-Mead until the first feasible point, then SLSQP in a trust box;
   warm start from the scenario's previous solution or the surrogate's best-ranked point; 40 evaluations (64 for the dual cycle) in the outer loop; 80 with three restarts for the reported scenario evaluations.
   SEC at z0, the one number in Eq. 8, is the lowest of three rigorous searches. Your Section 2.10 says the second stage is "screened with surrogate models and the best candidates re-optimised". In the engine the surrogate chooses the cold-start and restart points only.
2. **Eq. 8 and its interval.** Eq. 8 is a single number at z0, so it has no bootstrap interval over scenarios. The tables give `PoR_z0` (no interval), `PoR_scenario_mean` with a bootstrap 95 % interval, the change in CVaR and the change in feasible fraction with intervals.
   Decide which of these the text reports beside Eq. 8, and word Section 2.9 to match. The engine did not change the PoR definition.
3. **Outer search.** Population 12, 11 generations (generation 0 is the initial population), seeded with the nominal design, UA bound = nominal UA (iso-UA) or 1.25 times it. The robust design is the best found, not a proven optimum; the best-objective history per generation is in each chain's `final.json`.
4. **Sensitivity.** Efficiency, cooler temperature and MITA_min cases re-run the nominal NSGA-II and re-evaluate the best chance-constraint-feasible designs among the top four of the main robust archive; they do not re-run the outer search.
   Alpha and SEC_pen cases re-select among the archive. Kappa, Field D and Field E cases evaluate the main designs on the alternative scenario sets. Your Section 2.11 says "one-at-a-time runs"; say what was run.
5. **Sobol.** Indices are for the gradient-boosting surrogate of feasible-case SEC in a box of +/-15 % of the variable range around the nominal design, with additive log-ratio composition in the envelope range. The rigorous one-at-a-time confirmation is `TS_oat_confirmation.csv`; report agreement or disagreement as found.
6. **Ranking reversal.** Cells are 4 x 4 quantile cells on treated N2 and C2+ (mol %); differences within 5 % (the validation acceptance band) are ties. Cells with no cycle meeting the chance constraint are shown as such.
7. **Nominal design feasibility.** In the convergence check on the dual cycle the nominal design was feasible in 24 to 26 % of scenarios. Do not generalise this to other cycles before the full results exist.
8. LNG N2 content (mol %, after end flash) is in T5 and T6 for every design.

## Project

Manuscript: "The price of robustness in modular LNG refrigeration: risk-averse design of single mixed refrigerant and nitrogen expander cycles for variable Niger Delta associated gas". Authors: Tunji Fadoyeni, Gideon Owhonda. Target: Gas Science and Engineering (Elsevier).

## Rules you must follow when writing

1. Every number in the paper must come from a file produced by the engine. Cite the file in your working notes. If no file has the number, write `[AUTHOR TO PROVIDE]`.
2. Never quote a number from a probe run or any folder labelled SMOKE. Surrogate values are not results.
3. Do not state or imply an outcome before the data exist in a full-run results package.
4. A null or negligible result is publishable if the method is sound. Write it plainly if that is what the data show.
5. Label anchors (published) and synthetic scenarios separately in text, tables and figures.
6. Do not add references you have not checked. Do not complete author lists, titles or DOIs from memory.
7. Follow the author's style: clear direct language, active voice, British English, no em dashes, no filler openers, no metaphors or analogies, concrete numbers when they exist.

## Items the engine could not finish

See STATUS section 8 and the INCOMPLETE section of `RESULTS_SUMMARY.md`. Documents still wanted from the authors are in `manuscript/REQUESTS_TO_ENGINE.md` (Tsay and Baldea 2018 PDF; the NeqSim, scikit-learn and CoolProp reference texts).
