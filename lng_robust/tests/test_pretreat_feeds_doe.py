import numpy as np
import pytest

from lng_robust.config import load_basis
from lng_robust.cycles.pretreat import meets_spec, pretreat
from lng_robust.doe.dirichlet import choose_kappa, sample_dirichlet
from lng_robust.doe.feeds import Feed, load_feeds
from lng_robust.tests.conftest import A1_RAW


def test_pretreat_meets_spec_and_conserves_moles():
    pt = pretreat(A1_RAW)
    assert meets_spec(pt.treated) == []
    raw_n = sum(A1_RAW.values())
    # removed CO2 is not tracked as a stream; hydrocarbons removed go to the NGL stream
    assert abs(sum(pt.treated.values()) - 1.0) < 1e-12
    assert pt.ngl_mol_per_mol_feed > 0 and abs(sum(pt.ngl_comp.values()) - 1.0) < 1e-12


def test_pretreat_is_identity_for_a_feed_already_in_spec():
    z = {"C1": 0.95, "C2": 0.03, "C3": 0.015, "nC4": 0.004, "N2": 0.001}
    pt = pretreat(z)
    assert pt.notes == [] and pt.ngl_mol_per_mol_feed == 0
    assert all(abs(pt.treated[k] - v) < 1e-12 for k, v in z.items())


def test_feed_register_loads_verified_anchors_and_skips_unverified_and_todo(basis):
    feeds, skipped = load_feeds(basis)
    assert [f.id for f in feeds] == [f"A{i}" for i in range(2, 9)]
    assert {t["id"]: t["status"] for t in skipped} == {"A1": "unverified", "A9": "TODO"}
    a2 = feeds[0]
    assert a2.raw_mol_pct["C1"] == 91.20 and a2.raw_mol_pct["C5_total"] == 0.08 and "iC5" not in a2.raw_mol_pct
    assert abs(a2.raw_sum - 99.99) < 1e-9 and a2.synthetic is False and a2.grade == "secondary"
    d = next(f for f in feeds if f.id == "A5")
    assert d.raw_mol_pct["N2"] == 42.74            # Field D, as printed
    for f in feeds:
        assert 99.9 <= f.raw_sum <= 100.0 and "Ucheckukwu" in f.source


def test_dirichlet_samples_are_labelled_synthetic_and_in_spec(basis):
    a1 = load_feeds(basis)[0][0]
    s = sample_dirichlet(a1, 150.0, 25, seed=3, basis=basis)
    assert len(s) == 25 and all(f.synthetic and f.parent_id == a1.id and f.kappa == 150.0 for f in s)
    assert all(meets_spec(f.treated) == [] and abs(sum(f.treated.values()) - 1) < 1e-9 for f in s)
    assert sample_dirichlet(a1, 150.0, 5, seed=3, basis=basis)[2].treated == s[2].treated    # seeded, reproducible


def test_dirichlet_mean_matches_anchor(basis):
    a1 = load_feeds(basis)[0][0]
    s = sample_dirichlet(a1, 300.0, 400, seed=5, basis=basis)
    m = np.mean([f.sim_raw["C1"] for f in s])
    expected = 100 * a1.sim_raw["C1"] / sum(a1.sim_raw.values())    # synthetic samples come from the renormalised anchor
    assert abs(m - expected) < 0.3


def test_choose_kappa_needs_two_anchors(basis):
    a1 = load_feeds(basis)[0][0]
    k, note = choose_kappa([a1])
    assert "PLACEHOLDER" in note
    b = Feed("B", "x", "x", "primary", {}, 100.0, 0.0, sim_raw={"C1": 85.0})
    a = Feed("A", "x", "x", "primary", {}, 100.0, 0.0, sim_raw={"C1": 95.0})
    k, note = choose_kappa([a, b])
    assert note == "from anchor range" and 10 < k < 200
