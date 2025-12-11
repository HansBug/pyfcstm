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
state Root{
    event E1 named '事件1';
    state state1 {
        event E1 named 'S1 -> 事件1';
    };
    state state2;
    pseudo state state3 {
        event E2 named 'S3 -> 事件2';
    };
    state state4;

    [*] -> state1 : E1;
    state1 -> state2 :: E1;
    state2 -> state3 : E1;
    state3 -> state4 :: E2;
}
    """,
        entry_name="state_machine_dsl",
    )
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.fixture()
def state_root(model):
    return model.root_state


@pytest.fixture()
def state_root_state1(state_root):
    return state_root.substates["state1"]


@pytest.fixture()
def state_root_state2(state_root):
    return state_root.substates["state2"]


@pytest.fixture()
def state_root_state3(state_root):
    return state_root.substates["state3"]


@pytest.fixture()
def state_root_state4(state_root):
    return state_root.substates["state4"]


@pytest.mark.unittest
class TestModelStateRoot:
    def test_model(self, model):
        assert model.defines == {}
        assert model.root_state.name == "Root"
        assert model.root_state.path == ("Root",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == []
        assert ast_node.root_state.name == "Root"

    def test_state_root(self, state_root):
        assert state_root.name == "Root"
        assert state_root.path == ("Root",)
        assert sorted(state_root.substates.keys()) == [
            "state1",
            "state2",
            "state3",
            "state4",
        ]
        assert state_root.events == {
            "E1": Event(name="E1", state_path=("Root",), extra_name="事件1")
        }
        assert len(state_root.transitions) == 4
        assert state_root.transitions[0].from_state == INIT_STATE
        assert state_root.transitions[0].to_state == "state1"
        assert state_root.transitions[0].event == Event(
            name="E1", state_path=("Root",), extra_name="事件1"
        )
        assert state_root.transitions[0].guard is None
        assert state_root.transitions[0].effects == []
        assert state_root.transitions[0].parent_ref().name == "Root"
        assert state_root.transitions[0].parent_ref().path == ("Root",)
        assert state_root.transitions[1].from_state == "state1"
        assert state_root.transitions[1].to_state == "state2"
        assert state_root.transitions[1].event == Event(
            name="E1", state_path=("Root", "state1"), extra_name="S1 -> 事件1"
        )
        assert state_root.transitions[1].guard is None
        assert state_root.transitions[1].effects == []
        assert state_root.transitions[1].parent_ref().name == "Root"
        assert state_root.transitions[1].parent_ref().path == ("Root",)
        assert state_root.transitions[2].from_state == "state2"
        assert state_root.transitions[2].to_state == "state3"
        assert state_root.transitions[2].event == Event(
            name="E1", state_path=("Root",), extra_name="事件1"
        )
        assert state_root.transitions[2].guard is None
        assert state_root.transitions[2].effects == []
        assert state_root.transitions[2].parent_ref().name == "Root"
        assert state_root.transitions[2].parent_ref().path == ("Root",)
        assert state_root.transitions[3].from_state == "state3"
        assert state_root.transitions[3].to_state == "state4"
        assert state_root.transitions[3].event == Event(
            name="E2", state_path=("Root", "state3"), extra_name="S3 -> 事件2"
        )
        assert state_root.transitions[3].guard is None
        assert state_root.transitions[3].effects == []
        assert state_root.transitions[3].parent_ref().name == "Root"
        assert state_root.transitions[3].parent_ref().path == ("Root",)
        assert state_root.named_functions == {}
        assert state_root.on_enters == []
        assert state_root.on_durings == []
        assert state_root.on_exits == []
        assert state_root.on_during_aspects == []
        assert state_root.parent_ref is None
        assert state_root.substate_name_to_id == {
            "state1": 0,
            "state2": 1,
            "state3": 2,
            "state4": 3,
        }
        assert state_root.extra_name is None
        assert not state_root.is_pseudo
        assert state_root.abstract_on_during_aspects == []
        assert state_root.abstract_on_durings == []
        assert state_root.abstract_on_enters == []
        assert state_root.abstract_on_exits == []
        assert len(state_root.init_transitions) == 1
        assert state_root.init_transitions[0].from_state == INIT_STATE
        assert state_root.init_transitions[0].to_state == "state1"
        assert state_root.init_transitions[0].event == Event(
            name="E1", state_path=("Root",), extra_name="事件1"
        )
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
        assert state_root.transitions_entering_children[0].to_state == "state1"
        assert state_root.transitions_entering_children[0].event == Event(
            name="E1", state_path=("Root",), extra_name="事件1"
        )
        assert state_root.transitions_entering_children[0].guard is None
        assert state_root.transitions_entering_children[0].effects == []
        assert state_root.transitions_entering_children[0].parent_ref().name == "Root"
        assert state_root.transitions_entering_children[0].parent_ref().path == (
            "Root",
        )
        assert len(state_root.transitions_entering_children_simplified) == 2
        assert (
            state_root.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_root.transitions_entering_children_simplified[0].to_state == "state1"
        )
        assert state_root.transitions_entering_children_simplified[0].event == Event(
            name="E1", state_path=("Root",), extra_name="事件1"
        )
        assert state_root.transitions_entering_children_simplified[0].guard is None
        assert state_root.transitions_entering_children_simplified[0].effects == []
        assert (
            state_root.transitions_entering_children_simplified[0].parent_ref().name
            == "Root"
        )
        assert state_root.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Root",)
        assert state_root.transitions_entering_children_simplified[1] is None
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
            events=[dsl_nodes.EventDefinition(name="E1", extra_name="事件1")],
            substates=[
                dsl_nodes.StateDefinition(
                    name="state1",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name="S1 -> 事件1")
                    ],
                    substates=[],
                    transitions=[],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                ),
                dsl_nodes.StateDefinition(
                    name="state2",
                    extra_name=None,
                    events=[],
                    substates=[],
                    transitions=[],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                ),
                dsl_nodes.StateDefinition(
                    name="state3",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E2", extra_name="S3 -> 事件2")
                    ],
                    substates=[],
                    transitions=[],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=True,
                ),
                dsl_nodes.StateDefinition(
                    name="state4",
                    extra_name=None,
                    events=[],
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
                    from_state=INIT_STATE,
                    to_state="state1",
                    event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="state1",
                    to_state="state2",
                    event_id=dsl_nodes.ChainID(
                        path=["state1", "E1"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="state2",
                    to_state="state3",
                    event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="state3",
                    to_state="state4",
                    event_id=dsl_nodes.ChainID(
                        path=["state3", "E2"], is_absolute=False
                    ),
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

    def test_state_root_state1(self, state_root_state1):
        assert state_root_state1.name == "state1"
        assert state_root_state1.path == ("Root", "state1")
        assert sorted(state_root_state1.substates.keys()) == []
        assert state_root_state1.events == {
            "E1": Event(
                name="E1", state_path=("Root", "state1"), extra_name="S1 -> 事件1"
            )
        }
        assert state_root_state1.transitions == []
        assert state_root_state1.named_functions == {}
        assert state_root_state1.on_enters == []
        assert state_root_state1.on_durings == []
        assert state_root_state1.on_exits == []
        assert state_root_state1.on_during_aspects == []
        assert state_root_state1.parent_ref().name == "Root"
        assert state_root_state1.parent_ref().path == ("Root",)
        assert state_root_state1.substate_name_to_id == {}
        assert state_root_state1.extra_name is None
        assert not state_root_state1.is_pseudo
        assert state_root_state1.abstract_on_during_aspects == []
        assert state_root_state1.abstract_on_durings == []
        assert state_root_state1.abstract_on_enters == []
        assert state_root_state1.abstract_on_exits == []
        assert state_root_state1.init_transitions == []
        assert state_root_state1.is_leaf_state
        assert not state_root_state1.is_root_state
        assert state_root_state1.is_stoppable
        assert state_root_state1.non_abstract_on_during_aspects == []
        assert state_root_state1.non_abstract_on_durings == []
        assert state_root_state1.non_abstract_on_enters == []
        assert state_root_state1.non_abstract_on_exits == []
        assert state_root_state1.parent.name == "Root"
        assert state_root_state1.parent.path == ("Root",)
        assert state_root_state1.transitions_entering_children == []
        assert len(state_root_state1.transitions_entering_children_simplified) == 1
        assert state_root_state1.transitions_entering_children_simplified[0] is None
        assert len(state_root_state1.transitions_from) == 1
        assert state_root_state1.transitions_from[0].from_state == "state1"
        assert state_root_state1.transitions_from[0].to_state == "state2"
        assert state_root_state1.transitions_from[0].event == Event(
            name="E1", state_path=("Root", "state1"), extra_name="S1 -> 事件1"
        )
        assert state_root_state1.transitions_from[0].guard is None
        assert state_root_state1.transitions_from[0].effects == []
        assert state_root_state1.transitions_from[0].parent_ref().name == "Root"
        assert state_root_state1.transitions_from[0].parent_ref().path == ("Root",)
        assert len(state_root_state1.transitions_to) == 1
        assert state_root_state1.transitions_to[0].from_state == INIT_STATE
        assert state_root_state1.transitions_to[0].to_state == "state1"
        assert state_root_state1.transitions_to[0].event == Event(
            name="E1", state_path=("Root",), extra_name="事件1"
        )
        assert state_root_state1.transitions_to[0].guard is None
        assert state_root_state1.transitions_to[0].effects == []
        assert state_root_state1.transitions_to[0].parent_ref().name == "Root"
        assert state_root_state1.transitions_to[0].parent_ref().path == ("Root",)

    def test_state_root_state1_to_ast_node(self, state_root_state1):
        ast_node = state_root_state1.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="state1",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E1", extra_name="S1 -> 事件1")],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_root_state1_list_on_enters(self, state_root_state1):
        lst = state_root_state1.list_on_enters()
        assert lst == []

        lst = state_root_state1.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_state1.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_state1.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_state1.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_root_state1.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root_state1.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_state1.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root_state1.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_state1_during_aspects(self, state_root_state1):
        lst = state_root_state1.list_on_during_aspects()
        assert lst == []

        lst = state_root_state1.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_state1.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_state1.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_state1.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_state1.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_state1.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_state1.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_state1.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_root_state1_during_aspect_recursively(self, state_root_state1):
        lst = state_root_state1.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_root_state1.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_root_state2(self, state_root_state2):
        assert state_root_state2.name == "state2"
        assert state_root_state2.path == ("Root", "state2")
        assert sorted(state_root_state2.substates.keys()) == []
        assert state_root_state2.events == {}
        assert state_root_state2.transitions == []
        assert state_root_state2.named_functions == {}
        assert state_root_state2.on_enters == []
        assert state_root_state2.on_durings == []
        assert state_root_state2.on_exits == []
        assert state_root_state2.on_during_aspects == []
        assert state_root_state2.parent_ref().name == "Root"
        assert state_root_state2.parent_ref().path == ("Root",)
        assert state_root_state2.substate_name_to_id == {}
        assert state_root_state2.extra_name is None
        assert not state_root_state2.is_pseudo
        assert state_root_state2.abstract_on_during_aspects == []
        assert state_root_state2.abstract_on_durings == []
        assert state_root_state2.abstract_on_enters == []
        assert state_root_state2.abstract_on_exits == []
        assert state_root_state2.init_transitions == []
        assert state_root_state2.is_leaf_state
        assert not state_root_state2.is_root_state
        assert state_root_state2.is_stoppable
        assert state_root_state2.non_abstract_on_during_aspects == []
        assert state_root_state2.non_abstract_on_durings == []
        assert state_root_state2.non_abstract_on_enters == []
        assert state_root_state2.non_abstract_on_exits == []
        assert state_root_state2.parent.name == "Root"
        assert state_root_state2.parent.path == ("Root",)
        assert state_root_state2.transitions_entering_children == []
        assert len(state_root_state2.transitions_entering_children_simplified) == 1
        assert state_root_state2.transitions_entering_children_simplified[0] is None
        assert len(state_root_state2.transitions_from) == 1
        assert state_root_state2.transitions_from[0].from_state == "state2"
        assert state_root_state2.transitions_from[0].to_state == "state3"
        assert state_root_state2.transitions_from[0].event == Event(
            name="E1", state_path=("Root",), extra_name="事件1"
        )
        assert state_root_state2.transitions_from[0].guard is None
        assert state_root_state2.transitions_from[0].effects == []
        assert state_root_state2.transitions_from[0].parent_ref().name == "Root"
        assert state_root_state2.transitions_from[0].parent_ref().path == ("Root",)
        assert len(state_root_state2.transitions_to) == 1
        assert state_root_state2.transitions_to[0].from_state == "state1"
        assert state_root_state2.transitions_to[0].to_state == "state2"
        assert state_root_state2.transitions_to[0].event == Event(
            name="E1", state_path=("Root", "state1"), extra_name="S1 -> 事件1"
        )
        assert state_root_state2.transitions_to[0].guard is None
        assert state_root_state2.transitions_to[0].effects == []
        assert state_root_state2.transitions_to[0].parent_ref().name == "Root"
        assert state_root_state2.transitions_to[0].parent_ref().path == ("Root",)

    def test_state_root_state2_to_ast_node(self, state_root_state2):
        ast_node = state_root_state2.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="state2",
            extra_name=None,
            events=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_root_state2_list_on_enters(self, state_root_state2):
        lst = state_root_state2.list_on_enters()
        assert lst == []

        lst = state_root_state2.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_state2.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_state2.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_state2.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_root_state2.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root_state2.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_state2.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root_state2.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_state2_during_aspects(self, state_root_state2):
        lst = state_root_state2.list_on_during_aspects()
        assert lst == []

        lst = state_root_state2.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_state2.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_state2.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_state2.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_state2.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_state2.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_state2.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_state2.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_root_state2_during_aspect_recursively(self, state_root_state2):
        lst = state_root_state2.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_root_state2.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_root_state3(self, state_root_state3):
        assert state_root_state3.name == "state3"
        assert state_root_state3.path == ("Root", "state3")
        assert sorted(state_root_state3.substates.keys()) == []
        assert state_root_state3.events == {
            "E2": Event(
                name="E2", state_path=("Root", "state3"), extra_name="S3 -> 事件2"
            )
        }
        assert state_root_state3.transitions == []
        assert state_root_state3.named_functions == {}
        assert state_root_state3.on_enters == []
        assert state_root_state3.on_durings == []
        assert state_root_state3.on_exits == []
        assert state_root_state3.on_during_aspects == []
        assert state_root_state3.parent_ref().name == "Root"
        assert state_root_state3.parent_ref().path == ("Root",)
        assert state_root_state3.substate_name_to_id == {}
        assert state_root_state3.extra_name is None
        assert state_root_state3.is_pseudo
        assert state_root_state3.abstract_on_during_aspects == []
        assert state_root_state3.abstract_on_durings == []
        assert state_root_state3.abstract_on_enters == []
        assert state_root_state3.abstract_on_exits == []
        assert state_root_state3.init_transitions == []
        assert state_root_state3.is_leaf_state
        assert not state_root_state3.is_root_state
        assert not state_root_state3.is_stoppable
        assert state_root_state3.non_abstract_on_during_aspects == []
        assert state_root_state3.non_abstract_on_durings == []
        assert state_root_state3.non_abstract_on_enters == []
        assert state_root_state3.non_abstract_on_exits == []
        assert state_root_state3.parent.name == "Root"
        assert state_root_state3.parent.path == ("Root",)
        assert state_root_state3.transitions_entering_children == []
        assert len(state_root_state3.transitions_entering_children_simplified) == 1
        assert state_root_state3.transitions_entering_children_simplified[0] is None
        assert len(state_root_state3.transitions_from) == 1
        assert state_root_state3.transitions_from[0].from_state == "state3"
        assert state_root_state3.transitions_from[0].to_state == "state4"
        assert state_root_state3.transitions_from[0].event == Event(
            name="E2", state_path=("Root", "state3"), extra_name="S3 -> 事件2"
        )
        assert state_root_state3.transitions_from[0].guard is None
        assert state_root_state3.transitions_from[0].effects == []
        assert state_root_state3.transitions_from[0].parent_ref().name == "Root"
        assert state_root_state3.transitions_from[0].parent_ref().path == ("Root",)
        assert len(state_root_state3.transitions_to) == 1
        assert state_root_state3.transitions_to[0].from_state == "state2"
        assert state_root_state3.transitions_to[0].to_state == "state3"
        assert state_root_state3.transitions_to[0].event == Event(
            name="E1", state_path=("Root",), extra_name="事件1"
        )
        assert state_root_state3.transitions_to[0].guard is None
        assert state_root_state3.transitions_to[0].effects == []
        assert state_root_state3.transitions_to[0].parent_ref().name == "Root"
        assert state_root_state3.transitions_to[0].parent_ref().path == ("Root",)

    def test_state_root_state3_to_ast_node(self, state_root_state3):
        ast_node = state_root_state3.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="state3",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E2", extra_name="S3 -> 事件2")],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=True,
        )

    def test_state_root_state3_list_on_enters(self, state_root_state3):
        lst = state_root_state3.list_on_enters()
        assert lst == []

        lst = state_root_state3.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_state3.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_state3.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_state3.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_root_state3.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root_state3.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_state3.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root_state3.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_state3_during_aspects(self, state_root_state3):
        lst = state_root_state3.list_on_during_aspects()
        assert lst == []

        lst = state_root_state3.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_state3.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_state3.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_state3.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_state3.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_state3.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_state3.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_state3.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_root_state3_during_aspect_recursively(self, state_root_state3):
        lst = state_root_state3.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_root_state3.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_root_state4(self, state_root_state4):
        assert state_root_state4.name == "state4"
        assert state_root_state4.path == ("Root", "state4")
        assert sorted(state_root_state4.substates.keys()) == []
        assert state_root_state4.events == {}
        assert state_root_state4.transitions == []
        assert state_root_state4.named_functions == {}
        assert state_root_state4.on_enters == []
        assert state_root_state4.on_durings == []
        assert state_root_state4.on_exits == []
        assert state_root_state4.on_during_aspects == []
        assert state_root_state4.parent_ref().name == "Root"
        assert state_root_state4.parent_ref().path == ("Root",)
        assert state_root_state4.substate_name_to_id == {}
        assert state_root_state4.extra_name is None
        assert not state_root_state4.is_pseudo
        assert state_root_state4.abstract_on_during_aspects == []
        assert state_root_state4.abstract_on_durings == []
        assert state_root_state4.abstract_on_enters == []
        assert state_root_state4.abstract_on_exits == []
        assert state_root_state4.init_transitions == []
        assert state_root_state4.is_leaf_state
        assert not state_root_state4.is_root_state
        assert state_root_state4.is_stoppable
        assert state_root_state4.non_abstract_on_during_aspects == []
        assert state_root_state4.non_abstract_on_durings == []
        assert state_root_state4.non_abstract_on_enters == []
        assert state_root_state4.non_abstract_on_exits == []
        assert state_root_state4.parent.name == "Root"
        assert state_root_state4.parent.path == ("Root",)
        assert state_root_state4.transitions_entering_children == []
        assert len(state_root_state4.transitions_entering_children_simplified) == 1
        assert state_root_state4.transitions_entering_children_simplified[0] is None
        assert state_root_state4.transitions_from == []
        assert len(state_root_state4.transitions_to) == 1
        assert state_root_state4.transitions_to[0].from_state == "state3"
        assert state_root_state4.transitions_to[0].to_state == "state4"
        assert state_root_state4.transitions_to[0].event == Event(
            name="E2", state_path=("Root", "state3"), extra_name="S3 -> 事件2"
        )
        assert state_root_state4.transitions_to[0].guard is None
        assert state_root_state4.transitions_to[0].effects == []
        assert state_root_state4.transitions_to[0].parent_ref().name == "Root"
        assert state_root_state4.transitions_to[0].parent_ref().path == ("Root",)

    def test_state_root_state4_to_ast_node(self, state_root_state4):
        ast_node = state_root_state4.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="state4",
            extra_name=None,
            events=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_root_state4_list_on_enters(self, state_root_state4):
        lst = state_root_state4.list_on_enters()
        assert lst == []

        lst = state_root_state4.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_state4.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_state4.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_state4.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_root_state4.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root_state4.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_state4.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root_state4.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_state4_during_aspects(self, state_root_state4):
        lst = state_root_state4.list_on_during_aspects()
        assert lst == []

        lst = state_root_state4.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_state4.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_state4.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_state4.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_state4.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_state4.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_state4.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_state4.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_root_state4_during_aspect_recursively(self, state_root_state4):
        lst = state_root_state4.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_root_state4.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
state Root {
    state state1 {
        event E1 named 'S1 -> 事件1';
    }
    state state2;
    pseudo state state3 {
        event E2 named 'S3 -> 事件2';
    }
    state state4;
    event E1 named '事件1';
    [*] -> state1 :: E1;
    state1 -> state2 :: E1;
    state2 -> state3 : E1;
    state3 -> state4 :: E2;
}
            """).strip(),
            actual=str(model.to_ast_node()),
        )

    def test_to_plantuml(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
@startuml
hide empty description
state "Root" as root {
    state "state1" as root__state1
    state "state2" as root__state2
    state "state3" as root__state3 #line.dotted
    state "state4" as root__state4
    [*] --> root__state1 : 事件1(E1)
    root__state1 --> root__state2 : S1 -> 事件1(state1.E1)
    root__state2 --> root__state3 : 事件1(E1)
    root__state3 --> root__state4 : S3 -> 事件2(state3.E2)
}
[*] --> root
root --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml()),
        )
