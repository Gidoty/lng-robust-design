"""Single mixed refrigerant (PRICO-type) cycle: one compression train, one MSHE, one JT valve.

Decision variables x (dict):
  ref               dict of refrigerant mole fractions (any subset of COMPONENTS)    [first stage]
  P_high_bar        compressor discharge pressure
  P_low_bar         pressure at the JT valve outlet (LP stream entering the MSHE)
  flow_ratio        mol refrigerant per mol feed
  T_lng_C           LNG outlet temperature of the MSHE (the HP refrigerant leaves at the same T)
  ua_installed_kw_per_K   optional installed UA; required UA above it is infeasible          [first stage]
  n_ref_rated_mol_s       optional rated refrigerant flow of the compressor                  [first stage]
"""
from __future__ import annotations

from lng_robust.cycles.common import (BAD_INPUT, Fail, check_constraints, feed_side, finalise, run_cycle,
                                      solve_tear)
from lng_robust.props.eos import reduce_comp
from lng_robust.units.compressor import compress_multistage
from lng_robust.units.mshe import Stream, mshe
from lng_robust.units.valve import valve


def _body(res, feed, feed_T, feed_P, m_lng, x, basis, codes, viol):
    T_lng = x["T_lng_C"] + 273.15
    fs = feed_side(feed, feed_T, feed_P, T_lng, m_lng, basis)
    rmix, zr, _ = reduce_comp(x["ref"])
    P_high, P_low = x["P_high_bar"] * 1e5, x["P_low_bar"] * 1e5
    dp_lp, dp_hp = basis.dp_mshe_lp_bar * 1e5, basis.dp_mshe_hp_bar * 1e5
    dp_ic, dp_ac = basis.dp_intercooler_bar * 1e5, basis.dp_cooler_bar * 1e5
    dp_sc = basis.dp_suction_bar * 1e5
    if P_high < 1.2 * P_low or P_low - dp_lp - dp_sc < 0.3e5 or P_high - dp_ac - dp_hp <= P_low:
        raise Fail(BAD_INPUT, "pressure levels inconsistent", violation=1.0)
    res.n_feed, res.m_feed = fs.n_feed, fs.m_feed
    n_ref = x["flow_ratio"] * fs.n_feed
    res.n_ref = n_ref
    T0 = basis.T0

    def step(T_suc):
        comp = compress_multistage(rmix, zr, T_suc, P_low - dp_lp - dp_sc, P_high, basis.efficiency_compressor,
                                   basis.T_cool, dp_ic, dp_ac, basis.compressor_pr_max_per_stage, T0)
        hp_in = comp.state_out
        hp_out = rmix.flash_TP(T_lng, hp_in.P - dp_hp, zr)
        st_v, D_v = valve(rmix, zr, hp_out, P_low, T0)
        Qh = fs.n_feed * (fs.st_in.H - fs.st_out.H) + n_ref * (hp_in.H - hp_out.H)
        lp_out = rmix.flash_PH(P_low - dp_lp, st_v.H + Qh / n_ref, zr, T_guess=T_suc)
        return lp_out.T, dict(comp=comp, hp_in=hp_in, hp_out=hp_out, st_v=st_v, D_v=D_v, lp_out=lp_out)

    T_suc, its, resid, p = solve_tear(step, feed_T - 10.0, basis.tear_tol, basis.tear_max_iter)
    res.tear_iterations, res.tear_residual = its, resid
    comp, hp_in, hp_out, st_v, lp_out = p["comp"], p["hp_in"], p["hp_out"], p["st_v"], p["lp_out"]
    if lp_out.T - st_v.T < 1e-3:
        raise Fail(BAD_INPUT, "no cold-side temperature rise", violation=1.0)
    streams = [
        Stream("ng", "hot", fs.mix, fs.z, fs.n_feed, feed_T, T_lng, feed_P, fs.st_out.P),
        Stream("hp_ref", "hot", rmix, zr, n_ref, basis.T_cool, T_lng, hp_in.P, hp_out.P),
        Stream("lp_ref", "cold", rmix, zr, n_ref, st_v.T, lp_out.T, P_low, P_low - dp_lp),
    ]
    mr = mshe(streams, N=basis.mshe_N, n_table=basis.mshe_n_table, T0=T0)
    from lng_robust.units.compressor import suction_margin
    sm = min(comp.min_superheat_K, suction_margin(rmix, lp_out))
    check_constraints(res, basis, mr, sm, 0.0, x.get("ua_installed_kw_per_K"), x.get("n_ref_rated_mol_s"), codes, viol)
    D = {"compressors": n_ref * comp.exergy_destruction["compressors"],
         "coolers": n_ref * comp.exergy_destruction["coolers"],
         "jt_valve": n_ref * p["D_v"], "mshe": mr.exergy_destruction,
         "end_flash": fs.n_feed * fs.ef.exergy_destruction}
    res.lng_comp = dict(fs.ef.lng_comp)
    res.end_flash_fraction = fs.ef.mole_frac_gas
    res.lng_mass_frac = fs.ef.mass_frac_liquid
    res.details.update(P_high_bar=x["P_high_bar"], P_low_bar=x["P_low_bar"], T_suction_K=T_suc,
                       n_stages=comp.n_stages, min_superheat_K=sm, mshe_duty_kw=mr.duty_hot / 1e3,
                       pinch_index=mr.pinch_index)
    res._mshe = mr           # kept for plots / convergence study (not serialised)
    finalise(res, fs, n_ref * comp.work, 0.0, D, basis)


def solve_smr(feed, feed_T, feed_P, m_lng, x, basis):
    return run_cycle("smr", _body, feed, feed_T, feed_P, m_lng, x, basis)
