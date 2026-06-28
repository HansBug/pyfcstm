import pytest

from pyfcstm.dsl import GrammarParseError, parse_with_grammar_entry
from pyfcstm.dsl.node import (
    EXIT_STATE,
    INIT_STATE,
    BinaryOp,
    ChainID,
    ComboEventTerm,
    ComboGuardTerm,
    Integer,
    Name,
)
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils import ModelValidationError
from pyfcstm.utils.validate import Span


def _slice_by_span(source: str, span: Span) -> str:
    assert span is not None, "span must not be None"
    lines = source.split("\n")
    if span.end_line is None or span.end_line == span.line:
        line_text = lines[span.line - 1]
        return line_text[span.column - 1 : (span.end_column or span.column + 1) - 1]
    pieces = [lines[span.line - 1][span.column - 1 :]]
    for i in range(span.line, span.end_line - 1):
        pieces.append(lines[i])
    pieces.append(lines[span.end_line - 1][: span.end_column - 1])
    return "\n".join(pieces)


@pytest.mark.unittest
class TestComboTransitionTriggerParsing:
    @pytest.mark.parametrize(
        ["source", "expected_from", "expected_to", "expected_terms"],
        [
            (
                "S1 -> S2 :: E1 + E2;",
                "S1",
                "S2",
                [
                    ("event", "local", ChainID(["E1"])),
                    ("event", "local", ChainID(["E2"])),
                ],
            ),
            (
                "S1 -> S2 :: E1 + [x > 0];",
                "S1",
                "S2",
                [("event", "local", ChainID(["E1"])), ("guard", "x > 0")],
            ),
            (
                "S1 -> S2 :: [x > 0] + E1;",
                "S1",
                "S2",
                [("guard", "x > 0"), ("event", "local", ChainID(["E1"]))],
            ),
            (
                "S1 -> S2 :: E1 + [x > 0] + E2;",
                "S1",
                "S2",
                [
                    ("event", "local", ChainID(["E1"])),
                    ("guard", "x > 0"),
                    ("event", "local", ChainID(["E2"])),
                ],
            ),
            (
                "S1 -> S2 : E1 + /Bus.E2 + [x > 0];",
                "S1",
                "S2",
                [
                    ("event", "chain", ChainID(["E1"])),
                    ("event", "absolute", ChainID(["Bus", "E2"], is_absolute=True)),
                    ("guard", "x > 0"),
                ],
            ),
            (
                "S1 -> S2 : E1 + E2;",
                "S1",
                "S2",
                [
                    ("event", "chain", ChainID(["E1"])),
                    ("event", "chain", ChainID(["E2"])),
                ],
            ),
            (
                "S1 -> S2 : S1.E1 + Other.E2;",
                "S1",
                "S2",
                [
                    ("event", "chain", ChainID(["S1", "E1"])),
                    ("event", "chain", ChainID(["Other", "E2"])),
                ],
            ),
            (
                "[*] -> S1 :: E1 + E2;",
                INIT_STATE,
                "S1",
                [
                    ("event", "chain", ChainID(["E1"])),
                    ("event", "chain", ChainID(["E2"])),
                ],
            ),
            (
                "S1 -> [*] :: E1 + [x > 0];",
                "S1",
                EXIT_STATE,
                [("event", "local", ChainID(["E1"])), ("guard", "x > 0")],
            ),
            (
                "S1 -> S2 : [x > 0] + [y < 0];",
                "S1",
                "S2",
                [("guard", "x > 0"), ("guard", "y < 0")],
            ),
        ],
    )
    def test_positive_combo_forms(
        self, source, expected_from, expected_to, expected_terms
    ):
        transition = parse_with_grammar_entry(
            source, entry_name="transition_definition"
        )

        assert (
            transition.from_state is expected_from
            or transition.from_state == expected_from
        )
        assert transition.to_state is expected_to or transition.to_state == expected_to
        assert transition.combo_trigger is not None
        assert transition.condition_expr is None
        assert len(transition.combo_trigger.terms) == len(expected_terms)

        for term, expected in zip(transition.combo_trigger.terms, expected_terms):
            if expected[0] == "event":
                _, scope, event_id = expected
                assert isinstance(term, ComboEventTerm)
                assert term.event_scope == scope
                assert term.event_id == event_id
            else:
                _, condition_text = expected
                assert isinstance(term, ComboGuardTerm)
                assert str(term.condition_expr) == condition_text

    def test_single_entry_event_keeps_legacy_chain_origin(self):
        transition = parse_with_grammar_entry(
            "[*] -> S1 :: E1;", entry_name="transition_definition"
        )

        assert transition.combo_trigger is None
        assert transition.event_id == ChainID(["E1"])
        assert transition.event_scope == "chain"

    def test_entry_combo_terms_follow_legacy_chain_origin(self):
        transition = parse_with_grammar_entry(
            "[*] -> S1 :: E1 + E2;", entry_name="transition_definition"
        )

        assert transition.combo_trigger is not None
        assert [
            (term.event_scope, term.event_id) for term in transition.combo_trigger.terms
        ] == [
            ("chain", ChainID(["E1"])),
            ("chain", ChainID(["E2"])),
        ]
        assert str(transition) == "[*] -> S1 :: E1 + E2;"

    def test_pure_guard_alias_uses_existing_condition_field(self):
        transition = parse_with_grammar_entry(
            "S1 -> S2 : [x > 0];", entry_name="transition_definition"
        )

        assert transition.combo_trigger is not None
        assert not transition.combo_trigger.is_combo
        assert transition.event_id is None
        assert transition.condition_expr == BinaryOp(Name("x"), ">", Integer("0"))
        assert str(transition) == "S1 -> S2 : if [x > 0];"

    @pytest.mark.parametrize(
        "source",
        [
            "S1 -> S2 :: [x > 0];",
            "S1 -> S2 :: [x > 0] + [y < 0];",
            "S1 -> S2 :: E1 + : Other.E2;",
            "!S1 -> S2 :: E1 + E2;",
        ],
    )
    def test_negative_combo_forms(self, source):
        with pytest.raises(GrammarParseError):
            parse_with_grammar_entry(source, entry_name="transition_definition")

    def test_combo_model_build_fails_until_expansion_support(self):
        program = parse_with_grammar_entry(
            "state Root { state S1; state S2; [*] -> S1; S1 -> S2 :: E1 + E2; }",
            entry_name="state_machine_dsl",
        )

        with pytest.raises(ModelValidationError) as exc_info:
            parse_dsl_node_to_state_machine(program)

        diagnostic = next(
            diag
            for diag in exc_info.value.diagnostics
            if diag.code == "E_COMBO_TRIGGER_NOT_EXPANDED"
        )
        assert diagnostic.refs == {
            "state_path": "Root",
            "trigger": ":: E1 + E2",
        }

    def test_pure_guard_alias_builds_existing_model_guard(self):
        program = parse_with_grammar_entry(
            "def int x = 0; state Root { state S1; state S2; [*] -> S1; S1 -> S2 : [x > 0]; }",
            entry_name="state_machine_dsl",
        )

        model = parse_dsl_node_to_state_machine(program)
        transition = model.root_state.transitions[1]

        assert transition.event is None
        assert str(transition.guard) == "x > 0"


@pytest.mark.unittest
class TestComboTransitionTriggerSpans:
    def test_combo_term_and_value_spans_slice_original_source(self):
        source = "def int x = 0;\nstate Root { state S1; state S2; S1 -> S2 :: E1 + [x > 0] + E2; }"
        ast = parse_with_grammar_entry(source, entry_name="state_machine_dsl")
        transition = ast.root_state.transitions[0]
        trigger = transition.combo_trigger

        assert (
            _slice_by_span(source, transition._span) == "S1 -> S2 :: E1 + [x > 0] + E2;"
        )
        assert _slice_by_span(source, trigger.trigger_span) == ":: E1 + [x > 0] + E2"
        assert [_slice_by_span(source, term.term_span) for term in trigger.terms] == [
            "E1",
            "[x > 0]",
            "E2",
        ]
        assert [
            _slice_by_span(source, term.removal_span) for term in trigger.terms
        ] == [
            "E1 + ",
            " + [x > 0]",
            " + E2",
        ]

        guard_term = trigger.terms[1]
        assert isinstance(guard_term, ComboGuardTerm)
        assert _slice_by_span(source, guard_term.value_span) == "x > 0"
        assert trigger.canonical_text == ":: E1 + [x > 0] + E2"

    def test_pure_guard_alias_keeps_guard_value_span_in_internal_trigger(self):
        source = (
            "def int x = 0;\nstate Root { state S1; state S2; S1 -> S2 : [x > 0]; }"
        )
        ast = parse_with_grammar_entry(source, entry_name="state_machine_dsl")
        transition = ast.root_state.transitions[0]

        assert transition.combo_trigger is not None
        assert not transition.combo_trigger.is_combo
        guard_term = transition.combo_trigger.terms[0]
        assert isinstance(guard_term, ComboGuardTerm)
        assert str(transition.condition_expr) == "x > 0"
        assert (
            _slice_by_span(source, transition.combo_trigger.trigger_span) == ": [x > 0]"
        )
        assert _slice_by_span(source, guard_term.value_span) == "x > 0"
