"""Feasibility-guided sampling with active learning near the MITA boundary (manuscript Section 2.10, Phase 5).

Uniform sampling of designs finds a feasible one in 2 to 15 % of cases. Round 0 is a Latin hypercube plus a cloud around the nominal
design. Each later round fits a classifier of feasibility and a regressor of MITA on everything evaluated so far and spends the next
batch on: (a) candidates whose predicted MITA is within a window of the limit or whose feasibility probability is near 0.5
(the boundary), (b) perturbations of known feasible points, (c) candidates with high predicted feasibility and low predicted SEC,
(d) uniform exploration. All points are evaluated in the rigorous model; the surrogate only chooses where to look next."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import qmc
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

from lng_robust.doe.dirichlet import sample_dirichlet
from lng_robust.opt.common import nominal_var_names
from lng_robust.opt.parallel import get_pool
from lng_robust.opt.space import bounds, clean, decode
from lng_robust.study.store import compact_row
from lng_robust.surrogate.train import alr_features

META = ("group", "feed_id", "synthetic", "round", "sec", "mita", "feasible", "failure_code", "numerical_failure", "source")


def feature_columns(df):
    return [c for c in df.columns if c not in META]


def composition_pool(anchors, kappa, n_per_anchor, seed, basis):
    pool = list(anchors)
    for k, a in enumerate(anchors):
        pool += sample_dirichlet(a, kappa, n_per_anchor, seed + 7919 * (k + 1), basis)
    return pool


def _row_job(args):
    cycle, feed_treated, feed_id, synthetic, parent, m_lng, x, basis, rnd, source = args
    from lng_robust.cycles import solve
    r = solve(cycle, feed_treated, basis.feed_T, basis.feed_P, m_lng, x, basis)
    return compact_row(r, unit="sample", cycle=cycle, feed_id=feed_id, synthetic=synthetic, purpose=f"sampling_round{rnd}_{source}", x=x,
                       extra=dict(parent_anchor=parent or "", round=rnd, source=source)), r.feasible, r.sec, r.mita, r.failure_code


def evaluate_batch(cycle, feeds, V, feed_idx, names, m_lng, basis, rnd, source, sink, workers=None):
    tasks = []
    for v, fi in zip(V, feed_idx):
        f = feeds[fi]
        x = clean(decode(cycle, names, v, m_lng))
        tasks.append((cycle, f.treated, f.id, f.synthetic, f.parent_id, m_lng, x, basis, rnd, source))
    out = list(get_pool(workers).map(_row_job, tasks, chunksize=2)) if workers != 1 else [_row_job(t) for t in tasks]
    rows = []
    for (row, feas, sec, mita, code), v, fi in zip(out, V, feed_idx):
        f = feeds[fi]
        sink.add_rows([row])
        rows.append({**{n: float(val) for n, val in zip(names, v)},
                     **{f"alr{j}": a for j, a in enumerate(alr_features(f.treated))},
                     "group": f.parent_id or f.id, "feed_id": f.id, "synthetic": bool(f.synthetic), "round": rnd,
                     "sec": float(sec) if feas else np.nan, "mita": float(mita) if mita == mita else np.nan,
                     "feasible": bool(feas), "failure_code": code, "numerical_failure": code in ("FLASH_FAIL", "NONCONVERGED"),
                     "source": source})
    return pd.DataFrame(rows)


def _features(V, feeds, feed_idx):
    A = np.array([alr_features(feeds[i].treated) for i in feed_idx])
    return np.hstack([V, A])


def select_candidates(cycle, df, feeds, names, basis, batch, rng, mita_window=1.5, pool_size=6000, seed=1):
    lo, hi = bounds(cycle, names, basis)
    span = hi - lo
    n_b, n_l, n_x, n_e = int(0.4 * batch), int(0.3 * batch), int(0.2 * batch), 0
    n_e = batch - n_b - n_l - n_x
    P = lo + rng.random((pool_size, len(names))) * span
    Pf = rng.integers(0, len(feeds), pool_size)
    XP = _features(P, feeds, Pf)
    cols = feature_columns(df)
    feas = df["feasible"].values.astype(bool)
    chosen_V, chosen_F, chosen_src = [], [], []
    have_both = feas.sum() >= 10 and (~feas).sum() >= 10
    if have_both:
        clf = GradientBoostingClassifier(n_estimators=120, max_depth=3, random_state=seed).fit(df[cols].values, feas)
        prob = clf.predict_proba(XP)[:, 1]
        m_ok = df["mita"].notna().values
        pred_mita = None
        if m_ok.sum() >= 30:
            reg = GradientBoostingRegressor(n_estimators=120, max_depth=3, random_state=seed).fit(df.loc[m_ok, cols].values, df.loc[m_ok, "mita"].values)
            pred_mita = reg.predict(XP)
        score = np.abs(prob - 0.5) if pred_mita is None else np.minimum(np.abs(pred_mita - basis.mita_min_K) / mita_window, np.abs(prob - 0.5) * 4)
        for i in np.argsort(score)[:n_b]:
            chosen_V.append(P[i]); chosen_F.append(Pf[i]); chosen_src.append("boundary")
        sreg = None
        if feas.sum() >= 15:
            sreg = GradientBoostingRegressor(n_estimators=120, max_depth=3, random_state=seed).fit(df.loc[feas, cols].values, df.loc[feas, "sec"].values)
            ps = sreg.predict(XP)
            good = np.where(prob > 0.7)[0]
            for i in good[np.argsort(ps[good])][:n_x]:
                chosen_V.append(P[i]); chosen_F.append(Pf[i]); chosen_src.append("exploit")
    # local perturbations of feasible points (new compositions), always available once any feasible point exists
    fd = df[feas]
    if len(fd):
        for _ in range(n_l):
            row = fd.iloc[rng.integers(0, len(fd))]
            v = np.clip(row[names].values.astype(float) + rng.normal(0, 0.05, len(names)) * span, lo, hi)
            chosen_V.append(v); chosen_F.append(rng.integers(0, len(feeds))); chosen_src.append("local")
    while len(chosen_V) < batch:
        i = rng.integers(0, pool_size)
        chosen_V.append(P[i]); chosen_F.append(Pf[i]); chosen_src.append("explore")
    return np.array(chosen_V[:batch]), np.array(chosen_F[:batch]), chosen_src[:batch]


def run_active_sampling(cycle, feeds, m_lng, basis, sink, *, n0=1000, rounds=6, batch=600, centre=None, seed=1, workers=None, log=print):
    """Returns the dataset DataFrame. `centre` is the nominal design vector (in nominal_var_names order) or None."""
    names = nominal_var_names(cycle)
    lo, hi = bounds(cycle, names, basis)
    span = hi - lo
    rng = np.random.default_rng(seed)
    u = qmc.LatinHypercube(d=len(names), seed=seed).random(n0)
    V = lo + u * span
    src = ["lhs"] * n0
    if centre is not None:
        nl = n0 // 3
        loc = np.clip(np.asarray(centre, float) + rng.normal(0, 0.04, (nl, len(names))) * span, lo, hi)
        V = np.vstack([V[: n0 - nl], loc])
        src = ["lhs"] * (n0 - nl) + ["nominal_cloud"] * nl
    fi = rng.integers(0, len(feeds), len(V))
    parts = []
    for s_name in sorted(set(src)):
        m = np.array(src) == s_name
        parts.append(evaluate_batch(cycle, feeds, V[m], fi[m], names, m_lng, basis, 0, s_name, sink, workers))
    df = pd.concat(parts, ignore_index=True)
    sink.flush()
    log(f"[sample {cycle}] round 0: {len(df)} evals, {int(df.feasible.sum())} feasible")
    for r in range(1, rounds + 1):
        Vn, Fn, srcs = select_candidates(cycle, df, feeds, names, basis, batch, rng, seed=seed + r)
        dfs = []
        for s_name in sorted(set(srcs)):
            m = np.array(srcs) == s_name
            dfs.append(evaluate_batch(cycle, feeds, Vn[m], Fn[m], names, m_lng, basis, r, s_name, sink, workers))
        df = pd.concat([df] + dfs, ignore_index=True)
        sink.flush()
        log(f"[sample {cycle}] round {r}: total {len(df)}, feasible {int(df.feasible.sum())}")
    return df
