"""Shared helpers for the nominal and robust optimisers."""
from __future__ import annotations

import math

import numpy as np

from lng_robust.opt.parallel import map_eval
from lng_robust.opt.space import STAGE1, STAGE2, bounds, clean, decode


def nominal_var_names(cycle: str) -> list:
    """Variables searched in the nominal design: all stage-2 variables (+ SMR refrigerant weights)."""
    return STAGE2[cycle] + ([n for n in STAGE1["smr"] if n.startswith("w_")] if cycle == "smr" else [])


def cvar(values, alpha: float) -> float:
    """CVaR_alpha = min_t { t + 1/((1-alpha) S) * sum_s max(0, v_s - t) }  (Rockafellar-Uryasev).
    The objective is piecewise linear and convex in t, so the minimum is attained at one of the v_s."""
    v = np.asarray(values, float)
    S = len(v)
    best = math.inf
    for t in np.unique(v):
        best = min(best, t + np.maximum(0.0, v - t).sum() / ((1.0 - alpha) * S))
    return float(best)


def penalised_sec(res, sec_pen: float) -> float:
    """SEC of a feasible result, else the infeasibility penalty (manuscript Section 2.9)."""
    return float(res.sec) if res.feasible and res.sec == res.sec else float(sec_pen)


def knee_point(F: np.ndarray) -> int:
    """Index of the point closest to the utopia point in min-max normalised objective space."""
    F = np.asarray(F, float)
    lo, hi = F.min(0), F.max(0)
    span = np.where(hi - lo > 0, hi - lo, 1.0)
    return int(np.argmin((((F - lo) / span) ** 2).sum(1)))


def price_of_robustness(sec_rob_at_z0: float, sec_nom_at_z0: float) -> float:
    """PoR = (SEC(x_rob, z0) - SEC(x_nom, z0)) / SEC(x_nom, z0)   (manuscript Eq. 8). Fraction, not per cent."""
    return (sec_rob_at_z0 - sec_nom_at_z0) / sec_nom_at_z0
