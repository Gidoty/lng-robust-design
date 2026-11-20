"""Interior-pinch discretisation study on a HAND-SET SMR design (not an optimum, not a result).

The Jensen Case 1 design pinches at the cold end for every flow, so it cannot test interior pinches. The design below was found
by a 90-sample random search around Jensen's refrigerant (seed 7) as one whose pinch is interior (node 30 of 100, hot side about 193 K)
with MITA near 2 K. Feed and basis are the Jensen benchmark inputs (secondary sources).

For N = 10 ... 400 (table resolution fixed at 96): MITA, pinch node and temperature, UA, and the SEC obtained after
re-solving the refrigerant flow so that MITA equals a fixed target (1.5 K), i.e. the SEC of an N-consistent design.
Writes runs/mshe_convergence_smr.csv."""
from __future__ import annotations

import pandas as pd
import yaml
from scipy.optimize import brentq

from lng_robust.config import DATA_DIR, RUNS_DIR, load_basis
from lng_robust.props.eos import mixture_MW
from lng_robust.validate import _basis_for
from lng_robust.cycles.smr import solve_smr

TARGET_MITA = 2.0
DESIGN = dict(ref={'N2': 0.078, 'C1': 0.262, 'C2': 0.414, 'C3': 0.016, 'nC4': 0.178, 'iC5': 0.053}, P_high_bar=22.0, P_low_bar=4.844,
              flow_ratio=4.145, T_lng_C=-144.0)
N_LIST = [10, 20, 50, 100, 200, 400]


def run():
    spec = yaml.safe_load(open(DATA_DIR / "benchmarks.yaml"))["jensen_skogestad2009_prico"]
    inp = spec["inputs"]
    base = _basis_for(load_basis(), inp, 0.828, None, TARGET_MITA)   # basis from the Jensen inputs; PR
    feed = inp["feed_composition"]

    def evaluate(b, ratio):
        x = dict(DESIGN, flow_ratio=ratio)
        return solve_smr(feed, b.feed_T, b.feed_P, 1.0, x, b)

    r0 = DESIGN['flow_ratio']
    rows = []
    for N in N_LIST:
        b = base.override(mshe_N=N, mshe_n_table=96)
        r = evaluate(b, r0)
        mr = r._mshe
        T_pinch = float(mr.T_hot[mr.pinch_index])
        def f(ratio):
            q = evaluate(b, ratio)
            return q.mita - TARGET_MITA
        try:
            ratio = brentq(f, 0.85 * r0, 1.15 * r0, xtol=1e-6)
            sec_t = evaluate(b, ratio).sec
        except Exception as e:           # no sign change in the bracket: report, do not hide
            ratio, sec_t = float("nan"), float("nan")
        rows.append(dict(N=N, n_table=96, mita_K=r.mita, pinch_node=int(mr.pinch_index), pinch_is_interior=bool(0 < mr.pinch_index < N),
                         pinch_T_hot_K=T_pinch, ua_kw_per_K_per_kgs=r.ua, sec_at_published_flow=r.sec,
                         flow_ratio_for_target_mita=ratio, sec_at_target_mita=sec_t, target_mita_K=TARGET_MITA,
                         case="hand-set SMR design with interior pinch; Jensen benchmark basis; PR"))
    df = pd.DataFrame(rows)
    ref = df[df.N == 400].iloc[0]
    df["sec_target_change_vs_N400_pct"] = 100 * (df.sec_at_target_mita - ref.sec_at_target_mita) / ref.sec_at_target_mita
    df["ua_change_vs_N400_pct"] = 100 * (df.ua_kw_per_K_per_kgs - ref.ua_kw_per_K_per_kgs) / ref.ua_kw_per_K_per_kgs
    df.to_csv(RUNS_DIR / "mshe_convergence_smr.csv", index=False)
    return df


if __name__ == "__main__":
    print(run().round(5).to_string(index=False))
