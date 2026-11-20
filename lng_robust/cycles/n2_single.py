"""Single nitrogen expander (reverse Brayton) cycle.

Decision variables x:
  P_high_bar, P_low_bar   compressor discharge pressure; expander outlet pressure
  flow_ratio              mol N2 per mol feed
  T_exp_in_C              expander inlet temperature (the HP N2 leaves the MSHE here)
  T_lng_C                 LNG outlet temperature
  ua_installed_kw_per_K, n_ref_rated_mol_s   optional first-stage equipment limits
"""
from __future__ import annotations

from lng_robust.cycles.common import (BAD_INPUT, LIQUID_AT_EXPANDER, Fail, check_constraints, feed_side, finalise, run_cycle,
                                      solve_tear)
from lng_robust.props.eos import get_mixture
from lng_robust.units.compressor import compress_multistage, suction_margin
from lng_robust.units.expander import expand
from lng_robust.units.mshe import Stream, mshe

N2 = get_mixture
Z = [1.0]


def _body(res, feed, feed_T, feed_P, m_lng, x, basis, codes, viol):
    T_lng = x["T_lng_C"] + 273.15
    T_e = x["T_exp_in_C"] + 273.15
    fs = feed_side(feed, feed_T, feed_P, T_lng, m_lng, basis)
    mix = get_mixture(("N2",))
    P_high, P_low = x["P_high_bar"] * 1e5, x["P_low_bar"] * 1e5
    dp_lp, dp_hp = basis.dp_mshe_lp_bar * 1e5, basis.dp_mshe_hp_bar * 1e5
    dp_ic, dp_ac = basis.dp_intercooler_bar * 1e5, basis.dp_cooler_bar * 1e5
    dp_sc = basis.dp_suction_bar * 1e5
    if P_high < 1.2 * P_low or P_low - dp_lp - dp_sc < 0.3e5 or P_high - dp_ac - dp_hp <= P_low or T_e >= basis.T_cool - 5:
        raise Fail(BAD_INPUT, "pressure levels or expander inlet temperature inconsistent", violation=1.0)
    res.n_feed, res.m_feed = fs.n_feed, fs.m_feed
    n_ref = x["flow_ratio"] * fs.n_feed
    res.n_ref = n_ref
    T0 = basis.T0

    def step(T_suc):
        comp = compress_multistage(mix, Z, T_suc, P_low - dp_lp - dp_sc, P_high, basis.efficiency_compressor,
                                   basis.T_cool, dp_ic, dp_ac, basis.compressor_pr_max_per_stage, T0)
        hp_in = comp.state_out
        hp_out = mix.flash_TP(T_e, hp_in.P - dp_hp, Z)
        ex = expand(mix, Z, hp_out, P_low, basis.efficiency_expander, T0)
        Qh = fs.n_feed * (fs.st_in.H - fs.st_out.H) + n_ref * (hp_in.H - hp_out.H)
        lp_out = mix.flash_PH(P_low - dp_lp, ex.state_out.H + Qh / n_ref, Z, T_guess=T_suc)
        return lp_out.T, dict(comp=comp, hp_in=hp_in, hp_out=hp_out, ex=ex, lp_out=lp_out)

    T_suc, its, resid, p = solve_tear(step, feed_T - 10.0, basis.tear_tol, basis.tear_max_iter)
    res.tear_iterations, res.tear_residual = its, resid
    comp, hp_in, hp_out, ex, lp_out = p["comp"], p["hp_in"], p["hp_out"], p["ex"], p["lp_out"]
    liq_exp = ex.liquid_mass_frac
    if liq_exp > 1e-9:
        # A pure-fluid exhaust inside the two-phase dome has no (T, P) state, so the MSHE table cannot represent it.
        # Treated as infeasible by rule (liquid at expander outlet); see design_basis.yaml max_expander_liquid_mass_frac.
        raise Fail(LIQUID_AT_EXPANDER, f"two-phase expander exhaust, liquid mass fraction {liq_exp:.3f}",
                   violation=0.1 + liq_exp)
    if lp_out.T - ex.state_out.T < 1e-3:
        raise Fail(BAD_INPUT, "no cold-side temperature rise", violation=1.0)
    streams = [
        Stream("ng", "hot", fs.mix, fs.z, fs.n_feed, feed_T, T_lng, feed_P, fs.st_out.P),
        Stream("hp_n2", "hot", mix, Z, n_ref, basis.T_cool, T_e, hp_in.P, hp_out.P),
        Stream("lp_n2", "cold", mix, Z, n_ref, ex.state_out.T, lp_out.T, P_low, P_low - dp_lp),
    ]
    mr = mshe(streams, N=basis.mshe_N, n_table=basis.mshe_n_table, T0=T0)
    sm = min(comp.min_superheat_K, suction_margin(mix, lp_out))
    check_constraints(res, basis, mr, sm, ex.liquid_mass_frac, x.get("ua_installed_kw_per_K"),
                      x.get("n_ref_rated_mol_s"), codes, viol)
    D = {"compressors": n_ref * comp.exergy_destruction["compressors"],
         "coolers": n_ref * comp.exergy_destruction["coolers"],
         "expander": n_ref * ex.exergy_destruction, "mshe": mr.exergy_destruction,
         "end_flash": fs.n_feed * fs.ef.exergy_destruction}
    res.lng_comp = dict(fs.ef.lng_comp)
    res.end_flash_fraction = fs.ef.mole_frac_gas
    res.lng_mass_frac = fs.ef.mass_frac_liquid
    res.details.update(P_high_bar=x["P_high_bar"], P_low_bar=x["P_low_bar"], T_suction_K=T_suc,
                       T_exp_out_K=ex.state_out.T, n_stages=comp.n_stages, min_superheat_K=sm,
                       mshe_duty_kw=mr.duty_hot / 1e3, pinch_index=mr.pinch_index)
    res._mshe = mr
    finalise(res, fs, n_ref * comp.work, n_ref * ex.work, D, basis)


def solve_n2_single(feed, feed_T, feed_P, m_lng, x, basis):
    return run_cycle("n2_single", _body, feed, feed_T, feed_P, m_lng, x, basis)
