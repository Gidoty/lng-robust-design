"""Wall-time estimate for the study-scale plan (Phase 6), from the measured per-evaluation times in runs/cycle_timing.csv.
Every plan parameter is an explicit argument. Writes runs/budget_estimate.csv. It estimates; it does not run anything."""
from __future__ import annotations

import pandas as pd

from lng_robust.config import RUNS_DIR

PLAN = dict(
    workers=4, parallel_efficiency=0.85,
    nominal_pop=40, nominal_gen=40, screen_factor=3,
    doe_cap_evals=8000,                 # active-learning cap per cycle (Phase 5)
    S=50, inner_rigorous_evals=12,      # D5, D6: surrogate screen, then 12 rigorous evaluations per scenario
    outer_pop=8, outer_gen=8,           # outer GA budget (reduced to fit 24 h; see STATUS.md)
    variants=3,                         # CVaR iso-UA, CVaR UA x1.25, worst-case bound
    across_scenario_runs=6,             # nominal design across scenarios, S convergence (25, 50, 100), kappa 0.5x and 2x
    oat_designs_per_cycle=14,           # efficiency x3, cooler +-5 K, MITA x3, alpha x3 (re-opt), SEC_pen x3 (re-eval) - counted as design x scenario sets
)


def estimate(plan=PLAN):
    t = pd.read_csv(RUNS_DIR / "cycle_timing.csv")
    t = t[t.resolution.str.startswith("default")].set_index("cycle").median_s
    rows = []
    for cyc, sec in t.items():
        nominal = plan["nominal_pop"] * plan["nominal_gen"] + plan["screen_factor"] * plan["nominal_pop"]
        per_scen = plan["S"] * plan["inner_rigorous_evals"]
        outer = (plan["outer_pop"] * plan["outer_gen"] + 1) * per_scen * plan["variants"]
        across = plan["across_scenario_runs"] * per_scen
        oat = plan["oat_designs_per_cycle"] * per_scen
        total = nominal + plan["doe_cap_evals"] + outer + across + oat
        eff = plan["workers"] * plan["parallel_efficiency"]
        rows.append(dict(cycle=cyc, sec_per_eval=sec, evals_nominal=nominal, evals_doe=plan["doe_cap_evals"], evals_robust_outer=outer,
                         evals_across_scenarios=across, evals_sensitivity=oat, evals_total=total, hours_wall=total * sec / eff / 3600))
    df = pd.DataFrame(rows)
    df.loc[len(df)] = dict(cycle="TOTAL", sec_per_eval=float("nan"), evals_total=df.evals_total.sum(), hours_wall=df.hours_wall.sum())
    df.to_csv(RUNS_DIR / "budget_estimate.csv", index=False)
    return df, plan


if __name__ == "__main__":
    df, plan = estimate()
    print(plan)
    print(df.round(2).to_string(index=False))
