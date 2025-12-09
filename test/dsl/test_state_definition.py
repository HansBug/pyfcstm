import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLTransition:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                    "state S1;",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Simple leaf state definition
            (
                    "state Running;",
                    StateDefinition(
                        name="Running",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Leaf state with descriptive name
            (
                    "state IDLE;",
                    StateDefinition(
                        name="IDLE",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Leaf state with uppercase name
            (
                    "state s_2;",
                    StateDefinition(
                        name="s_2",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Leaf state with underscore in name
            (
                    "state waiting_for_input;",
                    StateDefinition(
                        name="waiting_for_input",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Leaf state with multiple underscores
            (
                    "state Complex { }",
                    StateDefinition(
                        name="Complex",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with empty body
            (
                    "state Parent { }",
                    StateDefinition(
                        name="Parent",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state named Parent with empty body
            (
                    "state S1 { state S2; }",
                    StateDefinition(
                        name="S1",
                        substates=[
                            StateDefinition(
                                name="S2",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            )
                        ],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),  # Composite state containing a leaf state
            (
                    "state Parent { state Child1; state Child2; }",
                    StateDefinition(
                        name="Parent",
                        substates=[
                            StateDefinition(
                                name="Child1",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            ),
                            StateDefinition(
                                name="Child2",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            ),
                        ],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with multiple leaf states
            (
                    "state S1 { state S2 { state S3; } }",
                    StateDefinition(
                        name="S1",
                        substates=[
                            StateDefinition(
                                name="S2",
                                substates=[
                                    StateDefinition(
                                        name="S3",
                                        substates=[],
                                        transitions=[],
                                        enters=[],
                                        durings=[],
                                        exits=[],
                                    )
                                ],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            )
                        ],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with nested composite state
            (
                    "state Machine { state Running { state Fast; state Slow; } }",
                    StateDefinition(
                        name="Machine",
                        substates=[
                            StateDefinition(
                                name="Running",
                                substates=[
                                    StateDefinition(
                                        name="Fast",
                                        substates=[],
                                        transitions=[],
                                        enters=[],
                                        durings=[],
                                        exits=[],
                                    ),
                                    StateDefinition(
                                        name="Slow",
                                        substates=[],
                                        transitions=[],
                                        enters=[],
                                        durings=[],
                                        exits=[],
                                    ),
                                ],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            )
                        ],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with nested composite state containing multiple leaf states
            (
                    "state S1 { [*] -> S2; }",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state=INIT_STATE,
                                to_state="S2",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with entry transition
            (
                    "state S1 { S2 -> S3; }",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with normal transition
            (
                    "state S1 { S2 -> [*]; }",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state=EXIT_STATE,
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with exit transition
            (
                    "state S1 { S2 -> S3: chain.id; }",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=ChainID(path=["chain", "id"]),
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with transition having chain ID
            (
                    "state S1 { [*] -> S2: entry.chain; }",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state=INIT_STATE,
                                to_state="S2",
                                event_id=ChainID(path=["entry", "chain"]),
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with entry transition having chain ID
            (
                    "state S1 { S2 -> S3: if [x > 5]; }",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=BinaryOp(
                                    expr1=Name(name="x"), op=">", expr2=Integer(raw="5")
                                ),
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with conditional transition
            (
                    "state S1 { S2 -> S3: if [x == 10 && y < 20]; }",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=BinaryOp(
                                    expr1=BinaryOp(
                                        expr1=Name(name="x"),
                                        op="==",
                                        expr2=Integer(raw="10"),
                                    ),
                                    op="&&",
                                    expr2=BinaryOp(
                                        expr1=Name(name="y"),
                                        op="<",
                                        expr2=Integer(raw="20"),
                                    ),
                                ),
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with complex conditional transition
            (
                    "state S1 { S2 -> S3 effect { x = 10; } }",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[
                                    OperationAssignment(name="x", expr=Integer(raw="10"))
                                ],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with effect-transition operation
            (
                    "state S1 { S2 -> S3 effect { x = 10; y = 20; } }",
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[
                                    OperationAssignment(name="x", expr=Integer(raw="10")),
                                    OperationAssignment(name="y", expr=Integer(raw="20")),
                                ],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with multiple effect-transition operations
            (
                    "state S1 { state S2; S2 -> S3: if [x > 5]; S3 -> [*]; }",
                    StateDefinition(
                        name="S1",
                        substates=[
                            StateDefinition(
                                name="S2",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            )
                        ],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=BinaryOp(
                                    expr1=Name(name="x"), op=">", expr2=Integer(raw="5")
                                ),
                                post_operations=[],
                            ),
                            TransitionDefinition(
                                from_state="S3",
                                to_state=EXIT_STATE,
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            ),
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with leaf state and transitions
            (
                    "state Machine { state Off; state On { state Idle; state Running; } Off -> On: if [power == 1]; On -> Off: if [power == 0]; }",
                    StateDefinition(
                        name="Machine",
                        substates=[
                            StateDefinition(
                                name="Off",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            ),
                            StateDefinition(
                                name="On",
                                substates=[
                                    StateDefinition(
                                        name="Idle",
                                        substates=[],
                                        transitions=[],
                                        enters=[],
                                        durings=[],
                                        exits=[],
                                    ),
                                    StateDefinition(
                                        name="Running",
                                        substates=[],
                                        transitions=[],
                                        enters=[],
                                        durings=[],
                                        exits=[],
                                    ),
                                ],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            ),
                        ],
                        transitions=[
                            TransitionDefinition(
                                from_state="Off",
                                to_state="On",
                                event_id=None,
                                condition_expr=BinaryOp(
                                    expr1=Name(name="power"),
                                    op="==",
                                    expr2=Integer(raw="1"),
                                ),
                                post_operations=[],
                            ),
                            TransitionDefinition(
                                from_state="On",
                                to_state="Off",
                                event_id=None,
                                condition_expr=BinaryOp(
                                    expr1=Name(name="power"),
                                    op="==",
                                    expr2=Integer(raw="0"),
                                ),
                                post_operations=[],
                            ),
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Complex state machine with nested states and transitions
            (
                    "state S1 { state S2; state S3; S2 -> S3: if [x > 5] effect { x = 10; }; S3 -> [*]; }",
                    StateDefinition(
                        name="S1",
                        substates=[
                            StateDefinition(
                                name="S2",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            ),
                            StateDefinition(
                                name="S3",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            ),
                        ],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=BinaryOp(
                                    expr1=Name(name="x"), op=">", expr2=Integer(raw="5")
                                ),
                                post_operations=[
                                    OperationAssignment(name="x", expr=Integer(raw="10"))
                                ],
                            ),
                            TransitionDefinition(
                                from_state="S3",
                                to_state=EXIT_STATE,
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            ),
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with states, conditional transition with effect operations
            (
                    "state S1 { ; state S2; ; S2 -> S3; ; }",
                    StateDefinition(
                        name="S1",
                        substates=[
                            StateDefinition(
                                name="S2",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            )
                        ],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
            ),
            # Composite state with empty statements between valid statements
            (
                    """
                    state X {
                        >> during after X {
                            y = 0;
                        }
                        >> during before {
                            x = 1;
                            y = x + 1;
                        }
                        >> during after abstract T;
                        >> during before abstract TF /* this is a line */
                    }
                    """,
                    StateDefinition(
                        name="X",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[
                            DuringAspectOperations(
                                aspect="after",
                                operations=[
                                    OperationAssignment(name="y", expr=Integer(raw="0"))
                                ],
                                name="X",
                            ),
                            DuringAspectOperations(
                                aspect="before",
                                operations=[
                                    OperationAssignment(name="x", expr=Integer(raw="1")),
                                    OperationAssignment(
                                        name="y",
                                        expr=BinaryOp(
                                            expr1=Name(name="x"),
                                            op="+",
                                            expr2=Integer(raw="1"),
                                        ),
                                    ),
                                ],
                                name=None,
                            ),
                            DuringAspectAbstractFunction(
                                name="T", aspect="after", doc=None
                            ),
                            DuringAspectAbstractFunction(
                                name="TF", aspect="before", doc="this is a line"
                            ),
                        ],
                    ),
            ),  # test for during aspects
            (
                    """
                    pseudo state SimpleState;
                    """,
                    StateDefinition(
                        name="SimpleState",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Basic pseudo leaf state definition
            (
                    """
                    pseudo state ComplexState { }
                    """,
                    StateDefinition(
                        name="ComplexState",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Basic pseudo composite state with empty body
            (
                    """
                    pseudo state ParentState { pseudo state ChildState; }
                    """,
                    StateDefinition(
                        name="ParentState",
                        substates=[
                            StateDefinition(
                                name="ChildState",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=True,
                            )
                        ],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo composite state containing pseudo leaf state
            (
                    """
                    pseudo state S1 { [*] -> S2; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state=INIT_STATE,
                                to_state="S2",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with entry transition
            (
                    """
                    pseudo state S1 { S2 -> S3; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with normal transition
            (
                    """
                    pseudo state S1 { S2 -> [*]; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state=EXIT_STATE,
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with exit transition
            (
                    """
                    pseudo state S1 { S2 -> S3: chain.id; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=ChainID(path=["chain", "id"], is_absolute=False),
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with transition having chain ID
            (
                    """
                    pseudo state S1 { S2 -> S3: if [x > 5]; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=BinaryOp(
                                    expr1=Name(name="x"), op=">", expr2=Integer(raw="5")
                                ),
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with conditional transition
            (
                    """
                    pseudo state S1 { ! S2 -> S3; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[
                            ForceTransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=None,
                            )
                        ],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with normal force transition
            (
                    """
                    pseudo state S1 { ! S2 -> [*]; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[
                            ForceTransitionDefinition(
                                from_state="S2",
                                to_state=EXIT_STATE,
                                event_id=None,
                                condition_expr=None,
                            )
                        ],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with exit force transition
            (
                    """
                    pseudo state S1 { ! * -> S3; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[
                            ForceTransitionDefinition(
                                from_state=ALL,
                                to_state="S3",
                                event_id=None,
                                condition_expr=None,
                            )
                        ],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with normal all force transition
            (
                    """
                    pseudo state S1 { ! * -> [*]; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[
                            ForceTransitionDefinition(
                                from_state=ALL,
                                to_state=EXIT_STATE,
                                event_id=None,
                                condition_expr=None,
                            )
                        ],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with exit all force transition
            (
                    """
                    pseudo state S1 { enter { x = 10; } }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[
                            EnterOperations(
                                operations=[
                                    OperationAssignment(name="x", expr=Integer(raw="10"))
                                ],
                                name=None,
                            )
                        ],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with enter operations
            (
                    """
                    pseudo state S1 { exit { y = 20; } }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[
                            ExitOperations(
                                operations=[
                                    OperationAssignment(name="y", expr=Integer(raw="20"))
                                ],
                                name=None,
                            )
                        ],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with exit operations
            (
                    """
                    pseudo state S1 { during { z = 30; } }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[
                            DuringOperations(
                                aspect=None,
                                operations=[
                                    OperationAssignment(name="z", expr=Integer(raw="30"))
                                ],
                                name=None,
                            )
                        ],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with during operations
            (
                    """
                    pseudo state S1 { enter abstract func1; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[EnterAbstractFunction(name="func1", doc=None)],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with abstract enter function
            (
                    """
                    pseudo state S1 { exit abstract func2; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[ExitAbstractFunction(name="func2", doc=None)],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with abstract exit function
            (
                    """
                    pseudo state S1 { during abstract func3; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[
                            DuringAbstractFunction(name="func3", aspect=None, doc=None)
                        ],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with abstract during function
            (
                    """
                    pseudo state S1 { >> during before { x = 1; } }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[
                            DuringAspectOperations(
                                aspect="before",
                                operations=[
                                    OperationAssignment(name="x", expr=Integer(raw="1"))
                                ],
                                name=None,
                            )
                        ],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with before during aspect
            (
                    """
                    pseudo state S1 { >> during after { y = 2; } }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[
                            DuringAspectOperations(
                                aspect="after",
                                operations=[
                                    OperationAssignment(name="y", expr=Integer(raw="2"))
                                ],
                                name=None,
                            )
                        ],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with after during aspect
            (
                    """
                    pseudo state S1 { >> during before abstract aspectFunc; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[
                            DuringAspectAbstractFunction(
                                name="aspectFunc", aspect="before", doc=None
                            )
                        ],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with abstract before during aspect
            (
                    """
                    pseudo state S1 { >> during after abstract aspectFunc; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[
                            DuringAspectAbstractFunction(
                                name="aspectFunc", aspect="after", doc=None
                            )
                        ],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with abstract after during aspect
            (
                    """
                    pseudo state Machine { pseudo state Running; pseudo state Idle; Running -> Idle: if [power == 0]; }
                    """,
                    StateDefinition(
                        name="Machine",
                        substates=[
                            StateDefinition(
                                name="Running",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=True,
                            ),
                            StateDefinition(
                                name="Idle",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=True,
                            ),
                        ],
                        transitions=[
                            TransitionDefinition(
                                from_state="Running",
                                to_state="Idle",
                                event_id=None,
                                condition_expr=BinaryOp(
                                    expr1=Name(name="power"),
                                    op="==",
                                    expr2=Integer(raw="0"),
                                ),
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Complex pseudo state with nested pseudo states and transitions
            (
                    """
                    pseudo state S1 { pseudo state S2; S2 -> S3: if [x > 5] effect { x = 10; }; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[
                            StateDefinition(
                                name="S2",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=True,
                            )
                        ],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=BinaryOp(
                                    expr1=Name(name="x"), op=">", expr2=Integer(raw="5")
                                ),
                                post_operations=[
                                    OperationAssignment(name="x", expr=Integer(raw="10"))
                                ],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with nested pseudo state and transition with effect
            (
                    """
                    pseudo state Parent { pseudo state Child1 { enter { init = 1; } } pseudo state Child2 { exit { cleanup = 1; } } }
                    """,
                    StateDefinition(
                        name="Parent",
                        substates=[
                            StateDefinition(
                                name="Child1",
                                substates=[],
                                transitions=[],
                                enters=[
                                    EnterOperations(
                                        operations=[
                                            OperationAssignment(
                                                name="init", expr=Integer(raw="1")
                                            )
                                        ],
                                        name=None,
                                    )
                                ],
                                durings=[],
                                exits=[],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=True,
                            ),
                            StateDefinition(
                                name="Child2",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[
                                    ExitOperations(
                                        operations=[
                                            OperationAssignment(
                                                name="cleanup", expr=Integer(raw="1")
                                            )
                                        ],
                                        name=None,
                                    )
                                ],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=True,
                            ),
                        ],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with nested pseudo states having enter/exit operations
            (
                    """
                    pseudo state S1 { state NormalChild; pseudo state PseudoChild; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[
                            StateDefinition(
                                name="NormalChild",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=False,
                            ),
                            StateDefinition(
                                name="PseudoChild",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=True,
                            ),
                        ],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state containing both normal and pseudo child states
            (
                    """
                    pseudo state S1 { state S2; pseudo state S3; S2 -> S3; S3 -> S2; }
                    """,
                    StateDefinition(
                        name="S1",
                        substates=[
                            StateDefinition(
                                name="S2",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=False,
                            ),
                            StateDefinition(
                                name="S3",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                                during_aspects=[],
                                force_transitions=[],
                                is_pseudo=True,
                            ),
                        ],
                        transitions=[
                            TransitionDefinition(
                                from_state="S2",
                                to_state="S3",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            ),
                            TransitionDefinition(
                                from_state="S3",
                                to_state="S2",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            ),
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                        during_aspects=[],
                        force_transitions=[],
                        is_pseudo=True,
                    ),
            ),  # Pseudo state with mixed child states and bidirectional transitions

            (
                    """
                    state idle named "Idle State";
                    """,
                    StateDefinition(name='idle', extra_name='Idle State', substates=[], transitions=[], enters=[],
                                    durings=[], exits=[], during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Basic leaf state with named string
            (
                    """
                    state idle named 'Idle State';
                    """,
                    StateDefinition(name='idle', extra_name='Idle State', substates=[], transitions=[], enters=[],
                                    durings=[], exits=[], during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Basic leaf state with named string with single quota
            (
                    """
                    state running named "Running State";
                    """,
                    StateDefinition(name='running', extra_name='Running State', substates=[], transitions=[], enters=[],
                                    durings=[], exits=[], during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Simple leaf state with descriptive name
            (
                    """
                    pseudo state error named "Error State";
                    """,
                    StateDefinition(name='error', extra_name='Error State', substates=[], transitions=[], enters=[],
                                    durings=[], exits=[], during_aspects=[], force_transitions=[], is_pseudo=True)
            ),  # Pseudo leaf state with named keyword
            (
                    """
                    state main named "Main State" {}
                    """,
                    StateDefinition(name='main', extra_name='Main State', substates=[], transitions=[], enters=[],
                                    durings=[], exits=[], during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Empty composite state with named keyword
            (
                    """
                    pseudo state container named "Container State" {}
                    """,
                    StateDefinition(name='container', extra_name='Container State', substates=[], transitions=[],
                                    enters=[], durings=[], exits=[], during_aspects=[], force_transitions=[],
                                    is_pseudo=True)
            ),  # Pseudo composite state with named keyword
            (
                    """
                    state parent named "Parent State" { state child named "Child State"; }
                    """,
                    StateDefinition(name='parent', extra_name='Parent State', substates=[
                        StateDefinition(name='child', extra_name='Child State', substates=[], transitions=[], enters=[],
                                        durings=[], exits=[], during_aspects=[], force_transitions=[],
                                        is_pseudo=False)], transitions=[], enters=[], durings=[], exits=[],
                                    during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Composite state with nested leaf state
            (
                    """
                    state machine named "State Machine" { ; }
                    """,
                    StateDefinition(name='machine', extra_name='State Machine', substates=[], transitions=[], enters=[],
                                    durings=[], exits=[], during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Composite state with empty statement
            (
                    """
                    state complex named "Complex State" { state sub1 named "Sub State 1"; state sub2 named "Sub State 2"; }
                    """,
                    StateDefinition(name='complex', extra_name='Complex State', substates=[
                        StateDefinition(name='sub1', extra_name='Sub State 1', substates=[], transitions=[], enters=[],
                                        durings=[], exits=[], during_aspects=[], force_transitions=[], is_pseudo=False),
                        StateDefinition(name='sub2', extra_name='Sub State 2', substates=[], transitions=[], enters=[],
                                        durings=[], exits=[], during_aspects=[], force_transitions=[],
                                        is_pseudo=False)], transitions=[], enters=[], durings=[], exits=[],
                                    during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Composite state with multiple nested states
            (
                    """
                    state active named "Active State" { [*] -> ready; }
                    """,
                    StateDefinition(name='active', extra_name='Active State', substates=[], transitions=[
                        TransitionDefinition(from_state=INIT_STATE, to_state='ready', event_id=None,
                                             condition_expr=None, post_operations=[])], enters=[], durings=[], exits=[],
                                    during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Composite state with entry transition
            (
                    """
                    state workflow named "Workflow State" { state1 -> state2; }
                    """,
                    StateDefinition(name='workflow', extra_name='Workflow State', substates=[], transitions=[
                        TransitionDefinition(from_state='state1', to_state='state2', event_id=None, condition_expr=None,
                                             post_operations=[])], enters=[], durings=[], exits=[], during_aspects=[],
                                    force_transitions=[], is_pseudo=False)
            ),  # Composite state with normal transition
            (
                    """
                    state managed named "Managed State" { enter { x = 1; }; }
                    """,
                    StateDefinition(name='managed', extra_name='Managed State', substates=[], transitions=[], enters=[
                        EnterOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='1'))], name=None)],
                                    durings=[], exits=[], during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Composite state with enter operation
            (
                    """
                    state controlled named "Controlled State" { exit abstract cleanup; }
                    """,
                    StateDefinition(name='controlled', extra_name='Controlled State', substates=[], transitions=[],
                                    enters=[], durings=[], exits=[ExitAbstractFunction(name='cleanup', doc=None)],
                                    during_aspects=[], force_transitions=[], is_pseudo=False)
            ),  # Composite state with abstract exit function
            (
                    """
                    state outer named "Outer State" { state inner named "Inner State" { state deep named "Deep State"; } }
                    """,
                    StateDefinition(name='outer', extra_name='Outer State', substates=[
                        StateDefinition(name='inner', extra_name='Inner State', substates=[
                            StateDefinition(name='deep', extra_name='Deep State', substates=[], transitions=[],
                                            enters=[], durings=[], exits=[], during_aspects=[], force_transitions=[],
                                            is_pseudo=False)], transitions=[], enters=[], durings=[], exits=[],
                                        during_aspects=[], force_transitions=[], is_pseudo=False)], transitions=[],
                                    enters=[], durings=[], exits=[], during_aspects=[], force_transitions=[],
                                    is_pseudo=False)
            ),  # Deeply nested composite states
            (
                    """
                    pseudo state root named "Root State" { state branch1 named "Branch 1" {} state branch2 named "Branch 2" {} }
                    """,
                    StateDefinition(name='root', extra_name='Root State', substates=[
                        StateDefinition(name='branch1', extra_name='Branch 1', substates=[], transitions=[], enters=[],
                                        durings=[], exits=[], during_aspects=[], force_transitions=[], is_pseudo=False),
                        StateDefinition(name='branch2', extra_name='Branch 2', substates=[], transitions=[], enters=[],
                                        durings=[], exits=[], during_aspects=[], force_transitions=[],
                                        is_pseudo=False)], transitions=[], enters=[], durings=[], exits=[],
                                    during_aspects=[], force_transitions=[], is_pseudo=True)
            ),  # Pseudo state with multiple composite children
            (
                    """
                    state system named "System State" { state init named "Init"; [*] -> init; }
                    """,
                    StateDefinition(name='system', extra_name='System State', substates=[
                        StateDefinition(name='init', extra_name='Init', substates=[], transitions=[], enters=[],
                                        durings=[], exits=[], during_aspects=[], force_transitions=[],
                                        is_pseudo=False)], transitions=[
                        TransitionDefinition(from_state=INIT_STATE, to_state='init', event_id=None, condition_expr=None,
                                             post_operations=[])], enters=[], durings=[], exits=[], during_aspects=[],
                                    force_transitions=[], is_pseudo=False)
            ),  # Composite state with nested state and transition
            (
                    """
                    state handler named "Handler State" { during { y = 2; }; state process named "Process"; }
                    """,
                    StateDefinition(name='handler', extra_name='Handler State', substates=[
                        StateDefinition(name='process', extra_name='Process', substates=[], transitions=[], enters=[],
                                        durings=[], exits=[], during_aspects=[], force_transitions=[],
                                        is_pseudo=False)], transitions=[], enters=[], durings=[
                        DuringOperations(aspect=None, operations=[OperationAssignment(name='y', expr=Integer(raw='2'))],
                                         name=None)], exits=[], during_aspects=[], force_transitions=[],
                                    is_pseudo=False)
            ),  # Composite state with during operation and nested state

            (
                    """
                    state MainState {
                        event ButtonClick;
                    }
                    """,
                    StateDefinition(name='MainState', extra_name=None,
                                    events=[EventDefinition(name='ButtonClick', extra_name=None)], substates=[],
                                    transitions=[], enters=[], durings=[], exits=[], during_aspects=[],
                                    force_transitions=[], is_pseudo=False)
            ),  # Basic composite state with simple event definition
            (
                    """
                    state ProcessingState {
                        event DataReceived named "Data Reception Event";
                    }
                    """,
                    StateDefinition(name='ProcessingState', extra_name=None,
                                    events=[EventDefinition(name='DataReceived', extra_name='Data Reception Event')],
                                    substates=[], transitions=[], enters=[], durings=[], exits=[], during_aspects=[],
                                    force_transitions=[], is_pseudo=False)
            ),  # Composite state with named event definition
            (
                    """
                    pseudo state ControllerState {
                        event StartEvent;
                        event StopEvent named "Stop Operation";
                        event ResetEvent named "System Reset";
                    }
                    """,
                    StateDefinition(name='ControllerState', extra_name=None,
                                    events=[EventDefinition(name='StartEvent', extra_name=None),
                                            EventDefinition(name='StopEvent', extra_name='Stop Operation'),
                                            EventDefinition(name='ResetEvent', extra_name='System Reset')],
                                    substates=[], transitions=[], enters=[], durings=[], exits=[], during_aspects=[],
                                    force_transitions=[], is_pseudo=True)
            ),  # Pseudo composite state with multiple events, mixed named usage
            (
                    """
                    state WorkflowState named "Main Workflow" {
                        event ProcessComplete named "Processing Completed";
                        state SubState;
                        event ErrorOccurred;
                        enter { x = 10; }
                    }
                    """,
                    StateDefinition(name='WorkflowState', extra_name='Main Workflow',
                                    events=[EventDefinition(name='ProcessComplete', extra_name='Processing Completed'),
                                            EventDefinition(name='ErrorOccurred', extra_name=None)], substates=[
                            StateDefinition(name='SubState', extra_name=None, events=[], substates=[], transitions=[],
                                            enters=[], durings=[], exits=[], during_aspects=[], force_transitions=[],
                                            is_pseudo=False)], transitions=[], enters=[
                            EnterOperations(operations=[OperationAssignment(name='x', expr=Integer(raw='10'))],
                                            name=None)], durings=[], exits=[], during_aspects=[], force_transitions=[],
                                    is_pseudo=False)
            ),  # Complex composite state with events, substates, and enter definition
            (
                    """
                    pseudo state AlertState named 'Alert Handler' {
                        event WarningTriggered named 'Warning Event';
                    }
                    """,
                    StateDefinition(name='AlertState', extra_name='Alert Handler',
                                    events=[EventDefinition(name='WarningTriggered', extra_name='Warning Event')],
                                    substates=[], transitions=[], enters=[], durings=[], exits=[], during_aspects=[],
                                    force_transitions=[], is_pseudo=True)
            ),  # Pseudo state with event using single quotes in named clause
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name="state_definition") == expected

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            ("state S1;", "state S1;"),  # Simple leaf state definition
            ("state Running;", "state Running;"),  # Leaf state with descriptive name
            ("state IDLE;", "state IDLE;"),  # Leaf state with uppercase name
            ("state s_2;", "state s_2;"),  # Leaf state with underscore in name
            (
                    "state waiting_for_input;",
                    "state waiting_for_input;",
            ),  # Leaf state with multiple underscores
            ("state Complex { }", "state Complex;"),  # Composite state with empty body
            (
                    "state Parent { }",
                    "state Parent;",
            ),  # Composite state named Parent with empty body
            (
                    "state S1 { state S2; }",
                    "state S1 {\n    state S2;\n}",
            ),  # Composite state containing a leaf state
            (
                    "state Parent { state Child1; state Child2; }",
                    "state Parent {\n    state Child1;\n    state Child2;\n}",
            ),
            # Composite state with multiple leaf states
            (
                    "state S1 { state S2 { state S3; } }",
                    "state S1 {\n    state S2 {\n        state S3;\n    }\n}",
            ),
            # Composite state with nested composite state
            (
                    "state Machine { state Running { state Fast; state Slow; } }",
                    "state Machine {\n    state Running {\n        state Fast;\n        state Slow;\n    }\n}",
            ),
            # Composite state with nested composite state containing multiple leaf states
            (
                    "state S1 { [*] -> S2; }",
                    "state S1 {\n    [*] -> S2;\n}",
            ),  # Composite state with entry transition
            (
                    "state S1 { S2 -> S3; }",
                    "state S1 {\n    S2 -> S3;\n}",
            ),  # Composite state with normal transition
            (
                    "state S1 { S2 -> [*]; }",
                    "state S1 {\n    S2 -> [*];\n}",
            ),  # Composite state with exit transition
            (
                    "state S1 { S2 -> S3: chain.id; }",
                    "state S1 {\n    S2 -> S3 : chain.id;\n}",
            ),
            # Composite state with transition having chain ID
            (
                    "state S1 { [*] -> S2: entry.chain; }",
                    "state S1 {\n    [*] -> S2 : entry.chain;\n}",
            ),
            # Composite state with entry transition having chain ID
            (
                    "state S1 { S2 -> S3: if [x > 5]; }",
                    "state S1 {\n    S2 -> S3 : if [x > 5];\n}",
            ),
            # Composite state with conditional transition
            (
                    "state S1 { S2 -> S3: if [x == 10 && y < 20]; }",
                    "state S1 {\n    S2 -> S3 : if [x == 10 && y < 20];\n}",
            ),
            # Composite state with complex conditional transition
            (
                    "state S1 { S2 -> S3 effect { x = 10; } }",
                    "state S1 {\n    S2 -> S3 effect {\n        x = 10;\n    }\n}",
            ),
            # Composite state with effect-transition operation
            (
                    "state S1 { S2 -> S3 effect { x = 10; y = 20; } }",
                    "state S1 {\n    S2 -> S3 effect {\n        x = 10;\n        y = 20;\n    }\n}",
            ),
            # Composite state with multiple effect-transition operations
            (
                    "state S1 { state S2; S2 -> S3: if [x > 5]; S3 -> [*]; }",
                    "state S1 {\n    state S2;\n    S2 -> S3 : if [x > 5];\n    S3 -> [*];\n}",
            ),
            # Composite state with leaf state and transitions
            (
                    "state Machine { state Off; state On { state Idle; state Running; } Off -> On: if [power == 1]; On -> Off: if [power == 0]; }",
                    "state Machine {\n    state Off;\n    state On {\n        state Idle;\n        state Running;\n    }\n    Off -> On : if [power == 1];\n    On -> Off : if [power == 0];\n}",
            ),
            # Complex state machine with nested states and transitions
            (
                    "state S1 { state S2; state S3; S2 -> S3: if [x > 5] effect { x = 10; }; S3 -> [*]; }",
                    "state S1 {\n    state S2;\n    state S3;\n    S2 -> S3 : if [x > 5] effect {\n        x = 10;\n    }\n    S3 -> [*];\n}",
            ),
            # Composite state with states, conditional transition with effect operations
            (
                    "state S1 { ; state S2; ; S2 -> S3; ; }",
                    "state S1 {\n    state S2;\n    S2 -> S3;\n}",
            ),
            # Composite state with empty statements between valid statements
            (
                    """
                    state X {
                        >> during after X {
                            y = 0;
                        }
                        >> during before {
                            x = 1;
                            y = x + 1;
                        }
                        >> during after abstract T;
                        >> during before abstract TF /* this is a line */
                    }
                    """,
                    "state X {\n    >> during after X {\n        y = 0;\n    }\n    >> during before {\n        x = 1;\n        y = x + 1;\n    }\n    >> during after abstract T;\n    >> during before abstract TF /*\n        this is a line\n    */\n}",
            ),  # test for during aspects
            (
                    """
                    pseudo state SimpleState;
                    """,
                    "pseudo state SimpleState;",
            ),  # Basic pseudo leaf state definition
            (
                    """
                    pseudo state ComplexState { }
                    """,
                    "pseudo state ComplexState;",
            ),  # Basic pseudo composite state with empty body
            (
                    """
                    pseudo state ParentState { pseudo state ChildState; }
                    """,
                    "pseudo state ParentState {\n    pseudo state ChildState;\n}",
            ),  # Pseudo composite state containing pseudo leaf state
            (
                    """
                    pseudo state S1 { [*] -> S2; }
                    """,
                    "pseudo state S1 {\n    [*] -> S2;\n}",
            ),  # Pseudo state with entry transition
            (
                    """
                    pseudo state S1 { S2 -> S3; }
                    """,
                    "pseudo state S1 {\n    S2 -> S3;\n}",
            ),  # Pseudo state with normal transition
            (
                    """
                    pseudo state S1 { S2 -> [*]; }
                    """,
                    "pseudo state S1 {\n    S2 -> [*];\n}",
            ),  # Pseudo state with exit transition
            (
                    """
                    pseudo state S1 { S2 -> S3: chain.id; }
                    """,
                    "pseudo state S1 {\n    S2 -> S3 : chain.id;\n}",
            ),  # Pseudo state with transition having chain ID
            (
                    """
                    pseudo state S1 { S2 -> S3: if [x > 5]; }
                    """,
                    "pseudo state S1 {\n    S2 -> S3 : if [x > 5];\n}",
            ),  # Pseudo state with conditional transition
            (
                    """
                    pseudo state S1 { ! S2 -> S3; }
                    """,
                    "pseudo state S1;",
            ),  # Pseudo state with normal force transition
            (
                    """
                    pseudo state S1 { ! S2 -> [*]; }
                    """,
                    "pseudo state S1;",
            ),  # Pseudo state with exit force transition
            (
                    """
                    pseudo state S1 { ! * -> S3; }
                    """,
                    "pseudo state S1;",
            ),  # Pseudo state with normal all force transition
            (
                    """
                    pseudo state S1 { ! * -> [*]; }
                    """,
                    "pseudo state S1;",
            ),  # Pseudo state with exit all force transition
            (
                    """
                    pseudo state S1 { enter { x = 10; } }
                    """,
                    "pseudo state S1 {\n    enter {\n        x = 10;\n    }\n}",
            ),  # Pseudo state with enter operations
            (
                    """
                    pseudo state S1 { exit { y = 20; } }
                    """,
                    "pseudo state S1 {\n    exit {\n        y = 20;\n    }\n}",
            ),  # Pseudo state with exit operations
            (
                    """
                    pseudo state S1 { during { z = 30; } }
                    """,
                    "pseudo state S1 {\n    during {\n        z = 30;\n    }\n}",
            ),  # Pseudo state with during operations
            (
                    """
                    pseudo state S1 { enter abstract func1; }
                    """,
                    "pseudo state S1 {\n    enter abstract func1;\n}",
            ),  # Pseudo state with abstract enter function
            (
                    """
                    pseudo state S1 { exit abstract func2; }
                    """,
                    "pseudo state S1 {\n    exit abstract func2;\n}",
            ),  # Pseudo state with abstract exit function
            (
                    """
                    pseudo state S1 { during abstract func3; }
                    """,
                    "pseudo state S1 {\n    during abstract func3;\n}",
            ),  # Pseudo state with abstract during function
            (
                    """
                    pseudo state S1 { >> during before { x = 1; } }
                    """,
                    "pseudo state S1 {\n    >> during before {\n        x = 1;\n    }\n}",
            ),  # Pseudo state with before during aspect
            (
                    """
                    pseudo state S1 { >> during after { y = 2; } }
                    """,
                    "pseudo state S1 {\n    >> during after {\n        y = 2;\n    }\n}",
            ),  # Pseudo state with after during aspect
            (
                    """
                    pseudo state S1 { >> during before abstract aspectFunc; }
                    """,
                    "pseudo state S1 {\n    >> during before abstract aspectFunc;\n}",
            ),  # Pseudo state with abstract before during aspect
            (
                    """
                    pseudo state S1 { >> during after abstract aspectFunc; }
                    """,
                    "pseudo state S1 {\n    >> during after abstract aspectFunc;\n}",
            ),  # Pseudo state with abstract after during aspect
            (
                    """
                    pseudo state Machine { pseudo state Running; pseudo state Idle; Running -> Idle: if [power == 0]; }
                    """,
                    "pseudo state Machine {\n    pseudo state Running;\n    pseudo state Idle;\n    Running -> Idle : if [power == 0];\n}",
            ),  # Complex pseudo state with nested pseudo states and transitions
            (
                    """
                    pseudo state S1 { pseudo state S2; S2 -> S3: if [x > 5] effect { x = 10; }; }
                    """,
                    "pseudo state S1 {\n    pseudo state S2;\n    S2 -> S3 : if [x > 5] effect {\n        x = 10;\n    }\n}",
            ),  # Pseudo state with nested pseudo state and transition with effect
            (
                    """
                    pseudo state Parent { pseudo state Child1 { enter { init = 1; } } pseudo state Child2 { exit { cleanup = 1; } } }
                    """,
                    "pseudo state Parent {\n    pseudo state Child1 {\n        enter {\n            init = 1;\n        }\n    }\n    pseudo state Child2 {\n        exit {\n            cleanup = 1;\n        }\n    }\n}",
            ),  # Pseudo state with nested pseudo states having enter/exit operations
            (
                    """
                    pseudo state S1 { state NormalChild; pseudo state PseudoChild; }
                    """,
                    "pseudo state S1 {\n    state NormalChild;\n    pseudo state PseudoChild;\n}",
            ),  # Pseudo state containing both normal and pseudo child states
            (
                    """
                    pseudo state S1 { state S2; pseudo state S3; S2 -> S3; S3 -> S2; }
                    """,
                    "pseudo state S1 {\n    state S2;\n    pseudo state S3;\n    S2 -> S3;\n    S3 -> S2;\n}",
            ),  # Pseudo state with mixed child states and bidirectional transitions

            (
                    """
                    state idle named "Idle State";
                    """,
                    "state idle named 'Idle State';"
            ),  # Basic leaf state with named string
            (
                    """
                    state idle named 'Idle State';
                    """,
                    "state idle named 'Idle State';"
            ),  # Basic leaf state with named string with single quota
            (
                    """
                    state running named "Running State";
                    """,
                    "state running named 'Running State';"
            ),  # Simple leaf state with descriptive name
            (
                    """
                    pseudo state error named "Error State";
                    """,
                    "pseudo state error named 'Error State';"
            ),  # Pseudo leaf state with named keyword
            (
                    """
                    state main named "Main State" {}
                    """,
                    "state main named 'Main State';"
            ),  # Empty composite state with named keyword
            (
                    """
                    pseudo state container named "Container State" {}
                    """,
                    "pseudo state container named 'Container State';"
            ),  # Pseudo composite state with named keyword
            (
                    """
                    state parent named "Parent State" { state child named "Child State"; }
                    """,
                    "state parent named 'Parent State' {\n    state child named 'Child State';\n}"
            ),  # Composite state with nested leaf state
            (
                    """
                    state machine named "State Machine" { ; }
                    """,
                    "state machine named 'State Machine';"
            ),  # Composite state with empty statement
            (
                    """
                    state complex named "Complex State" { state sub1 named "Sub State 1"; state sub2 named "Sub State 2"; }
                    """,
                    "state complex named 'Complex State' {\n    state sub1 named 'Sub State 1';\n    state sub2 named 'Sub State 2';\n}"
            ),  # Composite state with multiple nested states
            (
                    """
                    state active named "Active State" { [*] -> ready; }
                    """,
                    "state active named 'Active State' {\n    [*] -> ready;\n}"
            ),  # Composite state with entry transition
            (
                    """
                    state workflow named "Workflow State" { state1 -> state2; }
                    """,
                    "state workflow named 'Workflow State' {\n    state1 -> state2;\n}"
            ),  # Composite state with normal transition
            (
                    """
                    state managed named "Managed State" { enter { x = 1; }; }
                    """,
                    "state managed named 'Managed State' {\n    enter {\n        x = 1;\n    }\n}"
            ),  # Composite state with enter operation
            (
                    """
                    state controlled named "Controlled State" { exit abstract cleanup; }
                    """,
                    "state controlled named 'Controlled State' {\n    exit abstract cleanup;\n}"
            ),  # Composite state with abstract exit function
            (
                    """
                    state outer named "Outer State" { state inner named "Inner State" { state deep named "Deep State"; } }
                    """,
                    "state outer named 'Outer State' {\n    state inner named 'Inner State' {\n        state deep named 'Deep State';\n    }\n}"
            ),  # Deeply nested composite states
            (
                    """
                    pseudo state root named "Root State" { state branch1 named "Branch 1" {} state branch2 named "Branch 2" {} }
                    """,
                    "pseudo state root named 'Root State' {\n    state branch1 named 'Branch 1';\n    state branch2 named 'Branch 2';\n}"
            ),  # Pseudo state with multiple composite children
            (
                    """
                    state system named "System State" { state init named "Init"; [*] -> init; }
                    """,
                    "state system named 'System State' {\n    state init named 'Init';\n    [*] -> init;\n}"
            ),  # Composite state with nested state and transition
            (
                    """
                    state handler named "Handler State" { during { y = 2; }; state process named "Process"; }
                    """,
                    "state handler named 'Handler State' {\n    during {\n        y = 2;\n    }\n    state process named 'Process';\n}"
            ),  # Composite state with during operation and nested state

            (
                    """
                    state MainState {
                        event ButtonClick;
                    }
                    """,
                    'state MainState {\n    event ButtonClick;\n}'
            ),  # Basic composite state with simple event definition
            (
                    """
                    state ProcessingState {
                        event DataReceived named "Data Reception Event";
                    }
                    """,
                    "state ProcessingState {\n    event DataReceived named 'Data Reception Event';\n}"
            ),  # Composite state with named event definition
            (
                    """
                    pseudo state ControllerState {
                        event StartEvent;
                        event StopEvent named "Stop Operation";
                        event ResetEvent named "System Reset";
                    }
                    """,
                    "pseudo state ControllerState {\n    event StartEvent;\n    event StopEvent named 'Stop Operation';\n    event ResetEvent named 'System Reset';\n}"
            ),  # Pseudo composite state with multiple events, mixed named usage
            (
                    """
                    state WorkflowState named "Main Workflow" {
                        event ProcessComplete named "Processing Completed";
                        state SubState;
                        event ErrorOccurred;
                        enter { x = 10; }
                    }
                    """,
                    "state WorkflowState named 'Main Workflow' {\n    enter {\n        x = 10;\n    }\n    state SubState;\n    event ProcessComplete named 'Processing Completed';\n    event ErrorOccurred;\n}"
            ),  # Complex composite state with events, substates, and enter definition
            (
                    """
                    pseudo state AlertState named 'Alert Handler' {
                        event WarningTriggered named 'Warning Event';
                    }
                    """,
                    "pseudo state AlertState named 'Alert Handler' {\n    event WarningTriggered named 'Warning Event';\n}"
            ),  # Pseudo state with event using single quotes in named clause
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(
                parse_with_grammar_entry(input_text, entry_name="state_definition")
            ),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            ("state;",),  # Missing state identifier
            ("state 123;",),  # Invalid state name starting with number
            ("state S1",),  # Missing semicolon after leaf state
            ("state S1 {",),  # Unclosed composite state definition
            ("state S1 }",),  # Missing opening brace for composite state
            ("State S1;",),  # Incorrect capitalization of 'state' keyword
            ("state S1 { state }",),  # Missing state identifier in inner state
            ("state S1 { S2 -> }",),  # Incomplete transition definition
            ("state S1 { -> S2; }",),  # Missing source state in transition
            ("state S1 { S2 ->; }",),  # Missing target state in transition
            ("state S1 { S2 -> S3: }",),  # Incomplete chain ID specification
            ("state S1 { S2 -> S3: if; }",),  # Missing condition expression after 'if'
            ("state S1 { S2 -> S3: if []; }",),  # Empty condition expression
            ("state S1 { S2 -> S3: if x > 5; }",),  # Missing brackets around condition
            ("state S1 { S2 -> S3 effect }",),  # Missing braces after 'effect' keyword
            ("state S1 { S2 -> S3 effect { x := 10; } }",),
            # Incorrect assignment operator in effect operation (using := instead of =)
            (
                    "state S1 { S2 -> S3 effect { x = 10 } }",
            ),  # Missing semicolon after assignment in effect operation
            ("state { state S2; }",),  # Missing state identifier for outer state
            (
                    "state S1 { state S2 state S3; }",
            ),  # Missing semicolon between inner states
            ("state S1 { [*] -> [*]; }",),  # Invalid transition from entry to exit
            (
                    "state S1 { S2 -> S3: if [x > 5] effect x = 10; }",
            ),  # Missing braces around effect operations
            (
                    "state S1 { S2 -> S3: chain..id; }",
            ),  # Invalid chain ID with consecutive dots
            (
                    "state S1 { S2 -> S3: if [x > 5] else [y < 10]; }",
            ),  # Unsupported 'else' clause in condition
            (
                    "state S1 { S2 -> S3: when [x > 5]; }",
            ),  # Using 'when' instead of 'if' for condition
            (
                    """
                    Pseudo state S1;
                    """,
            ),  # Incorrect capitalization of pseudo keyword
            (
                    """
                    pseudo State S1;
                    """,
            ),  # Incorrect capitalization of state keyword after pseudo
            (
                    """
                    pseudo state;
                    """,
            ),  # Missing state identifier after pseudo state
            (
                    """
                    pseudo state 123;
                    """,
            ),  # Invalid state name starting with number in pseudo state
            (
                    """
                    pseudo state S1
                    """,
            ),  # Missing semicolon after pseudo leaf state
            (
                    """
                    pseudo state S1 {
                    """,
            ),  # Unclosed pseudo composite state definition
            (
                    """
                    pseudo state S1 }
                    """,
            ),  # Missing opening brace for pseudo composite state
            (
                    """
                    pseudo state S1 { pseudo state }
                    """,
            ),  # Missing state identifier in nested pseudo state
            (
                    """
                    pseudo state S1 { pseudo State S2; }
                    """,
            ),  # Incorrect capitalization in nested pseudo state
            (
                    """
                    pseudo state S1 { S2 -> }
                    """,
            ),  # Incomplete transition definition in pseudo state
            (
                    """
                    pseudo state S1 { -> S2; }
                    """,
            ),  # Missing source state in transition within pseudo state
            (
                    """
                    pseudo state S1 { S2 ->; }
                    """,
            ),  # Missing target state in transition within pseudo state
            (
                    """
                    pseudo state S1 { S2 -> S3: }
                    """,
            ),  # Incomplete chain ID specification in pseudo state transition
            (
                    """
                    pseudo state S1 { S2 -> S3: if; }
                    """,
            ),  # Missing condition expression after if in pseudo state
            (
                    """
                    pseudo state S1 { S2 -> S3: if []; }
                    """,
            ),  # Empty condition expression in pseudo state transition
            (
                    """
                    pseudo state S1 { ! -> S2; }
                    """,
            ),  # Missing source state in force transition within pseudo state
            (
                    """
                    pseudo state S1 { ! S2 -> }
                    """,
            ),  # Incomplete force transition definition in pseudo state
            (
                    """
                    pseudo state S1 { ! S2 ->; }
                    """,
            ),  # Missing target state in force transition within pseudo state
            (
                    """
                    pseudo state S1 { !! S2 -> S3; }
                    """,
            ),  # Double exclamation mark in force transition within pseudo state
            (
                    """
                    pseudo state S1 { enter }
                    """,
            ),  # Missing braces after enter keyword in pseudo state
            (
                    """
                    pseudo state S1 { exit }
                    """,
            ),  # Missing braces after exit keyword in pseudo state
            (
                    """
                    pseudo state S1 { during }
                    """,
            ),  # Missing braces after during keyword in pseudo state
            (
                    """
                    pseudo state S1 { enter { x := 10; } }
                    """,
            ),  # Incorrect assignment operator in enter operation within pseudo state
            (
                    """
                    pseudo state S1 { exit abstract; }
                    """,
            ),  # Missing function name after abstract in exit definition within pseudo state
            (
                    """
                    pseudo state S1 { >> during { x = 1; } }
                    """,
            ),  # Missing aspect (before/after) in during aspect within pseudo state
            (
                    """
                    pseudo state S1 { > during before { x = 1; } }
                    """,
            ),  # Single > instead of >> for during aspect in pseudo state
            (
                    """
                    pseudo state S1 { >> during middle { x = 1; } }
                    """,
            ),  # Invalid aspect 'middle' (should be before/after) in pseudo state
            (
                    """
                    pseudo state S1 { >> during before abstract; }
                    """,
            ),  # Missing function name after abstract in during aspect within pseudo state

            (
                    """
                    state idle "Idle State";
                    """,
            ),  # Leaf state without named keyword
            (
                    """
                    pseudo state error "Error State";
                    """,
            ),  # Pseudo state missing named keyword
            (
                    """
                    state idle named;
                    """,
            ),  # State with named but no string
            (
                    """
                    state running named Unquoted;
                    """,
            ),  # State with unquoted name after named
            (
                    """
                    state active named "Missing semicolon"
                    """,
            ),  # Leaf state missing semicolon
            (
                    """
                    state parent named "Parent" {
                    """,
            ),  # Composite state with unclosed brace
            (
                    """
                    state container named "Container" }
                    """,
            ),  # Composite state with missing opening brace
            (
                    """
                    pseudo named "Invalid";
                    """,
            ),  # Pseudo without state keyword
            (
                    """
                    state pseudo named "Wrong Order";
                    """,
            ),  # Wrong order of pseudo and state keywords
            (
                    """
                    pseudostate main named "Invalid";
                    """,
            ),  # Concatenated pseudo and state
            (
                    """
                    state 123invalid named "Number Start";
                    """,
            ),  # State ID starting with number
            (
                    """
                    state invalid-name named "Dash Name";
                    """,
            ),  # State ID with dash
            (
                    """
                    state invalid.name named "Dot Name";
                    """,
            ),  # State ID with dot
            (
                    """
                    state test named Invalid String;
                    """,
            ),  # Unquoted string after named
            (
                    """
                    state test named "Unclosed string;
                    """,
            ),  # Unclosed string literal
            (
                    """
                    named "Missing State";
                    """,
            ),  # Named clause without state keyword
            (
                    """
                    state;
                    """,
            ),  # State keyword without identifier
            (
                    """
                    pseudo state;
                    """,
            ),  # Pseudo state without identifier
            (
                    """
                    state parent named "Parent" { invalid content }
                    """,
            ),  # Composite state with invalid content
            (
                    """
                    state container named "Container" { 123invalid; }
                    """,
            ),  # Composite state with invalid statement
            (
                    """
                    state broken named "Broken" { state }
                    """,
            ),  # Composite state with incomplete nested state

            (
                    """
                    state SimpleState named "Simple" ;
                    event SomeEvent;
                    """,
            ),  # Leaf state followed by event definition (not allowed in leaf state)
            (
                    """
                    state ContainerState {
                        event Missingsemicolon named "Bad Event"
                    }
                    """,
            ),  # Event definition missing required semicolon
            (
                    """
                    state BadState {
                        event 123InvalidName;
                    }
                    """,
            ),  # Event with invalid identifier starting with number
            (
                    """
                    state IncompleteState {
                        event;
                    }
                    """,
            ),  # Event definition missing required event name
            (
                    """
                    state BrokenState {
                        event ValidName named "Unclosed string;
                    }
                    """,
            ),  # Event definition with unclosed string in named clause
            (
                    """
                    event GlobalEvent;
                    state SomeState {
                    }
                    """,
            ),  # Event definition outside of state context (not allowed at top level)
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name="state_definition")

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
