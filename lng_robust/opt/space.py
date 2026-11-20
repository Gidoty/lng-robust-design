"""Decision-variable definitions, bounds (from the design basis) and encodings for each cycle.

Stage 2 (operating, re-optimised per scenario): pressures, flows, temperatures.
Stage 1 (equipment, fixed across scenarios): SMR refrigerant composition and UA; nitrogen cycles UA and rated flow.
UA and rated flow are specific (per kg/s of LNG product) so designs transfer across capacities."""
from __future__ import annotations

import numpy as np

STAGE2 = {
    "smr": ["P_high_bar", "P_low_bar", "flow_ratio", "T_lng_C"],
    "n2_single": ["P_high_bar", "P_low_bar", "flow_ratio", "T_exp_in_C", "T_lng_C"],
    "n2_dual": ["P_high_bar", "P_low_bar", "flow_ratio", "T_exp_in_warm_C", "T_exp_in_cold_C", "split", "T_lng_C"],
}
SMR_COMPS = ["N2", "C1", "C2", "C3", "nC4", "iC5"]
STAGE1 = {
    "smr": [f"w_{c}" for c in SMR_COMPS] + ["ua_spec"],
    "n2_single": ["ua_spec", "n_rated_spec"],
    "n2_dual": ["ua_spec", "n_rated_spec"],
}


def bounds(cycle: str, names: list, basis) -> tuple[np.ndarray, np.ndarray]:
    b = basis.bounds[cycle]
    lo, hi = [], []
    for n in names:
        if n.startswith("w_"):
            l, h = b["ref_weights"][n[2:]]
        elif n == "ua_spec":
            l, h = b["ua_kw_per_K_per_kgs"]
        elif n == "n_rated_spec":
            l, h = b["n_rated_mol_per_kg_lng"]
        else:
            l, h = b[n]
        lo.append(l)
        hi.append(h)
    return np.array(lo, float), np.array(hi, float)


def decode(cycle: str, names: list, v, m_lng: float, with_equipment: bool = False) -> dict:
    """Vector -> solver input dict x. Stage-1 entries become ref composition / installed limits."""
    x = {}
    w = {}
    for n, val in zip(names, v):
        val = float(val)
        if n.startswith("w_"):
            w[n[2:]] = val
        elif n == "ua_spec":
            if with_equipment:
                x["ua_installed_kw_per_K"] = val * m_lng
            x["_ua_spec"] = val
        elif n == "n_rated_spec":
            if with_equipment:
                x["n_ref_rated_mol_s"] = val * m_lng
            x["_n_rated_spec"] = val
        else:
            x[n] = val
    if w:
        tot = sum(w.values())
        x["ref"] = {k: v_ / tot for k, v_ in w.items() if v_ > 0}
    return x


def clean(x: dict) -> dict:
    return {k: v for k, v in x.items() if not k.startswith("_")}
