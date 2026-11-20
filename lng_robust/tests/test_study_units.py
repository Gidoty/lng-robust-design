"""Study plumbing: logging, naming, chunk-and-merge equivalence, workflow structure, package build. Expensive rigorous evaluations are
replaced by deterministic stubs where the test is about plumbing, and used for real in test_scenario_eval_chunking."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from lng_robust.opt.scenario_eval import DesignEval
from lng_robust.study import units
from lng_robust.study.config import Ctx, get_preset, unit_key
from lng_robust.study.store import EvalSink, SinkLog, compact_row, read_parts


def test_unit_keys_and_directories(tmp_path):
    assert unit_key("robust", "smr", "cvar_iso", None, 2) == "robust-smr-cvar_iso-s2"
    ctx = Ctx("robust", "smr", "cvar_iso", None, "probe", get_preset("probe"), tmp_path, stage=2)
    assert ctx.out.name == "unit-robust-smr-cvar_iso-s2" and ctx.out.exists()
    (tmp_path / "unit-robust-smr-cvar_iso-s1").mkdir()
    (tmp_path / "unit-robust-smr-cvar_iso-s10").mkdir()
    assert [d.name for d in ctx.robust_dirs("smr", "cvar_iso")][-1] == "unit-robust-smr-cvar_iso-s10"      # numeric, not lexical, order


def test_preset_override_and_decisions_are_not_in_presets():
    p = get_preset("full", {"robust.gens": "3", "sample.n0": "10"})
    assert p["robust"]["gens"] == 3 and p["sample"]["n0"] == 10
    flat = json.dumps(get_preset("full"))
    for forbidden in ("alpha", "chance", "ua_budget", "cvar_alpha"):
        assert forbidden not in flat          # D1 to D11 are read from design_basis.yaml, never from a preset


def test_parquet_sink_roundtrip_and_resume_numbering(tmp_path, basis):
    from lng_robust.cycles import solve
    r = solve("n2_single", {"C1": 0.95, "C2": 0.05}, basis.feed_T, basis.feed_P, 1.0,
              dict(P_high_bar=60, P_low_bar=10, flow_ratio=8, T_exp_in_C=-60, T_lng_C=-150), basis)
    row = compact_row(r, unit="t", cycle="n2_single", feed_id="X", synthetic=False, purpose="test", x=dict(P_high_bar=60.0, ref={"C1": 0.5}))
    assert row["x_P_high_bar"] == 60.0 and row["x_w_C1"] == 0.5 and "lng_N2_mol_pct" in row and row["status"] in ("feasible", "converged_infeasible", "not_converged")
    s1 = EvalSink(tmp_path, "evals")
    s1.add_rows([row, row])
    s1.close()
    s2 = EvalSink(tmp_path, "evals")                       # a resumed unit appends a new part
    s2.add_rows([row])
    s2.close()
    df = read_parts(tmp_path)
    assert len(df) == 3 and sorted(p.name for p in tmp_path.glob("*.parquet")) == ["evals-00001.parquet", "evals-00002.parquet"]


class _Stub:
    """Deterministic stand-in for the rigorous second stage: SEC is a smooth function of the first-stage vector and the scenario."""
    @staticmethod
    def evaluate_design(cycle, scen, m_lng, x1, basis, *, warm, y_default, kw, unit, member, purpose, sink=None, workers=None, starts=None, serial=False):
        v = np.array([x1["ua_installed_kw_per_K"], x1["n_ref_rated_mol_s"]]) / m_lng
        base = 0.4 + 1e-4 * abs(v[0] - 150.0) + 1e-4 * abs(v[1] - 400.0)
        sec, feas = [], []
        for i, f in enumerate(scen):
            ok = not (v[0] < 100.0 and i % 4 == 0)
            feas.append(ok)
            sec.append(base + 0.01 * (i % 7) if ok else basis.sec_penalty_kwh_per_kg)
        return DesignEval(np.array(sec), np.array(feas), {f.id: [1.0, 2.0] for f in scen}, 10 * len(scen),
                          [dict(sid=f.id, sec=float(s), feasible=bool(k), n_evals=10, min_violation=0.0 if k else 0.5) for f, s, k in zip(scen, sec, feas)])


class _StubSelector:
    def __init__(self, *a, **k):
        pass

    def starts(self, treated, x1, k=3, pool=0, salt=0):
        return [np.zeros(2)] * k


def _fake_inputs(work: Path, cycle="n2_single"):
    nom = dict(cycle=cycle, nominal_anchor="A4", vec=[60.0, 10.0, 8.0, -60.0, -150.0], x=dict(P_high_bar=60.0), ua_spec=150.0, n_ref=400.0 * 100000 / 86400,
               sec=0.5, names=["P_high_bar", "P_low_bar", "flow_ratio", "T_exp_in_C", "T_lng_C"], feasible_found=True)
    d = work / f"unit-nominal-{cycle}"
    d.mkdir(parents=True)
    (d / "nominal.json").write_text(json.dumps(nom))


def _patch(monkeypatch):
    monkeypatch.setattr(units, "evaluate_design", _Stub.evaluate_design)
    monkeypatch.setattr(units, "StartSelector", _StubSelector)
    monkeypatch.setattr(units, "load_models", lambda ctx, cycle: dict(cols=[], regs={"gradient_boosting": None}, clfs={"gradient_boosting": None}))


def _run_robust(work, stage, gens, wall=1000.0):
    p = get_preset("probe")
    p["robust"].update(pop=4, gens=gens, unit_wall_min=wall)
    ctx = Ctx("robust", "n2_single", "cvar_iso", None, "probe", p, work, workers=1, stage=stage)
    return units.unit_robust(ctx)


def test_chunk_and_merge_equals_single_run(tmp_path, monkeypatch):
    """The robust chain run as 1 job with 3 generations equals the chain run as 3 jobs of 1 generation each (resume from checkpoints)."""
    _patch(monkeypatch)
    single, chunked = tmp_path / "single", tmp_path / "chunked"
    for w in (single, chunked):
        _fake_inputs(w)
    f_single = _run_robust(single, 1, gens=3)
    # chunked: stop each job after one generation by giving it a wall-clock budget below the next generation's cost
    _run_robust(chunked, 1, gens=3, wall=0.0)
    _run_robust(chunked, 2, gens=3, wall=0.0)
    f_chunk = _run_robust(chunked, 3, gens=3, wall=0.0)
    f_chunk = _run_robust(chunked, 4, gens=3, wall=1000.0)
    assert f_single["status"] == "complete" and f_chunk["status"] == "complete"
    np.testing.assert_allclose(f_single["vec"], f_chunk["vec"], rtol=0, atol=0)
    assert f_single["objective"] == f_chunk["objective"] and f_single["generation"] == f_chunk["generation"] == 3
    a1 = units.load_archive(Ctx("x", None, None, None, "probe", {}, single), "n2_single", "cvar_iso")
    a2 = units.load_archive(Ctx("x", None, None, None, "probe", {}, chunked), "n2_single", "cvar_iso")
    assert len(a1) == len(a2) == 16 and [round(a["objective"], 12) for a in a1] == [round(a["objective"], 12) for a in a2]
    assert [a["vec"] for a in a1] == [a["vec"] for a in a2]


def test_robust_respects_the_ua_budget_and_chance_constraint(tmp_path, monkeypatch, basis):
    _patch(monkeypatch)
    _fake_inputs(tmp_path)
    f = _run_robust(tmp_path, 1, gens=3)
    assert f["x1"]["ua_installed_kw_per_K"] / (100000 / 86400) <= 150.0 * (1 + 1e-5)       # iso-UA: not above the nominal design's UA
    assert f["chance_met"] and f["ua_factor"] == 1.0


def test_scenario_eval_chunking_matches_single_pass_on_real_cycle(basis):
    """Real rigorous second stage on two scenarios: evaluating them together or one by one gives identical SEC (deterministic solver)."""
    from lng_robust.doe.envelope import build_envelope, envelope_definitions
    from lng_robust.opt.scenario_eval import evaluate_design
    from lng_robust.analysis.inner_benchmark import equipment
    from lng_robust.analysis.golden import _feasible_start
    from lng_robust.opt.space import STAGE2
    anchors = envelope_definitions(basis)["main"]
    scen, nom, _ = build_envelope("main", anchors, basis, 8, basis.random_seed)
    x1, base, _ = equipment("n2_single", nom.treated, basis)
    y0 = np.array([base[n] for n in STAGE2["n2_single"]])
    kw = dict(method="nm", maxfev=6)
    two = scen[:2]
    M = 100000 / 86400
    full = evaluate_design("n2_single", two, M, x1, basis, warm={}, y_default=y0, kw=kw, unit="t", member="m", purpose="t", workers=1, serial=True)
    parts = [evaluate_design("n2_single", [f], M, x1, basis, warm={}, y_default=y0, kw=kw, unit="t", member="m", purpose="t", workers=1, serial=True) for f in two]
    merged_sec = np.concatenate([p.sec for p in parts])
    np.testing.assert_allclose(full.sec, merged_sec, rtol=0, atol=0)
    assert [bool(x) for x in full.feasible] == [bool(x) for p in parts for x in p.feasible]


def test_alr_inverse_roundtrip(basis):
    from lng_robust.doe.envelope import envelope_definitions
    from lng_robust.study.units2 import alr_to_treated
    from lng_robust.surrogate.train import alr_features
    for a in envelope_definitions(basis)["main"]:
        back = alr_to_treated(alr_features(a.treated), a.treated)
        assert abs(sum(back.values()) - 1) < 1e-12
        np.testing.assert_allclose(alr_features(back), alr_features(a.treated), atol=1e-9)


def test_workflow_structure():
    wf = yaml.safe_load((Path(__file__).parents[2] / ".github" / "workflows" / "study.yml").read_text())
    jobs = wf["jobs"]
    assert "workflow_dispatch" in wf[True] if True in wf else "workflow_dispatch" in wf["on"]
    for name, j in jobs.items():
        assert j["timeout-minutes"] <= 330, name
        if "strategy" in j:
            assert j["strategy"]["max-parallel"] == 20 and j["strategy"]["fail-fast"] is False
    assert jobs["robust2"]["needs"] == ["surrogate", "robust1"] and jobs["robust5"]["needs"] == ["surrogate", "robust4"] and jobs["across"]["needs"] == ["robust5"]
    assert len(jobs["robust1"]["strategy"]["matrix"]["variant"]) * len(jobs["robust1"]["strategy"]["matrix"]["cycle"]) == 9
    assert jobs["package"]["if"] and "permissions" in wf and wf["permissions"]["contents"] == "write"
    text = (Path(__file__).parents[2] / ".github" / "workflows" / "study.yml").read_text()
    assert 'python-version: "3.13"' in text and "requirements.lock" in text and "results/${{ github.run_id }}" in text


def test_missing_nominal_design_is_reported_incomplete_not_a_crash(tmp_path):
    from lng_robust.study import cli
    (tmp_path / "unit-nominal-smr").mkdir()
    (tmp_path / "unit-nominal-smr" / "nominal.json").write_text(json.dumps(dict(cycle="smr", feasible_found=False, note="no feasible design")))
    cli.main(["robust", "--cycle", "smr", "--variant", "cvar_iso", "--preset", "probe", "--work", str(tmp_path), "--workers", "1"])
    done = json.loads((tmp_path / "unit-robust-smr-cvar_iso-s1" / "done.json").read_text())
    assert done["status"].startswith("INCOMPLETE_no_feasible_nominal_design")


def test_nominal_seed_vectors_are_inside_bounds_and_follow_the_variable_order(basis):
    from lng_robust.analysis.golden import seed_vectors
    from lng_robust.opt.common import nominal_var_names
    from lng_robust.opt.space import bounds
    for cycle in ("smr", "n2_single", "n2_dual"):
        names = nominal_var_names(cycle)
        lo, hi = bounds(cycle, names, basis)
        S = seed_vectors(cycle, names, basis)
        assert len(S) == 10 and all(((v >= lo - 1e-12) & (v <= hi + 1e-12)).all() for v in S) and len(S[0]) == len(names)
