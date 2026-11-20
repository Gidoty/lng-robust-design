# STATUS

State at the end of engine session 3 (2026-11-20). This file says what works, what fails, what is untested and what is still needed.
It contains no study result. Numbers below are tests, diagnostics, timings and validation deviations of the code.
Repository: `Gidoty/lng-robust-design` (moved from `scholarship_application_intelligence_system`, branch `ccr-0a266400-jmatdr`).
Engine work is committed to branch `ccr-97ba1493-9mtuu0` and `main` of the new repository. `STATUS.md`, `HANDOFF_FOR_MANUSCRIPT_CLAUDE.md`,
`CLAUDE.md` and `manuscript/` are mirrored to the old branch.

## 0. Current state

| Item | State |
|---|---|
| Tests | **74 passed** (`python -m pytest -q`, about 35 s). Includes golden-output equivalence at 1e-9 and chunk-and-merge equivalence |
| Phases 1 to 4 | done (earlier sessions) |
| Phases 5 to 9 code | **built and tested** (section 3). Not yet producing results: see the run table below |
| Phase 10 | LICENSE (MIT), LICENSE-DATA (CC BY 4.0), CITATION.cff, `tools/zenodo_archive.py` (does not upload) |
| Probe runs (timing only, numbers are NOT results) | GitHub Actions run 44676187131 (all units complete), later probe runs listed in section 9 |
| Full study | see section 9 (run IDs, branch, resume command) |

Open author decisions: none of D1 to D11. The remaining ASSUMPTION values in `design_basis.yaml` are listed in section 8.

## 1. Requests from the manuscript session (REQUESTS_TO_ENGINE.md), what was done

| # | Request | Done | Where |
|---|---|---|---|
| 1 | D11 option (b): Field D out of the main envelope, kept as a sensitivity case; recompute kappa and the nominal anchor; LNG N2 content for every design | yes | `design_basis.yaml` (`main_envelope_excluded_anchors`), `doe/envelope.py`, `lng_N2_mol_pct` in every evaluation row, T5 and T6 |
| 2 | Primary Ebrunu and Akpoturi (2025) values, isomers as printed, C6 and heavier lumped | yes | `data/feeds.csv`, `data/sources/SOURCES.md` |
| 3 | Drop A1 (Soku) | yes. A9 (Sonibare) also dropped because the manuscript no longer cites it. Ids A2 to A8 are kept as stable labels | `feeds.csv`, `SOURCES.md` |
| 4 | Khan basis notes replaced | yes: efficiency 0.75, MITA 3 K, feed 30 C and 50 bar are `ASSUMPTION; sensitivity tested`. Khan benchmark entries stay INCOMPLETE and are labelled as not cited | `design_basis.yaml`, `benchmarks.yaml` |
| 5 | Tsay and Baldea (2018) citation | yes: Ind. Eng. Chem. Res. 57(17), 5868-5880, doi 10.1021/acs.iecr.7b03634 | `NOVELTY_NOTES.md` |
| 6 | Discretisation statement | corrected in section 5 from `runs/mshe_convergence_smr.csv` | this file |
| 7 | LNG N2 content, library versions | yes (section 7) | |
| 8 | D1 to D11 decided by the authors | recorded as DECIDED by the authors (Fadoyeni and Owhonda) | `design_basis.yaml` |
| 9 | Printed totals, renormalise, Field E sensitivity | yes: printed sums are 100.01, 100.01, 100.00, 99.63, 100.76, 99.98, 99.00 (Fields A to G); renormalised for simulation only. Field E sensitivity row `A6S` uses the secondary C1 84.03 and C2 4.14 and nothing else from the secondary copy; its components then sum to 100.00 | `feeds_sensitivity_fieldE.csv` |
| 10 | Run Phases 5 to 10 on GitHub Actions | workflow built and probed (section 9) | `.github/workflows/study.yml` |
| 11 | Versions and citations | section 7 | |

How the primary values were read: the PDF text layer splits every number over two lines ("0.1" above "3" for 0.13). The text was joined cell by cell and
checked against the rendered page (PDF page 5, printed page 108, Tables 4 to 10) and against the propane, iso-butane and n-butane rows of Table 12,
which agree for all seven fields. The values differ from the secondary copy for Field E (C1 84.09 against 84.03, C2 4.84 against 4.14), Field F (C1 77.59 against 77.60)
and others; Fields B and G differ in the second decimal.

## 2. Efficiency work (quality must not drop)

### 2.1 Profile of one evaluation (`runs/profile_*.txt`, `analysis/profile_eval.py`, warm process)

| Cycle | Time | Flashes | Share of time in the exchanger table build |
|---|---|---|---|
| SMR | 1.85 s | 177 | 73 % (1.34 s) |
| Single N2 | 1.05 s | 175 | 90 % (0.94 s) |
| Dual N2 | 1.15 s | 277 | 92 % (1.06 s) |

Nearly all of that is Michelsen stability tests inside `thermo` TP flashes of the natural-gas and refrigerant mixtures.

### 2.2 What was changed, and the proof that results did not change

- Exact-key cache of TP flashes and saturation temperatures (`props/eos.py`). A hit returns the object computed for identical (T, P, z), so results are bit-for-bit the same.
  The natural-gas table depends only on T_lng and the HP refrigerant table only on P_high and T_lng, so a local solver that perturbs one variable at a time reuses most states.
- Vectorised pressure grid of the exchanger table (`units/mshe.py`).
- Proof: 20 fixed cases (7 SMR, 7 single N2, 6 dual N2): 5 feasible, 4 MITA_VIOLATION, 8 TEMP_CROSS, 2 LIQUID_AT_SUCTION, 1 LIQUID_AT_EXPANDER; UA is finite in 9 and MITA in 19. NaN positions are compared too.
  Reference outputs were produced by the code before any change (`tests/data/golden_eval.csv`). `tests/test_golden.py` compares 16 outputs per case at 1e-9 relative tolerance, and
  checks that the cache returns the identical object and that results are bitwise equal with the cache switched off. All pass.
- Not changed: stability test, tolerances, N = 100, table points 48. A cheaper stability test or hot-started flashes would change the algorithm, so they were not used.

### 2.3 Second-stage solver (equal or lower SEC with fewer evaluations): NOT demonstrated as specified

10 scenarios per cycle (the 6 anchors then 4 synthetic neighbours, equipment fixed, warm start from the parent anchor for synthetic scenarios).
Files: `runs/inner_solver_comparison*.csv`, `inner_solver_summary*.csv`, `analysis/inner_benchmark.py`. Baselines: penalised Nelder-Mead (the old method) at 16 and 40 evaluations
and at 150 evaluations as a near-converged reference.

| Method tried | Result |
|---|---|
| SLSQP, warm start, 0 or 3 random restarts | lower SEC where it found a feasible point (1.6 to 15 % below Nelder-Mead at 40), but it used its whole cap of 40 evaluations on every scenario and found no feasible point in 3 of 10 dual-N2 scenarios and 9 of 10 SMR scenarios. The first linearised step from an infeasible start jumps into TEMP_CROSS regions because MITA changes about 5 K per K of T_lng |
| Trust-region sequential LP with Broyden updates | fewer evaluations (11 to 33) but it stopped without a feasible point on SMR and several dual-N2 scenarios. Kept in `opt/inner.py` as evidence, not used |
| **Hybrid (used)**: Nelder-Mead until the first feasible point, then SLSQP in a box of half-width 0.20 around it | see below |

Hybrid against Nelder-Mead at 40 evaluations (paired by scenario; `runs/inner_solver_summary_final.csv`):

| Cycle | Hybrid 40: evals, equal-or-lower SEC, mean difference | Hybrid 80 with 3 restarts: evals, equal-or-lower, mean difference | Wall time, hybrid 40 against Nelder-Mead 40 |
|---|---|---|---|
| Dual N2 | 400 against 397, 1 of 10, +9.2 % | 800, 5 of 10, +0.9 % | 78 s against 204 s |
| Single N2 | 400 against 395, 10 of 10, -8.0 % | 800, 10 of 10, -13.9 % | 75 s against 156 s |
| SMR | 400 against 393, 6 of 10, +0.7 % | 800, 7 of 10, -1.7 % | 210 s against 445 s |

All three methods find a feasible point in 10 of 10 scenarios. Verdict: the criterion "equal or lower SEC with **fewer evaluations**" is **not met**. At equal evaluations the hybrid is better on single N2,
equal on SMR and worse on dual N2; wall time is 2.1 to 2.6 times lower than Nelder-Mead at 40 (the same evaluations are cheaper because of the flash cache). Against the 150-evaluation reference, hybrid 80 is 1.1 % (SMR) and 9.3 % (dual N2) above it and 6.3 % below it on single N2 (Nelder-Mead at 150 evaluations is not fully converged there).
What the study does about this:
- outer loop: hybrid, 40 evaluations (dual N2 64), each scenario warm-started from its own previous best point; cold starts use the surrogate's best-ranked point (decision D6);
- reported evaluations (`across`): 80 evaluations with 3 restarts for the 50 scenarios, and **SEC at z0 is the lowest of three rigorous searches** (scenario search, a 200-evaluation hybrid, a 150-evaluation Nelder-Mead; for the nominal design also its own NSGA-II value), because only this number enters Eq. 8. All candidates are in `sec_z0_candidates.json`.
- the surrogate screening of D6 acts only through the cold-start point and the restart points; in a warm-started outer loop most solves use the whole budget before a restart runs. This is a weaker use of D6 than the manuscript text suggests. Say so.

### 2.4 CVaR convergence with S (`runs/cvar_convergence.csv`, `cvar_convergence_verdict.json`, `analysis/cvar_convergence.py`)

Dual N2, two fixed designs, nested scenario sets (S = 25, 50 and 100 share the per-anchor synthetic draws), alpha = 0.9, hybrid 40 evaluations.
The nominal design is feasible in 24 to 26 % of scenarios, so its CVaR equals the penalty (2.0 kWh/kg) at every S and carries no convergence information.
The same design with 25 % more conductance and rated flow: CVaR 0.8703 (S = 25, +1.22 % from S = 100), 0.8666 (S = 50, +0.79 %), 0.8598 (S = 100). Random 25- and 50-scenario subsets of the 100: mean CVaR 0.8527 and 0.8576, standard deviation 0.0162 and 0.0073.
Rule: smallest S within 1 % of S = 100. S = 25 fails, S = 50 passes. **S = 50 is used** (also D5). One cycle only, as specified.

### 2.5 Budget, old against new (`runs/budget_estimate_v2.csv`, `analysis/budget_estimate_v2.py`)

Measured inputs (4-core runner class, from the probe shards): 0.62 s per rigorous evaluation for SMR, 0.20 s single N2, about 0.25 s dual N2 (benchmark), parallel efficiency assumed 0.85.

| | Old plan (STATUS of 2026-11-20, session 2) | New plan |
|---|---|---|
| Rigorous evaluations | 416,000 | about 3,260,000 |
| Wall time | about 22 h on 4 workers | critical path about 15.8 h (jobs run in parallel) |
| Runner-minutes | 1,320 | about 5,650 |
| Outer search | population 8, 8 generations, 12 evaluations per scenario | population 12, 11 generations, 40 to 64 evaluations per scenario, 5 chained jobs of up to 280 min |

The new plan does 7.8 times more evaluations than the old one at a shorter critical path. Runner-minutes are not scarce (public repository). Actual runner-minutes of the full run are in section 9.

## 3. Phases 5 to 9: what the code does

All units: `python -m lng_robust.study.cli <unit> --cycle <c> [--variant v] [--case k] --preset probe|full --work work`.
Every rigorous evaluation (feasible or not) is written to Parquet shards (`evals-*.parquet`, zstd) with its failure code.

| Unit | Content |
|---|---|
| `nominal` | NSGA-II, population 60, 40 generations, on SEC and specific UA at the nominal composition (A4, Field C); knee design; exchanger composite curves. The initial screen is 180 random candidates plus 10 hand-set seed designs (`analysis/golden.py`); the reported design is whatever NSGA-II returns |
| `sample` | Phase 5. Latin hypercube plus a cloud around the nominal design, then 10 rounds of 800 candidates chosen by active learning: near the predicted MITA limit, around known feasible points, high predicted feasibility with low SEC, and exploration. Everything is evaluated rigorously |
| `surrogate` | Phase 6. Gradient boosting, Gaussian process (Matern 5/2, at most 1500 training points per fold) and ridge regression; gradient-boosting and logistic classifiers; leave-one-anchor-out (the anchor and its Dirichlet neighbours withheld together). FFR = FP/(FP+TN) overall and within 1 K of MITA_min, with counts and Wilson 95 % intervals; also with numerical failures excluded |
| `robust` | Phase 7. Two-stage design: first stage (SMR refrigerant weights and UA; N2 cycles UA and rated flow) by an elitist real-coded GA with feasibility rules; second stage re-optimised for each of S = 50 scenarios. CVaR at 0.9, chance constraint 0.95. Variants: `cvar_iso` (UA budget factor 1.0, primary), `cvar_125` (secondary), `worst_iso` (max over scenarios, the bound). Checkpoint (GA state, warm starts, archive) after every generation |
| `across` | nominal and robust designs over the 50 scenarios, price of robustness (below), designs at z0 (Tables 5 and 6), surrogate against rigorous at every scenario optimum (Figure 8) |
| `reversal` | Phase 8. 300 compositions (6 anchors plus Dirichlet samples), nominal and CVaR-iso designs, second stage re-optimised. Cells: 4 x 4 quantile cells on treated N2 and C2+ (mol %). Preferred cycle per cell: lowest mean SEC among cycles meeting the chance constraint; differences within 5 % (the acceptance band of the validation) count as indistinguishable and are not reversals |
| `sobol`, `sobol_pref` | Sobol (SALib, Saltelli, N = 1024) on the gradient-boosting surrogate with additive log-ratio composition, in a box of +/-15 % of the variable range around the nominal design and the envelope range of the ALR coordinates; rigorous one-at-a-time runs over the same box, Spearman correlation and top-2 agreement. `sobol_pref`: composition-only indices for each cycle's SEC and for pairwise SEC differences with each design fixed at its nominal values |
| `sens` | efficiency 0.70 and 0.80 (both machines), cooler outlet 30 and 40 C, MITA_min 2 and 5 K; alpha 0.8 and 0.95 and SEC_pen 1.5 and 3.0 (re-selection among the archive, no new evaluations); kappa x0.5 and x2, Field D (seven anchors) and Field E secondary values (new scenario sets) |
| `package` | tables T3 to T7 and supplementary tables (CSV), Figure_1 to Figure_9 (600 dpi PNG and vector PDF), `provenance.json`, `RESULTS_SUMMARY.md`, committed to `results/<run_id>` |

Price of robustness: Eq. 8 is unchanged, `PoR(z0) = (SEC(x_rob, z0) - SEC(x_nom, z0)) / SEC(x_nom, z0)`, with the operation re-optimised at z0 for both designs.
Eq. 8 is one number, so a bootstrap interval over scenarios cannot belong to it. The tables therefore report, with the names below, `PoR_z0` (no interval), `PoR_scenario_mean`
(mean of the paired relative differences over scenarios feasible for both designs, bootstrap 95 % interval over scenarios, 5000 resamples), the change in CVaR and the change in feasible fraction, each with a bootstrap interval.
Which one the manuscript prints next to Eq. 8 is an author decision.

**Chunking.** No unit exceeds 280 minutes of compute by design: the robust chain stops after any generation once the next one would not fit, writes its checkpoint, and the next chained job resumes from it
(five chained jobs; later jobs are no-ops when the chain has finished). Tests: `test_chunk_and_merge_equals_single_run` (a chain run as one job equals the same chain run as 4 resumed jobs: identical state, identical archive),
`test_scenario_eval_chunking_matches_single_pass_on_real_cycle` (real rigorous second stage, scenarios evaluated together or one by one give identical SEC),
`test_ga_is_deterministic_resumable...` (GA state round trip through JSON).

## 4. Validation (files: `runs/validation_report.md`, `validation_points.csv`, `validation_rounding.csv`, `validation_summary.md`)

Acceptance: |deviation| <= 5 % on every published quantity at every point, primary equation of state Peng-Robinson (fixed before results were seen). Unchanged this session.

| Benchmark | Source | Strict verdict | Detail (PR primary) |
|---|---|---|---|
| Jensen and Skogestad 2009 PRICO Case 1 | Part I Table 2; feed composition and pressure drops from secondary sources | **PASS** | compressor power -0.66 %, LNG flow -0.53 %. SRK cross-check +0.32 % and -0.80 % |
| Austbo 2015 single N2 expander, PR columns (Table 5.4), 15 points | thesis pp. 111, 124 | **FAIL** (14 of 15 within 5 %) | mean absolute 1.95 %. The failing point (+21.95 %) is input-precision limited (printed inputs allow 1686 to 2709 kW against 1813 kW published). 13 well-resolved points: mean absolute 0.29 %, maximum 1.18 % |
| Austbo 2015 single N2 expander, SRK columns | same | **FAIL** (12 of 15) | all three failures have pressures printed as whole numbers. 11 well-resolved points: PR 1.29 % mean, 1.94 % maximum; SRK cross-check 0.24 % and 0.50 % |
| Austbo 2015 dual N2 expander (Table 5.9, SRK), 15 points | thesis pp. 137, 142 | **PASS** | PR: 15 of 15, mean absolute 1.14 %, maximum 1.63 %. SRK cross-check maximum 0.45 % |
| Khan et al. 2015 | not cited by the manuscript | INCOMPLETE, unused | inputs null by rule |

Caveats that travel with these numbers: the Jensen feed composition and pressure drops are secondary-source; SRK runs reuse PR binary parameters; at published designs the computed MITA is generally below the
published dTmin, so many published designs violate MITA in this model although power agrees; single-expander pressures are rounded in the source.

## 5. Model credibility checks (Phase 3)

- Discretisation, interior pinch (`runs/mshe_convergence_smr.csv`, hand-set SMR design, pinch at node 30 of 100). Values relative to N = 400:
  UA -0.107 % at N = 100 and -0.025 % at N = 200 (so UA changes 0.082 % from N = 100 to 200 and 0.025 % from N = 200 to 400);
  MITA 2.0299 K at N = 100, 2.0240 K at N = 200, 2.0145 K at N = 400 (0.015 K from N = 100 to 400);
  SEC at fixed MITA -0.118 % at N = 100 and -0.066 % at N = 200. **Study value N = 100.** (The earlier text said "UA changes 0.08 % from N = 200 to 400"; that was wrong.)
  The Jensen design pinches at the cold end for every flow, so it cannot test interior pinches.
- The 42.87 % PR-versus-GERG density point (`runs/phase3_density_point.csv`) is a PR phase-equilibrium difference (molar vapour fraction 0.029 against 0.051), not a CoolProp convention artefact.
- Volume translation (`runs/phase3_translation.csv`): SEC +0.55 to +0.58 %, MITA about -0.19 K. Report as model-form sensitivity.
- Independent property engine (`runs/neqsim_crosscheck_*.csv`): NeqSim Peng-Robinson in the same flowsheet code: SEC -0.15 % (SMR), -0.07 % (single N2), -0.05 % (dual N2); UA -3.1 % on the one feasible design. DWSIM was not tried. The flowsheet logic is shared, so this checks the property implementation only.
- PR against GERG-2008: mean absolute density deviation 0.87 % in gas, 9.45 % in liquid, 5.31 % overall (`runs/gerg_check_summary.csv`); one CoolProp wrong-branch point is flagged `GERG_SUSPECT` and excluded from statistics, not deleted.

## 6. Feed register and envelope (new)

- Anchors A2 to A8 (Fields A to G), primary source. Main envelope: A2, A3, A4, A6, A7, A8 (six anchors, Field D excluded).
- kappa (median of kappa_C1 57.1, kappa_C2 247.1, kappa_C3 110.3, kappa_N2 2977.7, from 1.4826 x MAD across the six anchors) = **178.7**. With all seven anchors the same method gives 69.1.
- Nominal composition by the stated rule (closest to the anchor mean): **A4 (Field C)**. With all seven anchors it would be A8.
- Scenario set: 6 anchors (synthetic = False) plus 44 Dirichlet samples (synthetic = True, parent recorded), seed 20260101. Sensitivity sets: `kappa_x0.5` (89.3), `kappa_x2` (357.3), `fieldD` (seven anchors, kappa 69.1), `fieldE_secondary` (kappa 175.3). Files: `lng_robust/results/envelopes/`.
- The old envelope folder `lng_robust/results/study_20261120/` (secondary-source values, seven anchors) was deleted because it is superseded.

## 7. Library versions and citations

Pinned in `requirements.lock`; every results package records them in `provenance.json`. Python 3.13.

| Library | Version | Use | Citation (taken from the package's own metadata; no reference was completed from memory) |
|---|---|---|---|
| thermo | 0.6.1 | Peng-Robinson flashes, kij from the ChemSep table | Bell, C. and Contributors (2016-2024). Thermo: Chemical properties component of Chemical Engineering Design Library (ChEDL). https://github.com/CalebBell/thermo |
| chemicals, fluids | 1.5.2, 1.3.1 | constants and correlations under thermo | chemicals: Bell, C., Cortes-Pena, Y. R. and Contributors (2016-2025). https://github.com/CalebBell/chemicals. fluids: no citation text in its metadata, [AUTHOR TO VERIFY] |
| NeqSim (neqsim-python) | 3.29.0 | independent Peng-Robinson cross-check | package metadata gives only the repository https://github.com/Equinor/neqsim-python (author Even Solbraa). The reference to cite is [AUTHOR TO VERIFY] |
| scikit-learn | 1.9.1 | surrogate regression and classification | the package asks for citation via https://scikit-learn.org/stable/about.html#citing-scikit-learn. The reference text is [AUTHOR TO VERIFY] (that site was not reachable from the sandbox) |
| pymoo | 0.6.2 | NSGA-II | Blank, J. and Deb, K. (2020). pymoo: Multi-Objective Optimization in Python. IEEE Access 8, 89497-89509, doi 10.1109/ACCESS.2020.2990567 (as printed in the package README) |
| SALib | 1.6.0 | Sobol indices | Iwanaga, T., Usher, W. and Herman, J. (2022). Toward SALib 2.0. Socio-Environmental Systems Modelling 4, 18155, doi 10.18174/sesmo.18155; Herman, J. and Usher, W. (2017). SALib: An open-source Python library for sensitivity analysis. J. Open Source Software 2(9), doi 10.21105/joss.00097 (both as printed in the package README) |
| CoolProp | 8.0.0 | GERG-2008 comparison | package metadata has no citation text; [AUTHOR TO VERIFY] |
| numpy, scipy, pandas, pyarrow, matplotlib, joblib, PyYAML | 2.5.5, 1.18.1, 3.1.1, 26.0.1, 3.11.2, 1.6.0, 6.0.3 | | |

## 8. Not done, or limited, with the reason

- **Second stage**: the specified criterion (equal or lower SEC with fewer evaluations) is not met (section 2.3). The study uses the hybrid and a best-of-three search at z0.
- **Outer search budget**: population 12, 11 generations is a limited search for a 4 to 11 dimensional first-stage problem. The robust design is the best found, not a proven optimum, so the price of robustness is an upper bound on what a better search could reach. `final.json` holds the best-objective history per generation; a chain that stops before generation 10 is marked `partial` and listed under INCOMPLETE in `RESULTS_SUMMARY.md`.
- **Sensitivity protocol**: the model-parameter cases (efficiency, cooler, MITA_min) re-run the nominal NSGA-II and re-evaluate the best chance-constraint-feasible designs among the top four of the main robust archive; they do **not** re-run the outer robust search. Alpha and SEC_pen cases re-select among the archive without new evaluations. Kappa, Field D and Field E cases evaluate the main designs on the alternative scenario sets. Each result file states its protocol.
- **Surrogate**: the Gaussian process is trained on at most 1500 points per fold. Surrogate Sobol indices describe the surrogate of feasible-case SEC in a +/-15 % box around the nominal design; the rigorous one-at-a-time runs confirm or contradict the ranking (`TS_oat_confirmation.csv`).
- **Capacity**: one capacity (D1). No capacity-dependent efficiency (no sourced correlation).
- **Property models**: plain Peng-Robinson with no volume translation; NeqSim cross-check on three hand-set designs only; no DWSIM.
- **Nitrogen rejection and heavy-hydrocarbon removal duty** are not modelled (D8, D11).
- **Evaluation shards** are workflow artifacts (retention 90 days). The results branch holds the package (tables, figures, provenance, summary), not the raw shards. For archiving, `gh run download <run_id> -p 'shards-*'` then `tools/zenodo_archive.py`.
- ASSUMPTION values still in `design_basis.yaml` (authors to confirm): feed T and P, cooler outlet, dead state, pressure drops, compressor stage limit, storage pressure, minimum LNG mass fraction after end flash, SEC_pen = 2.0, variable bounds, random seed, tolerances.
- Not tested: Windows, macOS, Python versions other than 3.13.

## 9. Full study run, IDs and how to resume

{{RUN_TABLE}}

## 10. Failure handling

Failure codes: the six specified (`NONCONVERGED`, `TEMP_CROSS`, `MITA_VIOLATION`, `LIQUID_AT_SUCTION`, `PRODUCT_SPEC`, `FLASH_FAIL`) plus four added (`LIQUID_AT_EXPANDER`, `UA_EXCEEDED`, `RATED_FLOW_EXCEEDED`, `BAD_INPUT`).
Every evaluation is logged with its code; none is dropped. A pure-fluid expander exhaust inside the two-phase dome cannot be represented in the exchanger table and is coded `LIQUID_AT_EXPANDER` before the exchanger is built.
A unit whose predecessor found no feasible nominal design writes `INCOMPLETE_no_feasible_nominal_design` and exits cleanly; the package lists it.
