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


def plan(s_per_eval: float, par_eff: float, inner_evals: float, preset: str = "full", cores: int = 4):
    P = get_preset(preset)
    S = P["S"] or 50
    rows = []

    def add(unit, n_jobs, evals_per_job, note=""):
        core_s = evals_per_job * s_per_eval
        wall_min = core_s / (cores * par_eff) / 60 + 2.5          # + about 2.5 min of install, checkout and artifact transfer
        rows.append(dict(unit=unit, jobs=n_jobs, evals_per_job=int(evals_per_job), evals_total=int(n_jobs * evals_per_job),
                         wall_min_per_job=round(wall_min, 1), runner_minutes=round(n_jobs * wall_min, 1), note=note))

    nom = P["nominal"]
    add("nominal", 3, 3 * nom["pop"] + nom["pop"] * (nom["gen"] + 1) + 1)
    sm = P["sample"]
    add("sample", 3, sm["n0"] + sm["rounds"] * sm["batch"])
    add("surrogate (training only)", 3, 0, "no rigorous evaluations")
    rb = P["robust"]
    members = rb["pop"] * (rb["gens"] + 1)
    per_member = S * inner_evals
    add("robust (one chain: cycle x variant)", 3 * len(VARIANTS), members * per_member,
        f"{members} members x {S} scenarios x {inner_evals:g} evals; split over chained jobs of at most {rb['unit_wall_min']} min")
    ac = P["across"]
    add("across", 3, (len(VARIANTS) + 1) * (S + 1) * min(ac["max_evals"], inner_evals * 1.5))
    rv = P["reversal"]
    add("reversal", 6, rv["n_comp"] * min(rv["max_evals"], inner_evals))
    add("sobol + OAT", 3, 15 * P["sobol"]["oat_points"] * 2, "surrogate Sobol is cheap; OAT is rigorous")
    sn = P["sens"]
    nom_s = sn["nominal"]
    add("sens model-parameter cases", 3 * len(MODEL_CASES), 3 * nom_s["pop"] + nom_s["pop"] * (nom_s["gen"] + 1) + (sn["k_designs"] + 1) * (S + 1) * min(sn["max_evals"], inner_evals))
    add("sens archive cases (re-selection only)", 3 * len(ARCHIVE_CASES), 0, "no new rigorous evaluations")
    add("sens set cases", 3 * len(SET_CASES), 5 * S * min(sn["max_evals"], inner_evals))
    df = pd.DataFrame(rows)
    # wall time of the whole DAG: critical path = nominal -> sample -> surrogate -> 3 robust stages -> across -> sens (longest)
    cp = (df[df.unit == "nominal"].wall_min_per_job.iloc[0] + df[df.unit == "sample"].wall_min_per_job.iloc[0] + 5
          + df[df.unit.str.startswith("robust")].wall_min_per_job.iloc[0] + df[df.unit == "across"].wall_min_per_job.iloc[0]
          + df[df.unit == "sens model-parameter cases"].wall_min_per_job.iloc[0] + 5)
    return df, cp


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--s-per-eval", type=float, required=True, help="measured single-core solver seconds per rigorous evaluation on the runner")
    ap.add_argument("--par-eff", type=float, required=True, help="measured parallel efficiency on 4 cores (0 to 1)")
    ap.add_argument("--inner-evals", type=float, default=40.0, help="mean rigorous evaluations per second-stage solve (measured)")
    ap.add_argument("--preset", default="full")
    a = ap.parse_args(argv)
    df, cp = plan(a.s_per_eval, a.par_eff, a.inner_evals, a.preset)
    tot = dict(evals=int(df.evals_total.sum()), runner_minutes=float(df.runner_minutes.sum()))
    out = df.copy()
    out.loc[len(out)] = dict(unit="TOTAL (new plan)", jobs=int(df.jobs.sum()), evals_per_job=0, evals_total=tot["evals"], wall_min_per_job=0,
                             runner_minutes=tot["runner_minutes"], note=f"critical path about {cp / 60:.1f} h when jobs run in parallel (max-parallel 20)")
    out.loc[len(out)] = dict(unit="OLD plan (22 h on 4 workers)", jobs=1, evals_per_job=OLD["evals"], evals_total=OLD["evals"], wall_min_per_job=OLD["wall_h"] * 60,
                             runner_minutes=OLD["runner_minutes"], note=OLD["note"])
    out.to_csv(RUNS_DIR / "budget_estimate_v2.csv", index=False)
    print(out.to_string())
    return out


if __name__ == "__main__":
    main()
