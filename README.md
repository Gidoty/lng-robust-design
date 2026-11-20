# lng-robust-design

Computational engine for the manuscript *The price of robustness in modular LNG refrigeration: risk-averse design of
single mixed refrigerant and nitrogen expander cycles for variable Niger Delta associated gas* (target journal: Gas Science
and Engineering). This folder is self-contained. It does not import from, or share files with, `backend/`, `frontend/` or
`portfolio/` in the parent repository.

## Research-integrity rules enforced by the code

1. No result is hard-coded or estimated. Every number in an output file is computed here.
2. A benchmark that does not reproduce within 5 % is reported as FAIL with its deviation. Nothing is tuned to force agreement.
3. A missing benchmark input is `null` in `lng_robust/data/benchmarks.yaml`. `validate.py` prints `BENCHMARK_INPUTS_INCOMPLETE` and does not substitute a value.
4. Synthetic compositions carry `synthetic=True` and a parent anchor id in every data file and plot.
5. Every failed evaluation is stored with a failure code. Nothing is dropped.
6. Every value in `lng_robust/data/design_basis.yaml` is marked GIVEN, ASSUMPTION or TODO. ASSUMPTION values are the code author's placeholders and must be confirmed before any number is reported.

## Install

```bash
cd lng-robust-design
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock      # exact pinned versions
pip install -e .
```

## Commands

```bash
python -m pytest -q                                   # unit and integration tests
python -m lng_robust.props.gerg_check                 # PR vs GERG-2008 (CoolProp), writes runs/gerg_check*.csv, runs/methane_density_map.csv
python -m lng_robust.analysis.mshe_convergence        # MSHE discretisation study, writes runs/mshe_convergence.csv
python -m lng_robust.validate                         # benchmark validation, writes runs/validation_report.md
python -m lng_robust.run --quick                      # SMOKE TEST end-to-end pipeline (NOT a result), one folder under runs/
python -m lng_robust.run --full                       # study-scale budgets (not exercised in the first build)
```

`--quick` options: `--cycles smr,n2_single,n2_dual`, `--workers N`, `--capacity-tpd 100`, `--time-budget-min 45`.

## Layout

| Path | Content |
|---|---|
| `props/eos.py` | Peng-Robinson via `thermo`; TP, PH, PS flash with Michelsen stability test; bubble/dew; mass-closure check on every flash |
| `props/gerg_check.py` | PR vs GERG-2008 (CoolProp HEOS) density and enthalpy |
| `units/` | compressor (multistage, intercooled), expander, JT valve, cooler, end-flash, discretised multi-stream heat exchanger `mshe.py` |
| `cycles/` | `smr.py` (PRICO-type), `n2_single.py`, `n2_dual.py`, `pretreat.py` (spec-based), `common.py` (result object, failure codes, exergy bookkeeping) |
| `data/` | `design_basis.yaml`, `benchmarks.yaml`, `kij_table.csv`, `feeds.csv` |
| `doe/` | `feeds.py` (register loader), `dirichlet.py` (synthetic scenarios) |
| `opt/` | `nominal.py` (NSGA-II), `robust.py` (two-stage CVaR), `space.py`, `common.py` (CVaR, PoR), `parallel.py` |
| `surrogate/` | `train.py` (grouped leave-one-composition-out), `classify.py` (FFR), `screen.py` (screening + rigorous re-verification) |
| `analysis/` | `sobol.py`, `plots.py`, `mshe_convergence.py` |
| `runs/` | outputs; one folder per run with `config.json` and git hash |
| `NOVELTY_NOTES.md`, `FEED_LEADS.md` | literature leads for the authors; unverified, not used by the code |
| `STATUS.md` | what works, what fails, what is untested, inputs still needed |

## Run outputs (per run folder)

`config.json`, `evaluations.csv` (every rigorous evaluation with failure code and provenance, manuscript Appendix A),
`design_summary.csv`, `nominal_front_*.csv`, `surrogate_metrics.csv`, `surrogate_vs_rigorous.csv`,
`surrogate_dataset_*.csv`, `failure_code_counts.csv`, `timing.csv`, `feeds_used.csv`, figures. Quick-mode folders end in `_SMOKE`
and every table and figure carries the label `SMOKE TEST - NOT A RESULT`.
