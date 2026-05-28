"""
Precision tests for AST-node :class:`pyfcstm.utils.validate.Span` propagation.

PR-2 of the Layer 1 structured-diagnostic refactor (see issue #103) requires
the diagnostic-emit pipeline in :mod:`pyfcstm.model.model` to anchor each
:class:`pyfcstm.utils.validate.ModelDiagnostic` to a precise source
location. The anchor data comes from
:func:`pyfcstm.dsl.listener._ctx_span`, which the listener attaches to
``DefAssignment`` / ``StateDefinition`` / ``TransitionDefinition`` /
``ForceTransitionDefinition`` instances as a ``_span`` attribute.

This file pins down the precision contract by, for every spanning node
kind:

1. Constructing a DSL snippet with the relevant construct on a known line
   and column.
2. Parsing and locating the AST node.
3. Slicing the source text using the node's ``_span`` ``[column, end_column)``
   half-open range on the ``[line, end_line]`` line set.
4. Asserting the slice equals the expected source substring of the
   construct, character-for-character.

If any of the asserts fail, ``_ctx_span`` is reporting an imprecise
location that downstream tooling (IDE, jsfcstm visualization, LLM agent
loop) would visualize incorrectly.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.utils.validate import Span


def _slice_by_span(source: str, span: Span) -> str:
    """
    Slice ``source`` using ``[column, end_column)`` half-open columns over
    ``[line, end_line]`` lines. Both line and column indexing are 1-based,
    matching the :class:`Span` contract.
    """
    assert span is not None, "span must not be None"
    lines = source.split('\n')
    if span.end_line is None or span.end_line == span.line:
        line_text = lines[span.line - 1]
        return line_text[span.column - 1:(span.end_column or span.column + 1) - 1]
    # Multi-line slice: head line tail + intermediate full lines + last
    # line up to end_column (exclusive).
    pieces = [lines[span.line - 1][span.column - 1:]]
    for i in range(span.line, span.end_line - 1):
        pieces.append(lines[i])
    pieces.append(lines[span.end_line - 1][:span.end_column - 1])
    return '\n'.join(pieces)


@pytest.mark.unittest
class TestDefAssignmentSpan:
    def test_simple_def_int(self):
        src = "def int counter = 0;\nstate Root { state A; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        span = ast.definitions[0]._span
        assert _slice_by_span(src, span) == "def int counter = 0;"
        assert span.line == 1
        assert span.column == 1
        assert span.end_line == 1
        assert span.end_column == 21  # exclusive end after ';'

    def test_def_float(self):
        src = "def float temp = 25.5;\nstate Root { state A; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        assert _slice_by_span(src, ast.definitions[0]._span) == "def float temp = 25.5;"

    def test_def_with_leading_blank_lines(self):
        src = "\n\n  def int x = 0xFF;\nstate Root { state A; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        span = ast.definitions[0]._span
        assert span.line == 3
        assert span.column == 3
        assert _slice_by_span(src, span) == "def int x = 0xFF;"

    def test_def_with_hex_literal(self):
        src = "def int mask = 0xCAFE;\nstate Root { state A; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        assert _slice_by_span(src, ast.definitions[0]._span) == "def int mask = 0xCAFE;"

    def test_def_with_arithmetic_init(self):
        src = "def int flags = 0xFF & 0x0F;\nstate Root { state A; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        assert _slice_by_span(src, ast.definitions[0]._span) == "def int flags = 0xFF & 0x0F;"

    def test_multiple_defs_each_span_correct(self):
        src = "def int x = 0;\ndef float y = 1.5;\ndef int z = 7;\nstate Root { state A; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        assert _slice_by_span(src, ast.definitions[0]._span) == "def int x = 0;"
        assert _slice_by_span(src, ast.definitions[1]._span) == "def float y = 1.5;"
        assert _slice_by_span(src, ast.definitions[2]._span) == "def int z = 7;"
        assert ast.definitions[0]._span.line == 1
        assert ast.definitions[1]._span.line == 2
        assert ast.definitions[2]._span.line == 3


@pytest.mark.unittest
class TestStateDefinitionSpan:
    def test_leaf_state_simple(self):
        src = "state Root { state Idle; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        # Root state span covers the full composite block
        root_span = ast.root_state._span
        assert _slice_by_span(src, root_span) == "state Root { state Idle; }"
        # Leaf state span covers just "state Idle;"
        leaf_span = ast.root_state.substates[0]._span
        assert _slice_by_span(src, leaf_span) == "state Idle;"

    def test_pseudo_state_span_includes_pseudo_keyword(self):
        src = "state Root { pseudo state Special; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        leaf_span = ast.root_state.substates[0]._span
        assert _slice_by_span(src, leaf_span) == "pseudo state Special;"

    def test_named_leaf_state(self):
        src = 'state Root { state Running named "System Running"; }'
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        leaf_span = ast.root_state.substates[0]._span
        assert _slice_by_span(src, leaf_span) == 'state Running named "System Running";'

    def test_composite_state_multiline(self):
        src = "state Outer {\n    state A;\n    state B;\n}"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        span = ast.root_state._span
        assert span.line == 1
        assert span.column == 1
        assert span.end_line == 4
        # End column points one past the closing brace on line 4
        assert span.end_column == 2
        assert _slice_by_span(src, span) == src

    def test_nested_composite_each_substate_correct(self):
        src = "state Root {\n    state Mid {\n        state Leaf;\n    }\n}"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        root = ast.root_state
        assert root._span.line == 1
        assert root._span.column == 1

        mid = root.substates[0]
        assert mid._span.line == 2
        assert mid._span.column == 5
        assert _slice_by_span(src, mid._span) == (
            "state Mid {\n        state Leaf;\n    }"
        )

        leaf = mid.substates[0]
        assert leaf._span.line == 3
        assert leaf._span.column == 9
        assert _slice_by_span(src, leaf._span) == "state Leaf;"

    def test_leaf_with_column_offset(self):
        src = "state Root {     state Inner;     }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        leaf = ast.root_state.substates[0]
        # Find the "state Inner;" text and verify span maps to it.
        start_idx = src.index("state Inner;")
        # ANTLR's column is 0-based; our span.column is 1-based.
        assert leaf._span.column == start_idx + 1
        assert _slice_by_span(src, leaf._span) == "state Inner;"


@pytest.mark.unittest
class TestTransitionDefinitionSpan:
    def test_normal_transition_simple(self):
        src = "state Root { state A; state B; A -> B; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        trans = ast.root_state.transitions[0]
        assert _slice_by_span(src, trans._span) == "A -> B;"

    def test_normal_transition_with_event(self):
        src = "state Root { state A; state B; A -> B :: Done; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        trans = ast.root_state.transitions[0]
        assert _slice_by_span(src, trans._span) == "A -> B :: Done;"

    def test_normal_transition_with_guard(self):
        src = "def int x = 0;\nstate Root { state A; state B; A -> B : if [x > 0]; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        trans = ast.root_state.transitions[0]
        assert _slice_by_span(src, trans._span) == "A -> B : if [x > 0];"

    def test_normal_transition_with_effect(self):
        # The transition rule does not include the trailing ';' as part of
        # the parse context; the span covers from the source-state token
        # through the closing '}' of the effect block.
        src = "def int x = 0;\nstate Root { state A; state B; A -> B effect { x = 1; }; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        trans = ast.root_state.transitions[0]
        assert _slice_by_span(src, trans._span) == "A -> B effect { x = 1; }"

    def test_entry_transition(self):
        src = "state Root { state A; [*] -> A; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        trans = ast.root_state.transitions[0]
        # Entry transitions start with `[`; span includes the trailing ';'.
        assert _slice_by_span(src, trans._span) == "[*] -> A;"

    def test_exit_transition(self):
        src = "state Root { state A; A -> [*]; }"
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        trans = ast.root_state.transitions[0]
        assert _slice_by_span(src, trans._span) == "A -> [*];"

    def test_transition_multiline(self):
        src = (
            "state Root {\n"
            "    state A;\n"
            "    state B;\n"
            "    A -> B :: Done;\n"
            "}"
        )
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        trans = ast.root_state.transitions[0]
        assert trans._span.line == 4
        assert trans._span.column == 5
        assert trans._span.end_line == 4
        assert _slice_by_span(src, trans._span) == "A -> B :: Done;"


@pytest.mark.unittest
class TestForceTransitionDefinitionSpan:
    def test_force_transition_normal_named_source(self):
        # `!State -> Target :: Event;`
        src = (
            "state Root {\n"
            "    state A;\n"
            "    state B;\n"
            "    event Go;\n"
            "    !A -> B :: Go;\n"
            "}"
        )
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        ft = ast.root_state.force_transitions[0]
        assert ft._span.line == 5
        # Force-transition grammar includes the trailing ';' in the parse ctx.
        assert _slice_by_span(src, ft._span) == "!A -> B :: Go;"

    def test_force_transition_exit_form(self):
        src = (
            "state Root {\n"
            "    state A;\n"
            "    event Fatal;\n"
            "    !A -> [*] :: Fatal;\n"
            "}"
        )
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        ft = ast.root_state.force_transitions[0]
        assert _slice_by_span(src, ft._span) == "!A -> [*] :: Fatal;"

    def test_force_transition_all_wildcard(self):
        src = (
            "state Root {\n"
            "    state A;\n"
            "    state ErrorHandler;\n"
            "    event GlobalErr;\n"
            "    !* -> ErrorHandler :: GlobalErr;\n"
            "}"
        )
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        ft = ast.root_state.force_transitions[0]
        assert _slice_by_span(src, ft._span) == "!* -> ErrorHandler :: GlobalErr;"

    def test_force_transition_all_to_exit(self):
        src = (
            "state Root {\n"
            "    state A;\n"
            "    event GlobalErr;\n"
            "    !* -> [*] :: GlobalErr;\n"
            "}"
        )
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        ft = ast.root_state.force_transitions[0]
        assert _slice_by_span(src, ft._span) == "!* -> [*] :: GlobalErr;"


@pytest.mark.unittest
class TestSpanInvariants:
    """Cross-cutting properties that every spanned node must obey."""

    @pytest.fixture
    def parsed(self):
        src = (
            "def int x = 0;\n"
            "def float y = 1.5;\n"
            "state Root {\n"
            "    state Idle;\n"
            "    state Active {\n"
            "        state Sub;\n"
            "        [*] -> Sub;\n"
            "    }\n"
            "    event Go;\n"
            "    !Idle -> Active :: Go;\n"
            "    Active -> Idle :: Go;\n"
            "}"
        )
        ast = parse_with_grammar_entry(src, 'state_machine_dsl')
        return src, ast

    def test_every_spanned_node_has_span_attribute(self, parsed):
        src, ast = parsed
        targets = [
            ast.definitions[0],
            ast.definitions[1],
            ast.root_state,
            ast.root_state.substates[0],
            ast.root_state.substates[1],
            ast.root_state.substates[1].substates[0],
            ast.root_state.substates[1].transitions[0],
            ast.root_state.transitions[0],
            ast.root_state.force_transitions[0],
        ]
        for node in targets:
            span = getattr(node, '_span', None)
            assert span is not None, f"node missing _span: {node!r}"
            assert span.line >= 1
            assert span.column >= 1

    def test_spans_are_well_formed(self, parsed):
        src, ast = parsed

        def _walk(node, results):
            span = getattr(node, '_span', None)
            if span is not None:
                # end_line >= line; if same line, end_column > column.
                assert span.end_line is not None
                assert span.end_column is not None
                assert span.end_line >= span.line
                if span.end_line == span.line:
                    assert span.end_column > span.column, (
                        f"degenerate single-line span on {type(node).__name__}: "
                        f"col={span.column}, end_col={span.end_column}"
                    )
                results.append((type(node).__name__, span))
            # Walk children
            for attr in ('definitions', 'root_state', 'substates',
                         'transitions', 'force_transitions'):
                child = getattr(node, attr, None)
                if child is None:
                    continue
                if isinstance(child, list):
                    for c in child:
                        _walk(c, results)
                else:
                    _walk(child, results)

        results = []
        _walk(ast, results)
        # We should have collected spans for definitions + states + transitions
        assert len(results) >= 8

    def test_parent_span_contains_children_spans(self, parsed):
        """For nested constructs, the parent's span fully encloses each child's span."""
        src, ast = parsed
        root = ast.root_state
        for child in root.substates + root.transitions + root.force_transitions:
            child_span = getattr(child, '_span', None)
            if child_span is None:
                continue
            # Either child starts on a later line, or starts on same line with greater column
            ok_start = (
                child_span.line > root._span.line
                or (child_span.line == root._span.line
                    and child_span.column >= root._span.column)
            )
            ok_end = (
                child_span.end_line < root._span.end_line
                or (child_span.end_line == root._span.end_line
                    and child_span.end_column <= root._span.end_column)
            )
            assert ok_start, (
                f"child {type(child).__name__} starts before parent: "
                f"child={child_span}, parent={root._span}"
            )
            assert ok_end, (
                f"child {type(child).__name__} ends after parent: "
                f"child={child_span}, parent={root._span}"
            )

    def test_slice_via_span_equals_original_for_full_root(self, parsed):
        src, ast = parsed
        root_span = ast.root_state._span
        sliced = _slice_by_span(src, root_span)
        # Slice should start with "state Root" and end with "}"
        assert sliced.startswith("state Root")
        assert sliced.endswith("}")
