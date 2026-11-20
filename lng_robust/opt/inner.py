"""Second-stage (operating) solvers for one scenario with the equipment (stage 1) fixed.

solve_slsqp   gradient-based local solver (SciPy SLSQP) on the scaled operating variables, with smooth inequality constraints
              built from the rigorous model: MITA margin, installed-UA margin, rated-flow margin, suction margin.
              Warm start from a given point (the nearest solved scenario), plus `n_restarts` random restarts.
solve_nelder_mead   the earlier derivative-free method (kept as the baseline of the efficiency comparison).

Every rigorous evaluation of either method is returned (and logged by the caller). A solution is accepted only if the rigorous
model marks it feasible; nothing here uses a surrogate."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize as sp_minimize

from lng_robust.cycles import solve
from lng_robust.opt.space import STAGE2

SEC_PEN_FALLBACK = 2.0
FD_STEP = 2e-3          # SLSQP forward-difference step in scaled units (span-normalised)
CHANGE_CAP = 0.15       # max predicted change of a normalised constraint per TR-SLP step
TR_FD_STEP = 1e-2       # TR-SLP finite-difference step: MITA moves only ~0.01 K over 2e-3, so a larger step is needed for a usable gradient


@dataclass
class InnerResult:
    best_res: object | None
    best_y: np.ndarray | None
    evals: list = field(default_factory=list)       # [(x dict, CycleResult)] every rigorous evaluation
    n_evals: int = 0
    method: str = ""
    n_restarts_used: int = 0
    start_used: str = ""


class _Evaluator:
    def __init__(self, cycle, feed, m_lng, x1, y_lo, y_hi, basis, max_evals):
        self.cycle, self.feed, self.m_lng, self.x1, self.basis = cycle, feed, m_lng, x1, basis
        self.y_lo, self.span, self.names = y_lo, y_hi - y_lo, STAGE2[cycle]
        self.cache: dict = {}
        self.evals: list = []
        self.best = None
        self.best_y = None
        self.max_evals = max_evals
        self.ua_inst = x1.get("ua_installed_kw_per_K")
        self.n_rated = x1.get("n_ref_rated_mol_s")

    def to_y(self, u):
        return self.y_lo + np.clip(u, 0.0, 1.0) * self.span

    def run(self, u):
        u = np.clip(np.asarray(u, float), 0.0, 1.0)
        key = tuple(np.round(u, 12))
        if key in self.cache:
            return self.cache[key]
        if len(self.evals) >= self.max_evals:
            raise _Budget()
        y = self.to_y(u)
        x = dict(self.x1)
        x.update({n: float(v) for n, v in zip(self.names, y)})
        r = solve(self.cycle, self.feed, self.basis.feed_T, self.basis.feed_P, self.m_lng, x, self.basis)
        r.__dict__.pop("_mshe", None)
        self.evals.append((x, r))
        if r.feasible and (self.best is None or r.sec < self.best.sec):
            self.best, self.best_y = r, y.copy()
        self.cache[key] = r
        return r

    def objective(self, u):
        r = self.run(u)
        return float(r.sec) if r.sec == r.sec else SEC_PEN_FALLBACK + r.violation

    def constraints(self, u):
        """All entries >= 0 when feasible. Smooth in the interior; a hard failure returns -(violation)."""
        r = self.run(u)
        b = self.basis
        if not (r.mita == r.mita and r.sec == r.sec and r.ua == r.ua):      # incl. TEMP_CROSS: no UA, nonsmooth beyond the cross
            return np.full(4, -(1.0 + r.violation))
        c0 = (r.mita - b.mita_min_K) / b.mita_min_K
        c1 = (1.0 - r.ua / self.ua_inst) if (self.ua_inst and r.ua == r.ua) else -1.0 - (r.violation or 0.0)
        c2 = (1.0 - r.n_ref / self.n_rated) if self.n_rated else 1.0
        c3 = (r.details.get("min_superheat_K", 10.0) - b.min_suction_superheat_K) / 10.0
        return np.array([c0, c1, c2, c3])


class _Budget(Exception):
    pass


def _slsqp_from(ev: _Evaluator, u0, maxiter, box=None):
    try:
        bnds = [(0.0, 1.0)] * len(u0) if box is None else [(max(0.0, v - box), min(1.0, v + box)) for v in u0]
        sp_minimize(ev.objective, u0, method="SLSQP", bounds=bnds,
                    constraints=[dict(type="ineq", fun=ev.constraints)],
                    options=dict(maxiter=maxiter, ftol=1e-7, eps=FD_STEP))
    except _Budget:
        pass


def solve_slsqp(cycle, feed, m_lng, x1, y0, y_lo, y_hi, basis, *, max_evals=60, n_restarts=3, seed=1, maxiter=12,
                start_label="warm", extra_starts=None) -> InnerResult:
    """extra_starts: optional list of y-vectors (e.g. screened by a surrogate) used as the restart points instead of random jitter.
    The surrogate only proposes starting points; every accepted value comes from the rigorous model."""
    ev = _Evaluator(cycle, feed, m_lng, x1, y_lo, y_hi, basis, max_evals)
    span = y_hi - y_lo
    u0 = np.clip((np.asarray(y0, float) - y_lo) / span, 0.0, 1.0)
    rng = np.random.default_rng(seed)
    _slsqp_from(ev, u0, maxiter)
    used = 0
    # restarts: random points, run only while the budget lasts. Each restart is a full local solve.
    for k in range(n_restarts):
        if len(ev.evals) >= ev.max_evals:
            break
        used += 1
        if extra_starts is not None and k < len(extra_starts):
            u_k = np.clip((np.asarray(extra_starts[k], float) - y_lo) / span, 0.0, 1.0)
        else:
            u_k = np.clip(u0 + 0.25 * (rng.random(len(u0)) - 0.5), 0, 1)
        _slsqp_from(ev, u_k, maxiter)
    return InnerResult(ev.best, ev.best_y, ev.evals, len(ev.evals), "slsqp", used, start_label)


def _simplex(u0, step=0.08):
    n = len(u0)
    return np.vstack([u0] + [np.clip(u0 + step * np.eye(n)[i] * (1 if u0[i] < 0.9 else -1), 0, 1) for i in range(n)])


def solve_nelder_mead(cycle, feed, m_lng, x1, y0, y_lo, y_hi, basis, *, maxfev=16) -> InnerResult:
    """The earlier second-stage method (penalised Nelder-Mead). Same evaluation bookkeeping as solve_slsqp."""
    ev = _Evaluator(cycle, feed, m_lng, x1, y_lo, y_hi, basis, 10 ** 9)
    span = y_hi - y_lo
    u0 = np.clip((np.asarray(y0, float) - y_lo) / span, 0.0, 1.0)

    def f(u):
        r = ev.run(u)
        base = r.sec if (r.sec == r.sec) else 1.5
        return base + 20.0 * r.violation

    sp_minimize(f, u0, method="Nelder-Mead", options=dict(maxfev=maxfev, xatol=1e-4, fatol=1e-6, initial_simplex=_simplex(u0)))
    return InnerResult(ev.best, ev.best_y, ev.evals, len(ev.evals), "nelder_mead", 0, "nominal")


# ---------------------------------------------------------------------------------------------------------------------
# Trust-region sequential linear programming with an elastic (exact-penalty) constraint treatment and Broyden updates.
# Added after the SLSQP comparison (runs/inner_solver_comparison.csv): SLSQP took unbounded first steps from infeasible starts and
# landed in TEMP_CROSS regions, so it found no feasible point in many scenarios. A trust region rejects such steps.
# ---------------------------------------------------------------------------------------------------------------------
from scipy.optimize import linprog  # noqa: E402


def _fc(ev: _Evaluator, u):
    return ev.objective(u), ev.constraints(u)


def _merit(f, c, mu):
    return f + mu * float(np.maximum(0.0, -c).sum())


def _tr_slp_from(ev: _Evaluator, u0, *, delta0=0.04, mu=3.0, tol=2e-6, min_delta=4e-3, max_iter=60):
    n = len(u0)
    u = np.clip(u0, 0.0, 1.0)
    fk, ck = _fc(ev, u)
    m = len(ck)
    g = np.zeros(n)
    J = np.zeros((m, n))
    for i in range(n):                          # initial finite-difference model
        h = TR_FD_STEP if u[i] + TR_FD_STEP <= 1.0 else -TR_FD_STEP
        ui = u.copy()
        ui[i] += h
        fi, ci = _fc(ev, ui)
        g[i] = (fi - fk) / h
        J[:, i] = (ci - ck) / h
    delta = delta0
    small = 0
    for _ in range(max_iter):
        lo_d = np.maximum(-delta, -u)
        hi_d = np.minimum(delta, 1.0 - u)
        # LP in (d, s): min g.d + mu*sum(s)  s.t.  c + J d + s >= 0, s >= 0, lo_d <= d <= hi_d
        cost = np.concatenate([g, mu * np.ones(m)])
        A = np.hstack([-J, -np.eye(m)])
        b = ck
        # cap on the predicted change of every constraint per step (they are normalised: 0.15 = 0.45 K of MITA, 15 % of the UA margin):
        # MITA responds at about 1 K per K of T_lng, so a box in scaled variables alone overshoots along the sensitive variable
        A = np.vstack([A, np.hstack([J, np.zeros((m, m))]), np.hstack([-J, np.zeros((m, m))])])
        b = np.concatenate([b, np.full(m, CHANGE_CAP), np.full(m, CHANGE_CAP)])
        res = linprog(cost, A_ub=A, b_ub=b, bounds=list(zip(lo_d, hi_d)) + [(0, None)] * m, method="highs")
        if res.status != 0:
            break
        d = res.x[:n]
        pred = _merit(fk, ck, mu) - (fk + g @ d + mu * float(np.maximum(0.0, -(ck + J @ d)).sum()))
        if pred < tol or np.abs(d).max() < 1e-6:
            if delta <= min_delta * 1.01:
                break
            delta *= 0.5                         # model says no further progress at this radius: look closer before stopping
            small += 1
            if small >= 3:
                break
            continue
        try:
            ft, ct = _fc(ev, u + d)
        except _Budget:
            break
        ph_old, ph_new = _merit(fk, ck, mu), _merit(ft, ct, mu)
        rho = (ph_old - ph_new) / pred
        step = u + d - u
        rt = ev.cache[tuple(np.round(np.clip(u + d, 0, 1), 12))]
        ok_numbers = rt.mita == rt.mita and rt.ua == rt.ua and rt.sec == rt.sec
        if ok_numbers and rho > 0.1:             # Broyden update only from accepted steps with a complete evaluation
            dd = float(step @ step)
            if dd > 0:
                g = g + ((ft - fk - g @ step) / dd) * step
                J = J + np.outer(ct - ck - J @ step, step) / dd
        if rho > 0.1:
            u, fk, ck = np.clip(u + d, 0, 1), ft, ct
            if rho > 0.7 and np.abs(d).max() >= 0.95 * delta:
                delta = min(0.25, 2 * delta)
            small = 0
        else:
            delta *= 0.25 if not ok_numbers else 0.5
            if delta < min_delta * 0.5:
                break
    return u


def solve_tr_slp(cycle, feed, m_lng, x1, y0, y_lo, y_hi, basis, *, max_evals=40, n_restarts=0, seed=1, extra_starts=None,
                 start_label="warm", delta0=0.04, **_) -> InnerResult:
    ev = _Evaluator(cycle, feed, m_lng, x1, y_lo, y_hi, basis, max_evals)
    span = y_hi - y_lo
    u0 = np.clip((np.asarray(y0, float) - y_lo) / span, 0.0, 1.0)
    rng = np.random.default_rng(seed)
    used = 0
    try:
        _tr_slp_from(ev, u0, delta0=delta0)
        for k in range(n_restarts):
            if len(ev.evals) >= ev.max_evals:
                break
            used += 1
            if extra_starts is not None and k < len(extra_starts):
                u_k = np.clip((np.asarray(extra_starts[k], float) - y_lo) / span, 0.0, 1.0)
            else:
                u_k = np.clip(u0 + 0.25 * (rng.random(len(u0)) - 0.5), 0, 1)
            _tr_slp_from(ev, u_k, delta0=delta0)
    except _Budget:
        pass
    return InnerResult(ev.best, ev.best_y, ev.evals, len(ev.evals), "tr_slp", used, start_label)


class _Found(Exception):
    """Raised inside the feasibility phase as soon as the rigorous model has accepted a point."""


def solve_hybrid(cycle, feed, m_lng, x1, y0, y_lo, y_hi, basis, *, max_evals=40, n_restarts=0, seed=1, feas_max=24, box=0.20, maxiter=12,
                 extra_starts=None, start_label="warm", **_) -> InnerResult:
    """Second-stage solver used by the study.
    Phase A: one penalised Nelder-Mead run (at most `feas_max` evaluations) that stops at the first rigorous-feasible point.
    Phase B: SLSQP restricted to a box of half-width `box` (scaled units) around the best feasible point, using the remaining budget.
    Restarts (random or surrogate-screened starting points) repeat both phases while budget remains. Every accepted value is rigorous.
    Chosen after the comparison in runs/inner_solver_comparison*.csv (see STATUS.md)."""
    ev = _Evaluator(cycle, feed, m_lng, x1, y_lo, y_hi, basis, max_evals)
    span = y_hi - y_lo
    u0 = np.clip((np.asarray(y0, float) - y_lo) / span, 0.0, 1.0)
    rng = np.random.default_rng(seed)

    def f(u):
        r = ev.run(u)
        if ev.best is not None:
            raise _Found()
        return (r.sec if r.sec == r.sec else 1.5) + 20.0 * r.violation

    def one(start):
        try:
            if ev.best is None:
                try:
                    sp_minimize(f, start, method="Nelder-Mead", options=dict(maxfev=feas_max, xatol=1e-4, fatol=1e-6, initial_simplex=_simplex(start)))
                except _Found:
                    pass
            if ev.best is not None:
                _slsqp_from(ev, np.clip((ev.best_y - y_lo) / span, 0.0, 1.0), maxiter, box=box)
        except _Budget:
            pass

    one(u0)
    used = 0
    for k in range(n_restarts):
        if len(ev.evals) >= ev.max_evals:
            break
        used += 1
        st = (np.clip((np.asarray(extra_starts[k], float) - y_lo) / span, 0.0, 1.0) if extra_starts is not None and k < len(extra_starts)
              else np.clip(u0 + 0.25 * (rng.random(len(u0)) - 0.5), 0, 1))
        ev_best_before = ev.best
        one(st)
    return InnerResult(ev.best, ev.best_y, ev.evals, len(ev.evals), "hybrid", used, start_label)
