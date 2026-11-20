"""Phase 4: kappa selection, nominal composition and the scenario set.

kappa (Dirichlet concentration). For every major treated-feed component c (C1, C2, C3, N2) with anchor mean m_c and
between-anchor spread s_c, matching the synthetic spread sqrt(m(1-m)/(kappa+1)) to s_c gives kappa_c = m_c(1-m_c)/s_c^2 - 1.
s_c is the robust spread 1.4826 * MAD, so one outlying anchor (Field D, 46 mol% N2) does not dictate the answer.
kappa = median over c of kappa_c. The method and every kappa_c are recorded.

Nominal composition: the anchor closest (Euclidean, treated mole fractions of the major components) to the mean of the anchors.
Scenario set: all anchors (synthetic=False) plus synthetic Dirichlet samples centred on each anchor in turn, to S in total."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from lng_robust.doe.dirichlet import sample_dirichlet
from lng_robust.doe.feeds import Feed

MAJOR = ["C1", "C2", "C3", "N2"]


def _vec(f: Feed):
    return np.array([f.treated.get(c, 0.0) for c in MAJOR])


def choose_kappa_robust(anchors: list[Feed]):
    X = np.array([_vec(a) for a in anchors])
    mean = X.mean(0)
    med = np.median(X, 0)
    mad = np.median(np.abs(X - med), 0) * 1.4826
    kc = {}
    for j, c in enumerate(MAJOR):
        s = mad[j]
        kc[c] = float(mean[j] * (1 - mean[j]) / s ** 2 - 1.0) if s > 0 else float("nan")
    kappa = float(np.nanmedian(list(kc.values())))
    return kappa, dict(method="median over C1,C2,C3,N2 of m(1-m)/s^2 - 1, s = 1.4826*MAD across anchors", kappa_by_component=kc,
                       anchor_mean=dict(zip(MAJOR, mean.tolist())), anchor_robust_sd=dict(zip(MAJOR, mad.tolist())), n_anchors=len(anchors))


def choose_nominal(anchors: list[Feed]):
    X = np.array([_vec(a) for a in anchors])
    d = np.linalg.norm(X - X.mean(0), axis=1)
    i = int(np.argmin(d))
    return anchors[i], dict(nominal=anchors[i].id, distance_to_mean=d.tolist(), anchor_ids=[a.id for a in anchors],
                            reason="closest (Euclidean, treated mole fractions of C1, C2, C3, N2) to the anchor mean")


def build_scenarios(anchors: list[Feed], S: int, kappa: float, seed: int, basis, exclude_ids=()):
    use = [a for a in anchors if a.id not in exclude_ids]
    n_syn = S - len(use)
    per = [n_syn // len(use) + (1 if i < n_syn % len(use) else 0) for i in range(len(use))]
    scen = list(use)
    for k, (a, n) in enumerate(zip(use, per)):
        if n > 0:
            scen += sample_dirichlet(a, kappa, n, seed + 1000 * (k + 1), basis)
    return scen


def save_scenarios(scen: list[Feed], path: Path):
    rows = []
    for f in scen:
        rows.append(dict(id=f.id, synthetic=f.synthetic, parent_anchor=f.parent_id, kappa=f.kappa, grade=f.grade, source=f.source,
                         **{f"treated_{k}": v for k, v in sorted(f.treated.items())}))
    pd.DataFrame(rows).to_csv(path, index=False)
