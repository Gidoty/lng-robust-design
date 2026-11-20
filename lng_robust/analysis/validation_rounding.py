"""Input-precision diagnostic for point benchmarks.

Published decision variables are printed rounded. For every point, each variable is moved by half of its last printed
digit (all corners of the box), and the range of the computed net power is compared with the published value. This does not
change any verdict; it says whether the published value is consistent with the printed inputs. Writes runs/validation_rounding.csv.
"""
from __future__ import annotations

import itertools

import pandas as pd
import yaml

from lng_robust.config import DATA_DIR, RUNS_DIR, load_basis
from lng_robust.props.eos import mixture_MW, use_eos
from lng_robust.validate import N2_MW, _basis_for, _solver

COLS = {"n2_single": ["T_II_K", "mR_kg_s", "pL_bar", "pH_bar"]}


def half_ulp(raw: str) -> float:
    s = raw.strip()
    if "." in s:
        return 0.5 * 10 ** (-len(s.split(".")[1]))
    return 0.5          # a value printed as an integer in these tables (pressures 2, 3, 120): +/- 0.5 unit


def run(names=("austbo2015_n2_single_PR", "austbo2015_n2_single_SRK")):
    spec = yaml.safe_load(open(DATA_DIR / "benchmarks.yaml"))
    basis = load_basis()
    out = []
    for name in names:
        sp = spec[name]
        common = sp["common_inputs"]
        raw = pd.read_csv(DATA_DIR / sp["points_file"], comment="#", dtype=str)
        eos = "SRK" if sp["published_basis"]["equation_of_state"] == "SRK" else "PR"
        solve = _solver("n2_single")
        for _, r in raw.iterrows():
            vals = {c: float(r[c]) for c in COLS["n2_single"]}
            hu = {c: half_ulp(r[c]) for c in COLS["n2_single"]}
            # an integer 120 bar upper bound is a design bound, not a rounded value
            if vals["pH_bar"] == 120.0:
                hu["pH_bar"] = 0.0
            w = []
            for signs in itertools.product((-1, 1), repeat=len(COLS["n2_single"])):
                v = {c: vals[c] + s * hu[c] for c, s in zip(COLS["n2_single"], signs)}
                b = _basis_for(basis, common, float(r.eta_s), float(r.eta_s), float(r.dTmin_K))
                with use_eos(eos):
                    n_feed = common["feed_flow_kg_s"] / (mixture_MW(common["feed_composition"]) / 1e3)
                    x = dict(P_high_bar=v["pH_bar"], P_low_bar=v["pL_bar"], flow_ratio=v["mR_kg_s"] / (N2_MW / 1e3) / n_feed,
                             T_exp_in_C=v["T_II_K"] - 273.15, T_lng_C=common["T_lng_K"] - 273.15)
                    res = solve(common["feed_composition"], b.feed_T, b.feed_P, common["feed_flow_kg_s"], x, b)
                if res.sec == res.sec:
                    w.append(res.w_comp_kw - res.w_exp_kw)
            pub = float(r.Wnet_kW)
            lo, hi = (min(w), max(w)) if w else (float("nan"), float("nan"))
            out.append(dict(benchmark=name, dTmin_K=float(r.dTmin_K), eta_s=float(r.eta_s), published_Wnet_kW=pub,
                            computed_min_kW=lo, computed_max_kW=hi, published_inside_band=bool(lo <= pub <= hi),
                            half_ulp_pH_bar=hu["pH_bar"], n_corners=len(w)))
    df = pd.DataFrame(out)
    df.to_csv(RUNS_DIR / "validation_rounding.csv", index=False)
    return df


if __name__ == "__main__":
    print(run().to_string(index=False))
