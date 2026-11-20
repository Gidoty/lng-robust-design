"""Study presets and unit naming. Presets set budgets only; decisions D1 to D11 live in data/design_basis.yaml and are not
overridable from here (S, alpha, chance constraint, UA budget factors are read from the basis)."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

CYCLES = ["smr", "n2_single", "n2_dual"]
VARIANTS = {"cvar_iso": dict(risk="cvar", ua_factor_key="ua_budget_factor"),
            "cvar_125": dict(risk="cvar", ua_factor_key="ua_budget_factor_secondary"),
            "worst_iso": dict(risk="worst", ua_factor_key="ua_budget_factor")}
# model-parameter sensitivity cases: basis overrides (applied to every cycle). Efficiency changes compressor and expander together.
MODEL_CASES = {
    "eff070": dict(efficiency_compressor=0.70, efficiency_expander=0.70),
    "eff080": dict(efficiency_compressor=0.80, efficiency_expander=0.80),
    "cool30": dict(T_cool_C=30.0),
    "cool40": dict(T_cool_C=40.0),
    "mita2": dict(mita_min_K=2.0),
    "mita5": dict(mita_min_K=5.0),
}
ARCHIVE_CASES = {"alpha080": dict(alpha=0.8), "alpha095": dict(alpha=0.95),
                 "pen150": dict(sec_pen=1.5), "pen300": dict(sec_pen=3.0)}
SET_CASES = {"kappa_x0.5": "kappa_x0.5", "kappa_x2": "kappa_x2", "fieldD": "fieldD", "fieldE_secondary": "fieldE_secondary"}
ALL_SENS_CASES = list(MODEL_CASES) + list(ARCHIVE_CASES) + list(SET_CASES)

PRESETS = {
    # probe: tiny, to measure minutes per evaluation on the runner. Its numbers are NOT results.
    "probe": dict(S=6, nominal=dict(pop=8, gen=2), sample=dict(n0=48, rounds=1, batch=24),
                  robust=dict(pop=3, gens=1, inner=dict(max_evals=20, n_restarts=1, maxiter=6), unit_wall_min=40),
                  across=dict(max_evals=30, n_restarts=1, maxiter=8, z0_long_evals=40, z0_nm_evals=30), reversal=dict(n_comp=10, max_evals=20, n_restarts=0),
                  sobol=dict(N=64, oat_points=3), sens=dict(nominal=dict(pop=8, gen=2), k_designs=1, max_evals=20, n_restarts=1),
                  gp_max=300, bootstrap=200),
    "full": dict(S=None, nominal=dict(pop=60, gen=40), sample=dict(n0=2000, rounds=10, batch=800),
                 robust=dict(pop=12, gens=10, inner=dict(max_evals=40, n_restarts=2, maxiter=12), inner_by_cycle={"n2_dual": dict(max_evals=64)}, unit_wall_min=280),
                 across=dict(max_evals=80, n_restarts=3, maxiter=15, z0_long_evals=200, z0_nm_evals=150), reversal=dict(n_comp=300, max_evals=40, n_restarts=2),
                 sobol=dict(N=1024, oat_points=9), sens=dict(nominal=dict(pop=40, gen=25), k_designs=4, max_evals=40, n_restarts=3),
                 gp_max=1500, bootstrap=5000),
}


def get_preset(name: str, overrides: dict | None = None) -> dict:
    p = copy.deepcopy(PRESETS[name])
    for k, v in (overrides or {}).items():
        d = p
        parts = k.split(".")
        for q in parts[:-1]:
            d = d[q]
        d[parts[-1]] = json.loads(v) if isinstance(v, str) else v
    return p


def unit_key(unit: str, cycle: str | None = None, variant: str | None = None, case: str | None = None, stage: int | None = None) -> str:
    k = "-".join(x for x in (unit, cycle, variant, case) if x)
    return f"{k}-s{stage}" if stage else k


@dataclass
class Ctx:
    unit: str
    cycle: str | None
    variant: str | None
    case: str | None
    preset_name: str
    preset: dict
    work: Path                       # root that holds one sub-folder per unit key (inputs and this unit's output)
    workers: int | None = None
    seed: int = 20260101
    stage: int = 1                   # robust units: which chained job this is
    extra: dict = field(default_factory=dict)

    @property
    def key(self):
        return unit_key(self.unit, self.cycle, self.variant, self.case, self.stage if self.unit == "robust" else None)

    @property
    def out(self) -> Path:
        d = self.work / f"unit-{self.key}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def input(self, unit, cycle=None, variant=None, case=None) -> Path:
        return self.work / f"unit-{unit_key(unit, cycle, variant, case)}"

    def robust_dirs(self, cycle, variant) -> list:
        """All stage folders of one robust chain, oldest first."""
        ds = sorted(self.work.glob(f"unit-robust-{cycle}-{variant}-s*"), key=lambda p: int(p.name.rsplit("-s", 1)[1]))
        return ds
