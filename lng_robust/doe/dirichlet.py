"""Synthetic feed scenarios on the compositional simplex: z ~ Dir(kappa * z_anchor).

Every sampled composition carries synthetic=True and its parent anchor id. Zero components of the anchor
stay zero (their Dirichlet parameter would be zero)."""
from __future__ import annotations

import numpy as np

from lng_robust.doe.feeds import Feed, make_sim_feed


def sample_dirichlet(anchor: Feed, kappa: float, n: int, seed: int, basis) -> list[Feed]:
    rng = np.random.default_rng(seed)
    base = {k: v for k, v in anchor.sim_raw.items() if v and v > 0}
    names = list(base)
    p = np.array([base[k] for k in names], float)
    p = p / p.sum()
    out = []
    for i in range(n):
        z = rng.dirichlet(kappa * p)
        raw = {k: 100.0 * float(v) for k, v in zip(names, z)}
        sim, treated, notes = make_sim_feed(raw, basis)    # same pretreatment spec as every feed
        out.append(Feed(id=f"S-{anchor.id}-{i+1:03d}", facility="SYNTHETIC", source=f"Dirichlet(kappa={kappa}) around {anchor.id}",
                        grade="synthetic", raw_mol_pct=raw, raw_sum=100.0, unassigned_pct=0.0, synthetic=True,
                        parent_id=anchor.id, kappa=kappa, notes="synthetic composition, not a measurement",
                        treated=treated, pretreat_notes=notes, sim_raw=sim))
    return out


def choose_kappa(anchors: list[Feed], component: str = "C1", coverage_z: float = 1.96, default: float = 200.0):
    """kappa such that the +/- coverage_z interval of `component` spans the observed range across anchors.
    Needs at least two anchors; with fewer, returns (default, 'DEFAULT_PLACEHOLDER')."""
    vals = [a.sim_raw.get(component) for a in anchors if a.sim_raw.get(component) is not None]
    if len(vals) < 2:
        return default, "DEFAULT_PLACEHOLDER (fewer than two anchors; author must set kappa from the full register)"
    zbar = float(np.mean(vals)) / 100.0
    rng_ = (max(vals) - min(vals)) / 100.0
    sd = rng_ / (2 * coverage_z)
    return zbar * (1 - zbar) / sd ** 2 - 1.0, "from anchor range"
