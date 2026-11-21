"""Screening-level cost analysis for the manuscript (Section 2.12 / 3.9, Table 8). Moved here unchanged (calculation) from manuscript/analysis/cost_screening.py.

Reads only the results package results/44906558014 (T5, T6, TS_across_per_scenario)
and applies published correlations. No engine re-run. Run:
  python -m lng_robust.analysis.cost_screening <tables dir> [<output dir>]
(lng_robust/study/finalise.py calls run() on the results package.)
Sources:
  Turton et al. (2018), Table A.1: log10 Cp0 = K1 + K2 log10 X + K3 (log10 X)^2, 2001 basis, CEPCI 397.
    centrifugal compressor (X = shaft kW): 2.2897, 1.3604, -0.1027 (450-3000 kW)
    radial gas turbine / expander (X = kW): 2.2476, 1.4965, -0.1618 (100-1500 kW)
    flat-plate heat exchanger (X = m2):    4.6656, -0.1557, 0.1547 (10-1000 m2), proxy for plate-fin
  CEPCI May 2024 (final) = 800.2, Chemical Engineering, September 2024, p. 45.
  Lee et al. (2020): i = 8 %, n = 25 y, availability 95 %.
Assumptions (stated in manuscript): U = 250/500/1000 W m-2 K-1 (illustrative), electricity
0.05/0.10/0.15 USD/kWh (illustrative), units above the correlation range split into equal parallel units,
nominal designs sized at their design point (T5 compressor and expander power); robust designs sized for the
worst of the 50 scenarios, with the N2 compressor/expander split taken from the nominal design at Field C (T5).
Purchased equipment cost only; an installed-cost multiplier f = 1, 3, 5 is applied in the sensitivity.
"""
import math
import sys

import pandas as pd

CEPCI = 800.2 / 397.0   # CEPCI May 2024 final (Chem. Eng., Sept 2024, p. 45) over Turton 2001 basis
K = {'comp': (2.2897, 1.3604, -0.1027, 3000.0), 'exp': (2.2476, 1.4965, -0.1618, 1500.0),
     'hx': (4.6656, -0.1557, 0.1547, 1000.0)}
def pec(kind, X):
    k1, k2, k3, xmax = K[kind]
    n = max(1, math.ceil(X / xmax)); x = X / n
    lx = math.log10(x)
    return n * 10 ** (k1 + k2 * lx + k3 * lx * lx) * CEPCI
i, life, avail = 0.08, 25, 0.95
CRF = i * (1 + i) ** life / ((1 + i) ** life - 1)
mdot = 100e3 / 86400.0                       # kg/s LNG
prod = 100 * 365 * avail                     # t/yr
kw = lambda sec: sec * mdot * 3600.0         # kWh/kg -> kW
def run(D, out_dir=None):
    """Read T5, T6 and TS_across_per_scenario from D; write TS_cost_screening.csv to out_dir (default D); return the DataFrame."""
    out_csv = f'{out_dir or D}/TS_cost_screening.csv'
    t5 = pd.read_csv(f'{D}/T5_nominal_designs.csv').set_index('cycle')
    t6 = pd.read_csv(f'{D}/T6_nominal_cvar_worst_designs.csv')
    ps = pd.read_csv(f'{D}/TS_across_per_scenario.csv')
    rows = []
    for _, r in t6[t6.design.isin(['nominal', 'cvar_iso', 'cvar_125'])].iterrows():
        c, d = r.cycle, r.design
        s = ps[(ps.cycle == c) & (ps.design == d) & (ps.feasible)]
        if d == 'nominal':
            # nominal design sized at its own design point (NSGA-II knee at Field C, T5)
            Pc, Pe = t5.loc[c, 'compressor_kW'], t5.loc[c, 'expander_kW']
            Pnet = Pc - Pe
        elif c == 'smr':
            Pnet = kw(s.sec.max())               # robust design: worst of the 50 scenarios
            Pc, Pe = Pnet, 0.0
        else:
            Pnet = kw(s.sec.max())
            ratio = t5.loc[c, 'compressor_kW'] / (t5.loc[c, 'compressor_kW'] - t5.loc[c, 'expander_kW'])
            Pc, Pe = Pnet * ratio, Pnet * (ratio - 1)
        ua = r.UA_installed_kW_per_K
        for U in (250, 500, 1000):
            A = ua * 1000 / U
            cap = pec('comp', Pc) + (pec('exp', Pe) if Pe > 0 else 0) + pec('hx', A)
            for p in (0.05, 0.10, 0.15):
                e0 = r.SEC_z0_kWh_per_kg * prod * 1000 * p
                em = s.sec.mean() * prod * 1000 * p
                rows.append(dict(cycle=c, design=d, n_feasible=len(s), P_net_inst_kW=Pnet, P_comp_kW=Pc, P_exp_kW=Pe,
                                 UA=ua, U=U, A_m2=A, PEC_comp=pec('comp', Pc), PEC_exp=pec('exp', Pe) if Pe else 0,
                                 PEC_hx=pec('hx', A), PEC_total=cap, price=p,
                                 TAC_z0=CRF * cap + e0, cost_z0_USD_per_t=(CRF * cap + e0) / prod,
                                 TAC_mean=CRF * cap + em, cost_mean_USD_per_t=(CRF * cap + em) / prod,
                                 SEC_z0=r.SEC_z0_kWh_per_kg, SEC_mean_feasible=s.sec.mean()))
    out = pd.DataFrame(rows)
    out.to_csv(out_csv, index=False)
    for f in (1, 3, 5):
        out[f'cost_z0_f{f}'] = (CRF * f * out.PEC_total + out.SEC_z0 * prod * 1000 * out.price) / prod
    out.to_csv(out_csv, index=False)
    print('CRF', round(CRF, 4), 'CEPCI ratio', round(CEPCI, 4), 'prod t/yr', prod)
    pd.set_option('display.width', 250)
    b = out[(out.U == 500) & (out.price == 0.10)]
    print(b[['cycle', 'design', 'n_feasible', 'P_net_inst_kW', 'P_comp_kW', 'P_exp_kW', 'A_m2', 'PEC_comp', 'PEC_exp', 'PEC_hx', 'PEC_total', 'cost_z0_USD_per_t', 'cost_mean_USD_per_t']].round(1).to_string())
    return out


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else '/tmp', sys.argv[2] if len(sys.argv) > 2 else None)
