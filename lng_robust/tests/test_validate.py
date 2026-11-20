import copy
import yaml

from lng_robust import validate
from lng_robust.config import DATA_DIR
from lng_robust.tests.conftest import A1_RAW

# TEST FIXTURE ONLY. These inputs are arbitrary numbers used to exercise validate.py. They are NOT a benchmark.
FIXTURE = {
    "fixture_n2_dual": {
        "cycle": "n2_dual", "citation": "TEST FIXTURE (not a published benchmark)",
        "published": {"sec_kwh_per_kg_lng": 1.0},
        "published_basis": {"equation_of_state": "Peng-Robinson", "eta_compressor": 0.75, "eta_expander": 0.75, "mita_K": 3.0},
        "inputs": {"feed_T_C": 30.0, "feed_P_bar": 50.0, "feed_composition": {k: v / 100 for k, v in A1_RAW.items()},
                   "feed_flow_kg_s": 1.2, "product_basis": "after_end_flash", "lng_storage_pressure_bar": 1.2, "T_lng_C": -150.0,
                   "P_high_bar": 60.0, "P_low_bar": 10.0, "n2_flow_kg_s": 0.0, "T_exp_in_warm_C": -30.0, "T_exp_in_cold_C": -100.0,
                   "split": 0.5, "T_cool_C": 35.0, "compressor_pr_max_per_stage": 4.0, "dp_mshe_hp_bar": 1.0, "dp_mshe_lp_bar": 0.3,
                   "dp_cooler_bar": 0.5, "dp_intercooler_bar": 0.3},
    }
}


def test_khan_benchmarks_stay_incomplete_and_are_never_substituted(tmp_path, capsys, basis):
    """Khan et al. 2015 could not be opened, so its inputs stay null. Only those two entries are run here (fast)."""
    raw = yaml.safe_load(open(DATA_DIR / "benchmarks.yaml"))
    f = tmp_path / "khan.yaml"
    f.write_text(yaml.safe_dump({k: v for k, v in raw.items() if k.startswith("khan")}))
    res = validate.run(f, tmp_path, basis)
    assert {r["name"]: r["status"] for r in res} == {"khan2015_n2_single": "INCOMPLETE", "khan2015_n2_dual": "INCOMPLETE"}
    assert "BENCHMARK_INPUTS_INCOMPLETE" in capsys.readouterr().out
    assert "feed_composition" in (tmp_path / "validation_report.md").read_text()
    assert raw["khan2015_n2_single"]["published"]["sec_kwh_per_kg_lng"] == 0.7449
    assert raw["khan2015_n2_dual"]["published"]["sec_kwh_per_kg_lng"] == 0.5007


def test_sourced_benchmarks_cite_documents_and_transcriptions_match_the_thesis():
    raw = yaml.safe_load(open(DATA_DIR / "benchmarks.yaml"))
    for k in ("jensen_skogestad2009_prico", "austbo2015_n2_single_PR", "austbo2015_n2_single_SRK", "austbo2015_n2_dual_SRK"):
        assert raw[k]["source_documents"], k
    j = raw["jensen_skogestad2009_prico"]
    assert j["input_provenance"].startswith("secondary") and j["published"] == {"compressor_power_MW": 77.5, "lng_flow_kg_s": 44.6}
    import pandas as pd
    pr = pd.read_csv(DATA_DIR / "sources/austbo2015_table5_4_PR.csv", comment="#")
    row = pr[(pr.dTmin_K == 2.0) & (pr.eta_s == 0.8)].iloc[0]
    assert (row.T_II_K, row.mR_kg_s, row.pL_bar, row.pH_bar, row.Wnet_kW) == (212.6, 8.9, 11.2, 120, 2714)
    dual = pd.read_csv(DATA_DIR / "sources/austbo2015_table5_9_SRK.csv", comment="#")
    row = dual[(dual.dTmin_K == 2.0) & (dual.eta_s == 0.8)].iloc[0]
    assert (row.T_II_K, row.T_III_K, row.mRa_kg_s, row.mRb_kg_s, row.pL_bar, row.pH_bar, row.Wnet_kW) == (253, 175, 8.3, 2.7, 17.6, 82.9, 1682)
    assert len(pr) == 15 and len(dual) == 15


def test_point_benchmark_runs_one_row_and_reports_deviation(tmp_path, basis):
    """One Austbo point (dTmin 3 K, eta 0.8, PR): the computed power agrees with the published one to a few per cent."""
    import pandas as pd
    raw = yaml.safe_load(open(DATA_DIR / "benchmarks.yaml"))
    spec = copy.deepcopy(raw["austbo2015_n2_single_PR"])
    df = pd.read_csv(DATA_DIR / spec["points_file"], comment="#")
    keep = df[(df.dTmin_K == 3.0) & (df.eta_s == 0.8)]
    f = tmp_path / "one_point.csv"
    f.write_text(keep.to_csv(index=False))
    spec["points_file"] = str(f.relative_to(tmp_path)) if False else None
    import lng_robust.validate as V
    old = V.DATA_DIR
    V.DATA_DIR = tmp_path
    try:
        spec["points_file"] = "one_point.csv"
        r = V.run_benchmark("t", spec, basis)
    finally:
        V.DATA_DIR = old
    assert len(r["rows"]) == 1 and abs(r["rows"][0][3]) < 5.0 and r["status"] == "PASS"


def test_complete_fixture_runs_and_pass_fail_logic(tmp_path, fast_basis):
    spec = copy.deepcopy(FIXTURE["fixture_n2_dual"])
    spec["inputs"]["n2_flow_kg_s"] = 8 * 1.2 * 28.0134 / 16.5      # arbitrary N2 flow
    f = tmp_path / "fixture.yaml"
    f.write_text(yaml.safe_dump({"fixture_n2_dual": spec}))
    r1 = validate.run(f, tmp_path, fast_basis)[0]
    assert r1["status"] in ("PASS", "FAIL") and r1["rows"]
    computed = r1["rows"][0][2]
    spec["published"]["sec_kwh_per_kg_lng"] = computed / 1.03        # 3 % off: PASS only if the case itself is feasible
    f.write_text(yaml.safe_dump({"fixture_n2_dual": spec}))
    r2 = validate.run(f, tmp_path, fast_basis)[0]
    assert abs(r2["rows"][0][3] - 3.0) < 0.01
    spec["published"]["sec_kwh_per_kg_lng"] = computed / 1.20
    f.write_text(yaml.safe_dump({"fixture_n2_dual": spec}))
    assert validate.run(f, tmp_path, fast_basis)[0]["status"] == "FAIL"
