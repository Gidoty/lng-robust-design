import pytest

from lng_robust.analysis.validation_rounding import half_ulp
from lng_robust.props.eos import get_mixture, reduce_comp, use_eos


def test_srk_option_is_distinct_from_pr_and_is_restored_after_the_context():
    pr = get_mixture(("C1",)).flash_TP(300.0, 50e5, [1.0]).rho_mass
    with use_eos("SRK"):
        srk_mix = get_mixture(("C1",))
        assert srk_mix.eos_name == "SRK"
        srk = srk_mix.flash_TP(300.0, 50e5, [1.0]).rho_mass
    assert get_mixture(("C1",)).eos_name == "PR"
    assert srk != pr and abs(srk - pr) / pr < 0.05


def test_unknown_eos_rejected():
    with pytest.raises(ValueError):
        use_eos("VDW")


def test_neqsim_backend_agrees_with_thermo_pr_on_gas_and_saturation():
    pytest.importorskip("neqsim")
    mix, z, names = reduce_comp({"C1": 0.9, "C2": 0.07, "C3": 0.03})
    nq = get_mixture(names, "NEQSIM")
    a, b = mix.flash_TP(300.0, 50e5, z), nq.flash_TP(300.0, 50e5, z)
    assert abs(a.rho_mass - b.rho_mass) / a.rho_mass < 0.02
    assert abs(mix.bubble_T(10e5, z) - nq.bubble_T(10e5, z)) < 0.2
    ph = nq.flash_PH(10e5, nq.flash_TP(160.0, 10e5, z).H, z)
    assert abs(ph.T - 160.0) < 1e-3


def test_half_ulp_of_printed_values():
    assert half_ulp("212.6") == pytest.approx(0.05) and half_ulp("3") == 0.5 and half_ulp("0.7") == pytest.approx(0.05)
