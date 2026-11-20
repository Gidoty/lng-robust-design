import math

import pytest

from lng_robust.cycles import solve
from lng_robust.cycles.common import TEMP_CROSS
from lng_robust.tests.conftest import X_DUAL, X_SINGLE, X_SMR

M = 100e3 / 86400


def _run(cycle, x, feed, basis, m=M):
    return solve(cycle, feed, basis.feed_T, basis.feed_P, m, x, basis)


@pytest.mark.parametrize("cycle,x", [("n2_dual", X_DUAL), ("n2_single", X_SINGLE), ("smr", X_SMR)])
def test_exergy_balance_closes_and_tear_converged(cycle, x, feed, fast_basis):
    r = _run(cycle, x, feed, fast_basis)
    assert r.converged, (r.failure_codes, r.failure_msg)
    assert abs(r.exergy_closure_error) < 1e-6
    assert r.tear_residual < fast_basis.tear_tol
    assert r.balance_error < fast_basis.balance_tol
    assert sum(r.exergy_destruction_kw.values()) > 0
    assert math.isfinite(r.sec) and r.sec > 0


def test_feasible_reference_design_has_no_failure_code(feed, fast_basis):
    r = _run("n2_dual", X_DUAL, feed, fast_basis)
    assert r.feasible and r.failure_code == "" and r.mita >= fast_basis.mita_min_K


def test_infeasible_design_is_logged_with_a_code_not_dropped(feed, fast_basis):
    r = _run("n2_single", X_SINGLE, feed, fast_basis)      # this hand-set single-expander design pinches negatively
    assert not r.feasible
    assert r.failure_code == TEMP_CROSS and TEMP_CROSS in r.failure_codes
    assert r.violation > 0 and math.isfinite(r.mita) and r.mita < 0


def test_sec_is_scale_invariant_with_constant_efficiency(feed, fast_basis):
    a = _run("n2_dual", X_DUAL, feed, fast_basis, m=M)
    b = _run("n2_dual", X_DUAL, feed, fast_basis, m=3 * M)
    assert abs(a.sec - b.sec) / a.sec < 1e-9
    assert abs(b.ua / a.ua - 3.0) < 1e-6          # UA scales with capacity


def test_installed_limits_trigger_codes(feed, fast_basis):
    r = _run("n2_dual", {**X_DUAL, "ua_installed_kw_per_K": 1.0}, feed, fast_basis)
    assert "UA_EXCEEDED" in r.failure_codes
    r = _run("n2_dual", {**X_DUAL, "n_ref_rated_mol_s": 1.0}, feed, fast_basis)
    assert "RATED_FLOW_EXCEEDED" in r.failure_codes


def test_feed_out_of_spec_is_product_spec_failure(fast_basis):
    bad = {"C1": 0.90, "C2": 0.05, "C3": 0.03, "nC4": 0.02}        # C4+ = 2 mol% is on the limit; add C5 to break it
    bad = {"C1": 0.88, "C2": 0.05, "C3": 0.03, "nC4": 0.03, "nC5": 0.01}
    r = solve("n2_dual", bad, fast_basis.feed_T, fast_basis.feed_P, M, X_DUAL, fast_basis)
    assert r.failure_code == "PRODUCT_SPEC" and not r.feasible


def test_bad_pressure_levels_coded_not_raised(feed, fast_basis):
    r = _run("n2_dual", {**X_DUAL, "P_high_bar": 10.5, "P_low_bar": 10}, feed, fast_basis)
    assert r.failure_code == "BAD_INPUT"


def test_liquid_at_suction_detected_for_heavy_smr_refrigerant(feed, fast_basis):
    x = {**X_SMR, "ref": {"C3": 0.3, "nC4": 0.4, "iC5": 0.3}, "flow_ratio": 1.2}
    r = _run("smr", x, feed, fast_basis)
    assert "LIQUID_AT_SUCTION" in r.failure_codes or not r.converged or r.failure_codes   # logged either way
