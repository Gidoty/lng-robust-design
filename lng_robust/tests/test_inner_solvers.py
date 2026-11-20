import numpy as np
import pytest

from lng_robust.analysis.golden import M_LNG
from lng_robust.analysis.inner_benchmark import equipment
from lng_robust.doe.envelope import envelope_definitions
from lng_robust.opt.inner import solve_hybrid, solve_nelder_mead, solve_slsqp
from lng_robust.opt.space import STAGE2, bounds


@pytest.fixture(scope="module")
def setup(basis):
    feed = envelope_definitions(basis)["main"][2].treated        # A4
    x1, base, r0 = equipment("n2_single", feed, basis)
    y0 = np.array([base[n] for n in STAGE2["n2_single"]])
    lo, hi = bounds("n2_single", STAGE2["n2_single"], basis)
    return feed, x1, y0, lo, hi


def test_hybrid_respects_budget_returns_only_rigorous_feasible_best_and_is_deterministic(basis, setup):
    feed, x1, y0, lo, hi = setup
    a = solve_hybrid("n2_single", feed, M_LNG, x1, y0, lo, hi, basis, max_evals=18)
    b = solve_hybrid("n2_single", feed, M_LNG, x1, y0, lo, hi, basis, max_evals=18)
    assert a.n_evals == len(a.evals) <= 18 and a.n_evals == b.n_evals
    if a.best_res is not None:
        assert a.best_res.feasible and np.isfinite(a.best_res.sec)
        assert a.best_res.sec == min(r.sec for _, r in a.evals if r.feasible)       # best is the lowest feasible rigorous value
        assert a.best_res.sec == b.best_res.sec


def test_every_evaluation_is_returned_for_logging_including_failures(basis, setup):
    feed, x1, y0, lo, hi = setup
    out = solve_nelder_mead("n2_single", feed, M_LNG, x1, y0, lo, hi, basis, maxfev=10)
    assert out.n_evals == len(out.evals) and all(hasattr(r, "failure_code") for _, r in out.evals)


def test_slsqp_start_points_can_be_supplied_and_budget_is_a_hard_cap(basis, setup):
    feed, x1, y0, lo, hi = setup
    out = solve_slsqp("n2_single", feed, M_LNG, x1, y0, lo, hi, basis, max_evals=12, n_restarts=2, maxiter=3, extra_starts=[y0 * 1.01, y0 * 0.99])
    assert out.n_evals <= 12 and out.method == "slsqp"
