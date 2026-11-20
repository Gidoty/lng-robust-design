"""Merge validation_points.csv and validation_rounding.csv into runs/validation_summary.md and .csv.

A point is "well resolved" when the printed-input band of the computed power is within 5 % of the published value (the same
tolerance as the acceptance test), so rounding cannot hide a deviation larger than the tolerance. The strict verdict in
validation_report.md is not changed by this summary."""
from __future__ import annotations

import pandas as pd

from lng_robust.config import RUNS_DIR

BAND_TOL = 0.05


def run():
    pts = pd.read_csv(RUNS_DIR / "validation_points.csv")
    rnd = pd.read_csv(RUNS_DIR / "validation_rounding.csv")
    rows = []
    for bm, g in pts.groupby("benchmark"):
        for eos, h in g.groupby("eos"):
            h = h.copy()
            if "dTmin_K" in h and bm in set(rnd.benchmark):
                r = rnd[rnd.benchmark == bm][["dTmin_K", "eta_s", "computed_min_kW", "computed_max_kW", "published_inside_band"]]
                h = h.merge(r, on=["dTmin_K", "eta_s"], how="left")
                h["band_width_rel"] = (h.computed_max_kW - h.computed_min_kW) / h.published_Wnet_kW
                h["well_resolved"] = h.band_width_rel <= BAND_TOL
            else:
                h["well_resolved"] = True
            d = h.deviation_pct
            wr = h[h.well_resolved]
            rows.append(dict(benchmark=bm, eos=eos, n_points=len(h), n_within_5pct=int((d.abs() <= 5).sum()),
                             mean_abs_dev_all=d.abs().mean(), max_abs_dev_all=d.abs().max(),
                             n_well_resolved=len(wr), mean_abs_dev_well_resolved=wr.deviation_pct.abs().mean() if len(wr) else float("nan"),
                             max_abs_dev_well_resolved=wr.deviation_pct.abs().max() if len(wr) else float("nan"),
                             n_outside_5pct_and_well_resolved=int((wr.deviation_pct.abs() > 5).sum())))
    df = pd.DataFrame(rows)
    df.to_csv(RUNS_DIR / "validation_summary.csv", index=False)
    md = ["# Validation summary (informational; the strict verdicts are in validation_report.md)", "",
          f"Well resolved = printed-input band of the computed power within {BAND_TOL:.0%} of the published value.", "",
          df.round(2).to_markdown(index=False) if hasattr(df, "to_markdown") else df.round(2).to_string(index=False)]
    (RUNS_DIR / "validation_summary.md").write_text("\n".join(md))
    return df


if __name__ == "__main__":
    print(run().round(2).to_string(index=False))
