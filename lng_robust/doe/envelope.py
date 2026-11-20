"""Study envelopes (decision D11 option b).

main            six anchors (A5 = Field D excluded), kappa and nominal anchor recomputed from those six, S = 50
fieldD          sensitivity: all seven anchors including Field D (kappa and nominal recomputed from seven), S = 50
fieldE_secondary sensitivity: six anchors with Field E replaced by the secondary-copy C1 and C2 (A6S), S = 50
kappa_x0.5/x2   sensitivity: main anchors and nominal, kappa halved / doubled
Every envelope is deterministic given (basis, S, seed) and is written with its method, so each number is traceable."""
from __future__ import annotations

import json
from pathlib import Path

from lng_robust.config import DATA_DIR
from lng_robust.doe.feeds import Feed, load_feeds
from lng_robust.doe.scenarios import build_scenarios, choose_kappa_robust, choose_nominal, save_scenarios


def main_anchors(anchors: list[Feed], basis) -> list[Feed]:
    ex = set(basis.main_envelope_excluded_anchors)
    return [a for a in anchors if a.id not in ex]


def fieldE_secondary(basis) -> Feed:
    feeds, _ = load_feeds(basis, DATA_DIR / "feeds_sensitivity_fieldE.csv")
    return feeds[0]


def envelope_definitions(basis):
    anchors, todo = load_feeds(basis)
    main = main_anchors(anchors, basis)
    e_sec = fieldE_secondary(basis)
    e_set = [e_sec if a.id == "A6" else a for a in main]
    return {"main": main, "fieldD": anchors, "fieldE_secondary": e_set}


def build_envelope(name: str, anchors: list[Feed], basis, S: int, seed: int, kappa_scale: float = 1.0):
    kappa, info = choose_kappa_robust(anchors)
    kappa *= kappa_scale
    nom, ninfo = choose_nominal(anchors)
    scen = build_scenarios(anchors, S, kappa, seed, basis)
    meta = dict(name=name, kappa=kappa, kappa_scale=kappa_scale, kappa_info=info, nominal=ninfo, S=S, seed=seed,
                n_anchor_scenarios=sum(not f.synthetic for f in scen), n_synthetic_scenarios=sum(f.synthetic for f in scen),
                anchor_ids=[a.id for a in anchors])
    return scen, nom, meta


def write_envelopes(out_dir: Path, basis, S: int = 50, seed: int | None = None):
    seed = basis.random_seed if seed is None else seed
    out_dir.mkdir(parents=True, exist_ok=True)
    defs = envelope_definitions(basis)
    results = {}
    for name, anchors in defs.items():
        scen, nom, meta = build_envelope(name, anchors, basis, S, seed)
        results[name] = (scen, nom, meta)
    for scale in (0.5, 2.0):
        scen, nom, meta = build_envelope(f"kappa_x{scale:g}", defs["main"], basis, S, seed, scale)
        results[meta["name"]] = (scen, nom, meta)
    index = {}
    for name, (scen, nom, meta) in results.items():
        d = out_dir / name
        d.mkdir(exist_ok=True)
        save_scenarios(scen, d / "scenarios.csv")
        (d / "envelope.json").write_text(json.dumps(meta, indent=2))
        index[name] = dict(kappa=meta["kappa"], nominal=meta["nominal"]["nominal"], anchors=meta["anchor_ids"],
                           n_synthetic=meta["n_synthetic_scenarios"])
    (out_dir / "index.json").write_text(json.dumps(index, indent=2))
    return results
