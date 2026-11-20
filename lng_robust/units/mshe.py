"""Discretised multi-stream heat exchanger (MSHE).

Each stream is tabulated as T -> (H, S) with property-package flashes (saturation points are added so
the table breaks exactly where the curve kinks). The hot and cold composite curves are inverted at N
equal-duty nodes, giving node temperatures, MITA and UA = sum(dQ_k / dT_lm,k).

Composite construction (heat released/absorbed between the cold end of the exchanger and temperature T):
  hot :  C_h(T) = sum_i  [ H_i(clip(T, T_end_i, T_start_i)) - H_i(T_end_i) ]
  cold:  C_c(T) = sum_j  [ H_j(clip(T, T_start_j, T_end_j)) - H_j(T_start_j) ]
Node k sits at cumulative duty q_k = k * Q / N from the cold end; T_h,k = C_h^-1(q_k), T_c,k = C_c^-1(q_k).
Stream pressure varies linearly with temperature between its inlet and outlet pressure.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import PchipInterpolator

from lng_robust.props.eos import FlashError, Mixture


@dataclass
class Stream:
    name: str
    side: str                 # 'hot' (releases heat) or 'cold' (absorbs heat)
    mix: Mixture | None
    z: list | None
    n: float                  # mol/s
    T_start: float            # inlet temperature in the flow direction [K]
    T_end: float              # outlet temperature [K]
    P_start: float            # Pa
    P_end: float              # Pa
    table: tuple | None = None   # optional (T, H_molar, S_molar) override, used by tests


@dataclass
class MSHEResult:
    mita: float
    ua: float                 # W/K
    duty_hot: float           # W
    duty_cold: float          # W
    balance_error: float
    temp_cross: bool
    N: int
    q: np.ndarray = field(repr=False, default=None)
    T_hot: np.ndarray = field(repr=False, default=None)
    T_cold: np.ndarray = field(repr=False, default=None)
    pinch_index: int = -1
    exergy_destruction: float = 0.0      # W
    n_flashes: int = 0


def _stream_table(s: Stream, n_table: int):
    lo, hi = (s.T_end, s.T_start) if s.side == "hot" else (s.T_start, s.T_end)
    if hi - lo < 1e-9:
        raise ValueError(f"stream {s.name} has zero temperature span")
    if s.table is not None:
        T0_, H0_, S0_ = (np.asarray(a, float) for a in s.table)
        T = np.unique(np.concatenate([[lo, hi], T0_[(T0_ > lo) & (T0_ < hi)]]))
        return T, np.interp(T, T0_, H0_) * s.n, np.interp(T, T0_, S0_) * s.n
    def P_at(T):
        f = (T - s.T_start) / (s.T_end - s.T_start)
        return s.P_start + f * (s.P_end - s.P_start)
    pts = set(np.linspace(lo, hi, n_table).tolist())
    for P in (s.P_start, s.P_end):
        for tsat in (s.mix.bubble_T(P, s.z), s.mix.dew_T(P, s.z)):
            if tsat == tsat and lo + 1e-6 < tsat < hi - 1e-6:
                pts.add(float(tsat))
    T = np.array(sorted(pts))
    H = np.empty_like(T)
    S = np.empty_like(T)
    for i, t in enumerate(T):
        st = s.mix.flash_TP(float(t), float(P_at(t)), s.z)
        H[i], S[i] = st.H, st.S
    return T, H * s.n, S * s.n


def _composite(streams, tables, side):
    grid = np.unique(np.concatenate([tables[s.name][0] for s in streams]))
    C = np.zeros_like(grid)
    for s in streams:
        T, H, _ = tables[s.name]
        f = PchipInterpolator(T, H)
        lo, hi = T[0], T[-1]
        Tc = np.clip(grid, lo, hi)
        C += f(Tc) - H[0]      # H[0] is the lowest-temperature point of the stream on either side
    return grid, C


def mshe(streams: list[Stream], N: int = 100, n_table: int = 48, T0: float = 303.15) -> MSHEResult:
    hot = [s for s in streams if s.side == "hot"]
    cold = [s for s in streams if s.side == "cold"]
    if not hot or not cold:
        raise ValueError("MSHE needs at least one hot and one cold stream")
    n0 = sum(s.mix.n_flash for s in streams if s.mix is not None)
    tables = {s.name: _stream_table(s, n_table) for s in streams}
    gh, Ch = _composite(hot, tables, "hot")
    gc, Cc = _composite(cold, tables, "cold")
    Qh, Qc = float(Ch[-1]), float(Cc[-1])
    if Qh <= 0 or Qc <= 0:
        raise FlashError("non-positive exchanger duty")
    bal = abs(Qh - Qc) / max(Qh, Qc)
    Q = 0.5 * (Qh + Qc)
    q = np.linspace(0.0, Q, N + 1)

    def invert(g, C):
        C = np.maximum.accumulate(C)
        C = C + 1e-12 * Q * np.arange(len(C))
        return np.interp(np.minimum(q, C[-1]), C, g)
    Th = invert(gh, Ch)
    Tc = invert(gc, Cc)
    dT = Th - Tc
    mita = float(dT.min())
    cross = bool((dT < 0).any())
    if cross or (dT <= 0).any():
        ua = float("nan")
    else:
        a, b = dT[:-1], dT[1:]
        with np.errstate(divide="ignore", invalid="ignore"):    # the unused np.where branch is evaluated when a ~ b
            lm = np.where(np.abs(a - b) < 1e-9 * np.maximum(a, b), 0.5 * (a + b),
                          (a - b) / np.log(np.where(b > 0, a / b, 1.0)))
        ua = float(np.sum((Q / N) / lm))
    ds_hot = sum(tables[s.name][2][-1] - tables[s.name][2][0] for s in hot)    # H,S tabulated ascending in T
    ds_cold = sum(tables[s.name][2][-1] - tables[s.name][2][0] for s in cold)
    # hot streams lose entropy (S at T_end < S at T_start): ds_hot above is S(T_hi) - S(T_lo) > 0
    exergy_d = T0 * (ds_cold - ds_hot)
    n1 = sum(s.mix.n_flash for s in streams if s.mix is not None)
    return MSHEResult(mita=mita, ua=ua, duty_hot=Qh, duty_cold=Qc, balance_error=bal, temp_cross=cross,
                      N=N, q=q, T_hot=Th, T_cold=Tc, pinch_index=int(np.argmin(dT)),
                      exergy_destruction=exergy_d, n_flashes=n1 - n0)
