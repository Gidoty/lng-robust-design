"""NeqSim (Peng-Robinson) as an independent property engine with the same interface as `eos.Mixture`.

Used only for the cross-check in analysis/neqsim_crosscheck.py. The flowsheet logic is shared with the main code, so this
checks the property and flash implementation, not the flowsheet formulation. NeqSim uses its own binary interaction
parameters, so differences from the thermo-based PR are expected and are reported, not corrected."""
from __future__ import annotations

import math

from neqsim.thermo.thermoTools import PHflash, PSflash, TPflash, fluid

from lng_robust.props.eos import COMPONENTS, FlashError, State

NEQ_NAMES = {"N2": "nitrogen", "CO2": "CO2", "C1": "methane", "C2": "ethane", "C3": "propane", "iC4": "i-butane",
             "nC4": "n-butane", "iC5": "i-pentane", "nC5": "n-pentane", "C6": "n-hexane"}
MW = {"N2": 28.0134, "CO2": 44.0095, "C1": 16.04246, "C2": 30.06904, "C3": 44.09562, "iC4": 58.1222, "nC4": 58.1222,
      "iC5": 72.14878, "nC5": 72.14878, "C6": 86.17536}


class NeqSimMixture:
    eos_name = "NEQSIM_PR"

    def __init__(self, names):
        self.names = tuple(names)
        self.MWs = [MW[n] for n in self.names]
        self.n_flash = 0

    def vec(self, comp):
        if isinstance(comp, dict):
            z = [float(comp.get(n, 0.0)) for n in self.names]
        else:
            z = [float(v) for v in comp]
        s = sum(z)
        return [v / s for v in z]

    def _fluid(self, z, T=None, P=None):
        f = fluid("pr")
        for n, zi in zip(self.names, z):
            f.addComponent(NEQ_NAMES[n], float(zi))
        f.setMixingRule("classic")
        f.setTotalFlowRate(1.0, "mol/sec")
        if T is not None:
            f.setTemperature(float(T))
        if P is not None:
            f.setPressure(float(P) / 1e5)
        return f

    def _state(self, f, z, T, P):
        f.initProperties()
        nph = int(f.getNumberOfPhases())
        gas = f.hasPhaseType("gas")
        liq = f.hasPhaseType("oil") or f.hasPhaseType("liquid")
        if gas and liq and nph >= 2:
            pg, pl = f.getPhase("gas"), f.getPhase("oil") if f.hasPhaseType("oil") else f.getPhase("liquid")
            beta = float(pg.getNumberOfMolesInPhase() / f.getTotalNumberOfMoles())
            y = [float(pg.getComponent(NEQ_NAMES[n]).getx()) for n in self.names]
            x = [float(pl.getComponent(NEQ_NAMES[n]).getx()) for n in self.names]
        elif gas and not liq:
            beta, y, x = 1.0, list(z), None
        else:
            beta, y, x = 0.0, None, list(z)
        mw = sum(zi * m for zi, m in zip(z, self.MWs))
        mwg = sum(a * m for a, m in zip(y, self.MWs)) if y else 0.0
        H = float(f.getEnthalpy())            # J for 1 mol/s total
        S = float(f.getEntropy())             # J/K
        rho = float(f.getDensity("kg/m3"))
        return State(T=float(f.getTemperature()), P=float(f.getPressure()) * 1e5, z=list(z), names=self.names, beta_gas=beta, H=H, S=S,
                     rho_mass=rho, MW=mw, n_phases=2 if (gas and liq and nph >= 2) else 1, mass_frac_gas=beta * mwg / mw, x_liq=x, y_gas=y)

    def flash_TP(self, T, P, z):
        z = self.vec(z)
        self.n_flash += 1
        try:
            f = self._fluid(z, T, P)
            TPflash(f)
            return self._state(f, z, T, P)
        except Exception as e:
            raise FlashError(f"NeqSim TP flash failed: {e}") from e

    def flash_PH(self, P, H, z, T_guess=None):
        z = self.vec(z)
        self.n_flash += 1
        try:
            f = self._fluid(z, T_guess or 200.0, P)
            TPflash(f)
            PHflash(f, float(H), "J")
            return self._state(f, z, f.getTemperature(), P)
        except Exception as e:
            raise FlashError(f"NeqSim PH flash failed: {e}") from e

    def flash_PS(self, P, S, z, T_guess=None):
        z = self.vec(z)
        self.n_flash += 1
        try:
            f = self._fluid(z, T_guess or 200.0, P)
            TPflash(f)
            PSflash(f, float(S), "J/K")
            return self._state(f, z, f.getTemperature(), P)
        except Exception as e:
            raise FlashError(f"NeqSim PS flash failed: {e}") from e

    def _sat(self, P, z, bubble):
        z = self.vec(z)
        try:
            from neqsim.thermo.thermoTools import bubt, dewt
            f = self._fluid(z, 150.0, P)
            (bubt if bubble else dewt)(f)
            return float(f.getTemperature())
        except Exception:
            return float("nan")

    def bubble_T(self, P, z):
        return self._sat(P, z, True)

    def dew_T(self, P, z):
        return self._sat(P, z, False)
