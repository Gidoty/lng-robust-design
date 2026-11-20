"""Nominal design: NSGA-II (pymoo) on SEC and specific UA for the nominal feed, subject to feasibility.

The initial population is the best of a random screen (3x population, feasibility first, then violation),
so a population of all-infeasible designs does not stall the search. Every evaluation is logged."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize

from lng_robust.opt.common import knee_point, nominal_var_names
from lng_robust.opt.parallel import map_eval
from lng_robust.opt.space import bounds, clean, decode

SEC_FAIL, UA_FAIL = 5.0, 1.0e4


@dataclass
class NominalResult:
    cycle: str
    names: list
    best: dict | None                     # selected (knee) design, or None if nothing feasible was found
    front: list = field(default_factory=list)
    n_evals: int = 0
    feasible_found: bool = False
    note: str = ""


class _Problem(Problem):
    def __init__(self, cycle, feed, feed_id, m_lng, basis, names, log, workers, capacity_tpd, purpose="nominal_nsga2"):
        lo, hi = bounds(cycle, names, basis)
        super().__init__(n_var=len(names), n_obj=2, n_ieq_constr=1, xl=lo, xu=hi)
        self.cycle, self.feed, self.feed_id, self.m_lng, self.basis = cycle, feed, feed_id, m_lng, basis
        self.names, self.log, self.workers, self.capacity, self.purpose = names, log, workers, capacity_tpd, purpose
        self.n_evals = 0
        self.last = []

    def evaluate_vectors(self, X, purpose=None):
        xs = [clean(decode(self.cycle, self.names, v, self.m_lng)) for v in X]
        tasks = [(self.cycle, self.feed, self.basis.feed_T, self.basis.feed_P, self.m_lng, x, self.basis) for x in xs]
        R = map_eval(tasks, self.workers)
        self.n_evals += len(R)
        for x, r in zip(xs, R):
            if self.log is not None:
                self.log.add(r, cycle=self.cycle, feed_id=self.feed_id, synthetic=False, parent_id=None, kappa=None,
                             capacity_tpd=self.capacity, stage1={k: v for k, v in x.items() if k == "ref"},
                             stage2={k: v for k, v in x.items() if k != "ref"}, purpose=purpose or self.purpose,
                             composition=self.feed)
        return xs, R

    def _evaluate(self, X, out, *args, **kwargs):
        xs, R = self.evaluate_vectors(X)
        F = np.array([[r.sec if (r.sec == r.sec and r.feasible) else SEC_FAIL,
                       (r.ua / self.m_lng) if (r.ua == r.ua and r.feasible) else UA_FAIL] for r in R])
        G = np.array([[r.violation] for r in R])
        out["F"], out["G"] = F, G
        self.last = R


def run_nominal(cycle, feed, feed_id, m_lng, basis, *, pop=20, n_gen=10, seed=1, log=None, workers=None,
                capacity_tpd=100, screen_factor=3) -> NominalResult:
    names = nominal_var_names(cycle)
    prob = _Problem(cycle, feed, feed_id, m_lng, basis, names, log, workers, capacity_tpd)
    rng = np.random.default_rng(seed)
    cand = prob.xl + rng.random((screen_factor * pop, len(names))) * (prob.xu - prob.xl)
    xs, R = prob.evaluate_vectors(cand, purpose="nominal_initial_screen")
    order = sorted(range(len(R)), key=lambda i: (0 if R[i].feasible else 1, R[i].violation, R[i].sec if R[i].sec == R[i].sec else 9))
    X0 = cand[order[:pop]]
    algo = NSGA2(pop_size=pop, sampling=X0)
    res = minimize(prob, algo, ("n_gen", n_gen), seed=seed, verbose=False)
    n_evals = prob.n_evals
    feas = res.CV is not None and np.any(np.asarray(res.CV).reshape(-1) <= 0)
    if res.X is None or not feas:
        return NominalResult(cycle, names, None, [], n_evals, False,
                             "no feasible design found within the budget (least-violating designs are in the log)")
    X = np.atleast_2d(res.X)
    F = np.atleast_2d(res.F)
    ok = np.asarray(res.CV).reshape(-1) <= 0
    X, F = X[ok], F[ok]
    k = knee_point(F)
    front = []
    for v, f in zip(X, F):
        front.append(dict(vec=v.tolist(), sec=float(f[0]), ua_spec=float(f[1])))
    # re-verify the selected design in the rigorous model (it is already rigorous here; kept for symmetry with surrogate paths)
    xs, R2 = prob.evaluate_vectors(X[k:k + 1], purpose="nominal_selected_reverify")
    r = R2[0]
    best = dict(vec=X[k].tolist(), x=xs[0], sec=r.sec, ua_spec=r.ua / m_lng, mita=r.mita, feasible=r.feasible,
                n_ref=r.n_ref, ref=xs[0].get("ref"), result=r)
    return NominalResult(cycle, names, best, front, prob.n_evals, bool(r.feasible),
                         "" if r.feasible else "selected design failed re-verification")
