"""Downstream inspect compatibility tests for expanded combo trigger models."""

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.verify.inspect_adapter import run_inspect_algorithms
from test.diagnostics._schema_check import assert_all_diags_match_schema
from test.testings.combo_runtime import parse_machine


pytestmark = pytest.mark.unittest


def _raw_verify_codes(source):
    machine = parse_machine(source)
    results = run_inspect_algorithms(
        machine,
        max_complexity_tier="smt_linear",
        smt_timeout_ms=5000,
    )
    return [
        diagnostic["code"]
        for result in results
        for diagnostic in result.diagnostics
    ]


def test_inspect_verify_smoke_keeps_combo_pseudo_reachable_without_internal_refs():
    """Inspect and verify adapters can consume generated combo pseudo chains."""
    source = """
    def int x = 1;
    state Root {
        state S { during { x = x + 1; } }
        state T;
        [*] -> S;
        S -> T :: E1 + [x > 0] + E2;
        T -> [*];
    }
    """
    report = inspect_model(
        parse_machine(source), enable_verify=True, smt_timeout_ms=200
    )
    payload = report.to_json()

    assert_all_diags_match_schema(report.diagnostics, context="combo-downstream-smoke")
    assert payload["combo_transitions"]
    assert payload["combo_origins"]
    assert all(item["combo_origin_refs"] for item in payload["combo_transitions"])

    combo_state_paths = [
        item["path"] for item in payload["states"] if item["is_pseudo"]
    ]
    assert combo_state_paths
    assert set(combo_state_paths).issubset(set(report.reachability_graph["Root"]))

    origin_ids = {item["origin_id"] for item in payload["combo_origins"]}
    for transition in payload["combo_transitions"]:
        for ref in transition["combo_origin_refs"]:
            assert ref["origin_id"] in origin_ids
            assert ref["term_span"] is not None
            assert ref["transition_span"] is not None


def test_inspect_guard_warning_on_combo_transition_points_to_original_term():
    """Combo guard diagnostics keep refs on the original author-written term."""
    source = """
    def int x = 0;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B :: E1 + [(1 + 2) == 4] + E2;
    }
    """
    report = inspect_model(
        parse_machine(source), enable_verify=True, smt_timeout_ms=200
    )
    assert_all_diags_match_schema(report.diagnostics, context="combo-guard-refs")

    diagnostic = next(
        item for item in report.diagnostics if item.code == "W_COMBO_GUARD_CONST_FALSE"
    )
    assert diagnostic.refs["term_text"] == "[(1 + 2) == 4]"
    assert diagnostic.refs["term_span"] == diagnostic.span
    assert diagnostic.refs["origin_id"] in {
        item.origin_id for item in report.combo_origins
    }


def test_inspect_suppresses_generic_dead_guard_for_combo_const_false():
    """Combo const-false guard reports only the source-level combo warning."""
    source = """
    def int x = 0;
    state Root {
        state S;
        state T;
        [*] -> S;
        S -> T :: E1 + [x > 0 && x < 0] + E2;
    }
    """

    assert "W_DEAD_GUARD" in _raw_verify_codes(source)

    report = inspect_model(
        parse_machine(source),
        enable_verify=True,
        max_complexity_tier="smt_linear",
        smt_timeout_ms=5000,
    )

    codes = {item.code for item in report.diagnostics}
    assert "W_COMBO_GUARD_CONST_FALSE" in codes
    assert "W_DEAD_GUARD" not in codes


def test_inspect_suppresses_generic_guard_tautology_for_combo_const_true():
    """Combo const-true guard reports only the source-level combo warning."""
    source = """
    def int x = 0;
    state Root {
        state S;
        state T;
        [*] -> S;
        S -> T :: E1 + [x >= 0 || x < 0] + E2;
    }
    """

    assert "W_GUARD_TAUTOLOGY" in _raw_verify_codes(source)

    report = inspect_model(
        parse_machine(source),
        enable_verify=True,
        max_complexity_tier="smt_linear",
        smt_timeout_ms=5000,
    )

    codes = {item.code for item in report.diagnostics}
    assert "W_COMBO_GUARD_CONST_TRUE" in codes
    assert "W_GUARD_TAUTOLOGY" not in codes

def test_inspect_keeps_generic_guard_tautology_without_combo_replacement():
    """Inspect keeps raw tautology when combo analyzer has no source-level replacement."""
    source = """
    def int x = 1;
    state Root {
        state S;
        state T;
        [*] -> S;
        S -> T :: E1 + [x / x == 1] + E2;
    }
    """

    assert "W_GUARD_TAUTOLOGY" in _raw_verify_codes(source)

    report = inspect_model(
        parse_machine(source),
        enable_verify=True,
        max_complexity_tier="smt_linear",
        smt_timeout_ms=5000,
    )

    codes = {item.code for item in report.diagnostics}
    assert "W_COMBO_GUARD_CONST_TRUE" not in codes
    assert "W_GUARD_TAUTOLOGY" in codes


def test_inspect_keeps_generic_dead_guard_without_combo_replacement():
    """Inspect keeps raw dead guard when combo analyzer has no replacement."""
    source = """
    def int x = 1;
    state Root {
        state S;
        state T;
        [*] -> S;
        S -> T :: E1 + [x / x != 1] + E2;
    }
    """

    assert "W_DEAD_GUARD" in _raw_verify_codes(source)

    report = inspect_model(
        parse_machine(source),
        enable_verify=True,
        max_complexity_tier="smt_linear",
        smt_timeout_ms=5000,
    )

    codes = {item.code for item in report.diagnostics}
    assert "W_COMBO_GUARD_CONST_FALSE" not in codes
    assert "W_DEAD_GUARD" in codes
