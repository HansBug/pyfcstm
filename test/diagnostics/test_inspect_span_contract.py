"""Contract tests for inspect diagnostics source spans."""

from collections import defaultdict

import pytest

from pyfcstm.diagnostics import CODE_REGISTRY, VariableInfo, inspect_model
from pyfcstm.diagnostics.analyzers.data_flow import collect_data_flow_warnings
import pyfcstm.diagnostics.inspect as inspect_module
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils.validate import Span


def _parse(source):
    ast = parse_with_grammar_entry(source, "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast)


def _diagnostics_for_code(code, spec):
    if code == "W_WRITE_ONLY_VAR":
        source = spec.example_dsl
        variable = next(
            v for v in inspect_model(_parse(source)).variables if v.name == "counter"
        )
        diagnostics = collect_data_flow_warnings(
            [
                VariableInfo(
                    name=variable.name,
                    type=variable.type,
                    init_value=variable.init_value,
                    read_in_states=tuple(),
                    written_in_states=variable.written_in_states,
                    read_in_guards=tuple(),
                    written_in_effects=tuple(),
                    affects_guard_directly=True,
                    affects_guard_indirectly=False,
                    abstract_actions_in_scope=tuple(),
                    span=variable.span,
                ),
            ]
        )
        return source, diagnostics
    source = spec.example_dsl
    report = inspect_model(
        _parse(source),
        deep_hierarchy_threshold=0,
        large_composite_threshold=2,
        var_to_leaf_ratio_threshold=0,
    )
    return source, report.diagnostics


def _slice_by_span(source: str, span: Span) -> str:
    """Return the source slice covered by a 1-based listener span."""
    assert span is not None
    lines = source.split("\n")
    end_line = span.end_line or span.line
    end_column = span.end_column or span.column
    assert 1 <= span.line <= len(lines)
    assert 1 <= end_line <= len(lines)
    assert span.line <= end_line
    assert span.column >= 1
    assert end_column >= 1
    if end_line == span.line:
        assert span.column <= end_column
        return lines[span.line - 1][span.column - 1 : end_column - 1]
    pieces = [lines[span.line - 1][span.column - 1 :]]
    for index in range(span.line, end_line - 1):
        pieces.append(lines[index])
    pieces.append(lines[end_line - 1][: end_column - 1])
    return "\n".join(pieces)


@pytest.mark.unittest
def test_known_spanless_codes_are_registered_codes():
    assert inspect_module.KNOWN_SPANLESS_CODES <= set(CODE_REGISTRY)


@pytest.mark.unittest
def test_registry_static_warning_info_examples_have_source_spans():
    codes_seen = defaultdict(int)
    spanless_hits = defaultdict(int)
    for code, spec in CODE_REGISTRY.items():
        if spec.emit_tier != "static_pipeline" or spec.severity not in {
            "warning",
            "info",
        }:
            continue
        example_dsl = spec.example_dsl
        assert example_dsl, (
            f"{code} must provide an example_dsl for span contract coverage"
        )
        example_dsl, diagnostics = _diagnostics_for_code(code, spec)
        matching = [diag for diag in diagnostics if diag.code == code]
        assert matching, (
            f"{code} example_dsl did not emit its code; emitted "
            f"{[diag.code for diag in diagnostics]}"
        )
        for diag in matching:
            codes_seen[code] += 1
            if code in inspect_module.KNOWN_SPANLESS_CODES:
                if diag.span is None:
                    spanless_hits[code] += 1
                continue
            assert diag.span is not None, (code, diag.refs)
            assert _slice_by_span(example_dsl, diag.span).strip(), (
                code,
                diag.refs,
                diag.span,
            )

    expected = {
        code
        for code, spec in CODE_REGISTRY.items()
        if spec.emit_tier == "static_pipeline" and spec.severity in {"warning", "info"}
    }
    assert set(codes_seen) == expected
    assert set(spanless_hits) == inspect_module.KNOWN_SPANLESS_CODES


@pytest.mark.unittest
def test_all_static_inspect_diagnostics_have_source_spans():
    source = """def int counter = 0;
def int read_only = 0;
def int stable = 0;
def int assigned = 3.5;
def int extra = 0;
def int a = 0;
def int b = 0;
def int c = 0;
def int d = 0;
def int e = 0;
def int f = 0;

state Root {
    event Tick;
    event Unused;
    enter Sync { }

    state Active {
        enter Sync { }
        state Leaf;
        [*] -> Leaf;
    }
    state Sparse {
        pseudo state Marker;
        [*] -> Marker;
        >> during before { }
    }
    state Idle {
        during { counter = 5; assigned = 2.25; }
    }
    state Blocked;
    state Done;
    state Orphan { enter Cleanup {} }
    state LeafForced { !* -> [*] :: Never; }

    [*] -> Idle : if [true];
    Idle -> Active : if [read_only > 0];
    Idle -> Active : if [read_only > 0];
    Active -> Active;
    Active -> Blocked : if [(0x0F & 0xF0) != 0];
    Blocked -> Done effect { stable = stable; };
    Done -> Idle : Tick;
    !Done -> Idle : Tick;
}
"""
    report = inspect_model(_parse(source), large_composite_threshold=2)
    diagnostics = [diag for diag in report.diagnostics if diag.code in CODE_REGISTRY]
    assert diagnostics
    seen = {diag.code for diag in diagnostics}
    assert seen - inspect_module.KNOWN_SPANLESS_CODES
    for diag in diagnostics:
        if diag.code in inspect_module.KNOWN_SPANLESS_CODES:
            assert diag.span is None
            continue
        assert diag.span is not None, (diag.code, diag.refs)
        assert _slice_by_span(source, diag.span).strip(), (
            diag.code,
            diag.refs,
            diag.span,
        )
