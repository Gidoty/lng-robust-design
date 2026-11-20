"""Ranking reversal over the composition envelope (manuscript Section 2.9).

The envelope is partitioned into cells along two composition coordinates (treated-feed N2 mol% and C2+ mol%).
In each cell the preferred cycle is the one with the lowest mean SEC over the cell's scenarios among cycles whose feasible fraction
in that cell meets the chance constraint, determined separately for nominal and risk-averse designs. A cell where the two preferences
differ is a reversal. Differences smaller than `indistinguishable_pct` (the validation uncertainty) are reported as a tie, and a tie
is not counted as a reversal."""
from __future__ import annotations

import numpy as np
import pandas as pd

C2PLUS = ("C2", "C3", "iC4", "nC4", "iC5", "nC5", "C6")


def coords(treated: dict):
    return 100.0 * treated.get("N2", 0.0), 100.0 * sum(treated.get(k, 0.0) for k in C2PLUS)


def assign_cells(df: pd.DataFrame, n_x: int = 4, n_y: int = 4):
    """Quantile cells (equal counts) on the two coordinates; returns df with cell_x, cell_y, cell id."""
    d = df.copy()
    d["cell_x"] = pd.qcut(d["N2_pct"].rank(method="first"), n_x, labels=False)
    d["cell_y"] = pd.qcut(d["C2plus_pct"].rank(method="first"), n_y, labels=False)
    d["cell"] = d["cell_x"] * n_y + d["cell_y"]
    return d


def preferred(cell_stats: dict, chance: float, indistinguishable_pct: float):
    """cell_stats: {cycle: (mean_sec, feasible_fraction)}. Returns (preferred or 'TIE' or 'NONE', gap_pct)."""
    ok = {c: v for c, v in cell_stats.items() if v[1] >= chance and v[0] == v[0]}
    if not ok:
        return "NONE", float("nan")
    order = sorted(ok, key=lambda c: ok[c][0])
    if len(order) == 1:
        return order[0], float("nan")
    gap = 100.0 * (ok[order[1]][0] - ok[order[0]][0]) / ok[order[0]][0]
    return (order[0] if gap > indistinguishable_pct else "TIE"), gap


def reversal_table(df: pd.DataFrame, chance: float = 0.95, indistinguishable_pct: float = 5.0):
    """df columns: cell, cycle, design ('nominal' | 'robust'), sec (NaN when infeasible), feasible (bool). One row per scenario."""
    rows = []
    for cell, g in df.groupby("cell"):
        pref = {}
        for design in ("nominal", "robust"):
            st = {}
            for cyc, h in g[g.design == design].groupby("cycle"):
                feas = h["feasible"].astype(bool)
                st[cyc] = (float(h.loc[feas, "sec"].mean()) if feas.any() else float("nan"), float(feas.mean()))
            pref[design] = preferred(st, chance, indistinguishable_pct)
        n_scen = int(g[(g.design == "nominal") & (g.cycle == g.cycle.iloc[0])].shape[0])
        pn, pr = pref["nominal"][0], pref["robust"][0]
        rev = pn != pr and pn not in ("TIE", "NONE") and pr not in ("TIE", "NONE")
        rows.append(dict(cell=int(cell), cell_x=int(g.cell_x.iloc[0]), cell_y=int(g.cell_y.iloc[0]), n_scenarios=n_scen,
                         N2_pct_mean=float(g.N2_pct.mean()), C2plus_pct_mean=float(g.C2plus_pct.mean()),
                         preferred_nominal=pn, gap_nominal_pct=pref["nominal"][1], preferred_robust=pr,
                         gap_robust_pct=pref["robust"][1], reversal=bool(rev)))
    return pd.DataFrame(rows).sort_values("cell")
