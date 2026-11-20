"""Shared result object, failure codes, feed-side calculation and exergy bookkeeping for the cycles."""
from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field

from lng_robust.cycles.pretreat import meets_spec
import os

from lng_robust.props.eos import FlashError, Mixture, State, flash_count, reduce_comp
from lng_robust.units.flash import end_flash

KWH_PER_J = 1.0 / 3.6e6

# Failure codes. The first six are the specified set; the rest are additional physical checks.
NONCONVERGED = "NONCONVERGED"
TEMP_CROSS = "TEMP_CROSS"
MITA_VIOLATION = "MITA_VIOLATION"
LIQUID_AT_SUCTION = "LIQUID_AT_SUCTION"
PRODUCT_SPEC = "PRODUCT_SPEC"
FLASH_FAIL = "FLASH_FAIL"
LIQUID_AT_EXPANDER = "LIQUID_AT_EXPANDER"      # extra: liquid above the allowed fraction at expander outlet
UA_EXCEEDED = "UA_EXCEEDED"                      # extra: required UA above installed UA
RATED_FLOW_EXCEEDED = "RATED_FLOW_EXCEEDED"      # extra: refrigerant flow above rated machine flow
BAD_INPUT = "BAD_INPUT"                          # extra: decision variables outside a physical ordering
NUMERICAL_CODES = {NONCONVERGED, FLASH_FAIL}     # all others are physical infeasibility
PRECEDENCE = [FLASH_FAIL, NONCONVERGED, BAD_INPUT, PRODUCT_SPEC, LIQUID_AT_SUCTION, LIQUID_AT_EXPANDER,
              TEMP_CROSS, MITA_VIOLATION, UA_EXCEEDED, RATED_FLOW_EXCEEDED]


@dataclass
class CycleResult:
    cycle: str
    sec: float = float("nan")                  # kWh per kg LNG, net of expander work
    exergy_eff: float = float("nan")
    mita: float = float("nan")                 # K
    ua: float = float("nan")                   # kW/K required
    w_comp_kw: float = float("nan")
    w_exp_kw: float = 0.0
    m_lng: float = float("nan")                # kg/s
    m_feed: float = float("nan")               # kg/s
    n_feed: float = float("nan")               # mol/s
    n_ref: float = float("nan")                # mol/s
    exergy_destruction_kw: dict = field(default_factory=dict)
    lng_comp: dict = field(default_factory=dict)
    end_flash_fraction: float = float("nan")   # mol flash gas per mol feed
    lng_mass_frac: float = float("nan")        # kg LNG per kg feed after end flash
    converged: bool = False
    feasible: bool = False
    failure_code: str = ""
    failure_codes: list = field(default_factory=list)
    failure_msg: str = ""
    violation: float = 0.0                     # >= 0 continuous constraint violation (0 = feasible)
    tear_iterations: int = 0
    tear_residual: float = float("nan")
    balance_error: float = float("nan")        # energy-balance mismatch of the MSHE composites
    exergy_closure_error: float = float("nan")
    runtime_s: float = float("nan")
    n_flash: int = 0
    details: dict = field(default_factory=dict)

    def as_row(self) -> dict:
        d = asdict(self)
        d["exergy_destruction_kw"] = ";".join(f"{k}={v:.4g}" for k, v in self.exergy_destruction_kw.items())
        d["lng_comp"] = ";".join(f"{k}={v:.5f}" for k, v in self.lng_comp.items())
        d["failure_codes"] = ";".join(self.failure_codes)
        d.pop("details")
        for k, v in self.details.items():
            if isinstance(v, (int, float, str, bool)):
                d[f"d_{k}"] = v
        return d


class Fail(Exception):
    def __init__(self, code, msg="", violation=1e3):
        super().__init__(msg)
        self.code, self.msg, self.violation = code, msg, violation


def pick_code(codes: list) -> str:
    for c in PRECEDENCE:
        if c in codes:
            return c
    return codes[0] if codes else ""


@dataclass
class FeedSide:
    mix: Mixture
    z: list
    names: tuple
    st_in: State
    st_out: State
    ef: object
    m_feed: float
    n_feed: float
    mw: float


def feed_side(feed: dict, feed_T: float, feed_P: float, T_lng: float, m_lng: float, basis) -> FeedSide:
    mix, z, names = reduce_comp(feed)
    bad = meets_spec(dict(zip(names, z)), basis.pretreat_co2_ppmv, basis.pretreat_c4plus_mol_pct,
                     basis.pretreat_c5plus_mol_pct)
    if bad:
        raise Fail(PRODUCT_SPEC, f"treated feed violates spec: {bad}", violation=1.0)
    st_in = mix.flash_TP(feed_T, feed_P, z)
    p_cold = feed_P - basis.dp_mshe_ng_bar * 1e5
    st_out = mix.flash_TP(T_lng, p_cold, z)
    ef = end_flash(mix, z, st_out, basis.lng_storage_pressure_bar * 1e5, basis.T0)
    phi = ef.mass_frac_liquid
    if phi < basis.min_end_flash_liquid_mass_frac:
        raise Fail(PRODUCT_SPEC, f"LNG mass fraction after end flash {phi:.3f} below minimum "
                   f"{basis.min_end_flash_liquid_mass_frac}", violation=1.0 + (basis.min_end_flash_liquid_mass_frac - phi))
    m_feed = m_lng / phi
    return FeedSide(mix, z, names, st_in, st_out, ef, m_feed, m_feed / (st_in.MW / 1e3), st_in.MW)


_REF_CACHE: dict = {}


def _ref(mix: Mixture, z, T0, P0):
    key = (mix.names, mix.eos_name, tuple(round(v, 12) for v in z), T0, P0)
    if key not in _REF_CACHE:
        _REF_CACHE[key] = mix.flash_TP(T0, P0, z)
    return _REF_CACHE[key]


def phys_exergy(mix: Mixture, z, st: State, T0: float, P0: float) -> float:
    """Specific physical exergy [J/mol] relative to the same composition at the dead state."""
    r = _ref(mix, z, T0, P0)
    return (st.H - r.H) - T0 * (st.S - r.S)


def exergy_products(fs: FeedSide, n_lng_mol: float, basis):
    """Exergy flows [W] of feed, LNG, flash gas and the ambient-composition term X of the end flash."""
    T0, P0 = basis.T0, basis.P0
    ef = fs.ef
    E_feed = fs.n_feed * phys_exergy(fs.mix, fs.z, fs.st_in, T0, P0)
    n_lng = fs.n_feed * (1 - ef.mole_frac_gas)
    n_fg = fs.n_feed * ef.mole_frac_gas
    E_lng = E_fg = 0.0
    g_prod = 0.0
    if ef.state_lng is not None:
        zl = [ef.lng_comp.get(n, 0.0) for n in fs.names]
        E_lng = n_lng * phys_exergy(fs.mix, zl, ef.state_lng, T0, P0)
        r = _ref(fs.mix, zl, T0, P0)
        g_prod += n_lng * (r.H - T0 * r.S)
    if ef.state_gas is not None:
        zg = [ef.gas_comp.get(n, 0.0) for n in fs.names]
        E_fg = n_fg * phys_exergy(fs.mix, zg, ef.state_gas, T0, P0)
        r = _ref(fs.mix, zg, T0, P0)
        g_prod += n_fg * (r.H - T0 * r.S)
    rf = _ref(fs.mix, fs.z, T0, P0)
    X = g_prod - fs.n_feed * (rf.H - T0 * rf.S)
    return E_feed, E_lng, E_fg, X, n_lng


def finalise(res: CycleResult, fs: FeedSide, W_comp: float, W_exp: float, D: dict, basis) -> CycleResult:
    """Fill SEC, exergy numbers and feasibility flags (all W, J/s)."""
    res.w_comp_kw = W_comp / 1e3
    res.w_exp_kw = W_exp / 1e3
    W_net = W_comp - W_exp
    res.sec = W_net / res.m_lng * KWH_PER_J
    E_feed, E_lng, E_fg, X, n_lng = exergy_products(fs, 0.0, basis)
    D_total = sum(D.values())
    res.exergy_destruction_kw = {k: v / 1e3 for k, v in D.items()}
    # specific-exergy based efficiency (manuscript Eq. 5)
    m_lng = res.m_lng
    e_lng = E_lng / m_lng if m_lng else float("nan")
    e_feed_per_kg = E_feed / fs.m_feed
    res.exergy_eff = m_lng * (e_lng - e_feed_per_kg) / W_net if W_net > 0 else float("nan")
    # Exact plant balance: W_net + E_feed - E_lng - E_fg - D_total = +X, where X is the composition-change
    # term of the end-flash split (each product stream is referenced to its own composition at the dead state).
    res.exergy_closure_error = (W_net + E_feed - E_lng - E_fg - D_total - X) / max(abs(W_net), 1.0)
    res.details["E_feed_kw"] = E_feed / 1e3
    res.details["E_lng_kw"] = E_lng / 1e3
    res.details["E_flashgas_kw"] = E_fg / 1e3
    res.details["X_endflash_composition_kw"] = X / 1e3
    return res


def solve_tear(step, T_guess: float, tol: float, max_iter: int):
    """Fixed-point iteration on the refrigerant return temperature (tear stream)."""
    T = T_guess
    for it in range(1, max_iter + 1):
        T_new, payload = step(T)
        resid = abs(T_new - T) / T_new
        if resid < tol:
            return T_new, it, resid, payload
        T = T_new
    raise Fail(NONCONVERGED, f"tear stream not converged after {max_iter} iterations (residual {resid:.2e})")


def check_constraints(res, basis, mr, suction_margin_K, exp_liquid, ua_inst, n_rated, codes, viol):
    """Append failure codes / violation magnitudes from the MSHE result and unit limits."""
    mita_min = basis.mita_min_K
    res.mita, res.ua = mr.mita, (mr.ua / 1e3 if mr.ua == mr.ua else float("nan"))
    res.balance_error = mr.balance_error
    if mr.balance_error > basis.balance_tol:
        codes.append(NONCONVERGED)
        viol["balance"] = mr.balance_error / basis.balance_tol
        res.failure_msg += f"MSHE duty mismatch {mr.balance_error:.2e}; "
    if mr.temp_cross:
        codes.append(TEMP_CROSS)
        viol["mita"] = (mita_min - mr.mita) / mita_min
    elif mr.mita < mita_min - 1e-9:
        codes.append(MITA_VIOLATION)
        viol["mita"] = (mita_min - mr.mita) / mita_min
    if suction_margin_K < basis.min_suction_superheat_K - 1e-9:
        codes.append(LIQUID_AT_SUCTION)
        viol["suction"] = (basis.min_suction_superheat_K - suction_margin_K) / 10.0
    if exp_liquid > basis.max_expander_liquid_mass_frac + 1e-9:
        codes.append(LIQUID_AT_EXPANDER)
        viol["expander_liquid"] = exp_liquid - basis.max_expander_liquid_mass_frac
    if ua_inst and res.ua == res.ua and res.ua > ua_inst * (1 + 1e-9):
        codes.append(UA_EXCEEDED)
        viol["ua"] = res.ua / ua_inst - 1
    if n_rated and res.n_ref > n_rated * (1 + 1e-9):
        codes.append(RATED_FLOW_EXCEEDED)
        viol["rated_flow"] = res.n_ref / n_rated - 1


def run_cycle(name, body, feed, feed_T, feed_P, m_lng, x, basis) -> CycleResult:
    """Run a cycle body; convert every failure into a coded result. Nothing is dropped."""
    t0 = time.perf_counter()
    f0 = flash_count()
    res = CycleResult(cycle=name, m_lng=m_lng)
    codes: list = []
    viol: dict = {}
    try:
        body(res, feed, feed_T, feed_P, m_lng, x, basis, codes, viol)
        res.converged = True
    except Fail as f:
        codes.append(f.code)
        res.failure_msg += f.msg
        viol[f.code] = f.violation
        res.converged = f.code not in NUMERICAL_CODES
    except FlashError as e:
        codes.append(FLASH_FAIL)
        res.failure_msg += str(e)
        viol[FLASH_FAIL] = 1e3
    except Exception as e:      # unexpected thermo/solver exception: log it, do not drop the case
        if os.environ.get("LNG_STRICT") == "1":
            raise
        codes.append(FLASH_FAIL)
        res.failure_msg += f"{type(e).__name__}: {e}"
        viol[FLASH_FAIL] = 1e3
    res.failure_codes = list(dict.fromkeys(codes))
    res.failure_code = pick_code(codes)
    res.feasible = bool(res.converged and not codes)
    res.violation = float(sum(viol.values()))
    res.n_flash = flash_count() - f0
    res.runtime_s = time.perf_counter() - t0
    return res
