"""Combo inspect provenance and warning contract tests."""

import subprocess
import sys

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine

from ._schema_check import assert_all_diags_match_schema


def _parse(source):
    return parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(source, "state_machine_dsl")
    )


def _slice_by_span(source, span):
    lines = source.split("\n")
    end_line = span.end_line or span.line
    end_column = span.end_column or span.column
    if end_line == span.line:
        return lines[span.line - 1][span.column - 1:end_column - 1]
    pieces = [lines[span.line - 1][span.column - 1:]]
    for index in range(span.line, end_line - 1):
        pieces.append(lines[index])
    pieces.append(lines[end_line - 1][:end_column - 1])
    return "\n".join(pieces)


def _diagnostics_for(source, code):
    report = inspect_model(_parse(source))
    assert_all_diags_match_schema(report.diagnostics, context=code)
    return [item for item in report.diagnostics if item.code == code]


@pytest.mark.unittest
def test_combo_inspect_json_exposes_generated_edge_and_origin_contract():
    source = """
    def int x = 1;
    state Root {
        state A;
        state B;
        state C;
        [*] -> A;
        A -> B :: E1 + [x > 0] + E2;
        A -> C :: E1 + E3;
    }
    """
    report = inspect_model(_parse(source))
    payload = report.to_json()

    assert "combo_transitions" in payload
    assert "combo_origins" in payload
    assert payload["combo_transitions"]
    assert payload["combo_origins"]

    generated = [item for item in payload["transitions"] if item["combo_origin_refs"]]
    assert generated == payload["combo_transitions"]
    first_edge = generated[1]
    assert first_edge["combo_projection_key"] is not None
    assert first_edge["combo_projection_order_key"] is not None
    assert first_edge["combo_reuse_group_id"]
    assert first_edge["combo_priority_run_identity"] is not None
    assert first_edge["combo_priority_run_index"] == 1

    guard_ref = next(
        ref
        for item in generated
        for ref in item["combo_origin_refs"]
        if ref["term_text"] == "[x > 0]"
    )
    assert guard_ref["origin_id"]
    assert guard_ref["term_index"] == 1
    assert guard_ref["role"] == "prefix"
    assert guard_ref["consumes_term"] is True
    assert _slice_by_span(source, _span_obj(guard_ref["term_span"])) == "[x > 0]"
    assert _slice_by_span(source, _span_obj(guard_ref["value_span"])) == "x > 0"

    origin = next(
        item for item in payload["combo_origins"]
        if item["origin_id"] == guard_ref["origin_id"]
    )
    assert [term["term_text"] for term in origin["terms"]] == ["E1", "[x > 0]", "E2"]
    assert _slice_by_span(source, _span_obj(origin["trigger_span"])).strip() == ":: E1 + [x > 0] + E2"


def _span_obj(data):
    from pyfcstm.utils import Span

    return Span(
        line=data["line"],
        column=data["column"],
        end_line=data["end_line"],
        end_column=data["end_column"],
    )


@pytest.mark.unittest
def test_combo_duplicate_event_warning_points_to_second_term_and_first_related_term():
    source = """
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B :: E1 + E1;
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_DUPLICATE_EVENT")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "E1"
    assert diagnostic.refs["term_index"] == 1
    assert diagnostic.refs["first_term_index"] == 0
    assert _slice_by_span(source, diagnostic.refs["term_span"]) == "E1"
    assert _slice_by_span(source, diagnostic.refs["first_term_span"]) == "E1"


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("guard", "code", "expected"),
    [
        ("[(1 + 2) == 3]", "W_COMBO_GUARD_CONST_TRUE", True),
        ("[(1 + 2) == 4]", "W_COMBO_GUARD_CONST_FALSE", False),
    ],
)
def test_combo_guard_const_warning_points_to_original_guard_term(guard, code, expected):
    source = f"""
    state Root {{
        state A;
        state B;
        [*] -> A;
        A -> B :: E1 + {guard} + E2;
    }}
    """
    diagnostics = _diagnostics_for(source, code)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == guard
    assert diagnostic.refs["folded_value"] is expected
    assert _slice_by_span(source, diagnostic.refs["term_span"]) == guard
    assert _slice_by_span(source, diagnostic.refs["value_span"]) == guard[1:-1]


@pytest.mark.unittest
def test_combo_guard_prefix_implied_warning_links_prior_guard_term():
    source = """
    def int x = 1;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : [x > 0] + [x > -1];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_IMPLIED")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[x > -1]"
    assert diagnostic.refs["term_index"] == 1
    assert diagnostic.refs["prior_term_index"] == 0
    assert _slice_by_span(source, diagnostic.refs["term_span"]) == "[x > -1]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x > 0]"


@pytest.mark.unittest
def test_combo_guard_prefix_contradiction_warning_links_prior_guard_term():
    source = """
    def int x = 1;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : [x > 0] + [x < 0];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_CONTRADICTS")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[x < 0]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x > 0]"


@pytest.mark.unittest
def test_combo_guard_prefix_warning_links_decisive_prior_guard_term():
    source = """
    def int x = 1;
    def int y = 1;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : [x > 0] + [y > 0] + [x > -1];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_IMPLIED")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[x > -1]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x > 0]"
    assert diagnostic.refs["prior_term_text"] == "[x > 0]"


@pytest.mark.unittest
def test_combo_guard_prefix_implied_warning_handles_complex_prior_guard():
    source = """
    def int x = 1;
    def int y = 1;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : [x > 0 && y > 0] + [x > 0];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_IMPLIED")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[x > 0]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x > 0 && y > 0]"
    assert diagnostic.refs["prior_term_text"] == "[x > 0 && y > 0]"


@pytest.mark.unittest
def test_combo_guard_prefix_contradiction_warning_handles_complex_prior_guard():
    source = """
    def int x = 1;
    def int y = 1;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : [x > 0 && y > 0] + [x < 0];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_CONTRADICTS")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[x < 0]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x > 0 && y > 0]"
    assert diagnostic.refs["prior_term_text"] == "[x > 0 && y > 0]"


@pytest.mark.unittest
def test_combo_guard_prefix_contradiction_warning_handles_distinct_equalities():
    source = """
    def int x = 0;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : [x == 0] + [x == 1];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_CONTRADICTS")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[x == 1]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x == 0]"
    assert diagnostic.refs["prior_term_text"] == "[x == 0]"


@pytest.mark.unittest
def test_combo_guard_prefix_contradiction_warning_handles_singleton_not_equal():
    source = """
    def int x = 0;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : [x >= 0 && x <= 0] + [x != 0];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_CONTRADICTS")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[x != 0]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x >= 0 && x <= 0]"
    assert diagnostic.refs["prior_term_text"] == "[x >= 0 && x <= 0]"


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("decl", "code"),
    [
        ("def int x = 0;", "W_COMBO_GUARD_PREFIX_CONTRADICTS"),
        ("def float x = 0.0;", "W_COMBO_GUARD_PREFIX_IMPLIED"),
    ],
)
def test_combo_guard_prefix_warning_respects_variable_domain(decl, code):
    source = f"""
    {decl}
    state Root {{
        state A;
        state B;
        [*] -> A;
        A -> B : [x > 0 && x < 1] + [x > 0];
    }}
    """
    diagnostics = _diagnostics_for(source, code)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[x > 0]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x > 0 && x < 1]"


@pytest.mark.unittest
def test_combo_guard_prefix_implied_warning_handles_or_current_guard():
    source = """
    def int x = 1;
    def int y = 1;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : [x > 0] + [x > 0 || y > 0];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_IMPLIED")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[x > 0 || y > 0]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x > 0]"
    assert diagnostic.refs["prior_term_text"] == "[x > 0]"


@pytest.mark.unittest
def test_combo_guard_prefix_contradiction_warning_handles_not_current_guard():
    source = """
    def int x = 1;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : [x > 0] + [not (x > 0)];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_CONTRADICTS")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert _slice_by_span(source, diagnostic.span) == "[not (x > 0)]"
    assert _slice_by_span(source, diagnostic.refs["prior_term_span"]) == "[x > 0]"
    assert diagnostic.refs["prior_term_text"] == "[x > 0]"


@pytest.mark.unittest
def test_combo_guard_prefix_warning_suppressed_by_relevant_source_exit_write():
    source = """
    def int x = 1;
    state Root {
        state A { exit { x = -1; } }
        state B;
        [*] -> A;
        A -> B : [x > 0] + E1 + [x > -1];
    }
    """
    diagnostics = inspect_model(_parse(source)).diagnostics

    assert not any(item.code == "W_COMBO_GUARD_PREFIX_IMPLIED" for item in diagnostics)
    assert_all_diags_match_schema(diagnostics, context="combo-side-effect-suppressed")


@pytest.mark.unittest
def test_combo_guard_prefix_warning_suppressed_by_event_before_guard_source_exit_write():
    source = """
    def int x = 1;
    state Root {
        state A { exit { x = -1; } }
        state B;
        [*] -> A;
        A -> B :: E1 + [x > 0] + [x > -1];
    }
    """
    diagnostics = inspect_model(_parse(source)).diagnostics

    assert not any(item.code == "W_COMBO_GUARD_PREFIX_IMPLIED" for item in diagnostics)
    assert_all_diags_match_schema(
        diagnostics,
        context="combo-event-before-guard-side-effect-suppressed",
    )


@pytest.mark.unittest
def test_combo_guard_prefix_warning_not_suppressed_by_unrelated_source_exit_write():
    source = """
    def int x = 1;
    def int y = 0;
    state Root {
        state A { exit { y = y + 1; } }
        state B;
        [*] -> A;
        A -> B : [x > 0] + E1 + [x > -1];
    }
    """
    diagnostics = _diagnostics_for(source, "W_COMBO_GUARD_PREFIX_IMPLIED")

    assert len(diagnostics) == 1


@pytest.mark.unittest
def test_entry_combo_guard_prefix_warning_suppressed_by_owner_during_before_write():
    source = """
    def int x = 1;
    state Root {
        during before { x = 0; }
        state A;
        [*] -> A : [x > 0] + E1 + [x > -1];
    }
    """
    diagnostics = inspect_model(_parse(source)).diagnostics

    assert not any(item.code == "W_COMBO_GUARD_PREFIX_IMPLIED" for item in diagnostics)
    assert_all_diags_match_schema(diagnostics, context="combo-entry-during-before")


@pytest.mark.unittest
def test_entry_combo_guard_prefix_warning_suppressed_by_event_before_guard_owner_during_before_write():
    source = """
    def int x = 1;
    state Root {
        during before { x = 0; }
        state A;
        [*] -> A : E1 + [x > 0] + [x > -1];
    }
    """
    diagnostics = inspect_model(_parse(source)).diagnostics

    assert not any(item.code == "W_COMBO_GUARD_PREFIX_IMPLIED" for item in diagnostics)
    assert_all_diags_match_schema(
        diagnostics,
        context="combo-entry-event-before-guard-during-before",
    )


@pytest.mark.unittest
def test_combo_analyzer_does_not_break_model_first_import_order():
    script = "import pyfcstm.model; from pyfcstm.model import StateMachine; print(StateMachine.__name__)"
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "StateMachine"
