"""Isenthalpic (Joule-Thomson) valve."""
from __future__ import annotations

from lng_robust.props.eos import Mixture, State


def valve(mix: Mixture, z, st_in: State, P_out: float, T0: float):
    out = mix.flash_PH(P_out, st_in.H, z, T_guess=st_in.T - 10.0)
    return out, T0 * (out.S - st_in.S)    # (state, exergy destruction J/mol)
