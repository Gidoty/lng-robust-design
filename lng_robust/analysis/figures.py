"""Publication figures. Each function writes <name>.png (600 dpi) and <name>.pdf (vector). Axis labels carry units; no titles inside
the image (captions belong to the manuscript). Colour-blind-safe palette (Okabe-Ito); one colour per cycle in every figure."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

CYCLE_COLOR = {"smr": "#0072B2", "n2_single": "#D55E00", "n2_dual": "#009E73"}
CYCLE_LABEL = {"smr": "SMR", "n2_single": "Single N$_2$ expander", "n2_dual": "Dual N$_2$ expander"}
DESIGN_COLOR = {"nominal": "#555555", "cvar_iso": "#0072B2", "cvar_125": "#56B4E9", "worst_iso": "#CC79A7"}
DESIGN_LABEL = {"nominal": "Nominal", "cvar_iso": "CVaR, iso-UA", "cvar_125": "CVaR, UA x1.25", "worst_iso": "Worst case, iso-UA"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.8,
                     "font.family": "DejaVu Sans", "figure.dpi": 100, "savefig.bbox": "tight"})


def save(fig, out_dir: Path, name: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.png", dpi=600)
    fig.savefig(out_dir / f"{name}.pdf")
    plt.close(fig)
    return [f"{name}.png", f"{name}.pdf"]


def _box(ax, xy, w, h, text, fc="#f2f2f2", fs=6):
    ax.add_patch(FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.015", fc=fc, ec="#333333", lw=0.8))
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=fs)


def _arrow(ax, a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=7, lw=0.8, color="#333333"))


def _line(ax, pts, arrow=True):
    xs, ys = zip(*pts)
    ax.plot(xs[:-1] if arrow else xs, ys[:-1] if arrow else ys, color="#333333", lw=0.8, solid_capstyle="butt")
    if arrow:
        ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=7, lw=0.8, color="#333333", shrinkA=0, shrinkB=0))


def fig1_flowsheets(out):
    """Block flow diagrams: natural gas through the MSHE to the end flash; refrigerant loop compressor train, cooler, MSHE hot side,
    expansion device, MSHE cold side back to the compressor. Schematic only (not to scale)."""
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 3.2))
    exp_dev = {"(a) SMR": ["JT valve"], "(b) Single N$_2$ expander": ["Expander"], "(c) Dual N$_2$ expander": ["Warm\nexpander", "Cold\nexpander"]}
    for ax, (title, dev) in zip(axes, exp_dev.items()):
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.text(0.5, 0.97, title, ha="center", va="top", fontsize=8, weight="bold")
        _box(ax, (0.34, 0.22), 0.16, 0.56, "MSHE", fc="#e8eef6")
        _box(ax, (0.60, 0.76), 0.36, 0.10, "Compressor\ntrain", fs=5.5)
        _box(ax, (0.66, 0.54), 0.24, 0.08, "Cooler", fs=5.5)
        if len(dev) == 1:
            _box(ax, (0.62, 0.20), 0.30, 0.09, dev[0])
        else:
            _box(ax, (0.575, 0.22), 0.18, 0.12, dev[0], fs=5)
            _box(ax, (0.785, 0.22), 0.18, 0.12, dev[1], fs=5)
        _box(ax, (0.03, 0.10), 0.22, 0.09, "End flash", fs=5.5)
        _line(ax, [(0.02, 0.70), (0.34, 0.70)])                                  # natural gas in
        ax.text(0.02, 0.73, "Natural gas", fontsize=6)
        _line(ax, [(0.34, 0.30), (0.13, 0.30), (0.13, 0.19)])                    # cold NG to end flash
        _line(ax, [(0.13, 0.10), (0.13, 0.03)])                                  # LNG out
        ax.text(0.16, 0.04, "LNG", fontsize=6)
        _line(ax, [(0.50, 0.72), (0.77, 0.72), (0.77, 0.76)][:2] + [(0.62, 0.72)][:0] + [(0.62, 0.80)] if False else [(0.50, 0.74), (0.56, 0.74), (0.56, 0.81), (0.62, 0.81)])   # cold side out to compressor
        _line(ax, [(0.78, 0.76), (0.78, 0.62)])                                  # compressor to cooler
        _line(ax, [(0.66, 0.58), (0.58, 0.58), (0.58, 0.54), (0.50, 0.54)])     # cooler to MSHE hot side
        if len(dev) == 1:
            _line(ax, [(0.50, 0.34), (0.58, 0.34), (0.58, 0.245), (0.62, 0.245)])   # HP refrigerant leaves MSHE to expansion
            _line(ax, [(0.77, 0.29), (0.77, 0.40), (0.50, 0.40)])                    # expansion to MSHE cold side
        else:
            _line(ax, [(0.50, 0.34), (0.54, 0.34), (0.54, 0.28), (0.575, 0.28)])
            _line(ax, [(0.665, 0.34), (0.665, 0.44), (0.50, 0.44)])
            _line(ax, [(0.875, 0.34), (0.875, 0.40), (0.50, 0.40)])
        ax.text(1.0, 0.58, "refrigerant", fontsize=5, rotation=90, va="center", ha="right")
    return save(fig, out, "Figure_1")


def fig2_discretisation(df: pd.DataFrame, out):
    fig, ax = plt.subplots(1, 2, figsize=(6.4, 2.6))
    ax[0].semilogx(df.N, df.ua_change_vs_N400_pct, "o-", color="#0072B2")
    ax[0].set_xlabel("Number of enthalpy intervals, N (-)"); ax[0].set_ylabel("Change in UA relative to N = 400 (%)")
    ax[1].semilogx(df.N, df.sec_target_change_vs_N400_pct, "s-", color="#D55E00")
    ax[1].set_xlabel("Number of enthalpy intervals, N (-)"); ax[1].set_ylabel("Change in SEC at fixed MITA (%)")
    return save(fig, out, "Figure_2")


def fig3_envelope(main: pd.DataFrame, fieldD: dict, out):
    """main: columns N2_pct, C2plus_pct, synthetic, id."""
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    s = main[main.synthetic]
    a = main[~main.synthetic]
    ax.scatter(s.N2_pct, s.C2plus_pct, s=10, c="#9aa5b1", label="Synthetic (Dirichlet)", alpha=0.8, linewidths=0)
    ax.scatter(a.N2_pct, a.C2plus_pct, s=34, c="#0072B2", marker="D", label="Measured anchors", edgecolors="k", linewidths=0.5)
    for _, r in a.iterrows():
        ax.annotate(r["id"], (r.N2_pct, r.C2plus_pct), textcoords="offset points", xytext=(4, 3), fontsize=6)
    ax.scatter([fieldD["N2_pct"]], [fieldD["C2plus_pct"]], s=40, c="#D55E00", marker="X", label="Field D (excluded)")
    ax.set_xlabel("Nitrogen in treated feed (mol %)"); ax.set_ylabel("Ethane and heavier in treated feed (mol %)")
    ax.legend(frameon=False, fontsize=6.5)
    return save(fig, out, "Figure_3")


def fig4_pareto(fronts: dict, selected: dict, out):
    fig, ax = plt.subplots(figsize=(3.8, 3.0))
    for c, f in fronts.items():
        if not f:
            continue
        d = pd.DataFrame(f).sort_values("ua_spec")
        ax.plot(d.ua_spec, d.sec, "o-", ms=2.5, lw=0.8, color=CYCLE_COLOR[c], label=CYCLE_LABEL[c])
        if c in selected:
            ax.plot(*selected[c], marker="*", ms=10, color=CYCLE_COLOR[c], mec="k", mew=0.6, ls="none")
    ax.set_xlabel("Specific conductance, UA / m$_{LNG}$ (kW K$^{-1}$ per kg s$^{-1}$)"); ax.set_ylabel("SEC (kWh kg$^{-1}$)")
    ax.legend(frameon=False, fontsize=6.5)
    return save(fig, out, "Figure_4")


def fig5_composites(curves: dict, out):
    cyc = [c for c in curves if curves[c]]
    fig, axes = plt.subplots(1, max(1, len(cyc)), figsize=(2.6 * max(1, len(cyc)), 2.7), squeeze=False)
    for ax, c in zip(axes[0], cyc):
        d = curves[c]
        ax.plot(d["q_kw"], d["T_hot_K"], color="#D55E00", label="Hot composite")
        ax.plot(d["q_kw"], d["T_cold_K"], color="#0072B2", label="Cold composite")
        ax.set_xlabel("Cumulative duty (kW)"); ax.set_ylabel("Temperature (K)")
        ax.text(0.03, 0.93, CYCLE_LABEL[c], transform=ax.transAxes, fontsize=7, va="top")
    axes[0][0].legend(frameon=False, fontsize=6.5, loc="lower right")
    return save(fig, out, "Figure_6" if False else "Figure_5")


def fig6_sec_distribution(across: pd.DataFrame, out):
    cyc = [c for c in ("smr", "n2_single", "n2_dual") if c in set(across.cycle)]
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    rng = np.random.default_rng(0)
    for i, c in enumerate(cyc):
        d = across[(across.cycle == c) & (across.design == "nominal")]
        f = d[d.feasible]
        ax.boxplot([f.sec.values] if len(f) else [[np.nan]], positions=[i], widths=0.5, showfliers=False, medianprops=dict(color="k"),
                   boxprops=dict(color=CYCLE_COLOR[c]), whiskerprops=dict(color=CYCLE_COLOR[c]), capprops=dict(color=CYCLE_COLOR[c]))
        ax.scatter(i + rng.uniform(-0.15, 0.15, len(f)), f.sec, s=8, color=np.where(f.synthetic, "#9aa5b1", CYCLE_COLOR[c]), zorder=3, linewidths=0)
        ax.text(i, ax.get_ylim()[1] if False else 1.02, f"{d.feasible.mean() * 100:.0f} % feasible", transform=ax.get_xaxis_transform(), ha="center", fontsize=7)
    ax.set_xticks(range(len(cyc))); ax.set_xticklabels([CYCLE_LABEL[c] for c in cyc], fontsize=7)
    ax.set_ylabel("SEC of nominal design, operation re-optimised (kWh kg$^{-1}$)")
    return save(fig, out, "Figure_6")


def fig7_reversal(cells: pd.DataFrame, out):
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0), sharey=True)
    cyc_ids = {"smr": 0, "n2_single": 1, "n2_dual": 2}
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap([CYCLE_COLOR["smr"], CYCLE_COLOR["n2_single"], CYCLE_COLOR["n2_dual"], "#dddddd", "#ffffff"])
    nx, ny = int(cells.cell_x.max()) + 1, int(cells.cell_y.max()) + 1
    for ax, col, title in zip(axes, ("preferred_nominal", "preferred_robust"), ("Nominal designs", "CVaR designs (iso-UA)")):
        Z = np.full((ny, nx), 4.0)
        for _, r in cells.iterrows():
            Z[int(r.cell_y), int(r.cell_x)] = cyc_ids.get(r[col], 3 if r[col] == "TIE" else 4)
        ax.imshow(Z, origin="lower", cmap=cmap, vmin=0, vmax=4, aspect="auto")
        for _, r in cells.iterrows():
            if r.reversal:
                ax.text(r.cell_x, r.cell_y, "R", ha="center", va="center", fontsize=9, weight="bold", color="w")
        ax.set_xticks(range(nx)); ax.set_xticklabels([f"{a:.2f}-{b:.2f}" for a, b in zip(cells.groupby("cell_x").N2_pct_min.min(), cells.groupby("cell_x").N2_pct_max.max())], fontsize=5, rotation=30)
        ax.set_xlabel("Nitrogen in treated feed, cell range (mol %)")
        ax.text(0.5, 1.02, title, transform=ax.transAxes, ha="center", fontsize=7)
    axes[0].set_yticks(range(ny)); axes[0].set_yticklabels([f"{a:.1f}-{b:.1f}" for a, b in zip(cells.groupby("cell_y").C2plus_pct_min.min(), cells.groupby("cell_y").C2plus_pct_max.max())], fontsize=5.5)
    axes[0].set_ylabel("Ethane and heavier, cell range (mol %)")
    from matplotlib.patches import Patch
    axes[1].legend(handles=[Patch(color=CYCLE_COLOR[c], label=CYCLE_LABEL[c]) for c in cyc_ids] + [Patch(color="#dddddd", label="Indistinguishable"), Patch(color="#ffffff", ec="k", label="No design meets chance constraint")],
                   frameon=False, fontsize=5.5, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    return save(fig, out, "Figure_7")


def fig8_surrogate(oof: dict, mita_min: float, out):
    """oof: {cycle: DataFrame from oof_predictions.parquet}"""
    cyc = [c for c in oof]
    fig, axes = plt.subplots(2, len(cyc), figsize=(2.4 * len(cyc), 4.4), squeeze=False)
    for j, c in enumerate(cyc):
        d = oof[c]
        f = d[d.feasible & d.sec_gradient_boosting.notna()]
        ax = axes[0][j]
        ax.scatter(f.sec, f.sec_gradient_boosting, s=3, alpha=0.4, color=CYCLE_COLOR[c], linewidths=0)
        lim = [f.sec.min(), f.sec.max()] if len(f) else [0, 1]
        ax.plot(lim, lim, "k-", lw=0.6)
        ax.set_xlabel("Rigorous SEC (kWh kg$^{-1}$)"); ax.set_ylabel("Surrogate SEC, withheld anchor (kWh kg$^{-1}$)" if j == 0 else "")
        ax.text(0.04, 0.93, CYCLE_LABEL[c], transform=ax.transAxes, fontsize=7, va="top")
        g = d[d.mita.notna() & d.feas_gradient_boosting.notna() & ~d.feasible]
        ax2 = axes[1][j]
        if len(g):
            dist = np.abs(g.mita - mita_min)
            bins = [0, 0.5, 1, 2, 4, 8, 1e9]
            lab = ["0-0.5", "0.5-1", "1-2", "2-4", "4-8", ">8"]
            cat = pd.cut(dist, bins, labels=lab, include_lowest=True)
            rate = g.groupby(cat, observed=False).apply(lambda h: 100 * h.feas_gradient_boosting.mean() if len(h) else np.nan, include_groups=False)
            cnt = g.groupby(cat, observed=False).size()
            ax2.bar(range(len(lab)), rate.values, color=CYCLE_COLOR[c])
            for k, (r_, n_) in enumerate(zip(rate.values, cnt.values)):
                ax2.text(k, (0 if np.isnan(r_) else r_) + 0.5, f"n={n_}", ha="center", fontsize=5)
            ax2.set_xticks(range(len(lab))); ax2.set_xticklabels(lab, fontsize=6)
        ax2.set_xlabel("|MITA − MITA$_{min}$| (K)"); ax2.set_ylabel("False-feasible rate (%)" if j == 0 else "")
    return save(fig, out, "Figure_8")


def fig9_sobol(sob: pd.DataFrame, pref: pd.DataFrame, out):
    cyc = [c for c in ("smr", "n2_single", "n2_dual") if c in set(sob.cycle)]
    n = len(cyc) + (1 if len(pref) else 0)
    fig, axes = plt.subplots(1, n, figsize=(2.8 * n, 3.3), squeeze=False)
    for ax, c in zip(axes[0], cyc):
        d = sob[(sob.cycle == c) & (sob.output == "SEC_surrogate")].sort_values("ST", ascending=True)
        y = np.arange(len(d))
        ax.barh(y + 0.2, d.ST, 0.4, color=CYCLE_COLOR[c], label="Total-order")
        ax.barh(y - 0.2, d.S1, 0.4, color="#bbbbbb", label="First-order")
        ax.set_yticks(y); ax.set_yticklabels(d.variable, fontsize=5.5)
        ax.set_xlabel("Sobol index for SEC (-)")
        ax.text(0.97, 0.05, CYCLE_LABEL[c], transform=ax.transAxes, ha="right", fontsize=6.5)
    if len(pref):
        d = pref[pref.output.str.startswith("SECdiff")]
        piv = d.pivot_table(index="variable", columns="output", values="ST")
        piv.plot.barh(ax=axes[0][-1], legend=True, fontsize=5.5, width=0.8)
        axes[0][-1].legend(fontsize=4.5, frameon=False)
        axes[0][-1].set_xlabel("Total-order Sobol index for cycle preference (-)")
        axes[0][-1].set_ylabel("")
    axes[0][0].legend(frameon=False, fontsize=6)
    return save(fig, out, "Figure_9")


def figS1_convergence(h: pd.DataFrame, out):
    """Best objective per generation of every robust chain. Supplementary figure (not one of Figure_1 to Figure_9)."""
    cyc = [c for c in ("smr", "n2_single", "n2_dual") if c in set(h.cycle)]
    fig, axes = plt.subplots(1, len(cyc), figsize=(2.6 * len(cyc), 2.8), squeeze=False)
    for ax, c in zip(axes[0], cyc):
        for v, d in h[h.cycle == c].groupby("variant"):
            d = d.dropna(subset=["best_feasible_objective"]).sort_values("generation")
            ax.plot(d.generation, d.best_feasible_objective, "o-", ms=3, lw=0.9, color=DESIGN_COLOR[v], label=DESIGN_LABEL[v])
        ax.set_xlabel("Generation (-)"); ax.set_ylabel("Best feasible objective (kWh kg$^{-1}$)" if c == cyc[0] else "")
        ax.text(0.97, 0.95, CYCLE_LABEL[c], transform=ax.transAxes, ha="right", va="top", fontsize=6.5)
    axes[0][0].legend(frameon=False, fontsize=5.5)
    return save(fig, out, "Figure_S1")
