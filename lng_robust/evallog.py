"""Evaluation log: every rigorous evaluation (feasible or not) is kept with its failure code (manuscript Appendix A)."""
from __future__ import annotations

import itertools
import json
import subprocess
from pathlib import Path

import pandas as pd

_counter = itertools.count(1)


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).parent,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "nogit"


class EvalLog:
    def __init__(self, tag: str, seed: int, smoke: bool = False):
        self.rows: list = []
        self.tag, self.seed, self.smoke = tag, seed, smoke

    def add(self, res, *, cycle, feed_id, synthetic, parent_id, kappa, capacity_tpd, stage1, stage2, purpose,
            composition: dict) -> int:
        cid = next(_counter)
        row = res.as_row()
        row.update(case_id=f"{self.tag}-{cid:07d}", feed_id=feed_id, synthetic_feed=synthetic, parent_anchor=parent_id,
                   kappa=kappa, capacity_tpd=capacity_tpd, purpose=purpose, seed=self.seed,
                   feed_composition=json.dumps(composition, sort_keys=True),
                   stage1_variables=json.dumps(stage1, sort_keys=True, default=float),
                   stage2_variables=json.dumps(stage2, sort_keys=True, default=float),
                   status=("feasible" if res.feasible else ("converged_infeasible" if res.converged else "not_converged")),
                   code_version=git_hash(), label=("SMOKE TEST - NOT A RESULT" if self.smoke else ""))
        self.rows.append(row)
        return cid

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)

    def save(self, path: Path):
        self.frame().to_csv(path, index=False)
