"""Small elitist real-coded GA with an explicit, serialisable state, so the outer robust search can stop after any generation
and resume in another job. Constraint handling by feasibility rules (Deb): feasible beats infeasible; two infeasible individuals are
ranked by constraint violation; two feasible ones by objective. Deterministic given the seed stored in the state."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np


@dataclass
class GAState:
    gen: int
    X: np.ndarray                 # (pop, d)
    F: np.ndarray                 # (pop,) objective (nan = not evaluated)
    CV: np.ndarray                # (pop,) constraint violation >= 0
    rng_state: dict
    seed: int
    lo: np.ndarray
    hi: np.ndarray
    history: list = field(default_factory=list)      # per generation: best feasible F, best CV, n_feasible

    def to_json(self) -> str:
        return json.dumps(dict(gen=self.gen, X=self.X.tolist(), F=self.F.tolist(), CV=self.CV.tolist(), rng_state=self.rng_state,
                               seed=self.seed, lo=self.lo.tolist(), hi=self.hi.tolist(), history=self.history))

    @staticmethod
    def from_json(s: str) -> "GAState":
        d = json.loads(s)
        return GAState(d["gen"], np.array(d["X"], float), np.array(d["F"], float), np.array(d["CV"], float), d["rng_state"], d["seed"],
                       np.array(d["lo"], float), np.array(d["hi"], float), d["history"])


def _rng(state: GAState):
    g = np.random.default_rng(state.seed)
    g.bit_generator.state = state.rng_state
    return g


def init_state(seed_vecs, lo, hi, pop: int, seed: int) -> GAState:
    rng = np.random.default_rng(seed)
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    X = [np.clip(np.asarray(v, float), lo, hi) for v in seed_vecs][:pop]
    while len(X) < pop:
        X.append(lo + rng.random(len(lo)) * (hi - lo))
    return GAState(-1, np.array(X), np.full(pop, np.nan), np.full(pop, np.inf), rng.bit_generator.state, seed, lo, hi, [])


def better(Fa, CVa, Fb, CVb) -> bool:
    """True if a is preferred to b under the feasibility rules."""
    fa, fb = CVa <= 0, CVb <= 0
    if fa and fb:
        return Fa < Fb
    if fa != fb:
        return fa
    return CVa < CVb


def _tournament(state, rng, k=2):
    idx = rng.integers(0, len(state.X), k)
    best = idx[0]
    for i in idx[1:]:
        if better(state.F[i], state.CV[i], state.F[best], state.CV[best]):
            best = i
    return best


def offspring(state: GAState, n: int, rng, blx=0.3, p_mut=None, sigma=0.08):
    d = state.X.shape[1]
    p_mut = 1.0 / d if p_mut is None else p_mut
    span = state.hi - state.lo
    out = []
    for _ in range(n):
        a, b = state.X[_tournament(state, rng)], state.X[_tournament(state, rng)]
        lo_, hi_ = np.minimum(a, b), np.maximum(a, b)
        ext = blx * (hi_ - lo_)
        child = (lo_ - ext) + rng.random(d) * ((hi_ + ext) - (lo_ - ext))
        m = rng.random(d) < p_mut
        child = child + m * rng.normal(0.0, sigma, d) * span
        out.append(np.clip(child, state.lo, state.hi))
    return np.array(out)


def survive(X, F, CV, pop: int):
    order = sorted(range(len(X)), key=lambda i: (0 if CV[i] <= 0 else 1, F[i] if CV[i] <= 0 else CV[i]))
    keep = order[:pop]
    return X[keep], F[keep], CV[keep]


def advance(state: GAState, evaluate) -> GAState:
    """One generation. evaluate(X) -> (F, CV) arrays. Generation 0 evaluates the initial population."""
    rng = _rng(state)
    if state.gen < 0:
        F, CV = evaluate(state.X)
        state.F, state.CV, state.gen = np.asarray(F, float), np.asarray(CV, float), 0
    else:
        pop = len(state.X)
        C = offspring(state, pop, rng)
        F, CV = evaluate(C)
        X, F2, CV2 = survive(np.vstack([state.X, C]), np.concatenate([state.F, F]), np.concatenate([state.CV, CV]), pop)
        state.X, state.F, state.CV, state.gen = X, F2, CV2, state.gen + 1
    feas = state.CV <= 0
    state.history.append(dict(gen=state.gen, best_feasible_F=float(state.F[feas].min()) if feas.any() else None,
                              best_CV=float(state.CV.min()), n_feasible=int(feas.sum())))
    state.rng_state = rng.bit_generator.state
    return state


def best(state: GAState):
    i = min(range(len(state.X)), key=lambda j: (0 if state.CV[j] <= 0 else 1, state.F[j] if state.CV[j] <= 0 else state.CV[j]))
    return i
