"""Evaluate one first-stage design x1 over a scenario set: for each scenario the second stage is re-optimised in the rigorous model.

Returns the per-scenario SEC vector (with the infeasibility penalty), the feasible mask and the best operating point of every
scenario (used as the warm start of the next evaluation, i.e. the nearest solved case). Every rigorous evaluation is turned into a
compact row in the worker and returned for logging."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from lng_robust.opt.common import cvar
from lng_robust.opt.inner import solve_hybrid, solve_nelder_mead, solve_slsqp
from lng_robust.opt.parallel import get_pool
from lng_robust.opt.space import STAGE2, bounds
from lng_robust.study.store import compact_row


def scenario_job(args):
    (cycle, sid, synthetic, parent, treated, m_lng, x1, y0, basis, kw, tag) = args
    y_lo, y_hi = bounds(cycle, STAGE2[cycle], basis)
    method = kw.get("method", "hybrid")
    if method == "nm":
        out = solve_nelder_mead(cycle, treated, m_lng, x1, y0, y_lo, y_hi, basis, maxfev=kw.get("maxfev", 16), seed_points=kw.get("seed_points"))
    elif method == "slsqp":
        out = solve_slsqp(cycle, treated, m_lng, x1, y0, y_lo, y_hi, basis, max_evals=kw.get("max_evals", 40),
                          n_restarts=kw.get("n_restarts", 3), seed=kw.get("seed", 1), maxiter=kw.get("maxiter", 12),
                          extra_starts=kw.get("extra_starts"))
    else:    # hybrid: penalised Nelder-Mead to feasibility, then SLSQP in a trust box (see opt/inner.py and runs/inner_solver_*.csv)
        out = solve_hybrid(cycle, treated, m_lng, x1, y0, y_lo, y_hi, basis, max_evals=kw.get("max_evals", 40), n_restarts=kw.get("n_restarts", 0),
                           seed=kw.get("seed", 1), box=kw.get("box", 0.20), feas_max=kw.get("feas_max", 24),
                           maxiter=kw.get("maxiter", 12),
                           extra_starts=kw.get("extra_starts"), seed_points=kw.get("seed_points"))
    stage1 = {k: v for k, v in x1.items() if k in ("ua_installed_kw_per_K", "n_ref_rated_mol_s")}
    rows = []
    min_viol = float("inf")
    near = None          # the evaluation closest to feasibility: its failure code explains an infeasible scenario
    for x, r in out.evals:
        xx = {k: v for k, v in x.items() if k in STAGE2[cycle] or k == "ref"}
        xx.update(stage1)
        rows.append(compact_row(r, unit=tag["unit"], cycle=cycle, feed_id=sid, synthetic=synthetic, purpose=tag["purpose"], x=xx,
                                member=tag.get("member", ""), extra=dict(parent_anchor=parent or "", n_inner=out.n_evals)))
        if r.violation == r.violation:
            if r.violation < min_viol:
                near = r
            min_viol = min(min_viol, r.violation)
    feas = out.best_res is not None
    return dict(sid=sid, sec=float(out.best_res.sec) if feas else float("nan"), feasible=feas,
                y=out.best_y.tolist() if out.best_y is not None else None, n_evals=out.n_evals, rows=rows,
                min_violation=min_viol if min_viol != float("inf") else float("nan"),
                fail_code="" if feas else (near.failure_code if near is not None else "NO_EVALUATION"),
                fail_codes="" if feas else (";".join(near.failure_codes) if near is not None else ""),
                lng_N2_mol_pct=float(out.best_res.as_row()["lng_N2_mol_pct"]) if feas else float("nan"),
                mita=float(out.best_res.mita) if feas else float("nan"), ua=float(out.best_res.ua) if feas else float("nan"),
                n_ref=float(out.best_res.n_ref) if feas else float("nan"))


@dataclass
class DesignEval:
    sec: np.ndarray                  # with penalty
    feasible: np.ndarray
    y: dict                          # sid -> best y (list) or None
    n_evals: int
    detail: list = field(default_factory=list)   # per-scenario dicts without rows

    def cvar(self, alpha):
        return cvar(self.sec, alpha)

    @property
    def worst(self):
        return float(self.sec.max())

    @property
    def feasible_fraction(self):
        return float(self.feasible.mean())


def evaluate_design(cycle, scen, m_lng, x1, basis, *, warm: dict, y_default, kw, unit, member, purpose, sink=None, workers=None,
                    starts: dict | None = None, serial=False, seeds: dict | None = None) -> DesignEval:
    tasks = []
    for f in scen:
        y0 = warm.get(f.id)
        k = dict(kw)
        sf = starts.get(f.id) if starts else None
        if y0 is None:
            # cold start (no solved neighbour yet): begin at the surrogate's best-ranked point (decision D6: surrogate screening, then rigorous
            # re-optimisation); the remaining screened points are the restart points
            y0 = sf[0] if sf else y_default
            sf = sf[1:] if sf else sf
        if sf:
            k["extra_starts"] = sf
        if seeds and seeds.get(f.id):
            k["seed_points"] = [list(map(float, y)) for y in seeds[f.id] if y is not None]
        tasks.append((cycle, f.id, f.synthetic, f.parent_id, f.treated, m_lng, x1, np.asarray(y0, float), basis, k,
                      dict(unit=unit, member=member, purpose=purpose)))
    if serial or workers == 1:
        outs = [scenario_job(t) for t in tasks]
    else:
        outs = list(get_pool(workers).map(scenario_job, tasks, chunksize=1))
    pen = basis.sec_penalty_kwh_per_kg
    sec = np.array([o["sec"] if o["feasible"] else pen for o in outs])
    feas = np.array([o["feasible"] for o in outs])
    ydict = {o["sid"]: o["y"] for o in outs}
    n = sum(o["n_evals"] for o in outs)
    if sink is not None:
        for o in outs:
            sink.add_rows(o["rows"])
    detail = [{k: v for k, v in o.items() if k not in ("rows", "y")} for o in outs]
    return DesignEval(sec, feas, ydict, n, detail)
