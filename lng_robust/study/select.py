"""Request 12, 13, 14, 15, 17, 18: select the reported designs from the existing robust archives, without any new search.

`candidate_list`   deterministic list of first-stage designs taken from the archives of run 44682889025: the nominal design, the designs
                   reported before, and the best designs by archived CVaR and by archived worst case (iso-UA pool = cvar_iso + worst_iso
                   archives; the 1.25 pool adds the cvar_125 archive).
`unit_evalcand`    one candidate re-evaluated on the same 50 scenarios with the same second-stage budget (across quality), seeded with
                   the design's best known feasible points (its own solves in the run's shards) and the nominal operating point; SEC at z0 by
                   three searches.
`select_designs`   the reported design of each variant is the best of the re-evaluated candidates by the rule the GA used
                   (chance constraint first, then the objective). Pure function, tested.
`unit_across`      aggregates the re-evaluated candidates: selected designs, price of robustness, failure-code counts, per-scenario table."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from lng_robust.analysis import por as por_mod
from lng_robust.cycles import solve
from lng_robust.opt.common import cvar, nominal_var_names
from lng_robust.opt.robust import stage1_vec_of_design, x1_from_vec
from lng_robust.opt.space import STAGE2
from lng_robust.study.common import M_LNG, basis_for, load_nominal, nominal_design_dict, scenario_set, write_done
from lng_robust.study.config import VARIANTS
from lng_robust.study.store import EvalSink, Timer
from lng_robust.study.units import eval_designs_on_set, load_archive, load_final, load_models

N_SLOTS = 12          # evalcand jobs per cycle in the workflow; slots beyond the candidate list are no-ops


def _key(vec):
    return tuple(round(float(v), 9) for v in vec)


def _cv(ff, chance):
    return max(0.0, chance - ff)


def rank_key(ff, objective, chance):
    """The GA's feasibility rule as a sort key: chance constraint met first (then the objective); otherwise the smaller violation."""
    cv = _cv(ff, chance)
    return (0, objective) if cv <= 0 else (1, cv, objective)


def candidate_list(ctx, cycle, basis, k_iso_cvar=3, k_iso_worst=2, k_125=3):
    nom = load_nominal(ctx, cycle)
    chance = basis.chance_feasible_fraction
    arch = {v: [dict(a, variant=v) for a in load_archive(ctx, cycle, v)] for v in VARIANTS}
    iso = arch["cvar_iso"] + arch["worst_iso"]
    allp = iso + arch["cvar_125"]
    cands, seen = [], {}

    def add(name, origin, vec, pools, a=None):
        k = "nominal" if vec is None else _key(vec)
        if k in seen:
            seen[k]["origins"].append(origin)
            return
        c = dict(name=name, origins=[origin], vec=None if vec is None else list(map(float, vec)), pools=sorted(pools))
        if a is not None:
            c["archived"] = dict(cvar=a["cvar"], worst=a["worst"], feasible_fraction=a["feasible_fraction"], gen=a["gen"], member=a["member"], variant=a["variant"])
        cands.append(c)
        seen[k] = c

    add("nominal", "nominal design (NSGA-II knee)", None, ["iso", "125"])
    for v in VARIANTS:                                    # the designs reported before this selection (final.json of each chain)
        fin = load_final(ctx, cycle, v)
        if fin is not None:
            a = next((a for a in arch[v] if _key(a["vec"]) == _key(fin["vec"])), None)
            add(f"c{len(cands):02d}", f"reported by chain {v} (generation {fin['generation']})", fin["vec"], ["iso", "125"] if v != "cvar_125" else ["125"], a)
    for a in sorted(iso, key=lambda a: rank_key(a["feasible_fraction"], a["cvar"], chance))[:k_iso_cvar]:
        add(f"c{len(cands):02d}", f"top archived CVaR, iso-UA pool ({a['variant']} g{a['gen']} m{a['member']})", a["vec"], ["iso", "125"], a)
    for a in sorted(iso, key=lambda a: rank_key(a["feasible_fraction"], a["worst"], chance))[:k_iso_worst]:
        add(f"c{len(cands):02d}", f"top archived worst case, iso-UA pool ({a['variant']} g{a['gen']} m{a['member']})", a["vec"], ["iso", "125"], a)
    for a in sorted(allp, key=lambda a: rank_key(a["feasible_fraction"], a["cvar"], chance))[:k_125]:
        add(f"c{len(cands):02d}", f"top archived CVaR, 1.25 pool ({a['variant']} g{a['gen']} m{a['member']})", a["vec"], ["iso", "125"] if a["variant"] != "cvar_125" else ["125"], a)
    x1_nom = x1_from_vec(cycle, stage1_vec_of_design(cycle, nominal_design_dict(nom), M_LNG), M_LNG)
    ua_iso = x1_nom["ua_installed_kw_per_K"] * (1 + 1e-9)
    for c in cands:     # pools follow the installed UA: iso-UA means not above the nominal design's UA (the 1.25 pool admits every candidate)
        c["x1"] = x1_nom if c["vec"] is None else x1_from_vec(cycle, np.asarray(c["vec"], float), M_LNG)
        c["pools"] = ["125"] + (["iso"] if c["x1"]["ua_installed_kw_per_K"] <= ua_iso else [])
        c["origin"] = "; ".join(c["origins"])
    return cands[:N_SLOTS], nom


def known_points_from_shards(ctx, cycle, cand):
    """Best known feasible operating point of the candidate for every scenario: its own second-stage solves in the run's shards."""
    a = cand.get("archived")
    if not a:
        return {}
    tag = f"{a['variant']}-g{a['gen']}-m{a['member']}"
    cols = ["member", "feed_id", "feasible", "sec"] + [f"x_{n}" for n in STAGE2[cycle]]
    parts = []
    for p in sorted(ctx.work.glob(f"shards-robust-{cycle}-{a['variant']}-s*/evals-*.parquet")):
        try:
            d = pd.read_parquet(p, columns=cols)
        except Exception:
            continue
        d = d[(d.member == tag) & d.feasible.astype(bool)]
        if len(d):
            parts.append(d)
    if not parts:
        return {}
    d = pd.concat(parts)
    d = d.sort_values("sec").drop_duplicates("feed_id")
    return {r.feed_id: [[float(getattr(r, f"x_{n}")) for n in STAGE2[cycle]]] for r in d.itertuples()}


def unit_evalcand(ctx):
    cycle, idx = ctx.cycle, int(ctx.case)
    basis = basis_for(ctx)
    P = ctx.preset["across"]
    sel = ctx.preset.get("select", {})
    cands, nom = candidate_list(ctx, cycle, basis, **sel)
    if idx >= len(cands):
        write_done(ctx.out, unit="evalcand", cycle=cycle, case=ctx.case, status="complete", note="no candidate in this slot")
        return None
    c = cands[idx]
    scen, nom_feed, meta = scenario_set(ctx, basis)
    models = load_models(ctx, cycle)
    sink = EvalSink(ctx.out, "evals")
    t = Timer()
    name = c["name"]
    known = {name: known_points_from_shards(ctx, cycle, c)}
    kw = dict(max_evals=P["max_evals"], n_restarts=P["n_restarts"], maxiter=P["maxiter"])
    res = eval_designs_on_set(ctx, cycle, {name: c["x1"]}, scen, basis, nom, kw, "evalcand", sink, models, known=known)[name]
    z0 = eval_designs_on_set(ctx, cycle, {name: c["x1"]}, [nom_feed], basis, nom, kw, "evalcand_z0", sink, models, known=known)[name]
    kw_long = dict(max_evals=P["z0_long_evals"], n_restarts=3, maxiter=20)
    z0_long = eval_designs_on_set(ctx, cycle, {name: c["x1"]}, [nom_feed], basis, nom, kw_long, "evalcand_z0_long", sink, models, known=known)[name]
    z0_nm = eval_designs_on_set(ctx, cycle, {name: c["x1"]}, [nom_feed], basis, nom, dict(method="nm", maxfev=P["z0_nm_evals"]), "evalcand_z0_nm", sink, None, known=known)[name]
    sink.close()
    z0s = {k: float(v.sec[0]) for k, v in (("scenario_search", z0), ("hybrid_long", z0_long), ("nelder_mead_long", z0_nm)) if v.feasible[0]}
    z0y = {k: v.y.get(nom_feed.id) for k, v in (("scenario_search", z0), ("hybrid_long", z0_long), ("nelder_mead_long", z0_nm))}
    if name == "nominal" and nom.get("sec") == nom.get("sec"):
        z0s["nominal_nsga2_own_optimum"] = float(nom["sec"])
        z0y["nominal_nsga2_own_optimum"] = nominal_design_dict(nom)["vec"][:len(STAGE2[cycle])]
    sc = {f.id: f for f in scen}
    detail = []
    for i, (sid, d) in enumerate(zip(res.ids, res.detail)):
        detail.append(dict(scenario=sid, synthetic=bool(sc[sid].synthetic), parent=sc[sid].parent_id or "", sec=float(res.sec[i]), feasible=bool(res.feasible[i]),
                           mita=d["mita"], ua=d["ua"], n_ref=d["n_ref"], lng_N2_mol_pct=d["lng_N2_mol_pct"], fail_code=d["fail_code"], fail_codes=d["fail_codes"],
                           n_evals=d["n_evals"], y=res.y.get(sid), n2_pct_feed=100 * sc[sid].treated.get("N2", 0.0)))
    out = dict(cycle=cycle, name=name, origin=c["origin"], pools=c["pools"], vec=c["vec"], x1=c["x1"], archived=c.get("archived"),
               cvar=float(res.cvar(basis.cvar_alpha)), worst=float(res.worst), feasible_fraction=float(res.feasible_fraction),
               sec=[float(v) for v in res.sec], feasible=[bool(v) for v in res.feasible], ids=list(res.ids), detail=detail, n_evals=int(res.n_evals),
               n_known_seed_scenarios=len(known[name]), sec_z0_searches=z0s, sec_z0_search_points=z0y, minutes=t.minutes())
    (ctx.out / "cand.json").write_text(json.dumps(out, default=float))
    write_done(ctx.out, unit="evalcand", cycle=cycle, case=ctx.case, status="complete", minutes=t.minutes(), design=name, origin=c["origin"])
    return out


def select_designs(cands: list, chance: float, alpha_unused=None):
    """cands: list of dicts with name, pools, cvar, worst, feasible_fraction. Returns {variant: candidate}.
    cvar_iso and worst_iso choose from the iso-UA pool (nominal included); cvar_125 from every candidate."""
    iso = [c for c in cands if "iso" in c["pools"]]
    allc = [c for c in cands if "125" in c["pools"]]
    pick = lambda pool, f: min(pool, key=lambda c: rank_key(c["feasible_fraction"], c[f], chance) + (c["name"],))
    return {"cvar_iso": pick(iso, "cvar"), "worst_iso": pick(iso, "worst"), "cvar_125": pick(allc, "cvar")}


def failure_code_table(rows):
    """rows: per-scenario dicts with design, synthetic, feasible, fail_code. Counts of each failure code by anchors and synthetic."""
    out = {}
    for r in rows:
        if r["feasible"]:
            continue
        k = (r["design"], "synthetic" if r["synthetic"] else "anchor", r["fail_code"] or "UNKNOWN")
        out[k] = out.get(k, 0) + 1
    return out


def unit_across(ctx):
    cycle = ctx.cycle
    basis = basis_for(ctx)
    P = ctx.preset["across"]
    scen, nom_feed, meta = scenario_set(ctx, basis)
    nom = load_nominal(ctx, cycle)
    models = load_models(ctx, cycle)
    t = Timer()
    cands = []
    for d in sorted(ctx.work.glob(f"unit-evalcand-{cycle}-*")):
        p = d / "cand.json"
        if p.exists():
            cands.append(json.loads(p.read_text()))
    cands.sort(key=lambda c: (c["name"] != "nominal", c["name"]))
    if not cands or cands[0]["name"] != "nominal":
        raise RuntimeError("evalcand outputs missing (nominal candidate not found)")
    chance = basis.chance_feasible_fraction
    chosen = select_designs(cands, chance)
    # transparency table: every candidate, archived against re-evaluated values, and which variant selected it
    selrows = []
    for c in cands:
        a = c.get("archived") or {}
        selrows.append(dict(cycle=cycle, candidate=c["name"], origin=c["origin"], pools=",".join(c["pools"]), archived_CVaR=a.get("cvar"), archived_worst=a.get("worst"),
                            archived_feasible_fraction=a.get("feasible_fraction"), archived_generation=a.get("gen"), reeval_CVaR=c["cvar"], reeval_worst=c["worst"],
                            reeval_feasible_fraction=c["feasible_fraction"], chance_met=c["feasible_fraction"] >= chance,
                            selected_for=",".join(v for v, ch in chosen.items() if ch["name"] == c["name"])))
    pd.DataFrame(selrows).to_csv(ctx.out / "selection_table.csv", index=False)
    designs = {"nominal": cands[0], **{v: chosen[v] for v in VARIANTS}}
    sc_by_id = {f.id: f for f in scen}
    alpha = basis.cvar_alpha
    rows, summary, scen_rows = [], [], []
    sec_z0 = {}
    for name, c in designs.items():
        z = c["sec_z0_searches"]
        search_only = {k: v for k, v in z.items() if k != "nominal_nsga2_own_optimum"}
        best = min(z.values()) if z else float("nan")
        spread = (max(search_only.values()) - min(search_only.values())) / min(search_only.values()) if len(search_only) >= 2 else float("nan")
        sec_z0[name] = dict(best=best, candidates=z, spread_fraction=spread, source_candidate=c["name"])
        sec_arr = np.array(c["sec"])
        feas = np.array(c["feasible"], bool)
        ids = c["ids"]
        for d in c["detail"]:
            scen_rows.append(dict(cycle=cycle, design=name, source_candidate=c["name"], scenario=d["scenario"], synthetic=d["synthetic"], parent=d["parent"],
                                  sec=d["sec"] if d["feasible"] else float("nan"), sec_with_penalty=d["sec"], mita=d["mita"], ua_kw_per_K=d["ua"], n_ref=d["n_ref"],
                                  lng_N2_mol_pct=d["lng_N2_mol_pct"], feasible=d["feasible"], failure_code=d["fail_code"], n_evaluations=d["n_evals"],
                                  n2_pct_feed=d["n2_pct_feed"], y=json.dumps(d["y"])))
            rows.append(dict(design=name, scenario=d["scenario"], synthetic=d["synthetic"], parent=d["parent"], sec=d["sec"], feasible=d["feasible"], mita=d["mita"],
                             ua_kw_per_K=d["ua"], n_ref=d["n_ref"], lng_N2_mol_pct=d["lng_N2_mol_pct"], n2_pct_feed=d["n2_pct_feed"], y=json.dumps(d["y"]),
                             failure_code=d["fail_code"]))
        an = [i for i, s in enumerate(ids) if not sc_by_id[s].synthetic]
        sy = [i for i, s in enumerate(ids) if sc_by_id[s].synthetic]
        summary.append(dict(cycle=cycle, design=name, source_candidate=c["name"], origin=c["origin"], CVaR=float(cvar(sec_arr, alpha)), worst=float(sec_arr.max()),
                            feasible_fraction=float(feas.mean()), chance_met=bool(feas.mean() >= chance),
                            mean_sec_feasible=float(sec_arr[feas].mean()) if feas.any() else float("nan"),
                            sec_z0=best, feasible_z0=bool(best == best), sec_z0_min=min(search_only.values()) if search_only else float("nan"),
                            sec_z0_max=max(search_only.values()) if search_only else float("nan"), sec_z0_spread_pct=100 * spread,
                            n_anchor_feasible=int(feas[an].sum()), n_anchor=len(an), n_synth_feasible=int(feas[sy].sum()), n_synth=len(sy)))
    pd.DataFrame(rows).to_parquet(ctx.out / "across_scenarios.parquet", index=False)
    per = pd.DataFrame(scen_rows)
    per.to_csv(ctx.out / "per_scenario.csv", index=False)
    pd.DataFrame(summary).to_csv(ctx.out / "across_summary.csv", index=False)
    # failure codes (request 14)
    fc = failure_code_table(per.rename(columns={"failure_code": "fail_code"}).assign(design=per.design).to_dict("records"))
    pd.DataFrame([dict(cycle=cycle, design=k[0], group=k[1], failure_code=k[2], n=v) for k, v in sorted(fc.items())],
                 columns=["cycle", "design", "group", "failure_code", "n"]).to_csv(ctx.out / "failure_codes.csv", index=False)
    # price of robustness (requests 17, 18)
    nd = designs["nominal"]
    por_rows = []
    for name, c in designs.items():
        if name == "nominal":
            continue
        s = por_mod.por_summary(np.array(c["sec"]), np.array(nd["sec"]), np.array(c["feasible"]), np.array(nd["feasible"]), sec_z0[name]["best"],
                                sec_z0["nominal"]["best"], alpha, B=ctx.preset["bootstrap"], seed=ctx.seed)
        tol = np.nanmax([sec_z0[name]["spread_fraction"], sec_z0["nominal"]["spread_fraction"]])
        por_rows.append(dict(cycle=cycle, design=name, source_candidate=c["name"], feasible_z0_robust=bool(sec_z0[name]["best"] == sec_z0[name]["best"]),
                             feasible_z0_nominal=bool(sec_z0["nominal"]["best"] == sec_z0["nominal"]["best"]), sec_z0_robust=sec_z0[name]["best"],
                             sec_z0_nominal=sec_z0["nominal"]["best"], z0_search_spread_fraction=float(tol),
                             PoR_z0_within_z0_spread=bool(abs(s["PoR_z0"]) <= tol) if tol == tol else None,
                             **s))
    pd.DataFrame(por_rows).to_csv(ctx.out / "price_of_robustness.csv", index=False)
    (ctx.out / "sec_z0_candidates.json").write_text(json.dumps(sec_z0, indent=2, default=float))
    # designs at z0 (Tables 5 and 6): one serial re-solve at the best z0 operating point
    dz = {}
    for name, c in designs.items():
        z = c["sec_z0_searches"]
        if not z:
            dz[name] = dict(feasible=False)
            continue
        bk = min(z, key=z.get)
        y = c["sec_z0_search_points"].get(bk)
        x = dict(c["x1"])
        x.update({n: v for n, v in zip(STAGE2[cycle], y)})
        r = solve(cycle, nom_feed.treated, basis.feed_T, basis.feed_P, M_LNG, x, basis)
        ro = r.as_row()
        dz[name] = dict(feasible=bool(r.feasible), sec=float(r.sec), exergy_eff=float(r.exergy_eff), mita=float(r.mita), ua_kw_per_K=float(r.ua),
                        lng_N2_mol_pct=float(ro["lng_N2_mol_pct"]), exergy_destruction_kw=r.exergy_destruction_kw, w_comp_kw=float(r.w_comp_kw),
                        w_exp_kw=float(r.w_exp_kw), ua_installed_kw_per_K=float(c["x1"].get("ua_installed_kw_per_K", np.nan)),
                        n_ref_rated_mol_s=float(c["x1"].get("n_ref_rated_mol_s", np.nan)), operating=dict(zip(STAGE2[cycle], [float(v) for v in y])),
                        refrigerant=c["x1"].get("ref"), z0_search_used=bk)
    (ctx.out / "designs_at_z0.json").write_text(json.dumps(dz, indent=2, default=float))
    # selected designs for the downstream units: equipment, origin, best known operating point per scenario
    (ctx.out / "selected_designs.json").write_text(json.dumps(
        {name: dict(x1=c["x1"], vec=c["vec"], source_candidate=c["name"], origin=c["origin"], y_by_scenario={d["scenario"]: d["y"] for d in c["detail"] if d["y"] is not None})
         for name, c in designs.items()}, default=float))
    # surrogate against rigorous at the optima (Figure 8)
    from lng_robust.surrogate.train import alr_features
    reg, clf = models["regs"]["gradient_boosting"], models["clfs"]["gradient_boosting"]
    names = nominal_var_names(cycle)
    sv = []
    for name, c in designs.items():
        x1 = c["x1"]
        for d in c["detail"]:
            y = d["y"]
            if y is None:
                continue
            v = [dict(zip(STAGE2[cycle], y)).get(n) if n in STAGE2[cycle] else (x1.get("ref") or {}).get(n[2:], 0.0) for n in names]
            X = np.array([v + alr_features(sc_by_id[d["scenario"]].treated)])
            sv.append(dict(cycle=cycle, design=name, scenario=d["scenario"], rigorous_sec=d["sec"], surrogate_sec=float(reg.predict(X)[0]),
                           surrogate_prob_feasible=float(clf.predict_proba(X)[0, 1]), rigorous_feasible=True))
    pd.DataFrame(sv).to_csv(ctx.out / "surrogate_vs_rigorous_at_optima.csv", index=False)
    write_done(ctx.out, unit="across", cycle=cycle, status="complete", minutes=t.minutes(), designs={k: v["name"] for k, v in designs.items()}, n_candidates=len(cands))
    return summary
