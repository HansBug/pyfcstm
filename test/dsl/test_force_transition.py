import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLForceTransition:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                """
                ! StateA -> StateB;
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state="StateB",
                    event_id=None,
                    condition_expr=None,
                ),
            ),  # Basic normal force transition from StateA to StateB
            (
                """
                ! StateA -> StateB :: fromId;
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state="StateB",
                    event_id=ChainID(path=["StateA", "fromId"], is_absolute=False),
                    condition_expr=None,
                ),
            ),  # Normal force transition with from_id specified
            (
                """
                ! StateA -> StateB : chain.id;
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state="StateB",
                    event_id=ChainID(path=["chain", "id"], is_absolute=False),
                    condition_expr=None,
                ),
            ),  # Normal force transition with chain_id specified
            (
                """
                ! StateA -> StateB : if [x == 10];
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state="StateB",
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=Name(name="x"), op="==", expr2=Integer(raw="10")
                    ),
                ),
            ),  # Normal force transition with condition
            (
                """
                ! StateA -> [*];
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=None,
                ),
            ),  # Basic exit force transition from StateA
            (
                """
                ! StateA -> [*] :: fromId;
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state=EXIT_STATE,
                    event_id=ChainID(path=["StateA", "fromId"], is_absolute=False),
                    condition_expr=None,
                ),
            ),  # Exit force transition with from_id specified
            (
                """
                ! StateA -> [*] : chain.id;
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state=EXIT_STATE,
                    event_id=ChainID(path=["chain", "id"], is_absolute=False),
                    condition_expr=None,
                ),
            ),  # Exit force transition with chain_id specified
            (
                """
                ! StateA -> [*] : if [x == 10];
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=Name(name="x"), op="==", expr2=Integer(raw="10")
                    ),
                ),
            ),  # Exit force transition with condition
            (
                """
                ! * -> StateB;
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state="StateB",
                    event_id=None,
                    condition_expr=None,
                ),
            ),  # Basic normal all force transition to StateB
            (
                """
                ! * -> StateB :: fromId;
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state="StateB",
                    event_id=ChainID(path=["fromId"], is_absolute=False),
                    condition_expr=None,
                ),
            ),  # Normal all force transition with from_id specified
            (
                """
                ! * -> StateB : chain.id;
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state="StateB",
                    event_id=ChainID(path=["chain", "id"], is_absolute=False),
                    condition_expr=None,
                ),
            ),  # Normal all force transition with chain_id specified
            (
                """
                ! * -> StateB : if [x == 10];
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state="StateB",
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=Name(name="x"), op="==", expr2=Integer(raw="10")
                    ),
                ),
            ),  # Normal all force transition with condition
            (
                """
                ! * -> [*];
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=None,
                ),
            ),  # Basic exit all force transition
            (
                """
                ! * -> [*] :: fromId;
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state=EXIT_STATE,
                    event_id=ChainID(path=["fromId"], is_absolute=False),
                    condition_expr=None,
                ),
            ),  # Exit all force transition with from_id specified
            (
                """
                ! * -> [*] : chain.id;
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state=EXIT_STATE,
                    event_id=ChainID(path=["chain", "id"], is_absolute=False),
                    condition_expr=None,
                ),
            ),  # Exit all force transition with chain_id specified
            (
                """
                ! * -> [*] : if [x == 10];
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=Name(name="x"), op="==", expr2=Integer(raw="10")
                    ),
                ),
            ),  # Exit all force transition with condition
            (
                """
                ! StateA -> StateB : if [x > 5 && y < 10];
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state="StateB",
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Name(name="x"), op=">", expr2=Integer(raw="5")
                        ),
                        op="&&",
                        expr2=BinaryOp(
                            expr1=Name(name="y"), op="<", expr2=Integer(raw="10")
                        ),
                    ),
                ),
            ),  # Normal force transition with complex AND condition
            (
                """
                ! StateA -> [*] : if [x == 5 || y != 10];
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Name(name="x"), op="==", expr2=Integer(raw="5")
                        ),
                        op="||",
                        expr2=BinaryOp(
                            expr1=Name(name="y"), op="!=", expr2=Integer(raw="10")
                        ),
                    ),
                ),
            ),  # Exit force transition with complex OR condition
            (
                """
                ! * -> StateB : if [flag == 0 && x > 10];
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state="StateB",
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Name(name="flag"), op="==", expr2=Integer(raw="0")
                        ),
                        op="&&",
                        expr2=BinaryOp(
                            expr1=Name(name="x"), op=">", expr2=Integer(raw="10")
                        ),
                    ),
                ),
            ),  # Normal all force transition with negation in condition
            (
                """
                ! * -> [*] : if [(x > 5) ? true : false];
                """,
                ForceTransitionDefinition(
                    from_state=ALL,
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=ConditionalOp(
                        cond=BinaryOp(
                            expr1=Name(name="x"), op=">", expr2=Integer(raw="5")
                        ),
                        value_true=Boolean(raw="true"),
                        value_false=Boolean(raw="false"),
                    ),
                ),
            ),  # Exit all force transition with conditional expression in condition
            (
                """
                ! StateA -> StateB : /absolute.chain.id;
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state="StateB",
                    event_id=ChainID(
                        path=["absolute", "chain", "id"], is_absolute=True
                    ),
                    condition_expr=None,
                ),
            ),  # Normal force transition with absolute chain ID
            (
                """
                ! StateA -> [*] : /root.path;
                """,
                ForceTransitionDefinition(
                    from_state="StateA",
                    to_state=EXIT_STATE,
                    event_id=ChainID(path=["root", "path"], is_absolute=True),
                    condition_expr=None,
                ),
            ),  # Exit force transition with absolute chain ID
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert (
            parse_with_grammar_entry(
                input_text, entry_name="transition_force_definition"
            )
            == expected
        )

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                """
                ! StateA -> StateB;
                """,
                "! StateA -> StateB;",
            ),  # Basic normal force transition from StateA to StateB
            (
                """
                ! StateA -> StateB :: fromId;
                """,
                "! StateA -> StateB :: fromId;",
            ),  # Normal force transition with from_id specified
            (
                """
                ! StateA -> StateB : chain.id;
                """,
                "! StateA -> StateB : chain.id;",
            ),  # Normal force transition with chain_id specified
            (
                """
                ! StateA -> StateB : if [x == 10];
                """,
                "! StateA -> StateB : if [x == 10];",
            ),  # Normal force transition with condition
            (
                """
                ! StateA -> [*];
                """,
                "! StateA -> [*];",
            ),  # Basic exit force transition from StateA
            (
                """
                ! StateA -> [*] :: fromId;
                """,
                "! StateA -> [*] :: fromId;",
            ),  # Exit force transition with from_id specified
            (
                """
                ! StateA -> [*] : chain.id;
                """,
                "! StateA -> [*] : chain.id;",
            ),  # Exit force transition with chain_id specified
            (
                """
                ! StateA -> [*] : if [x == 10];
                """,
                "! StateA -> [*] : if [x == 10];",
            ),  # Exit force transition with condition
            (
                """
                ! * -> StateB;
                """,
                "! * -> StateB;",
            ),  # Basic normal all force transition to StateB
            (
                """
                ! * -> StateB :: fromId;
                """,
                "! * -> StateB :: fromId;",
            ),  # Normal all force transition with from_id specified
            (
                """
                ! * -> StateB : chain.id;
                """,
                "! * -> StateB : chain.id;",
            ),  # Normal all force transition with chain_id specified
            (
                """
                ! * -> StateB : if [x == 10];
                """,
                "! * -> StateB : if [x == 10];",
            ),  # Normal all force transition with condition
            (
                """
                ! * -> [*];
                """,
                "! * -> [*];",
            ),  # Basic exit all force transition
            (
                """
                ! * -> [*] :: fromId;
                """,
                "! * -> [*] :: fromId;",
            ),  # Exit all force transition with from_id specified
            (
                """
                ! * -> [*] : chain.id;
                """,
                "! * -> [*] : chain.id;",
            ),  # Exit all force transition with chain_id specified
            (
                """
                ! * -> [*] : if [x == 10];
                """,
                "! * -> [*] : if [x == 10];",
            ),  # Exit all force transition with condition
            (
                """
                ! StateA -> StateB : if [x > 5 && y < 10];
                """,
                "! StateA -> StateB : if [x > 5 && y < 10];",
            ),  # Normal force transition with complex AND condition
            (
                """
                ! StateA -> [*] : if [x == 5 || y != 10];
                """,
                "! StateA -> [*] : if [x == 5 || y != 10];",
            ),  # Exit force transition with complex OR condition
            (
                """
                ! * -> StateB : if [flag == 0 && x > 10];
                """,
                "! * -> StateB : if [flag == 0 && x > 10];",
            ),  # Normal all force transition with negation in condition
            (
                """
                ! * -> [*] : if [(x > 5) ? true : false];
                """,
                "! * -> [*] : if [(x > 5) ? True : False];",
            ),  # Exit all force transition with conditional expression in condition
            (
                """
                ! StateA -> StateB : /absolute.chain.id;
                """,
                "! StateA -> StateB : /absolute.chain.id;",
            ),  # Normal force transition with absolute chain ID
            (
                """
                ! StateA -> [*] : /root.path;
                """,
                "! StateA -> [*] : /root.path;",
            ),  # Exit force transition with absolute chain ID
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(
                parse_with_grammar_entry(
                    input_text, entry_name="transition_force_definition"
                )
            ),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                """
                StateA -> StateB;
                """,
            ),  # Missing exclamation mark (!) at the beginning
            (
                """
                ! StateA -> StateB
                """,
            ),  # Missing semicolon at the end
            (
                """
                ! [StateA] -> StateB;
                """,
            ),  # Invalid from state format with brackets
            (
                """
                ! StateA -> [StateB];
                """,
            ),  # Invalid to state format with brackets for normal transition
            (
                """
                ! ** -> StateB;
                """,
            ),  # Invalid wildcard format (using ** instead of *)
            (
                """
                ! [**] -> StateB;
                """,
            ),  # Invalid wildcard format with brackets
            (
                """
                ! StateA -> StateB : if x == 10;
                """,
            ),  # Missing brackets in condition
            (
                """
                ! StateA -> StateB : if (x == 10);
                """,
            ),  # Using parentheses instead of brackets in condition
            (
                """
                ! StateA -> StateB : /chain..id;
                """,
            ),  # Invalid chain ID with consecutive dots
            (
                """
                ! StateA -> StateB : chain-id;
                """,
            ),  # Invalid chain ID with hyphens
            (
                """
                ! StateA -> StateB effect { x = 10; };
                """,
            ),  # Effect block not allowed in force transitions
            (
                """
                ! [*] -> StateB;
                """,
            ),  # Invalid mixing of entry syntax with force transitions
            (
                """
                ! StateA -> StateB : if [x > 5] : chain.id;
                """,
            ),  # Invalid order of options (condition before chain_id)
            (
                """
                ! StateA -> StateB :: fromId :: anotherId;
                """,
            ),  # Multiple from_id specifications
            (
                """
                ! StateA -> StateB : if;
                """,
            ),  # Missing condition after if keyword
            (
                """
                ! StateA -> StateB : : chain.id;
                """,
            ),  # Empty option before chain_id
            (
                """
                ! StateA -> StateB : if x > 5;
                """,
            ),  # Missing brackets around condition
            (
                """
                ! StateA -> StateB : if [x > > 5];
                """,
            ),  # Invalid condition expression with consecutive operators
            (
                """
                ! * -> StateB effect { x = 10; };
                """,
            ),  # Effect block not allowed in force transitions
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(
                input_text, entry_name="transition_force_definition"
            )

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
