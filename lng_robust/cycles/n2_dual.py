"""Dual nitrogen expander cycle: a warm and a cold expander in parallel (flow split).

Topology (CONFIRM against Khan et al. 2015 Fig. before benchmark use): HP N2 leaves the aftercooler,
is cooled in the MSHE to the warm-expander inlet temperature T_exp_in_warm; a fraction `split` is expanded
there to P_low; the rest continues to T_exp_in_cold and is expanded in the cold expander to P_low. Both
exhaust streams are heated in the MSHE and leave together at one temperature.

Decision variables x: P_high_bar, P_low_bar, flow_ratio (mol N2 / mol feed), T_exp_in_warm_C, T_exp_in_cold_C,
split, T_lng_C, optional ua_installed_kw_per_K, n_ref_rated_mol_s.
"""
from __future__ import annotations

from lng_robust.cycles.common import (BAD_INPUT, LIQUID_AT_EXPANDER, Fail, check_constraints, feed_side, finalise, run_cycle,
                                      solve_tear)
from lng_robust.props.eos import get_mixture
from lng_robust.units.compressor import compress_multistage, suction_margin
from lng_robust.units.expander import expand
from lng_robust.units.mshe import Stream, mshe

Z = [1.0]


def _body(res, feed, feed_T, feed_P, m_lng, x, basis, codes, viol):
    T_lng = x["T_lng_C"] + 273.15
    T_w, T_c = x["T_exp_in_warm_C"] + 273.15, x["T_exp_in_cold_C"] + 273.15
    f = x["split"]
    fs = feed_side(feed, feed_T, feed_P, T_lng, m_lng, basis)
    mix = get_mixture(("N2",))
    P_high, P_low = x["P_high_bar"] * 1e5, x["P_low_bar"] * 1e5
    dp_lp, dp_hp = basis.dp_mshe_lp_bar * 1e5, basis.dp_mshe_hp_bar * 1e5
    dp_ic, dp_ac = basis.dp_intercooler_bar * 1e5, basis.dp_cooler_bar * 1e5
    dp_sc = basis.dp_suction_bar * 1e5
    if (P_high < 1.2 * P_low or P_low - dp_lp - dp_sc < 0.3e5 or P_high - dp_ac - dp_hp <= P_low
            or T_w >= basis.T_cool - 5 or T_w < T_c + 1.0 or not (0.01 <= f <= 0.99)):
        raise Fail(BAD_INPUT, "pressure levels / expander temperatures / split inconsistent", violation=1.0)
    res.n_feed, res.m_feed = fs.n_feed, fs.m_feed
    n = x["flow_ratio"] * fs.n_feed
    res.n_ref = n
    T0 = basis.T0
    eta_e = basis.efficiency_expander

    def step(T_suc):
        comp = compress_multistage(mix, Z, T_suc, P_low - dp_lp - dp_sc, P_high, basis.efficiency_compressor,
                                   basis.T_cool, dp_ic, dp_ac, basis.compressor_pr_max_per_stage, T0)
        hp_in = comp.state_out
        P_split = hp_in.P - 0.5 * dp_hp
        s_w = mix.flash_TP(T_w, P_split, Z)
        s_c = mix.flash_TP(T_c, hp_in.P - dp_hp, Z)
        ew = expand(mix, Z, s_w, P_low, eta_e, T0)
        ec = expand(mix, Z, s_c, P_low, eta_e, T0)
        Qh = (fs.n_feed * (fs.st_in.H - fs.st_out.H) + n * (hp_in.H - s_w.H) + (1 - f) * n * (s_w.H - s_c.H))
        H_out = (Qh + (1 - f) * n * ec.state_out.H + f * n * ew.state_out.H) / n
        lp_out = mix.flash_PH(P_low - dp_lp, H_out, Z, T_guess=T_suc)
        return lp_out.T, dict(comp=comp, hp_in=hp_in, s_w=s_w, s_c=s_c, ew=ew, ec=ec, lp_out=lp_out)

    T_suc, its, resid, p = solve_tear(step, feed_T - 10.0, basis.tear_tol, basis.tear_max_iter)
    res.tear_iterations, res.tear_residual = its, resid
    comp, hp_in, s_w, s_c, ew, ec, lp_out = (p[k] for k in ("comp", "hp_in", "s_w", "s_c", "ew", "ec", "lp_out"))
    liq_exp = max(ew.liquid_mass_frac, ec.liquid_mass_frac)
    if liq_exp > 1e-9:
        # A pure-fluid exhaust inside the two-phase dome has no (T, P) state, so the MSHE table cannot represent it.
        # Treated as infeasible by rule (liquid at expander outlet); see design_basis.yaml max_expander_liquid_mass_frac.
        raise Fail(LIQUID_AT_EXPANDER, f"two-phase expander exhaust, liquid mass fraction {liq_exp:.3f}",
                   violation=0.1 + liq_exp)
    if lp_out.T - max(ew.state_out.T, ec.state_out.T) < 1e-3:
        raise Fail(BAD_INPUT, "no cold-side temperature rise", violation=1.0)
    streams = [
        Stream("ng", "hot", fs.mix, fs.z, fs.n_feed, feed_T, T_lng, feed_P, fs.st_out.P),
        Stream("hp_n2_a", "hot", mix, Z, n, basis.T_cool, T_w, hp_in.P, s_w.P),
        Stream("hp_n2_b", "hot", mix, Z, (1 - f) * n, T_w, T_c, s_w.P, s_c.P),
        Stream("lp_n2_cold", "cold", mix, Z, (1 - f) * n, ec.state_out.T, lp_out.T, P_low, P_low - dp_lp),
        Stream("lp_n2_warm", "cold", mix, Z, f * n, ew.state_out.T, lp_out.T, P_low, P_low - dp_lp),
    ]
    mr = mshe(streams, N=basis.mshe_N, n_table=basis.mshe_n_table, T0=T0)
    sm = min(comp.min_superheat_K, suction_margin(mix, lp_out))
    liq = max(ew.liquid_mass_frac, ec.liquid_mass_frac)
    check_constraints(res, basis, mr, sm, liq, x.get("ua_installed_kw_per_K"), x.get("n_ref_rated_mol_s"),
                      codes, viol)
    D = {"compressors": n * comp.exergy_destruction["compressors"],
         "coolers": n * comp.exergy_destruction["coolers"],
         "expanders": n * (f * ew.exergy_destruction + (1 - f) * ec.exergy_destruction),
         "mshe": mr.exergy_destruction, "end_flash": fs.n_feed * fs.ef.exergy_destruction}
    res.lng_comp = dict(fs.ef.lng_comp)
    res.end_flash_fraction = fs.ef.mole_frac_gas
    res.lng_mass_frac = fs.ef.mass_frac_liquid
    res.details.update(P_high_bar=x["P_high_bar"], P_low_bar=x["P_low_bar"], T_suction_K=T_suc,
                       n_stages=comp.n_stages, min_superheat_K=sm, mshe_duty_kw=mr.duty_hot / 1e3,
                       pinch_index=mr.pinch_index)
    res._mshe = mr
    finalise(res, fs, n * comp.work, n * (f * ew.work + (1 - f) * ec.work), D, basis)


def solve_n2_dual(feed, feed_T, feed_P, m_lng, x, basis):
    return run_cycle("n2_dual", _body, feed, feed_T, feed_P, m_lng, x, basis)
