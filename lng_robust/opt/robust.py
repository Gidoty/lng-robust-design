"""Two-stage risk-averse design.

First stage x (fixed across scenarios): SMR refrigerant weights + UA; nitrogen cycles UA + rated flow.
Second stage y_s (re-optimised for every scenario s with x fixed): pressures, flows, temperatures.
  SEC_s(x) = min_y SEC(x, y, z_s)  s.t. every feasibility condition, UA_req <= UA_installed, flow <= rated.
A scenario with no feasible y_s gets SEC_pen and counts as infeasible.
Outer problem: minimise CVaR_alpha over x  s.t. feasible fraction >= 0.95 and UA_installed <= budget.
(`risk="worst"` minimises max_s SEC_s instead, as the bound described in the manuscript.)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from scipy.optimize import minimize as sp_minimize

from lng_robust.cycles import solve
from lng_robust.opt.common import cvar, nominal_var_names, penalised_sec
from lng_robust.opt.parallel import get_pool
from lng_robust.opt.space import STAGE1, STAGE2, bounds, clean, decode


def inner_solve(args):
    """Second-stage re-optimisation for one scenario (runs in a worker). Returns best result + every evaluation."""
    cycle, feed, m_lng, x1, y0, y_lo, y_hi, basis, maxfev, seed = args
    names2 = STAGE2[cycle]
    allres = []
    best = {"res": None, "y": None}
    span = y_hi - y_lo

    def to_y(u):
        return y_lo + np.clip(u, 0.0, 1.0) * span

    def f(u):
        y = to_y(u)
        x = dict(x1)
        x.update({n: float(v) for n, v in zip(names2, y)})
        r = solve(cycle, feed, basis.feed_T, basis.feed_P, m_lng, x, basis)
        r.__dict__.pop("_mshe", None)
        allres.append((x, r))
        if r.feasible and (best["res"] is None or r.sec < best["res"].sec):
            best["res"], best["y"] = r, y.copy()
        # penalised objective drives the simplex towards feasibility; SEC is in kWh/kg (~0.3-1), violation is O(1)
        base = r.sec if (r.sec == r.sec) else 1.5
        return base + 20.0 * r.violation

    u0 = np.clip((np.asarray(y0, float) - y_lo) / span, 0.0, 1.0)
    sp_minimize(f, u0, method="Nelder-Mead", options=dict(maxfev=maxfev, xatol=1e-4, fatol=1e-6, initial_simplex=_simplex(u0, seed)))
    return best["res"], best["y"], allres


def _simplex(u0, seed, step=0.08):
    n = len(u0)
    S = np.vstack([u0] + [np.clip(u0 + step * np.eye(n)[i] * (1 if u0[i] < 0.9 else -1), 0, 1) for i in range(n)])
    return S


@dataclass
class RobustResult:
    cycle: str
    risk: str
    feasible_design: bool
    x1: dict | None
    stage1_vec: list | None
    cvar: float = float("nan")
    worst: float = float("nan")
    feasible_fraction: float = float("nan")
    sec_by_scenario: list = field(default_factory=list)
    n_outer_evals: int = 0
    n_rigorous_evals: int = 0
    note: str = ""


def stage1_vec_of_design(cycle, design, m_lng):
    """Stage-1 vector (equipment) implied by a nominal design: its refrigerant composition, UA and rated flow."""
    names1 = stage1_names(cycle)
    v = np.zeros(len(names1))
    for i, n in enumerate(names1):
        if n.startswith("w_"):
            v[i] = (design["x"].get("ref") or {}).get(n[2:], 0.0)
        elif n == "ua_spec":
            v[i] = design["ua_spec"] * (1 + 1e-6)
        elif n == "n_rated_spec":
            v[i] = design["n_ref"] / m_lng * (1 + 1e-6)
    return v


def stage1_names(cycle):
    return STAGE1[cycle]


def x1_from_vec(cycle, vec, m_lng):
    names = stage1_names(cycle)
    x = decode(cycle, names, vec, m_lng, with_equipment=True)
    return clean_stage1(x)


def clean_stage1(x):
    return {k: v for k, v in x.items() if not k.startswith("_")}


def evaluate_scenarios(cycle, scen_feeds, m_lng, x1, y0, basis, maxfev, workers=None, seed=1, log=None, capacity_tpd=100,
                       purpose="robust_inner"):
    """Second-stage re-optimisation over every scenario. Returns (sec_s array with penalties, feasible mask, bests)."""
    y_lo, y_hi = bounds(cycle, STAGE2[cycle], basis)
    tasks = [(cycle, f.treated, m_lng, x1, y0, y_lo, y_hi, basis, maxfev, seed) for f in scen_feeds]
    pool = get_pool(workers)
    out = list(pool.map(inner_solve, tasks, chunksize=1)) if (workers or 2) != 1 else [inner_solve(t) for t in tasks]
    sec = np.array([penalised_sec(r, basis.sec_penalty_kwh_per_kg) if r is not None else basis.sec_penalty_kwh_per_kg for r, _, _ in out])
    feas = np.array([r is not None for r, _, _ in out])
    n_eval = sum(len(a) for _, _, a in out)
    if log is not None:
        for f, (_, _, allres) in zip(scen_feeds, out):
            for x, r in allres:          # every second-stage evaluation is logged, feasible or not
                log.add(r, cycle=cycle, feed_id=f.id, synthetic=f.synthetic, parent_id=f.parent_id, kappa=f.kappa,
                        capacity_tpd=capacity_tpd, stage1={k: v for k, v in x1.items()},
                        stage2={k: v for k, v in x.items() if k in STAGE2[cycle]}, purpose=purpose, composition=f.treated)
    return sec, feas, out, n_eval


class _Outer(Problem):
    def __init__(self, cycle, scen, m_lng, basis, y0, lo, hi, maxfev, workers, risk, log, capacity_tpd):
        super().__init__(n_var=len(lo), n_obj=1, n_ieq_constr=1, xl=lo, xu=hi)
        self.cycle, self.scen, self.m_lng, self.basis, self.y0 = cycle, scen, m_lng, basis, y0
        self.maxfev, self.workers, self.risk, self.log, self.capacity = maxfev, workers, risk, log, capacity_tpd
        self.n_outer = 0
        self.n_rigorous = 0
        self.cache = {}

    def _evaluate(self, X, out, *args, **kwargs):
        F, G = [], []
        for v in X:
            x1 = x1_from_vec(self.cycle, v, self.m_lng)
            sec, feas, _, n = evaluate_scenarios(self.cycle, self.scen, self.m_lng, x1, self.y0, self.basis, self.maxfev,
                                                 self.workers, log=self.log, capacity_tpd=self.capacity)
            self.n_outer += 1
            self.n_rigorous += n
            obj = cvar(sec, self.basis.cvar_alpha) if self.risk == "cvar" else float(sec.max())
            F.append([obj])
            G.append([self.basis.chance_feasible_fraction - feas.mean()])
        out["F"], out["G"] = np.array(F), np.array(G)


def run_robust(cycle, scen_feeds, m_lng, basis, nominal_best, *, risk="cvar", pop=4, n_gen=2, maxfev=10, seed=1,
               workers=None, log=None, capacity_tpd=100, ua_budget_factor=None) -> RobustResult:
    """Outer search over stage-1 variables. nominal_best supplies the warm start and the UA budget."""
    names1 = stage1_names(cycle)
    lo, hi = bounds(cycle, names1, basis)
    names_nom = nominal_var_names(cycle)
    y0 = np.array([nominal_best["vec"][names_nom.index(n)] for n in STAGE2[cycle]])
    ua_nom = nominal_best["ua_spec"]
    f = basis.ua_budget_factor if ua_budget_factor is None else ua_budget_factor
    hi = hi.copy()
    iua = names1.index("ua_spec")
    hi[iua] = min(hi[iua], ua_nom * f * (1 + 1e-6))
    lo = np.minimum(lo, hi)
    seed_vec = stage1_vec_of_design(cycle, nominal_best, m_lng)
    seed_vec = np.clip(seed_vec, lo, hi)
    prob = _Outer(cycle, scen_feeds, m_lng, basis, y0, lo, hi, maxfev, workers, risk, log, capacity_tpd)
    rng = np.random.default_rng(seed)
    X0 = np.vstack([seed_vec] + [lo + rng.random(len(lo)) * (hi - lo) for _ in range(pop - 1)])
    algo = GA(pop_size=pop, sampling=X0, eliminate_duplicates=True)
    res = minimize(prob, algo, ("n_gen", n_gen), seed=seed, verbose=False)
    if res.X is None:        # pymoo returns no optimum when nothing satisfied the chance constraint: take the least-violating individual
        pop = res.pop
        v = np.atleast_1d(pop.get("X")[int(np.argmin(pop.get("CV").reshape(-1)))])
    else:
        v = np.atleast_1d(res.X)
    x1 = x1_from_vec(cycle, v, m_lng)
    sec, feas, _, n = evaluate_scenarios(cycle, scen_feeds, m_lng, x1, y0, basis, maxfev, workers, log=log,
                                         capacity_tpd=capacity_tpd, purpose="robust_final_reverify")
    ok = float(feas.mean()) >= basis.chance_feasible_fraction
    return RobustResult(cycle=cycle, risk=risk, feasible_design=bool(ok), x1=x1, stage1_vec=v.tolist(),
                        cvar=cvar(sec, basis.cvar_alpha), worst=float(sec.max()), feasible_fraction=float(feas.mean()),
                        sec_by_scenario=sec.tolist(), n_outer_evals=prob.n_outer, n_rigorous_evals=prob.n_rigorous + n,
                        note="" if ok else "chance constraint not met within the budget; least-violating design reported")
