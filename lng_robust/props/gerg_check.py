"""Compare Peng-Robinson (thermo) with GERG-2008 (CoolProp HEOS mixture backend).

Density is compared directly. Enthalpy is compared as a difference from a per-composition reference
state (25 C, 1 bar) because the two libraries use different enthalpy datums.
Writes runs/gerg_check.csv and runs/gerg_check_summary.csv. Failures are logged, never dropped.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from lng_robust.config import RUNS_DIR
from lng_robust.props.eos import FlashError, reduce_comp

COOLPROP_NAMES = {
    "N2": "Nitrogen", "CO2": "CarbonDioxide", "C1": "Methane", "C2": "Ethane", "C3": "Propane",
    "iC4": "IsoButane", "nC4": "n-Butane", "iC5": "Isopentane", "nC5": "n-Pentane", "C6": "n-Hexane",
}

# Test compositions for the property comparison ONLY. They are synthetic (not field data) and are
# not part of the feed envelope. mole fractions.
TEST_COMPOSITIONS = {
    "TEST_LEAN_synthetic": {"C1": 0.950, "C2": 0.025, "C3": 0.010, "iC4": 0.002, "nC4": 0.003, "N2": 0.010},
    "TEST_A1LIKE_synthetic": {"C1": 0.9251, "C2": 0.0278, "C3": 0.0166, "iC4": 0.0039, "nC4": 0.0039,
                              "iC5": 0.0015, "nC5": 0.0015, "N2": 0.0022, "CO2": 0.0011, "C6": 0.0},
    "TEST_RICH_synthetic": {"C1": 0.800, "C2": 0.090, "C3": 0.060, "iC4": 0.012, "nC4": 0.018,
                            "iC5": 0.004, "nC5": 0.004, "N2": 0.010, "CO2": 0.002},
    "TEST_MR_synthetic": {"N2": 0.064, "C1": 0.333, "C2": 0.353, "nC4": 0.250},
}
T_C = [-165, -150, -130, -110, -90, -60, -30, 0, 40]
P_BAR = [1, 5, 10, 20, 40, 60]
REF_T, REF_P = 298.15, 1.0e5


def _cp_state(comp: dict):
    import CoolProp.CoolProp as CP
    names = [c for c, v in comp.items() if v > 0]
    fluid = "&".join(COOLPROP_NAMES[c] for c in names)
    st = CP.AbstractState("HEOS", fluid)
    tot = sum(comp[c] for c in names)
    st.set_mole_fractions([comp[c] / tot for c in names])
    return st


def _flag_suspect_gerg(df: pd.DataFrame) -> pd.DataFrame:
    """CoolProp's mixture PT solver can return a wrong-branch result without raising (seen near the
    two-phase boundary). Along an isobar, enthalpy must rise and density must fall with temperature.
    A point that breaks either rule against its neighbours is labelled GERG_SUSPECT. It stays in the
    CSV, with its numbers, and is excluded from the summary statistics. Nothing is dropped silently."""
    df = df.copy()
    df["gerg_suspect"] = False
    for (_, _), g in df.groupby(["composition", "P_bar"]):
        g = g.sort_values("T_C")
        idx = list(g.index)
        h = dict(zip(idx, g["dh_gerg_kJ_kg"].values))
        r = dict(zip(idx, g["rho_gerg"].values))
        live = [i for i in idx if math.isfinite(h[i]) and math.isfinite(r[i])]
        while True:  # greedy: flag the point that breaks the ordering against most neighbours, re-check
            viol = {i: 0 for i in live}
            for a, b in zip(live[:-1], live[1:]):  # a is colder than b
                if h[b] <= h[a] or r[b] >= r[a]:
                    viol[a] += 1
                    viol[b] += 1
            worst = max(viol, key=viol.get) if viol else None
            if worst is None or viol[worst] == 0:
                break
            df.loc[worst, "gerg_suspect"] = True
            live.remove(worst)
    ok_before = df["status"] == "OK"
    df.loc[ok_before & df["gerg_suspect"], "status"] = "GERG_SUSPECT"
    return df


def run(out_dir: Path = RUNS_DIR) -> pd.DataFrame:
    import CoolProp.CoolProp as CP
    rows = []
    for cname, comp in TEST_COMPOSITIONS.items():
        mix, z, names = reduce_comp(comp)
        cp = _cp_state({n: zi for n, zi in zip(names, z)})
        try:
            cp.update(CP.PT_INPUTS, REF_P, REF_T)
            h_ref_g = cp.hmass()
        except Exception as e:  # pragma: no cover
            h_ref_g = float("nan")
        h_ref_pr = mix.flash_TP(REF_T, REF_P, z).H_mass
        for tc in T_C:
            for pb in P_BAR:
                T, P = tc + 273.15, pb * 1e5
                row = dict(composition=cname, T_C=tc, P_bar=pb, synthetic_test_composition=True)
                try:
                    cp.update(CP.PT_INPUTS, P, T)
                    row.update(rho_gerg=cp.rhomass(), dh_gerg_kJ_kg=(cp.hmass() - h_ref_g) / 1e3,
                               gerg_phase=CP.PhaseSI("T", T, "P", P, cp.fluid_names()[0]) if False else int(cp.phase()))
                    gerg_ok = True
                except Exception as e:
                    gerg_ok = False
                    row.update(rho_gerg=np.nan, dh_gerg_kJ_kg=np.nan, gerg_phase=-1, gerg_error=str(e)[:120])
                try:
                    st = mix.flash_TP(T, P, z)
                    row.update(rho_pr=st.rho_mass, dh_pr_kJ_kg=(st.H_mass - h_ref_pr) / 1e3,
                               pr_beta_gas=st.beta_gas, pr_n_phases=st.n_phases)
                    pr_ok = True
                except FlashError as e:
                    pr_ok = False
                    row.update(rho_pr=np.nan, dh_pr_kJ_kg=np.nan, pr_beta_gas=np.nan, pr_n_phases=-1,
                               pr_error=str(e)[:120])
                if gerg_ok and pr_ok:
                    row["rho_dev_pct"] = 100 * (row["rho_pr"] - row["rho_gerg"]) / row["rho_gerg"]
                    row["dh_dev_kJ_kg"] = row["dh_pr_kJ_kg"] - row["dh_gerg_kJ_kg"]
                    row["status"] = "OK"
                else:
                    row["status"] = ("GERG_FAIL " if not gerg_ok else "") + ("PR_FAIL" if not pr_ok else "")
                rows.append(row)
    df = pd.DataFrame(rows)
    # region label from the PR flash (consistent across compositions): vapour, liquid, two-phase
    def region(r):
        if r.get("status") != "OK":
            return "failed"
        if r["pr_n_phases"] == 2:
            return "two-phase"
        return "vapour/gas-like" if r["pr_beta_gas"] >= 0.5 else "liquid/dense"
    df = _flag_suspect_gerg(df)
    df["region"] = df.apply(region, axis=1)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "gerg_check.csv", index=False)
    ok = df[df.status == "OK"]
    def summ(g):
        return pd.Series(dict(
            n=len(g),
            rho_mean_abs_dev_pct=g.rho_dev_pct.abs().mean(), rho_max_abs_dev_pct=g.rho_dev_pct.abs().max(),
            rho_rms_dev_pct=math.sqrt((g.rho_dev_pct ** 2).mean()),
            dh_mean_abs_dev_kJ_kg=g.dh_dev_kJ_kg.abs().mean(), dh_max_abs_dev_kJ_kg=g.dh_dev_kJ_kg.abs().max()))
    summary = pd.concat([
        ok.groupby("composition").apply(summ, include_groups=False).assign(group="by composition"),
        ok.groupby("region").apply(summ, include_groups=False).assign(group="by region"),
        summ(ok).to_frame("ALL").T.assign(group="all"),
    ])
    summary.index.name = "key"
    summary.to_csv(out_dir / "gerg_check_summary.csv")
    return df


def methane_density_map(out_dir: Path = RUNS_DIR) -> pd.DataFrame:
    """Pure-methane PR vs CoolProp (reference EOS) density on a T-P grid, including the states where
    plain PR exceeds 2 per cent. Written so the failing region is reported, not hidden."""
    import CoolProp.CoolProp as CP
    from lng_robust.props.eos import get_mixture
    m = get_mixture(("C1",))
    rows = []
    for tc in (-160, -140, -120, -100, -80, -60, -40, -20, 0, 25, 60):
        for pb in (1, 5, 10, 20, 30, 40, 60):
            T, P = tc + 273.15, pb * 1e5
            st = m.flash_TP(T, P, [1.0])
            ref = CP.PropsSI("D", "T", T, "P", P, "Methane")
            rows.append(dict(T_C=tc, P_bar=pb, rho_pr=st.rho_mass, rho_coolprop=ref, n_phases=st.n_phases,
                             rho_dev_pct=100 * (st.rho_mass - ref) / ref))
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "methane_density_map.csv", index=False)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUNS_DIR))
    a = ap.parse_args()
    methane_density_map(Path(a.out))
    df = run(Path(a.out))
    print(f"states: {len(df)}  ok: {(df.status=='OK').sum()}  failed: {(df.status!='OK').sum()}")
    print(pd.read_csv(Path(a.out) / "gerg_check_summary.csv").to_string(index=False))


if __name__ == "__main__":
    main()
