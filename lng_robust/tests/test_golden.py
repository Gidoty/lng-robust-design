"""Speed-ups must not change results. 20 fixed cases, reference output produced by the code BEFORE any optimisation
(tests/data/golden_eval.csv, written once by analysis/golden.py), compared at 1e-9 relative tolerance."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lng_robust.analysis.golden import NUMERIC, evaluate, make_cases

GOLD = Path(__file__).parent / "data" / "golden_eval.csv"


@pytest.fixture(scope="module")
def current(basis):
    return pd.DataFrame(evaluate(make_cases(basis), basis))


def test_golden_has_twenty_cases_with_mixed_outcomes():
    g = pd.read_csv(GOLD)
    assert len(g) == 20 and g["feasible"].sum() >= 4 and (~g["feasible"]).sum() >= 8


def test_outputs_equal_reference_at_1e9(current):
    g = pd.read_csv(GOLD)
    assert list(current["case"]) == list(g["case"])
    assert (current["feasible"].values == g["feasible"].values).all()
    assert (current["failure_code"].fillna("").values == g["failure_code"].fillna("").values).all()
    for col in NUMERIC:
        a, b = current[col].astype(float).values, g[col].astype(float).values
        assert (np.isnan(a) == np.isnan(b)).all(), col
        m = ~np.isnan(a)
        np.testing.assert_allclose(a[m], b[m], rtol=1e-9, atol=1e-12, err_msg=col)


def test_cache_returns_the_identical_object_and_counts_hits(basis):
    from lng_robust.props.eos import get_mixture
    m = get_mixture(("C1", "C2"))
    s1 = m.flash_TP(200.0, 30e5, [0.9, 0.1])
    h0 = m.n_cache_hits
    s2 = m.flash_TP(200.0, 30e5, [0.9, 0.1])
    assert s2 is s1 and m.n_cache_hits == h0 + 1


def test_cache_off_gives_bitwise_equal_results(monkeypatch):
    import lng_robust.props.eos as eos
    m = eos.get_mixture(("C1", "C2", "C3"))
    z = [0.8, 0.15, 0.05]
    on = m.flash_TP(150.0, 25e5, z)
    monkeypatch.setattr(eos, "FLASH_CACHE_ON", False)
    off = m.flash_TP(150.0, 25e5, z)
    assert off is not on and (on.H, on.S, on.rho_mass, on.beta_gas) == (off.H, off.S, off.rho_mass, off.beta_gas)
