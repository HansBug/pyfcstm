import textwrap
import pytest

from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl.node import INIT_STATE, EXIT_STATE
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.expr import *
from pyfcstm.model.model import *


@pytest.fixture()
def model():
    ast_node = parse_with_grammar_entry(
        """
def int x = 0;
def int y = 0;
def int z = 0;
def int flag = 0;

state Root {
    state Active {
        during {
            tmp = x + 1;

            if [flag > 0] {
                tmp = tmp + 10;

                if [y > 5] {
                    bonus = y + 2;
                    z = tmp + bonus;
                } else {
                    z = tmp - y;
                }
            } else if [x > 3] {
                tmp = tmp + 20;
                z = tmp;
            } else {
                z = tmp;
            }

            x = z + tmp;
        }
    }

    [*] -> Active;
}
    """,
        entry_name="state_machine_dsl",
    )
    model = parse_dsl_node_to_state_machine(
        ast_node, path="test/testfile/sample_codes/if_nested_temporaries.fcstm"
    )
    return model


@pytest.fixture()
def state_root(model):
    return model.root_state


@pytest.fixture()
def state_root_active(state_root):
    return state_root.substates["Active"]


@pytest.mark.unittest
class TestModelStateRoot:
    def test_model(self, model):
        assert model.defines == {
            "x": VarDefine(name="x", type="int", init=Integer(value=0)),
            "y": VarDefine(name="y", type="int", init=Integer(value=0)),
            "z": VarDefine(name="z", type="int", init=Integer(value=0)),
            "flag": VarDefine(name="flag", type="int", init=Integer(value=0)),
        }
        assert model.root_state.name == "Root"
        assert model.root_state.path == ("Root",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="x", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
            dsl_nodes.DefAssignment(
                name="y", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
            dsl_nodes.DefAssignment(
                name="z", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
            dsl_nodes.DefAssignment(
                name="flag", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
        ]
        assert ast_node.root_state.name == "Root"

    def test_state_root(self, state_root):
        assert state_root.name == "Root"
        assert state_root.path == ("Root",)
        assert sorted(state_root.substates.keys()) == ["Active"]
        assert state_root.events == {}
        assert len(state_root.transitions) == 1
        assert state_root.transitions[0].from_state == INIT_STATE
        assert state_root.transitions[0].to_state == "Active"
        assert state_root.transitions[0].event is None
        assert state_root.transitions[0].guard is None
        assert state_root.transitions[0].effects == []
        assert state_root.transitions[0].parent_ref().name == "Root"
        assert state_root.transitions[0].parent_ref().path == ("Root",)
        assert state_root.named_functions == {}
        assert state_root.on_enters == []
        assert state_root.on_durings == []
        assert state_root.on_exits == []
        assert state_root.on_during_aspects == []
        assert state_root.parent_ref is None
        assert state_root.substate_name_to_id == {"Active": 0}
        assert state_root.extra_name is None
        assert not state_root.is_pseudo
        assert state_root.abstract_on_during_aspects == []
        assert state_root.abstract_on_durings == []
        assert state_root.abstract_on_enters == []
        assert state_root.abstract_on_exits == []
        assert len(state_root.init_transitions) == 1
        assert state_root.init_transitions[0].from_state == INIT_STATE
        assert state_root.init_transitions[0].to_state == "Active"
        assert state_root.init_transitions[0].event is None
        assert state_root.init_transitions[0].guard is None
        assert state_root.init_transitions[0].effects == []
        assert state_root.init_transitions[0].parent_ref().name == "Root"
        assert state_root.init_transitions[0].parent_ref().path == ("Root",)
        assert not state_root.is_leaf_state
        assert state_root.is_root_state
        assert not state_root.is_stoppable
        assert state_root.non_abstract_on_during_aspects == []
        assert state_root.non_abstract_on_durings == []
        assert state_root.non_abstract_on_enters == []
        assert state_root.non_abstract_on_exits == []
        assert state_root.parent is None
        assert len(state_root.transitions_entering_children) == 1
        assert state_root.transitions_entering_children[0].from_state == INIT_STATE
        assert state_root.transitions_entering_children[0].to_state == "Active"
        assert state_root.transitions_entering_children[0].event is None
        assert state_root.transitions_entering_children[0].guard is None
        assert state_root.transitions_entering_children[0].effects == []
        assert state_root.transitions_entering_children[0].parent_ref().name == "Root"
        assert state_root.transitions_entering_children[0].parent_ref().path == (
            "Root",
        )
        assert len(state_root.transitions_entering_children_simplified) == 1
        assert (
            state_root.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_root.transitions_entering_children_simplified[0].to_state == "Active"
        )
        assert state_root.transitions_entering_children_simplified[0].event is None
        assert state_root.transitions_entering_children_simplified[0].guard is None
        assert state_root.transitions_entering_children_simplified[0].effects == []
        assert (
            state_root.transitions_entering_children_simplified[0].parent_ref().name
            == "Root"
        )
        assert state_root.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Root",)
        assert len(state_root.transitions_from) == 1
        assert state_root.transitions_from[0].from_state == "Root"
        assert state_root.transitions_from[0].to_state == EXIT_STATE
        assert state_root.transitions_from[0].event is None
        assert state_root.transitions_from[0].guard is None
        assert state_root.transitions_from[0].effects == []
        assert state_root.transitions_from[0].parent_ref is None
        assert len(state_root.transitions_to) == 1
        assert state_root.transitions_to[0].from_state == INIT_STATE
        assert state_root.transitions_to[0].to_state == "Root"
        assert state_root.transitions_to[0].event is None
        assert state_root.transitions_to[0].guard is None
        assert state_root.transitions_to[0].effects == []
        assert state_root.transitions_to[0].parent_ref is None

    def test_state_root_to_ast_node(self, state_root):
        ast_node = state_root.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Root",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Active",
                    extra_name=None,
                    events=[],
                    imports=[],
                    substates=[],
                    transitions=[],
                    enters=[],
                    durings=[
                        dsl_nodes.DuringOperations(
                            aspect=None,
                            operations=[
                                dsl_nodes.OperationAssignment(
                                    name="tmp",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="x"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
                                dsl_nodes.OperationIf(
                                    branches=[
                                        dsl_nodes.OperationIfBranch(
                                            condition=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(name="flag"),
                                                op=">",
                                                expr2=dsl_nodes.Integer(raw="0"),
                                            ),
                                            statements=[
                                                dsl_nodes.OperationAssignment(
                                                    name="tmp",
                                                    expr=dsl_nodes.BinaryOp(
                                                        expr1=dsl_nodes.Name(
                                                            name="tmp"
                                                        ),
                                                        op="+",
                                                        expr2=dsl_nodes.Integer(
                                                            raw="10"
                                                        ),
                                                    ),
                                                ),
                                                dsl_nodes.OperationIf(
                                                    branches=[
                                                        dsl_nodes.OperationIfBranch(
                                                            condition=dsl_nodes.BinaryOp(
                                                                expr1=dsl_nodes.Name(
                                                                    name="y"
                                                                ),
                                                                op=">",
                                                                expr2=dsl_nodes.Integer(
                                                                    raw="5"
                                                                ),
                                                            ),
                                                            statements=[
                                                                dsl_nodes.OperationAssignment(
                                                                    name="bonus",
                                                                    expr=dsl_nodes.BinaryOp(
                                                                        expr1=dsl_nodes.Name(
                                                                            name="y"
                                                                        ),
                                                                        op="+",
                                                                        expr2=dsl_nodes.Integer(
                                                                            raw="2"
                                                                        ),
                                                                    ),
                                                                ),
                                                                dsl_nodes.OperationAssignment(
                                                                    name="z",
                                                                    expr=dsl_nodes.BinaryOp(
                                                                        expr1=dsl_nodes.Name(
                                                                            name="tmp"
                                                                        ),
                                                                        op="+",
                                                                        expr2=dsl_nodes.Name(
                                                                            name="bonus"
                                                                        ),
                                                                    ),
                                                                ),
                                                            ],
                                                        ),
                                                        dsl_nodes.OperationIfBranch(
                                                            condition=None,
                                                            statements=[
                                                                dsl_nodes.OperationAssignment(
                                                                    name="z",
                                                                    expr=dsl_nodes.BinaryOp(
                                                                        expr1=dsl_nodes.Name(
                                                                            name="tmp"
                                                                        ),
                                                                        op="-",
                                                                        expr2=dsl_nodes.Name(
                                                                            name="y"
                                                                        ),
                                                                    ),
                                                                )
                                                            ],
                                                        ),
                                                    ]
                                                ),
                                            ],
                                        ),
                                        dsl_nodes.OperationIfBranch(
                                            condition=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(name="x"),
                                                op=">",
                                                expr2=dsl_nodes.Integer(raw="3"),
                                            ),
                                            statements=[
                                                dsl_nodes.OperationAssignment(
                                                    name="tmp",
                                                    expr=dsl_nodes.BinaryOp(
                                                        expr1=dsl_nodes.Name(
                                                            name="tmp"
                                                        ),
                                                        op="+",
                                                        expr2=dsl_nodes.Integer(
                                                            raw="20"
                                                        ),
                                                    ),
                                                ),
                                                dsl_nodes.OperationAssignment(
                                                    name="z",
                                                    expr=dsl_nodes.Name(name="tmp"),
                                                ),
                                            ],
                                        ),
                                        dsl_nodes.OperationIfBranch(
                                            condition=None,
                                            statements=[
                                                dsl_nodes.OperationAssignment(
                                                    name="z",
                                                    expr=dsl_nodes.Name(name="tmp"),
                                                )
                                            ],
                                        ),
                                    ]
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="x",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="z"),
                                        op="+",
                                        expr2=dsl_nodes.Name(name="tmp"),
                                    ),
                                ),
                            ],
                            name=None,
                        )
                    ],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                )
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="Active",
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
            is_pseudo=False,
        )

    def test_state_root_list_on_enters(self, state_root):
        lst = state_root.list_on_enters()
        assert lst == []

        lst = state_root.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_root.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_during_aspects(self, state_root):
        lst = state_root.list_on_during_aspects()
        assert lst == []

        lst = state_root.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_root.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_root.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_root.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_root_active(self, state_root_active):
        assert state_root_active.name == "Active"
        assert state_root_active.path == ("Root", "Active")
        assert sorted(state_root_active.substates.keys()) == []
        assert state_root_active.events == {}
        assert state_root_active.transitions == []
        assert state_root_active.named_functions == {}
        assert state_root_active.on_enters == []
        assert len(state_root_active.on_durings) == 1
        assert state_root_active.on_durings[0].stage == "during"
        assert state_root_active.on_durings[0].aspect is None
        assert state_root_active.on_durings[0].name is None
        assert state_root_active.on_durings[0].doc is None
        assert state_root_active.on_durings[0].operations == [
            Operation(
                var_name="tmp",
                expr=BinaryOp(x=Variable(name="x"), op="+", y=Integer(value=1)),
            ),
            IfBlock(
                branches=[
                    IfBlockBranch(
                        condition=BinaryOp(
                            x=Variable(name="flag"), op=">", y=Integer(value=0)
                        ),
                        statements=[
                            Operation(
                                var_name="tmp",
                                expr=BinaryOp(
                                    x=Variable(name="tmp"), op="+", y=Integer(value=10)
                                ),
                            ),
                            IfBlock(
                                branches=[
                                    IfBlockBranch(
                                        condition=BinaryOp(
                                            x=Variable(name="y"),
                                            op=">",
                                            y=Integer(value=5),
                                        ),
                                        statements=[
                                            Operation(
                                                var_name="bonus",
                                                expr=BinaryOp(
                                                    x=Variable(name="y"),
                                                    op="+",
                                                    y=Integer(value=2),
                                                ),
                                            ),
                                            Operation(
                                                var_name="z",
                                                expr=BinaryOp(
                                                    x=Variable(name="tmp"),
                                                    op="+",
                                                    y=Variable(name="bonus"),
                                                ),
                                            ),
                                        ],
                                    ),
                                    IfBlockBranch(
                                        condition=None,
                                        statements=[
                                            Operation(
                                                var_name="z",
                                                expr=BinaryOp(
                                                    x=Variable(name="tmp"),
                                                    op="-",
                                                    y=Variable(name="y"),
                                                ),
                                            )
                                        ],
                                    ),
                                ]
                            ),
                        ],
                    ),
                    IfBlockBranch(
                        condition=BinaryOp(
                            x=Variable(name="x"), op=">", y=Integer(value=3)
                        ),
                        statements=[
                            Operation(
                                var_name="tmp",
                                expr=BinaryOp(
                                    x=Variable(name="tmp"), op="+", y=Integer(value=20)
                                ),
                            ),
                            Operation(var_name="z", expr=Variable(name="tmp")),
                        ],
                    ),
                    IfBlockBranch(
                        condition=None,
                        statements=[Operation(var_name="z", expr=Variable(name="tmp"))],
                    ),
                ]
            ),
            Operation(
                var_name="x",
                expr=BinaryOp(x=Variable(name="z"), op="+", y=Variable(name="tmp")),
            ),
        ]
        assert not state_root_active.on_durings[0].is_abstract
        assert state_root_active.on_durings[0].state_path == ("Root", "Active", None)
        assert state_root_active.on_durings[0].ref is None
        assert state_root_active.on_durings[0].ref_state_path is None
        assert state_root_active.on_durings[0].parent_ref().name == "Active"
        assert state_root_active.on_durings[0].parent_ref().path == ("Root", "Active")
        assert state_root_active.on_durings[0].func_name == "Root.Active.<unnamed>"
        assert not state_root_active.on_durings[0].is_aspect
        assert not state_root_active.on_durings[0].is_ref
        assert state_root_active.on_durings[0].parent.name == "Active"
        assert state_root_active.on_durings[0].parent.path == ("Root", "Active")
        assert state_root_active.on_exits == []
        assert state_root_active.on_during_aspects == []
        assert state_root_active.parent_ref().name == "Root"
        assert state_root_active.parent_ref().path == ("Root",)
        assert state_root_active.substate_name_to_id == {}
        assert state_root_active.extra_name is None
        assert not state_root_active.is_pseudo
        assert state_root_active.abstract_on_during_aspects == []
        assert state_root_active.abstract_on_durings == []
        assert state_root_active.abstract_on_enters == []
        assert state_root_active.abstract_on_exits == []
        assert state_root_active.init_transitions == []
        assert state_root_active.is_leaf_state
        assert not state_root_active.is_root_state
        assert state_root_active.is_stoppable
        assert state_root_active.non_abstract_on_during_aspects == []
        assert len(state_root_active.non_abstract_on_durings) == 1
        assert state_root_active.non_abstract_on_durings[0].stage == "during"
        assert state_root_active.non_abstract_on_durings[0].aspect is None
        assert state_root_active.non_abstract_on_durings[0].name is None
        assert state_root_active.non_abstract_on_durings[0].doc is None
        assert state_root_active.non_abstract_on_durings[0].operations == [
            Operation(
                var_name="tmp",
                expr=BinaryOp(x=Variable(name="x"), op="+", y=Integer(value=1)),
            ),
            IfBlock(
                branches=[
                    IfBlockBranch(
                        condition=BinaryOp(
                            x=Variable(name="flag"), op=">", y=Integer(value=0)
                        ),
                        statements=[
                            Operation(
                                var_name="tmp",
                                expr=BinaryOp(
                                    x=Variable(name="tmp"), op="+", y=Integer(value=10)
                                ),
                            ),
                            IfBlock(
                                branches=[
                                    IfBlockBranch(
                                        condition=BinaryOp(
                                            x=Variable(name="y"),
                                            op=">",
                                            y=Integer(value=5),
                                        ),
                                        statements=[
                                            Operation(
                                                var_name="bonus",
                                                expr=BinaryOp(
                                                    x=Variable(name="y"),
                                                    op="+",
                                                    y=Integer(value=2),
                                                ),
                                            ),
                                            Operation(
                                                var_name="z",
                                                expr=BinaryOp(
                                                    x=Variable(name="tmp"),
                                                    op="+",
                                                    y=Variable(name="bonus"),
                                                ),
                                            ),
                                        ],
                                    ),
                                    IfBlockBranch(
                                        condition=None,
                                        statements=[
                                            Operation(
                                                var_name="z",
                                                expr=BinaryOp(
                                                    x=Variable(name="tmp"),
                                                    op="-",
                                                    y=Variable(name="y"),
                                                ),
                                            )
                                        ],
                                    ),
                                ]
                            ),
                        ],
                    ),
                    IfBlockBranch(
                        condition=BinaryOp(
                            x=Variable(name="x"), op=">", y=Integer(value=3)
                        ),
                        statements=[
                            Operation(
                                var_name="tmp",
                                expr=BinaryOp(
                                    x=Variable(name="tmp"), op="+", y=Integer(value=20)
                                ),
                            ),
                            Operation(var_name="z", expr=Variable(name="tmp")),
                        ],
                    ),
                    IfBlockBranch(
                        condition=None,
                        statements=[Operation(var_name="z", expr=Variable(name="tmp"))],
                    ),
                ]
            ),
            Operation(
                var_name="x",
                expr=BinaryOp(x=Variable(name="z"), op="+", y=Variable(name="tmp")),
            ),
        ]
        assert not state_root_active.non_abstract_on_durings[0].is_abstract
        assert state_root_active.non_abstract_on_durings[0].state_path == (
            "Root",
            "Active",
            None,
        )
        assert state_root_active.non_abstract_on_durings[0].ref is None
        assert state_root_active.non_abstract_on_durings[0].ref_state_path is None
        assert (
            state_root_active.non_abstract_on_durings[0].parent_ref().name == "Active"
        )
        assert state_root_active.non_abstract_on_durings[0].parent_ref().path == (
            "Root",
            "Active",
        )
        assert (
            state_root_active.non_abstract_on_durings[0].func_name
            == "Root.Active.<unnamed>"
        )
        assert not state_root_active.non_abstract_on_durings[0].is_aspect
        assert not state_root_active.non_abstract_on_durings[0].is_ref
        assert state_root_active.non_abstract_on_durings[0].parent.name == "Active"
        assert state_root_active.non_abstract_on_durings[0].parent.path == (
            "Root",
            "Active",
        )
        assert state_root_active.non_abstract_on_enters == []
        assert state_root_active.non_abstract_on_exits == []
        assert state_root_active.parent.name == "Root"
        assert state_root_active.parent.path == ("Root",)
        assert state_root_active.transitions_entering_children == []
        assert len(state_root_active.transitions_entering_children_simplified) == 1
        assert state_root_active.transitions_entering_children_simplified[0] is None
        assert state_root_active.transitions_from == []
        assert len(state_root_active.transitions_to) == 1
        assert state_root_active.transitions_to[0].from_state == INIT_STATE
        assert state_root_active.transitions_to[0].to_state == "Active"
        assert state_root_active.transitions_to[0].event is None
        assert state_root_active.transitions_to[0].guard is None
        assert state_root_active.transitions_to[0].effects == []
        assert state_root_active.transitions_to[0].parent_ref().name == "Root"
        assert state_root_active.transitions_to[0].parent_ref().path == ("Root",)

    def test_state_root_active_to_ast_node(self, state_root_active):
        ast_node = state_root_active.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Active",
            extra_name=None,
            events=[],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[
                dsl_nodes.DuringOperations(
                    aspect=None,
                    operations=[
                        dsl_nodes.OperationAssignment(
                            name="tmp",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="x"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
                        dsl_nodes.OperationIf(
                            branches=[
                                dsl_nodes.OperationIfBranch(
                                    condition=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="flag"),
                                        op=">",
                                        expr2=dsl_nodes.Integer(raw="0"),
                                    ),
                                    statements=[
                                        dsl_nodes.OperationAssignment(
                                            name="tmp",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(name="tmp"),
                                                op="+",
                                                expr2=dsl_nodes.Integer(raw="10"),
                                            ),
                                        ),
                                        dsl_nodes.OperationIf(
                                            branches=[
                                                dsl_nodes.OperationIfBranch(
                                                    condition=dsl_nodes.BinaryOp(
                                                        expr1=dsl_nodes.Name(name="y"),
                                                        op=">",
                                                        expr2=dsl_nodes.Integer(
                                                            raw="5"
                                                        ),
                                                    ),
                                                    statements=[
                                                        dsl_nodes.OperationAssignment(
                                                            name="bonus",
                                                            expr=dsl_nodes.BinaryOp(
                                                                expr1=dsl_nodes.Name(
                                                                    name="y"
                                                                ),
                                                                op="+",
                                                                expr2=dsl_nodes.Integer(
                                                                    raw="2"
                                                                ),
                                                            ),
                                                        ),
                                                        dsl_nodes.OperationAssignment(
                                                            name="z",
                                                            expr=dsl_nodes.BinaryOp(
                                                                expr1=dsl_nodes.Name(
                                                                    name="tmp"
                                                                ),
                                                                op="+",
                                                                expr2=dsl_nodes.Name(
                                                                    name="bonus"
                                                                ),
                                                            ),
                                                        ),
                                                    ],
                                                ),
                                                dsl_nodes.OperationIfBranch(
                                                    condition=None,
                                                    statements=[
                                                        dsl_nodes.OperationAssignment(
                                                            name="z",
                                                            expr=dsl_nodes.BinaryOp(
                                                                expr1=dsl_nodes.Name(
                                                                    name="tmp"
                                                                ),
                                                                op="-",
                                                                expr2=dsl_nodes.Name(
                                                                    name="y"
                                                                ),
                                                            ),
                                                        )
                                                    ],
                                                ),
                                            ]
                                        ),
                                    ],
                                ),
                                dsl_nodes.OperationIfBranch(
                                    condition=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="x"),
                                        op=">",
                                        expr2=dsl_nodes.Integer(raw="3"),
                                    ),
                                    statements=[
                                        dsl_nodes.OperationAssignment(
                                            name="tmp",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(name="tmp"),
                                                op="+",
                                                expr2=dsl_nodes.Integer(raw="20"),
                                            ),
                                        ),
                                        dsl_nodes.OperationAssignment(
                                            name="z", expr=dsl_nodes.Name(name="tmp")
                                        ),
                                    ],
                                ),
                                dsl_nodes.OperationIfBranch(
                                    condition=None,
                                    statements=[
                                        dsl_nodes.OperationAssignment(
                                            name="z", expr=dsl_nodes.Name(name="tmp")
                                        )
                                    ],
                                ),
                            ]
                        ),
                        dsl_nodes.OperationAssignment(
                            name="x",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="z"),
                                op="+",
                                expr2=dsl_nodes.Name(name="tmp"),
                            ),
                        ),
                    ],
                    name=None,
                )
            ],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_root_active_list_on_enters(self, state_root_active):
        lst = state_root_active.list_on_enters()
        assert lst == []

        lst = state_root_active.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_active.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_active.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_active.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_root_active.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root_active.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_active.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root_active.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_active_during_aspects(self, state_root_active):
        lst = state_root_active.list_on_during_aspects()
        assert lst == []

        lst = state_root_active.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_active.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_active.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_active.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_active.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_active.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_active.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_active.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_root_active_during_aspect_recursively(self, state_root_active):
        lst = state_root_active.list_on_during_aspect_recursively()
        assert len(lst) == 1
        st, on_stage = lst[0]
        assert st.name == "Active"
        assert st.path == ("Root", "Active")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(
                var_name="tmp",
                expr=BinaryOp(x=Variable(name="x"), op="+", y=Integer(value=1)),
            ),
            IfBlock(
                branches=[
                    IfBlockBranch(
                        condition=BinaryOp(
                            x=Variable(name="flag"), op=">", y=Integer(value=0)
                        ),
                        statements=[
                            Operation(
                                var_name="tmp",
                                expr=BinaryOp(
                                    x=Variable(name="tmp"), op="+", y=Integer(value=10)
                                ),
                            ),
                            IfBlock(
                                branches=[
                                    IfBlockBranch(
                                        condition=BinaryOp(
                                            x=Variable(name="y"),
                                            op=">",
                                            y=Integer(value=5),
                                        ),
                                        statements=[
                                            Operation(
                                                var_name="bonus",
                                                expr=BinaryOp(
                                                    x=Variable(name="y"),
                                                    op="+",
                                                    y=Integer(value=2),
                                                ),
                                            ),
                                            Operation(
                                                var_name="z",
                                                expr=BinaryOp(
                                                    x=Variable(name="tmp"),
                                                    op="+",
                                                    y=Variable(name="bonus"),
                                                ),
                                            ),
                                        ],
                                    ),
                                    IfBlockBranch(
                                        condition=None,
                                        statements=[
                                            Operation(
                                                var_name="z",
                                                expr=BinaryOp(
                                                    x=Variable(name="tmp"),
                                                    op="-",
                                                    y=Variable(name="y"),
                                                ),
                                            )
                                        ],
                                    ),
                                ]
                            ),
                        ],
                    ),
                    IfBlockBranch(
                        condition=BinaryOp(
                            x=Variable(name="x"), op=">", y=Integer(value=3)
                        ),
                        statements=[
                            Operation(
                                var_name="tmp",
                                expr=BinaryOp(
                                    x=Variable(name="tmp"), op="+", y=Integer(value=20)
                                ),
                            ),
                            Operation(var_name="z", expr=Variable(name="tmp")),
                        ],
                    ),
                    IfBlockBranch(
                        condition=None,
                        statements=[Operation(var_name="z", expr=Variable(name="tmp"))],
                    ),
                ]
            ),
            Operation(
                var_name="x",
                expr=BinaryOp(x=Variable(name="z"), op="+", y=Variable(name="tmp")),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("Root", "Active", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "Active"
        assert on_stage.parent_ref().path == ("Root", "Active")
        assert on_stage.func_name == "Root.Active.<unnamed>"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "Active"
        assert on_stage.parent.path == ("Root", "Active")

        lst = state_root_active.list_on_during_aspect_recursively(with_ids=True)
        assert len(lst) == 1
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "Active"
        assert st.path == ("Root", "Active")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(
                var_name="tmp",
                expr=BinaryOp(x=Variable(name="x"), op="+", y=Integer(value=1)),
            ),
            IfBlock(
                branches=[
                    IfBlockBranch(
                        condition=BinaryOp(
                            x=Variable(name="flag"), op=">", y=Integer(value=0)
                        ),
                        statements=[
                            Operation(
                                var_name="tmp",
                                expr=BinaryOp(
                                    x=Variable(name="tmp"), op="+", y=Integer(value=10)
                                ),
                            ),
                            IfBlock(
                                branches=[
                                    IfBlockBranch(
                                        condition=BinaryOp(
                                            x=Variable(name="y"),
                                            op=">",
                                            y=Integer(value=5),
                                        ),
                                        statements=[
                                            Operation(
                                                var_name="bonus",
                                                expr=BinaryOp(
                                                    x=Variable(name="y"),
                                                    op="+",
                                                    y=Integer(value=2),
                                                ),
                                            ),
                                            Operation(
                                                var_name="z",
                                                expr=BinaryOp(
                                                    x=Variable(name="tmp"),
                                                    op="+",
                                                    y=Variable(name="bonus"),
                                                ),
                                            ),
                                        ],
                                    ),
                                    IfBlockBranch(
                                        condition=None,
                                        statements=[
                                            Operation(
                                                var_name="z",
                                                expr=BinaryOp(
                                                    x=Variable(name="tmp"),
                                                    op="-",
                                                    y=Variable(name="y"),
                                                ),
                                            )
                                        ],
                                    ),
                                ]
                            ),
                        ],
                    ),
                    IfBlockBranch(
                        condition=BinaryOp(
                            x=Variable(name="x"), op=">", y=Integer(value=3)
                        ),
                        statements=[
                            Operation(
                                var_name="tmp",
                                expr=BinaryOp(
                                    x=Variable(name="tmp"), op="+", y=Integer(value=20)
                                ),
                            ),
                            Operation(var_name="z", expr=Variable(name="tmp")),
                        ],
                    ),
                    IfBlockBranch(
                        condition=None,
                        statements=[Operation(var_name="z", expr=Variable(name="tmp"))],
                    ),
                ]
            ),
            Operation(
                var_name="x",
                expr=BinaryOp(x=Variable(name="z"), op="+", y=Variable(name="tmp")),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("Root", "Active", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "Active"
        assert on_stage.parent_ref().path == ("Root", "Active")
        assert on_stage.func_name == "Root.Active.<unnamed>"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "Active"
        assert on_stage.parent.path == ("Root", "Active")

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int x = 0;
def int y = 0;
def int z = 0;
def int flag = 0;
state Root {
    state Active {
        during {
            tmp = x + 1;
            if [flag > 0] {
                tmp = tmp + 10;
                if [y > 5] {
                    bonus = y + 2;
                    z = tmp + bonus;
                } else {
                    z = tmp - y;
                }
            } else if [x > 3] {
                tmp = tmp + 20;
                z = tmp;
            } else {
                z = tmp;
            }
            x = z + tmp;
        }
    }
    [*] -> Active;
}
            """).strip(),
            actual=str(model.to_ast_node()),
        )

    def test_to_plantuml(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
@startuml
hide empty description

skinparam state {
  BackgroundColor<<pseudo>> LightGray
  BackgroundColor<<composite>> LightBlue
  BorderColor<<pseudo>> Gray
  FontStyle<<pseudo>> italic
}

legend top left
|= Variable |= Type |= Initial Value |
| x | int | 0 |
| y | int | 0 |
| z | int | 0 |
| flag | int | 0 |
endlegend

state "Root" as root <<composite>> {
    state "Active" as root__active
    root__active : during {\\n    tmp = x + 1;\\n    if [flag > 0] {\\n        tmp = tmp + 10;\\n        if [y > 5] {\\n            bonus = y + 2;\\n            z = tmp + bonus;\\n        } else {\\n            z = tmp - y;\\n        }\\n    } else if [x > 3] {\\n        tmp = tmp + 20;\\n        z = tmp;\\n    } else {\\n        z = tmp;\\n    }\\n    x = z + tmp;\\n}
    [*] --> root__active
}
[*] --> root
root --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml(options="full")),
        )
