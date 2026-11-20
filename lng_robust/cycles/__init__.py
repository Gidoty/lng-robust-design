from lng_robust.cycles.n2_dual import solve_n2_dual
from lng_robust.cycles.n2_single import solve_n2_single
from lng_robust.cycles.smr import solve_smr

SOLVERS = {"smr": solve_smr, "n2_single": solve_n2_single, "n2_dual": solve_n2_dual}


def solve(cycle, feed, feed_T, feed_P, m_lng, x, basis):
    return SOLVERS[cycle](feed, feed_T, feed_P, m_lng, x, basis)
