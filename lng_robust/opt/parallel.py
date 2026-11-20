"""Process-pool evaluation of cycles. Workers build their own property objects (thermo objects are per process)."""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

from lng_robust.cycles import solve

_POOL = None


def _task(args):
    cycle, feed, feed_T, feed_P, m_lng, x, basis = args
    res = solve(cycle, feed, feed_T, feed_P, m_lng, x, basis)
    res.__dict__.pop("_mshe", None)
    return res


def get_pool(n_workers: int | None = None):
    global _POOL
    if _POOL is None:
        _POOL = ProcessPoolExecutor(max_workers=n_workers or os.cpu_count())
    return _POOL


def map_eval(tasks: list, n_workers: int | None = None, serial: bool = False) -> list:
    if serial or len(tasks) == 1 or (n_workers == 1):
        return [_task(t) for t in tasks]
    return list(get_pool(n_workers).map(_task, tasks, chunksize=1))


def shutdown():
    global _POOL
    if _POOL is not None:
        _POOL.shutdown()
        _POOL = None
