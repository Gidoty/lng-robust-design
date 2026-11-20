from lng_robust.doe.feeds import load_feeds
from lng_robust.doe.scenarios import build_scenarios, choose_kappa_robust, choose_nominal


def test_kappa_is_robust_to_the_nitrogen_outlier_and_recorded(basis):
    anchors, _ = load_feeds(basis)
    k, info = choose_kappa_robust(anchors)
    assert 20 < k < 500 and set(info["kappa_by_component"]) == {"C1", "C2", "C3", "N2"} and info["n_anchors"] == 7


def test_nominal_is_a_loaded_anchor_and_rule_is_stated(basis):
    anchors, _ = load_feeds(basis)
    nom, info = choose_nominal(anchors)
    assert nom.id in info["anchor_ids"] and "closest" in info["reason"] and not nom.synthetic


def test_scenario_set_has_s_members_with_anchors_unlabelled_synthetic_and_samples_labelled(basis):
    anchors, _ = load_feeds(basis)
    scen = build_scenarios(anchors, 50, 71.0, 20260101, basis)
    assert len(scen) == 50
    assert sum(not f.synthetic for f in scen) == 7 and sum(f.synthetic for f in scen) == 43
    assert all(f.parent_id in {a.id for a in anchors} for f in scen if f.synthetic)
    again = build_scenarios(anchors, 50, 71.0, 20260101, basis)
    assert [f.treated for f in scen] == [f.treated for f in again]          # fixed seed
    assert len(build_scenarios(anchors, 50, 71.0, 1, basis, exclude_ids=("A5",))) == 50
