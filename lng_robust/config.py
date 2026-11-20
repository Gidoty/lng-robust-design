"""Design-basis loader. One YAML file; every value carries a GIVEN / ASSUMPTION / TODO status."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent / "data"
RUNS_DIR = Path(__file__).parent / "runs"
DEFAULT_BASIS = DATA_DIR / "design_basis.yaml"


class Basis:
    def __init__(self, raw: dict):
        self._raw = raw
        self.values = {}
        self.status = {}
        for k, v in raw.items():
            if isinstance(v, dict) and "value" in v:
                self.values[k] = v["value"]
                self.status[k] = v.get("status", "ASSUMPTION")
            else:
                self.values[k] = v
                self.status[k] = (v or {}).get("status", "ASSUMPTION") if isinstance(v, dict) else "ASSUMPTION"

    def __getattr__(self, k):
        try:
            return self.__dict__["values"][k]
        except KeyError as e:
            raise AttributeError(k) from e

    @property
    def T_cool(self): return self.T_cool_C + 273.15
    @property
    def T0(self): return self.T_ambient_C + 273.15
    @property
    def P0(self): return self.P_ambient_bar * 1e5
    @property
    def feed_T(self): return self.feed_T_C + 273.15
    @property
    def feed_P(self): return self.feed_P_bar * 1e5

    def override(self, **kw) -> "Basis":
        raw = copy.deepcopy(self._raw)
        for k, v in kw.items():
            if k not in raw:
                raise KeyError(k)
            raw[k] = {**raw[k], "value": v} if isinstance(raw[k], dict) and "value" in raw[k] else v
        return Basis(raw)

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.values, sort_keys=True, default=str).encode()).hexdigest()[:12]

    def assumptions(self):
        return {k: self.values[k] for k, s in self.status.items() if s in ("ASSUMPTION", "TODO")}


def load_basis(path: str | Path | None = None) -> Basis:
    with open(path or DEFAULT_BASIS) as f:
        return Basis(yaml.safe_load(f))
