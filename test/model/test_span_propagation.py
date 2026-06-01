"""
Model-layer source span propagation tests.

PR-D1 of issue #133 keeps diagnostic emit sites unchanged, but requires
model objects created from DSL AST nodes to retain the AST source span so
PR-D2 can anchor diagnostics without re-parsing source text.
"""

import pytest

from pyfcstm.diagnostics.inspect import inspect_model
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.utils.validate import Span


MODEL_SPAN_DSL = """def int x = 0;
def float y = 1.0;

state Root {
    event Go named "Go Event";

    enter Init { x = 1; }
    during before Tick { x = x + 1; }
    exit abstract Cleanup;
    >> during after Monitor { x = x + 2; }

    state A {
        enter { x = x + 3; }
    }
    state B;

    [*] -> A;
    A -> B : Go effect {
        x = x + 4;
    };
}
"""


def _slice_by_span(source: str, span: Span) -> str:
    """Return the source slice covered by a 1-based listener span."""
    assert span is not None, "span must not be None"
    lines = source.split("\n")
    end_line = span.end_line or span.line
    end_column = span.end_column or (span.column + 1)
    if end_line == span.line:
        return lines[span.line - 1][span.column - 1 : end_column - 1]

    pieces = [lines[span.line - 1][span.column - 1 :]]
    for index in range(span.line, end_line - 1):
        pieces.append(lines[index])
    pieces.append(lines[end_line - 1][: end_column - 1])
    return "\n".join(pieces)


def _assert_source_slice(source: str, obj, expected: str) -> None:
    span = getattr(obj, "_span", None)
    assert span is not None, f"{obj!r} does not carry _span"
    assert _slice_by_span(source, span) == expected


@pytest.mark.unittest
class TestModelSpanPropagation:
    def test_core_model_objects_keep_ast_source_spans(self):
        machine = load_state_machine_from_text(MODEL_SPAN_DSL)
        root = machine.root_state

        _assert_source_slice(MODEL_SPAN_DSL, machine.defines["x"], "def int x = 0;")
        _assert_source_slice(
            MODEL_SPAN_DSL, root, MODEL_SPAN_DSL.split("\n", 3)[3].rstrip("\n")
        )
        _assert_source_slice(
            MODEL_SPAN_DSL, root.events["Go"], 'event Go named "Go Event";'
        )
        _assert_source_slice(
            MODEL_SPAN_DSL,
            root.substates["A"],
            "state A {\n        enter { x = x + 3; }\n    }",
        )

        user_transition = next(
            transition
            for transition in root.transitions
            if transition.from_state == "A" and transition.to_state == "B"
        )
        _assert_source_slice(
            MODEL_SPAN_DSL,
            user_transition,
            "A -> B : Go effect {\n        x = x + 4;\n    }",
        )

    def test_lifecycle_actions_and_operations_keep_ast_source_spans(self):
        machine = load_state_machine_from_text(MODEL_SPAN_DSL)
        root = machine.root_state

        enter_action = root.on_enters[0]
        during_action = root.on_durings[0]
        exit_action = root.on_exits[0]
        aspect_action = root.on_during_aspects[0]
        user_transition = next(
            transition
            for transition in root.transitions
            if transition.from_state == "A" and transition.to_state == "B"
        )

        _assert_source_slice(MODEL_SPAN_DSL, enter_action, "enter Init { x = 1; }")
        _assert_source_slice(MODEL_SPAN_DSL, enter_action.operations[0], "x = 1;")
        _assert_source_slice(
            MODEL_SPAN_DSL, during_action, "during before Tick { x = x + 1; }"
        )
        _assert_source_slice(MODEL_SPAN_DSL, during_action.operations[0], "x = x + 1;")
        _assert_source_slice(MODEL_SPAN_DSL, exit_action, "exit abstract Cleanup;")
        _assert_source_slice(
            MODEL_SPAN_DSL, aspect_action, ">> during after Monitor { x = x + 2; }"
        )
        _assert_source_slice(MODEL_SPAN_DSL, aspect_action.operations[0], "x = x + 2;")
        _assert_source_slice(MODEL_SPAN_DSL, user_transition.effects[0], "x = x + 4;")

    def test_lifecycle_ref_actions_keep_their_own_ast_source_spans(self):
        source = """def int x = 0;

state Root {
    enter SharedEnter { x = 1; }
    enter ref SharedEnter;
    during before SharedDuring { x = x + 1; }
    during before ref SharedDuring;
    exit SharedExit { x = x + 2; }
    exit ref SharedExit;
    >> during after SharedAspect { x = x + 3; }
    >> during after ref SharedAspect;

    state A;
    [*] -> A;
}
"""
        machine = load_state_machine_from_text(source)
        root = machine.root_state

        _assert_source_slice(source, root.on_enters[1], "enter ref SharedEnter;")
        _assert_source_slice(
            source, root.on_durings[1], "during before ref SharedDuring;"
        )
        _assert_source_slice(source, root.on_exits[1], "exit ref SharedExit;")
        _assert_source_slice(
            source, root.on_during_aspects[1], ">> during after ref SharedAspect;"
        )

    def test_inspect_json_does_not_leak_model_private_span_fields(self):
        machine = load_state_machine_from_text(MODEL_SPAN_DSL)
        payload = inspect_model(machine).to_json()

        def _walk(value):
            if isinstance(value, dict):
                assert "_span" not in value
                for item in value.values():
                    _walk(item)
            elif isinstance(value, list):
                for item in value:
                    _walk(item)

        _walk(payload)

    def test_if_block_statements_keep_ast_source_spans(self):
        source = """def int x = 0;

state Root {
    state A {
        during {
            if [x > 0] {
                x = x + 1;
            } else {
                x = x + 2;
            }
        }
    }
    [*] -> A;
}
"""
        machine = load_state_machine_from_text(source)
        if_block = machine.root_state.substates["A"].on_durings[0].operations[0]

        _assert_source_slice(
            source,
            if_block,
            (
                "if [x > 0] {\n"
                "                x = x + 1;\n"
                "            } else {\n"
                "                x = x + 2;\n"
                "            }"
            ),
        )
        _assert_source_slice(source, if_block.branches[0].statements[0], "x = x + 1;")
        _assert_source_slice(source, if_block.branches[1].statements[0], "x = x + 2;")

    def test_forced_transition_expansions_keep_declaring_ast_source_span(self):
        source = """def int x = 0;

state Root {
    state A;
    state B;

    [*] -> A;
    !A -> B : if [x > 0];
}
"""
        machine = load_state_machine_from_text(source)
        transition = next(
            transition
            for transition in machine.root_state.transitions
            if transition.is_forced
        )

        _assert_source_slice(source, transition, "!A -> B : if [x > 0];")
