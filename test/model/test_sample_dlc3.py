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
def int Event  = 0;

state LX
{
    [*] -> LX2;
    !*->ERROR :: E1;

    enter {}
    enter abstract act1;

    state LX2{
        [*] -> start;
         state start {
            [*] -> LX4;
            state LX4 {
                [*] -> LX5;
                state LX5;
            }
         }
    }


    state ERROR
    {}
    ERROR ->[*];
}
    """,
        entry_name="state_machine_dsl",
    )
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.fixture()
def state_lx(model):
    return model.root_state


@pytest.fixture()
def state_lx_lx2(state_lx):
    return state_lx.substates["LX2"]


@pytest.fixture()
def state_lx_lx2_start(state_lx_lx2):
    return state_lx_lx2.substates["start"]


@pytest.fixture()
def state_lx_lx2_start_lx4(state_lx_lx2_start):
    return state_lx_lx2_start.substates["LX4"]


@pytest.fixture()
def state_lx_lx2_start_lx4_lx5(state_lx_lx2_start_lx4):
    return state_lx_lx2_start_lx4.substates["LX5"]


@pytest.fixture()
def state_lx_error(state_lx):
    return state_lx.substates["ERROR"]


@pytest.mark.unittest
class TestModelStateLx:
    def test_model(self, model):
        assert model.defines == {
            "Event": VarDefine(name="Event", type="int", init=Integer(value=0))
        }
        assert model.root_state.name == "LX"
        assert model.root_state.path == ("LX",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="Event", type="int", expr=dsl_nodes.Integer(raw="0")
            )
        ]
        assert ast_node.root_state.name == "LX"

    def test_state_lx(self, state_lx):
        assert state_lx.name == "LX"
        assert state_lx.path == ("LX",)
        assert sorted(state_lx.substates.keys()) == ["ERROR", "LX2"]
        assert state_lx.events == {"E1": Event(name="E1", state_path=("LX",))}
        assert len(state_lx.transitions) == 4
        assert state_lx.transitions[0].from_state == "LX2"
        assert state_lx.transitions[0].to_state == "ERROR"
        assert state_lx.transitions[0].event == Event(name="E1", state_path=("LX",))
        assert state_lx.transitions[0].guard is None
        assert state_lx.transitions[0].effects == []
        assert state_lx.transitions[0].parent_ref().name == "LX"
        assert state_lx.transitions[0].parent_ref().path == ("LX",)
        assert state_lx.transitions[1].from_state == "ERROR"
        assert state_lx.transitions[1].to_state == "ERROR"
        assert state_lx.transitions[1].event == Event(name="E1", state_path=("LX",))
        assert state_lx.transitions[1].guard is None
        assert state_lx.transitions[1].effects == []
        assert state_lx.transitions[1].parent_ref().name == "LX"
        assert state_lx.transitions[1].parent_ref().path == ("LX",)
        assert state_lx.transitions[2].from_state == INIT_STATE
        assert state_lx.transitions[2].to_state == "LX2"
        assert state_lx.transitions[2].event is None
        assert state_lx.transitions[2].guard is None
        assert state_lx.transitions[2].effects == []
        assert state_lx.transitions[2].parent_ref().name == "LX"
        assert state_lx.transitions[2].parent_ref().path == ("LX",)
        assert state_lx.transitions[3].from_state == "ERROR"
        assert state_lx.transitions[3].to_state == EXIT_STATE
        assert state_lx.transitions[3].event is None
        assert state_lx.transitions[3].guard is None
        assert state_lx.transitions[3].effects == []
        assert state_lx.transitions[3].parent_ref().name == "LX"
        assert state_lx.transitions[3].parent_ref().path == ("LX",)
        assert sorted(state_lx.named_functions.keys()) == ["act1"]
        assert state_lx.named_functions["act1"].stage == "enter"
        assert state_lx.named_functions["act1"].aspect is None
        assert state_lx.named_functions["act1"].name == "act1"
        assert state_lx.named_functions["act1"].doc is None
        assert state_lx.named_functions["act1"].operations == []
        assert state_lx.named_functions["act1"].is_abstract
        assert state_lx.named_functions["act1"].state_path == ("LX", "act1")
        assert state_lx.named_functions["act1"].ref is None
        assert state_lx.named_functions["act1"].ref_state_path is None
        assert state_lx.named_functions["act1"].parent_ref().name == "LX"
        assert state_lx.named_functions["act1"].parent_ref().path == ("LX",)
        assert not state_lx.named_functions["act1"].is_aspect
        assert not state_lx.named_functions["act1"].is_ref
        assert state_lx.named_functions["act1"].parent.name == "LX"
        assert state_lx.named_functions["act1"].parent.path == ("LX",)
        assert len(state_lx.on_enters) == 2
        assert state_lx.on_enters[0].stage == "enter"
        assert state_lx.on_enters[0].aspect is None
        assert state_lx.on_enters[0].name is None
        assert state_lx.on_enters[0].doc is None
        assert state_lx.on_enters[0].operations == []
        assert not state_lx.on_enters[0].is_abstract
        assert state_lx.on_enters[0].state_path == ("LX", None)
        assert state_lx.on_enters[0].ref is None
        assert state_lx.on_enters[0].ref_state_path is None
        assert state_lx.on_enters[0].parent_ref().name == "LX"
        assert state_lx.on_enters[0].parent_ref().path == ("LX",)
        assert not state_lx.on_enters[0].is_aspect
        assert not state_lx.on_enters[0].is_ref
        assert state_lx.on_enters[0].parent.name == "LX"
        assert state_lx.on_enters[0].parent.path == ("LX",)
        assert state_lx.on_enters[1].stage == "enter"
        assert state_lx.on_enters[1].aspect is None
        assert state_lx.on_enters[1].name == "act1"
        assert state_lx.on_enters[1].doc is None
        assert state_lx.on_enters[1].operations == []
        assert state_lx.on_enters[1].is_abstract
        assert state_lx.on_enters[1].state_path == ("LX", "act1")
        assert state_lx.on_enters[1].ref is None
        assert state_lx.on_enters[1].ref_state_path is None
        assert state_lx.on_enters[1].parent_ref().name == "LX"
        assert state_lx.on_enters[1].parent_ref().path == ("LX",)
        assert not state_lx.on_enters[1].is_aspect
        assert not state_lx.on_enters[1].is_ref
        assert state_lx.on_enters[1].parent.name == "LX"
        assert state_lx.on_enters[1].parent.path == ("LX",)
        assert state_lx.on_durings == []
        assert state_lx.on_exits == []
        assert state_lx.on_during_aspects == []
        assert state_lx.parent_ref is None
        assert state_lx.substate_name_to_id == {"LX2": 0, "ERROR": 1}
        assert state_lx.extra_name is None
        assert not state_lx.is_pseudo
        assert state_lx.abstract_on_during_aspects == []
        assert state_lx.abstract_on_durings == []
        assert len(state_lx.abstract_on_enters) == 1
        assert state_lx.abstract_on_enters[0].stage == "enter"
        assert state_lx.abstract_on_enters[0].aspect is None
        assert state_lx.abstract_on_enters[0].name == "act1"
        assert state_lx.abstract_on_enters[0].doc is None
        assert state_lx.abstract_on_enters[0].operations == []
        assert state_lx.abstract_on_enters[0].is_abstract
        assert state_lx.abstract_on_enters[0].state_path == ("LX", "act1")
        assert state_lx.abstract_on_enters[0].ref is None
        assert state_lx.abstract_on_enters[0].ref_state_path is None
        assert state_lx.abstract_on_enters[0].parent_ref().name == "LX"
        assert state_lx.abstract_on_enters[0].parent_ref().path == ("LX",)
        assert not state_lx.abstract_on_enters[0].is_aspect
        assert not state_lx.abstract_on_enters[0].is_ref
        assert state_lx.abstract_on_enters[0].parent.name == "LX"
        assert state_lx.abstract_on_enters[0].parent.path == ("LX",)
        assert state_lx.abstract_on_exits == []
        assert not state_lx.is_leaf_state
        assert state_lx.is_root_state
        assert state_lx.non_abstract_on_during_aspects == []
        assert state_lx.non_abstract_on_durings == []
        assert len(state_lx.non_abstract_on_enters) == 1
        assert state_lx.non_abstract_on_enters[0].stage == "enter"
        assert state_lx.non_abstract_on_enters[0].aspect is None
        assert state_lx.non_abstract_on_enters[0].name is None
        assert state_lx.non_abstract_on_enters[0].doc is None
        assert state_lx.non_abstract_on_enters[0].operations == []
        assert not state_lx.non_abstract_on_enters[0].is_abstract
        assert state_lx.non_abstract_on_enters[0].state_path == ("LX", None)
        assert state_lx.non_abstract_on_enters[0].ref is None
        assert state_lx.non_abstract_on_enters[0].ref_state_path is None
        assert state_lx.non_abstract_on_enters[0].parent_ref().name == "LX"
        assert state_lx.non_abstract_on_enters[0].parent_ref().path == ("LX",)
        assert not state_lx.non_abstract_on_enters[0].is_aspect
        assert not state_lx.non_abstract_on_enters[0].is_ref
        assert state_lx.non_abstract_on_enters[0].parent.name == "LX"
        assert state_lx.non_abstract_on_enters[0].parent.path == ("LX",)
        assert state_lx.non_abstract_on_exits == []
        assert state_lx.parent is None
        assert len(state_lx.transitions_entering_children) == 1
        assert state_lx.transitions_entering_children[0].from_state == INIT_STATE
        assert state_lx.transitions_entering_children[0].to_state == "LX2"
        assert state_lx.transitions_entering_children[0].event is None
        assert state_lx.transitions_entering_children[0].guard is None
        assert state_lx.transitions_entering_children[0].effects == []
        assert state_lx.transitions_entering_children[0].parent_ref().name == "LX"
        assert state_lx.transitions_entering_children[0].parent_ref().path == ("LX",)
        assert len(state_lx.transitions_entering_children_simplified) == 1
        assert (
            state_lx.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert state_lx.transitions_entering_children_simplified[0].to_state == "LX2"
        assert state_lx.transitions_entering_children_simplified[0].event is None
        assert state_lx.transitions_entering_children_simplified[0].guard is None
        assert state_lx.transitions_entering_children_simplified[0].effects == []
        assert (
            state_lx.transitions_entering_children_simplified[0].parent_ref().name
            == "LX"
        )
        assert state_lx.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("LX",)
        assert len(state_lx.transitions_from) == 1
        assert state_lx.transitions_from[0].from_state == "LX"
        assert state_lx.transitions_from[0].to_state == EXIT_STATE
        assert state_lx.transitions_from[0].event is None
        assert state_lx.transitions_from[0].guard is None
        assert state_lx.transitions_from[0].effects == []
        assert state_lx.transitions_from[0].parent_ref is None
        assert len(state_lx.transitions_to) == 1
        assert state_lx.transitions_to[0].from_state == INIT_STATE
        assert state_lx.transitions_to[0].to_state == "LX"
        assert state_lx.transitions_to[0].event is None
        assert state_lx.transitions_to[0].guard is None
        assert state_lx.transitions_to[0].effects == []
        assert state_lx.transitions_to[0].parent_ref is None

    def test_state_lx_to_ast_node(self, state_lx):
        ast_node = state_lx.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="LX",
            extra_name=None,
            substates=[
                dsl_nodes.StateDefinition(
                    name="LX2",
                    extra_name=None,
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="start",
                            extra_name=None,
                            substates=[
                                dsl_nodes.StateDefinition(
                                    name="LX4",
                                    extra_name=None,
                                    substates=[
                                        dsl_nodes.StateDefinition(
                                            name="LX5",
                                            extra_name=None,
                                            substates=[],
                                            transitions=[],
                                            enters=[],
                                            durings=[],
                                            exits=[],
                                            during_aspects=[],
                                            force_transitions=[],
                                            is_pseudo=False,
                                        )
                                    ],
                                    transitions=[
                                        dsl_nodes.TransitionDefinition(
                                            from_state="LX5",
                                            to_state=EXIT_STATE,
                                            event_id=dsl_nodes.ChainID(
                                                path=["E1"], is_absolute=True
                                            ),
                                            condition_expr=None,
                                            post_operations=[],
                                        ),
                                        dsl_nodes.TransitionDefinition(
                                            from_state=INIT_STATE,
                                            to_state="LX5",
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
                                    is_pseudo=False,
                                )
                            ],
                            transitions=[
                                dsl_nodes.TransitionDefinition(
                                    from_state="LX4",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["E1"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state=INIT_STATE,
                                    to_state="LX4",
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
                            is_pseudo=False,
                        )
                    ],
                    transitions=[
                        dsl_nodes.TransitionDefinition(
                            from_state="start",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=True),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="start",
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
                    is_pseudo=False,
                ),
                dsl_nodes.StateDefinition(
                    name="ERROR",
                    extra_name=None,
                    substates=[],
                    transitions=[],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                ),
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="LX2",
                    to_state="ERROR",
                    event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="ERROR",
                    to_state="ERROR",
                    event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="LX2",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="ERROR",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
            ],
            enters=[
                dsl_nodes.EnterOperations(operations=[], name=None),
                dsl_nodes.EnterAbstractFunction(name="act1", doc=None),
            ],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_lx_list_on_enters(self, state_lx):
        lst = state_lx.list_on_enters()
        assert len(lst) == 2
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("LX", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)
        on_stage = lst[1]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "act1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("LX", "act1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)

        lst = state_lx.list_on_enters(with_ids=False)
        assert len(lst) == 2
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("LX", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)
        on_stage = lst[1]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "act1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("LX", "act1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)

        lst = state_lx.list_on_enters(with_ids=True)
        assert len(lst) == 2
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("LX", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)
        id_, on_stage = lst[1]
        assert id_ == 2
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "act1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("LX", "act1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)

        lst = state_lx.list_on_enters(is_abstract=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("LX", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)

        lst = state_lx.list_on_enters(is_abstract=False, with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("LX", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)

        lst = state_lx.list_on_enters(is_abstract=False, with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("LX", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)

        lst = state_lx.list_on_enters(is_abstract=True)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "act1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("LX", "act1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)

        lst = state_lx.list_on_enters(is_abstract=True, with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "act1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("LX", "act1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)

        lst = state_lx.list_on_enters(is_abstract=True, with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 2
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "act1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("LX", "act1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LX"
        assert on_stage.parent_ref().path == ("LX",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LX"
        assert on_stage.parent.path == ("LX",)

    def test_state_lx_during_aspects(self, state_lx):
        lst = state_lx.list_on_during_aspects()
        assert lst == []

        lst = state_lx.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lx.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lx.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lx.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_lx.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_lx.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lx.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_lx.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_lx_lx2(self, state_lx_lx2):
        assert state_lx_lx2.name == "LX2"
        assert state_lx_lx2.path == ("LX", "LX2")
        assert sorted(state_lx_lx2.substates.keys()) == ["start"]
        assert state_lx_lx2.events == {}
        assert len(state_lx_lx2.transitions) == 2
        assert state_lx_lx2.transitions[0].from_state == "start"
        assert state_lx_lx2.transitions[0].to_state == EXIT_STATE
        assert state_lx_lx2.transitions[0].event == Event(name="E1", state_path=("LX",))
        assert state_lx_lx2.transitions[0].guard is None
        assert state_lx_lx2.transitions[0].effects == []
        assert state_lx_lx2.transitions[0].parent_ref().name == "LX2"
        assert state_lx_lx2.transitions[0].parent_ref().path == ("LX", "LX2")
        assert state_lx_lx2.transitions[1].from_state == INIT_STATE
        assert state_lx_lx2.transitions[1].to_state == "start"
        assert state_lx_lx2.transitions[1].event is None
        assert state_lx_lx2.transitions[1].guard is None
        assert state_lx_lx2.transitions[1].effects == []
        assert state_lx_lx2.transitions[1].parent_ref().name == "LX2"
        assert state_lx_lx2.transitions[1].parent_ref().path == ("LX", "LX2")
        assert state_lx_lx2.named_functions == {}
        assert state_lx_lx2.on_enters == []
        assert state_lx_lx2.on_durings == []
        assert state_lx_lx2.on_exits == []
        assert state_lx_lx2.on_during_aspects == []
        assert state_lx_lx2.parent_ref().name == "LX"
        assert state_lx_lx2.parent_ref().path == ("LX",)
        assert state_lx_lx2.substate_name_to_id == {"start": 0}
        assert state_lx_lx2.extra_name is None
        assert not state_lx_lx2.is_pseudo
        assert state_lx_lx2.abstract_on_during_aspects == []
        assert state_lx_lx2.abstract_on_durings == []
        assert state_lx_lx2.abstract_on_enters == []
        assert state_lx_lx2.abstract_on_exits == []
        assert not state_lx_lx2.is_leaf_state
        assert not state_lx_lx2.is_root_state
        assert state_lx_lx2.non_abstract_on_during_aspects == []
        assert state_lx_lx2.non_abstract_on_durings == []
        assert state_lx_lx2.non_abstract_on_enters == []
        assert state_lx_lx2.non_abstract_on_exits == []
        assert state_lx_lx2.parent.name == "LX"
        assert state_lx_lx2.parent.path == ("LX",)
        assert len(state_lx_lx2.transitions_entering_children) == 1
        assert state_lx_lx2.transitions_entering_children[0].from_state == INIT_STATE
        assert state_lx_lx2.transitions_entering_children[0].to_state == "start"
        assert state_lx_lx2.transitions_entering_children[0].event is None
        assert state_lx_lx2.transitions_entering_children[0].guard is None
        assert state_lx_lx2.transitions_entering_children[0].effects == []
        assert state_lx_lx2.transitions_entering_children[0].parent_ref().name == "LX2"
        assert state_lx_lx2.transitions_entering_children[0].parent_ref().path == (
            "LX",
            "LX2",
        )
        assert len(state_lx_lx2.transitions_entering_children_simplified) == 1
        assert (
            state_lx_lx2.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_lx_lx2.transitions_entering_children_simplified[0].to_state == "start"
        )
        assert state_lx_lx2.transitions_entering_children_simplified[0].event is None
        assert state_lx_lx2.transitions_entering_children_simplified[0].guard is None
        assert state_lx_lx2.transitions_entering_children_simplified[0].effects == []
        assert (
            state_lx_lx2.transitions_entering_children_simplified[0].parent_ref().name
            == "LX2"
        )
        assert state_lx_lx2.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("LX", "LX2")
        assert len(state_lx_lx2.transitions_from) == 1
        assert state_lx_lx2.transitions_from[0].from_state == "LX2"
        assert state_lx_lx2.transitions_from[0].to_state == "ERROR"
        assert state_lx_lx2.transitions_from[0].event == Event(
            name="E1", state_path=("LX",)
        )
        assert state_lx_lx2.transitions_from[0].guard is None
        assert state_lx_lx2.transitions_from[0].effects == []
        assert state_lx_lx2.transitions_from[0].parent_ref().name == "LX"
        assert state_lx_lx2.transitions_from[0].parent_ref().path == ("LX",)
        assert len(state_lx_lx2.transitions_to) == 1
        assert state_lx_lx2.transitions_to[0].from_state == INIT_STATE
        assert state_lx_lx2.transitions_to[0].to_state == "LX2"
        assert state_lx_lx2.transitions_to[0].event is None
        assert state_lx_lx2.transitions_to[0].guard is None
        assert state_lx_lx2.transitions_to[0].effects == []
        assert state_lx_lx2.transitions_to[0].parent_ref().name == "LX"
        assert state_lx_lx2.transitions_to[0].parent_ref().path == ("LX",)

    def test_state_lx_lx2_to_ast_node(self, state_lx_lx2):
        ast_node = state_lx_lx2.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="LX2",
            extra_name=None,
            substates=[
                dsl_nodes.StateDefinition(
                    name="start",
                    extra_name=None,
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="LX4",
                            extra_name=None,
                            substates=[
                                dsl_nodes.StateDefinition(
                                    name="LX5",
                                    extra_name=None,
                                    substates=[],
                                    transitions=[],
                                    enters=[],
                                    durings=[],
                                    exits=[],
                                    during_aspects=[],
                                    force_transitions=[],
                                    is_pseudo=False,
                                )
                            ],
                            transitions=[
                                dsl_nodes.TransitionDefinition(
                                    from_state="LX5",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["E1"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state=INIT_STATE,
                                    to_state="LX5",
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
                            is_pseudo=False,
                        )
                    ],
                    transitions=[
                        dsl_nodes.TransitionDefinition(
                            from_state="LX4",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=True),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="LX4",
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
                    is_pseudo=False,
                )
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="start",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="start",
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
            is_pseudo=False,
        )

    def test_state_lx_lx2_list_on_enters(self, state_lx_lx2):
        lst = state_lx_lx2.list_on_enters()
        assert lst == []

        lst = state_lx_lx2.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_lx_lx2.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_lx_lx2.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_lx_lx2.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_lx_lx2.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_lx_lx2.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_lx_lx2.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_lx_lx2.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_lx_lx2_during_aspects(self, state_lx_lx2):
        lst = state_lx_lx2.list_on_during_aspects()
        assert lst == []

        lst = state_lx_lx2.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lx_lx2.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lx_lx2.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lx_lx2.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_lx_lx2.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_lx_lx2.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lx_lx2.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_lx_lx2.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_lx_lx2_start(self, state_lx_lx2_start):
        assert state_lx_lx2_start.name == "start"
        assert state_lx_lx2_start.path == ("LX", "LX2", "start")
        assert sorted(state_lx_lx2_start.substates.keys()) == ["LX4"]
        assert state_lx_lx2_start.events == {}
        assert len(state_lx_lx2_start.transitions) == 2
        assert state_lx_lx2_start.transitions[0].from_state == "LX4"
        assert state_lx_lx2_start.transitions[0].to_state == EXIT_STATE
        assert state_lx_lx2_start.transitions[0].event == Event(
            name="E1", state_path=("LX",)
        )
        assert state_lx_lx2_start.transitions[0].guard is None
        assert state_lx_lx2_start.transitions[0].effects == []
        assert state_lx_lx2_start.transitions[0].parent_ref().name == "start"
        assert state_lx_lx2_start.transitions[0].parent_ref().path == (
            "LX",
            "LX2",
            "start",
        )
        assert state_lx_lx2_start.transitions[1].from_state == INIT_STATE
        assert state_lx_lx2_start.transitions[1].to_state == "LX4"
        assert state_lx_lx2_start.transitions[1].event is None
        assert state_lx_lx2_start.transitions[1].guard is None
        assert state_lx_lx2_start.transitions[1].effects == []
        assert state_lx_lx2_start.transitions[1].parent_ref().name == "start"
        assert state_lx_lx2_start.transitions[1].parent_ref().path == (
            "LX",
            "LX2",
            "start",
        )
        assert state_lx_lx2_start.named_functions == {}
        assert state_lx_lx2_start.on_enters == []
        assert state_lx_lx2_start.on_durings == []
        assert state_lx_lx2_start.on_exits == []
        assert state_lx_lx2_start.on_during_aspects == []
        assert state_lx_lx2_start.parent_ref().name == "LX2"
        assert state_lx_lx2_start.parent_ref().path == ("LX", "LX2")
        assert state_lx_lx2_start.substate_name_to_id == {"LX4": 0}
        assert state_lx_lx2_start.extra_name is None
        assert not state_lx_lx2_start.is_pseudo
        assert state_lx_lx2_start.abstract_on_during_aspects == []
        assert state_lx_lx2_start.abstract_on_durings == []
        assert state_lx_lx2_start.abstract_on_enters == []
        assert state_lx_lx2_start.abstract_on_exits == []
        assert not state_lx_lx2_start.is_leaf_state
        assert not state_lx_lx2_start.is_root_state
        assert state_lx_lx2_start.non_abstract_on_during_aspects == []
        assert state_lx_lx2_start.non_abstract_on_durings == []
        assert state_lx_lx2_start.non_abstract_on_enters == []
        assert state_lx_lx2_start.non_abstract_on_exits == []
        assert state_lx_lx2_start.parent.name == "LX2"
        assert state_lx_lx2_start.parent.path == ("LX", "LX2")
        assert len(state_lx_lx2_start.transitions_entering_children) == 1
        assert (
            state_lx_lx2_start.transitions_entering_children[0].from_state == INIT_STATE
        )
        assert state_lx_lx2_start.transitions_entering_children[0].to_state == "LX4"
        assert state_lx_lx2_start.transitions_entering_children[0].event is None
        assert state_lx_lx2_start.transitions_entering_children[0].guard is None
        assert state_lx_lx2_start.transitions_entering_children[0].effects == []
        assert (
            state_lx_lx2_start.transitions_entering_children[0].parent_ref().name
            == "start"
        )
        assert state_lx_lx2_start.transitions_entering_children[
            0
        ].parent_ref().path == ("LX", "LX2", "start")
        assert len(state_lx_lx2_start.transitions_entering_children_simplified) == 1
        assert (
            state_lx_lx2_start.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_lx_lx2_start.transitions_entering_children_simplified[0].to_state
            == "LX4"
        )
        assert (
            state_lx_lx2_start.transitions_entering_children_simplified[0].event is None
        )
        assert (
            state_lx_lx2_start.transitions_entering_children_simplified[0].guard is None
        )
        assert (
            state_lx_lx2_start.transitions_entering_children_simplified[0].effects == []
        )
        assert (
            state_lx_lx2_start.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "start"
        )
        assert state_lx_lx2_start.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("LX", "LX2", "start")
        assert len(state_lx_lx2_start.transitions_from) == 1
        assert state_lx_lx2_start.transitions_from[0].from_state == "start"
        assert state_lx_lx2_start.transitions_from[0].to_state == EXIT_STATE
        assert state_lx_lx2_start.transitions_from[0].event == Event(
            name="E1", state_path=("LX",)
        )
        assert state_lx_lx2_start.transitions_from[0].guard is None
        assert state_lx_lx2_start.transitions_from[0].effects == []
        assert state_lx_lx2_start.transitions_from[0].parent_ref().name == "LX2"
        assert state_lx_lx2_start.transitions_from[0].parent_ref().path == ("LX", "LX2")
        assert len(state_lx_lx2_start.transitions_to) == 1
        assert state_lx_lx2_start.transitions_to[0].from_state == INIT_STATE
        assert state_lx_lx2_start.transitions_to[0].to_state == "start"
        assert state_lx_lx2_start.transitions_to[0].event is None
        assert state_lx_lx2_start.transitions_to[0].guard is None
        assert state_lx_lx2_start.transitions_to[0].effects == []
        assert state_lx_lx2_start.transitions_to[0].parent_ref().name == "LX2"
        assert state_lx_lx2_start.transitions_to[0].parent_ref().path == ("LX", "LX2")

    def test_state_lx_lx2_start_to_ast_node(self, state_lx_lx2_start):
        ast_node = state_lx_lx2_start.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="start",
            extra_name=None,
            substates=[
                dsl_nodes.StateDefinition(
                    name="LX4",
                    extra_name=None,
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="LX5",
                            extra_name=None,
                            substates=[],
                            transitions=[],
                            enters=[],
                            durings=[],
                            exits=[],
                            during_aspects=[],
                            force_transitions=[],
                            is_pseudo=False,
                        )
                    ],
                    transitions=[
                        dsl_nodes.TransitionDefinition(
                            from_state="LX5",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=True),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="LX5",
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
                    is_pseudo=False,
                )
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="LX4",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="LX4",
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
            is_pseudo=False,
        )

    def test_state_lx_lx2_start_list_on_enters(self, state_lx_lx2_start):
        lst = state_lx_lx2_start.list_on_enters()
        assert lst == []

        lst = state_lx_lx2_start.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_lx_lx2_start.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_lx_lx2_start.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_lx_lx2_start.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_lx_lx2_start.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_lx_lx2_start.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_lx_lx2_start.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_lx_lx2_start.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_lx_lx2_start_during_aspects(self, state_lx_lx2_start):
        lst = state_lx_lx2_start.list_on_during_aspects()
        assert lst == []

        lst = state_lx_lx2_start.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lx_lx2_start.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lx_lx2_start.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lx_lx2_start.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_lx_lx2_start.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_lx_lx2_start.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lx_lx2_start.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_lx_lx2_start.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_lx_lx2_start_lx4(self, state_lx_lx2_start_lx4):
        assert state_lx_lx2_start_lx4.name == "LX4"
        assert state_lx_lx2_start_lx4.path == ("LX", "LX2", "start", "LX4")
        assert sorted(state_lx_lx2_start_lx4.substates.keys()) == ["LX5"]
        assert state_lx_lx2_start_lx4.events == {}
        assert len(state_lx_lx2_start_lx4.transitions) == 2
        assert state_lx_lx2_start_lx4.transitions[0].from_state == "LX5"
        assert state_lx_lx2_start_lx4.transitions[0].to_state == EXIT_STATE
        assert state_lx_lx2_start_lx4.transitions[0].event == Event(
            name="E1", state_path=("LX",)
        )
        assert state_lx_lx2_start_lx4.transitions[0].guard is None
        assert state_lx_lx2_start_lx4.transitions[0].effects == []
        assert state_lx_lx2_start_lx4.transitions[0].parent_ref().name == "LX4"
        assert state_lx_lx2_start_lx4.transitions[0].parent_ref().path == (
            "LX",
            "LX2",
            "start",
            "LX4",
        )
        assert state_lx_lx2_start_lx4.transitions[1].from_state == INIT_STATE
        assert state_lx_lx2_start_lx4.transitions[1].to_state == "LX5"
        assert state_lx_lx2_start_lx4.transitions[1].event is None
        assert state_lx_lx2_start_lx4.transitions[1].guard is None
        assert state_lx_lx2_start_lx4.transitions[1].effects == []
        assert state_lx_lx2_start_lx4.transitions[1].parent_ref().name == "LX4"
        assert state_lx_lx2_start_lx4.transitions[1].parent_ref().path == (
            "LX",
            "LX2",
            "start",
            "LX4",
        )
        assert state_lx_lx2_start_lx4.named_functions == {}
        assert state_lx_lx2_start_lx4.on_enters == []
        assert state_lx_lx2_start_lx4.on_durings == []
        assert state_lx_lx2_start_lx4.on_exits == []
        assert state_lx_lx2_start_lx4.on_during_aspects == []
        assert state_lx_lx2_start_lx4.parent_ref().name == "start"
        assert state_lx_lx2_start_lx4.parent_ref().path == ("LX", "LX2", "start")
        assert state_lx_lx2_start_lx4.substate_name_to_id == {"LX5": 0}
        assert state_lx_lx2_start_lx4.extra_name is None
        assert not state_lx_lx2_start_lx4.is_pseudo
        assert state_lx_lx2_start_lx4.abstract_on_during_aspects == []
        assert state_lx_lx2_start_lx4.abstract_on_durings == []
        assert state_lx_lx2_start_lx4.abstract_on_enters == []
        assert state_lx_lx2_start_lx4.abstract_on_exits == []
        assert not state_lx_lx2_start_lx4.is_leaf_state
        assert not state_lx_lx2_start_lx4.is_root_state
        assert state_lx_lx2_start_lx4.non_abstract_on_during_aspects == []
        assert state_lx_lx2_start_lx4.non_abstract_on_durings == []
        assert state_lx_lx2_start_lx4.non_abstract_on_enters == []
        assert state_lx_lx2_start_lx4.non_abstract_on_exits == []
        assert state_lx_lx2_start_lx4.parent.name == "start"
        assert state_lx_lx2_start_lx4.parent.path == ("LX", "LX2", "start")
        assert len(state_lx_lx2_start_lx4.transitions_entering_children) == 1
        assert (
            state_lx_lx2_start_lx4.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert state_lx_lx2_start_lx4.transitions_entering_children[0].to_state == "LX5"
        assert state_lx_lx2_start_lx4.transitions_entering_children[0].event is None
        assert state_lx_lx2_start_lx4.transitions_entering_children[0].guard is None
        assert state_lx_lx2_start_lx4.transitions_entering_children[0].effects == []
        assert (
            state_lx_lx2_start_lx4.transitions_entering_children[0].parent_ref().name
            == "LX4"
        )
        assert state_lx_lx2_start_lx4.transitions_entering_children[
            0
        ].parent_ref().path == ("LX", "LX2", "start", "LX4")
        assert len(state_lx_lx2_start_lx4.transitions_entering_children_simplified) == 1
        assert (
            state_lx_lx2_start_lx4.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_lx_lx2_start_lx4.transitions_entering_children_simplified[0].to_state
            == "LX5"
        )
        assert (
            state_lx_lx2_start_lx4.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_lx_lx2_start_lx4.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_lx_lx2_start_lx4.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_lx_lx2_start_lx4.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "LX4"
        )
        assert state_lx_lx2_start_lx4.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("LX", "LX2", "start", "LX4")
        assert len(state_lx_lx2_start_lx4.transitions_from) == 1
        assert state_lx_lx2_start_lx4.transitions_from[0].from_state == "LX4"
        assert state_lx_lx2_start_lx4.transitions_from[0].to_state == EXIT_STATE
        assert state_lx_lx2_start_lx4.transitions_from[0].event == Event(
            name="E1", state_path=("LX",)
        )
        assert state_lx_lx2_start_lx4.transitions_from[0].guard is None
        assert state_lx_lx2_start_lx4.transitions_from[0].effects == []
        assert state_lx_lx2_start_lx4.transitions_from[0].parent_ref().name == "start"
        assert state_lx_lx2_start_lx4.transitions_from[0].parent_ref().path == (
            "LX",
            "LX2",
            "start",
        )
        assert len(state_lx_lx2_start_lx4.transitions_to) == 1
        assert state_lx_lx2_start_lx4.transitions_to[0].from_state == INIT_STATE
        assert state_lx_lx2_start_lx4.transitions_to[0].to_state == "LX4"
        assert state_lx_lx2_start_lx4.transitions_to[0].event is None
        assert state_lx_lx2_start_lx4.transitions_to[0].guard is None
        assert state_lx_lx2_start_lx4.transitions_to[0].effects == []
        assert state_lx_lx2_start_lx4.transitions_to[0].parent_ref().name == "start"
        assert state_lx_lx2_start_lx4.transitions_to[0].parent_ref().path == (
            "LX",
            "LX2",
            "start",
        )

    def test_state_lx_lx2_start_lx4_to_ast_node(self, state_lx_lx2_start_lx4):
        ast_node = state_lx_lx2_start_lx4.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="LX4",
            extra_name=None,
            substates=[
                dsl_nodes.StateDefinition(
                    name="LX5",
                    extra_name=None,
                    substates=[],
                    transitions=[],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                )
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="LX5",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="LX5",
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
            is_pseudo=False,
        )

    def test_state_lx_lx2_start_lx4_list_on_enters(self, state_lx_lx2_start_lx4):
        lst = state_lx_lx2_start_lx4.list_on_enters()
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_lx_lx2_start_lx4_during_aspects(self, state_lx_lx2_start_lx4):
        lst = state_lx_lx2_start_lx4.list_on_during_aspects()
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_lx_lx2_start_lx4.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_lx_lx2_start_lx4_lx5(self, state_lx_lx2_start_lx4_lx5):
        assert state_lx_lx2_start_lx4_lx5.name == "LX5"
        assert state_lx_lx2_start_lx4_lx5.path == ("LX", "LX2", "start", "LX4", "LX5")
        assert sorted(state_lx_lx2_start_lx4_lx5.substates.keys()) == []
        assert state_lx_lx2_start_lx4_lx5.events == {}
        assert state_lx_lx2_start_lx4_lx5.transitions == []
        assert state_lx_lx2_start_lx4_lx5.named_functions == {}
        assert state_lx_lx2_start_lx4_lx5.on_enters == []
        assert state_lx_lx2_start_lx4_lx5.on_durings == []
        assert state_lx_lx2_start_lx4_lx5.on_exits == []
        assert state_lx_lx2_start_lx4_lx5.on_during_aspects == []
        assert state_lx_lx2_start_lx4_lx5.parent_ref().name == "LX4"
        assert state_lx_lx2_start_lx4_lx5.parent_ref().path == (
            "LX",
            "LX2",
            "start",
            "LX4",
        )
        assert state_lx_lx2_start_lx4_lx5.substate_name_to_id == {}
        assert state_lx_lx2_start_lx4_lx5.extra_name is None
        assert not state_lx_lx2_start_lx4_lx5.is_pseudo
        assert state_lx_lx2_start_lx4_lx5.abstract_on_during_aspects == []
        assert state_lx_lx2_start_lx4_lx5.abstract_on_durings == []
        assert state_lx_lx2_start_lx4_lx5.abstract_on_enters == []
        assert state_lx_lx2_start_lx4_lx5.abstract_on_exits == []
        assert state_lx_lx2_start_lx4_lx5.is_leaf_state
        assert not state_lx_lx2_start_lx4_lx5.is_root_state
        assert state_lx_lx2_start_lx4_lx5.non_abstract_on_during_aspects == []
        assert state_lx_lx2_start_lx4_lx5.non_abstract_on_durings == []
        assert state_lx_lx2_start_lx4_lx5.non_abstract_on_enters == []
        assert state_lx_lx2_start_lx4_lx5.non_abstract_on_exits == []
        assert state_lx_lx2_start_lx4_lx5.parent.name == "LX4"
        assert state_lx_lx2_start_lx4_lx5.parent.path == ("LX", "LX2", "start", "LX4")
        assert state_lx_lx2_start_lx4_lx5.transitions_entering_children == []
        assert (
            len(state_lx_lx2_start_lx4_lx5.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_lx_lx2_start_lx4_lx5.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_lx_lx2_start_lx4_lx5.transitions_from) == 1
        assert state_lx_lx2_start_lx4_lx5.transitions_from[0].from_state == "LX5"
        assert state_lx_lx2_start_lx4_lx5.transitions_from[0].to_state == EXIT_STATE
        assert state_lx_lx2_start_lx4_lx5.transitions_from[0].event == Event(
            name="E1", state_path=("LX",)
        )
        assert state_lx_lx2_start_lx4_lx5.transitions_from[0].guard is None
        assert state_lx_lx2_start_lx4_lx5.transitions_from[0].effects == []
        assert state_lx_lx2_start_lx4_lx5.transitions_from[0].parent_ref().name == "LX4"
        assert state_lx_lx2_start_lx4_lx5.transitions_from[0].parent_ref().path == (
            "LX",
            "LX2",
            "start",
            "LX4",
        )
        assert len(state_lx_lx2_start_lx4_lx5.transitions_to) == 1
        assert state_lx_lx2_start_lx4_lx5.transitions_to[0].from_state == INIT_STATE
        assert state_lx_lx2_start_lx4_lx5.transitions_to[0].to_state == "LX5"
        assert state_lx_lx2_start_lx4_lx5.transitions_to[0].event is None
        assert state_lx_lx2_start_lx4_lx5.transitions_to[0].guard is None
        assert state_lx_lx2_start_lx4_lx5.transitions_to[0].effects == []
        assert state_lx_lx2_start_lx4_lx5.transitions_to[0].parent_ref().name == "LX4"
        assert state_lx_lx2_start_lx4_lx5.transitions_to[0].parent_ref().path == (
            "LX",
            "LX2",
            "start",
            "LX4",
        )

    def test_state_lx_lx2_start_lx4_lx5_to_ast_node(self, state_lx_lx2_start_lx4_lx5):
        ast_node = state_lx_lx2_start_lx4_lx5.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="LX5",
            extra_name=None,
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_lx_lx2_start_lx4_lx5_list_on_enters(
        self, state_lx_lx2_start_lx4_lx5
    ):
        lst = state_lx_lx2_start_lx4_lx5.list_on_enters()
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_lx_lx2_start_lx4_lx5_during_aspects(
        self, state_lx_lx2_start_lx4_lx5
    ):
        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspects()
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_lx_lx2_start_lx4_lx5_during_aspect_recursively(
        self, state_lx_lx2_start_lx4_lx5
    ):
        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_lx_lx2_start_lx4_lx5.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_lx_error(self, state_lx_error):
        assert state_lx_error.name == "ERROR"
        assert state_lx_error.path == ("LX", "ERROR")
        assert sorted(state_lx_error.substates.keys()) == []
        assert state_lx_error.events == {}
        assert state_lx_error.transitions == []
        assert state_lx_error.named_functions == {}
        assert state_lx_error.on_enters == []
        assert state_lx_error.on_durings == []
        assert state_lx_error.on_exits == []
        assert state_lx_error.on_during_aspects == []
        assert state_lx_error.parent_ref().name == "LX"
        assert state_lx_error.parent_ref().path == ("LX",)
        assert state_lx_error.substate_name_to_id == {}
        assert state_lx_error.extra_name is None
        assert not state_lx_error.is_pseudo
        assert state_lx_error.abstract_on_during_aspects == []
        assert state_lx_error.abstract_on_durings == []
        assert state_lx_error.abstract_on_enters == []
        assert state_lx_error.abstract_on_exits == []
        assert state_lx_error.is_leaf_state
        assert not state_lx_error.is_root_state
        assert state_lx_error.non_abstract_on_during_aspects == []
        assert state_lx_error.non_abstract_on_durings == []
        assert state_lx_error.non_abstract_on_enters == []
        assert state_lx_error.non_abstract_on_exits == []
        assert state_lx_error.parent.name == "LX"
        assert state_lx_error.parent.path == ("LX",)
        assert state_lx_error.transitions_entering_children == []
        assert len(state_lx_error.transitions_entering_children_simplified) == 1
        assert state_lx_error.transitions_entering_children_simplified[0] is None
        assert len(state_lx_error.transitions_from) == 2
        assert state_lx_error.transitions_from[0].from_state == "ERROR"
        assert state_lx_error.transitions_from[0].to_state == "ERROR"
        assert state_lx_error.transitions_from[0].event == Event(
            name="E1", state_path=("LX",)
        )
        assert state_lx_error.transitions_from[0].guard is None
        assert state_lx_error.transitions_from[0].effects == []
        assert state_lx_error.transitions_from[0].parent_ref().name == "LX"
        assert state_lx_error.transitions_from[0].parent_ref().path == ("LX",)
        assert state_lx_error.transitions_from[1].from_state == "ERROR"
        assert state_lx_error.transitions_from[1].to_state == EXIT_STATE
        assert state_lx_error.transitions_from[1].event is None
        assert state_lx_error.transitions_from[1].guard is None
        assert state_lx_error.transitions_from[1].effects == []
        assert state_lx_error.transitions_from[1].parent_ref().name == "LX"
        assert state_lx_error.transitions_from[1].parent_ref().path == ("LX",)
        assert len(state_lx_error.transitions_to) == 2
        assert state_lx_error.transitions_to[0].from_state == "LX2"
        assert state_lx_error.transitions_to[0].to_state == "ERROR"
        assert state_lx_error.transitions_to[0].event == Event(
            name="E1", state_path=("LX",)
        )
        assert state_lx_error.transitions_to[0].guard is None
        assert state_lx_error.transitions_to[0].effects == []
        assert state_lx_error.transitions_to[0].parent_ref().name == "LX"
        assert state_lx_error.transitions_to[0].parent_ref().path == ("LX",)
        assert state_lx_error.transitions_to[1].from_state == "ERROR"
        assert state_lx_error.transitions_to[1].to_state == "ERROR"
        assert state_lx_error.transitions_to[1].event == Event(
            name="E1", state_path=("LX",)
        )
        assert state_lx_error.transitions_to[1].guard is None
        assert state_lx_error.transitions_to[1].effects == []
        assert state_lx_error.transitions_to[1].parent_ref().name == "LX"
        assert state_lx_error.transitions_to[1].parent_ref().path == ("LX",)

    def test_state_lx_error_to_ast_node(self, state_lx_error):
        ast_node = state_lx_error.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="ERROR",
            extra_name=None,
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_lx_error_list_on_enters(self, state_lx_error):
        lst = state_lx_error.list_on_enters()
        assert lst == []

        lst = state_lx_error.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_lx_error.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_lx_error.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_lx_error.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_lx_error.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_lx_error.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_lx_error.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_lx_error.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_lx_error_during_aspects(self, state_lx_error):
        lst = state_lx_error.list_on_during_aspects()
        assert lst == []

        lst = state_lx_error.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lx_error.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lx_error.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lx_error.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_lx_error.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_lx_error.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lx_error.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_lx_error.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_lx_error_during_aspect_recursively(self, state_lx_error):
        lst = state_lx_error.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_lx_error.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int Event = 0;
state LX {
    enter {
    }
    enter abstract act1;
    state LX2 {
        state start {
            state LX4 {
                state LX5;
                LX5 -> [*] : /E1;
                [*] -> LX5;
            }
            LX4 -> [*] : /E1;
            [*] -> LX4;
        }
        start -> [*] : /E1;
        [*] -> start;
    }
    state ERROR;
    LX2 -> ERROR : E1;
    ERROR -> ERROR : E1;
    [*] -> LX2;
    ERROR -> [*];
}
            """).strip(),
            actual=str(model.to_ast_node()),
        )

    def test_to_plantuml(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
@startuml
hide empty description
note as DefinitionNote
defines {
    def int Event = 0;
}
end note

state "LX" as lx {
    state "LX2" as lx__lx2 {
        state "start" as lx__lx2__start {
            state "LX4" as lx__lx2__start__lx4 {
                state "LX5" as lx__lx2__start__lx4__lx5
                lx__lx2__start__lx4__lx5 --> [*] : /E1
                [*] --> lx__lx2__start__lx4__lx5
            }
            lx__lx2__start__lx4 --> [*] : /E1
            [*] --> lx__lx2__start__lx4
        }
        lx__lx2__start --> [*] : /E1
        [*] --> lx__lx2__start
    }
    state "ERROR" as lx__error
    lx__lx2 --> lx__error : E1
    lx__error --> lx__error : E1
    [*] --> lx__lx2
    lx__error --> [*]
}
lx : enter {\\n}\\nenter abstract act1;
[*] --> lx
lx --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml()),
        )
