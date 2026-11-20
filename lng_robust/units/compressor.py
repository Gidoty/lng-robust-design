"""Multistage compression with intercooling (isentropic efficiency, equal pressure ratios)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from lng_robust.props.eos import Mixture, State


@dataclass
class CompressionResult:
    work: float                    # J/mol, shaft work
    n_stages: int
    state_out: State               # after the final (after)cooler, at T_cool
    discharge_state: State         # hot gas leaving the last stage
    suction_states: list = field(default_factory=list)
    min_superheat_K: float = math.inf     # smallest (T - T_dew) over all stage suctions; <0 means liquid
    exergy_destruction: dict = field(default_factory=dict)  # J/mol: compressors, coolers
    cooler_duty: float = 0.0       # J/mol rejected in inter/after coolers
    liquid_at_suction: bool = False


def suction_margin(mix: Mixture, st: State) -> float:
    """Superheat margin T - T_dew [K] at the given pressure. Negative means liquid is present."""
    tdew = mix.dew_T(st.P, st.z)
    if tdew != tdew:      # no dew point (supercritical): gas-like, large margin
        return 1e3
    return st.T - tdew


def compress_multistage(mix: Mixture, z, T_in: float, P_in: float, P_out: float, eta: float,
                        T_cool: float, dp_inter: float, dp_after: float, pr_max: float,
                        T0: float) -> CompressionResult:
    pr = P_out / P_in
    if pr <= 1.0:
        raise ValueError("compressor needs P_out > P_in")
    n = max(1, math.ceil(math.log(pr) / math.log(pr_max) - 1e-12))
    r = pr ** (1.0 / n)
    st = mix.flash_TP(T_in, P_in, z)
    work = 0.0
    d_comp = d_cool = 0.0
    cool_duty = 0.0
    suctions = [st]
    min_sh = suction_margin(mix, st)
    liquid = min_sh < 0
    suction_P = P_in
    discharge = None
    for k in range(n):
        d_P = P_out if k == n - 1 else suction_P * r
        iso = mix.flash_PS(d_P, st.S, z, T_guess=st.T * (d_P / st.P) ** 0.25)
        h_out = st.H + (iso.H - st.H) / eta
        real = mix.flash_PH(d_P, h_out, z, T_guess=iso.T)
        work += real.H - st.H
        d_comp += T0 * (real.S - st.S)
        discharge = real
        cool_P = d_P - (dp_after if k == n - 1 else dp_inter)
        cooled = mix.flash_TP(T_cool, cool_P, z)
        cool_duty += real.H - cooled.H
        d_cool += (real.H - cooled.H) - T0 * (real.S - cooled.S)
        if k < n - 1:
            sh = suction_margin(mix, cooled)
            min_sh = min(min_sh, sh)
            liquid = liquid or sh < 0
            suctions.append(cooled)
            st = cooled
            suction_P = cooled.P
        else:
            st = cooled
    return CompressionResult(work=work, n_stages=n, state_out=st, discharge_state=discharge,
                             suction_states=suctions, min_superheat_K=min_sh,
                             exergy_destruction={"compressors": d_comp, "coolers": d_cool},
                             cooler_duty=cool_duty, liquid_at_suction=liquid)
