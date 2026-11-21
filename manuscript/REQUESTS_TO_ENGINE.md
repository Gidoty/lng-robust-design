# Requests from the manuscript session to the engine session

Add one entry per request: date, what is needed, which manuscript section needs it. The engine session clears entries it has done and lists them under "Cleared".

## Open (engine session to the authors, 2026-11-20)

- AUTHORS: PDF of Tsay and Baldea (2018), Ind. Eng. Chem. Res. 57(17), 5868-5880 (paywalled), to state the difference from this study exactly (Section 1).
- AUTHORS: reference texts for NeqSim, scikit-learn and CoolProp (and `fluids`). The packages' own metadata does not give them and none was completed from memory. See STATUS section 7.
- AUTHORS: decide which interval is printed beside Eq. 8. Eq. 8 is a single number at z0 and has no bootstrap interval over scenarios. The tables report `PoR_z0`, the scenario-mean relative difference with a bootstrap 95 % interval, the change in CVaR and the change in feasible fraction (HANDOFF item 2).
- AUTHORS: Sections 2.10 and 2.11 describe the second stage as surrogate screening with rigorous re-optimisation, and the sensitivity runs as one-at-a-time runs. The engine does something narrower in both places (HANDOFF items 1 and 4). Please word the text to match.
- MANUSCRIPT SESSION: the Table 4 draft values already equal `feeds.csv`; Table 3 and the discretisation text use the CSV values (checked).

## Open (manuscript session to the engine, 2026-11-21, after full run 44682889025)

The package of run 44682889025 has internal contradictions. The manuscript cannot report Sections 3.4 to 3.6 from it until they are resolved. Requests 12 and 13 are blockers.

**Cleared by the engine on 2026-11-21: requests 12 to 19, package `results/44906558014` (run 44906558014). See STATUS section 9 and the HANDOFF update for the facts the authors must read (nominal still below the chance constraint; negative iso-UA PoR is larger than the z0 search spread).**

12. **BLOCKER: nominal N2 designs reported infeasible at their own design composition.** T6: `n2_dual` nominal feasible fraction 0.00, anchors 0/6, although its design composition is A4, T5 gives a feasible design at A4 (MITA 10.37 K) and T6 itself gives SEC_z0 0.7248 kWh/kg with MITA_z0 11.21 K. `n2_single` nominal: anchors 1/6. A design that is feasible at A4 by construction cannot be infeasible at A4 in `across`. Diagnose with the failure codes per scenario (rated flow, solver, warm start, renormalisation of A4, or a different feasibility rule in `across`). Required fix: every second-stage solve starts from (and keeps as a candidate) the design's own operating point and the best known feasible point for that scenario, so a known feasible point can never be reported infeasible. Add a test: each nominal design evaluated by `across` at its own anchor is feasible. Re-run `across`, `reversal` and the sensitivity units.
13. **BLOCKER: the SMR CVaR design is not the best CVaR design found.** T6 `smr`: `worst_iso` has CVaR 0.4835 kWh/kg, lower than `cvar_iso` at 0.5047, with the same UA budget; both chains ended `partial` at stage 5. The reported CVaR design must be the best CVaR design among all iso-UA designs evaluated rigorously in the run (union of the cvar_iso, worst_iso and nominal archives, each re-evaluated on the same 50 scenarios with the same second-stage budget). Apply the same rule to the worst-case and cvar_125 variants and to the N2 cycles. Do NOT extend the chains (authors' decision 2026-11-21, to save time): select from the existing archives and report the per-generation history so the text can state that the design is the best found within the budget.
14. **Failure-code table.** For every design in T6, the count of each failure code over the 50 scenarios, anchors and synthetic separately (new table `TS_failure_codes.csv`). The manuscript needs it to explain why the iso-UA N2 designs miss the chance constraint (0.84 and 0.76): whether it is MITA, rated flow, liquid at the expander outlet, or a solver failure.
15. **Per-scenario results in the package.** The manuscript session cannot download workflow artifacts (blocked host). Add `TS_across_per_scenario.csv` (cycle, design, scenario id, anchor or synthetic, SEC, MITA, UA, feasible, failure code, number of evaluations) to `tables/`.
16. **Convergence history.** Best objective per generation for every robust chain, as a table and a supplementary figure.
17. **PoR intervals.** After 12, `PoR_scenario_mean` and its interval must exist for `n2_dual` (currently NaN because the nominal design had no feasible scenario).
18. **Negative PoR at iso-UA.** `n2_single` cvar_iso PoR_z0 is -0.25 %: the robust design gives lower SEC at z0 than the nominal design at the same UA. Report whether this lies within the z0 search tolerance (spread of the best-of-three z0 searches, already in `sec_z0_candidates.json`) and add that spread to T6.
19. After 12 to 18, re-run ONLY the downstream units (`across`, `reversal`, `sens_*`, `package`) in a new workflow run that downloads the nominal, sample, surrogate, sobol and robust outputs of run 44682889025 instead of recomputing them. No new robust search. Update HANDOFF with what changed. Keep run 44682889025 as is.

## Answers to the engine's open items to the authors (2026-11-21)

- Eq. 8 interval: the manuscript reports PoR_z0 without an interval, and beside it the scenario-mean difference, the change in CVaR and the change in feasible fraction, each with its bootstrap 95 % interval (manuscript Section 2.9 already says this).
- Sections 2.10 and 2.11 were reworded on 2026-11-20 to match HANDOFF items 1 and 4 (surrogate only chooses cold-start and restart points; sensitivity protocol as run).
- References checked by the manuscript session: scikit-learn = Pedregosa et al. 2011, J. Mach. Learn. Res. 12(85), 2825-2830 (jmlr.org); CoolProp = Bell et al. 2014, Ind. Eng. Chem. Res. 53(6), 2498-2508, doi 10.1021/ie4033999 (coolprop.org); NeqSim cited as software (Equinor, github.com/equinor/neqsim, version 3.29.0). Tsay and Baldea PDF: still with the authors.

## Cleared by the engine on 2026-11-20 (see STATUS section 1)

1. D11 option (b): Field D outside the main envelope, sensitivity case, kappa and nominal anchor recomputed (kappa 178.7, nominal A4), LNG N2 content in every design table.
2. Primary Ebrunu and Akpoturi (2025) values transcribed from the PDF with page and table, isomers as printed, C6 and heavier lumped as C6+ (n-hexane).
3. A1 (Soku) dropped; A9 dropped as well.
4. Khan basis notes replaced; Khan benchmark entries left INCOMPLETE and unused.
5. Tsay and Baldea (2018) citation corrected in `NOVELTY_NOTES.md`.
6. Discretisation statement in STATUS corrected from `mshe_convergence_smr.csv`.
7. LNG N2 content and library versions provided (STATUS section 7).
8. D1 to D11 recorded as decided by the authors.
9. Printed component sums, renormalisation and the Field E secondary-value sensitivity row (`A6S`).
10. Phases 5 to 10 moved to GitHub Actions: `.github/workflows/study.yml`; run IDs in STATUS section 9.
11. Versions of thermo, NeqSim, scikit-learn, pymoo, SALib and others in STATUS section 7 and in each `provenance.json`.
