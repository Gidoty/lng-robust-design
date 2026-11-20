"""LEGACY single-process pipeline (first build, one anchor, in-memory). Superseded by lng_robust.study (chunked units, GitHub Actions workflow); kept for the
smoke test and for reproducing the first-build diagnostics. Do not use it for study results.

End-to-end pipeline.  python -m lng_robust.run --quick   (smoke test: proves the pipeline runs; NOT a result)
                         python -m lng_robust.run --full    (study-scale budgets; not exercised in the first build)

Pipeline per cycle: nominal NSGA-II -> performance of the nominal design across scenarios (second stage re-optimised)
-> two-stage CVaR design -> price of robustness -> surrogate dataset, grouped CV, FFR, surrogate screening with
rigorous re-verification. Every evaluation is logged with its failure code."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lng_robust.analysis import plots
from lng_robust.config import RUNS_DIR, load_basis
from lng_robust.doe.dirichlet import choose_kappa, sample_dirichlet
from lng_robust.doe.feeds import load_feeds
from lng_robust.evallog import EvalLog, git_hash
from lng_robust.opt import parallel
from lng_robust.opt.nominal import run_nominal
from lng_robust.opt.robust import (evaluate_scenarios, run_robust, stage1_vec_of_design, x1_from_vec)
from lng_robust.opt.common import cvar, nominal_var_names, price_of_robustness
from lng_robust.opt.space import STAGE2
from lng_robust.surrogate.screen import screen_and_reverify
from lng_robust.surrogate.train import build_dataset, grouped_cv

SMOKE = "SMOKE TEST - NOT A RESULT"
PRESETS = {
    "quick": dict(n_scen=20, nom_pop=20, nom_gen=10, rob_pop=4, rob_gen=2, rob_maxfev=16, doe=200, mshe_N=40, mshe_n_table=24,
                  screen_candidates=2000, screen_top_k=5, ref_maxfev=16),
    "full": dict(n_scen=200, nom_pop=100, nom_gen=100, rob_pop=24, rob_gen=30, rob_maxfev=40, doe=3000, mshe_N=100, mshe_n_table=48,
                 screen_candidates=20000, screen_top_k=10, ref_maxfev=40),
}


def _ensure_nominal_y(nominal):
    names = nominal_var_names(nominal.cycle)
    return np.array([nominal.best["vec"][names.index(n)] for n in STAGE2[nominal.cycle]])


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--quick", action="store_true")
    g.add_argument("--full", action="store_true")
    ap.add_argument("--cycles", default="smr,n2_single,n2_dual")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--capacity-tpd", type=float, default=100.0)
    ap.add_argument("--seed", type=int, default=20260101)
    ap.add_argument("--time-budget-min", type=float, default=45.0)
    ap.add_argument("--out", default=str(RUNS_DIR))
    a = ap.parse_args(argv)
    mode = "quick" if a.quick else "full"
    if a.full:
        print("WARNING: the 'full' preset is a placeholder and has NOT been run. At about 0.5 s per rigorous evaluation the "
              "preset implies roughly 6 million second-stage evaluations per cycle and capacity (see STATUS.md). "
              "Reduce rob_pop, rob_gen, n_scen and rob_maxfev, or use surrogate-assisted second stages, before running it.")
    smoke = a.quick
    P = PRESETS[mode]
    t_start = time.time()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(a.out) / f"{stamp}_{mode}{'_SMOKE' if smoke else ''}"
    out.mkdir(parents=True, exist_ok=True)
    basis = load_basis().override(mshe_N=P["mshe_N"], mshe_n_table=P["mshe_n_table"], random_seed=a.seed)
    label = SMOKE if smoke else ""
    cfg = dict(mode=mode, label=label, args=vars(a), preset=P, git_hash=git_hash(),
               requirements_lock_sha256=hashlib.sha256(Path(__file__).parents[1].joinpath("requirements.lock").read_bytes()).hexdigest()[:16],
               basis_digest=basis.digest(), basis_values=basis.values, basis_status=basis.status, utc=stamp)
    (out / "config.json").write_text(json.dumps(cfg, indent=2, default=str))
    if smoke:
        (out / "SMOKE_TEST_NOT_A_RESULT.txt").write_text("This folder is the output of a --quick smoke test. It proves the pipeline runs. "
                                                         "No number here is a result, a finding or a benchmark.\n")
    print(f"[{mode}] output: {out}")
    m_lng = a.capacity_tpd * 1000.0 / 86400.0
    anchors, todo = load_feeds(basis)
    anchor = anchors[0]
    kappa, kappa_note = choose_kappa(anchors)
    scen = sample_dirichlet(anchor, kappa, P["n_scen"], a.seed, basis)
    log = EvalLog(f"{stamp}", a.seed, smoke)
    plots.envelope(anchors, scen, out / "fig_envelope.png", smoke)
    pd.DataFrame([dict(id=f.id, synthetic=f.synthetic, parent=f.parent_id, kappa=f.kappa, source=f.source, grade=f.grade,
                       **{f"treated_{k}": v for k, v in f.treated.items()}, label=label) for f in anchors + scen]).to_csv(out / "feeds_used.csv", index=False)
    print(f"anchors: {[f.id for f in anchors]}  TODO rows skipped: {[t['id'] for t in todo]}  kappa={kappa} ({kappa_note})")

    summary_rows, timing_rows, notes = [], [], []
    fronts, sec_dists, surr_metrics, surr_checks = {}, {}, [], []
    oof_for_plot = {}
    for cycle in a.cycles.split(","):
        def over():
            return (time.time() - t_start) / 60 > a.time_budget_min
        if over():
            notes.append(f"{cycle}: SKIPPED, time budget exceeded"); continue
        t0 = time.time()
        print(f"\n=== {cycle}: nominal NSGA-II (pop {P['nom_pop']}, gen {P['nom_gen']}) ===", flush=True)
        n0 = len(log.rows)
        nom = run_nominal(cycle, anchor.treated, anchor.id, m_lng, basis, pop=P["nom_pop"], n_gen=P["nom_gen"], seed=a.seed, log=log,
                          workers=a.workers, capacity_tpd=a.capacity_tpd)
        fronts[cycle] = nom.front
        nom_t = time.time() - t0
        print(f"  evals {nom.n_evals}  feasible_found={nom.feasible_found}  {nom.note}  ({nom_t:.0f}s)", flush=True)
        row = dict(cycle=cycle, nominal_feasible_found=nom.feasible_found, nominal_note=nom.note, nominal_evals=nom.n_evals, label=label)
        if nom.best is None:
            summary_rows.append(row)
            notes.append(f"{cycle}: no feasible nominal design within the budget; robust and surrogate-screen steps skipped for it")
            # the surrogate dataset is still built so the classifier can be assessed
        else:
            b = nom.best
            row.update(nominal_sec=b["sec"], nominal_ua_spec=b["ua_spec"], nominal_mita=b["mita"],
                       nominal_exergy_eff=b["result"].exergy_eff)
            y0 = _ensure_nominal_y(nom)
            x1_nom = x1_from_vec(cycle, stage1_vec_of_design(cycle, b, m_lng), m_lng)
            if not over():
                print("  nominal design across scenarios (second stage re-optimised)", flush=True)
                sec_n, feas_n, _, n_n = evaluate_scenarios(cycle, scen, m_lng, x1_nom, y0, basis, P["ref_maxfev"], a.workers, log=log,
                                                           capacity_tpd=a.capacity_tpd, purpose="nominal_design_across_scenarios")
                sec_z0n, feas_z0n, _, _ = evaluate_scenarios(cycle, [anchor], m_lng, x1_nom, y0, basis, P["ref_maxfev"], a.workers, log=log,
                                                             capacity_tpd=a.capacity_tpd, purpose="nominal_design_at_z0")
                row.update(nominal_cvar=cvar(sec_n, basis.cvar_alpha), nominal_feasible_fraction=float(feas_n.mean()),
                           nominal_sec_at_z0_reopt=float(sec_z0n[0]))
                sec_dists[f"{cycle}\nnominal design"] = sec_n
            if not over():
                print(f"=== {cycle}: two-stage CVaR (pop {P['rob_pop']}, gen {P['rob_gen']}, inner maxfev {P['rob_maxfev']}, S={len(scen)}) ===", flush=True)
                t1 = time.time()
                rob = run_robust(cycle, scen, m_lng, basis, b, risk="cvar", pop=P["rob_pop"], n_gen=P["rob_gen"], maxfev=P["rob_maxfev"],
                                 seed=a.seed, workers=a.workers, log=log, capacity_tpd=a.capacity_tpd)
                print(f"  outer evals {rob.n_outer_evals}, rigorous evals {rob.n_rigorous_evals}, feasible_design={rob.feasible_design} {rob.note} ({time.time()-t1:.0f}s)", flush=True)
                sec_zr, feas_zr, _, _ = evaluate_scenarios(cycle, [anchor], m_lng, rob.x1, y0, basis, P["ref_maxfev"], a.workers, log=log,
                                                           capacity_tpd=a.capacity_tpd, purpose="robust_design_at_z0")
                row.update(robust_feasible_design=rob.feasible_design, robust_cvar=rob.cvar, robust_worst=rob.worst,
                           robust_feasible_fraction=rob.feasible_fraction, robust_sec_at_z0_reopt=float(sec_zr[0]),
                           robust_note=rob.note, robust_outer_evals=rob.n_outer_evals, robust_rigorous_evals=rob.n_rigorous_evals)
                if "nominal_sec_at_z0_reopt" in row and feas_z0n[0] and feas_zr[0]:
                    row["price_of_robustness_pct"] = 100 * price_of_robustness(row["robust_sec_at_z0_reopt"], row["nominal_sec_at_z0_reopt"])
                sec_dists[f"{cycle}\nCVaR design"] = np.array(rob.sec_by_scenario)
            summary_rows.append(row)
        timing_rows.append(dict(cycle=cycle, stage="nominal_nsga2", seconds=nom_t, rigorous_evals=nom.n_evals, label=label))
        # ---- surrogate pipeline ----
        if not over():
            print(f"=== {cycle}: surrogate dataset (n={P['doe']}) + grouped CV ===", flush=True)
            t2 = time.time()
            df, names = build_dataset(cycle, [anchor] + scen, m_lng, basis, P["doe"], a.seed, log=log, workers=a.workers,
                                      capacity_tpd=a.capacity_tpd, group_by_anchor=(mode == "full"))
            met, oof = grouped_cv(df, basis.mita_min_K, a.seed)
            met.insert(0, "cycle", cycle)
            met["label"] = label
            surr_metrics.append(met)
            oof_for_plot[cycle] = oof
            df.assign(cycle=cycle, label=label).to_csv(out / f"surrogate_dataset_{cycle}.csv", index=False)
            chk, why = screen_and_reverify(cycle, df, anchor.treated, anchor.id, m_lng, basis, n_candidates=P["screen_candidates"],
                                           top_k=P["screen_top_k"], seed=a.seed, log=log, workers=a.workers, capacity_tpd=a.capacity_tpd)
            if why:
                notes.append(f"{cycle}: surrogate screening not done: {why}")
            else:
                chk["label"] = label
                surr_checks.append(chk)
            timing_rows.append(dict(cycle=cycle, stage="surrogate_dataset_cv_screen", seconds=time.time() - t2, rigorous_evals=P["doe"] + P["screen_top_k"], label=label))
            print(f"  done ({time.time()-t2:.0f}s)", flush=True)
        else:
            notes.append(f"{cycle}: surrogate stage SKIPPED, time budget exceeded")
    parallel.shutdown()

    # ---- write outputs ----
    pd.DataFrame(summary_rows).to_csv(out / "design_summary.csv", index=False)
    pd.DataFrame(timing_rows).to_csv(out / "timing.csv", index=False)
    if surr_metrics:
        pd.concat(surr_metrics).to_csv(out / "surrogate_metrics.csv", index=False)
    if surr_checks:
        pd.concat(surr_checks).to_csv(out / "surrogate_vs_rigorous.csv", index=False)
    for cyc, front in fronts.items():
        if front:
            pd.DataFrame(front).assign(cycle=cyc, label=label).to_csv(out / f"nominal_front_{cyc}.csv", index=False)
    log.save(out / "evaluations.csv")
    plots.pareto(fronts, out / "fig_nominal_fronts.png", smoke)
    if sec_dists:
        plots.sec_distribution(sec_dists, out / "fig_scenario_sec.png", smoke, basis.sec_penalty_kwh_per_kg)
    for cyc, oof in oof_for_plot.items():
        plots.parity(oof, ["linear_ridge", "gradient_boosting", "gaussian_process"], out / f"fig_surrogate_parity_{cyc}.png", smoke)
        plots.ffr_vs_distance(oof, "gradient_boosting", basis.mita_min_K, out / f"fig_ffr_{cyc}.png", smoke)
    ev = log.frame()
    code_counts = ev.groupby(["cycle", "failure_code"]).size().rename("n").reset_index() if len(ev) else pd.DataFrame()
    code_counts.to_csv(out / "failure_code_counts.csv", index=False)
    md = [f"# {'SMOKE TEST - NOT A RESULT' if smoke else 'Run summary'}", "",
          f"mode={mode}  git={cfg['git_hash']}  seed={a.seed}  wall time {(time.time()-t_start)/60:.1f} min", "",
          "This file reports pipeline status only. It does not summarise any number as a finding.", "",
          f"- rigorous evaluations logged: {len(ev)} (every one, including failures, in evaluations.csv)",
          f"- scenarios: {len(scen)} synthetic compositions around anchor {anchor.id} (kappa {kappa}: {kappa_note})",
          "- anchors still TODO in feeds.csv: " + ", ".join(t["id"] for t in todo), ""]
    md += [f"- {n}" for n in notes]
    (out / ("SUMMARY_SMOKE.md" if smoke else "SUMMARY.md")).write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nfinished in {(time.time()-t_start)/60:.1f} min; output {out}")
    return out


if __name__ == "__main__":
    main()
