"""Helpers shared by the study units."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from lng_robust.config import load_basis
from lng_robust.doe.envelope import build_envelope, envelope_definitions
from lng_robust.opt.common import nominal_var_names
from lng_robust.opt.space import STAGE2

M_LNG = 100.0 * 1000.0 / 86400.0          # D1: one capacity, 100 t/d of LNG


def basis_for(ctx, overrides: dict | None = None):
    b = load_basis().override(random_seed=ctx.seed)
    if overrides:
        b = b.override(**overrides)
    return b


def n_scenarios(ctx, basis) -> int:
    return ctx.preset["S"] or basis.n_scenarios_main


def scenario_set(ctx, basis, name="main", S=None):
    """(scenarios, nominal anchor, meta). Deterministic given (basis, S, seed). The probe preset uses a small S."""
    defs = envelope_definitions(basis)
    S = S or n_scenarios(ctx, basis)
    if name in ("main", "fieldD", "fieldE_secondary"):
        scen, nom, meta = build_envelope(name, defs[name], basis, S, basis.random_seed)
    elif name.startswith("kappa_x"):
        scale = float(name[len("kappa_x"):])
        scen, nom, meta = build_envelope(name, defs["main"], basis, S, basis.random_seed, scale)
    else:
        raise KeyError(name)
    return scen, nom, meta


def load_nominal(ctx, cycle):
    return json.loads((ctx.input("nominal", cycle) / "nominal.json").read_text())


def nominal_y0(nom: dict, cycle: str):
    names = nominal_var_names(cycle)
    return np.array([nom["vec"][names.index(n)] for n in STAGE2[cycle]])


def nominal_design_dict(nom: dict):
    """The structure expected by opt.robust.stage1_vec_of_design."""
    return dict(x=nom["x"], ua_spec=nom["ua_spec"], n_ref=nom["n_ref"], vec=nom["vec"])


def write_done(out: Path, **kw):
    (Path(out) / "done.json").write_text(json.dumps(kw, indent=2, default=float))
