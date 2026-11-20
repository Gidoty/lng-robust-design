"""Feed register: published anchor compositions and the simulation-ready (treated) versions of them."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field

from lng_robust.config import DATA_DIR
from lng_robust.cycles.pretreat import pretreat

COMP_COLS = ["N2", "CO2", "C1", "C2", "C3", "iC4", "nC4", "C4_total", "iC5", "nC5", "C5_total", "C6"]


@dataclass
class Feed:
    id: str
    facility: str
    source: str
    grade: str
    raw_mol_pct: dict                 # exactly as reported (C4_total / C5_total kept as totals)
    raw_sum: float
    unassigned_pct: float
    synthetic: bool = False
    parent_id: str | None = None
    kappa: float | None = None
    notes: str = ""
    treated: dict = field(default_factory=dict)       # mole fractions after the spec-based pretreatment
    pretreat_notes: list = field(default_factory=list)
    sim_raw: dict = field(default_factory=dict)       # simulation raw composition (mol%, isomers split, renormalised)


def split_isomers(raw: dict, basis) -> dict:
    """Reported totals (C4_total, C5_total) -> iso/normal species using the labelled assumption in the basis."""
    out = {}
    for k in ("N2", "CO2", "C1", "C2", "C3", "C6"):
        if raw.get(k) is not None:
            out[k] = raw[k]
    if raw.get("C4_total") is not None:
        a = basis.c4_iso_fraction
        out["iC4"], out["nC4"] = raw["C4_total"] * a, raw["C4_total"] * (1 - a)
    else:
        for k in ("iC4", "nC4"):
            if raw.get(k) is not None:
                out[k] = raw[k]
    if raw.get("C5_total") is not None:
        a = basis.c5_iso_fraction
        out["iC5"], out["nC5"] = raw["C5_total"] * a, raw["C5_total"] * (1 - a)
    else:
        for k in ("iC5", "nC5"):
            if raw.get(k) is not None:
                out[k] = raw[k]
    return out


def make_sim_feed(raw_mol_pct: dict, basis):
    """Return (sim_raw mol%, treated mole-fraction dict, pretreat notes). Unassigned mass is renormalised away
    only here (for simulation); the reported raw values and their sum are never altered."""
    sim = split_isomers(raw_mol_pct, basis)
    if basis.unassigned_treatment != "renormalise":
        raise NotImplementedError(basis.unassigned_treatment)
    pt = pretreat(sim, basis.pretreat_co2_ppmv, basis.pretreat_c4plus_mol_pct, basis.pretreat_c5plus_mol_pct)
    return sim, pt.treated, pt.notes


def load_feeds(basis, path=None) -> tuple[list[Feed], list[dict]]:
    """Return (entered anchors, TODO rows). TODO rows are never simulated."""
    feeds, todo = [], []
    with open(path or DATA_DIR / "feeds.csv") as f:
        for row in csv.DictReader(f):
            if row["status"].strip().upper() in ("TODO", "UNVERIFIED"):
                todo.append(row)
                continue
            raw = {c: (float(row[c]) if row[c].strip() != "" else None) for c in COMP_COLS}
            known = {k: v for k, v in raw.items() if v is not None and k not in ("iC4", "nC4", "iC5", "nC5") or
                     (v is not None and raw.get("C4_total") is None and k in ("iC4", "nC4")) or
                     (v is not None and raw.get("C5_total") is None and k in ("iC5", "nC5"))}
            s = sum(known.values())
            if abs(s - float(row["sum"])) > 0.005:
                raise ValueError(f"{row['id']}: sum column {row['sum']} != computed {s:.4f}")
            sim, treated, notes = make_sim_feed(raw, basis)
            feeds.append(Feed(id=row["id"], facility=row["facility"], source=row["source"], grade=row["grade"],
                              raw_mol_pct={k: v for k, v in raw.items() if v is not None}, raw_sum=s,
                              unassigned_pct=100.0 - s, notes=row["notes"], treated=treated,
                              pretreat_notes=notes, sim_raw=sim))
    return feeds, todo
