"""cProfile of one rigorous evaluation per cycle (warm process, second call), written to runs/profile_<cycle>.txt."""
from __future__ import annotations

import cProfile
import io
import pstats
import sys
import time

from lng_robust.analysis.golden import M_LNG, make_cases
from lng_robust.config import RUNS_DIR, load_basis
from lng_robust.cycles import solve


def run(out_dir=RUNS_DIR, top=25):
    basis = load_basis()
    cases = make_cases(basis)
    picks = {}
    for c in cases:
        picks.setdefault(c["cycle"], c)
    rows = []
    for cycle, c in picks.items():
        args = (cycle, c["feed"], basis.feed_T, basis.feed_P, M_LNG, c["x"], basis)
        solve(*args)                       # warm caches (mixtures are built once per process)
        pr = cProfile.Profile()
        t = time.perf_counter()
        pr.enable()
        r = solve(*args)
        pr.disable()
        dt = time.perf_counter() - t
        buf = io.StringIO()
        pstats.Stats(pr, stream=buf).sort_stats("cumulative").print_stats(top)
        (out_dir / f"profile_{cycle}.txt").write_text(buf.getvalue())
        rows.append((cycle, dt, r.n_flash))
    return rows


if __name__ == "__main__":
    for r in run():
        print(r)
