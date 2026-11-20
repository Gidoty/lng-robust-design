"""Feasibility-classifier reliability: confusion matrix and false-feasible rate FFR = FP / (FP + TN)."""
from __future__ import annotations

import numpy as np


def confusion(y_true_feasible, y_pred_feasible):
    yt = np.asarray(y_true_feasible, bool)
    yp = np.asarray(y_pred_feasible, bool)
    tp = int((yt & yp).sum())
    tn = int((~yt & ~yp).sum())
    fp = int((~yt & yp).sum())          # infeasible predicted feasible
    fn = int((yt & ~yp).sum())
    return dict(TP=tp, TN=tn, FP=fp, FN=fn)


def ffr(y_true_feasible, y_pred_feasible) -> float:
    c = confusion(y_true_feasible, y_pred_feasible)
    d = c["FP"] + c["TN"]
    return c["FP"] / d if d else float("nan")


def near_limit_mask(mita, mita_min: float, window_K: float = 1.0):
    """True where the rigorous MITA is within window_K of the limit (MITA known only if the exchanger was evaluated)."""
    m = np.asarray(mita, float)
    return np.isfinite(m) & (np.abs(m - mita_min) <= window_K)


def report(y_true_feasible, y_pred_feasible, mita, mita_min, window_K=1.0):
    yt, yp = np.asarray(y_true_feasible, bool), np.asarray(y_pred_feasible, bool)
    near = near_limit_mask(mita, mita_min, window_K)
    out = dict(overall=confusion(yt, yp), FFR_overall=ffr(yt, yp),
               n_near=int(near.sum()), FFR_near=ffr(yt[near], yp[near]) if near.any() else float("nan"),
               near_confusion=confusion(yt[near], yp[near]) if near.any() else {})
    return out
