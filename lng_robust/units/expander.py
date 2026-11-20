"""Turbo-expander with isentropic efficiency."""
from __future__ import annotations

from dataclasses import dataclass

from lng_robust.props.eos import Mixture, State


@dataclass
class ExpansionResult:
    work: float                  # J/mol recovered (positive)
    state_out: State
    liquid_mass_frac: float
    exergy_destruction: float    # J/mol


def expand(mix: Mixture, z, st_in: State, P_out: float, eta: float, T0: float) -> ExpansionResult:
    iso = mix.flash_PS(P_out, st_in.S, z, T_guess=st_in.T * 0.8)
    h_out = st_in.H - eta * (st_in.H - iso.H)
    out = mix.flash_PH(P_out, h_out, z, T_guess=iso.T)
    liq = max(0.0, 1.0 - out.mass_frac_gas) if (out.n_phases == 2 or out.beta_gas < 1 - 1e-9) else 0.0
    return ExpansionResult(work=st_in.H - out.H, state_out=out, liquid_mass_frac=liq,
                           exergy_destruction=T0 * (out.S - st_in.S))
