"""Independent, resumable study units. Each reads the output folders of its predecessors under ctx.work and writes its own
folder (unit-<key>/) with Parquet shards, JSON/CSV results and done.json. No unit holds state in memory between jobs."""
from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from lng_robust.analysis import por as por_mod
from lng_robust.cycles import solve
from lng_robust.opt import ga
from lng_robust.opt.common import cvar, nominal_var_names
from lng_robust.opt.nominal import run_nominal
from lng_robust.opt.parallel import shutdown
from lng_robust.opt.robust import stage1_vec_of_design, x1_from_vec
from lng_robust.opt.scenario_eval import evaluate_design
from lng_robust.opt.space import STAGE1, STAGE2, bounds
from lng_robust.study.common import (M_LNG, basis_for, load_nominal, nominal_design_dict, nominal_y0, scenario_set, write_done)
from lng_robust.study.config import ALL_SENS_CASES, ARCHIVE_CASES, MODEL_CASES, SET_CASES, VARIANTS
from lng_robust.study.store import EvalSink, SinkLog, Timer, read_parts
from lng_robust.surrogate.active import composition_pool, run_active_sampling
from lng_robust.surrogate.starts import StartSelector
from lng_robust.surrogate.validate import fit_final, grouped_validation


def _log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ------------------------------------------------------------------ nominal
def unit_nominal(ctx, basis=None, tag_out=None):
    cycle, P = ctx.cycle, ctx.preset["nominal"]
    basis = basis or basis_for(ctx)
    scen, nom_feed, meta = scenario_set(ctx, basis)
    out = tag_out or ctx.out
    sink = EvalSink(out, "evals")
    log = SinkLog(sink, "nominal", ctx.seed)
    t = Timer()
    from lng_robust.analysis.golden import seed_vectors
    seeds = seed_vectors(cycle, nominal_var_names(cycle), basis)
    res = run_nominal(cycle, nom_feed.treated, nom_feed.id, M_LNG, basis, pop=P["pop"], n_gen=P["gen"], seed=ctx.seed, log=log,
                      workers=ctx.workers, seeds=seeds)
    sink.close()
    info = dict(cycle=cycle, nominal_anchor=nom_feed.id, feasible_found=res.feasible_found, note=res.note, n_evals=res.n_evals,
                initial_screen=f"{3 * P['pop']} random candidates plus {len(seeds)} hand-set seed designs (analysis/golden.py)",
                names=res.names, front=res.front, minutes=t.minutes(), pop=P["pop"], gen=P["gen"])
    if res.best is not None:
        b = res.best
        r = solve(cycle, nom_feed.treated, basis.feed_T, basis.feed_P, M_LNG, b["x"], basis)    # serial re-run keeps the exchanger curves
        ro = r.as_row()
        info.update(vec=b["vec"], x=b["x"], sec=float(b["sec"]), ua_spec=float(b["ua_spec"]), mita=float(b["mita"]), n_ref=float(b["n_ref"]),
                    exergy_eff=float(r.exergy_eff), lng_N2_mol_pct=float(ro["lng_N2_mol_pct"]), w_comp_kw=float(r.w_comp_kw),
                    w_exp_kw=float(r.w_exp_kw), ua_kw_per_K=float(r.ua), exergy_destruction_kw=r.exergy_destruction_kw,
                    lng_comp=r.lng_comp, feasible=bool(r.feasible), end_flash_fraction=float(r.end_flash_fraction))
        m = getattr(r, "_mshe", None)
        if m is not None:
            info["composite"] = dict(q_kw=(m.q / 1e3).tolist(), T_hot_K=m.T_hot.tolist(), T_cold_K=m.T_cold.tolist())
    (out / "nominal.json").write_text(json.dumps(info, indent=2, default=float))
    write_done(out, unit="nominal", cycle=cycle, status="complete" if res.feasible_found else "INCOMPLETE_no_feasible_design",
               n_evals=res.n_evals, minutes=t.minutes())
    return info


# ------------------------------------------------------------------ sampling (Phase 5)
def unit_sample(ctx):
    cycle, P = ctx.cycle, ctx.preset["sample"]
    basis = basis_for(ctx)
    scen, nom_feed, meta = scenario_set(ctx, basis)
    anchors = [f for f in scen if not f.synthetic]
    pool = composition_pool(anchors, meta["kappa"], 25 if ctx.preset_name == "full" else 3, ctx.seed + 31, basis)
    nom = load_nominal(ctx, cycle)
    centre = nom.get("vec")
    sink = EvalSink(ctx.out, "evals")
    t = Timer()
    df = run_active_sampling(cycle, pool, M_LNG, basis, sink, n0=P["n0"], rounds=P["rounds"], batch=P["batch"], centre=centre,
                             seed=ctx.seed, workers=ctx.workers, log=_log)
    sink.close()
    df.to_parquet(ctx.out / "dataset.parquet", compression="zstd", index=False)
    write_done(ctx.out, unit="sample", cycle=cycle, status="complete", n_evals=len(df), n_feasible=int(df.feasible.sum()), minutes=t.minutes(),
               groups=sorted(set(df.group)), by_source=df.groupby("source").feasible.agg(["sum", "count"]).to_dict())
    return df


# ------------------------------------------------------------------ surrogate validation (Phase 6)
def unit_surrogate(ctx):
    cycle = ctx.cycle
    basis = basis_for(ctx)
    df = pd.read_parquet(ctx.input("sample", cycle) / "dataset.parquet")
    t = Timer()
    metrics, oof = grouped_validation(df, basis.mita_min_K, ctx.seed, gp_max=ctx.preset["gp_max"])
    metrics.insert(0, "cycle", cycle)
    metrics.to_csv(ctx.out / "surrogate_metrics.csv", index=False)
    oof.to_parquet(ctx.out / "oof_predictions.parquet", index=False)
    cols, regs, clfs = fit_final(df, ctx.seed, ctx.preset["gp_max"])
    joblib.dump(dict(cols=cols, regs=regs, clfs=clfs, cycle=cycle), ctx.out / "models.joblib", compress=3)
    write_done(ctx.out, unit="surrogate", cycle=cycle, status="complete", minutes=t.minutes(), n_train=len(df))
    return metrics


def load_models(ctx, cycle):
    return joblib.load(ctx.input("surrogate", cycle) / "models.joblib")


# ------------------------------------------------------------------ robust outer search (Phase 7)
def _robust_setup(ctx, basis):
    cycle, variant = ctx.cycle, ctx.variant
    nom = load_nominal(ctx, cycle)
    names1 = STAGE1[cycle]
    lo, hi = bounds(cycle, names1, basis)
    f = basis.values[VARIANTS[variant]["ua_factor_key"]]
    iua = names1.index("ua_spec")
    hi = hi.copy()
    hi[iua] = min(hi[iua], nom["ua_spec"] * f * (1 + 1e-6))
    lo = np.minimum(lo, hi)
    seed_vec = np.clip(stage1_vec_of_design(cycle, nominal_design_dict(nom), M_LNG), lo, hi)
    return nom, names1, lo, hi, seed_vec, f


def _latest_state(ctx, cycle, variant):
    for d in reversed(ctx.robust_dirs(cycle, variant)):
        if (d / "ga_state.json").exists() and d != ctx.out:
            return d
    return None


def unit_robust(ctx):
    cycle, variant, P = ctx.cycle, ctx.variant, ctx.preset["robust"]
    basis = basis_for(ctx)
    risk = VARIANTS[variant]["risk"]
    nom, names1, lo, hi, seed_vec, ua_factor = _robust_setup(ctx, basis)
    scen, nom_feed, meta = scenario_set(ctx, basis)
    models = load_models(ctx, cycle)
    selector = StartSelector(cycle, models["cols"], models["regs"]["gradient_boosting"], models["clfs"]["gradient_boosting"], basis, ctx.seed)
    y_default = nominal_y0(nom, cycle)
    out = ctx.out
    prev = _latest_state(ctx, cycle, variant)
    if prev is not None:
        state = ga.GAState.from_json((prev / "ga_state.json").read_text())
        warm = json.loads((prev / "warm.json").read_text())
        _log(f"resuming from {prev.name}: generation {state.gen}")
    else:
        rng = np.random.default_rng(ctx.seed)
        cloud = [np.clip(seed_vec + rng.normal(0, 0.08, len(lo)) * (hi - lo), lo, hi) for _ in range(P["pop"] // 2)]
        state = ga.init_state([seed_vec] + cloud, lo, hi, P["pop"], ctx.seed)
        warm = {}
    sink = EvalSink(out, "evals")
    target = P["gens"]
    inner = dict(P["inner"], **P.get("inner_by_cycle", {}).get(cycle, {}), seed=ctx.seed)
    archive = open(out / "archive.jsonl", "a")
    t_unit = Timer()
    member_counter = [0]
    last_gen_min = [0.0]

    def evaluate(X):
        F, CV = [], []
        for v in X:
            x1 = x1_from_vec(cycle, v, M_LNG)
            starts = {f.id: selector.starts(f.treated, x1, k=inner.get("n_restarts", 3), salt=member_counter[0]) for f in scen}
            tm = Timer()
            de = evaluate_design(cycle, scen, M_LNG, x1, basis, warm=warm, y_default=y_default, kw=inner, unit="robust",
                                 member=f"{variant}-g{state.gen + 1}-m{member_counter[0]}", purpose=f"robust_{variant}", sink=sink,
                                 workers=ctx.workers, starts=starts)
            for sid, y in de.y.items():
                if y is not None:
                    warm[sid] = y
            obj = de.cvar(basis.cvar_alpha) if risk == "cvar" else de.worst
            ff = de.feasible_fraction
            miss = [d["min_violation"] for d, ok in zip(de.detail, de.feasible) if not ok and d["min_violation"] == d["min_violation"]]
            cv = max(0.0, basis.chance_feasible_fraction - ff)
            if cv > 0:
                cv += 1e-3 * (float(np.mean(miss)) if miss else 0.0)
            F.append(obj)
            CV.append(cv)
            archive.write(json.dumps(dict(gen=state.gen + 1, member=member_counter[0], vec=np.asarray(v).tolist(), objective=obj, cvar=de.cvar(basis.cvar_alpha),
                                          worst=de.worst, feasible_fraction=ff, sec=de.sec.tolist(), feasible=de.feasible.tolist(),
                                          scenario_ids=[f.id for f in scen], n_evals=de.n_evals, minutes=tm.minutes())) + "\n")
            archive.flush()
            sink.flush()
            member_counter[0] += 1
            _log(f"  member {member_counter[0]}: obj {obj:.4f}  ff {ff:.2f}  evals {de.n_evals}  {tm.minutes():.1f} min")
        return np.array(F), np.array(CV)

    status = "partial"
    while True:
        if state.gen >= target:                      # generation 0 is the initial population; `target` offspring generations follow
            status = "complete"
            break
        tg = Timer()
        state = ga.advance(state, evaluate)
        last_gen_min[0] = tg.minutes()
        (out / "ga_state.json").write_text(state.to_json())
        (out / "warm.json").write_text(json.dumps(warm))
        _log(f"generation {state.gen} done in {tg.minutes():.1f} min; best {state.history[-1]}")
        if state.gen < target and t_unit.minutes() + 1.2 * last_gen_min[0] > P["unit_wall_min"]:
            _log("wall-clock budget for this job reached; checkpoint written")
            break
    archive.close()
    sink.close()
    i = ga.best(state)
    x1 = x1_from_vec(cycle, state.X[i], M_LNG)
    (out / "ga_state.json").write_text(state.to_json())
    (out / "warm.json").write_text(json.dumps(warm))
    final = dict(cycle=cycle, variant=variant, risk=risk, ua_factor=ua_factor, vec=state.X[i].tolist(), x1=x1, objective=float(state.F[i]),
                 constraint_violation=float(state.CV[i]), chance_met=bool(state.CV[i] <= 0), generation=state.gen, target_generations=target,
                 history=state.history, stage1_names=names1, status=status)
    (out / "final.json").write_text(json.dumps(final, indent=2, default=float))
    write_done(out, unit="robust", cycle=cycle, variant=variant, stage=ctx.stage, status=status, generation=state.gen, minutes=t_unit.minutes(),
               members_evaluated=member_counter[0])
    return final


def load_final(ctx, cycle, variant):
    for d in reversed(ctx.robust_dirs(cycle, variant)):
        if (d / "final.json").exists():
            return json.loads((d / "final.json").read_text())
    return None


def load_archive(ctx, cycle, variant):
    rows = []
    for d in ctx.robust_dirs(cycle, variant):
        p = d / "archive.jsonl"
        if p.exists():
            rows += [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    return rows


# ------------------------------------------------------------------ nominal and robust designs across scenarios (Phase 7/8)
def _stage1_of(cycle, vec_or_nom, from_nominal: bool, nom=None):
    if from_nominal:
        return x1_from_vec(cycle, stage1_vec_of_design(cycle, nominal_design_dict(nom), M_LNG), M_LNG)
    return x1_from_vec(cycle, np.asarray(vec_or_nom, float), M_LNG)


def design_table(ctx, cycle, basis):
    """{design name: x1} for the nominal design and every available robust variant."""
    nom = load_nominal(ctx, cycle)
    d = {"nominal": _stage1_of(cycle, None, True, nom)}
    for v in VARIANTS:
        fin = load_final(ctx, cycle, v)
        if fin is not None:
            d[v] = fin["x1"]
    return d, nom


def eval_designs_on_set(ctx, cycle, designs: dict, scen, basis, nom, kw, tag, sink, starts_models=None):
    """Second stage re-optimised for every scenario for each design. Returns {design: DesignEval}."""
    y0 = nominal_y0(nom, cycle)
    selector = None
    if starts_models is not None:
        selector = StartSelector(cycle, starts_models["cols"], starts_models["regs"]["gradient_boosting"], starts_models["clfs"]["gradient_boosting"], basis, ctx.seed)
    out = {}
    for name, x1 in designs.items():
        starts = {f.id: selector.starts(f.treated, x1, k=kw.get("n_restarts", 3)) for f in scen} if selector else None
        warm = {}
        first = [f for f in scen if not f.synthetic]
        rest = [f for f in scen if f.synthetic]
        kw2 = dict(kw, seed=ctx.seed)
        d1 = evaluate_design(cycle, first, M_LNG, x1, basis, warm={}, y_default=y0, kw=kw2, unit=tag, member=name, purpose=f"{tag}_{name}", sink=sink,
                             workers=ctx.workers, starts={k: v for k, v in (starts or {}).items() if k in {f.id for f in first}} or None)
        for sid, y in d1.y.items():
            if y is not None:
                warm[sid] = y
        warm2 = {f.id: warm.get(f.parent_id) for f in rest}      # nearest solved scenario = the parent anchor
        d2 = evaluate_design(cycle, rest, M_LNG, x1, basis, warm={k: v for k, v in warm2.items() if v}, y_default=y0, kw=kw2, unit=tag,
                             member=name, purpose=f"{tag}_{name}", sink=sink, workers=ctx.workers,
                             starts={k: v for k, v in (starts or {}).items() if k in {f.id for f in rest}} or None) if rest else None
        from lng_robust.opt.scenario_eval import DesignEval
        ids = [f.id for f in first] + [f.id for f in rest]
        sec = np.concatenate([d1.sec] + ([d2.sec] if d2 else []))
        feas = np.concatenate([d1.feasible] + ([d2.feasible] if d2 else []))
        ydict = dict(d1.y, **(d2.y if d2 else {}))
        detail = d1.detail + (d2.detail if d2 else [])
        out[name] = DesignEval(sec, feas, ydict, d1.n_evals + (d2.n_evals if d2 else 0), detail)
        out[name].ids = ids
    return out


def unit_across(ctx):
    cycle, P = ctx.cycle, ctx.preset["across"]
    basis = basis_for(ctx)
    scen, nom_feed, meta = scenario_set(ctx, basis)
    designs, nom = design_table(ctx, cycle, basis)
    models = load_models(ctx, cycle)
    sink = EvalSink(ctx.out, "evals")
    t = Timer()
    kw = dict(max_evals=P["max_evals"], n_restarts=P["n_restarts"], maxiter=P["maxiter"])
    res = eval_designs_on_set(ctx, cycle, designs, scen, basis, nom, kw, "across", sink, models)
    z0 = eval_designs_on_set(ctx, cycle, designs, [nom_feed], basis, nom, kw, "across_z0", sink, models)
    # SEC at z0 is the one number that enters Eq. 8, so it gets extra effort: the best rigorous value of three searches
    # (the scenario-level search above, a long hybrid search with restarts, and a long Nelder-Mead run).
    kw_long = dict(max_evals=P["z0_long_evals"], n_restarts=3, maxiter=20)
    kw_nm = dict(method="nm", maxfev=P["z0_nm_evals"])
    z0_long = eval_designs_on_set(ctx, cycle, designs, [nom_feed], basis, nom, kw_long, "across_z0_long", sink, models)
    z0_nm = eval_designs_on_set(ctx, cycle, designs, [nom_feed], basis, nom, kw_nm, "across_z0_nm", sink, None)
    sink.close()
    sec_z0 = {}
    for name in designs:
        cands = {k: v[name].sec[0] for k, v in (("scenario_search", z0), ("hybrid_long", z0_long), ("nelder_mead_long", z0_nm)) if v[name].feasible[0]}
        if name == "nominal" and nom.get("sec") == nom.get("sec"):
            cands["nominal_nsga2_own_optimum"] = float(nom["sec"])
        sec_z0[name] = (min(cands.values()) if cands else float("nan"), cands)
    rows, summary = [], []
    sc_by_id = {f.id: f for f in scen}
    for name, de in res.items():
        for i, (sid, d) in enumerate(zip(de.ids, de.detail)):
            f = sc_by_id[sid]
            rows.append(dict(design=name, scenario=sid, synthetic=f.synthetic, parent=f.parent_id or "", sec=float(de.sec[i]),
                             feasible=bool(de.feasible[i]), mita=d["mita"], ua_kw_per_K=d["ua"], n_ref=d["n_ref"], lng_N2_mol_pct=d["lng_N2_mol_pct"],
                             n2_pct_feed=100 * f.treated.get("N2", 0.0), y=json.dumps(de.y.get(sid))))
        summary.append(dict(cycle=cycle, design=name, CVaR=de.cvar(basis.cvar_alpha), worst=de.worst, feasible_fraction=de.feasible_fraction,
                            mean_sec_feasible=float(de.sec[de.feasible].mean()) if de.feasible.any() else float("nan"),
                            sec_z0=sec_z0[name][0], feasible_z0=bool(sec_z0[name][0] == sec_z0[name][0]),
                            n_anchor_feasible=int(sum(de.feasible[i] for i, s in enumerate(de.ids) if not sc_by_id[s].synthetic)),
                            n_anchor=int(sum(not sc_by_id[s].synthetic for s in de.ids)),
                            n_synth_feasible=int(sum(de.feasible[i] for i, s in enumerate(de.ids) if sc_by_id[s].synthetic)),
                            n_synth=int(sum(sc_by_id[s].synthetic for s in de.ids))))
    pd.DataFrame(rows).to_parquet(ctx.out / "across_scenarios.parquet", index=False)
    pd.DataFrame(summary).to_csv(ctx.out / "across_summary.csv", index=False)
    por_rows = []
    nd = res["nominal"]
    for name, de in res.items():
        if name == "nominal":
            continue
        s = por_mod.por_summary(de.sec, nd.sec, de.feasible, nd.feasible, sec_z0[name][0], sec_z0["nominal"][0], basis.cvar_alpha,
                                B=ctx.preset["bootstrap"], seed=ctx.seed)
        por_rows.append(dict(cycle=cycle, design=name, feasible_z0_robust=bool(sec_z0[name][0] == sec_z0[name][0]), feasible_z0_nominal=bool(sec_z0["nominal"][0] == sec_z0["nominal"][0]),
                             sec_z0_robust=sec_z0[name][0], sec_z0_nominal=sec_z0["nominal"][0], **s))
    (ctx.out / "sec_z0_candidates.json").write_text(json.dumps({k: dict(best=v[0], candidates=v[1]) for k, v in sec_z0.items()}, indent=2, default=float))
    pd.DataFrame(por_rows).to_csv(ctx.out / "price_of_robustness.csv", index=False)
    # the designs at z0 (Tables 5 and 6): re-solve once serially to keep exergy numbers and LNG N2
    dz = {}
    for name, x1 in designs.items():
        best_src = min((v for v in (z0, z0_long, z0_nm) if v[name].feasible[0]), key=lambda v: v[name].sec[0], default=None)
        y = best_src[name].y.get(nom_feed.id) if best_src is not None else None
        if y is None:
            dz[name] = dict(feasible=False)
            continue
        x = dict(x1)
        x.update({n: v for n, v in zip(STAGE2[cycle], y)})
        r = solve(cycle, nom_feed.treated, basis.feed_T, basis.feed_P, M_LNG, x, basis)
        ro = r.as_row()
        dz[name] = dict(feasible=bool(r.feasible), sec=float(r.sec), exergy_eff=float(r.exergy_eff), mita=float(r.mita), ua_kw_per_K=float(r.ua),
                        lng_N2_mol_pct=float(ro["lng_N2_mol_pct"]), exergy_destruction_kw=r.exergy_destruction_kw, w_comp_kw=float(r.w_comp_kw),
                        w_exp_kw=float(r.w_exp_kw), ua_installed_kw_per_K=float(x1.get("ua_installed_kw_per_K", np.nan)),
                        n_ref_rated_mol_s=float(x1.get("n_ref_rated_mol_s", np.nan)), operating=dict(zip(STAGE2[cycle], [float(v) for v in y])),
                        refrigerant=x1.get("ref"))
    (ctx.out / "designs_at_z0.json").write_text(json.dumps(dz, indent=2, default=float))
    # surrogate versus rigorous at every scenario optimum (Figure 8)
    from lng_robust.surrogate.train import alr_features
    cols, reg, clf = models["cols"], models["regs"]["gradient_boosting"], models["clfs"]["gradient_boosting"]
    names = nominal_var_names(cycle)
    sv = []
    for name, de in res.items():
        x1 = designs[name]
        for i, sid in enumerate(de.ids):
            y = de.y.get(sid)
            if y is None:
                continue
            v = [dict(zip(STAGE2[cycle], y)).get(n) if n in STAGE2[cycle] else (x1.get("ref") or {}).get(n[2:], 0.0) for n in names]
            X = np.array([v + alr_features(sc_by_id[sid].treated)])
            sv.append(dict(cycle=cycle, design=name, scenario=sid, rigorous_sec=float(de.sec[i]), surrogate_sec=float(reg.predict(X)[0]),
                           surrogate_prob_feasible=float(clf.predict_proba(X)[0, 1]), rigorous_feasible=True))
    pd.DataFrame(sv).to_csv(ctx.out / "surrogate_vs_rigorous_at_optima.csv", index=False)
    write_done(ctx.out, unit="across", cycle=cycle, status="complete", minutes=t.minutes(), designs=list(designs))
    return summary


# ------------------------------------------------------------------ ranking-reversal data (Phase 8)
def reversal_compositions(ctx, basis):
    """The same compositions for every cycle and design: the six anchors plus Dirichlet samples around random anchors."""
    from lng_robust.doe.dirichlet import sample_dirichlet
    scen, nom_feed, meta = scenario_set(ctx, basis)
    anchors = [f for f in scen if not f.synthetic]
    n = ctx.preset["reversal"]["n_comp"]
    rng = np.random.default_rng(ctx.seed + 4242)
    comps = list(anchors)
    k = 0
    per = max(1, (n - len(anchors)) // len(anchors) + 1)
    for a in anchors:
        k += 1
        comps += sample_dirichlet(a, meta["kappa"], per, ctx.seed + 4242 + 97 * k, basis)
    return comps[:max(n, len(anchors))], meta


def unit_reversal(ctx):
    cycle, design, P = ctx.cycle, ctx.variant, ctx.preset["reversal"]
    basis = basis_for(ctx)
    comps, meta = reversal_compositions(ctx, basis)
    designs, nom = design_table(ctx, cycle, basis)
    key = "nominal" if design == "nominal" else "cvar_iso"
    if key not in designs:
        write_done(ctx.out, unit="reversal", cycle=cycle, status="INCOMPLETE_design_missing", design=key)
        return None
    sink = EvalSink(ctx.out, "evals")
    t = Timer()
    kw = dict(max_evals=P["max_evals"], n_restarts=P["n_restarts"], maxiter=12)
    models = load_models(ctx, cycle) if P["n_restarts"] > 0 else None
    res = eval_designs_on_set(ctx, cycle, {key: designs[key]}, comps, basis, nom, kw, "reversal", sink, models)[key]
    sink.close()
    from lng_robust.analysis.reversal import coords
    rows = []
    by = {f.id: f for f in comps}
    for i, sid in enumerate(res.ids):
        n2, c2p = coords(by[sid].treated)
        rows.append(dict(cycle=cycle, design=design, scenario=sid, synthetic=by[sid].synthetic, parent=by[sid].parent_id or "", N2_pct=n2,
                         C2plus_pct=c2p, sec=float(res.sec[i]) if res.feasible[i] else float("nan"), feasible=bool(res.feasible[i])))
    pd.DataFrame(rows).to_parquet(ctx.out / "reversal_points.parquet", index=False)
    write_done(ctx.out, unit="reversal", cycle=cycle, design=design, status="complete", minutes=t.minutes(), n=len(rows), design_used=key)
    return rows
