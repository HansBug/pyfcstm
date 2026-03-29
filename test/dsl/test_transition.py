import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLTransition:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                "[*] -> StateA;",
                TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="StateA",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
            ),
            # Basic entry transition to StateA
            (
                "[*] -> StateB: chain1;",
                TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="StateB",
                    event_id=ChainID(path=["chain1"]),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # Entry transition with chain identifier
            (
                "[*] -> StateC: if [x > 10];",
                TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="StateC",
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=Name(name="x"), op=">", expr2=Integer(raw="10")
                    ),
                    post_operations=[],
                ),
            ),  # Entry transition with condition
            (
                "[*] -> StateD effect { a = 5; }",
                TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="StateD",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[
                        OperationAssignment(name="a", expr=Integer(raw="5"))
                    ],
                ),
            ),
            # Entry transition with effect action
            (
                "[*] -> StateF: if [x < 0 && y > 10];",
                TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="StateF",
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Name(name="x"), op="<", expr2=Integer(raw="0")
                        ),
                        op="&&",
                        expr2=BinaryOp(
                            expr1=Name(name="y"), op=">", expr2=Integer(raw="10")
                        ),
                    ),
                    post_operations=[],
                ),
            ),
            # Entry transition with complex condition
            (
                "[*] -> StateG effect { a = sin(b); c = 10; }",
                TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="StateG",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[
                        OperationAssignment(
                            name="a", expr=UFunc(func="sin", expr=Name(name="b"))
                        ),
                        OperationAssignment(name="c", expr=Integer(raw="10")),
                    ],
                ),
            ),
            # Entry transition with multiple effect actions
            (
                "StateA -> StateB;",
                TransitionDefinition(
                    from_state="StateA",
                    to_state="StateB",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
            ),
            # Basic transition from StateA to StateB
            (
                "StateC -> StateD: chain4;",
                TransitionDefinition(
                    from_state="StateC",
                    to_state="StateD",
                    event_id=ChainID(path=["chain4"]),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # Transition with chain identifier
            (
                "StateE -> StateF: if [x <= 20];",
                TransitionDefinition(
                    from_state="StateE",
                    to_state="StateF",
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=Name(name="x"), op="<=", expr2=Integer(raw="20")
                    ),
                    post_operations=[],
                ),
            ),  # Transition with condition
            (
                "StateG -> StateH effect { a = 15; }",
                TransitionDefinition(
                    from_state="StateG",
                    to_state="StateH",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[
                        OperationAssignment(name="a", expr=Integer(raw="15"))
                    ],
                ),
            ),
            # Transition with effect action
            (
                "StateK -> StateL: if [x != y && z == 10];",
                TransitionDefinition(
                    from_state="StateK",
                    to_state="StateL",
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Name(name="x"), op="!=", expr2=Name(name="y")
                        ),
                        op="&&",
                        expr2=BinaryOp(
                            expr1=Name(name="z"), op="==", expr2=Integer(raw="10")
                        ),
                    ),
                    post_operations=[],
                ),
            ),
            # Transition with complex condition
            (
                "StateM -> StateN effect { a = cos(b); d = 30; }",
                TransitionDefinition(
                    from_state="StateM",
                    to_state="StateN",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[
                        OperationAssignment(
                            name="a", expr=UFunc(func="cos", expr=Name(name="b"))
                        ),
                        OperationAssignment(name="d", expr=Integer(raw="30")),
                    ],
                ),
            ),
            # Transition with multiple effect actions
            (
                "StateA -> [*];",
                TransitionDefinition(
                    from_state="StateA",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
            ),
            # Basic exit transition from StateA
            (
                "StateB -> [*]: chain7;",
                TransitionDefinition(
                    from_state="StateB",
                    to_state=EXIT_STATE,
                    event_id=ChainID(path=["chain7"]),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # Exit transition with chain identifier
            (
                "StateC -> [*]: if [x >= 100];",
                TransitionDefinition(
                    from_state="StateC",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=Name(name="x"), op=">=", expr2=Integer(raw="100")
                    ),
                    post_operations=[],
                ),
            ),  # Exit transition with condition
            (
                "StateD -> [*] effect { a = 50; }",
                TransitionDefinition(
                    from_state="StateD",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=None,
                    post_operations=[
                        OperationAssignment(name="a", expr=Integer(raw="50"))
                    ],
                ),
            ),
            # Exit transition with effect action
            (
                "StateF -> [*]: if [x == y || z != 10];",
                TransitionDefinition(
                    from_state="StateF",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=BinaryOp(
                            expr1=Name(name="x"), op="==", expr2=Name(name="y")
                        ),
                        op="||",
                        expr2=BinaryOp(
                            expr1=Name(name="z"), op="!=", expr2=Integer(raw="10")
                        ),
                    ),
                    post_operations=[],
                ),
            ),
            # Exit transition with complex condition
            (
                "StateG -> [*] effect { a = sqrt(b); e = 40; }",
                TransitionDefinition(
                    from_state="StateG",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=None,
                    post_operations=[
                        OperationAssignment(
                            name="a", expr=UFunc(func="sqrt", expr=Name(name="b"))
                        ),
                        OperationAssignment(name="e", expr=Integer(raw="40")),
                    ],
                ),
            ),
            # Exit transition with multiple effect actions
            (
                """
                A -> B : /XXX;
                """,
                TransitionDefinition(
                    from_state="A",
                    to_state="B",
                    event_id=ChainID(path=["XXX"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # absolute event path
            (
                """
                A -> B : /XXX effect { x = 1; }
                """,
                TransitionDefinition(
                    from_state="A",
                    to_state="B",
                    event_id=ChainID(path=["XXX"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[
                        OperationAssignment(name="x", expr=Integer(raw="1"))
                    ],
                ),
            ),  # absolute event path with effect
            (
                """
                A -> B : /XXX.YYY;
                """,
                TransitionDefinition(
                    from_state="A",
                    to_state="B",
                    event_id=ChainID(path=["XXX", "YYY"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # absolute event path with chain
            (
                """
                A -> B : /XXX.YYY.ZZZ effect { x = 1; }
                """,
                TransitionDefinition(
                    from_state="A",
                    to_state="B",
                    event_id=ChainID(path=["XXX", "YYY", "ZZZ"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[
                        OperationAssignment(name="x", expr=Integer(raw="1"))
                    ],
                ),
            ),  # absolute event path with chain and effect
            (
                "[*] -> Boot : Boot;",
                TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="Boot",
                    event_id=ChainID(path=["Boot"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # entry transition with local shorthand event encoded via single-segment chain
            (
                "[*] -> Boot : boot.chain;",
                TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="Boot",
                    event_id=ChainID(path=["boot", "chain"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # entry transition with multi-segment relative event path
            (
                "Source -> Target :: Fire;",
                TransitionDefinition(
                    from_state="Source",
                    to_state="Target",
                    event_id=ChainID(path=["Source", "Fire"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # normal transition with explicit local-event shorthand
            (
                "Source -> Target : Source.Fire;",
                TransitionDefinition(
                    from_state="Source",
                    to_state="Target",
                    event_id=ChainID(path=["Source", "Fire"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # normal transition with equivalent relative event path
            (
                "Source -> Target : /Root.Fire;",
                TransitionDefinition(
                    from_state="Source",
                    to_state="Target",
                    event_id=ChainID(path=["Root", "Fire"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
            ),  # normal transition with absolute event path
            (
                "Source -> Target : if [not true or false];",
                TransitionDefinition(
                    from_state="Source",
                    to_state="Target",
                    event_id=None,
                    condition_expr=BinaryOp(
                        expr1=UnaryOp(op="!", expr=Boolean(raw="true")),
                        op="||",
                        expr2=Boolean(raw="false"),
                    ),
                    post_operations=[],
                ),
            ),  # normal transition with keyword logical aliases in guard
            (
                "Source -> Target effect { if [x > 0] { y = 1; } else { y = 2; } }",
                TransitionDefinition(
                    from_state="Source",
                    to_state="Target",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[
                        OperationIf(
                            branches=[
                                OperationIfBranch(
                                    condition=BinaryOp(
                                        expr1=Name(name="x"),
                                        op=">",
                                        expr2=Integer(raw="0"),
                                    ),
                                    statements=[
                                        OperationAssignment(
                                            name="y", expr=Integer(raw="1")
                                        )
                                    ],
                                ),
                                OperationIfBranch(
                                    condition=None,
                                    statements=[
                                        OperationAssignment(
                                            name="y", expr=Integer(raw="2")
                                        )
                                    ],
                                ),
                            ]
                        )
                    ],
                ),
            ),  # transition effect block with if/else statement
            (
                "Source -> [*] : Source.Stop effect { if [flag == 0] { flag = 1; } }",
                TransitionDefinition(
                    from_state="Source",
                    to_state=EXIT_STATE,
                    event_id=ChainID(path=["Source", "Stop"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[
                        OperationIf(
                            branches=[
                                OperationIfBranch(
                                    condition=BinaryOp(
                                        expr1=Name(name="flag"),
                                        op="==",
                                        expr2=Integer(raw="0"),
                                    ),
                                    statements=[
                                        OperationAssignment(
                                            name="flag", expr=Integer(raw="1")
                                        )
                                    ],
                                )
                            ]
                        )
                    ],
                ),
            ),  # exit transition with local event shorthand and single-branch if effect
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert (
            parse_with_grammar_entry(input_text, entry_name="transition_definition")
            == expected
        )

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            ("[*] -> StateA;", "[*] -> StateA;"),  # Basic entry transition to StateA
            (
                "[*] -> StateB: chain1;",
                "[*] -> StateB :: chain1;",
            ),  # Entry transition with chain identifier
            (
                "[*] -> StateC: if [x > 10];",
                "[*] -> StateC : if [x > 10];",
            ),  # Entry transition with condition
            (
                "[*] -> StateD effect { a = 5; }",
                "[*] -> StateD effect {\n    a = 5;\n}",
            ),
            # Entry transition with effect action
            (
                "[*] -> StateF: if [x < 0 && y > 10];",
                "[*] -> StateF : if [x < 0 && y > 10];",
            ),
            # Entry transition with complex condition
            (
                "[*] -> StateG effect { a = sin(b); c = 10; }",
                "[*] -> StateG effect {\n    a = sin(b);\n    c = 10;\n}",
            ),
            # Entry transition with multiple effect actions
            (
                "StateA -> StateB;",
                "StateA -> StateB;",
            ),  # Basic transition from StateA to StateB
            (
                "StateC -> StateD: chain4;",
                "StateC -> StateD : chain4;",
            ),  # Transition with chain identifier
            (
                "StateC -> StateD: StateC.chain4;",
                "StateC -> StateD :: chain4;",
            ),  # Transition with chain identifier
            (
                "StateE -> StateF: if [x <= 20];",
                "StateE -> StateF : if [x <= 20];",
            ),  # Transition with condition
            (
                "StateG -> StateH effect { a = 15; }",
                "StateG -> StateH effect {\n    a = 15;\n}",
            ),
            # Transition with effect action
            (
                "StateK -> StateL: if [x != y && z == 10];",
                "StateK -> StateL : if [x != y && z == 10];",
            ),
            # Transition with complex condition
            (
                "StateM -> StateN effect { a = cos(b); d = 30; }",
                "StateM -> StateN effect {\n    a = cos(b);\n    d = 30;\n}",
            ),  # Transition with multiple effect actions
            ("StateA -> [*];", "StateA -> [*];"),  # Basic exit transition from StateA
            (
                "StateB -> [*]: chain7;",
                "StateB -> [*] : chain7;",
            ),  # Exit transition with chain identifier
            (
                "StateC -> [*]: if [x >= 100];",
                "StateC -> [*] : if [x >= 100];",
            ),  # Exit transition with condition
            (
                "StateD -> [*] effect { a = 50; }",
                "StateD -> [*] effect {\n    a = 50;\n}",
            ),
            # Exit transition with effect action
            (
                "StateF -> [*]: if [x == y || z != 10];",
                "StateF -> [*] : if [x == y || z != 10];",
            ),
            # Exit transition with complex condition
            (
                "StateG -> [*] effect { a = sqrt(b); e = 40; }",
                "StateG -> [*] effect {\n    a = sqrt(b);\n    e = 40;\n}",
            ),
            # Exit transition with multiple effect actions
            (
                """
                A -> B : /XXX;
                """,
                "A -> B : /XXX;",
            ),  # absolute event path
            (
                """
                A -> B : /XXX effect { x = 1; }
                """,
                "A -> B : /XXX effect {\n    x = 1;\n}",
            ),  # absolute event path with effect
            (
                """
                A -> B : /XXX.YYY;
                """,
                "A -> B : /XXX.YYY;",
            ),  # absolute event path with chain
            (
                """
                A -> B : /XXX.YYY.ZZZ effect { x = 1; }
                """,
                "A -> B : /XXX.YYY.ZZZ effect {\n    x = 1;\n}",
            ),  # absolute event path with chain and effect
            (
                "[*] -> Boot : Boot;",
                "[*] -> Boot :: Boot;",
            ),  # entry transition canonicalizes single-segment relative event to local shorthand
            (
                "[*] -> Boot : boot.chain;",
                "[*] -> Boot : boot.chain;",
            ),  # entry transition preserves multi-segment relative event path
            (
                "Source -> Target :: Fire;",
                "Source -> Target :: Fire;",
            ),  # normal transition preserves explicit local-event shorthand
            (
                "Source -> Target : Source.Fire;",
                "Source -> Target :: Fire;",
            ),  # normal transition canonicalizes equivalent relative event path
            (
                "Source -> Target : /Root.Fire;",
                "Source -> Target : /Root.Fire;",
            ),  # normal transition preserves absolute event path
            (
                "Source -> Target : if [not true or false];",
                "Source -> Target : if [!True || False];",
            ),  # guard canonicalizes keyword logical aliases and boolean literals
            (
                "Source -> Target effect { if [x > 0] { y = 1; } else { y = 2; } }",
                "Source -> Target effect {\n    if [x > 0] {\n        y = 1;\n    } else {\n        y = 2;\n    }\n}",
            ),  # transition effect block preserves if/else structure in DSL output
            (
                "Source -> [*] : Source.Stop effect { if [flag == 0] { flag = 1; } }",
                "Source -> [*] :: Stop effect {\n    if [flag == 0] {\n        flag = 1;\n    }\n}",
            ),  # exit transition canonicalizes local event path and preserves nested if effect
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(
                parse_with_grammar_entry(input_text, entry_name="transition_definition")
            ),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            ("StateA -> StateB",),  # Missing semicolon at the end
            # ('[*] -> StateC effect { a = 5; }',),  # Missing semicolon after effect action block
            ("* -> StateA;",),  # Invalid entry state format, should be [*]
            ("StateB -> *;",),  # Invalid exit state format, should be [*]
            ("(StateC) -> StateD;",),  # Invalid state name format with parentheses
            ("StateE => StateF;",),  # Invalid arrow syntax, should be ->
            ("[*] --> StateG;",),  # Invalid arrow syntax, should be ->
            ("StateH >> [*];",),  # Invalid arrow syntax, should be ->
            (
                "StateI -> StateJ: if (x > 10);",
            ),  # Invalid condition syntax, should use square brackets
            ("[*] -> StateK: if x > 10;",),  # Missing square brackets in condition
            ("StateL -> StateM: if [x > 10;",),  # Unclosed square bracket in condition
            ("StateN -> StateO: if [x > 10)",),  # Mismatched brackets in condition
            (
                "StateP -> StateQ effect a = 5;",
            ),  # Missing curly braces in effect action
            (
                "StateR -> StateS effect { a = 5 };",
            ),  # Missing semicolon in effect action assignment
            (
                "StateT -> [*] effect { a = 5; };",
            ),  # Invalid assignment operator in effect action, should be =
            # ('StateU -> StateV: chain.id;',),  # Invalid chain identifier with dot
            ("[*] -> StateW: :if [x > 10];",),  # Missing chain identifier before colon
            ("StateX [*];",),  # Missing arrow in transition
            ("-> StateY;",),  # Missing source state
            ("StateZ ->;",),  # Missing target state
            ("[*] -> StateAA: if [];",),  # Empty condition
            ("StateBB -> StateCC: if [x > 10] effect;",),  # Empty effect action block
            (
                "StateDD -> StateEE effect { a = ; };",
            ),  # Missing expression in effect action
            (
                "[*] -> StateFFA: if x > 10] effect { a = 5; };",
            ),  # Missing opening bracket in condition
            (
                "StateGG -> [*]: chain10: if [x > 10 effect { a = 5; };",
            ),  # Missing closing bracket in condition
            (
                """
                A -> B :: /XXX;
                """,
            ),  # absolute event path with ::, error
            (
                """
                A -> B : / effect { x = 1; }
                """,
            ),  # absolute event path with effect and empty absolute path, error
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name="transition_definition")

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
