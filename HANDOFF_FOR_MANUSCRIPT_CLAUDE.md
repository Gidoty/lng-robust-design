# Briefing for the Claude that writes the manuscript

Paste this whole file at the start of the manuscript session. Update it whenever the engine session changes something.

## UPDATE 2026-11-20 (read `STATUS.md` section 0 first)

What you may now describe, with the file as the source: benchmark validation against Jensen and Skogestad (2009) and Austbo (2015) with the caveats in STATUS 0.2, the discretisation study (N = 100), the PR-GERG
comparison including the vapour-fraction explanation of the 42.87 % point, the volume-translation sensitivity (+0.55 to +0.58 % SEC), the NeqSim property cross-check, the feed register (seven secondary-source flow-station anchors; A1 unverified, not used),
and the scenario method (kappa 71.0, nominal A8, S = 50 with 7 anchors and 43 synthetic). Still NOT available: any Section 3.3 to 3.8 result (nominal and robust designs, price of robustness, ranking reversal, surrogate false-feasible rate,
sensitivity) and the Khan et al. benchmark. Do not write "validated against Khan et al." The manuscript draft's Table 4 A1 row should be removed or marked unverified. Open author decisions: D11 (nitrogen-rich anchors), nominal composition A8.

## Project

Manuscript: "The price of robustness in modular LNG refrigeration: risk-averse design of single mixed refrigerant and nitrogen expander cycles for variable Niger Delta associated gas". Authors: Tunji Fadoyeni, Gideon Owhonda. Target: Gas Science and Engineering (Elsevier). Goal: a paper that passes review and is published.

A separate Claude session built the computational engine. You write the paper from what the engine produces.

## Where the work is

- Repository: https://github.com/Gidoty/scholarship_application_intelligence_system
- Branch: `ccr-0a266400-jmatdr`, folder `lng-robust-design/` (independent of the rest of the repository)
- Read first: `STATUS.md` (state, failures, open items), `README.md` (commands), `NOVELTY_NOTES.md`, `FEED_LEADS.md`
- Inputs and basis: `lng_robust/data/design_basis.yaml` (every value is GIVEN, ASSUMPTION or TODO), `benchmarks.yaml`, `feeds.csv`, `kij_table.csv`
- Result files: `lng_robust/runs/` (`gerg_check*.csv`, `mshe_convergence.csv`, `validation_report.md`, `cycle_timing.csv`, `methane_density_map.csv`) and one subfolder per pipeline run

If you cannot read the repository, ask the author to paste the file you need. Do not reconstruct numbers from memory.

## Rules you must follow when writing

1. Every number in the paper must come from a file produced by the engine. Cite the file in your working notes. If no file has the number, write `[AUTHOR TO PROVIDE]`.
2. No result exists yet. The folder `runs/20261119T224509Z_quick_SMOKE/` is a smoke test labelled "SMOKE TEST - NOT A RESULT". Never quote, summarise or round numbers from it.
3. Do not state or imply an outcome before the data exist: not a ranking reversal, not a price-of-robustness size, not a surrogate failure rate. The abstract template in the manuscript has blanks for these. Leave them blank.
4. A null or negligible result is publishable if the method is sound. Write it plainly if that is what the data show.
5. Label anchors (published) and synthetic scenarios separately in text, tables and figures.
6. Do not add references you have not checked. Several draft references are marked `[AUTHOR TO VERIFY]`. Do not complete author lists, titles or DOIs from memory.
7. Follow the author's style: clear direct language, active voice, British English, no em dashes, no filler openers, no metaphors or analogies, concrete numbers when they exist.

## What exists and is verified (you may describe the method, with the file as the source)

- Property model: Peng-Robinson via the `thermo` library, kij from the ChemSep PR table (8 hydrocarbon pairs are zero in that databank). Compared with GERG-2008 (CoolProp) at 216 states. Mean absolute density deviation 0.87 % in gas, 9.45 % in liquid, 5.31 % overall. Plain PR over-predicts liquid density by about 12 %. SEC uses enthalpy and entropy, not liquid density. Source: `gerg_check_summary.csv`, `methane_density_map.csv`.
- One CoolProp point returned a wrong branch without error. It is flagged `GERG_SUSPECT` and excluded from statistics, not deleted.
- Heat exchanger: equal-duty discretised multi-stream model. On the reference N2-dual design UA changes 0.003 % from N = 100 to 200. That case pinches at the cold end, so it does not test interior pinches. Source: `mshe_convergence.csv`.
- Cycles: SMR (PRICO type), single N2 expander, dual N2 expander (parallel expanders with a flow split; topology not yet confirmed against Khan et al. 2015). Mass, energy and exergy balances close. Exergy closure needs a composition-change term for the end-flash split.
- Failure handling: six specified failure codes plus four added. Every evaluation is logged with its code. Source: `STATUS.md` section 5.
- Two-stage CVaR formulation (CVaR at 0.9, chance constraint 0.95, equipment fixed, operation re-optimised per scenario), NSGA-II nominal design, price of robustness, grouped leave-one-composition-out surrogates, false-feasible rate, Sobol analysis (code tested, not run on the cycles).
- Tests: 40 pass.

## What is not done (do not write it as done)

- **Benchmark validation: none.** All three benchmarks are INCOMPLETE because inputs are null. Missing fields are listed in `STATUS.md` section 9. The paper cannot claim "validated against published benchmarks" until `validation_report.md` shows PASS or reports deviations.
- Only one real composition (A1, secondary source, sums to 98.36 %, C4/C5 isomer split assumed). Rows A2 onward are TODO.
- No capacity-dependent efficiency, so SEC is scale-invariant and the capacity dimension of RQ2 is empty.
- The study-scale run (`--full`) has not been run. The default budget is not feasible on the build machine (see `STATUS.md` section 7).
- Surrogate training data are too thin (7 to 17 feasible cases of 200). No surrogate result is reportable.
- No ranking-reversal code, no independent-simulator comparison, no sensitivity runs, no interior-pinch convergence study.

## Writing plan that the current state supports

| Manuscript section | What you can write now | What waits for data |
|---|---|---|
| 1 Introduction | Background, gap, objectives. Add Tsay, Pattison and Baldea (2018, Ind. Eng. Chem. Res.), which the draft omits: it optimised PRICO under varying feed composition with equipment sizing. State the difference only after the author checks its exact formulation | Final novelty statement needs the author's Scopus search |
| 2.1 to 2.6 Methods | Describe the implemented models and equations. Replace each `[AUTHOR TO PROVIDE]` that the engine now answers (solver tolerances, N, table points) with the value and its source file | Capacity points, efficiency correlation, benchmark inputs |
| 2.7 Composition envelope | Method, grading, anchor/synthetic separation | Table 4 values, kappa |
| 2.9 to 2.11 | Formulation as implemented | Budgets, thresholds |
| 3 Results | Nothing yet except the property comparison and discretisation study (Section 3.1 parts) | Everything else |
| 3.9 Limitations | Expand using `STATUS.md` sections 4, 10, 11 | |
| 4 Conclusions | Nothing | After results |

## Decisions the author must confirm (ask, do not decide)

Price-of-robustness definition (iso-UA budget factor 1.0 is the engine default), nominal design rule (knee of the SEC-UA front), dual-N2 topology, dual mixed refrigerant as a limitation, heavy-hydrocarbon removal method, feed T and P, cooler outlet temperature, pressure drops, bounds, SEC penalty, capacity points and flare-site mapping. The full list is `STATUS.md` section 10.

## What the engine session will do next

1. Fill benchmark inputs once the author supplies them, then run `validate.py` and report PASS, FAIL or deviation.
2. Add real compositions to `feeds.csv` after the author or the engine session reads the primary sources.
3. Replace the surrogate design of experiments with feasibility-guided sampling.
4. Add the capacity-dependent efficiency (needs a source), capacity runs, ranking-reversal maps, sensitivity runs, an interior-pinch convergence study and an independent-simulator comparison.
5. Choose a feasible study-scale budget, run it, and write tables and figures with provenance (config, git hash, seed).
6. Update this file and `STATUS.md` at each step. Re-read them before you write any section.

When the engine session produces results, ask the author for the run folder name and read its `config.json`, `design_summary.csv`, `evaluations.csv` and `failure_code_counts.csv` before writing a number.
