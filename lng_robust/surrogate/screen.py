"""Surrogate-assisted screening of candidate designs. Every selected candidate is re-run in the rigorous model
and BOTH values (surrogate and rigorous) are recorded, including any feasibility disagreement."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lng_robust.opt.common import nominal_var_names
from lng_robust.opt.parallel import map_eval
from lng_robust.opt.space import bounds, clean, decode
from lng_robust.surrogate.train import alr_features, classifiers, feature_cols, regressors, _fit_gp_iso


def screen_and_reverify(cycle, df_train, feed, feed_id, m_lng, basis, *, n_candidates=2000, top_k=5, seed=1, log=None,
                        workers=None, capacity_tpd=100):
    names = nominal_var_names(cycle)
    cols = feature_cols(df_train)
    X = df_train[cols].values
    feas = df_train["feasible"].values.astype(bool)
    reg = regressors(seed)["gradient_boosting"]
    clf = classifiers(seed)["gradient_boosting"]
    if feas.sum() < 5 or feas.all() or (~feas).all():
        return pd.DataFrame(), "surrogate not trainable (too few feasible or infeasible cases)"
    reg.fit(X[feas], df_train["sec"].values[feas])
    clf.fit(X, feas)
    lo, hi = bounds(cycle, names, basis)
    rng = np.random.default_rng(seed + 7)
    V = lo + rng.random((n_candidates, len(names))) * (hi - lo)
    alr = np.tile(alr_features(feed), (n_candidates, 1))
    Xc = np.hstack([V, alr])
    pf = clf.predict(Xc).astype(bool)
    ps = reg.predict(Xc)
    idx = [i for i in np.argsort(ps) if pf[i]][:top_k]
    if not idx:
        return pd.DataFrame(), "no candidate predicted feasible"
    xs = [clean(decode(cycle, names, V[i], m_lng)) for i in idx]
    R = map_eval([(cycle, feed, basis.feed_T, basis.feed_P, m_lng, x, basis) for x in xs], workers)
    rows = []
    for i, x, r in zip(idx, xs, R):
        if log is not None:
            log.add(r, cycle=cycle, feed_id=feed_id, synthetic=False, parent_id=None, kappa=None, capacity_tpd=capacity_tpd,
                    stage1={"ref": x.get("ref")}, stage2={k: v for k, v in x.items() if k != "ref"},
                    purpose="surrogate_selected_reverify", composition=feed)
        rows.append(dict(cycle=cycle, candidate=int(i), surrogate_sec=float(ps[i]), surrogate_pred_feasible=bool(pf[i]),
                         rigorous_sec=float(r.sec) if r.feasible else np.nan, rigorous_feasible=bool(r.feasible),
                         rigorous_failure_codes=";".join(r.failure_codes), rigorous_mita=r.mita,
                         abs_sec_difference=abs(float(r.sec) - float(ps[i])) if r.feasible else np.nan,
                         feasibility_disagreement=bool(pf[i]) != bool(r.feasible)))
    return pd.DataFrame(rows), ""
