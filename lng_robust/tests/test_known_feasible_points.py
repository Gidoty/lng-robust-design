"""Request 12: a design that is feasible at a composition by construction cannot be reported infeasible there."""
from types import SimpleNamespace

import numpy as np
import pytest

from lng_robust.analysis.golden import M_LNG
from lng_robust.cycles import solve
from lng_robust.doe.envelope import build_envelope, envelope_definitions
from lng_robust.opt.scenario_eval import scenario_job
from lng_robust.opt.space import STAGE2, bounds
from lng_robust.study.units import eval_designs_on_set

# found by a seeded random search; feasible on the nominal anchor A4 (asserted below)
N2S_A4 = dict(P_high_bar=70.21188348676853, P_low_bar=9.800692042801586, flow_ratio=8.772728960622349,
              T_exp_in_C=-69.10238140572024, T_lng_C=-143.0419683390787)


@pytest.fixture(scope="module")
def a4(basis):
    anchors = envelope_definitions(basis)["main"]
    feed = next(a for a in anchors if a.id == "A4")
    r = solve("n2_single", feed.treated, basis.feed_T, basis.feed_P, M_LNG, dict(N2S_A4), basis)
    assert r.feasible, "the reference design must be feasible at A4"
    return feed, r


def _tight_equipment(r):
    """The nominal design is installed at exactly its own UA and rated flow (stage1_vec_of_design uses a factor 1 + 1e-6)."""
    return dict(ua_installed_kw_per_K=r.ua * (1 + 1e-6), n_ref_rated_mol_s=r.n_ref * (1 + 1e-6))


def test_seed_point_is_always_a_candidate_even_with_a_one_evaluation_budget(basis, a4):
    feed, r = a4
    x1 = _tight_equipment(r)
    lo, hi = bounds("n2_single", STAGE2["n2_single"], basis)
    y_own = [N2S_A4[n] for n in STAGE2["n2_single"]]
    far = 0.5 * (lo + hi)                                              # a start that is nowhere near the design
    out = scenario_job(("n2_single", "A4", False, None, feed.treated, M_LNG, x1, far, basis,
                        dict(method="hybrid", max_evals=1, n_restarts=0, seed_points=[y_own]), dict(unit="t", purpose="t")))
    assert out["feasible"] and out["sec"] <= r.sec * (1 + 1e-9)


def test_without_the_seed_the_search_may_fail_but_the_seeded_one_never_does(basis, a4):
    feed, r = a4
    x1 = _tight_equipment(r)
    lo, hi = bounds("n2_single", STAGE2["n2_single"], basis)
    y_own = [N2S_A4[n] for n in STAGE2["n2_single"]]
    out = scenario_job(("n2_single", "A4", False, None, feed.treated, M_LNG, x1, 0.5 * (lo + hi), basis,
                        dict(method="hybrid", max_evals=40, n_restarts=0, seed_points=[y_own]), dict(unit="t", purpose="t")))
    assert out["feasible"] and out["sec"] <= r.sec * (1 + 1e-9) and out["fail_code"] == ""


def test_infeasible_scenarios_report_the_failure_code_of_the_closest_evaluation(basis, a4):
    feed, r = a4
    x1 = dict(ua_installed_kw_per_K=1e-3, n_ref_rated_mol_s=r.n_ref)      # absurdly small UA: nothing can be feasible
    lo, hi = bounds("n2_single", STAGE2["n2_single"], basis)
    out = scenario_job(("n2_single", "A4", False, None, feed.treated, M_LNG, x1, np.array([N2S_A4[n] for n in STAGE2["n2_single"]]), basis,
                        dict(method="hybrid", max_evals=8, n_restarts=0), dict(unit="t", purpose="t")))
    assert not out["feasible"] and out["fail_code"] != "" and out["n_evals"] <= 8


def test_nominal_design_evaluated_by_across_at_its_own_anchor_is_feasible(basis, a4):
    """The across-level path (eval_designs_on_set) with the nominal design: feasible at A4, SEC not above the design's own SEC."""
    from lng_robust.opt.robust import stage1_vec_of_design, x1_from_vec
    from lng_robust.study.common import nominal_design_dict
    feed, r = a4
    nom = dict(vec=[N2S_A4[n] for n in STAGE2["n2_single"]], x=dict(N2S_A4), ua_spec=r.ua / M_LNG, n_ref=r.n_ref, sec=r.sec)
    x1 = x1_from_vec("n2_single", stage1_vec_of_design("n2_single", nominal_design_dict(nom), M_LNG), M_LNG)
    ctx = SimpleNamespace(workers=1, seed=1)
    res = eval_designs_on_set(ctx, "n2_single", {"nominal": x1}, [feed], basis, nom, dict(max_evals=30, n_restarts=0), "t", None)
    de = res["nominal"]
    assert bool(de.feasible[0]) and de.sec[0] <= r.sec * (1 + 1e-9) and de.detail[0]["fail_code"] == ""
