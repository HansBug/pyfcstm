import pytest

from pyfcstm.verify import REGISTRY


pytestmark = pytest.mark.unittest


GROUP1_TOPOLOGY = (
    "topological_reachable_set",
    "unreachable_states",
    "strongly_connected_components",
    "topological_finite",
    "topological_inevitable_terminator",
    "event_emission_to_consumer_reachable",
)

GROUP2_SMT_LOCAL = (
    "dead_guard",
    "guard_tautology",
    "forced_guard_unsat_under_init",
    "effect_no_op_under_guard",
    "effect_contradicts_guard",
    "transition_shadowed_by_predecessor",
    "enter_postcondition_implies_during_precondition",
)

GROUP3_BMC_PLACEHOLDERS = (
    "bounded_reachability",
    "symbolic_bfs",
    "bounded_safety",
    "bounded_invariant",
    "path_witness",
)

ALL_ALGORITHMS = GROUP1_TOPOLOGY + GROUP2_SMT_LOCAL + GROUP3_BMC_PLACEHOLDERS


def test_registry_contains_exactly_all_pr_a_algorithms_in_stable_order():
    assert tuple(REGISTRY) == ALL_ALGORITHMS
    assert len(REGISTRY) == 18


def test_registry_keys_match_meta_names_and_all_impls_are_placeholders():
    assert not hasattr(REGISTRY, "__setitem__")
    assert len(set(REGISTRY)) == len(REGISTRY)
    for name, meta in REGISTRY.items():
        assert meta.name == name
        assert meta.description
        assert meta.quantifier_alternation_depth == 0
        assert meta.impl is None


def test_group1_topology_metadata_contract():
    for name in GROUP1_TOPOLOGY:
        meta = REGISTRY[name]
        assert meta.closedness == "closed"
        assert meta.complexity_tier == "structural"
        assert meta.smt_logic is None
        assert meta.formula_size_scaling == "none"
        assert meta.fallback_unknown_risk == "none"
        assert meta.recommended_tactic is None
        assert meta.theory_combination == ()
        assert meta.verification_scope == "topological_only"
        assert meta.incremental is False

    assert (
        REGISTRY["event_emission_to_consumer_reachable"].call_count_scaling
        == "linear_in_transitions"
    )
    for name in set(GROUP1_TOPOLOGY) - {"event_emission_to_consumer_reachable"}:
        assert REGISTRY[name].call_count_scaling == "linear_in_states"

    assert REGISTRY["topological_reachable_set"].diagnostic_codes == ()
    assert REGISTRY["unreachable_states"].diagnostic_codes == ("W_UNREACHABLE_STATE",)
    assert REGISTRY["strongly_connected_components"].diagnostic_codes == (
        "I_NONTRIVIAL_SCC",
    )
    assert REGISTRY["topological_finite"].diagnostic_codes == ("W_TOPOLOGICAL_NOEXIT",)
    assert REGISTRY["topological_inevitable_terminator"].diagnostic_codes == (
        "I_TOPOLOGICAL_NON_TERMINATING",
    )
    assert REGISTRY["event_emission_to_consumer_reachable"].diagnostic_codes == (
        "W_EVENT_UNREACHABLE_EMIT",
    )


def test_group2_smt_local_metadata_contract():
    for name in GROUP2_SMT_LOCAL:
        meta = REGISTRY[name]
        assert meta.closedness == "closed"
        assert meta.complexity_tier == "smt_linear"
        assert meta.smt_logic == "QF_LIRA"
        assert meta.formula_size_scaling == "constant"
        assert meta.fallback_unknown_risk in {"low", "medium"}
        assert meta.recommended_tactic == "smt"
        assert meta.theory_combination == ("LIA", "LRA")
        assert meta.verification_scope == "smt_local"

    assert REGISTRY["forced_guard_unsat_under_init"].fallback_unknown_risk == "low"
    assert REGISTRY["transition_shadowed_by_predecessor"].incremental is True
    assert (
        REGISTRY["enter_postcondition_implies_during_precondition"].call_count_scaling
        == "linear_in_leaves"
    )
    for name in set(GROUP2_SMT_LOCAL) - {
        "enter_postcondition_implies_during_precondition"
    }:
        assert REGISTRY[name].call_count_scaling == "linear_in_transitions"

    expected_codes = {
        "dead_guard": ("W_DEAD_GUARD",),
        "guard_tautology": ("W_GUARD_TAUTOLOGY",),
        "forced_guard_unsat_under_init": ("W_FORCED_GUARD_UNSAT",),
        "effect_no_op_under_guard": ("W_EFFECT_SMT_NO_OP",),
        "effect_contradicts_guard": ("I_EFFECT_GUARD_CONTRADICT",),
        "transition_shadowed_by_predecessor": ("W_TRANSITION_SHADOWED",),
        "enter_postcondition_implies_during_precondition": (
            "I_ENTER_DURING_CONTRADICT",
        ),
    }
    for name, codes in expected_codes.items():
        assert REGISTRY[name].diagnostic_codes == codes


def test_group3_bmc_placeholder_metadata_contract():
    for name in GROUP3_BMC_PLACEHOLDERS:
        meta = REGISTRY[name]
        assert meta.closedness == "queried"
        assert meta.complexity_tier == "bmc_search"
        assert meta.smt_logic == "QF_LIRA"
        assert meta.formula_size_scaling == "linear"
        assert meta.incremental is True
        assert meta.recommended_tactic == "smt"
        assert meta.verification_scope == "bmc_unrolled"
        assert meta.diagnostic_codes == ()

    assert REGISTRY["bounded_reachability"].call_count_scaling == "k_unrollings"
    assert REGISTRY["bounded_safety"].call_count_scaling == "k_unrollings"
    assert REGISTRY["symbolic_bfs"].call_count_scaling == "k_unrollings_times_branching"
    assert (
        REGISTRY["bounded_invariant"].call_count_scaling
        == "k_unrollings_times_branching"
    )
    assert REGISTRY["path_witness"].call_count_scaling == "one"
    assert REGISTRY["bounded_invariant"].fallback_unknown_risk == "high"
    for name in set(GROUP3_BMC_PLACEHOLDERS) - {"bounded_invariant"}:
        assert REGISTRY[name].fallback_unknown_risk == "medium"


def test_structural_smt_and_bmc_metadata_are_mutually_consistent():
    for meta in REGISTRY.values():
        if meta.complexity_tier == "structural":
            assert meta.smt_logic is None
            assert meta.verification_scope == "topological_only"
            assert meta.theory_combination == ()
        if meta.complexity_tier == "smt_linear":
            assert meta.closedness == "closed"
            assert meta.smt_logic == "QF_LIRA"
            assert meta.verification_scope == "smt_local"
        if meta.complexity_tier == "bmc_search":
            assert meta.closedness == "queried"
            assert meta.verification_scope == "bmc_unrolled"


def test_verify_package_does_not_import_diagnostics():
    import ast
    import pathlib

    def resolved_import_from(path, node):
        parts = list(path.with_suffix("").parts)
        if path.name == "__init__.py":
            current_module = parts
        else:
            current_module = parts[:-1]
        if node.level:
            prefix = current_module[: len(current_module) - node.level + 1]
            if node.module:
                prefix.extend(node.module.split("."))
            return ".".join(prefix)
        return node.module or ""

    bad = []
    for path in pathlib.Path("pyfcstm/verify").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "pyfcstm.diagnostics" or alias.name.startswith(
                        "pyfcstm.diagnostics."
                    ):
                        bad.append((path, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                module = resolved_import_from(path, node)
                if module == "pyfcstm.diagnostics" or module.startswith(
                    "pyfcstm.diagnostics."
                ):
                    bad.append((path, node.lineno, module))
                if module == "pyfcstm" and any(
                    alias.name == "diagnostics" for alias in node.names
                ):
                    bad.append((path, node.lineno, "from pyfcstm import diagnostics"))
    assert bad == []


def test_pr_a1_does_not_create_later_verify_or_solver_modules():
    import pathlib

    forbidden_paths = (
        "pyfcstm/verify/search.py",
        "pyfcstm/verify/reachability.py",
        "pyfcstm/verify/topology.py",
        "pyfcstm/verify/smt_local.py",
        "pyfcstm/solver/logical.py",
        "pyfcstm/solver/safety.py",
    )
    assert [path for path in forbidden_paths if pathlib.Path(path).exists()] == []
