"""Surrogate models of SEC and feasibility, trained on rigorous evaluations, validated leave-one-composition-out.

Groups: every case from one composition (and, in the full study, one anchor with its synthetic neighbours) is
withheld in turn, so no withheld composition is seen in training. Regression is scored on feasible cases only
(SEC exists only there); the classifier is scored on all cases."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import qmc
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from lng_robust.opt.common import nominal_var_names
from lng_robust.opt.parallel import map_eval
from lng_robust.opt.space import bounds, clean, decode
from lng_robust.surrogate import classify

C4S, C5S = ("iC4", "nC4"), ("iC5", "nC5", "C6")


def alr_features(treated: dict) -> list:
    """Additive log-ratio coordinates of the treated feed relative to methane."""
    f = lambda keys: max(sum(treated.get(k, 0.0) for k in keys), 1e-6)
    c1 = max(treated.get("C1", 0.0), 1e-6)
    return [math.log(f(("N2",)) / c1), math.log(f(("C2",)) / c1), math.log(f(("C3",)) / c1),
            math.log(f(C4S) / c1), math.log(f(C5S) / c1)]


def build_dataset(cycle, feeds, m_lng, basis, n_samples, seed, log=None, workers=None, capacity_tpd=100,
                  group_by_anchor=False):
    """group_by_anchor=True (full study): group = parent anchor, so an anchor and its synthetic neighbours are withheld
    together. False (quick mode, one anchor): every composition is its own group."""
    names = nominal_var_names(cycle)
    lo, hi = bounds(cycle, names, basis)
    u = qmc.LatinHypercube(d=len(names) + 1, seed=seed).random(n_samples)
    vecs = lo + u[:, :-1] * (hi - lo)
    fidx = np.minimum((u[:, -1] * len(feeds)).astype(int), len(feeds) - 1)
    xs = [clean(decode(cycle, names, v, m_lng)) for v in vecs]
    tasks = [(cycle, feeds[i].treated, basis.feed_T, basis.feed_P, m_lng, x, basis) for i, x in zip(fidx, xs)]
    R = map_eval(tasks, workers)
    rows = []
    for v, i, x, r in zip(vecs, fidx, xs, R):
        if log is not None:
            log.add(r, cycle=cycle, feed_id=feeds[i].id, synthetic=feeds[i].synthetic, parent_id=feeds[i].parent_id,
                    kappa=feeds[i].kappa, capacity_tpd=capacity_tpd, stage1={"ref": x.get("ref")},
                    stage2={k: val for k, val in x.items() if k != "ref"}, purpose="surrogate_doe", composition=feeds[i].treated)
        rows.append({**{n: val for n, val in zip(names, v)}, **{f"alr{j}": a for j, a in enumerate(alr_features(feeds[i].treated))},
                     "group": (feeds[i].parent_id or feeds[i].id) if group_by_anchor else feeds[i].id,
                     "feed_id": feeds[i].id, "sec": r.sec if r.feasible else np.nan, "mita": r.mita,
                     "feasible": bool(r.feasible), "failure_code": r.failure_code,
                     "numerical_failure": bool(r.failure_code in ("FLASH_FAIL", "NONCONVERGED"))})
    return pd.DataFrame(rows), names


def feature_cols(df):
    return [c for c in df.columns if c not in ("group", "feed_id", "sec", "mita", "feasible", "failure_code", "numerical_failure")]


def regressors(seed):
    gp = GaussianProcessRegressor(ConstantKernel(1.0) * RBF(length_scale=np.ones(1)) + WhiteKernel(1e-3),
                                  normalize_y=True, n_restarts_optimizer=0, random_state=seed)
    return {"linear_ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
            "gradient_boosting": GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=seed),
            "gaussian_process": make_pipeline(StandardScaler(), gp)}


def classifiers(seed):
    return {"logistic_baseline": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
            "gradient_boosting": GradientBoostingClassifier(n_estimators=150, max_depth=3, random_state=seed)}


def _fit_gp_iso(model, X):
    """GP with an anisotropic RBF needs the feature count; rebuild the kernel per fit."""
    gp = model.steps[-1][1]
    gp.kernel = ConstantKernel(1.0) * RBF(length_scale=np.ones(X.shape[1])) + WhiteKernel(1e-3)


def grouped_cv(df: pd.DataFrame, mita_min: float, seed: int = 1, window_K: float = 1.0):
    """Leave-one-group-out predictions for every model. Returns (metrics_df, oof_df)."""
    cols = feature_cols(df)
    X = df[cols].values
    groups = df["group"].values
    logo = LeaveOneGroupOut()
    feas = df["feasible"].values.astype(bool)
    oof = df[["group", "feed_id", "sec", "mita", "feasible", "failure_code", "numerical_failure"]].copy()
    for name in regressors(seed):
        oof[f"sec_{name}"] = np.nan
    for name in classifiers(seed):
        oof[f"feas_{name}"] = np.nan
    for tr, te in logo.split(X, feas, groups):
        for name, model in regressors(seed).items():
            trf = tr[feas[tr]]
            if len(trf) < 5:
                continue
            if name == "gaussian_process":
                _fit_gp_iso(model, X[trf])
            model.fit(X[trf], df["sec"].values[trf])
            oof.loc[oof.index[te], f"sec_{name}"] = model.predict(X[te])
        for name, model in classifiers(seed).items():
            y = feas[tr]
            if y.all() or (~y).all():
                oof.loc[oof.index[te], f"feas_{name}"] = float(y[0])
                continue
            model.fit(X[tr], y)
            oof.loc[oof.index[te], f"feas_{name}"] = model.predict(X[te]).astype(float)
    rows = []
    ok = feas
    for name in regressors(seed):
        m = ok & oof[f"sec_{name}"].notna().values
        if m.sum() >= 2:
            y, p = df["sec"].values[m], oof[f"sec_{name}"].values[m]
            rows.append(dict(kind="regression", model=name, n=int(m.sum()), MAE=mean_absolute_error(y, p),
                             RMSE=math.sqrt(mean_squared_error(y, p)), R2=r2_score(y, p), unit="kWh/kg"))
    for name in classifiers(seed):
        p = oof[f"feas_{name}"].values
        m = ~np.isnan(p)
        yt, yp = feas[m], p[m].astype(bool)
        rep = classify.report(yt, yp, df["mita"].values[m], mita_min, window_K)
        # physical-infeasibility-only negatives (exclude numerical non-convergence)
        phys = m & ~df["numerical_failure"].values
        rep_phys = classify.report(feas[phys], p[phys].astype(bool), df["mita"].values[phys], mita_min, window_K)
        rows.append(dict(kind="classification", model=name, n=int(m.sum()), **rep["overall"],
                         FFR_overall=rep["FFR_overall"], n_near_limit=rep["n_near"], FFR_near_limit=rep["FFR_near"],
                         FFR_overall_physical_only=rep_phys["FFR_overall"], FFR_near_physical_only=rep_phys["FFR_near"]))
    return pd.DataFrame(rows), oof
