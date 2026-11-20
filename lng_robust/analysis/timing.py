"""Wall-clock time of one rigorous cycle evaluation at default and quick-mode resolution, single process.
Writes runs/cycle_timing.csv. The designs are hand-set reference designs (not optima, not results)."""
from __future__ import annotations

import statistics
import time

import pandas as pd

from lng_robust.config import RUNS_DIR, load_basis
from lng_robust.cycles import solve
from lng_robust.cycles.pretreat import pretreat

FEED = {"C1": 92.51, "C2": 2.78, "C3": 1.66, "iC4": 0.39, "nC4": 0.39, "iC5": 0.15, "nC5": 0.15, "N2": 0.22, "CO2": 0.11}
DESIGNS = {
    "smr": dict(ref={"N2": 0.08, "C1": 0.28, "C2": 0.35, "C3": 0.12, "nC4": 0.15, "iC5": 0.02}, P_high_bar=25, P_low_bar=3.5, flow_ratio=2.5, T_lng_C=-150),
    "n2_single": dict(P_high_bar=60, P_low_bar=10, flow_ratio=8, T_exp_in_C=-95, T_lng_C=-150),
    "n2_dual": dict(P_high_bar=60, P_low_bar=10, flow_ratio=8, T_exp_in_warm_C=-30, T_exp_in_cold_C=-100, split=0.5, T_lng_C=-150),
}


def run(reps: int = 5):
    feed = pretreat(FEED).treated
    m = 100e3 / 86400
    rows = []
    for label, kw in (("default (N=100, table=48)", {}), ("quick (N=40, table=24)", dict(mshe_N=40, mshe_n_table=24))):
        b = load_basis().override(**kw) if kw else load_basis()
        for cyc, x in DESIGNS.items():
            solve(cyc, feed, b.feed_T, b.feed_P, m, x, b)           # warm-up: builds property objects
            ts, nf = [], []
            for _ in range(reps):
                t = time.perf_counter()
                r = solve(cyc, feed, b.feed_T, b.feed_P, m, x, b)
                ts.append(time.perf_counter() - t)
                nf.append(r.n_flash)
            rows.append(dict(resolution=label, cycle=cyc, median_s=statistics.median(ts), min_s=min(ts), max_s=max(ts),
                             flashes_per_eval=statistics.median(nf), reps=reps))
    df = pd.DataFrame(rows)
    df.to_csv(RUNS_DIR / "cycle_timing.csv", index=False)
    return df


if __name__ == "__main__":
    print(run().to_string(index=False))
