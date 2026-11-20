"""Plots. Quick-mode plots carry a visible SMOKE TEST watermark and the figure title says it is not a result."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SMOKE = "SMOKE TEST - NOT A RESULT"


def _finish(fig, ax, path, smoke, title):
    ax.set_title(f"{title}{'  [' + SMOKE + ']' if smoke else ''}", fontsize=9, color="crimson" if smoke else "black")
    if smoke:
        fig.text(0.5, 0.5, SMOKE, fontsize=26, color="crimson", alpha=0.18, ha="center", va="center", rotation=25)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def envelope(anchors, synthetic, path: Path, smoke: bool):
    fig, ax = plt.subplots(figsize=(5, 4))
    if synthetic:
        ax.scatter([f.treated.get("C1", 0) * 100 for f in synthetic], [(f.treated.get("C2", 0) + f.treated.get("C3", 0)) * 100 for f in synthetic],
                   s=14, c="tab:blue", alpha=0.6, label="synthetic (Dirichlet)")
    ax.scatter([f.treated.get("C1", 0) * 100 for f in anchors], [(f.treated.get("C2", 0) + f.treated.get("C3", 0)) * 100 for f in anchors],
               s=70, marker="*", c="k", label="published anchor")
    ax.set_xlabel("C1 (mol%, treated feed)")
    ax.set_ylabel("C2 + C3 (mol%, treated feed)")
    ax.legend(fontsize=8)
    _finish(fig, ax, path, smoke, "Feed composition envelope")


def pareto(fronts: dict, path: Path, smoke: bool):
    fig, ax = plt.subplots(figsize=(5, 4))
    for cyc, front in fronts.items():
        if front:
            ax.plot([p["ua_spec"] for p in front], [p["sec"] for p in front], "o-", ms=3, label=cyc)
    ax.set_xlabel("UA (kW/K per kg/s LNG)")
    ax.set_ylabel("SEC (kWh/kg LNG)")
    ax.legend(fontsize=8)
    _finish(fig, ax, path, smoke, "Nominal designs: SEC vs UA front")


def sec_distribution(data: dict, path: Path, smoke: bool, sec_pen: float):
    """data[label] = array of SEC_s (penalised values mark infeasible scenarios)."""
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = list(data)
    for i, lab in enumerate(labels):
        v = np.asarray(data[lab], float)
        ax.scatter(np.full(len(v), i) + np.random.default_rng(0).normal(0, 0.05, len(v)), v, s=12, alpha=0.7)
    ax.axhline(sec_pen, ls="--", c="grey", lw=0.8)
    ax.text(0, sec_pen, " SEC_pen (infeasible scenario)", fontsize=7, va="bottom")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("SEC_s (kWh/kg), second stage re-optimised")
    _finish(fig, ax, path, smoke, "Scenario SEC: nominal vs CVaR design")


def parity(oof, models, path: Path, smoke: bool):
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    m = oof["feasible"].values.astype(bool)
    for name in models:
        col = f"sec_{name}"
        if col in oof:
            ok = m & oof[col].notna().values
            ax.scatter(oof["sec"].values[ok], oof[col].values[ok], s=10, alpha=0.6, label=name)
    lim = ax.get_xlim()
    ax.plot(lim, lim, "k--", lw=0.7)
    ax.set_xlabel("rigorous SEC (kWh/kg)")
    ax.set_ylabel("surrogate SEC, withheld composition")
    ax.legend(fontsize=7)
    _finish(fig, ax, path, smoke, "Surrogate parity (leave-one-composition-out)")


def ffr_vs_distance(oof, model, mita_min, path: Path, smoke: bool):
    fig, ax = plt.subplots(figsize=(5, 3.8))
    col = f"feas_{model}"
    d = np.abs(oof["mita"].values - mita_min)
    ok = np.isfinite(d) & oof[col].notna().values
    edges = [0, 0.5, 1, 2, 5, 10, 1e9]
    xs, ys, ns = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = ok & (d >= lo) & (d < hi)
        neg = m & ~oof["feasible"].values.astype(bool)
        if neg.sum() > 0:
            ys.append(float((oof[col].values[neg] == 1).mean()))
            xs.append(f"{lo:g}-{hi:g}" if hi < 1e8 else f">{lo:g}")
            ns.append(int(neg.sum()))
    ax.bar(range(len(ys)), ys)
    for i, n in enumerate(ns):
        ax.text(i, ys[i], f"n={n}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels(xs, fontsize=7)
    ax.set_xlabel("|MITA - MITA_min| (K)")
    ax.set_ylabel("false-feasible rate")
    _finish(fig, ax, path, smoke, f"FFR vs distance from MITA limit ({model})")
