"""Counts and Wilson 95 % intervals for the false-feasible rate FFR = FP / (FP + TN) (manuscript Eq. 9)."""
from __future__ import annotations

import math

import numpy as np

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95):
    """Wilson score interval for k successes in n trials. Returns (p, lo, hi); all nan when n = 0."""
    if n <= 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def ffr_counts(y_true_feasible, y_pred_feasible, mask=None):
    yt = np.asarray(y_true_feasible, bool)
    yp = np.asarray(y_pred_feasible, bool)
    if mask is not None:
        m = np.asarray(mask, bool)
        yt, yp = yt[m], yp[m]
    fp = int((~yt & yp).sum())
    tn = int((~yt & ~yp).sum())
    p, lo, hi = wilson(fp, fp + tn)
    return dict(FP=fp, TN=tn, n_infeasible=fp + tn, FFR=p, FFR_lo95=lo, FFR_hi95=hi,
                TP=int((yt & yp).sum()), FN=int((yt & ~yp).sum()))


def ffr_report(y_true_feasible, y_pred_feasible, mita, mita_min: float, window_K: float = 1.0):
    """Overall and near-limit (|MITA - MITA_min| <= window_K, MITA from the rigorous model) FFR with Wilson intervals."""
    m = np.asarray(mita, float)
    near = np.isfinite(m) & (np.abs(m - mita_min) <= window_K)
    out = {f"overall_{k}": v for k, v in ffr_counts(y_true_feasible, y_pred_feasible).items()}
    out.update({f"near_{k}": v for k, v in ffr_counts(y_true_feasible, y_pred_feasible, near).items()})
    out["n_near"] = int(near.sum())
    return out
