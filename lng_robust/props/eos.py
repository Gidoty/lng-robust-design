"""Peng-Robinson property layer built on the open-source `thermo` library.

Everything that needs a thermodynamic property in this repository goes through this module.
Units: T [K], P [Pa], H [J/mol], S [J/mol/K], rho_mass [kg/m3], MW [g/mol].
"""
from __future__ import annotations

import functools
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq
from thermo import (CEOSGas, CEOSLiquid, ChemicalConstantsPackage, FlashPureVLS, FlashVL,
                    PRMIX, PropertyCorrelationsPackage, SRKMIX)
from thermo.interaction_parameters import IPDB

# Short component names used everywhere in the repo -> `thermo`/`chemicals` identifiers.
COMPONENTS = ["N2", "CO2", "C1", "C2", "C3", "iC4", "nC4", "iC5", "nC5", "C6"]
THERMO_IDS = {
    "N2": "nitrogen", "CO2": "carbon dioxide", "C1": "methane", "C2": "ethane",
    "C3": "propane", "iC4": "isobutane", "nC4": "butane", "iC5": "isopentane",
    "nC5": "pentane", "C6": "hexane",
}
KIJ_DATABANK = "ChemSep PR"  # thermo.interaction_parameters.IPDB table name
# Equation of state. PR is the study default. SRK exists only to reproduce published SRK benchmarks; it reuses the PR
# binary interaction parameters (no SRK kij table is available in `thermo`), so an SRK run is a labelled cross-check,
# not a reproduction of the original package's SRK parameters.
EOS_CLASSES = {"PR": PRMIX, "SRK": SRKMIX, "NEQSIM": None}   # NEQSIM is routed to props/neqsim_backend.py
_DEFAULT_EOS = "PR"


def default_eos() -> str:
    return _DEFAULT_EOS


class use_eos:
    """Context manager: temporarily switch the default equation of state (single process)."""

    def __init__(self, name: str):
        if name not in EOS_CLASSES:
            raise ValueError(f"unknown EOS {name}")
        self.name = name

    def __enter__(self):
        global _DEFAULT_EOS
        self.prev, _DEFAULT_EOS = _DEFAULT_EOS, self.name

    def __exit__(self, *a):
        global _DEFAULT_EOS
        _DEFAULT_EOS = self.prev
ZERO_TOL = 1e-12


class FlashError(RuntimeError):
    """Raised when a flash cannot be completed or fails its mass-closure check."""


@dataclass
class State:
    T: float
    P: float
    z: list
    names: tuple
    beta_gas: float          # molar vapour fraction (1 = all gas, 0 = all liquid)
    H: float                 # J/mol
    S: float                 # J/mol/K
    rho_mass: float          # kg/m3 (bulk)
    MW: float                # g/mol (bulk)
    n_phases: int
    mass_frac_gas: float
    closure_error: float = 0.0
    x_liq: list | None = None
    y_gas: list | None = None
    extras: dict = field(default_factory=dict)

    @property
    def beta_liq(self) -> float:
        return 1.0 - self.beta_gas

    @property
    def H_mass(self) -> float:  # J/kg
        return self.H / self.MW * 1e3

    @property
    def S_mass(self) -> float:  # J/kg/K
        return self.S / self.MW * 1e3


@functools.lru_cache(maxsize=None)
def _full_constants():
    consts, corr = ChemicalConstantsPackage.from_IDs([THERMO_IDS[c] for c in COMPONENTS])
    kij = np.array(IPDB.get_ip_asymmetric_matrix(KIJ_DATABANK, consts.CASs, "kij"), dtype=float)
    return consts, corr, kij


def kij_table():
    """Return list of (name_i, name_j, kij, source, flag) for every unique pair."""
    consts, _, kij = _full_constants()
    rows = []
    for i, ci in enumerate(COMPONENTS):
        for j in range(i + 1, len(COMPONENTS)):
            v = float(kij[i, j])
            flag = "ZERO_IN_DATABANK" if v == 0.0 else ""
            rows.append((ci, COMPONENTS[j], v, f"thermo IPDB '{KIJ_DATABANK}' (ChemSep)", flag))
    return rows


_REGISTRY: list = []


def flash_count() -> int:
    """Total number of flash calls made so far in this process (all mixtures)."""
    return sum(m.n_flash for m in _REGISTRY)


class Mixture:
    """A Peng-Robinson fluid restricted to a fixed subset of components."""

    def __init__(self, names: tuple[str, ...], eos: str = "PR"):
        self.names = tuple(names)
        self.eos_name = eos
        idx = [COMPONENTS.index(n) for n in self.names]
        consts_full, corr_full, kij_full = _full_constants()
        consts, corr = ChemicalConstantsPackage.from_IDs([THERMO_IDS[n] for n in self.names])
        kij = kij_full[np.ix_(idx, idx)].tolist() if len(idx) > 1 else [[0.0]]
        eos_kw = dict(Tcs=consts.Tcs, Pcs=consts.Pcs, omegas=consts.omegas, kijs=kij)
        cls = EOS_CLASSES[eos]
        gas = CEOSGas(cls, eos_kw, HeatCapacityGases=corr.HeatCapacityGases)
        liq = CEOSLiquid(cls, eos_kw, HeatCapacityGases=corr.HeatCapacityGases)
        self.consts = consts
        if len(self.names) == 1:   # FlashVL cannot handle a pure fluid
            self.flasher = FlashPureVLS(consts, corr, gas=gas, liquids=[liq], solids=[])
        else:
            self.flasher = FlashVL(consts, corr, liquid=liq, gas=gas)
        self.MWs = list(consts.MWs)
        self.n_flash = 0
        _REGISTRY.append(self)

    # ---- helpers -------------------------------------------------------------------
    def vec(self, comp) -> list:
        """dict {name: mole fraction} or sequence -> normalised list in this mixture's order."""
        if isinstance(comp, dict):
            extra = {k: v for k, v in comp.items() if k not in self.names and abs(v) > ZERO_TOL}
            if extra:
                raise ValueError(f"components {sorted(extra)} not in mixture {self.names}")
            z = [float(comp.get(n, 0.0)) for n in self.names]
        else:
            z = [float(v) for v in comp]
        s = sum(z)
        if s <= 0:
            raise ValueError("composition sums to zero")
        return [v / s for v in z]

    def _state(self, r, z, T, P) -> State:
        beta_g = 0.0
        x_liq = y_gas = None
        if r.gas is not None and r.liquids:
            beta_g = float(r.gas_beta)
            y_gas = list(r.gas.zs)
            x_liq = list(r.liquid0.zs)
        elif r.gas is not None:
            beta_g = 1.0
            y_gas = list(z)
        else:
            beta_g = 0.0
            x_liq = list(z)
        # mass closure: sum_p beta_p * z_p == z  and  sum_p beta_p * MW_p == MW_mix
        comp_err = 0.0
        mw_mix = sum(zi * m for zi, m in zip(z, self.MWs))
        recon = [0.0] * len(z)
        mw_recon = 0.0
        if y_gas is not None:
            recon = [recon[i] + beta_g * y_gas[i] for i in range(len(z))]
            mw_recon += beta_g * sum(y * m for y, m in zip(y_gas, self.MWs))
        if x_liq is not None:
            recon = [recon[i] + (1 - beta_g) * x_liq[i] for i in range(len(z))]
            mw_recon += (1 - beta_g) * sum(x * m for x, m in zip(x_liq, self.MWs))
        comp_err = max(abs(a - b) for a, b in zip(recon, z))
        mass_err = abs(mw_recon - mw_mix) / mw_mix
        err = max(comp_err, mass_err)
        mwg = sum(y * m for y, m in zip(y_gas, self.MWs)) if y_gas else 0.0
        mass_frac_gas = beta_g * mwg / mw_mix
        return State(T=float(T), P=float(P), z=list(z), names=self.names, beta_gas=beta_g,
                     H=float(r.H()), S=float(r.S()), rho_mass=float(r.rho_mass()), MW=mw_mix,
                     n_phases=int(r.phase_count), mass_frac_gas=mass_frac_gas,
                     closure_error=err, x_liq=x_liq, y_gas=y_gas)

    def _check(self, st: State):
        if st.closure_error > 1e-8:
            raise FlashError(f"mass closure failed: {st.closure_error:.2e}")
        if not all(math.isfinite(v) for v in (st.T, st.H, st.S)):
            raise FlashError("non-finite flash result")

    # ---- flashes --------------------------------------------------------------------
    def flash_TP(self, T: float, P: float, z) -> State:
        z = self.vec(z)
        self.n_flash += 1
        try:
            r = self.flasher.flash(T=float(T), P=float(P), zs=z)
            st = self._state(r, z, T, P)
        except FlashError:
            raise
        except Exception as e:  # thermo raises many exception types
            raise FlashError(f"TP flash failed (T={T:.2f} K, P={P/1e5:.2f} bar): {e}") from e
        self._check(st)
        return st

    def _solve_T(self, target, prop, P, z, T_guess):
        """Bracketing solve of prop(T,P)=target via TP flashes (robust fallback)."""
        def f(T):
            st = self.flash_TP(T, P, z)
            return getattr(st, prop) - target
        lo = hi = T_guess if T_guess else 200.0
        step = 20.0
        flo = fhi = None
        for _ in range(40):
            lo = max(lo - step, 20.0)
            hi = hi + step
            try:
                flo, fhi = f(lo), f(hi)
            except FlashError:
                step *= 1.3
                continue
            if flo * fhi <= 0:
                break
            step *= 1.5
        else:
            raise FlashError(f"could not bracket {prop}={target:.4g} at P={P/1e5:.2f} bar")
        T = brentq(f, lo, hi, xtol=1e-8, rtol=1e-12)
        return self.flash_TP(T, P, z)

    def flash_PH(self, P: float, H: float, z, T_guess: float | None = None) -> State:
        z = self.vec(z)
        self.n_flash += 1
        try:
            r = self.flasher.flash(H=float(H), P=float(P), zs=z)
            st = self._state(r, z, r.T, P)
            self._check(st)
            if abs(st.H - H) <= 1e-6 * max(1.0, abs(H)) + 1e-3:
                return st
        except Exception:
            pass
        return self._solve_T(H, "H", P, z, T_guess)

    def flash_PS(self, P: float, S: float, z, T_guess: float | None = None) -> State:
        z = self.vec(z)
        self.n_flash += 1
        try:
            r = self.flasher.flash(S=float(S), P=float(P), zs=z)
            st = self._state(r, z, r.T, P)
            self._check(st)
            if abs(st.S - S) <= 1e-7 * max(1.0, abs(S)) + 1e-5:
                return st
        except Exception:
            pass
        return self._solve_T(S, "S", P, z, T_guess)

    def saturation_T(self, P: float, z, vf: float) -> float:
        """Bubble (vf=0) or dew (vf=1) temperature at pressure P [K]; nan if not defined."""
        z = self.vec(z)
        try:
            r = self.flasher.flash(VF=vf, P=float(P), zs=z)
            return float(r.T)
        except Exception:
            return float("nan")

    def bubble_T(self, P, z):
        return self.saturation_T(P, z, 0.0)

    def dew_T(self, P, z):
        return self.saturation_T(P, z, 1.0)


@functools.lru_cache(maxsize=None)
def _get_mixture(names: tuple, eos: str):
    if eos == "NEQSIM":          # independent PR property engine, cross-check only
        from lng_robust.props.neqsim_backend import NeqSimMixture
        m = NeqSimMixture(tuple(names))
        _REGISTRY.append(m)
        return m
    return Mixture(tuple(names), eos)


def get_mixture(names: tuple[str, ...], eos: str | None = None) -> Mixture:
    return _get_mixture(tuple(names), eos or _DEFAULT_EOS)


def reduce_comp(comp: dict) -> tuple[Mixture, list, tuple]:
    """Drop zero components from a {name: mole fraction} dict and return (mixture, z, names).

    Component order follows COMPONENTS so equal compositions share one cached Mixture.
    """
    comp = {k: float(v) for k, v in comp.items() if abs(float(v)) > ZERO_TOL}
    for k in comp:
        if k not in COMPONENTS:
            raise ValueError(f"unknown component {k}")
    names = tuple(c for c in COMPONENTS if c in comp)
    mix = get_mixture(names)
    return mix, mix.vec(comp), names


def mol_to_mass_frac(comp: dict) -> dict:
    mix, z, names = reduce_comp(comp)
    mw = sum(zi * m for zi, m in zip(z, mix.MWs))
    return {n: zi * m / mw for n, zi, m in zip(names, z, mix.MWs)}


def mixture_MW(comp: dict) -> float:
    mix, z, _ = reduce_comp(comp)
    return sum(zi * m for zi, m in zip(z, mix.MWs))
