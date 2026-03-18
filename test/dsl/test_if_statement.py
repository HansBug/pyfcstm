import pytest

from pyfcstm.dsl import GrammarParseError, parse_with_grammar_entry
from pyfcstm.dsl.node import (
    BinaryOp,
    DefAssignment,
    DuringAspectOperations,
    DuringOperations,
    EnterOperations,
    ExitOperations,
    Integer,
    Name,
    OperationAssignment,
    OperationIf,
    OperationIfBranch,
    StateDefinition,
    StateMachineDSLProgram,
    TransitionDefinition,
    UnaryOp,
)


@pytest.mark.unittest
class TestDSLIfStatementDirect:
    @pytest.mark.parametrize(
        ["entry_name", "input_text", "expected"],
        [
            (
                "if_statement",
                """
                if [x > 0] {
                    y = 1;
                } else if [x == 0] {
                    y = 0;
                } else {
                    y = -1;
                }
                """,
                OperationIf(
                    branches=[
                        OperationIfBranch(
                            condition=BinaryOp(
                                expr1=Name(name="x"),
                                op=">",
                                expr2=Integer(raw="0"),
                            ),
                            statements=[
                                OperationAssignment(name="y", expr=Integer(raw="1"))
                            ],
                        ),
                        OperationIfBranch(
                            condition=BinaryOp(
                                expr1=Name(name="x"),
                                op="==",
                                expr2=Integer(raw="0"),
                            ),
                            statements=[
                                OperationAssignment(name="y", expr=Integer(raw="0"))
                            ],
                        ),
                        OperationIfBranch(
                            condition=None,
                            statements=[
                                OperationAssignment(
                                    name="y",
                                    expr=UnaryOp(op="-", expr=Integer(raw="1")),
                                )
                            ],
                        ),
                    ]
                ),
            ),
            (
                "if_statement",
                """
                if [mode == 0] {
                    if [temp > 80] {
                        level = 3;
                    } else {
                        level = 1;
                    }
                } else {
                    level = 0;
                }
                """,
                OperationIf(
                    branches=[
                        OperationIfBranch(
                            condition=BinaryOp(
                                expr1=Name(name="mode"),
                                op="==",
                                expr2=Integer(raw="0"),
                            ),
                            statements=[
                                OperationIf(
                                    branches=[
                                        OperationIfBranch(
                                            condition=BinaryOp(
                                                expr1=Name(name="temp"),
                                                op=">",
                                                expr2=Integer(raw="80"),
                                            ),
                                            statements=[
                                                OperationAssignment(
                                                    name="level",
                                                    expr=Integer(raw="3"),
                                                )
                                            ],
                                        ),
                                        OperationIfBranch(
                                            condition=None,
                                            statements=[
                                                OperationAssignment(
                                                    name="level",
                                                    expr=Integer(raw="1"),
                                                )
                                            ],
                                        ),
                                    ]
                                )
                            ],
                        ),
                        OperationIfBranch(
                            condition=None,
                            statements=[
                                OperationAssignment(
                                    name="level",
                                    expr=Integer(raw="0"),
                                )
                            ],
                        ),
                    ]
                ),
            ),
            (
                "operation_block",
                """
                {
                    if [x > 0] {
                        y = 1;
                    }
                    z = 2;
                }
                """,
                [
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
                            )
                        ]
                    ),
                    OperationAssignment(name="z", expr=Integer(raw="2")),
                ],
            ),
            (
                "operational_statement_set",
                """
                if [flag > 0] {
                    ;
                    ;
                } else {
                }
                """,
                [
                    OperationIf(
                        branches=[
                            OperationIfBranch(
                                condition=BinaryOp(
                                    expr1=Name(name="flag"),
                                    op=">",
                                    expr2=Integer(raw="0"),
                                ),
                                statements=[],
                            ),
                            OperationIfBranch(condition=None, statements=[]),
                        ]
                    )
                ],
            ),
            (
                "operational_statement_set",
                """
                if [x > 0] {
                    y = 1;
                }
                z = y + 1;
                """,
                [
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
                            )
                        ]
                    ),
                    OperationAssignment(
                        name="z",
                        expr=BinaryOp(
                            expr1=Name(name="y"),
                            op="+",
                            expr2=Integer(raw="1"),
                        ),
                    ),
                ],
            ),
        ],
    )
    def test_positive_cases(self, entry_name, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name=entry_name) == expected

    @pytest.mark.parametrize(
        ["entry_name", "input_text", "expected_str"],
        [
            (
                "if_statement",
                """
                if [x > 0] {
                    y = 1;
                } else if [x == 0] {
                    y = 0;
                } else {
                    y = -1;
                }
                """,
                """if [x > 0] {
    y = 1;
} else if [x == 0] {
    y = 0;
} else {
    y = -1;
}""",
            ),
            (
                "if_statement",
                """
                if [x > 0] {
                    y = 1;
                    if [z > 0] {
                        w = 2;
                    } else {
                        w = 3;
                    }
                } else {
                    y = 0;
                }
                """,
                """if [x > 0] {
    y = 1;
    if [z > 0] {
        w = 2;
    } else {
        w = 3;
    }
} else {
    y = 0;
}""",
            ),
            (
                "if_statement",
                """
                if [x > 0] {
                    y = 1;
                }
                """,
                """if [x > 0] {
    y = 1;
}""",
            ),
            (
                "operational_statement_set",
                """
                if [x > 0] {
                    y = 1;
                } else {
                    y = 0;
                }
                z = 2;
                """,
                """if [x > 0] {
    y = 1;
} else {
    y = 0;
}
z = 2;""",
            ),
        ],
    )
    def test_positive_cases_str(self, entry_name, input_text, expected_str, text_aligner):
        result = parse_with_grammar_entry(input_text, entry_name=entry_name)
        if isinstance(result, list):
            actual = "\n".join(map(str, result))
        else:
            actual = str(result)

        text_aligner.assert_equal(expected_str, actual)

    @pytest.mark.parametrize(
        ["entry_name", "input_text"],
        [
            (
                "operational_statement_set",
                """
                if [x > 0] y = 1;
                """,
            ),
            (
                "operational_statement_set",
                """
                else {
                    y = 1;
                }
                """,
            ),
            (
                "operational_statement_set",
                """
                if [x + 1] {
                    y = 1;
                }
                """,
            ),
            (
                "if_statement",
                """
                if [x > 0] {
                    y = 1;
                } else if [x == 0] {
                    y = 0;
                } else
                """,
            ),
            (
                "operation_block",
                """
                {
                    if [x > 0] {
                        y = 1;
                    }
                """,
            ),
        ],
    )
    def test_negative_cases(self, entry_name, input_text):
        with pytest.raises(GrammarParseError):
            parse_with_grammar_entry(input_text, entry_name=entry_name)


@pytest.mark.unittest
class TestDSLIfStatementIntegration:
    @pytest.mark.parametrize(
        ["entry_name", "input_text", "expected"],
        [
            (
                "enter_definition",
                """
                enter {
                    if [x > 0] {
                        y = 1;
                    } else {
                        y = 0;
                    }
                }
                """,
                EnterOperations(
                    operations=[
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
                                            name="y", expr=Integer(raw="0")
                                        )
                                    ],
                                ),
                            ]
                        )
                    ],
                    name=None,
                ),
            ),
            (
                "during_definition",
                """
                during before {
                    if [x > 0] {
                        y = 1;
                    }
                }
                """,
                DuringOperations(
                    aspect="before",
                    operations=[
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
                                )
                            ]
                        )
                    ],
                    name=None,
                ),
            ),
            (
                "exit_definition",
                """
                exit cleanup {
                    if [x > 0] {
                        y = 1;
                    } else {
                        y = 2;
                    }
                }
                """,
                ExitOperations(
                    operations=[
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
                    name="cleanup",
                ),
            ),
            (
                "during_aspect_definition",
                """
                >> during before {
                    if [x > 0] {
                        y = 1;
                    }
                }
                """,
                DuringAspectOperations(
                    aspect="before",
                    operations=[
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
                                )
                            ]
                        )
                    ],
                    name=None,
                ),
            ),
            (
                "transition_definition",
                """
                A -> B effect {
                    if [x > 0] {
                        y = 1;
                    }
                    z = 2;
                }
                """,
                TransitionDefinition(
                    from_state="A",
                    to_state="B",
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
                                )
                            ]
                        ),
                        OperationAssignment(name="z", expr=Integer(raw="2")),
                    ],
                ),
            ),
            (
                "state_machine_dsl",
                """
                def int x = 0;
                state Root {
                    enter {
                        if [x > 0] {
                            x = 1;
                        } else {
                            x = 2;
                        }
                    }
                }
                """,
                StateMachineDSLProgram(
                    definitions=[
                        DefAssignment(name="x", type="int", expr=Integer(raw="0"))
                    ],
                    root_state=StateDefinition(
                        "Root",
                        enters=[
                            EnterOperations(
                                operations=[
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
                                                        name="x",
                                                        expr=Integer(raw="1"),
                                                    )
                                                ],
                                            ),
                                            OperationIfBranch(
                                                condition=None,
                                                statements=[
                                                    OperationAssignment(
                                                        name="x",
                                                        expr=Integer(raw="2"),
                                                    )
                                                ],
                                            ),
                                        ]
                                    )
                                ],
                                name=None,
                            )
                        ],
                    ),
                ),
            ),
        ],
    )
    def test_positive_cases(self, entry_name, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name=entry_name) == expected

    @pytest.mark.parametrize(
        ["entry_name", "input_text", "expected_str"],
        [
            (
                "enter_definition",
                """
                enter {
                    if [x > 0] {
                        y = 1;
                    } else {
                        y = 0;
                    }
                }
                """,
                """enter {
    if [x > 0] {
        y = 1;
    } else {
        y = 0;
    }
}""",
            ),
            (
                "during_definition",
                """
                during before {
                    if [x > 0] {
                        y = 1;
                    }
                }
                """,
                """during before {
    if [x > 0] {
        y = 1;
    }
}""",
            ),
            (
                "exit_definition",
                """
                exit cleanup {
                    if [x > 0] {
                        y = 1;
                    } else {
                        y = 2;
                    }
                }
                """,
                """exit cleanup {
    if [x > 0] {
        y = 1;
    } else {
        y = 2;
    }
}""",
            ),
            (
                "during_aspect_definition",
                """
                >> during before {
                    if [x > 0] {
                        y = 1;
                    }
                }
                """,
                """>> during before {
    if [x > 0] {
        y = 1;
    }
}""",
            ),
            (
                "transition_definition",
                """
                A -> B effect {
                    if [x > 0] {
                        y = 1;
                    }
                    z = 2;
                }
                """,
                """A -> B effect {
    if [x > 0] {
        y = 1;
    }
    z = 2;
}""",
            ),
            (
                "state_machine_dsl",
                """
                def int x = 0;
                state Root {
                    enter {
                        if [x > 0] {
                            x = 1;
                        } else {
                            x = 2;
                        }
                    }
                }
                """,
                """def int x = 0;
state Root {
    enter {
        if [x > 0] {
            x = 1;
        } else {
            x = 2;
        }
    }
}""",
            ),
        ],
    )
    def test_positive_cases_str(self, entry_name, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expected_str,
            str(parse_with_grammar_entry(input_text, entry_name=entry_name)),
        )

    @pytest.mark.parametrize(
        ["entry_name", "input_text"],
        [
            (
                "enter_definition",
                """
                enter {
                    if [x > 0] y = 1;
                }
                """,
            ),
            (
                "during_definition",
                """
                during {
                    else {
                        y = 1;
                    }
                }
                """,
            ),
            (
                "exit_definition",
                """
                exit {
                    if [x + 1] {
                        y = 1;
                    }
                }
                """,
            ),
            (
                "during_aspect_definition",
                """
                >> during before {
                    if [x > 0] {
                        y = 1;
                    } else if [x == 0] {
                        y = 0;
                    } else
                }
                """,
            ),
            (
                "transition_definition",
                """
                A -> B effect {
                    if [x > 0] {
                        y = 1;
                    }
                };
                """,
            ),
        ],
    )
    def test_negative_cases(self, entry_name, input_text):
        with pytest.raises(GrammarParseError):
            parse_with_grammar_entry(input_text, entry_name=entry_name)
