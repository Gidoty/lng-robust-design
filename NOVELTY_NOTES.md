# Novelty and reviewer-risk notes (for the authors; written during the build, not used by the code)

Status: **leads only**. Each item below was found by a quick search and has NOT been read in full or verified against the
original. Confirm every claim and reference before it goes into the manuscript.

## Closest prior work that the manuscript draft does not cite

1. **Tsay, Pattison and Baldea (2018), "Scenario-Free Optimal Design under Uncertainty of the PRICO Natural Gas
   Liquefaction Process", Industrial & Engineering Chemistry Research.** The abstract states that PRICO is optimised with
   varying feed composition and that equipment size is optimised together with operating conditions. This is the nearest
   neighbour to the paper's "design for feed variability with equipment fixed and operation retuned" idea for the SMR cycle.
   A reviewer who knows it will ask how this study differs. The manuscript must cite it and state the difference
   (tail-risk CVaR objective instead of a scenario-free worst-case formulation; three cycles including nitrogen expanders;
   documented Niger Delta composition envelope; surrogate reliability). Check the exact formulation before claiming a difference.
2. **Mortazavi (2012 thesis) and Mortazavi et al. (2016, Energy 113, 1042-1050).** Already cited in the draft. Robust
   refrigerant for a propane-precooled cycle; gradient-assisted robust optimisation, not CVaR.
3. **Wahid Ali et al. (2023), Thermal Science and Engineering Progress**, HFO-based SMR for floating LNG with uncertainty
   analysis on inlet conditions. Different cycle and no tail-risk design, but it is an "uncertainty in SMR" paper.
4. **Uncertainty quantification for DMR (Applied Energy 250, 2019, 1446-1456)**, Monte Carlo and sensitivity analysis. Context for the Sobol section.

## Search results on the specific combination (as of this build, limited searches)

- No paper was found that combines CVaR (or any tail-risk measure) with LNG refrigeration cycle design. A CVaR-constrained
  process-design thesis exists for non-LNG plants (a Bogazici University thesis). Searches were few and shallow. The draft
  already says a systematic Scopus search is required immediately before submission; that stays mandatory.
- No Niger Delta associated-gas liquefaction cycle study was found in these searches.
- Scite MCP search was not available (paid plan), so the Scite-based check of claims and references was NOT run.

## Update 2026-11-19 (engine session)

Tsay, Pattison and Baldea (2018) could not be opened (paywalled). Its formulation (objective, what is fixed, how composition
varies, which cycles) is still unrecorded. Request filed in `manuscript/REQUESTS_TO_ENGINE.md`. Until it is read, do not claim a
specific difference from it in the manuscript.

## What makes the paper defensible (design decisions the code supports)

- Report the price of robustness even if it is small. A null result with a sound method is publishable; an overstated one is not.
- Keep anchors (published) and synthetic scenarios separate in every table (the code labels both).
- State that the Dirichlet envelope is a modelling choice and show sensitivity to kappa.
- Report the surrogate false-feasible rate near the MITA limit with its sample size. Small counts need confidence intervals.
- Use an iso-UA comparison (`ua_budget_factor = 1.0`) as the primary PoR definition, and show the UA-growth variant separately. Decide this before looking at results.

## Possible reviewer objections to prepare for

| Objection | Where the code or paper answers it |
|---|---|
| Too few real compositions | register grading, anchor-vs-synthetic reporting, kappa sensitivity |
| PR is not accurate for LNG density | GERG-2008 comparison; SEC depends on enthalpy and entropy, not liquid density; report both deviations |
| Capacity effect is not modelled | efficiency-vs-capacity correlation is an open TODO in `design_basis.yaml`; needed before three capacities mean anything |
| No economics | stated limitation; UA and machine count as indicators |
| Pure steady state | stated limitation |
| Benchmarks are only partly reproducible | validate.py reports deviations honestly; Jensen uses SRK |
