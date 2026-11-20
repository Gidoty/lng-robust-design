"""Phase 3 property checks.
(1) The largest PR-vs-GERG density deviation (42.87 % in gerg_check.csv): is it PR, or the CoolProp two-phase convention?
(2) Volume translation: does a Peneloux-type translation change SEC? One design per cycle, translated vs untranslated PR.
Writes runs/phase3_density_point.csv and runs/phase3_translation.csv."""
from __future__ import annotations

import numpy as np
import pandas as pd
import CoolProp.CoolProp as CP

from lng_robust.config import RUNS_DIR, load_basis
from lng_robust.props.eos import reduce_comp
from lng_robust.props.gerg_check import COOLPROP_NAMES, TEST_COMPOSITIONS, _cp_state


def density_point():
    d = pd.read_csv(RUNS_DIR / "gerg_check.csv")
    d = d[d.status == "OK"].copy()
    worst = d.reindex(d.rho_dev_pct.abs().sort_values(ascending=False).index).head(5)
    rows = []
    for _, r in worst.iterrows():
        comp = TEST_COMPOSITIONS[r.composition]
        mix, z, names = reduce_comp(comp)
        T, P = r.T_C + 273.15, r.P_bar * 1e5
        cp = _cp_state({n: zi for n, zi in zip(names, z)})
        cp.update(CP.PT_INPUTS, P, T)
        rho_bulk = cp.rhomass()
        q = cp.Q() if cp.phase() == CP.iphase_twophase else float("nan")
        rho_l = cp.saturated_liquid_keyed_output(CP.iDmass) if cp.phase() == CP.iphase_twophase else float("nan")
        rho_v = cp.saturated_vapor_keyed_output(CP.iDmass) if cp.phase() == CP.iphase_twophase else float("nan")
        rho_from_phases = float("nan")
        if q == q and 0 < q < 1:
            # CoolProp's Q is a MOLAR quality. Bulk molar volume = q*Vv + (1-q)*Vl with Vk = M_k / rho_k.
            fl = cp.fluid_names()
            M = np.array([CP.PropsSI("M", f) for f in fl])
            yv, xl = np.array(cp.mole_fractions_vapor()), np.array(cp.mole_fractions_liquid())
            Mv, Ml = float(yv @ M), float(xl @ M)
            Mbulk = q * Mv + (1 - q) * Ml
            rho_from_phases = Mbulk / (q * Mv / rho_v + (1 - q) * Ml / rho_l)
        st = mix.flash_TP(T, P, z)
        rows.append(dict(composition=r.composition, T_C=r.T_C, P_bar=r.P_bar, rho_pr=r.rho_pr, rho_gerg_reported=rho_bulk,
                         coolprop_phase=int(cp.phase()), coolprop_molar_quality=q, rho_gerg_liquid_phase=rho_l,
                         rho_gerg_vapour_phase=rho_v, rho_gerg_bulk_from_phases=rho_from_phases,
                         pr_beta_gas=st.beta_gas, pr_rho_dev_vs_reported_pct=r.rho_dev_pct,
                         pr_rho_dev_vs_phase_bulk_pct=100 * (r.rho_pr - rho_from_phases) / rho_from_phases if rho_from_phases == rho_from_phases else float("nan")))
    out = pd.DataFrame(rows)
    out.to_csv(RUNS_DIR / "phase3_density_point.csv", index=False)
    return out


def translation():
    """Compare SEC with PR and with a Peneloux-type (Jhaveri-Youngren) volume translation for one design per cycle."""
    from lng_robust.props import eos as E
    from thermo import CEOSGas, CEOSLiquid
    from thermo.eos_mix import PRMIXTranslated
    R = 8.31446
    E.EOS_CLASSES["PRT"] = PRMIXTranslated
    orig_init = E.Mixture.__init__

    def init(self, names, eos="PR"):
        if eos != "PRT":
            return orig_init(self, names, eos)
        # build like PR but with translation parameters c_i = 0.50033 (R Tc/Pc) (0.25969 - Z_RA), Z_RA = 0.29056 - 0.08775 omega
        from thermo import ChemicalConstantsPackage, FlashPureVLS, FlashVL
        idx = [E.COMPONENTS.index(n) for n in names]
        _, _, kij_full = E._full_constants()
        consts, corr = ChemicalConstantsPackage.from_IDs([E.THERMO_IDS[n] for n in names])
        kij = kij_full[np.ix_(idx, idx)].tolist() if len(idx) > 1 else [[0.0]]
        cs = [0.50033 * (R * Tc / Pc) * (0.25969 - (0.29056 - 0.08775 * w)) for Tc, Pc, w in zip(consts.Tcs, consts.Pcs, consts.omegas)]
        kw = dict(Tcs=consts.Tcs, Pcs=consts.Pcs, omegas=consts.omegas, kijs=kij, cs=cs)
        gas = CEOSGas(PRMIXTranslated, kw, HeatCapacityGases=corr.HeatCapacityGases)
        liq = CEOSLiquid(PRMIXTranslated, kw, HeatCapacityGases=corr.HeatCapacityGases)
        self.names, self.eos_name, self.consts = tuple(names), "PRT", consts
        self.flasher = FlashPureVLS(consts, corr, gas=gas, liquids=[liq], solids=[]) if len(names) == 1 else FlashVL(consts, corr, liquid=liq, gas=gas)
        self.MWs, self.n_flash = list(consts.MWs), 0
        E._REGISTRY.append(self)
    E.Mixture.__init__ = init
    from lng_robust.cycles import solve
    from lng_robust.cycles.pretreat import pretreat
    from lng_robust.analysis.timing import DESIGNS, FEED
    basis = load_basis()
    feed = pretreat(FEED).treated
    m = 100e3 / 86400
    rows = []
    for cyc, x in DESIGNS.items():
        for eos in ("PR", "PRT"):
            with E.use_eos(eos):
                E.EOS_CLASSES.setdefault(eos, PRMIXTranslated)
                r = solve(cyc, feed, basis.feed_T, basis.feed_P, m, x, basis)
            rows.append(dict(cycle=cyc, eos=eos, sec=r.sec, mita=r.mita, ua=r.ua, lng_mass_frac=r.lng_mass_frac, failure_codes=";".join(r.failure_codes)))
    df = pd.DataFrame(rows)
    pv = df.pivot(index="cycle", columns="eos", values=["sec", "mita", "ua"])
    summ = pd.DataFrame({"sec_PR": pv["sec"]["PR"], "sec_PRT": pv["sec"]["PRT"],
                         "sec_change_pct": 100 * (pv["sec"]["PRT"] - pv["sec"]["PR"]) / pv["sec"]["PR"],
                         "mita_change_K": pv["mita"]["PRT"] - pv["mita"]["PR"],
                         "ua_change_pct": 100 * (pv["ua"]["PRT"] - pv["ua"]["PR"]) / pv["ua"]["PR"]}).reset_index()
    summ["note"] = "hand-set reference designs (not optima, not results); translation c_i = 0.50033 (R Tc/Pc)(0.25969 - Z_RA)"
    summ.to_csv(RUNS_DIR / "phase3_translation.csv", index=False)
    return summ


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    print(density_point().round(3).to_string(index=False))
    print(translation().round(4).to_string(index=False))
