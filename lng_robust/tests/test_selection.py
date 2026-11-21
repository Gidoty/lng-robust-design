"""Request 13: the reported design is the best of the re-evaluated candidates by the GA's own rule; request 14: failure-code counts."""
from lng_robust.study.select import failure_code_table, rank_key, select_designs

CH = 0.95


def c(name, pools, cvar, worst, ff):
    return dict(name=name, pools=pools, cvar=cvar, worst=worst, feasible_fraction=ff)


def test_chance_constraint_comes_before_the_objective():
    assert rank_key(1.0, 9.0, CH) < rank_key(0.9, 0.1, CH)                 # feasible beats infeasible whatever the objective
    assert rank_key(0.90, 0.5, CH) < rank_key(0.80, 0.1, CH)               # two infeasible: the smaller violation wins
    assert rank_key(0.96, 0.4, CH) < rank_key(0.99, 0.5, CH)               # two feasible: the lower objective wins


def test_worst_case_design_can_have_the_lower_cvar_so_cvar_is_selected_across_the_pool():
    """The audit case of run 44682889025: a design from the worst-case chain had a lower CVaR than the reported CVaR design."""
    cands = [c("nominal", ["iso", "125"], 2.0, 2.0, 0.86), c("rep_cvar", ["iso", "125"], 0.5047, 0.60, 1.0),
             c("rep_worst", ["iso", "125"], 0.4835, 0.58, 1.0), c("big_ua", ["125"], 0.46, 0.55, 1.0)]
    sel = select_designs(cands, CH)
    assert sel["cvar_iso"]["name"] == "rep_worst"            # lowest CVaR among the iso-UA pool
    assert sel["cvar_125"]["name"] == "big_ua"               # the 1.25 pool admits the larger-UA design, iso does not
    assert sel["worst_iso"]["name"] == "rep_worst"


def test_when_no_candidate_meets_the_chance_constraint_the_least_violating_is_chosen_and_ties_are_deterministic():
    cands = [c("a", ["iso", "125"], 2.0, 2.0, 0.76), c("b", ["iso", "125"], 2.0, 2.0, 0.84), c("c", ["iso", "125"], 2.0, 2.0, 0.84)]
    assert select_designs(cands, CH)["cvar_iso"]["name"] == "b"            # 0.84 beats 0.76; b before c on the name tie-break


def test_nominal_is_selected_when_it_is_the_best_design():
    cands = [c("nominal", ["iso", "125"], 0.40, 0.5, 1.0), c("x", ["iso", "125"], 0.45, 0.55, 1.0)]
    assert select_designs(cands, CH)["cvar_iso"]["name"] == "nominal"


def test_failure_code_counts_split_anchors_and_synthetic_and_skip_feasible():
    rows = [dict(design="d", synthetic=False, feasible=False, fail_code="MITA_VIOLATION"), dict(design="d", synthetic=False, feasible=True, fail_code=""),
            dict(design="d", synthetic=True, feasible=False, fail_code="RATED_FLOW_EXCEEDED"), dict(design="d", synthetic=True, feasible=False, fail_code="RATED_FLOW_EXCEEDED"),
            dict(design="d", synthetic=True, feasible=False, fail_code="")]
    t = failure_code_table(rows)
    assert t == {("d", "anchor", "MITA_VIOLATION"): 1, ("d", "synthetic", "RATED_FLOW_EXCEEDED"): 2, ("d", "synthetic", "UNKNOWN"): 1}
