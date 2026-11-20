"""Re-estimate of the study budget with the new second stage, chunked units and measured timings.

Old plan (STATUS.md section 0.6, runs/budget_estimate.csv, written before this work): 416,000 rigorous evaluations, about 22 h on 4 workers
(SMR 10.6 h, single N2 5.3 h, dual N2 5.9 h), outer GA population 8 for 8 generations, S = 50, 12 evaluations per scenario, three robust variants.

New plan: counts follow from the `full` preset in study/config.py. Time per evaluation and parallel efficiency are INPUTS measured on the GitHub
runner by the probe run (`--s-per-eval`, `--par-eff`); nothing is assumed silently. Runner-minutes = sum over jobs of wall minutes (one 4-core runner each).
Usage: python -m lng_robust.analysis.budget_estimate_v2 --s-per-eval 0.55 --par-eff 0.8 [--inner-evals 40] [--preset full]"""
from __future__ import annotations

import argparse
import math

import pandas as pd

from lng_robust.config import RUNS_DIR
from lng_robust.study.config import ALL_SENS_CASES, ARCHIVE_CASES, MODEL_CASES, SET_CASES, VARIANTS, get_preset

OLD = dict(evals=416000, wall_h=22.0, runner_minutes=22.0 * 60, note="STATUS.md 0.6 (SMR 10.6 h, single N2 5.3 h, dual N2 5.9 h on 4 workers)")


def plan(s_per_eval: dict, par_eff: float, inner_evals: dict, preset: str = "full", cores: int = 4):
    """s_per_eval and inner_evals are dicts keyed by cycle (smr, n2_single, n2_dual)."""
    P = get_preset(preset)
    S = P["S"] or 50
    rows = []

    def add(unit, cycle, n_jobs, evals_per_job, note=""):
        core_s = evals_per_job * s_per_eval[cycle]
        wall_min = core_s / (cores * par_eff) / 60 + 2.5          # + about 2.5 min of install, checkout and artifact transfer
        rows.append(dict(unit=unit, cycle=cycle, jobs=n_jobs, evals_per_job=int(evals_per_job), evals_total=int(n_jobs * evals_per_job),
                         wall_min_per_job=round(wall_min, 1), runner_minutes=round(n_jobs * wall_min, 1), note=note))

    stage_min = P["robust"]["unit_wall_min"]
    for c in s_per_eval:
        nom = P["nominal"]
        add("nominal", c, 1, 3 * nom["pop"] + 10 + nom["pop"] * (nom["gen"] + 1) + 1)
        sm = P["sample"]
        add("sample", c, 1, sm["n0"] + sm["rounds"] * sm["batch"])
        rb = P["robust"]
        members = rb["pop"] * (rb["gens"] + 1)
        ie = inner_evals[c]
        per_member = S * ie
        chain_wall = members * per_member * s_per_eval[c] / (cores * par_eff) / 60
        n_stage_jobs = max(1, math.ceil(chain_wall / (stage_min - 15)))
        for v in VARIANTS:
            rows.append(dict(unit=f"robust chain ({v})", cycle=c, jobs=n_stage_jobs, evals_per_job=int(members * per_member / n_stage_jobs),
                             evals_total=int(members * per_member), wall_min_per_job=round(chain_wall / n_stage_jobs + 2.5, 1),
                             runner_minutes=round(chain_wall + 2.5 * n_stage_jobs, 1),
                             note=f"{members} members x {S} scenarios x {ie} evals; {chain_wall / 60:.1f} h of compute over {n_stage_jobs} chained jobs (5 slots provided)"))
        ac = P["across"]
        add("across", c, 1, (len(VARIANTS) + 1) * (S + 1) * ac["max_evals"] * 0.8 + (len(VARIANTS) + 1) * (ac["z0_long_evals"] * 2 + ac["z0_nm_evals"]))
        rv = P["reversal"]
        for d in ("nominal", "robust"):
            add(f"reversal ({d})", c, 1, rv["n_comp"] * rv["max_evals"] * 0.8)
        add("sobol + OAT", c, 1, 15 * P["sobol"]["oat_points"] * 2)
        sn = P["sens"]
        nom_s = sn["nominal"]
        add("sens model-parameter case", c, len(MODEL_CASES), 3 * nom_s["pop"] + 10 + nom_s["pop"] * (nom_s["gen"] + 1) + (sn["k_designs"] + 1) * (S + 1) * sn["max_evals"] * 0.8)
        add("sens set case", c, len(SET_CASES), 5 * S * sn["max_evals"] * 0.8)
        add("sens archive case (re-selection only)", c, len(ARCHIVE_CASES), 0, "no new rigorous evaluations")
    df = pd.DataFrame(rows)
    cp = {}
    for c in s_per_eval:
        d = df[df.cycle == c]
        cp[c] = (d[d.unit == "nominal"].wall_min_per_job.iloc[0] + d[d.unit == "sample"].wall_min_per_job.iloc[0] + 5
                 + d[d.unit.str.startswith("robust chain")].wall_min_per_job.max() * d[d.unit.str.startswith("robust chain")].jobs.max()
                 + d[d.unit == "across"].wall_min_per_job.iloc[0] + d[d.unit == "sens model-parameter case"].wall_min_per_job.iloc[0] + 5)
    return df, max(cp.values())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--s-smr", type=float, required=True, help="measured single-core solver seconds per rigorous evaluation, SMR")
    ap.add_argument("--s-n2-single", type=float, required=True)
    ap.add_argument("--s-n2-dual", type=float, required=True)
    ap.add_argument("--par-eff", type=float, required=True, help="measured parallel efficiency on 4 cores (0 to 1)")
    ap.add_argument("--inner-smr", type=float, default=40.0, help="rigorous evaluations per second-stage solve in the outer loop (cap from the preset)")
    ap.add_argument("--inner-n2-single", type=float, default=40.0)
    ap.add_argument("--inner-n2-dual", type=float, default=64.0)
    ap.add_argument("--preset", default="full")
    a = ap.parse_args(argv)
    df, cp = plan(dict(smr=a.s_smr, n2_single=a.s_n2_single, n2_dual=a.s_n2_dual), a.par_eff,
                  dict(smr=a.inner_smr, n2_single=a.inner_n2_single, n2_dual=a.inner_n2_dual), a.preset)
    tot = dict(evals=int(df.evals_total.sum()), runner_minutes=float(df.runner_minutes.sum()))
    out = df.copy()
    out.loc[len(out)] = dict(unit="TOTAL (new plan)", cycle="all", jobs=int(df.jobs.sum()), evals_per_job=0, evals_total=tot["evals"], wall_min_per_job=0,
                             runner_minutes=tot["runner_minutes"], note=f"critical path about {cp / 60:.1f} h when jobs run in parallel (max-parallel 20)")
    out.loc[len(out)] = dict(unit="OLD plan (22 h on 4 workers)", cycle="all", jobs=1, evals_per_job=OLD["evals"], evals_total=OLD["evals"], wall_min_per_job=OLD["wall_h"] * 60,
                             runner_minutes=OLD["runner_minutes"], note=OLD["note"])
    out.to_csv(RUNS_DIR / "budget_estimate_v2.csv", index=False)
    print(out.to_string())
    return out


if __name__ == "__main__":
    main()
