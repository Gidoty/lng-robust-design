"""python -m lng_robust.study.counts <unit folder>: write eval_counts.csv (rows by cycle, purpose, status, failure code) from the unit's Parquet shards."""
import sys
from pathlib import Path

import pandas as pd


def main(d):
    d = Path(d)
    parts = sorted(d.glob("evals-*.parquet"))
    if not parts:
        return
    cols = ["cycle", "purpose", "status", "failure_code", "numerical_failure", "runtime_s"]
    df = pd.concat([pd.read_parquet(p, columns=cols) for p in parts], ignore_index=True)
    out = df.groupby(["cycle", "purpose", "status", "failure_code"], dropna=False).agg(n=("runtime_s", "size"), runtime_s=("runtime_s", "sum")).reset_index()
    out.to_csv(d / "eval_counts.csv", index=False)
    print(f"{d.name}: {len(df)} rigorous evaluations, {df.runtime_s.sum() / 60:.1f} core-minutes of solver time")


if __name__ == "__main__":
    main(sys.argv[1])
