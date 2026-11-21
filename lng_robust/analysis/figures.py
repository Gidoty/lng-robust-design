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


def _fmt_mol(v: float) -> str:
    """Mol % with enough digits to keep neighbouring cell edges distinct (two significant figures, no trailing noise)."""
    if v == 0:
        return "0"
    if abs(v) < 0.01:
        return f"{v:.1e}".replace("e-0", "e-").replace("e+0", "e+")
    return f"{v:.2g}" if abs(v) < 10 else f"{v:.1f}"


def fig7_reversal(cells: pd.DataFrame, out):
    """Ranking-reversal cells on 4 x 4 quantile cells. Columns are labelled by the mean treated N2 of the cell column (range below),
    rows by the mean C2+ of the cell row. The nitrogen-rich cell (largest mean N2) is outlined and annotated."""
    fig, axes = plt.subplots(1, 2, figsize=(7.48, 3.6), sharey=True)
    cyc_ids = {"smr": 0, "n2_single": 1, "n2_dual": 2}
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch, Rectangle
    cmap = ListedColormap([CYCLE_COLOR["smr"], CYCLE_COLOR["n2_single"], CYCLE_COLOR["n2_dual"], "#dddddd", "#ffffff"])
    nx, ny = int(cells.cell_x.max()) + 1, int(cells.cell_y.max()) + 1
    w = cells.n_scenarios
    colx = cells.groupby("cell_x").apply(lambda g: pd.Series(dict(mean=np.average(g.N2_pct_mean, weights=g.n_scenarios), lo=g.N2_pct_min.min(), hi=g.N2_pct_max.max())), include_groups=False)
    rowy = cells.groupby("cell_y").apply(lambda g: pd.Series(dict(mean=np.average(g.C2plus_pct_mean, weights=g.n_scenarios), lo=g.C2plus_pct_min.min(), hi=g.C2plus_pct_max.max())), include_groups=False)
    rich = cells.loc[cells.N2_pct_mean.idxmax()]
    for ax, col, title in zip(axes, ("preferred_nominal", "preferred_robust"), ("Nominal designs", "CVaR designs (iso-UA)")):
        Z = np.full((ny, nx), 4.0)
        for _, r in cells.iterrows():
            Z[int(r.cell_y), int(r.cell_x)] = cyc_ids.get(r[col], 3 if r[col] == "TIE" else 4)
        ax.imshow(Z, origin="lower", cmap=cmap, vmin=0, vmax=4, aspect="auto")
        for k in range(nx + 1):
            ax.axvline(k - 0.5, color="#888888", lw=0.4)
        for k in range(ny + 1):
            ax.axhline(k - 0.5, color="#888888", lw=0.4)
        for _, r in cells.iterrows():
            if r.reversal:
                ax.text(r.cell_x, r.cell_y, "R", ha="center", va="center", fontsize=10, weight="bold", color="w")
            ax.text(r.cell_x, r.cell_y - 0.30, f"N$_2$ {_fmt_mol(r.N2_pct_mean)}\nn={int(r.n_scenarios)}", ha="center", va="center", fontsize=7, linespacing=1.15,
                    color="#222222" if Z[int(r.cell_y), int(r.cell_x)] in (3, 4) else "w")
        ax.add_patch(Rectangle((rich.cell_x - 0.5, rich.cell_y - 0.5), 1, 1, fill=False, ec="k", lw=1.8, zorder=5))
        ax.set_xticks(range(nx))
        ax.set_xticklabels([f"{_fmt_mol(colx.loc[i, 'lo'])} - {_fmt_mol(colx.loc[i, 'hi'])}" for i in range(nx)], fontsize=7, rotation=30, ha="right", rotation_mode="anchor")
        ax.set_title(title, fontsize=8.5, pad=4)
        ax.tick_params(axis="y", labelsize=7)
    axes[0].set_yticks(range(ny))
    axes[0].set_yticklabels([f"{rowy.loc[i, 'mean']:.1f}\n({rowy.loc[i, 'lo']:.1f} to {rowy.loc[i, 'hi']:.1f})" for i in range(ny)], fontsize=7)
    axes[0].set_ylabel("Ethane and heavier: row mean (range), mol %", fontsize=8)
    axes[1].annotate(f"nitrogen-rich cell\n(mean {rich.N2_pct_mean:.1f} mol % N$_2$)", xy=(rich.cell_x + 0.5, rich.cell_y), xycoords="data", xytext=(1.04, 0.12), textcoords="axes fraction",
                     fontsize=7, va="center", arrowprops=dict(arrowstyle="-", lw=0.8, color="k"))
    axes[1].legend(handles=[Patch(color=CYCLE_COLOR[c], label=CYCLE_LABEL[c]) for c in cyc_ids] + [Patch(color="#dddddd", label="Indistinguishable (within 5 %)"), Patch(fc="#ffffff", ec="k", label="No design meets chance constraint")],
                   frameon=False, fontsize=7, loc="upper left", bbox_to_anchor=(1.04, 1.0), title="Preferred cycle", title_fontsize=7)
    fig.subplots_adjust(left=0.12, right=0.70, bottom=0.25, top=0.9, wspace=0.08)
    fig.text(0.41, 0.015, "Nitrogen in treated feed, column range (mol %); cell label: mean N$_2$ (mol %) and number of scenarios", ha="center", fontsize=8)
    return save(fig, out, "Figure_7")


def fig8_surrogate(oof: dict, mita_min: float, out):
    """oof: {cycle: DataFrame from oof_predictions.parquet}. Top row: parity plots; bottom row: false-feasible rate against distance to the MITA limit.
    Each row has its own y label; n= labels at 7 pt."""
    cyc = [c for c in oof]
    fig, axes = plt.subplots(2, len(cyc), figsize=(7.48, 6.2), squeeze=False)
    for j, c in enumerate(cyc):
        d = oof[c]
        f = d[d.feasible & d.sec_gradient_boosting.notna()]
        ax = axes[0][j]
        ax.scatter(f.sec, f.sec_gradient_boosting, s=3, alpha=0.4, color=CYCLE_COLOR[c], linewidths=0)
        lim = [f.sec.min(), f.sec.max()] if len(f) else [0, 1]
        ax.plot(lim, lim, "k-", lw=0.6)
        ax.set_xlabel("Rigorous SEC (kWh kg$^{-1}$)", fontsize=8)
        ax.set_ylabel("Surrogate SEC, withheld anchor (kWh kg$^{-1}$)", fontsize=8)
        ax.text(0.04, 0.95, CYCLE_LABEL[c], transform=ax.transAxes, fontsize=8, va="top")
        ax.tick_params(labelsize=7.5)
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
            top = np.nanmax(rate.values) if np.isfinite(rate.values).any() else 1.0
            for k, (r_, n_) in enumerate(zip(rate.values, cnt.values)):
                ax2.text(k, (0 if np.isnan(r_) else r_) + 0.02 * top, f"n={n_}", ha="center", va="bottom", fontsize=7, rotation=90)
            ax2.set_ylim(0, top * 1.28)
            ax2.set_xticks(range(len(lab))); ax2.set_xticklabels(lab, fontsize=7)
        ax2.set_xlabel("|MITA \u2212 MITA$_{min}$| (K)", fontsize=8)
        ax2.set_ylabel("False-feasible rate (%)", fontsize=8)
        ax2.tick_params(axis="y", labelsize=7.5)
    fig.subplots_adjust(left=0.09, right=0.99, bottom=0.08, top=0.98, wspace=0.42, hspace=0.34)
    return save(fig, out, "Figure_8")


def fig9_sobol(sob: pd.DataFrame, pref: pd.DataFrame, out, top_n: int = 8):
    """One panel per cycle (surrogate Sobol indices of feasible-case SEC), plus one panel for the cycle-preference indices; the top_n largest
    total-order inputs only. 190 mm wide, text 8 pt or larger."""
    cyc = [c for c in ("smr", "n2_single", "n2_dual") if c in set(sob.cycle)]
    npan = len(cyc) + (1 if len(pref) else 0)
    ncol = 2
    nrow = int(np.ceil(npan / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(7.48, 3.1 * nrow), squeeze=False)
    flat = list(axes.ravel())
    for ax, c in zip(flat, cyc):
        d = sob[(sob.cycle == c) & (sob.output == "SEC_surrogate")].sort_values("ST", ascending=False).head(top_n).iloc[::-1]
        y = np.arange(len(d))
        ax.barh(y + 0.2, d.ST, 0.4, color=CYCLE_COLOR[c], label="Total-order")
        ax.barh(y - 0.2, d.S1, 0.4, color="#bbbbbb", label="First-order")
        ax.set_yticks(y); ax.set_yticklabels([v.replace("_", " ") for v in d.variable], fontsize=8)
        ax.set_xlabel("Sobol index for SEC (-)", fontsize=8)
        ax.tick_params(axis="x", labelsize=8)
        ax.text(0.97, 0.05, CYCLE_LABEL[c], transform=ax.transAxes, ha="right", fontsize=8.5, bbox=dict(fc="w", ec="none", pad=1.5))
    if len(pref):
        ax = flat[len(cyc)]
        d = pref[pref.output.str.startswith("SECdiff")]
        piv = d.pivot_table(index="variable", columns="output", values="ST")
        piv = piv.loc[piv.max(axis=1).sort_values(ascending=False).head(top_n).index].iloc[::-1]
        short = {"n2_single": "single N$_2$", "n2_dual": "dual N$_2$", "smr": "SMR"}
        piv.columns = [" minus ".join(short[x] for x in col.replace("SECdiff_", "").split("_minus_")) for col in piv.columns]
        piv.plot.barh(ax=ax, legend=True, fontsize=8, width=0.8, color=["#E69F00", "#CC79A7", "#999999"])
        ax.set_yticklabels([t.get_text().replace("_", " ") for t in ax.get_yticklabels()], fontsize=8)
        ax.legend(fontsize=8, frameon=False, loc="lower right")
        ax.set_xlabel("Total-order Sobol index for cycle preference (-)", fontsize=8)
        ax.set_ylabel("")
    for ax in flat[npan:]:
        ax.set_visible(False)
    flat[0].legend(frameon=False, fontsize=8, loc="lower right", bbox_to_anchor=(1.0, 0.16))
    fig.subplots_adjust(left=0.2, right=0.985, bottom=0.09, top=0.985, wspace=0.62, hspace=0.38)
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
