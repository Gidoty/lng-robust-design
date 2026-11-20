"""Spec-based pretreatment: a common treated-feed specification applied to every cycle.

This is a specification, not a unit design. CO2 and water are removed by an idealised unit that has no
energy cost here; heavy hydrocarbons are removed by a component split with no duty calculated.
The manuscript marks the heavy-hydrocarbon removal method (scrub column or cold flash) as an author
decision, so duty_modelled is False and NGL by-product moles are reported.
"""
from __future__ import annotations

from dataclasses import dataclass, field

C4 = ("iC4", "nC4")
C5P = ("iC5", "nC5", "C6")


@dataclass
class PretreatResult:
    treated: dict
    ngl_comp: dict
    ngl_mol_per_mol_feed: float
    co2_removed: bool
    notes: list = field(default_factory=list)
    duty_modelled: bool = False


def _norm(c: dict) -> dict:
    t = sum(c.values())
    return {k: v / t for k, v in c.items()}


def pretreat(raw: dict, co2_ppmv: float = 50.0, c4plus_pct: float = 2.0, c5plus_pct: float = 0.1) -> PretreatResult:
    c = _norm({k: float(v) for k, v in raw.items() if v and v > 0})
    removed = {}                         # mol of each species removed per mol raw feed
    n = 1.0                              # mol gas remaining per mol raw feed
    notes = []
    mol = dict(c)                        # absolute mol per mol raw feed
    co2_removed = False

    def frac(k):
        return mol.get(k, 0.0) / n

    t_co2, t5, t4 = co2_ppmv * 1e-6, c5plus_pct / 100.0, c4plus_pct / 100.0
    eps = 1e-12
    first = {"co2": True, "c5": True, "c4": True}
    for _ in range(50):     # removals change the totals, so iterate until every spec holds together
        changed = False
        y = frac("CO2")
        if y > t_co2 * (1 + eps):       # CO2 to the ppmv limit (acid-gas removal, idealised)
            rem = (mol["CO2"] - t_co2 * n) / (1 - t_co2)
            mol["CO2"] -= rem
            n -= rem
            co2_removed = changed = True
            if first["co2"]:
                notes.append(f"CO2 reduced from {y*1e6:.0f} to {co2_ppmv:.0f} ppmv")
                first["co2"] = False
        s5 = sum(frac(k) for k in C5P)
        if s5 > t5 * (1 + eps):         # C5+ to its limit (proportional removal of C5+ species to NGL)
            r = (s5 - t5) / (s5 * (1 - t5))
            for k in C5P:
                rem = mol.get(k, 0.0) * r
                if rem:
                    mol[k] -= rem
                    removed[k] = removed.get(k, 0.0) + rem
                    n -= rem
            changed = True
            if first["c5"]:
                notes.append(f"C5+ reduced from {s5*100:.3f} to {t5*100:.3f} mol%")
                first["c5"] = False
        s4 = sum(frac(k) for k in C4)
        s5 = sum(frac(k) for k in C5P)
        if s4 + s5 > t4 * (1 + eps) and s4 > 0:     # C4+ to its limit (remove C4 species)
            r = (s4 + s5 - t4) / (s4 * (1 - t4))
            for k in C4:
                rem = mol.get(k, 0.0) * r
                if rem:
                    mol[k] -= rem
                    removed[k] = removed.get(k, 0.0) + rem
                    n -= rem
            changed = True
            if first["c4"]:
                notes.append(f"C4+ reduced from {(s4+s5)*100:.3f} to {t4*100:.3f} mol%")
                first["c4"] = False
        if not changed:
            break
    treated = {k: v / n for k, v in mol.items() if v > 1e-15}
    ngl_total = sum(removed.values())
    ngl = {k: v / ngl_total for k, v in removed.items()} if ngl_total > 0 else {}
    return PretreatResult(treated=treated, ngl_comp=ngl, ngl_mol_per_mol_feed=ngl_total,
                          co2_removed=co2_removed, notes=notes)


def meets_spec(treated: dict, co2_ppmv=50.0, c4plus_pct=2.0, c5plus_pct=0.1, tol=1e-6) -> list:
    """Return a list of violated spec names (empty = in spec)."""
    bad = []
    if treated.get("CO2", 0.0) * 1e6 > co2_ppmv * (1 + tol):
        bad.append("CO2")
    c4p = sum(treated.get(k, 0.0) for k in C4 + C5P) * 100
    c5p = sum(treated.get(k, 0.0) for k in C5P) * 100
    if c4p > c4plus_pct * (1 + tol):
        bad.append("C4+")
    if c5p > c5plus_pct * (1 + tol):
        bad.append("C5+")
    return bad
