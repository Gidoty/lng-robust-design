# STATUS

State at the end of the first build. This file says what works, what fails, what is untested and what is still needed.
It contains no study result. Numbers below are tests, diagnostics and runtimes of the code.

## 0. CURRENT STATE (engine session 2, 2026-11-20). Where sections 1 to 12 below conflict with this section, this section is current.

Tests: **49 passed**. Branch `ccr-0a266400-jmatdr`. Phases 1 to 4 of the study plan are done. **Phases 5 to 10 are not done** (section 0.6).

### 0.1 Decisions recorded as DECIDED in `design_basis.yaml`
D1 one capacity, 100 t/d (RQ2 is composition-only); D2 iso-UA primary, UA x1.25 secondary; D3 knee of the SEC-UA front; D4 CVaR 0.9, chance
constraint 0.95, worst case as a bound; D5 S = 50; D6 surrogate screening then rigorous re-optimisation; D7 DMR and cascade excluded; D8 specification split;
D9 dual-N2 topology; D10 benchmark basis where the benchmark gives it.
D9 outcome: Austbo (2015) Fig. 5.16 (warm expander on a split stream at T_II, cold expander at T_III, exhausts merged at equal temperature) is
equivalent to the implemented parallel flow-split model. Khan et al. 2015 could not be read, so equivalence with Khan is unconfirmed.

### 0.2 Validation (files: `runs/validation_report.md`, `validation_points.csv`, `validation_rounding.csv`, `validation_summary.md`)
Acceptance: |deviation| <= 5 % on every published quantity at every point, primary equation of state Peng-Robinson (fixed before results were seen).

| Benchmark | Source | Strict verdict | Detail (PR primary) |
|---|---|---|---|
| Jensen and Skogestad 2009 PRICO Case 1 | Part I Table 2; feed composition and pressure drops from secondary sources (Jacobsen and Skogestad 2013 Table 1, Perez 2009) | **PASS** | compressor power -0.66 %, LNG flow -0.53 %. SRK cross-check +0.32 % and -0.80 %. Computed MITA 1.82 K (PR) and 1.95 K (SRK) against 1.96 K published |
| Austbo 2015 single N2 expander, PR columns (Table 5.4), 15 points | thesis pp. 111, 124 | **FAIL** (14 of 15 within 5 %) | mean absolute 1.95 %. The failing point (+21.95 %, dTmin 1.0 K, eta 0.9, pH printed as 3 bar) is input-precision limited: the printed inputs allow 1686 to 2709 kW against 1813 kW published. 13 well-resolved points: mean absolute 0.29 %, maximum 1.18 % |
| Austbo 2015 single N2 expander, SRK columns | same | **FAIL** (12 of 15) | all three failures have pressures printed as whole numbers (bands up to 2000 to 6000 kW). 11 well-resolved points: PR run mean absolute 1.29 %, maximum 1.94 %; SRK cross-check 0.24 % and 0.50 % |
| Austbo 2015 dual N2 expander (Table 5.9, SRK), 15 points | thesis pp. 137, 142 | **PASS** | PR: 15 of 15, mean -1.14 %, maximum 1.63 %. SRK cross-check: maximum 0.45 % |
| Khan et al. 2015 single and dual | paper not accessible | **INCOMPLETE** | inputs null; PDF requested from the authors |

Caveats that must travel with these numbers: (i) the Jensen feed composition and pressure drops are secondary-source and their applicability to Case 1 is not
confirmed; (ii) the SRK runs reuse PR binary parameters, so they are cross-checks, not reproductions of the source's SRK; (iii) at the published designs the computed MITA
is generally lower than the published dTmin (for example PR single expander, dTmin 5 K: computed 3.1 to 4.4 K), so most published designs are MITA-violating in this model even though
power agrees. Power depends on states, MITA on the cooling-curve shape, so property-package differences show up in MITA first. The study uses one model throughout, but the
manuscript must report this; (iv) the single-expander pH, pL printed values are rounded; the rounding-band diagnostic is in `validation_rounding.csv`.

### 0.3 Model credibility checks (Phase 3)
- Discretisation, interior pinch (`runs/mshe_convergence_smr.csv`, hand-set SMR design, pinch node 30 of 100): MITA changes 0.015 K from N = 100 to 400; UA changes 0.08 % from N = 200 to 400;
  SEC at fixed MITA changes 0.05 % from N = 100 to 200. **Study value N = 100.** The Jensen design pinches at the cold end for every flow, so it cannot test interior pinches.
- The 42.87 % PR-vs-GERG density point (`runs/phase3_density_point.csv`): CoolProp's bulk density equals the bulk computed from its own phase densities and molar quality, so it is not a convention artefact.
  PR predicts a molar vapour fraction of 0.029 where GERG-2008 gives 0.051 for the N2/C1/C2/nC4 refrigerant at -150 C and 5 bar. It is a PR phase-equilibrium difference.
- Volume translation (`runs/phase3_translation.csv`): a Peneloux-type translation changes SEC by +0.55 to +0.58 % on one hand-set design per cycle, MITA by about -0.19 K. SEC is not independent of translation. Report as model-form sensitivity.
- Independent property engine (`runs/neqsim_crosscheck_*.csv`): NeqSim Peng-Robinson plugged into the same flowsheet code. SEC differs by -0.15 % (SMR), -0.07 % (single N2), -0.05 % (dual N2); mean enthalpy difference
  1.3 kJ/kg over 20 states; UA -3.1 % on the one feasible design (NeqSim bubble-point failures skip saturation breakpoints in some exchanger tables, which may contribute). The flowsheet logic is shared, so this
  checks the property implementation, not the flowsheet formulation. DWSIM not tried.

### 0.4 Feed register (`lng_robust/data/feeds.csv`, `data/sources/SOURCES.md`)
- **A1 (Soku) is marked unverified and is not used.** Ismail and Umukoro 2012 (full text opened) has no composition table and no mention of Soku. Okwilagwe 2025 could not be opened.
- A2 to A8: seven western Niger Delta flow-station analyses (Fields A to G) from Ucheckukwu et al. 2026 (IJISRT 11(6), Table 1), a **secondary** source that cites Ebrunu and Akpoturi 2025 (primary, not opened). C5+ is lumped; the iso/normal split is an assumption.
- A9 (Sonibare and Akeredolu 2004): TODO, paper not accessible.
- Field D (A5) has 46 mol % N2 after treatment and Field G (A8) 10 %. The treated-feed spec has no nitrogen limit and no nitrogen rejection is modelled. **Author decision D11 is open** (keep, exclude A5, or add an LNG nitrogen limit). The engine keeps all seven by default.

### 0.5 Envelope (Phase 4; `lng_robust/results/study_20261120/`)
- kappa = 71.0 (median of C1 30.1, C2 98.6, C3 43.4, N2 5190, using 1.4826 x MAD across anchors; recorded in `envelope.json`). Without A5 the same method gives 186.8, so kappa depends on the Field D decision.
- Nominal composition by the stated rule (closest to the anchor mean): **A8 (Field G, about 10 mol % N2)**. The mean is pulled by Field D, so the nominal feed is nitrogen-rich. Authors should confirm this is acceptable.
- Scenario set `scenarios.csv`: 50 scenarios = 7 anchors (synthetic = False) + 43 Dirichlet samples (synthetic = True, parent anchor recorded), seed 20260101.

### 0.6 Not done, with reason
- **Phase 5 to 9** (feasibility-guided surrogate data with Wilson intervals, study-scale CVaR and worst-case runs, ranking-reversal maps, Sobol and one-at-a-time sensitivity, 600 dpi figures and results package): the code for the surrogate-assisted second stage, active learning,
  Parquet logging, checkpoint and resume, ranking reversal and figures is **not written**, and no study-scale run exists. No result number exists for the manuscript's Sections 3.3 to 3.8.
- **Phase 10** (LICENSE, CITATION.cff, Zenodo script): not done.
- Wall-time estimate for the planned run (`runs/budget_estimate.csv`, plan parameters in `analysis/budget_estimate.py`): about **22 hours on 4 workers** (SMR 10.6 h, single N2 5.3 h, dual N2 5.9 h; 416,000 rigorous evaluations),
  with outer GA population 8 for 8 generations, S = 50, 12 rigorous evaluations per scenario, three robust variants. This is under the 48 h stop limit but needs a machine that stays up that long, and the second-stage inner solve is still to be built. It is an estimate.
- Documents still needed from the authors are in `manuscript/REQUESTS_TO_ENGINE.md`.

---

The sections below were written at the end of the first build and are partly superseded.

## 1. Summary

| Item | State |
|---|---|
| Test suite | **40 passed, 0 failed** (`python -m pytest -q`, about 12 s) |
| Property layer (Peng-Robinson, flashes, GERG-2008 comparison) | works; PR deviations from GERG-2008 are large in the liquid region (section 4) |
| Heat-exchanger model and discretisation study | works; the study case pinches at the cold end, so it does not test interior-pinch convergence (section 4) |
| Three cycle models | run, close mass, energy and exergy balances; **not benchmark-validated** |
| Benchmark validation | **all three benchmarks INCOMPLETE** (inputs are null by rule); no deviation exists yet |
| Nominal NSGA-II, two-stage CVaR, surrogates, FFR, screening | run end to end in `--quick` (smoke test only) |
| Sobol analysis | implemented and tested on the Ishigami function; **not run on the cycle models** |
| `--full` mode | **not run; the default budget is not feasible on this machine** (section 7) |
| Feed register | 1 anchor (A1, secondary source). A2 onward are TODO for the authors |

The smoke-test run folder is `lng_robust/runs/20261119T224509Z_quick_SMOKE/`. It is git-ignored, labelled
`SMOKE TEST - NOT A RESULT`, and its numbers are not findings. Its `config.json` records git hash `d2f468c`,
which is the parent commit. The code was uncommitted when the run started, so that hash does not identify the exact code.
Re-run the smoke test after committing if exact provenance matters.

## 2. Tests

40 tests in `lng_robust/tests/`, all passing:

- properties: pure-methane density vs CoolProp, mass closure of every flash, PH/PS round trips, kij table completeness, bubble/dew ordering
- heat exchanger: balanced and unbalanced counterflow against analytic UA, temperature-cross detection, multi-stream energy balance
- units: compressor and expander against CoolProp and exact PR mechanics, valve enthalpy, efficiency scaling
- cycles: exergy balance closure below 1e-6, tear convergence, scale invariance of SEC, failure codes for UA, rated flow, spec, bad input
- pretreatment, feed register, Dirichlet sampling (labels, reproducibility, mean)
- CVaR against brute-force minimisation, price-of-robustness formula, knee point, FFR, grouped CV leakage check, Sobol on Ishigami
- validation harness: repository benchmarks stay INCOMPLETE; a test fixture (labelled, not a benchmark) exercises the PASS/FAIL logic

Two test expectations were corrected during the build, both because the test was wrong and not the code:
the Dirichlet mean must be compared with the renormalised anchor (94.05 % C1, not the raw 92.51 %), and the
dense-gas expander test used a 2 % tolerance that plain PR exceeds at 40 bar (section 4).

Warnings seen: scikit-learn Gaussian-process `ConvergenceWarning` (length scale at its lower bound) in a test and in the smoke run.

## 3. Deliverables

| Deliverable | File | State |
|---|---|---|
| GERG check | `lng_robust/runs/gerg_check.csv`, `gerg_check_summary.csv` | written, 216 states |
| Methane density map | `lng_robust/runs/methane_density_map.csv` | written |
| Heat-exchanger convergence | `lng_robust/runs/mshe_convergence.csv` | written |
| Validation report | `lng_robust/runs/validation_report.md` | written, all INCOMPLETE |
| Cycle timing | `lng_robust/runs/cycle_timing.csv` | written |
| Smoke run | `lng_robust/runs/20261119T224509Z_quick_SMOKE/` | complete, 27.3 min |
| README | `README.md` | written |
| kij table | `lng_robust/data/kij_table.csv` | 45 pairs, 8 are zero in the databank and flagged |

## 4. What fails or deviates

**PR against GERG-2008** (`gerg_check_summary.csv`; 215 usable states, 1 state flagged `GERG_SUSPECT`):

| Region | n | Mean abs density dev | Max abs density dev |
|---|---|---|---|
| vapour / gas-like | 54 | 0.87 % | 3.65 % |
| two-phase | 85 | 4.43 % | 42.87 % (MR test composition) |
| liquid / dense | 76 | 9.45 % | 12.31 % |
| all | 215 | 5.31 % | 42.87 % |

Enthalpy difference from a reference state: mean absolute deviation 2.10 kJ/kg, maximum 25.18 kJ/kg. Plain PR (no volume
translation) over-predicts liquid density by about 12 %, as shown for pure methane in `methane_density_map.csv`. SEC is built
from enthalpy and entropy, not liquid density, but the manuscript must report this and discuss the effect.
The 42.87 % two-phase maximum is one point on the refrigerant-like composition; check whether it is a PR error or a CoolProp
bulk-density convention for two-phase mixtures before quoting it.

**CoolProp wrong-branch result.** For `TEST_A1LIKE_synthetic` at -130 C and 20 bar, CoolProp returned a gas root with an
enthalpy 13,570 kJ/kg away from PR, without raising an error. The check in `gerg_check.py` flags a point when GERG enthalpy or
density breaks monotonic order along an isobar. The point stays in the CSV with status `GERG_SUSPECT` and is excluded from the
summary. This flags a library fault; it does not remove a case silently.

**Pure-methane 2 % density test** passes only on a gas-phase domain (P at most 10 bar, or T at least 60 C). PR exceeds 2 %
for dense gas (about 2 to 5 % at 20 to 60 bar and -100 to 0 C) and by about 12 % in the liquid. The failing region is
in `methane_density_map.csv`, not hidden.

**Dense-gas isentropic work.** For N2 at 200 K and 40 bar, PR's isentropic expansion work differs from CoolProp by about
2.1 %. That is an equation-of-state effect. The unit mechanics are tested exactly against PR.

**Heat-exchanger convergence.** On the N2-dual reference design, UA changes by 0.003 % from N = 100 to N = 200 and by -1.34 %
from N = 10 to N = 100. Table resolution (12 to 192 points) changes UA by at most 0.08 %. MITA is identical in every row because
this design pinches at the cold end (node 0), which does not depend on N. The manuscript needs the same study on a design
with an interior pinch, typically an SMR design. TODO.

**Exergy accounting.** The exergy balance closes to about 1e-8 of shaft power once the composition-change term X of the
end-flash split is included. Each product stream is referenced to its own composition at the dead state, so X is a real
term, reported in `details` as `X_endflash_composition_kw`. The manuscript's Eq. 5 uses specific exergies and does not show X.

## 5. Failure handling

Failure codes: the six specified (`NONCONVERGED`, `TEMP_CROSS`, `MITA_VIOLATION`, `LIQUID_AT_SUCTION`, `PRODUCT_SPEC`,
`FLASH_FAIL`) plus four added: `LIQUID_AT_EXPANDER`, `UA_EXCEEDED`, `RATED_FLOW_EXCEEDED`, `BAD_INPUT`.

In the smoke run, 11,094 rigorous evaluations were logged and none were dropped. Status counts: 2,098 feasible, 8,996
converged but infeasible, 0 not converged. There was no `FLASH_FAIL` and no `NONCONVERGED`. All infeasibility was physical.

A pure-fluid expander exhaust inside the two-phase dome cannot be represented in the heat-exchanger table (no (T, P) state).
Such cases are coded `LIQUID_AT_EXPANDER` before the exchanger is built. Before this rule they produced spurious
`NONCONVERGED` codes from a duty mismatch, which was a code limitation. Only `max_expander_liquid_mass_frac = 0` is supported.

## 6. Runtime per rigorous cycle evaluation (one process, `cycle_timing.csv`, median of 5)

| Cycle | Default (N = 100, table 48) | Quick (N = 40, table 24) | Flashes per evaluation (default) |
|---|---|---|---|
| SMR | 0.94 s | 0.66 s | 177 |
| Single N2 expander | 0.47 s | 0.33 s | 175 |
| Dual N2 expander | 0.52 s | 0.36 s | 277 |

Cost is dominated by thermo's Michelsen stability test inside property-table flashes (about 5 ms per flash).

## 7. Compute budget: the `--full` preset is not feasible as written

The smoke run took 27.3 min on 4 cores with S = 20 scenarios, outer population 4 for 2 generations, inner budget 16.
The `full` preset (S = 200, outer population 24 for 30 generations, inner budget 40) implies about 720 outer evaluations
of 8,000 second-stage evaluations, which is 5.8 million rigorous evaluations per cycle and capacity. At 0.5 s that is about
800 core-hours, or about 200 hours on 4 cores, for each of 9 cycle-capacity combinations. This is a rough estimate.
Options, to decide before running it:

1. fewer scenarios (S = 50) and a smaller outer search, which is about 8 hours per combination on 4 cores
2. surrogate-assisted second stages (the paper's own plan), with every reported optimum re-verified in the rigorous model
3. a larger machine or a cluster
4. a compiled or vectorised property kernel (large engineering task)

`--full` now prints this warning. Logging every inner evaluation, as rule 5 requires, produces millions of rows at that scale.
CSV will not be adequate; switch to a columnar format.

## 8. Pipeline observations from the smoke run (code behaviour, not study results)

- **The surrogate dataset is data-starved.** Of 200 Latin-hypercube cases per cycle, only 7 (SMR), 17 (single N2) and
  17 (dual N2) were feasible. Regression models trained on 7 to 17 points are not meaningful, and the screening step
  proposed designs that the rigorous model rejected (SMR 5 of 5, single N2 3 of 5, dual N2 2 of 5). Before any
  surrogate result is reported, the design of experiments needs feasibility-guided sampling (sample around the nominal design,
  active learning near the constraint boundary, or a larger set).
- The nominal search found a feasible design in all three cycles only because the initial population is the best of a
  3x random screen. Random sampling alone finds feasible designs in about 2 to 15 % of cases (2 to 3 % in the initial screen, 3.5 to 8.5 % in the DOE, up to 15 % in an earlier 60-case probe).
- The robust stage returned designs with feasible fraction 1.0 for all three cycles at this budget. The inner second-stage
  search is a short Nelder-Mead (16 evaluations), so that says little. Do not read it as a property of the cycles.
- UA exceeded installed UA in 2,212 (dual N2), 2,260 (single N2) and 740 (SMR) logged evaluations, which is the main way a
  fixed-equipment design fails across scenarios. `LIQUID_AT_SUCTION` was 2,009 of the SMR evaluations.

## 9. Inputs still needed from the benchmark papers

All fields below are `null` in `lng_robust/data/benchmarks.yaml`. None was guessed. Each benchmark also requires
`product_basis` to be `after_end_flash` (the only product basis the code supports); a paper that defines SEC on another basis
needs new code.

**Khan et al. 2015, single N2 expander** (published SEC 0.7449 kWh/kg is entered): `feed_composition`, `feed_flow_kg_s`,
`product_basis`, `lng_storage_pressure_bar`, `T_lng_C`, `P_high_bar`, `P_low_bar`, `n2_flow_kg_s`, `T_exp_in_C`, `T_cool_C`,
`compressor_pr_max_per_stage`, `dp_mshe_hp_bar`, `dp_mshe_lp_bar`, `dp_cooler_bar`, `dp_intercooler_bar`.

**Khan et al. 2015, dual N2 expander** (published SEC 0.5007 kWh/kg is entered): the same list, with `T_exp_in_warm_C`,
`T_exp_in_cold_C` and `split` in place of `T_exp_in_C`. Also confirm the flowsheet topology. The code implements a warm and a
cold expander in parallel with a flow split; Khan's dual-expander arrangement may differ (for example series expansion with an
intermediate pressure).

**Jensen and Skogestad 2009, PRICO** (power 77.5 MW, LNG 44.6 kg/s, 22 and 4.0 bar, refrigerant composition, efficiency 0.828
are entered): `feed_T_C`, `feed_P_bar`, `feed_composition`, `feed_flow_kg_s`, `product_basis`, `lng_storage_pressure_bar`,
`T_lng_C`, `refrigerant_flow_kg_s`, `T_cool_C`, `compressor_pr_max_per_stage`, `dp_mshe_hp_bar`, `dp_mshe_lp_bar`,
`dp_cooler_bar`, `dp_intercooler_bar`. The original used SRK. A PR deviation is expected and must be reported as such.
Also check whether the paper's compressor power is shaft power and whether the LNG flow is an output or an input.

If the original paper states that a pressure drop is zero, enter an explicit `0`, with a note. A null is not zero.

## 10. Decisions and inputs the authors must confirm

Every item below is an ASSUMPTION or TODO in `design_basis.yaml`. None is sourced.

- treated-feed temperature and pressure (30 C, 50 bar), cooler outlet temperature (35 C), dead state (30 C, 1.01325 bar)
- pressure drops, compressor stage limit (pressure ratio 4), LNG storage pressure (1.2 bar), minimum LNG mass fraction after end flash (0.5)
- the C4 and C5 isomer splits (0.5 each), because the A1 source reports totals only
- renormalisation of A1, which sums to 98.36 % (the 1.64 % unassigned is renormalised away for simulation only)
- Dirichlet concentration kappa. It is 200 as a placeholder. With fewer than two anchors it cannot be derived from the anchor range
- decision-variable bounds (manuscript Table 2 asks for them)
- infeasibility penalty `SEC_pen` (2.0 kWh/kg)
- **capacity-dependent efficiency**: manuscript Section 2.1 needs a sourced correlation. Not implemented; efficiencies are constant at 0.75,
  so SEC is scale-invariant and the three capacity points differ only in UA. Without the correlation, the capacity dimension of RQ2 is empty
- capacity points (20, 100, 300 t/d) and the flare-site mapping
- **price-of-robustness definition**: the robust design may install at most `ua_budget_factor` times the nominal design's UA
  (default 1.0, an iso-exchanger comparison). The manuscript does not say. Decide this before looking at results
- nominal design selection rule: the knee of the SEC-UA front (min-max normalised distance to the utopia point)
- heavy-hydrocarbon removal: `pretreat.py` is a component split with no duty (manuscript: scrub column or cold flash, author decision)
- dual mixed refrigerant: recommended as a stated limitation, not a case. Nothing in the code needs it
- Binary interaction parameters come from the `thermo` ChemSep PR table. Eight hydrocarbon pairs are zero in that databank (flagged).
  The manuscript says no pair is set to zero without a stated reason; the reason here is "zero in the databank"

## 11. Untested or not done

- `--full` mode, at any scale
- two-stage design at S above 20, or with an inner budget above 16 evaluations
- the worst-case design (`risk="worst"`): implemented, never run
- Sobol analysis on the cycle models; surrogate-based Sobol
- an independent-simulator comparison (NeqSim or DWSIM), which the manuscript promises
- the interior-pinch discretisation study
- more than one anchor, anchor-grouped cross-validation (the code path exists; quick mode groups by individual composition)
- ranking-reversal maps (RQ2): no code yet. It needs more than one capacity and a composition partition
- surrogate FFR confidence intervals: the counts near the limit were 2 to 9 cases, too few to report a rate
- convergence of SEC (not only UA and MITA) when N changes, which needs a re-optimisation at each N
- Peneloux volume translation, or a check that SEC is insensitive to it
- the sensitivity runs listed in manuscript Section 2.11 (efficiency, ambient temperature, MITA limit, alpha, kappa)
- Windows, macOS, other Python versions. Built and tested on Python 3.13, Linux

## 12. Related files

- `NOVELTY_NOTES.md`: prior-work leads, including Tsay, Pattison and Baldea (2018), which the manuscript draft does not cite
- `FEED_LEADS.md`: unverified leads for the missing compositions
- `README.md`: run commands and layout
