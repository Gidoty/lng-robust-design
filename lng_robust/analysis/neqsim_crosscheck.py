"""Independent property-engine cross-check (NeqSim Peng-Robinson) against the thermo-based PR used in the study.

(1) 20 state points (a treated feed and a refrigerant-like mixture, -165 to 40 C, 1 to 60 bar): beta, enthalpy and entropy
    differences from a 25 C / 1 bar reference, bulk density.
(2) One design per cycle (hand-set reference designs, not optima): SEC, MITA, UA, LNG mass fraction with each engine.
The flowsheet logic is shared, so this tests the property and flash implementation, not the flowsheet formulation.
Writes runs/neqsim_crosscheck_states.csv and runs/neqsim_crosscheck_cycles.csv."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lng_robust.config import RUNS_DIR, load_basis
from lng_robust.cycles import solve
from lng_robust.cycles.pretreat import pretreat
from lng_robust.analysis.timing import DESIGNS, FEED
from lng_robust.props.eos import get_mixture, reduce_comp, use_eos
from lng_robust.props.gerg_check import TEST_COMPOSITIONS

STATES = [(-165, 5), (-150, 10), (-130, 20), (-110, 40), (-90, 5), (-70, 20), (-50, 60), (-30, 10), (0, 1), (40, 30)]


def states():
    rows = []
    for cname in ("TEST_A1LIKE_synthetic", "TEST_MR_synthetic"):
        mix, z, names = reduce_comp(TEST_COMPOSITIONS[cname])
        nq = get_mixture(names, "NEQSIM")
        h0, s0 = mix.flash_TP(298.15, 1e5, z), nq.flash_TP(298.15, 1e5, z)
        for tc, pb in STATES:
            T, P = tc + 273.15, pb * 1e5
            a, b = mix.flash_TP(T, P, z), nq.flash_TP(T, P, z)
            rows.append(dict(composition=cname, T_C=tc, P_bar=pb, beta_thermo=a.beta_gas, beta_neqsim=b.beta_gas,
                             dH_thermo_kJ_kg=(a.H - h0.H) / a.MW, dH_neqsim_kJ_kg=(b.H - s0.H) / b.MW,
                             dS_thermo_J_kg_K=(a.S - h0.S) / a.MW * 1e3, dS_neqsim_J_kg_K=(b.S - s0.S) / b.MW * 1e3,
                             rho_thermo=a.rho_mass, rho_neqsim=b.rho_mass))
    df = pd.DataFrame(rows)
    df["dH_dev_kJ_kg"] = df.dH_neqsim_kJ_kg - df.dH_thermo_kJ_kg
    df["dS_dev_J_kg_K"] = df.dS_neqsim_J_kg_K - df.dS_thermo_J_kg_K
    df["beta_dev"] = df.beta_neqsim - df.beta_thermo
    df["rho_dev_pct"] = 100 * (df.rho_neqsim - df.rho_thermo) / df.rho_thermo
    df.to_csv(RUNS_DIR / "neqsim_crosscheck_states.csv", index=False)
    return df


def cycles():
    basis = load_basis().override(mshe_N=100, mshe_n_table=48)
    feed = pretreat(FEED).treated
    m = 100e3 / 86400
    rows = []
    for cyc, x in DESIGNS.items():
        for label, eos in (("thermo PR", "PR"), ("NeqSim PR", "NEQSIM")):
            with use_eos(eos):
                r = solve(cyc, feed, basis.feed_T, basis.feed_P, m, x, basis)
            rows.append(dict(cycle=cyc, engine=label, sec=r.sec, w_comp_kw=r.w_comp_kw, w_exp_kw=r.w_exp_kw, mita_K=r.mita, ua_kw_per_K=r.ua,
                             lng_mass_frac=r.lng_mass_frac, failure_codes=";".join(r.failure_codes), runtime_s=r.runtime_s, msg=r.failure_msg[:60]))
    df = pd.DataFrame(rows)
    df.to_csv(RUNS_DIR / "neqsim_crosscheck_cycles.csv", index=False)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    s = states()
    print(s[["dH_dev_kJ_kg", "dS_dev_J_kg_K", "beta_dev", "rho_dev_pct"]].abs().describe().loc[["mean", "max"]].round(3))
    print(cycles().round(4).to_string(index=False))
