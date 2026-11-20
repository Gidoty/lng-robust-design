# Requests from the manuscript session to the engine session

Add one entry per request: date, what is needed, which manuscript section needs it. The engine session clears entries it has done and lists them under "Cleared".

## Open (engine session to the authors, 2026-11-20)

- AUTHORS: PDF of Tsay and Baldea (2018), Ind. Eng. Chem. Res. 57(17), 5868-5880 (paywalled), to state the difference from this study exactly (Section 1).
- AUTHORS: reference texts for NeqSim, scikit-learn and CoolProp (and `fluids`). The packages' own metadata does not give them and none was completed from memory. See STATUS section 7.
- AUTHORS: decide which interval is printed beside Eq. 8. Eq. 8 is a single number at z0 and has no bootstrap interval over scenarios. The tables report `PoR_z0`, the scenario-mean relative difference with a bootstrap 95 % interval, the change in CVaR and the change in feasible fraction (HANDOFF item 2).
- AUTHORS: Sections 2.10 and 2.11 describe the second stage as surrogate screening with rigorous re-optimisation, and the sensitivity runs as one-at-a-time runs. The engine does something narrower in both places (HANDOFF items 1 and 4). Please word the text to match.
- MANUSCRIPT SESSION: the Table 4 draft values already equal `feeds.csv`; Table 3 and the discretisation text use the CSV values (checked).

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
