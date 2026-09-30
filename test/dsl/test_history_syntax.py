import pytest

from pyfcstm.dsl import GrammarParseError, parse_with_grammar_entry
from pyfcstm.dsl.node import *


def _state(text):
    return parse_with_grammar_entry(text, "state_definition")


@pytest.mark.unittest
class TestHistoryDeclarations:
    def test_shallow_and_deep_defaults_are_collected_on_the_owner(self):
        state = _state(
            """
            state Program {
                state Idle;
                state Wash { state Fill; [*] -> Fill; }
                [*] -> Idle;
                [H] -> Idle;
                [H*] -> Wash.Fill;
            }
            """
        )
        assert state.histories == [
            HistoryDefinition(kind="shallow", default_path=["Idle"]),
            HistoryDefinition(kind="deep", default_path=["Wash", "Fill"]),
        ]
        assert [str(item) for item in state.histories] == [
            "[H] -> Idle;",
            "[H*] -> Wash.Fill;",
        ]

    def test_history_declaration_keeps_its_leading_documentation(self):
        state = _state(
            """
            state Program {
                state Idle;
                [*] -> Idle;
                /* Resume where the program stopped. */
                [H] -> Idle;
            }
            """
        )
        (history,) = state.histories
        assert history.doc == "Resume where the program stopped."
        assert str(history).startswith("/*")
        assert str(history).endswith("[H] -> Idle;")

    def test_history_declarations_round_trip_through_the_state_text(self):
        state = _state(
            """
            state Program {
                state Idle;
                [*] -> Idle;
                [H] -> Idle;
                [H*] -> Idle;
            }
            """
        )
        assert _state(str(state)) == state
        assert "[H] -> Idle;" in str(state)
        assert "[H*] -> Idle;" in str(state)

    def test_a_state_with_only_history_declarations_is_not_rendered_as_a_leaf(self):
        state = StateDefinition(
            "Program", histories=[HistoryDefinition("shallow", ["Idle"])]
        )
        assert str(state) == "state Program {\n    [H] -> Idle;\n}"

    def test_states_without_history_have_an_empty_history_list(self):
        assert _state("state Idle;").histories == []
        assert _state("state P { state A; [*] -> A; }").histories == []


@pytest.mark.unittest
class TestHistoryTargets:
    @pytest.mark.parametrize(
        ["text", "expected"],
        [
            (
                "Paused -> Program.[H] :: Shallow;",
                TransitionDefinition(
                    from_state="Paused",
                    to_state="Program",
                    event_id=ChainID(["Paused", "Shallow"]),
                    condition_expr=None,
                    post_operations=[],
                    target_history="shallow",
                ),
            ),
            (
                "Paused -> Program.[H*] : if [x > 0];",
                TransitionDefinition(
                    from_state="Paused",
                    to_state="Program",
                    event_id=None,
                    condition_expr=BinaryOp(Name("x"), ">", Integer("0")),
                    post_operations=[],
                    target_history="deep",
                ),
            ),
            (
                "[*] -> Program.[H*];",
                TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="Program",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                    target_history="deep",
                ),
            ),
            (
                "Program -> Program.[H];",
                TransitionDefinition(
                    from_state="Program",
                    to_state="Program",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                    target_history="shallow",
                ),
            ),
        ],
    )
    def test_transitions_may_target_history(self, text, expected):
        node = parse_with_grammar_entry(text, "transition_definition")
        assert node == expected
        assert str(node) == text
        assert parse_with_grammar_entry(str(node), "transition_definition") == node

    def test_history_target_is_part_of_transition_identity(self):
        plain = parse_with_grammar_entry("A -> B;", "transition_definition")
        history = parse_with_grammar_entry("A -> B.[H];", "transition_definition")
        assert plain.target_history is None
        assert plain != history

    def test_combo_trigger_and_effect_follow_the_history_target(self):
        text = (
            "Offline -> Session.[H*] :: Resume + [online > 0] effect {\n"
            "    resume_count = resume_count + 1;\n"
            "}"
        )
        node = parse_with_grammar_entry(text, "transition_definition")
        assert node.to_state == "Session"
        assert node.target_history == "deep"
        assert node.combo_trigger is not None and node.combo_trigger.is_combo
        assert len(node.post_operations) == 1
        assert str(node) == text

    @pytest.mark.parametrize(
        ["text", "from_state", "kind", "rendered"],
        [
            ("!Program -> Program.[H*] :: Reenter;", "Program", "deep", "! Program -> Program.[H*] :: Reenter;"),
            ("!* -> Program.[H];", ALL, "shallow", "! * -> Program.[H];"),
            ("!Idle -> Program.[H] : if [x > 0];", "Idle", "shallow", "! Idle -> Program.[H] : if [x > 0];"),
        ],
    )
    def test_forced_transitions_may_target_history(self, text, from_state, kind, rendered):
        node = parse_with_grammar_entry(text, "transition_force_definition")
        assert node.from_state == from_state
        assert node.to_state == "Program"
        assert node.target_history == kind
        assert str(node) == rendered
        assert parse_with_grammar_entry(str(node), "transition_force_definition") == node


@pytest.mark.unittest
class TestHistoryLexicalBoundaries:
    @pytest.mark.parametrize(
        "text",
        [
            "state H { state A; [*] -> A; }",
            "state P { state H; [*] -> H; H -> H :: Go; }",
            "state P { state A; [*] -> A : if [H > 1]; }",
        ],
    )
    def test_plain_h_identifiers_keep_working(self, text):
        # The history markers are compact bracket tokens, so ``H`` stays an
        # ordinary identifier for states, events and variables.
        assert isinstance(_state(text), StateDefinition)

    @pytest.mark.parametrize(
        "text",
        [
            "state P { state A; [*] -> A; [ H ] -> A; }",
            "state P { state A; [*] -> A; [H *] -> A; }",
            "state P { state A; [*] -> A; [H] -> ; }",
            "state P { state A; [*] -> A; [H] -> A.[H]; }",
            "state P { state A; [*] -> A; [H] -> A effect { x = 1; } }",
            "state P { state A; [*] -> A; [H] -> A :: E; }",
            "state P { state A; [*] -> A; A -> [*].[H]; }",
            "state P { state A; [*] -> A; B -> P.A.[H]; }",
            "state P { state A; [*] -> A; B -> A.[H].x; }",
            "state P { state A; [*] -> A : [H]; }",
            "state P { state A; [*] -> A; !A -> [*].[H]; }",
        ],
    )
    def test_history_markers_are_rejected_outside_their_positions(self, text):
        with pytest.raises(GrammarParseError):
            _state(text)
