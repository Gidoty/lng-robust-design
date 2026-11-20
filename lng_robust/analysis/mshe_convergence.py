"""MSHE discretisation study on ONE converged case (a hand-set reference design, not an optimum, not a result).

Varies N (equal-duty intervals) at a fixed property-table resolution, and the table resolution at fixed N,
and records MITA and UA. Writes runs/mshe_convergence.csv.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from lng_robust.config import RUNS_DIR, load_basis
from lng_robust.cycles.n2_dual import solve_n2_dual
from lng_robust.cycles.pretreat import pretreat

REFERENCE_FEED_RAW = {"C1": 92.51, "C2": 2.78, "C3": 1.66, "iC4": 0.39, "nC4": 0.39, "iC5": 0.15, "nC5": 0.15,
                      "N2": 0.22, "CO2": 0.11}     # A1 (secondary source); C4/C5 split is an assumption
REFERENCE_X = dict(P_high_bar=60, P_low_bar=10, flow_ratio=8, T_exp_in_warm_C=-30, T_exp_in_cold_C=-100,
                   split=0.5, T_lng_C=-150)
N_LIST = [10, 20, 50, 100, 200]
TABLE_LIST = [12, 24, 48, 96, 192]


def run(out_dir: Path = RUNS_DIR):
    basis = load_basis()
    feed = pretreat(REFERENCE_FEED_RAW).treated
    m_lng = 100 * 1000 / 86400
    rows = []
    for study, grid in (("N", [(n, basis.mshe_n_table) for n in N_LIST]),
                        ("n_table", [(basis.mshe_N, t) for t in TABLE_LIST])):
        for N, nt in grid:
            b = basis.override(mshe_N=N, mshe_n_table=nt)
            r = solve_n2_dual(feed, b.feed_T, b.feed_P, m_lng, REFERENCE_X, b)
            rows.append(dict(study=study, N=N, n_table=nt, mita_K=r.mita, ua_kw_per_K=r.ua, sec_kwh_per_kg=r.sec,
                             converged=r.converged, feasible=r.feasible, failure_codes=";".join(r.failure_codes),
                             balance_error=r.balance_error, runtime_s=r.runtime_s,
                             case="N2_dual reference design (hand-set, not optimised)"))
    df = pd.DataFrame(rows)
    ref = df[(df.study == "N")].set_index("N")
    base = ref.loc[basis.mshe_N]
    df["ua_change_vs_default_pct"] = 100 * (df.ua_kw_per_K - base.ua_kw_per_K) / base.ua_kw_per_K
    df["mita_change_vs_default_K"] = df.mita_K - base.mita_K
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "mshe_convergence.csv", index=False)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUNS_DIR))
    print(run(Path(ap.parse_args().out)).to_string(index=False))
