"""Surrogate screening of second-stage starting points (decision D6). The surrogate proposes where the rigorous gradient solver
starts; the value accepted for a scenario is always the rigorous one."""
from __future__ import annotations

import numpy as np

from lng_robust.opt.space import STAGE2, bounds
from lng_robust.opt.common import nominal_var_names
from lng_robust.surrogate.train import alr_features


class StartSelector:
    def __init__(self, cycle, cols, reg, clf, basis, seed=1):
        self.cycle, self.cols, self.reg, self.clf, self.basis, self.seed = cycle, cols, reg, clf, basis, seed
        self.names = nominal_var_names(cycle)
        self.lo, self.hi = bounds(cycle, self.names, basis)

    def starts(self, treated: dict, x1: dict, k: int = 3, pool: int = 1500, salt: int = 0):
        rng = np.random.default_rng(self.seed + salt)
        V = self.lo + rng.random((pool, len(self.names))) * (self.hi - self.lo)
        if self.cycle == "smr" and x1.get("ref"):
            for j, n in enumerate(self.names):
                if n.startswith("w_"):
                    V[:, j] = x1["ref"].get(n[2:], 0.0)        # refrigerant weights are first stage: fixed by the design
        X = np.hstack([V, np.tile(alr_features(treated), (pool, 1))])
        prob = self.clf.predict_proba(X)[:, 1]
        sec = self.reg.predict(X)
        order = np.lexsort((sec, (prob <= 0.5).astype(int)))   # predicted-feasible first, then lowest predicted SEC
        idx = order[:k]
        y_idx = [self.names.index(n) for n in STAGE2[self.cycle]]
        return [V[i][y_idx] for i in idx]
