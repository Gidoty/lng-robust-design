"""Cooler to a specified outlet temperature (utility side is the dead state, so its exergy is lost)."""
from __future__ import annotations

from lng_robust.props.eos import Mixture, State


def cool_to(mix: Mixture, z, st_in: State, T_out: float, P_out: float, T0: float):
    out = mix.flash_TP(T_out, P_out, z)
    duty = st_in.H - out.H
    destruction = duty - T0 * (st_in.S - out.S)   # exergy removed: includes the exergy of rejected heat
    return out, duty, destruction
