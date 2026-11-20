"""Sensitivity units (Phase 9): Sobol on the surrogate with additive log-ratio composition, rigorous one-at-a-time confirmation,
cycle-preference Sobol, and the sensitivity cases (model parameters, alpha, SEC_pen, kappa, Field D, Field E)."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from lng_robust.analysis.por import por_summary
from lng_robust.analysis.sobol import sobol_indices
from lng_robust.cycles import solve
from lng_robust.opt.common import cvar, nominal_var_names
from lng_robust.opt.space import STAGE2, bounds
from lng_robust.study.common import M_LNG, basis_for, load_nominal, nominal_y0, scenario_set, write_done
from lng_robust.study.config import ARCHIVE_CASES, MODEL_CASES, SET_CASES, VARIANTS
from lng_robust.study.store import EvalSink, Timer
from lng_robust.study.units import (_log, design_table, eval_designs_on_set, load_archive, load_final, load_models, unit_nominal)
from lng_robust.surrogate.train import C4S, C5S, alr_features

ALR_NAMES = ["alr_N2", "alr_C2", "alr_C3", "alr_C4", "alr_C5plus"]


def alr_to_treated(alr, template: dict) -> dict:
    """Inverse of surrogate.train.alr_features for a given template composition (keeps the template's iso/normal split and CO2 ratio)."""
    t = {k: v for k, v in template.items() if v > 0}
    c1 = t.get("C1", 1.0)
    out = {"C1": 1.0, "N2": math.exp(alr[0]), "C2": math.exp(alr[1]), "C3": math.exp(alr[2])}
    for grp, a in ((C4S, alr[3]), (C5S, alr[4])):
        tot = sum(t.get(k, 0.0) for k in grp)
        if tot > 0:
            for k in grp:
                out[k] = t.get(k, 0.0) / tot * math.exp(a)
    if t.get("CO2"):
        out["CO2"] = t["CO2"] / c1
    s = sum(out.values())
    return {k: v / s for k, v in out.items()}


def sobol_box(ctx, cycle, basis, nom, scen, frac=0.15):
    names = nominal_var_names(cycle)
    lo, hi = bounds(cycle, names, basis)
    centre = np.array(nom["vec"], float)
    span = hi - lo
    dlo, dhi = np.maximum(lo, centre - frac * span), np.minimum(hi, centre + frac * span)
    A = np.array([alr_features(f.treated) for f in scen])
    alr_lo, alr_hi = A.min(0), A.max(0)
    return names, dlo, dhi, centre, alr_lo, alr_hi


def unit_sobol(ctx):
    cycle, P = ctx.cycle, ctx.preset["sobol"]
    basis = basis_for(ctx)
    scen, nom_feed, meta = scenario_set(ctx, basis)
    nom = load_nominal(ctx, cycle)
    models = load_models(ctx, cycle)
    reg, clf = models["regs"]["gradient_boosting"], models["clfs"]["gradient_boosting"]
    names, dlo, dhi, centre, alo, ahi = sobol_box(ctx, cycle, basis, nom, scen)
    all_names = names + ALR_NAMES
    bnds = [[float(a), float(b)] for a, b in zip(np.concatenate([dlo, alo]), np.concatenate([dhi, ahi]))]
    t = Timer()
    S_sec = sobol_indices(lambda X: reg.predict(X), all_names, bnds, N=P["N"], seed=ctx.seed)
    S_feas = sobol_indices(lambda X: clf.predict_proba(X)[:, 1], all_names, bnds, N=P["N"], seed=ctx.seed)
    rows = []
    for out_name, S in (("SEC_surrogate", S_sec), ("P_feasible_surrogate", S_feas)):
        for i, n in enumerate(all_names):
            rows.append(dict(cycle=cycle, output=out_name, variable=n, S1=float(S["S1"][i]), S1_conf=float(S["S1_conf"][i]),
                             ST=float(S["ST"][i]), ST_conf=float(S["ST_conf"][i]), N=P["N"], n_samples=S["n_samples"]))
    sob = pd.DataFrame(rows)
    sob.to_csv(ctx.out / "sobol_indices.csv", index=False)
    # rigorous one-at-a-time confirmation: vary one input over its box, everything else at the centre (nominal design, nominal anchor)
    alr0 = np.array(alr_features(nom_feed.treated))
    template = nom_feed.treated
    k = P["oat_points"]
    oat = []
    for j, n in enumerate(all_names):
        lo_j = np.concatenate([dlo, alo])[j]
        hi_j = np.concatenate([dhi, ahi])[j]
        for val in np.linspace(lo_j, hi_j, k):
            v = centre.copy()
            a = alr0.copy()
            if j < len(names):
                v[j] = val
            else:
                a[j - len(names)] = val
            comp = nom_feed.treated if j < len(names) else alr_to_treated(a, template)
            x = _x_from_vec(cycle, names, v, nom)
            r = solve(cycle, comp, basis.feed_T, basis.feed_P, M_LNG, x, basis)
            oat.append(dict(cycle=cycle, variable=n, value=float(val), sec=float(r.sec) if r.feasible else float("nan"), feasible=bool(r.feasible),
                            failure_code=r.failure_code, mita=float(r.mita)))
    oat = pd.DataFrame(oat)
    oat.to_csv(ctx.out / "oat_points.csv", index=False)
    eff = oat.groupby("variable").apply(lambda g: pd.Series(dict(n_feasible=int(g.feasible.sum()), n_points=len(g),
                                                               sec_range=float(g.sec.max() - g.sec.min()) if g.feasible.sum() >= 2 else float("nan"))),
                                        include_groups=False).reset_index()
    st = sob[sob.output == "SEC_surrogate"].set_index("variable")["ST"]
    eff["ST_surrogate"] = eff.variable.map(st)
    ok = eff.dropna(subset=["sec_range"])
    rho = float(spearmanr(ok.sec_range, ok.ST_surrogate).statistic) if len(ok) >= 3 else float("nan")
    top2_sob = set(st.sort_values(ascending=False).index[:2])
    top2_oat = set(ok.sort_values("sec_range", ascending=False).variable[:2])
    eff.to_csv(ctx.out / "oat_effects.csv", index=False)
    (ctx.out / "oat_confirmation.json").write_text(json.dumps(dict(cycle=cycle, spearman_oat_vs_ST=rho, top2_sobol_ST=sorted(top2_sob),
                                                                 top2_oat=sorted(top2_oat), top2_agree=top2_sob == top2_oat,
                                                                 box_fraction_of_range=0.15, n_variables_with_two_feasible_points=len(ok))))
    write_done(ctx.out, unit="sobol", cycle=cycle, status="complete", minutes=t.minutes())


def _x_from_vec(cycle, names, v, nom):
    from lng_robust.opt.space import clean, decode
    return clean(decode(cycle, names, v, M_LNG))


def unit_sobol_pref(ctx):
    """Composition-only Sobol indices for each cycle's SEC and for the pairwise SEC difference (cycle preference).
    Each cycle's design variables are fixed at its nominal design; operation is not re-optimised (surrogate of fixed-design SEC)."""
    basis = basis_for(ctx)
    scen, nom_feed, meta = scenario_set(ctx, basis)
    A = np.array([alr_features(f.treated) for f in scen])
    alo, ahi = A.min(0), A.max(0)
    cyc = ["smr", "n2_single", "n2_dual"]
    fns = {}
    for c in cyc:
        nom = load_nominal(ctx, c)
        reg = load_models(ctx, c)["regs"]["gradient_boosting"]
        centre = np.array(nom["vec"], float)
        fns[c] = (lambda reg_, centre_: (lambda Z: reg_.predict(np.hstack([np.tile(centre_, (len(Z), 1)), Z]))))(reg, centre)
    bnds = [[float(a), float(b)] for a, b in zip(alo, ahi)]
    outs = {f"SEC_{c}": (lambda c_: (lambda Z: fns[c_](Z)))(c) for c in cyc}
    for i in range(3):
        for j in range(i + 1, 3):
            outs[f"SECdiff_{cyc[i]}_minus_{cyc[j]}"] = (lambda a, b: (lambda Z: fns[a](Z) - fns[b](Z)))(cyc[i], cyc[j])
    rows = []
    for name, fn in outs.items():
        S = sobol_indices(fn, ALR_NAMES, bnds, N=ctx.preset["sobol"]["N"], seed=ctx.seed)
        for i, n in enumerate(ALR_NAMES):
            rows.append(dict(output=name, variable=n, S1=float(S["S1"][i]), S1_conf=float(S["S1_conf"][i]), ST=float(S["ST"][i]), ST_conf=float(S["ST_conf"][i])))
    pd.DataFrame(rows).to_csv(ctx.out / "sobol_preference.csv", index=False)
    write_done(ctx.out, unit="sobol_pref", status="complete")


# ------------------------------------------------------------------ sensitivity cases
def _candidates(ctx, cycle, k):
    """Top-k distinct designs of the main cvar_iso archive: chance-constraint-met first, then lowest CVaR."""
    arch = load_archive(ctx, cycle, "cvar_iso")
    seen, out = set(), []
    for a in sorted(arch, key=lambda a: (0 if a["feasible_fraction"] >= 0.95 else 1, a["cvar"] if a["feasible_fraction"] >= 0.95 else -a["feasible_fraction"])):
        key = tuple(round(v, 9) for v in a["vec"])
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
        if len(out) >= k:
            break
    return out


def unit_sens(ctx):
    cycle, case, P = ctx.cycle, ctx.case, ctx.preset["sens"]
    t = Timer()
    res = {}
    if case in MODEL_CASES:
        res = _sens_model(ctx, cycle, case, P)
    elif case in ARCHIVE_CASES:
        res = _sens_archive(ctx, cycle, case)
    elif case in SET_CASES:
        res = _sens_set(ctx, cycle, case, P)
    else:
        raise KeyError(case)
    res.update(cycle=cycle, case=case, minutes=t.minutes())
    (ctx.out / "sens.json").write_text(json.dumps(res, indent=2, default=float))
    write_done(ctx.out, unit="sens", cycle=cycle, case=case, status=res.get("status", "complete"), minutes=t.minutes())
    return res


def _design_stats(de, alpha, ids=None):
    return dict(CVaR=de.cvar(alpha), worst=de.worst, feasible_fraction=de.feasible_fraction,
                mean_sec_feasible=float(de.sec[de.feasible].mean()) if de.feasible.any() else float("nan"))


def _sens_model(ctx, cycle, case, P):
    from lng_robust.opt.robust import x1_from_vec
    basis = basis_for(ctx, MODEL_CASES[case])
    scen, nom_feed, meta = scenario_set(ctx, basis)
    sub = ctx.out / "nominal_rerun"
    sub.mkdir(exist_ok=True)
    ctx_n = type(ctx)(**{**ctx.__dict__, "preset": {**ctx.preset, "nominal": P["nominal"]}})
    info = unit_nominal(ctx_n, basis=basis, tag_out=sub)
    if not info.get("feasible_found"):
        return dict(status="INCOMPLETE_no_feasible_nominal", note=info.get("note"), nominal_n_evals=info.get("n_evals"))
    from lng_robust.opt.robust import stage1_vec_of_design
    from lng_robust.study.common import nominal_design_dict
    designs = {"nominal_new": x1_from_vec(cycle, stage1_vec_of_design(cycle, nominal_design_dict(info), M_LNG), M_LNG)}
    cands = _candidates(ctx, cycle, P["k_designs"])
    for i, a in enumerate(cands):
        designs[f"main_robust_cand{i}"] = x1_from_vec(cycle, np.asarray(a["vec"], float), M_LNG)
    sink = EvalSink(ctx.out, "evals")
    kw = dict(max_evals=P["max_evals"], n_restarts=P["n_restarts"], maxiter=12)
    ev = eval_designs_on_set(ctx, cycle, designs, scen, basis, info, kw, f"sens_{case}", sink, load_models(ctx, cycle))
    z0 = eval_designs_on_set(ctx, cycle, designs, [nom_feed], basis, info, kw, f"sens_{case}_z0", sink, load_models(ctx, cycle))
    sink.close()
    rows = {n: dict(_design_stats(de, basis.cvar_alpha), sec_z0=float(z0[n].sec[0]) if z0[n].feasible[0] else float("nan")) for n, de in ev.items()}
    ok = [n for n in rows if n != "nominal_new" and rows[n]["feasible_fraction"] >= basis.chance_feasible_fraction]
    best = min(ok, key=lambda n: rows[n]["CVaR"]) if ok else None
    out = dict(protocol="nominal design re-optimised under the changed basis; main-run robust candidates re-evaluated (second stage re-optimised, S scenarios) "
                        "and the best chance-constraint-feasible one selected. The outer robust search is NOT re-run.",
               basis_override=MODEL_CASES[case], nominal_new=dict(sec=info["sec"], ua_spec=info["ua_spec"], mita=info["mita"], lng_N2_mol_pct=info["lng_N2_mol_pct"]),
               designs=rows, best_candidate=best, status="complete")
    if best:
        out["PoR_z0_fixed_candidate"] = (rows[best]["sec_z0"] - rows["nominal_new"]["sec_z0"]) / rows["nominal_new"]["sec_z0"]
    else:
        out["note"] = "no main-run candidate meets the chance constraint under this basis"
    return out


def _sens_archive(ctx, cycle, case):
    spec = ARCHIVE_CASES[case]
    basis = basis_for(ctx)
    alpha = spec.get("alpha", basis.cvar_alpha)
    pen = spec.get("sec_pen", basis.sec_penalty_kwh_per_kg)
    arch = load_archive(ctx, cycle, "cvar_iso")
    best, rows = None, []
    for a in arch:
        sec = np.where(np.array(a["feasible"]), np.array(a["sec"]), pen)
        ff = float(np.mean(a["feasible"]))
        obj = cvar(sec, alpha)
        rows.append((obj, ff, a["gen"], a["member"]))
        if ff >= basis.chance_feasible_fraction and (best is None or obj < best[0]):
            best = (obj, ff, a["gen"], a["member"], a["vec"])
    main = load_final(ctx, cycle, "cvar_iso")
    nom_across = pd.read_csv(ctx.input("across", cycle) / "across_summary.csv") if (ctx.input("across", cycle) / "across_summary.csv").exists() else None
    out = dict(protocol="re-selection among the main-run archive of evaluated first-stage designs with the changed alpha or penalty; no new evaluations",
               alpha=alpha, sec_pen=pen, n_archive=len(arch), status="complete")
    if best is None:
        out.update(note="no archive member meets the chance constraint", best=None)
    else:
        out.update(best=dict(objective=best[0], feasible_fraction=best[1], generation=best[2], member=best[3], vec=best[4]),
                   same_design_as_main=bool(main is not None and np.allclose(best[4], main["vec"])))
    # nominal design under the changed alpha/penalty: its scenario vector from the across unit
    ap = ctx.input("across", cycle) / "across_scenarios.parquet"
    if ap.exists():
        df = pd.read_parquet(ap)
        d = df[df.design == "nominal"]
        sec = np.where(d.feasible.values, d.sec.values, pen)
        out["nominal_CVaR"] = cvar(sec, alpha)
        out["nominal_feasible_fraction"] = float(d.feasible.mean())
        if best is not None:
            out["dCVaR_rel_vs_nominal"] = (best[0] - out["nominal_CVaR"]) / out["nominal_CVaR"]
    return out


def _sens_set(ctx, cycle, case, P):
    name = SET_CASES[case]
    basis = basis_for(ctx)
    scen, nom_feed, meta = scenario_set(ctx, basis, name)
    designs, nom = design_table(ctx, cycle, basis)
    sink = EvalSink(ctx.out, "evals")
    kw = dict(max_evals=P["max_evals"], n_restarts=P["n_restarts"], maxiter=12)
    ev = eval_designs_on_set(ctx, cycle, designs, scen, basis, nom, kw, f"sens_{case}", sink, load_models(ctx, cycle))
    sink.close()
    out = dict(protocol="main-run designs (nominal and robust) evaluated across the alternative scenario set, second stage re-optimised; designs are NOT re-optimised",
               set=name, kappa=meta["kappa"], anchors=meta["anchor_ids"], nominal_anchor_of_set=meta["nominal"]["nominal"], status="complete")
    out["designs"] = {n: _design_stats(de, basis.cvar_alpha) for n, de in ev.items()}
    by = {f.id: f for f in scen}
    per_parent = {}
    for n, de in ev.items():
        for sid, ok, s in zip(de.ids, de.feasible, de.sec):
            par = by[sid].parent_id or sid
            per_parent.setdefault(n, {}).setdefault(par, []).append((bool(ok), float(s)))
    out["by_parent_anchor"] = {n: {p: dict(n=len(v), feasible_fraction=float(np.mean([a for a, _ in v])),
                                            mean_sec_feasible=float(np.mean([s for a, s in v if a])) if any(a for a, _ in v) else float("nan"))
                                    for p, v in d.items()} for n, d in per_parent.items()}
    if "fieldD" in name or case == "fieldD":
        out["note"] = "Field D (A5) is outside LNG-grade nitrogen (42.74 mol% N2 before treatment); see by_parent_anchor[A5]"
    return out
