"""Grouped (leave-one-anchor-out) validation of the surrogates with FFR counts and Wilson 95 % intervals (Phase 6).

Groups: every composition that descends from one anchor (the anchor and its Dirichlet neighbours) is withheld together, so a
withheld composition is never seen in training. Regression is scored on feasible cases only. The Gaussian process is trained on a
random subsample of at most `gp_max` points per fold (cost grows as n^3); the subsample size is recorded."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from lng_robust.surrogate.active import feature_columns
from lng_robust.surrogate.stats import ffr_report


def make_regressors(seed, n_features):
    gp = GaussianProcessRegressor(ConstantKernel(1.0) * Matern(length_scale=np.ones(n_features), nu=2.5, length_scale_bounds=(1e-2, 1e3)) + WhiteKernel(1e-4),
                                  normalize_y=True, n_restarts_optimizer=0, random_state=seed)
    return {"linear_ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
            "gradient_boosting": GradientBoostingRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, random_state=seed),
            "gaussian_process": make_pipeline(StandardScaler(), gp)}


def make_classifiers(seed):
    return {"logistic_baseline": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
            "gradient_boosting": GradientBoostingClassifier(n_estimators=300, max_depth=4, learning_rate=0.05, random_state=seed)}


def grouped_validation(df: pd.DataFrame, mita_min: float, seed: int = 1, window_K: float = 1.0, gp_max: int = 1500):
    cols = feature_columns(df)
    X = df[cols].values
    feas = df["feasible"].values.astype(bool)
    groups = df["group"].values
    rng = np.random.default_rng(seed)
    oof = df[["group", "feed_id", "sec", "mita", "feasible", "failure_code", "numerical_failure"]].copy()
    for n in make_regressors(seed, X.shape[1]):
        oof[f"sec_{n}"] = np.nan
    for n in make_classifiers(seed):
        oof[f"feas_{n}"] = np.nan
    n_folds = 0
    for tr, te in LeaveOneGroupOut().split(X, feas, groups):
        n_folds += 1
        for name, model in make_regressors(seed, X.shape[1]).items():
            trf = tr[feas[tr]]
            if len(trf) < 10:
                continue
            if name == "gaussian_process" and len(trf) > gp_max:
                trf = rng.choice(trf, gp_max, replace=False)
            model.fit(X[trf], df["sec"].values[trf])
            oof.loc[oof.index[te], f"sec_{name}"] = model.predict(X[te])
        for name, model in make_classifiers(seed).items():
            y = feas[tr]
            if y.all() or (~y).all():
                oof.loc[oof.index[te], f"feas_{name}"] = float(y[0])
                continue
            model.fit(X[tr], y)
            oof.loc[oof.index[te], f"feas_{name}"] = model.predict(X[te]).astype(float)
    rows = []
    for name in make_regressors(seed, X.shape[1]):
        m = feas & oof[f"sec_{name}"].notna().values
        if m.sum() >= 3:
            y, p = df["sec"].values[m], oof[f"sec_{name}"].values[m]
            rows.append(dict(kind="regression", model=name, output="SEC", n=int(m.sum()), n_folds=n_folds, MAE=mean_absolute_error(y, p),
                             RMSE=math.sqrt(mean_squared_error(y, p)), R2=r2_score(y, p), unit="kWh/kg",
                             gp_subsample_max=gp_max if name == "gaussian_process" else None))
    for name in make_classifiers(seed):
        p = oof[f"feas_{name}"].values
        m = ~np.isnan(p)
        rep = ffr_report(feas[m], p[m].astype(bool), df["mita"].values[m], mita_min, window_K)
        phys = m & ~df["numerical_failure"].values
        rep_p = ffr_report(feas[phys], p[phys].astype(bool), df["mita"].values[phys], mita_min, window_K)
        rows.append(dict(kind="classification", model=name, output="feasibility", n=int(m.sum()), n_folds=n_folds, **rep,
                         **{f"physical_only_{k}": v for k, v in rep_p.items()}))
    return pd.DataFrame(rows), oof


def fit_final(df: pd.DataFrame, seed: int = 1, gp_max: int = 1500):
    """Models fitted on all data (used to propose second-stage starting points and for Sobol)."""
    cols = feature_columns(df)
    X = df[cols].values
    feas = df["feasible"].values.astype(bool)
    rng = np.random.default_rng(seed)
    regs = make_regressors(seed, X.shape[1])
    idx = np.where(feas)[0]
    for name, model in regs.items():
        sub = idx if not (name == "gaussian_process" and len(idx) > gp_max) else rng.choice(idx, gp_max, replace=False)
        model.fit(X[sub], df["sec"].values[sub])
    clfs = make_classifiers(seed)
    for model in clfs.values():
        model.fit(X, feas)
    return cols, regs, clfs
