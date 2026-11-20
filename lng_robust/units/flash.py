"""End-flash of the cold LNG stream to storage pressure."""
from __future__ import annotations

from dataclasses import dataclass

from lng_robust.props.eos import Mixture, State


@dataclass
class EndFlashResult:
    state_after_valve: State
    mass_frac_liquid: float        # kg LNG / kg feed
    mole_frac_gas: float           # mol flash gas / mol feed
    lng_comp: dict                 # mole fractions of the liquid product
    gas_comp: dict                 # mole fractions of the flash gas
    state_lng: State | None        # liquid product state (saturated at storage pressure)
    state_gas: State | None
    exergy_destruction: float      # J/mol feed (valve)


def end_flash(mix: Mixture, z, st_in: State, P_store: float, T0: float) -> EndFlashResult:
    out = mix.flash_PH(P_store, st_in.H, z, T_guess=st_in.T - 20.0)
    names = mix.names
    if out.n_phases == 2:
        liq, gas = out.x_liq, out.y_gas
        bg = out.beta_gas
        mw_l = sum(x * m for x, m in zip(liq, mix.MWs))
        mass_liq = (1 - bg) * mw_l / out.MW
        s_l = mix.flash_TP(out.T, P_store, liq)
        s_g = mix.flash_TP(out.T, P_store, gas)
    elif out.beta_gas <= 0.0:
        liq, gas, bg, mass_liq = list(z), None, 0.0, 1.0
        s_l, s_g = out, None
    else:
        liq, gas, bg, mass_liq = None, list(z), 1.0, 0.0
        s_l, s_g = None, out
    return EndFlashResult(state_after_valve=out, mass_frac_liquid=mass_liq, mole_frac_gas=bg,
                          lng_comp=dict(zip(names, liq)) if liq else {},
                          gas_comp=dict(zip(names, gas)) if gas else {},
                          state_lng=s_l, state_gas=s_g,
                          exergy_destruction=T0 * (out.S - st_in.S))
