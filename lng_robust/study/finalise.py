"""Post-processing of a finished results package (request 20 and 21 of manuscript/REQUESTS_TO_ENGINE.md). No simulation, no number changes.

    python -m lng_robust.study.finalise --pkg results/<run_id> --work work --code-commit <sha>

* redraws Figure_7 (from tables/TS_ranking_reversal_cells.csv), Figure_8 (from work/unit-surrogate-<cycle>/oof_predictions.parquet of the run that
  produced the surrogate, the same input the package used) and Figure_9 (from tables/TS_sobol_indices.csv and TS_sobol_preference.csv);
* writes tables/TS_cost_screening.csv from T5, T6 and TS_across_per_scenario (lng_robust/analysis/cost_screening.py);
* records what was done, with the code commit, in provenance.json (key `post_processing`) and in RESULTS_SUMMARY.md.
Every output is derived from files of the package (and the surrogate out-of-fold predictions); T-tables and headline_numbers.csv are not touched.
A missing input is an error, never a silent skip."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path

import pandas as pd

from lng_robust.analysis import cost_screening
from lng_robust.analysis import figures as F
from lng_robust.config import load_basis
from lng_robust.study.config import CYCLES


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def finalise(pkg: Path, work: Path, code_commit: str) -> dict:
    pkg, work = Path(pkg), Path(work)
    T, FIG = pkg / "tables", pkg / "figures"
    for need in ("TS_ranking_reversal_cells.csv", "TS_sobol_indices.csv", "TS_sobol_preference.csv", "T5_nominal_designs.csv",
                 "T6_nominal_cvar_worst_designs.csv", "TS_across_per_scenario.csv"):
        if not (T / need).exists():
            raise FileNotFoundError(f"{T / need} is needed and missing")
    prov_path = pkg / "provenance.json"
    prov = json.loads(prov_path.read_text())
    if prov.get("preset") != "full":
        raise SystemExit("finalise runs on a full-run package only")
    oof = {}
    for c in CYCLES:
        p = work / f"unit-surrogate-{c}" / "oof_predictions.parquet"
        if not p.exists():
            raise FileNotFoundError(f"{p} is needed for Figure_8 and is missing")
        oof[c] = pd.read_parquet(p)
    basis = load_basis()
    before = {f.name: _sha(f) for f in sorted(T.glob("*.csv"))}
    made = []
    made += F.fig7_reversal(pd.read_csv(T / "TS_ranking_reversal_cells.csv"), FIG)
    made += F.fig8_surrogate(oof, basis.mita_min_K, FIG)
    made += F.fig9_sobol(pd.read_csv(T / "TS_sobol_indices.csv"), pd.read_csv(T / "TS_sobol_preference.csv"), FIG)
    cost_screening.run(str(T))
    after = {f.name: _sha(f) for f in sorted(T.glob("*.csv"))}
    changed = sorted(k for k in before if before[k] != after[k])
    if changed:
        raise RuntimeError(f"post-processing changed existing tables: {changed}")
    entry = dict(
        step="request 20 (Figure_7, Figure_8, Figure_9 redrawn) and request 21 (TS_cost_screening.csv)",
        code_commit=code_commit, date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        figures_rewritten=made, tables_added=["TS_cost_screening.csv"], existing_tables_unchanged=sorted(before),
        inputs=dict(Figure_7="tables/TS_ranking_reversal_cells.csv", Figure_9="tables/TS_sobol_indices.csv, tables/TS_sobol_preference.csv",
                    Figure_8="surrogate out-of-fold predictions (unit-surrogate-<cycle>/oof_predictions.parquet of run " + str(prov.get("source_run_id", prov.get("run_id"))) + ")",
                    TS_cost_screening="tables/T5_nominal_designs.csv, T6_nominal_cvar_worst_designs.csv, TS_across_per_scenario.csv; correlations and assumptions in the script header"),
        note="no simulation was run and no number in an existing table changed (SHA-256 of every earlier table checked before and after)")
    prov.setdefault("post_processing", []).append(entry)
    prov_path.write_text(json.dumps(prov, indent=2, default=str))
    summ = pkg / "RESULTS_SUMMARY.md"
    if summ.exists():
        s = summ.read_text()
        s += (f"\n## Post-processing (code commit `{code_commit[:10]}`)\n\n- Figure_7, Figure_8 and Figure_9 were redrawn from this package's tables (Figure_8: surrogate out-of-fold predictions); no number changed.\n"
              "- `tables/TS_cost_screening.csv` was added (screening-level purchased-equipment and annualised cost; U and electricity price are illustrative assumptions, see `lng_robust/analysis/cost_screening.py`).\n"
              "- Per-scenario compressor and expander shaft power are not stored by the evaluation shards, so they are not in this package.\n")
        summ.write_text(s)
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--work", default="work")
    ap.add_argument("--code-commit", required=True)
    a = ap.parse_args()
    e = finalise(Path(a.pkg), Path(a.work), a.code_commit)
    print(json.dumps(e, indent=2))


if __name__ == "__main__":
    main()
