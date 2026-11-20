import CoolProp.CoolProp as CP
import pytest

from lng_robust.props.eos import get_mixture
from lng_robust.units.compressor import compress_multistage
from lng_robust.units.expander import expand
from lng_robust.units.valve import valve

N2 = get_mixture(("N2",))
Z = [1.0]


def test_isentropic_compression_work_matches_coolprop_n2():
    T1, P1, P2 = 300.0, 2e5, 8e5
    res = compress_multistage(N2, Z, T1, P1, P2, 1.0, 300.0, 0.0, 0.0, 4.0, 303.15)
    assert res.n_stages == 1
    h1, s1 = CP.PropsSI("Hmolar", "T", T1, "P", P1, "Nitrogen"), CP.PropsSI("Smolar", "T", T1, "P", P1, "Nitrogen")
    h2 = CP.PropsSI("Hmolar", "P", P2, "Smolar", s1, "Nitrogen")
    assert abs(res.work - (h2 - h1)) / (h2 - h1) < 0.01


def test_compression_work_scales_inversely_with_efficiency_and_stages_split():
    r1 = compress_multistage(N2, Z, 300.0, 5e5, 60e5, 1.0, 308.15, 0.1e5, 0.1e5, 4.0, 303.15)
    r2 = compress_multistage(N2, Z, 300.0, 5e5, 60e5, 0.75, 308.15, 0.1e5, 0.1e5, 4.0, 303.15)
    assert r1.n_stages >= 2
    assert 1.3 < r2.work / r1.work < 1.4        # work is close to 1/eta (not exact: real-gas effects)
    assert r2.exergy_destruction["compressors"] > r1.exergy_destruction["compressors"] >= -1e-2


def test_expander_isentropic_mechanics_exact_in_pr():
    """Unit mechanics: with eta=1 the outlet is the PR isentropic state, and work = H_in - H_out."""
    st_in = N2.flash_TP(200.0, 40e5, Z)
    e1 = expand(N2, Z, st_in, 8e5, 1.0, 303.15)
    iso = N2.flash_PS(8e5, st_in.S, Z)
    assert abs(e1.state_out.T - iso.T) < 1e-3 and abs(e1.work - (st_in.H - iso.H)) < 1e-3
    assert abs(e1.exergy_destruction) < 1e-2          # reversible expansion generates no entropy
    e2 = expand(N2, Z, st_in, 8e5, 0.75, 303.15)
    assert 0.74 < e2.work / e1.work < 0.76 and e2.state_out.T > e1.state_out.T and e2.exergy_destruction > 0


def test_expander_matches_coolprop_at_moderate_pressure():
    """PR vs the reference EOS at a moderate-pressure state (within 1 %). At 40 bar and 200 K the PR-vs-CoolProp
    gap in isentropic work is about 2.1 %; that is an equation-of-state effect, not a unit error (see STATUS.md)."""
    st_in = N2.flash_TP(250.0, 10e5, Z)
    e1 = expand(N2, Z, st_in, 2e5, 1.0, 303.15)
    s1 = CP.PropsSI("Smolar", "T", 250.0, "P", 10e5, "Nitrogen")
    h_in = CP.PropsSI("Hmolar", "T", 250.0, "P", 10e5, "Nitrogen")
    h_out = CP.PropsSI("Hmolar", "P", 2e5, "Smolar", s1, "Nitrogen")
    assert abs(e1.work - (h_in - h_out)) / (h_in - h_out) < 0.01


def test_valve_conserves_enthalpy_and_generates_entropy():
    st = N2.flash_TP(150.0, 40e5, Z)
    out, d = valve(N2, Z, st, 5e5, 303.15)
    assert abs(out.H - st.H) < 1e-3 * abs(st.H) + 1e-3
    assert d > 0 and out.T < st.T
