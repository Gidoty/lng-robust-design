"""Sobol sensitivity (Saltelli scheme, SALib). Composition enters through additive log-ratio coordinates,
because mole fractions are dependent. `model` is any callable mapping an (n, d) array to (n,) outputs; NaN outputs
(infeasible points) are reported and replaced by the column mean ONLY for the index calculation, with the count logged."""
from __future__ import annotations

import numpy as np
from SALib.analyze import sobol as sobol_analyze
from SALib.sample import sobol as sobol_sample


def alr(z: np.ndarray, ref: int = 0) -> np.ndarray:
    z = np.asarray(z, float)
    return np.log(np.delete(z, ref, axis=-1) / z[..., [ref]])


def alr_inv(y: np.ndarray) -> np.ndarray:
    e = np.exp(np.asarray(y, float))
    denom = 1.0 + e.sum(-1, keepdims=True)
    return np.concatenate([1.0 / denom, e / denom], axis=-1)


def sobol_indices(model, names: list, bounds: list, N: int = 64, seed: int = 1, calc_second_order: bool = False):
    problem = dict(num_vars=len(names), names=names, bounds=bounds)
    X = sobol_sample.sample(problem, N, calc_second_order=calc_second_order, seed=seed)
    Y = np.asarray(model(X), float)
    n_nan = int(np.isnan(Y).sum())
    if n_nan:
        Y = np.where(np.isnan(Y), np.nanmean(Y), Y)
    S = sobol_analyze.analyze(problem, Y, calc_second_order=calc_second_order, print_to_console=False, seed=seed)
    return dict(names=names, S1=S["S1"], ST=S["ST"], S1_conf=S["S1_conf"], ST_conf=S["ST_conf"], n_nan_replaced=n_nan, n_samples=len(Y))
