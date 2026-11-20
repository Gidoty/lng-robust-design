import math

import numpy as np
import pytest
import CoolProp.CoolProp as CP

from lng_robust.props.eos import COMPONENTS, get_mixture, kij_table, reduce_comp


def test_pure_methane_density_vs_coolprop_gas_domain():
    """2 per cent criterion, gas-phase domain: P <= 10 bar (T down to -100 C) or T >= 60 C (to 60 bar).
    Plain PR is worse than 2 per cent for dense gas and liquid; that region is written to
    runs/methane_density_map.csv by `python -m lng_robust.props.gerg_check` and listed in STATUS.md."""
    mix = get_mixture(("C1",))
    checked = 0
    for T_C in (-100, -80, -60, -20, 25, 60):
        for P_bar in (1, 5, 10, 20, 40, 60):
            in_domain = (P_bar <= 10 and T_C >= -100) or (T_C >= 60)
            if not in_domain:
                continue
            T, P = T_C + 273.15, P_bar * 1e5
            st = mix.flash_TP(T, P, [1.0])
            rho_cp = CP.PropsSI("D", "T", T, "P", P, "Methane")
            assert abs(st.rho_mass - rho_cp) / rho_cp < 0.02, (T_C, P_bar, st.rho_mass, rho_cp)
            checked += 1
    assert checked >= 15


def test_pure_methane_liquid_density_deviation_is_recorded_not_hidden():
    # Plain Peng-Robinson over-predicts liquid density (no volume translation). Characterise, do not hide.
    mix = get_mixture(("C1",))
    st = mix.flash_TP(113.15, 2e5, [1.0])
    rho_cp = CP.PropsSI("D", "T", 113.15, "P", 2e5, "Methane")
    dev = (st.rho_mass - rho_cp) / rho_cp
    assert 0.0 < abs(dev) < 0.2


def test_every_flash_closes_mass_and_components():
    mix, z, _ = reduce_comp({"N2": 0.05, "C1": 0.5, "C2": 0.2, "C3": 0.1, "nC4": 0.1, "iC5": 0.05})
    worst = 0.0
    for T in np.linspace(110, 400, 30):
        for P in (1e5, 5e5, 20e5, 50e5):
            st = mix.flash_TP(T, P, z)
            worst = max(worst, st.closure_error)
    assert worst < 1e-8


def test_ph_and_ps_flash_roundtrip():
    mix, z, _ = reduce_comp({"C1": 0.9, "C2": 0.07, "C3": 0.03})
    st = mix.flash_TP(180.0, 30e5, z)
    assert abs(mix.flash_PH(30e5, st.H, z).T - 180.0) < 1e-3
    assert abs(mix.flash_PS(30e5, st.S, z).T - 180.0) < 1e-3


def test_kij_table_complete_and_zeros_flagged():
    rows = kij_table()
    n = len(COMPONENTS)
    assert len(rows) == n * (n - 1) // 2
    for r in rows:
        assert (r[2] == 0.0) == (r[4] == "ZERO_IN_DATABANK")


def test_bubble_dew_ordering():
    mix, z, _ = reduce_comp({"C1": 0.7, "C2": 0.2, "C3": 0.1})
    assert mix.bubble_T(10e5, z) < mix.dew_T(10e5, z)
