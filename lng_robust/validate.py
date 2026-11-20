"""Run every benchmark whose inputs are complete; report INCOMPLETE ones without substituting values.

Usage: python -m lng_robust.validate [--yaml path] [--out runs_dir]
Writes runs/validation_report.md and runs/validation_points.csv.

Rules fixed BEFORE any result was seen:
- PASS means |deviation| <= 5 % on every published quantity of every point, with the study's equation of state (Peng-Robinson).
- When the source used SRK, the SRK run (which reuses the PR binary parameters, so it is only a cross-check) is reported next to
  the PR run. It never replaces the PR verdict.
- Nothing is tuned. A point whose flowsheet fails is reported as FAIL with its failure code.
- Published decision variables are inputs; the published net power (or compressor power, LNG flow) is the compared quantity.
  The computed MITA at the published design is a diagnostic, not part of the verdict.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pandas as pd
import yaml

from lng_robust.config import DATA_DIR, RUNS_DIR, load_basis
from lng_robust.props.eos import mixture_MW, use_eos

TOL_PCT = 5.0
N2_MW = 28.0134
_BASIS_KEYS = ["feed_T_C", "feed_P_bar", "T_cool_C", "lng_storage_pressure_bar", "compressor_pr_max_per_stage",
               "dp_mshe_hp_bar", "dp_mshe_ng_bar", "dp_mshe_lp_bar", "dp_cooler_bar", "dp_intercooler_bar", "dp_suction_bar"]


def _missing(d: dict, prefix="") -> list:
    out = []
    for k, v in d.items():
        if isinstance(v, dict):
            out += _missing(v, f"{prefix}{k}.")
        elif v is None:
            out.append(f"{prefix}{k}")
    return out


def _solver(cycle):
    from lng_robust.cycles.n2_dual import solve_n2_dual
    from lng_robust.cycles.n2_single import solve_n2_single
    from lng_robust.cycles.smr import solve_smr
    return {"n2_single": solve_n2_single, "n2_dual": solve_n2_dual, "smr": solve_smr}[cycle]


def _basis_for(basis, inp: dict, eta_c, eta_e, mita):
    ov = {k: inp[k] for k in _BASIS_KEYS if k in inp and inp[k] is not None}
    if "T_cool_K" in inp:
        ov["T_cool_C"] = inp["T_cool_K"] - 273.15
    if inp.get("product_basis") == "no_flash_at_feed_pressure":
        ov["lng_storage_pressure_bar"] = inp["feed_P_bar"] - inp.get("dp_mshe_ng_bar", 0.0)
    # the benchmark feed is taken as given: the pretreatment spec screen is not applied to it
    ov.update(pretreat_co2_ppmv=1e9, pretreat_c4plus_mol_pct=100.0, pretreat_c5plus_mol_pct=100.0,
              min_end_flash_liquid_mass_frac=0.0)
    if eta_c is not None:
        ov["efficiency_compressor"] = eta_c
    if eta_e is not None:
        ov["efficiency_expander"] = eta_e
    if mita is not None:
        ov["mita_min_K"] = mita
    return basis.override(**ov)


def _evaluate(cycle, inp, x_fn, b, eos):
    """Run one flowsheet. Returns (result, m_lng)."""
    solve = _solver(cycle)
    feed = inp["feed_composition"]
    with use_eos(eos):
        mw = mixture_MW(feed)
        n_feed = inp["feed_flow_kg_s"] / (mw / 1e3)
        x = x_fn(n_feed)
        if inp["product_basis"] == "no_flash_at_feed_pressure":
            m_lng = inp["feed_flow_kg_s"]
            probe = None
        else:
            probe = solve(feed, b.feed_T, b.feed_P, 1.0, x, b)
            if probe.lng_mass_frac != probe.lng_mass_frac:
                return probe, float("nan")
            m_lng = inp["feed_flow_kg_s"] * probe.lng_mass_frac
        return solve(feed, b.feed_T, b.feed_P, m_lng, x, b), m_lng


def _run_points(name, spec, basis, eos_list):
    common = spec["common_inputs"]
    pts = pd.read_csv(DATA_DIR / spec["points_file"], comment="#")
    rows = []
    cyc = spec["cycle"]
    for i, r in pts.iterrows():
        for eos_label, eos in eos_list:
            def x_fn(n_feed, r=r):
                if cyc == "n2_single":
                    n2 = r.mR_kg_s / (N2_MW / 1e3)
                    return dict(P_high_bar=float(r.pH_bar), P_low_bar=float(r.pL_bar), flow_ratio=n2 / n_feed,
                                T_exp_in_C=float(r.T_II_K) - 273.15, T_lng_C=common["T_lng_K"] - 273.15)
                total = r.mRa_kg_s + r.mRb_kg_s
                return dict(P_high_bar=float(r.pH_bar), P_low_bar=float(r.pL_bar), flow_ratio=(total / (N2_MW / 1e3)) / n_feed,
                            T_exp_in_warm_C=float(r.T_II_K) - 273.15, T_exp_in_cold_C=float(r.T_III_K) - 273.15,
                            split=float(r.mRa_kg_s / total), T_lng_C=common["T_lng_K"] - 273.15)
            b = _basis_for(basis, common, float(r.eta_s), float(r.eta_s), float(r.dTmin_K))
            res, m_lng = _evaluate(cyc, common, x_fn, b, eos)
            wnet = res.w_comp_kw - res.w_exp_kw if res.sec == res.sec else float("nan")
            dev = 100 * (wnet - r.Wnet_kW) / r.Wnet_kW if wnet == wnet else float("nan")
            rows.append(dict(benchmark=name, point=i + 1, eos=eos_label, dTmin_K=r.dTmin_K, eta_s=r.eta_s, published_Wnet_kW=r.Wnet_kW,
                             computed_Wnet_kW=wnet, deviation_pct=dev, computed_MITA_K=res.mita,
                             flowsheet_converged=res.converged, failure_codes=";".join(res.failure_codes), failure_msg=res.failure_msg[:80]))
    return rows


def _run_single(name, spec, basis, eos_list):
    """Single-design benchmark (Jensen). Compared: compressor power and LNG flow."""
    inp = spec["inputs"]
    pb = spec.get("published_basis", {})
    cyc = spec["cycle"]
    rows = []
    for eos_label, eos in eos_list:
        b = _basis_for(basis, inp, pb.get("eta_compressor", inp.get("eta_compressor")), None, pb.get("mita_K"))

        def x_fn(n_feed):
            if cyc == "smr":
                n_ref = inp["refrigerant_flow_kg_s"] / (mixture_MW(inp["refrigerant_composition"]) / 1e3)
                p_low = inp["P_low_bar"]
                if inp.get("low_pressure_definition") == "compressor_suction":
                    p_low = p_low + inp.get("dp_suction_bar", 0.0) + inp.get("dp_mshe_lp_bar", 0.0)
                return dict(ref=inp["refrigerant_composition"], P_high_bar=inp["P_high_bar"], P_low_bar=p_low,
                            flow_ratio=n_ref / n_feed, T_lng_C=inp["T_lng_C"])
            x = dict(P_high_bar=inp["P_high_bar"], P_low_bar=inp["P_low_bar"], T_lng_C=inp["T_lng_C"],
                     flow_ratio=inp["n2_flow_kg_s"] / (N2_MW / 1e3) / n_feed)
            if cyc == "n2_single":
                x["T_exp_in_C"] = inp["T_exp_in_C"]
            else:
                x.update(T_exp_in_warm_C=inp["T_exp_in_warm_C"], T_exp_in_cold_C=inp["T_exp_in_cold_C"], split=inp["split"])
            return x
        res, m_lng = _evaluate(cyc, inp, x_fn, b, eos)
        for q, pub, comp in (("Compressor power (MW)", spec["published"].get("compressor_power_MW"), res.w_comp_kw / 1e3),
                             ("LNG flow (kg/s)", spec["published"].get("lng_flow_kg_s"), m_lng),
                             ("SEC (kWh/kg LNG)", spec["published"].get("sec_kwh_per_kg_lng"), res.sec)):
            if pub is None:
                continue
            dev = 100 * (comp - pub) / pub if comp == comp else float("nan")
            rows.append(dict(benchmark=name, point=1, eos=eos_label, quantity=q, published=pub, computed=comp, deviation_pct=dev,
                             computed_MITA_K=res.mita, flowsheet_converged=res.converged, failure_codes=";".join(res.failure_codes),
                             failure_msg=res.failure_msg[:80],
                             computed_superheat_K=res.details.get("min_superheat_K", float("nan")),
                             published_superheat_K=spec.get("diagnostics_published", {}).get("superheat_K")))
    return rows


def run_benchmark(name: str, spec: dict, basis):
    """Return dict(name, status, missing, rows=[(quantity, published, computed, dev)], points=[...])."""
    inputs = spec.get("common_inputs", spec.get("inputs", {}))
    miss = _missing(inputs)
    if miss:
        return dict(name=name, status="INCOMPLETE", missing=miss, rows=[], points=[])
    if inputs.get("product_basis") not in ("after_end_flash", "no_flash_at_feed_pressure"):
        return dict(name=name, status="INCOMPLETE", missing=["product_basis must be 'after_end_flash' or 'no_flash_at_feed_pressure'"],
                    rows=[], points=[])
    pub_eos = spec.get("published_basis", {}).get("equation_of_state", "Peng-Robinson")
    eos_list = [("PR (primary)", "PR")]
    if pub_eos == "SRK":
        eos_list.append(("SRK with PR kij (cross-check)", "SRK"))
    pts = _run_points(name, spec, basis, eos_list) if "points_file" in spec else _run_single(name, spec, basis, eos_list)
    primary = [p for p in pts if p["eos"].startswith("PR")]
    if "points_file" in spec:
        rows = [(f"point {p['point']} Wnet (kW), dTmin {p['dTmin_K']} K, eta {p['eta_s']}", p["published_Wnet_kW"], p["computed_Wnet_kW"], p["deviation_pct"])
                for p in primary]
    else:
        rows = [(p["quantity"], p["published"], p["computed"], p["deviation_pct"]) for p in primary]
    ok = bool(rows) and all(d == d and abs(d) <= TOL_PCT for *_, d in rows)
    return dict(name=name, status="PASS" if ok else "FAIL", missing=[], rows=rows, points=pts, published_eos=pub_eos,
                provenance=spec.get("input_provenance", "primary"), citation=spec.get("citation", ""),
                sources=spec.get("source_documents", []))


def _summary(points, label):
    df = pd.DataFrame([p for p in points if p["eos"].startswith(label)])
    if df.empty:
        return None
    d = df["deviation_pct"].dropna()
    return dict(n=len(df), n_flowsheet_failed=int((~df.flowsheet_converged).sum()), n_within_5pct=int((d.abs() <= TOL_PCT).sum()),
                mean_dev=float(d.mean()) if len(d) else float("nan"), mean_abs_dev=float(d.abs().mean()) if len(d) else float("nan"),
                max_abs_dev=float(d.abs().max()) if len(d) else float("nan"))


def run(yaml_path=None, out_dir=RUNS_DIR, basis=None) -> list:
    spec = yaml.safe_load(open(yaml_path or DATA_DIR / "benchmarks.yaml"))
    basis = basis or load_basis()
    results = [run_benchmark(n, s, basis) for n, s in spec.items()]
    lines = ["# Benchmark validation report", "",
             f"Acceptance: |deviation| <= {TOL_PCT:.0f} % on every published quantity at every point, with the study equation of state (Peng-Robinson). "
             "No parameter is tuned to force agreement. The computed MITA at the published design is a diagnostic only.", ""]
    all_pts = []
    for r in results:
        lines.append(f"## {r['name']}: {r['status']}")
        if r["status"] == "INCOMPLETE":
            lines.append("BENCHMARK_INPUTS_INCOMPLETE. Missing inputs (null in benchmarks.yaml, not substituted):")
            lines += [f"- `{m}`" for m in r["missing"]]
            print(f"BENCHMARK_INPUTS_INCOMPLETE [{r['name']}]: {', '.join(r['missing'])}")
        else:
            if r.get("citation"):
                lines.append(f"Source: {r['citation']}")
            for d in r.get("sources", []):
                lines.append(f"- {d}")
            if r.get("provenance") and r["provenance"] != "primary":
                lines.append(f"- **Input provenance: {r['provenance']}**")
            lines.append("")
            all_pts += r["points"]
            if r["points"]:
                for lab in ("PR", "SRK"):
                    sm = _summary(r["points"], lab)
                    if sm:
                        lines.append(f"{'PR (primary)' if lab == 'PR' else 'SRK with PR kij (cross-check)'}: {sm['n_within_5pct']} of {sm['n']} points within 5 %, "
                                     f"mean deviation {sm['mean_dev']:+.2f} %, mean absolute {sm['mean_abs_dev']:.2f} %, maximum absolute {sm['max_abs_dev']:.2f} %, "
                                     f"flowsheet failures {sm['n_flowsheet_failed']}.")
                lines.append("")
                lines.append("| Point | EOS | Published | Computed | Deviation (%) | Computed MITA (K) | Codes |")
                lines.append("|---|---|---|---|---|---|---|")
                for p in r["points"]:
                    pub = p.get("published_Wnet_kW", p.get("published"))
                    comp = p.get("computed_Wnet_kW", p.get("computed"))
                    lab = p.get("quantity") or f"dTmin {p['dTmin_K']} K, eta {p['eta_s']}"
                    lines.append(f"| {lab} | {p['eos']} | {pub} | {comp:.5g} | {p['deviation_pct']:+.2f} | {p['computed_MITA_K']:.3g} | {p['failure_codes']} |")
            if r["published_eos"] == "SRK":
                lines.append("")
                lines.append("Note: the source used SRK. The PR deviation includes the equation-of-state difference; the SRK run reuses the PR binary "
                             "interaction parameters, so it is a cross-check and not a reproduction of the source's SRK parameters.")
        lines.append("")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "validation_report.md").write_text("\n".join(lines))
    if all_pts:
        pd.DataFrame(all_pts).to_csv(out / "validation_points.csv", index=False)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaml", default=None)
    ap.add_argument("--out", default=str(RUNS_DIR))
    a = ap.parse_args()
    res = run(a.yaml, a.out)
    print({r["name"]: r["status"] for r in res})


if __name__ == "__main__":
    main()
