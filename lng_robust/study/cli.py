"""python -m lng_robust.study.cli <unit> [--cycle smr] [--variant cvar_iso] [--case eff070] [--preset full|probe] [--work work] [--stage 1]

Units: nominal, sample, surrogate, robust, across, reversal, sobol, sobol_pref, sens. Inputs are read from sibling unit-<key>/
folders under --work (the workflow downloads the predecessor artifacts there)."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from lng_robust.opt.parallel import shutdown
from lng_robust.study.common import NoNominalDesign, write_done
from lng_robust.study import select, units, units2
from lng_robust.study.config import Ctx, get_preset

UNITS = {"nominal": units.unit_nominal, "sample": units.unit_sample, "surrogate": units.unit_surrogate, "robust": units.unit_robust,
         "across": select.unit_across, "evalcand": select.unit_evalcand, "reversal": units.unit_reversal, "sobol": units2.unit_sobol, "sobol_pref": units2.unit_sobol_pref,
         "sens": units2.unit_sens}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("unit", choices=sorted(UNITS))
    ap.add_argument("--cycle")
    ap.add_argument("--variant")
    ap.add_argument("--case")
    ap.add_argument("--preset", default="full")
    ap.add_argument("--work", default="work")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--seed", type=int, default=20260101)
    ap.add_argument("--set", action="append", default=[], help="override a preset value, e.g. robust.gens=3")
    a = ap.parse_args(argv)
    over = dict(s.split("=", 1) for s in a.set)
    ctx = Ctx(unit=a.unit, cycle=a.cycle, variant=a.variant, case=a.case, preset_name=a.preset, preset=get_preset(a.preset, over),
              work=Path(a.work), workers=a.workers, seed=a.seed, stage=a.stage)
    t0 = time.time()
    print(f"unit {ctx.key}  preset {a.preset}  workers {a.workers}", flush=True)
    try:
        UNITS[a.unit](ctx)
    except NoNominalDesign as e:
        print(f"::warning::{ctx.key}: INCOMPLETE, {e}", flush=True)
        write_done(ctx.out, unit=a.unit, cycle=a.cycle, variant=a.variant, case=a.case, status=f"INCOMPLETE_no_feasible_nominal_design: {e}")
    finally:
        shutdown()
    print(f"unit {ctx.key} finished in {(time.time() - t0) / 60:.1f} min", flush=True)
    done = ctx.out / "done.json"
    if done.exists():
        st = json.loads(done.read_text()).get("status", "")
        if st.startswith("INCOMPLETE"):
            print(f"::warning::{ctx.key}: {st}", flush=True)


if __name__ == "__main__":
    main()
