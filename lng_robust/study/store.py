"""Compact evaluation rows and a Parquet sink (zstd). Every rigorous evaluation of the study is written here, feasible or not.

`compact_row` keeps the numbers a reviewer needs to audit one evaluation; the composition is referenced by feed_id (the scenario /
anchor tables are written once per unit), not repeated as JSON in every row. Shards are numbered parts, so a resumed unit appends."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

ROW_FIELDS = ["sec", "mita", "ua", "w_comp_kw", "w_exp_kw", "n_ref", "violation", "exergy_eff", "balance_error",
              "exergy_closure_error", "tear_iterations", "runtime_s", "n_flash", "lng_N2_mol_pct", "lng_mass_frac"]


def compact_row(res, *, unit: str, cycle: str, feed_id: str, synthetic: bool, purpose: str, x: dict, member: str = "",
                scenario_group: str = "", extra: dict | None = None) -> dict:
    d = res.as_row()
    row = dict(unit=unit, cycle=cycle, feed_id=feed_id, synthetic=bool(synthetic), purpose=purpose, member=member,
               feasible=bool(res.feasible), status=("feasible" if res.feasible else ("converged_infeasible" if res.converged else "not_converged")),
               failure_code=res.failure_code, failure_codes=";".join(res.failure_codes),
               numerical_failure=bool(res.failure_code in ("FLASH_FAIL", "NONCONVERGED")), group=scenario_group)
    for k in ROW_FIELDS:
        row[k] = float(d.get(k, float("nan"))) if d.get(k) is not None else float("nan")
    for k, v in x.items():
        if k == "ref":
            for c, w in (v or {}).items():
                row[f"x_w_{c}"] = float(w)
        elif isinstance(v, (int, float)):
            row[f"x_{k}"] = float(v)
    if extra:
        row.update(extra)
    return row


class EvalSink:
    """Collects rows and writes numbered Parquet parts. flush() is cheap to call often."""

    def __init__(self, out_dir: Path, prefix: str = "evals", max_rows: int = 100_000):
        self.dir = Path(out_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.prefix, self.max_rows = prefix, max_rows
        self.rows: list = []
        self.n_written = 0
        self.part = len(list(self.dir.glob(f"{prefix}-*.parquet")))

    def add_rows(self, rows):
        self.rows.extend(rows)
        if len(self.rows) >= self.max_rows:
            self.flush()

    def flush(self):
        if not self.rows:
            return
        self.part += 1
        df = pd.DataFrame(self.rows)
        df.to_parquet(self.dir / f"{self.prefix}-{self.part:05d}.parquet", compression="zstd", index=False)
        self.n_written += len(df)
        self.rows = []

    def close(self):
        self.flush()
        return self.n_written


class SinkLog:
    """Drop-in for evallog.EvalLog.add used by opt.nominal: writes compact rows to a sink."""

    def __init__(self, sink: EvalSink, unit: str, seed: int):
        self.sink, self.unit, self.seed = sink, unit, seed
        self.n = 0

    def add(self, res, *, cycle, feed_id, synthetic, parent_id, kappa, capacity_tpd, stage1, stage2, purpose, composition):
        x = dict(stage2)
        if stage1:
            x.update({k: v for k, v in stage1.items() if k != "ref" or v})
        self.sink.add_rows([compact_row(res, unit=self.unit, cycle=cycle, feed_id=feed_id, synthetic=synthetic, purpose=purpose, x=x,
                                        extra=dict(parent_anchor=parent_id or "", seed=self.seed))])
        self.n += 1


def read_parts(dir_: Path, prefix: str = "evals") -> pd.DataFrame:
    files = sorted(Path(dir_).glob(f"{prefix}-*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else pd.DataFrame()


def write_json(path: Path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, default=float))


def read_json(path: Path):
    return json.loads(Path(path).read_text())


class Timer:
    def __init__(self):
        self.t0 = time.time()

    def minutes(self):
        return (time.time() - self.t0) / 60.0
