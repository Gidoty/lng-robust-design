"""Merge unit outputs into the results package: tables T3 to T7 (CSV), Figure_1 to Figure_9 (600 dpi PNG and vector PDF),
provenance.json and RESULTS_SUMMARY.md (every headline number with its source file and row).

Only rigorous-model numbers are reported. Surrogate quantities appear only in the surrogate-reliability table and figures and are
labelled as such. A missing or partial unit is listed under INCOMPLETE; nothing is filled in."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

from lng_robust.analysis import figures as F
from lng_robust.analysis.reversal import assign_cells, reversal_table
from lng_robust.config import DATA_DIR, RUNS_DIR, load_basis
from lng_robust.doe.envelope import envelope_definitions
from lng_robust.doe.feeds import load_feeds
from lng_robust.study.config import ALL_SENS_CASES, CYCLES, VARIANTS
from lng_robust.study.store import read_parts

PKGS = ["thermo", "chemicals", "fluids", "neqsim", "scikit-learn", "pymoo", "SALib", "numpy", "scipy", "pandas", "pyarrow", "CoolProp",
        "matplotlib", "joblib", "PyYAML", "pytest"]


class Headlines:
    def __init__(self):
        self.rows = []

    def add(self, label, value, unit, file, row, column):
        self.rows.append(dict(label=label, value=value, unit=unit, source_file=file, source_row=row, source_column=column))

    def markdown(self):
        lines = ["| Quantity | Value | Unit | Source file | Row | Column |", "|---|---|---|---|---|---|"]
        for r in self.rows:
            v = r["value"]
            vs = f"{v:.4g}" if isinstance(v, (float, np.floating)) else str(v)
            lines.append(f"| {r['label']} | {vs} | {r['unit']} | `{r['source_file']}` | {r['source_row']} | {r['source_column']} |")
        return "\n".join(lines)


def _read(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def collect_done(work: Path):
    out = []
    for d in sorted(work.glob("unit-*")):
        j = _read(d / "done.json")
        if j:
            out.append(dict(folder=d.name, **{k: v for k, v in j.items() if k not in ("by_source", "groups")}))
        else:
            out.append(dict(folder=d.name, status="INCOMPLETE_no_done_json"))
    return out


def provenance(work: Path, out: Path, run_id: str, preset: str, seed: int, done: list):
    def v(p):
        try:
            return metadata.version(p)
        except Exception:
            return None
    try:
        sha = os.environ.get("GITHUB_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parents[2]).decode().strip()
    except Exception:
        sha = "unknown"
    prov = dict(run_id=run_id, preset=preset, commit_hash=sha, seeds=dict(global_seed=seed, scenario_seed=seed, note="all unit seeds derive from the global seed"),
                package_versions={p: v(p) for p in PKGS}, python=sys.version, platform=platform.platform(), cpu_count=os.cpu_count(),
                runner=dict(name=os.environ.get("RUNNER_NAME"), os=os.environ.get("RUNNER_OS"), arch=os.environ.get("RUNNER_ARCH")),
                source_run_id=os.environ.get("SOURCE_RUN_ID"),
                github=dict(run_id=os.environ.get("GITHUB_RUN_ID"), run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"), repository=os.environ.get("GITHUB_REPOSITORY"),
                            ref=os.environ.get("GITHUB_REF")),
                requirements_lock_sha256=__import__("hashlib").sha256((Path(__file__).parents[2] / "requirements.lock").read_bytes()).hexdigest()
                if (Path(__file__).parents[2] / "requirements.lock").exists() else None,
                design_basis_digest=load_basis().digest(), units=done)
    (out / "provenance.json").write_text(json.dumps(prov, indent=2, default=str))
    return prov


def build(work: Path, out: Path, run_id: str = "local", preset: str = "full", seed: int = 20260101):
    out = Path(out)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    H = Headlines()
    basis = load_basis()
    done = collect_done(work)
    incomplete = [d for d in done if str(d.get("status", "")).startswith(("INCOMPLETE", "partial"))]
    T = out / "tables"

    # ---- T3: benchmark reproduction (from the validation harness; produced before the study)
    vp = RUNS_DIR / "validation_summary.csv"
    if vp.exists():
        pd.read_csv(vp).to_csv(T / "T3_benchmark_reproduction.csv", index=False)

    # ---- T4: feed register
    feeds, _ = load_feeds(basis)
    t4 = pd.DataFrame([dict(id=f.id, facility=f.facility, source=f.source, grade=f.grade, **f.raw_mol_pct, printed_sum=f.raw_sum,
                            in_main_envelope=f.id not in basis.main_envelope_excluded_anchors) for f in feeds])
    t4.to_csv(T / "T4_feed_compositions.csv", index=False)

    # ---- T5 nominal designs, nominal front, composite curves
    t5, fronts, selected, curves = [], {}, {}, {}
    for c in CYCLES:
        nom = _read(work / f"unit-nominal-{c}" / "nominal.json")
        if not nom or "sec" not in nom:
            continue
        t5.append(dict(cycle=c, nominal_anchor=nom["nominal_anchor"], SEC_kWh_per_kg=nom["sec"], exergy_efficiency_pct=100 * nom["exergy_eff"], MITA_K=nom["mita"],
                       UA_kW_per_K=nom["ua_kw_per_K"], UA_specific_kW_per_K_per_kgs=nom["ua_spec"], LNG_N2_mol_pct=nom["lng_N2_mol_pct"],
                       compressor_kW=nom["w_comp_kw"], expander_kW=nom["w_exp_kw"],
                       **{f"exergy_destruction_{k}_kW": v for k, v in nom["exergy_destruction_kw"].items()}))
        fronts[c] = nom["front"]
        selected[c] = (nom["ua_spec"], nom["sec"])
        curves[c] = nom.get("composite")
        r = len(t5) - 1
        H.add(f"Nominal SEC ({c})", nom["sec"], "kWh/kg", "tables/T5_nominal_designs.csv", f"cycle={c}", "SEC_kWh_per_kg")
        H.add(f"Nominal LNG N2 content ({c})", nom["lng_N2_mol_pct"], "mol %", "tables/T5_nominal_designs.csv", f"cycle={c}", "LNG_N2_mol_pct")
        H.add(f"Nominal UA ({c})", nom["ua_kw_per_K"], "kW/K", "tables/T5_nominal_designs.csv", f"cycle={c}", "UA_kW_per_K")
    if t5:
        pd.DataFrame(t5).to_csv(T / "T5_nominal_designs.csv", index=False)

    # ---- across-scenario results, T6
    t6, por_all, across_all, surr_vs = [], [], [], []
    for c in CYCLES:
        d = work / f"unit-across-{c}"
        if not (d / "across_summary.csv").exists():
            continue
        s = pd.read_csv(d / "across_summary.csv")
        p = pd.read_csv(d / "price_of_robustness.csv") if (d / "price_of_robustness.csv").exists() else pd.DataFrame()
        dz = _read(d / "designs_at_z0.json") or {}
        for _, r in s.iterrows():
            row = dict(cycle=c, design=r.design, selected_from_candidate=r.get("source_candidate"), design_origin=r.get("origin"), chance_constraint_met=r.get("chance_met"),
                       SEC_z0_kWh_per_kg=r.sec_z0, SEC_z0_search_min=r.get("sec_z0_min"), SEC_z0_search_max=r.get("sec_z0_max"), SEC_z0_search_spread_pct=r.get("sec_z0_spread_pct"), CVaR_0p9_kWh_per_kg=r.CVaR, worst_case_kWh_per_kg=r.worst, feasible_fraction=r.feasible_fraction,
                       anchors_feasible=f"{r.n_anchor_feasible}/{r.n_anchor}", synthetic_feasible=f"{r.n_synth_feasible}/{r.n_synth}",
                       LNG_N2_mol_pct_z0=(dz.get(r.design) or {}).get("lng_N2_mol_pct"), MITA_z0_K=(dz.get(r.design) or {}).get("mita"),
                       UA_z0_kW_per_K=(dz.get(r.design) or {}).get("ua_kw_per_K"), UA_installed_kW_per_K=(dz.get(r.design) or {}).get("ua_installed_kw_per_K"))
            if r.design == "nominal":
                row.update(PoR_z0_pct=0.0)
            else:
                q = p[p.design == r.design]
                if len(q):
                    q = q.iloc[0]
                    row.update(PoR_z0_within_z0_search_spread=q.get("PoR_z0_within_z0_spread"), n_scenarios_feasible_for_both=q.get("n_both_feasible"),
                               PoR_z0_pct=100 * q.PoR_z0, PoR_scenario_mean_pct=100 * q.PoR_scenario_mean, PoR_scenario_mean_lo95_pct=100 * q.PoR_scenario_mean_lo95,
                               PoR_scenario_mean_hi95_pct=100 * q.PoR_scenario_mean_hi95, dCVaR_pct=100 * q.dCVaR_rel, dCVaR_lo95_pct=100 * q.dCVaR_rel_lo95,
                               dCVaR_hi95_pct=100 * q.dCVaR_rel_hi95, dFeasibleFraction=q.dFeasibleFraction, dFF_lo95=q.dFeasibleFraction_lo95, dFF_hi95=q.dFeasibleFraction_hi95)
                    if r.design in ("cvar_iso", "cvar_125"):
                        H.add(f"PoR at z0, {r.design} ({c})", 100 * q.PoR_z0, "%", "tables/T6_nominal_cvar_worst_designs.csv", f"cycle={c}, design={r.design}", "PoR_z0_pct")
                        H.add(f"PoR scenario mean 95% CI low, {r.design} ({c})", 100 * q.PoR_scenario_mean_lo95, "%", "tables/T6_nominal_cvar_worst_designs.csv", f"cycle={c}, design={r.design}", "PoR_scenario_mean_lo95_pct")
                        H.add(f"PoR scenario mean 95% CI high, {r.design} ({c})", 100 * q.PoR_scenario_mean_hi95, "%", "tables/T6_nominal_cvar_worst_designs.csv", f"cycle={c}, design={r.design}", "PoR_scenario_mean_hi95_pct")
            t6.append(row)
            H.add(f"CVaR0.9 {r.design} ({c})", r.CVaR, "kWh/kg", "tables/T6_nominal_cvar_worst_designs.csv", f"cycle={c}, design={r.design}", "CVaR_0p9_kWh_per_kg")
            H.add(f"Feasible fraction {r.design} ({c})", r.feasible_fraction, "-", "tables/T6_nominal_cvar_worst_designs.csv", f"cycle={c}, design={r.design}", "feasible_fraction")
        a = pd.read_parquet(d / "across_scenarios.parquet")
        a["cycle"] = c
        across_all.append(a)
        sv = d / "surrogate_vs_rigorous_at_optima.csv"
        if sv.exists():
            surr_vs.append(pd.read_csv(sv))
    if t6:
        pd.DataFrame(t6).to_csv(T / "T6_nominal_cvar_worst_designs.csv", index=False)
    fcs, per, sels = [], [], []
    for c in CYCLES:
        d = work / f"unit-across-{c}"
        for name, lst in (("failure_codes.csv", fcs), ("per_scenario.csv", per), ("selection_table.csv", sels)):
            if (d / name).exists():
                try:
                    lst.append(pd.read_csv(d / name))
                except pd.errors.EmptyDataError:
                    pass
    if fcs:
        f = pd.concat(fcs)
        f.to_csv(T / "TS_failure_codes.csv", index=False)           # request 14: count of each failure code over the scenarios, anchors and synthetic apart
    if per:
        pp = pd.concat(per)
        pp.insert(4, "group", np.where(pp.synthetic, "synthetic", "anchor"))
        pp.drop(columns=["y", "sec_with_penalty"], errors="ignore").to_csv(T / "TS_across_per_scenario.csv", index=False)     # request 15
    if sels:
        pd.concat(sels).to_csv(T / "TS_selection_table.csv", index=False)                                                      # request 13: all candidates
    # request 16: best objective per generation of every robust chain (final.json of the last stage holds the whole history)
    hist, status = [], []
    for c in CYCLES:
        for v in VARIANTS:
            dirs = sorted(work.glob(f"unit-robust-{c}-{v}-s*"), key=lambda p: int(p.name.rsplit("-s", 1)[1]))
            fin = next((_read(d / "final.json") for d in reversed(dirs) if (d / "final.json").exists()), None)
            if not fin:
                continue
            status.append(dict(cycle=c, variant=v, generation_reached=fin["generation"], target_generations=fin["target_generations"], status=fin["status"],
                               chance_met_at_end=fin["chance_met"]))
            for h in fin["history"]:
                hist.append(dict(cycle=c, variant=v, generation=h["gen"], best_feasible_objective=h["best_feasible_F"], best_constraint_violation=h["best_CV"],
                                 n_feasible_in_population=h["n_feasible"], objective="CVaR 0.9" if v != "worst_iso" else "worst case SEC", unit="kWh/kg"))
    if hist:
        hdf = pd.DataFrame(hist)
        hdf.to_csv(T / "TS_robust_convergence.csv", index=False)
        pd.DataFrame(status).to_csv(T / "TS_robust_chain_status.csv", index=False)
        for r_ in status:
            H.add(f"Generation reached, robust chain {r_['variant']} ({r_['cycle']})", r_["generation_reached"], "generation (target 10)", "tables/TS_robust_chain_status.csv", f"cycle={r_['cycle']}, variant={r_['variant']}", "generation_reached")
    if surr_vs:
        sv = pd.concat(surr_vs)
        sv["abs_diff"] = (sv.surrogate_sec - sv.rigorous_sec).abs()
        sv.to_csv(T / "TS_surrogate_vs_rigorous_at_optima.csv", index=False)

    # ---- T7 surrogate performance
    met = []
    oof = {}
    for c in CYCLES:
        d = work / f"unit-surrogate-{c}"
        if (d / "surrogate_metrics.csv").exists():
            met.append(pd.read_csv(d / "surrogate_metrics.csv"))
            oof[c] = pd.read_parquet(d / "oof_predictions.parquet")
    if met:
        m = pd.concat(met)
        t7 = pd.DataFrame(dict(cycle=m.cycle, model=m.model, output=m.output, n=m.n, MAE=m.get("MAE"), RMSE=m.get("RMSE"), R2=m.get("R2"),
                               FFR_pct=100 * m.get("overall_FFR"), FFR_lo95_pct=100 * m.get("overall_FFR_lo95"), FFR_hi95_pct=100 * m.get("overall_FFR_hi95"),
                               FP=m.get("overall_FP"), TN=m.get("overall_TN"), n_near_limit=m.get("n_near"), FFR_near_pct=100 * m.get("near_FFR"),
                               FFR_near_lo95_pct=100 * m.get("near_FFR_lo95"), FFR_near_hi95_pct=100 * m.get("near_FFR_hi95"), FP_near=m.get("near_FP"), TN_near=m.get("near_TN")))
        t7.to_csv(T / "T7_surrogate_performance.csv", index=False)
        for _, r in t7[(t7.model == "gradient_boosting") & (t7.output == "feasibility")].iterrows():
            H.add(f"Surrogate FFR overall, gradient boosting ({r.cycle})", r.FFR_pct, "%", "tables/T7_surrogate_performance.csv", f"cycle={r.cycle}, model=gradient_boosting, output=feasibility", "FFR_pct")
            H.add(f"Surrogate FFR near MITA limit, gradient boosting ({r.cycle})", r.FFR_near_pct, "%", "tables/T7_surrogate_performance.csv", f"cycle={r.cycle}, model=gradient_boosting, output=feasibility", "FFR_near_pct")
        for _, r in t7[(t7.model == "gradient_boosting") & (t7.output == "SEC")].iterrows():
            H.add(f"Surrogate SEC MAE, gradient boosting ({r.cycle})", r.MAE, "kWh/kg", "tables/T7_surrogate_performance.csv", f"cycle={r.cycle}, model=gradient_boosting, output=SEC", "MAE")

    # ---- reversal
    pts = []
    for c in CYCLES:
        for dsg in ("nominal", "robust"):
            p = work / f"unit-reversal-{c}-{dsg}" / "reversal_points.parquet"
            if p.exists():
                pts.append(pd.read_parquet(p))
    cells = pd.DataFrame()
    if pts:
        P = pd.concat(pts)
        base = P[(P.cycle == P.cycle.iloc[0]) & (P.design == P.design.iloc[0])][["scenario", "N2_pct", "C2plus_pct"]].drop_duplicates("scenario")
        cm = assign_cells(base, 4, 4)[["scenario", "cell_x", "cell_y", "cell"]]
        P2 = P.merge(cm, on="scenario")
        cells = reversal_table(P2, basis.chance_feasible_fraction, 5.0)
        cells.to_csv(T / "TS_ranking_reversal_cells.csv", index=False)
        H.add("Cells with a ranking reversal", int(cells.reversal.sum()), "cells", "tables/TS_ranking_reversal_cells.csv", "all rows", "reversal")
        H.add("Cells total", len(cells), "cells", "tables/TS_ranking_reversal_cells.csv", "all rows", "cell")

    # ---- sensitivity tables
    sob = [pd.read_csv(work / f"unit-sobol-{c}" / "sobol_indices.csv") for c in CYCLES if (work / f"unit-sobol-{c}" / "sobol_indices.csv").exists()]
    if sob:
        sob = pd.concat(sob)
        sob.to_csv(T / "TS_sobol_indices.csv", index=False)
    oatc = [_read(work / f"unit-sobol-{c}" / "oat_confirmation.json") for c in CYCLES]
    oatc = [o for o in oatc if o]
    if oatc:
        pd.DataFrame(oatc).to_csv(T / "TS_oat_confirmation.csv", index=False)
    pref = pd.read_csv(work / "unit-sobol_pref" / "sobol_preference.csv") if (work / "unit-sobol_pref" / "sobol_preference.csv").exists() else pd.DataFrame()
    if len(pref):
        pref.to_csv(T / "TS_sobol_preference.csv", index=False)
    srows = []
    for c in CYCLES:
        for case in ALL_SENS_CASES:
            j = _read(work / f"unit-sens-{c}-{case}" / "sens.json")
            if j:
                srows.append(dict(cycle=c, case=case, status=j.get("status"), protocol=j.get("protocol"), summary=json.dumps({k: v for k, v in j.items() if k not in ("protocol",)}, default=float)[:20000]))
    if srows:
        pd.DataFrame(srows).to_csv(T / "TS_sensitivity_cases.csv", index=False)

    # ---- figures
    made = []
    made += F.fig1_flowsheets(out / "figures")
    d2 = RUNS_DIR / "mshe_convergence_smr.csv"
    if d2.exists():
        made += F.fig2_discretisation(pd.read_csv(d2), out / "figures")
    defs = envelope_definitions(basis)
    from lng_robust.study.config import Ctx, get_preset
    from lng_robust.study.common import scenario_set
    from lng_robust.analysis.reversal import coords
    ctx0 = Ctx("pkg", None, None, None, preset, get_preset(preset), work, seed=seed)
    scen, nom_feed, meta = scenario_set(ctx0, basis)
    env = pd.DataFrame([dict(id=f.id, synthetic=f.synthetic, N2_pct=coords(f.treated)[0], C2plus_pct=coords(f.treated)[1]) for f in scen])
    fd = next(a for a in defs["fieldD"] if a.id == "A5")
    made += F.fig3_envelope(env, dict(N2_pct=coords(fd.treated)[0], C2plus_pct=coords(fd.treated)[1]), out / "figures")
    if fronts:
        made += F.fig4_pareto(fronts, selected, out / "figures")
    if any(curves.values()):
        made += F.fig5_composites(curves, out / "figures")
    if across_all:
        made += F.fig6_sec_distribution(pd.concat(across_all), out / "figures")
    if len(cells):
        made += F.fig7_reversal(cells, out / "figures")
    if hist:
        made += F.figS1_convergence(pd.DataFrame(hist), out / "figures")
    if oof:
        made += F.fig8_surrogate(oof, basis.mita_min_K, out / "figures")
    if isinstance(sob, pd.DataFrame) and len(sob):
        made += F.fig9_sobol(sob, pref, out / "figures")

    probe = preset != "full"
    if probe:
        label = "PROBE TIMING RUN - NOT A RESULT"
        for f in T.glob("*.csv"):
            d = pd.read_csv(f)
            d["label"] = label
            d.to_csv(f, index=False)
        (out / "PROBE_NOT_A_RESULT.txt").write_text("This package comes from the probe preset. It measures time per evaluation and checks the plumbing. "
                                                      "No number in it is a result, a finding or a benchmark. Do not quote it.\n")
    prov = provenance(work, out, run_id, preset, seed, done)
    hn = pd.DataFrame(H.rows)
    if probe:
        hn["label"] = "PROBE TIMING RUN - NOT A RESULT"
    (out / "headline_numbers.csv").write_text(hn.to_csv(index=False))
    md = (["# PROBE TIMING RUN - NOT A RESULT", "", "Every number in this package is from the probe preset (tiny budgets). Do not quote any of it.", ""] if probe else []) + ["# RESULTS SUMMARY", "",
          f"Run `{run_id}`, preset `{preset}`, commit `{prov['commit_hash'][:10]}`. Every number below is read from a file in this package or in the unit shards; "
          "none is typed by hand. Surrogate quantities appear only where labelled `Surrogate`. Anchors and synthetic scenarios are reported separately in the tables.", "",
          "## Headline numbers", "", H.markdown(), "",
          "## Unit status", ""]
    md += [f"- `{d['folder']}`: {d.get('status')}" for d in done]
    md += ["", "## INCOMPLETE", ""] + ([f"- `{d['folder']}`: {d.get('status')}" for d in incomplete] or ["- none"])
    md += ["", "## Files", "", "Tables: " + ", ".join(sorted(p.name for p in T.glob("*.csv"))), "", "Figures: " + ", ".join(sorted(made))]
    (out / "RESULTS_SUMMARY.md").write_text("\n".join(md))
    return dict(n_headlines=len(H.rows), figures=made, incomplete=incomplete)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work")
    ap.add_argument("--out", default="results_package")
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--preset", default="full")
    a = ap.parse_args()
    print(build(Path(a.work), Path(a.out), a.run_id, a.preset))
