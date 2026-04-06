import textwrap
import pytest
import os
import pathlib
from hbutils.testing import isolated_directory

from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl.node import INIT_STATE, EXIT_STATE
from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.model.expr import *
from pyfcstm.model.model import *


def _write_text_file(path: str, content: str):
    file_path = pathlib.Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        textwrap.dedent(content).strip() + os.linesep, encoding="utf-8"
    )
    return file_path


@pytest.fixture()
def model():
    with isolated_directory():
        _write_text_file(
            "main.fcstm",
            """
state Root {
    state Bus;
    import "./modules/child.fcstm" as Child named "Child Layer" {
        event /Start -> /Bus.Start named "Top Start";
        event /InnerBus.Stop -> /Bus.Stop named "Top Stop";
        event /Trip -> /Bus.Trip named "Top Trip";
    }
    [*] -> Child;
}
        """,
        )
        _write_text_file(
            "modules/child.fcstm",
            """
state ChildRoot {
    state InnerBus;
    import "./grand/grand.fcstm" as Grand named "Grand Layer" {
        event /Pulse -> Start named "Child Start";
        event /Halt -> /InnerBus.Stop named "Child Stop";
        event /Trip -> Trip named "Child Trip";
    }
    [*] -> Grand;
}
        """,
        )
        _write_text_file(
            "modules/grand/grand.fcstm",
            """
state GrandRoot {
    event Pulse named "Pulse Source";
    event Trip named "Trip Source";
    state Idle;
    state Running;
    state Tripped;
    [*] -> Idle;
    Idle -> Running : Pulse;
    Running -> Idle : /Halt;
    ! * -> Tripped : Trip;
}
        """,
        )
        entry_file = pathlib.Path("main.fcstm")
        ast_node = parse_state_machine_dsl(entry_file.read_text(encoding="utf-8"))
        model = parse_dsl_node_to_state_machine(ast_node, path=entry_file)
        return model


@pytest.fixture()
def state_root(model):
    return model.root_state


@pytest.fixture()
def state_root_child(state_root):
    return state_root.substates["Child"]


@pytest.fixture()
def state_root_child_grand(state_root_child):
    return state_root_child.substates["Grand"]


@pytest.fixture()
def state_root_child_grand_idle(state_root_child_grand):
    return state_root_child_grand.substates["Idle"]


@pytest.fixture()
def state_root_child_grand_running(state_root_child_grand):
    return state_root_child_grand.substates["Running"]


@pytest.fixture()
def state_root_child_grand_tripped(state_root_child_grand):
    return state_root_child_grand.substates["Tripped"]


@pytest.fixture()
def state_root_child_innerbus(state_root_child):
    return state_root_child.substates["InnerBus"]


@pytest.fixture()
def state_root_bus(state_root):
    return state_root.substates["Bus"]


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
        assert sorted(state_root.substates.keys()) == ["Bus", "Child"]
        assert state_root.events == {}
        assert len(state_root.transitions) == 1
        assert state_root.transitions[0].from_state == INIT_STATE
        assert state_root.transitions[0].to_state == "Child"
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
        assert state_root.substate_name_to_id == {"Child": 0, "Bus": 1}
        assert state_root.extra_name is None
        assert not state_root.is_pseudo
        assert state_root.abstract_on_during_aspects == []
        assert state_root.abstract_on_durings == []
        assert state_root.abstract_on_enters == []
        assert state_root.abstract_on_exits == []
        assert len(state_root.init_transitions) == 1
        assert state_root.init_transitions[0].from_state == INIT_STATE
        assert state_root.init_transitions[0].to_state == "Child"
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
        assert state_root.transitions_entering_children[0].to_state == "Child"
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
            state_root.transitions_entering_children_simplified[0].to_state == "Child"
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
                    name="Child",
                    extra_name="Child Layer",
                    events=[],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Grand",
                            extra_name="Grand Layer",
                            events=[],
                            imports=[],
                            substates=[
                                dsl_nodes.StateDefinition(
                                    name="Idle",
                                    extra_name=None,
                                    events=[],
                                    imports=[],
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
                                    name="Running",
                                    extra_name=None,
                                    events=[],
                                    imports=[],
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
                                    name="Tripped",
                                    extra_name=None,
                                    events=[],
                                    imports=[],
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
                                    from_state="Idle",
                                    to_state="Tripped",
                                    event_id=dsl_nodes.ChainID(
                                        path=["Bus", "Trip"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="Running",
                                    to_state="Tripped",
                                    event_id=dsl_nodes.ChainID(
                                        path=["Bus", "Trip"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="Tripped",
                                    to_state="Tripped",
                                    event_id=dsl_nodes.ChainID(
                                        path=["Bus", "Trip"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state=INIT_STATE,
                                    to_state="Idle",
                                    event_id=None,
                                    condition_expr=None,
                                    post_operations=[],
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="Idle",
                                    to_state="Running",
                                    event_id=dsl_nodes.ChainID(
                                        path=["Bus", "Start"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="Running",
                                    to_state="Idle",
                                    event_id=dsl_nodes.ChainID(
                                        path=["Bus", "Stop"], is_absolute=True
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
                        ),
                        dsl_nodes.StateDefinition(
                            name="InnerBus",
                            extra_name=None,
                            events=[],
                            imports=[],
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
                            to_state="Grand",
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
                ),
                dsl_nodes.StateDefinition(
                    name="Bus",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="Start", extra_name="Top Start"),
                        dsl_nodes.EventDefinition(name="Stop", extra_name="Top Stop"),
                        dsl_nodes.EventDefinition(name="Trip", extra_name="Top Trip"),
                    ],
                    imports=[],
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
                    to_state="Child",
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

    def test_state_root_child(self, state_root_child):
        assert state_root_child.name == "Child"
        assert state_root_child.path == ("Root", "Child")
        assert sorted(state_root_child.substates.keys()) == ["Grand", "InnerBus"]
        assert state_root_child.events == {}
        assert len(state_root_child.transitions) == 1
        assert state_root_child.transitions[0].from_state == INIT_STATE
        assert state_root_child.transitions[0].to_state == "Grand"
        assert state_root_child.transitions[0].event is None
        assert state_root_child.transitions[0].guard is None
        assert state_root_child.transitions[0].effects == []
        assert state_root_child.transitions[0].parent_ref().name == "Child"
        assert state_root_child.transitions[0].parent_ref().path == ("Root", "Child")
        assert state_root_child.named_functions == {}
        assert state_root_child.on_enters == []
        assert state_root_child.on_durings == []
        assert state_root_child.on_exits == []
        assert state_root_child.on_during_aspects == []
        assert state_root_child.parent_ref().name == "Root"
        assert state_root_child.parent_ref().path == ("Root",)
        assert state_root_child.substate_name_to_id == {"Grand": 0, "InnerBus": 1}
        assert state_root_child.extra_name == "Child Layer"
        assert not state_root_child.is_pseudo
        assert state_root_child.abstract_on_during_aspects == []
        assert state_root_child.abstract_on_durings == []
        assert state_root_child.abstract_on_enters == []
        assert state_root_child.abstract_on_exits == []
        assert len(state_root_child.init_transitions) == 1
        assert state_root_child.init_transitions[0].from_state == INIT_STATE
        assert state_root_child.init_transitions[0].to_state == "Grand"
        assert state_root_child.init_transitions[0].event is None
        assert state_root_child.init_transitions[0].guard is None
        assert state_root_child.init_transitions[0].effects == []
        assert state_root_child.init_transitions[0].parent_ref().name == "Child"
        assert state_root_child.init_transitions[0].parent_ref().path == (
            "Root",
            "Child",
        )
        assert not state_root_child.is_leaf_state
        assert not state_root_child.is_root_state
        assert not state_root_child.is_stoppable
        assert state_root_child.non_abstract_on_during_aspects == []
        assert state_root_child.non_abstract_on_durings == []
        assert state_root_child.non_abstract_on_enters == []
        assert state_root_child.non_abstract_on_exits == []
        assert state_root_child.parent.name == "Root"
        assert state_root_child.parent.path == ("Root",)
        assert len(state_root_child.transitions_entering_children) == 1
        assert (
            state_root_child.transitions_entering_children[0].from_state == INIT_STATE
        )
        assert state_root_child.transitions_entering_children[0].to_state == "Grand"
        assert state_root_child.transitions_entering_children[0].event is None
        assert state_root_child.transitions_entering_children[0].guard is None
        assert state_root_child.transitions_entering_children[0].effects == []
        assert (
            state_root_child.transitions_entering_children[0].parent_ref().name
            == "Child"
        )
        assert state_root_child.transitions_entering_children[0].parent_ref().path == (
            "Root",
            "Child",
        )
        assert len(state_root_child.transitions_entering_children_simplified) == 1
        assert (
            state_root_child.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_root_child.transitions_entering_children_simplified[0].to_state
            == "Grand"
        )
        assert (
            state_root_child.transitions_entering_children_simplified[0].event is None
        )
        assert (
            state_root_child.transitions_entering_children_simplified[0].guard is None
        )
        assert (
            state_root_child.transitions_entering_children_simplified[0].effects == []
        )
        assert (
            state_root_child.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "Child"
        )
        assert state_root_child.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Root", "Child")
        assert state_root_child.transitions_from == []
        assert len(state_root_child.transitions_to) == 1
        assert state_root_child.transitions_to[0].from_state == INIT_STATE
        assert state_root_child.transitions_to[0].to_state == "Child"
        assert state_root_child.transitions_to[0].event is None
        assert state_root_child.transitions_to[0].guard is None
        assert state_root_child.transitions_to[0].effects == []
        assert state_root_child.transitions_to[0].parent_ref().name == "Root"
        assert state_root_child.transitions_to[0].parent_ref().path == ("Root",)

    def test_state_root_child_to_ast_node(self, state_root_child):
        ast_node = state_root_child.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Child",
            extra_name="Child Layer",
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Grand",
                    extra_name="Grand Layer",
                    events=[],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Idle",
                            extra_name=None,
                            events=[],
                            imports=[],
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
                            name="Running",
                            extra_name=None,
                            events=[],
                            imports=[],
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
                            name="Tripped",
                            extra_name=None,
                            events=[],
                            imports=[],
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
                            from_state="Idle",
                            to_state="Tripped",
                            event_id=dsl_nodes.ChainID(
                                path=["Bus", "Trip"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Running",
                            to_state="Tripped",
                            event_id=dsl_nodes.ChainID(
                                path=["Bus", "Trip"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Tripped",
                            to_state="Tripped",
                            event_id=dsl_nodes.ChainID(
                                path=["Bus", "Trip"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="Idle",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Idle",
                            to_state="Running",
                            event_id=dsl_nodes.ChainID(
                                path=["Bus", "Start"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Running",
                            to_state="Idle",
                            event_id=dsl_nodes.ChainID(
                                path=["Bus", "Stop"], is_absolute=True
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
                ),
                dsl_nodes.StateDefinition(
                    name="InnerBus",
                    extra_name=None,
                    events=[],
                    imports=[],
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
                    to_state="Grand",
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

    def test_state_root_child_list_on_enters(self, state_root_child):
        lst = state_root_child.list_on_enters()
        assert lst == []

        lst = state_root_child.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_child.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_child.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_child.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_root_child.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root_child.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_child.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root_child.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_child_during_aspects(self, state_root_child):
        lst = state_root_child.list_on_during_aspects()
        assert lst == []

        lst = state_root_child.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_child.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_child.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_child.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_child.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_root_child.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_child.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_root_child.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_root_child_grand(self, state_root_child_grand):
        assert state_root_child_grand.name == "Grand"
        assert state_root_child_grand.path == ("Root", "Child", "Grand")
        assert sorted(state_root_child_grand.substates.keys()) == [
            "Idle",
            "Running",
            "Tripped",
        ]
        assert state_root_child_grand.events == {}
        assert len(state_root_child_grand.transitions) == 6
        assert state_root_child_grand.transitions[0].from_state == "Idle"
        assert state_root_child_grand.transitions[0].to_state == "Tripped"
        assert state_root_child_grand.transitions[0].event == Event(
            name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
        )
        assert state_root_child_grand.transitions[0].guard is None
        assert state_root_child_grand.transitions[0].effects == []
        assert state_root_child_grand.transitions[0].parent_ref().name == "Grand"
        assert state_root_child_grand.transitions[0].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand.transitions[1].from_state == "Running"
        assert state_root_child_grand.transitions[1].to_state == "Tripped"
        assert state_root_child_grand.transitions[1].event == Event(
            name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
        )
        assert state_root_child_grand.transitions[1].guard is None
        assert state_root_child_grand.transitions[1].effects == []
        assert state_root_child_grand.transitions[1].parent_ref().name == "Grand"
        assert state_root_child_grand.transitions[1].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand.transitions[2].from_state == "Tripped"
        assert state_root_child_grand.transitions[2].to_state == "Tripped"
        assert state_root_child_grand.transitions[2].event == Event(
            name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
        )
        assert state_root_child_grand.transitions[2].guard is None
        assert state_root_child_grand.transitions[2].effects == []
        assert state_root_child_grand.transitions[2].parent_ref().name == "Grand"
        assert state_root_child_grand.transitions[2].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand.transitions[3].from_state == INIT_STATE
        assert state_root_child_grand.transitions[3].to_state == "Idle"
        assert state_root_child_grand.transitions[3].event is None
        assert state_root_child_grand.transitions[3].guard is None
        assert state_root_child_grand.transitions[3].effects == []
        assert state_root_child_grand.transitions[3].parent_ref().name == "Grand"
        assert state_root_child_grand.transitions[3].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand.transitions[4].from_state == "Idle"
        assert state_root_child_grand.transitions[4].to_state == "Running"
        assert state_root_child_grand.transitions[4].event == Event(
            name="Start", state_path=("Root", "Bus"), extra_name="Top Start"
        )
        assert state_root_child_grand.transitions[4].guard is None
        assert state_root_child_grand.transitions[4].effects == []
        assert state_root_child_grand.transitions[4].parent_ref().name == "Grand"
        assert state_root_child_grand.transitions[4].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand.transitions[5].from_state == "Running"
        assert state_root_child_grand.transitions[5].to_state == "Idle"
        assert state_root_child_grand.transitions[5].event == Event(
            name="Stop", state_path=("Root", "Bus"), extra_name="Top Stop"
        )
        assert state_root_child_grand.transitions[5].guard is None
        assert state_root_child_grand.transitions[5].effects == []
        assert state_root_child_grand.transitions[5].parent_ref().name == "Grand"
        assert state_root_child_grand.transitions[5].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand.named_functions == {}
        assert state_root_child_grand.on_enters == []
        assert state_root_child_grand.on_durings == []
        assert state_root_child_grand.on_exits == []
        assert state_root_child_grand.on_during_aspects == []
        assert state_root_child_grand.parent_ref().name == "Child"
        assert state_root_child_grand.parent_ref().path == ("Root", "Child")
        assert state_root_child_grand.substate_name_to_id == {
            "Idle": 0,
            "Running": 1,
            "Tripped": 2,
        }
        assert state_root_child_grand.extra_name == "Grand Layer"
        assert not state_root_child_grand.is_pseudo
        assert state_root_child_grand.abstract_on_during_aspects == []
        assert state_root_child_grand.abstract_on_durings == []
        assert state_root_child_grand.abstract_on_enters == []
        assert state_root_child_grand.abstract_on_exits == []
        assert len(state_root_child_grand.init_transitions) == 1
        assert state_root_child_grand.init_transitions[0].from_state == INIT_STATE
        assert state_root_child_grand.init_transitions[0].to_state == "Idle"
        assert state_root_child_grand.init_transitions[0].event is None
        assert state_root_child_grand.init_transitions[0].guard is None
        assert state_root_child_grand.init_transitions[0].effects == []
        assert state_root_child_grand.init_transitions[0].parent_ref().name == "Grand"
        assert state_root_child_grand.init_transitions[0].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert not state_root_child_grand.is_leaf_state
        assert not state_root_child_grand.is_root_state
        assert not state_root_child_grand.is_stoppable
        assert state_root_child_grand.non_abstract_on_during_aspects == []
        assert state_root_child_grand.non_abstract_on_durings == []
        assert state_root_child_grand.non_abstract_on_enters == []
        assert state_root_child_grand.non_abstract_on_exits == []
        assert state_root_child_grand.parent.name == "Child"
        assert state_root_child_grand.parent.path == ("Root", "Child")
        assert len(state_root_child_grand.transitions_entering_children) == 1
        assert (
            state_root_child_grand.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert (
            state_root_child_grand.transitions_entering_children[0].to_state == "Idle"
        )
        assert state_root_child_grand.transitions_entering_children[0].event is None
        assert state_root_child_grand.transitions_entering_children[0].guard is None
        assert state_root_child_grand.transitions_entering_children[0].effects == []
        assert (
            state_root_child_grand.transitions_entering_children[0].parent_ref().name
            == "Grand"
        )
        assert state_root_child_grand.transitions_entering_children[
            0
        ].parent_ref().path == ("Root", "Child", "Grand")
        assert len(state_root_child_grand.transitions_entering_children_simplified) == 1
        assert (
            state_root_child_grand.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_root_child_grand.transitions_entering_children_simplified[0].to_state
            == "Idle"
        )
        assert (
            state_root_child_grand.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_root_child_grand.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_root_child_grand.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_root_child_grand.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "Grand"
        )
        assert state_root_child_grand.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Root", "Child", "Grand")
        assert state_root_child_grand.transitions_from == []
        assert len(state_root_child_grand.transitions_to) == 1
        assert state_root_child_grand.transitions_to[0].from_state == INIT_STATE
        assert state_root_child_grand.transitions_to[0].to_state == "Grand"
        assert state_root_child_grand.transitions_to[0].event is None
        assert state_root_child_grand.transitions_to[0].guard is None
        assert state_root_child_grand.transitions_to[0].effects == []
        assert state_root_child_grand.transitions_to[0].parent_ref().name == "Child"
        assert state_root_child_grand.transitions_to[0].parent_ref().path == (
            "Root",
            "Child",
        )

    def test_state_root_child_grand_to_ast_node(self, state_root_child_grand):
        ast_node = state_root_child_grand.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Grand",
            extra_name="Grand Layer",
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Idle",
                    extra_name=None,
                    events=[],
                    imports=[],
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
                    name="Running",
                    extra_name=None,
                    events=[],
                    imports=[],
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
                    name="Tripped",
                    extra_name=None,
                    events=[],
                    imports=[],
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
                    from_state="Idle",
                    to_state="Tripped",
                    event_id=dsl_nodes.ChainID(path=["Bus", "Trip"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Running",
                    to_state="Tripped",
                    event_id=dsl_nodes.ChainID(path=["Bus", "Trip"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Tripped",
                    to_state="Tripped",
                    event_id=dsl_nodes.ChainID(path=["Bus", "Trip"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="Idle",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Idle",
                    to_state="Running",
                    event_id=dsl_nodes.ChainID(path=["Bus", "Start"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Running",
                    to_state="Idle",
                    event_id=dsl_nodes.ChainID(path=["Bus", "Stop"], is_absolute=True),
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

    def test_state_root_child_grand_list_on_enters(self, state_root_child_grand):
        lst = state_root_child_grand.list_on_enters()
        assert lst == []

        lst = state_root_child_grand.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_child_grand.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_child_grand.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_child_grand.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_root_child_grand.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root_child_grand.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_child_grand.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root_child_grand.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_child_grand_during_aspects(self, state_root_child_grand):
        lst = state_root_child_grand.list_on_during_aspects()
        assert lst == []

        lst = state_root_child_grand.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_child_grand.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_child_grand.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_child_grand.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_child_grand.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_child_grand.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_child_grand.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_child_grand.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_root_child_grand_idle(self, state_root_child_grand_idle):
        assert state_root_child_grand_idle.name == "Idle"
        assert state_root_child_grand_idle.path == ("Root", "Child", "Grand", "Idle")
        assert sorted(state_root_child_grand_idle.substates.keys()) == []
        assert state_root_child_grand_idle.events == {}
        assert state_root_child_grand_idle.transitions == []
        assert state_root_child_grand_idle.named_functions == {}
        assert state_root_child_grand_idle.on_enters == []
        assert state_root_child_grand_idle.on_durings == []
        assert state_root_child_grand_idle.on_exits == []
        assert state_root_child_grand_idle.on_during_aspects == []
        assert state_root_child_grand_idle.parent_ref().name == "Grand"
        assert state_root_child_grand_idle.parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand_idle.substate_name_to_id == {}
        assert state_root_child_grand_idle.extra_name is None
        assert not state_root_child_grand_idle.is_pseudo
        assert state_root_child_grand_idle.abstract_on_during_aspects == []
        assert state_root_child_grand_idle.abstract_on_durings == []
        assert state_root_child_grand_idle.abstract_on_enters == []
        assert state_root_child_grand_idle.abstract_on_exits == []
        assert state_root_child_grand_idle.init_transitions == []
        assert state_root_child_grand_idle.is_leaf_state
        assert not state_root_child_grand_idle.is_root_state
        assert state_root_child_grand_idle.is_stoppable
        assert state_root_child_grand_idle.non_abstract_on_during_aspects == []
        assert state_root_child_grand_idle.non_abstract_on_durings == []
        assert state_root_child_grand_idle.non_abstract_on_enters == []
        assert state_root_child_grand_idle.non_abstract_on_exits == []
        assert state_root_child_grand_idle.parent.name == "Grand"
        assert state_root_child_grand_idle.parent.path == ("Root", "Child", "Grand")
        assert state_root_child_grand_idle.transitions_entering_children == []
        assert (
            len(state_root_child_grand_idle.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_root_child_grand_idle.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_root_child_grand_idle.transitions_from) == 2
        assert state_root_child_grand_idle.transitions_from[0].from_state == "Idle"
        assert state_root_child_grand_idle.transitions_from[0].to_state == "Tripped"
        assert state_root_child_grand_idle.transitions_from[0].event == Event(
            name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
        )
        assert state_root_child_grand_idle.transitions_from[0].guard is None
        assert state_root_child_grand_idle.transitions_from[0].effects == []
        assert (
            state_root_child_grand_idle.transitions_from[0].parent_ref().name == "Grand"
        )
        assert state_root_child_grand_idle.transitions_from[0].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand_idle.transitions_from[1].from_state == "Idle"
        assert state_root_child_grand_idle.transitions_from[1].to_state == "Running"
        assert state_root_child_grand_idle.transitions_from[1].event == Event(
            name="Start", state_path=("Root", "Bus"), extra_name="Top Start"
        )
        assert state_root_child_grand_idle.transitions_from[1].guard is None
        assert state_root_child_grand_idle.transitions_from[1].effects == []
        assert (
            state_root_child_grand_idle.transitions_from[1].parent_ref().name == "Grand"
        )
        assert state_root_child_grand_idle.transitions_from[1].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert len(state_root_child_grand_idle.transitions_to) == 2
        assert state_root_child_grand_idle.transitions_to[0].from_state == INIT_STATE
        assert state_root_child_grand_idle.transitions_to[0].to_state == "Idle"
        assert state_root_child_grand_idle.transitions_to[0].event is None
        assert state_root_child_grand_idle.transitions_to[0].guard is None
        assert state_root_child_grand_idle.transitions_to[0].effects == []
        assert (
            state_root_child_grand_idle.transitions_to[0].parent_ref().name == "Grand"
        )
        assert state_root_child_grand_idle.transitions_to[0].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand_idle.transitions_to[1].from_state == "Running"
        assert state_root_child_grand_idle.transitions_to[1].to_state == "Idle"
        assert state_root_child_grand_idle.transitions_to[1].event == Event(
            name="Stop", state_path=("Root", "Bus"), extra_name="Top Stop"
        )
        assert state_root_child_grand_idle.transitions_to[1].guard is None
        assert state_root_child_grand_idle.transitions_to[1].effects == []
        assert (
            state_root_child_grand_idle.transitions_to[1].parent_ref().name == "Grand"
        )
        assert state_root_child_grand_idle.transitions_to[1].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )

    def test_state_root_child_grand_idle_to_ast_node(self, state_root_child_grand_idle):
        ast_node = state_root_child_grand_idle.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Idle",
            extra_name=None,
            events=[],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_root_child_grand_idle_list_on_enters(
        self, state_root_child_grand_idle
    ):
        lst = state_root_child_grand_idle.list_on_enters()
        assert lst == []

        lst = state_root_child_grand_idle.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_child_grand_idle.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_child_grand_idle.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_child_grand_idle.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_root_child_grand_idle.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_root_child_grand_idle.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_child_grand_idle.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_root_child_grand_idle.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_root_child_grand_idle_during_aspects(
        self, state_root_child_grand_idle
    ):
        lst = state_root_child_grand_idle.list_on_during_aspects()
        assert lst == []

        lst = state_root_child_grand_idle.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_child_grand_idle.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_child_grand_idle.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_child_grand_idle.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_child_grand_idle.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_child_grand_idle.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_child_grand_idle.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_child_grand_idle.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_root_child_grand_idle_during_aspect_recursively(
        self, state_root_child_grand_idle
    ):
        lst = state_root_child_grand_idle.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_root_child_grand_idle.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_root_child_grand_running(self, state_root_child_grand_running):
        assert state_root_child_grand_running.name == "Running"
        assert state_root_child_grand_running.path == (
            "Root",
            "Child",
            "Grand",
            "Running",
        )
        assert sorted(state_root_child_grand_running.substates.keys()) == []
        assert state_root_child_grand_running.events == {}
        assert state_root_child_grand_running.transitions == []
        assert state_root_child_grand_running.named_functions == {}
        assert state_root_child_grand_running.on_enters == []
        assert state_root_child_grand_running.on_durings == []
        assert state_root_child_grand_running.on_exits == []
        assert state_root_child_grand_running.on_during_aspects == []
        assert state_root_child_grand_running.parent_ref().name == "Grand"
        assert state_root_child_grand_running.parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand_running.substate_name_to_id == {}
        assert state_root_child_grand_running.extra_name is None
        assert not state_root_child_grand_running.is_pseudo
        assert state_root_child_grand_running.abstract_on_during_aspects == []
        assert state_root_child_grand_running.abstract_on_durings == []
        assert state_root_child_grand_running.abstract_on_enters == []
        assert state_root_child_grand_running.abstract_on_exits == []
        assert state_root_child_grand_running.init_transitions == []
        assert state_root_child_grand_running.is_leaf_state
        assert not state_root_child_grand_running.is_root_state
        assert state_root_child_grand_running.is_stoppable
        assert state_root_child_grand_running.non_abstract_on_during_aspects == []
        assert state_root_child_grand_running.non_abstract_on_durings == []
        assert state_root_child_grand_running.non_abstract_on_enters == []
        assert state_root_child_grand_running.non_abstract_on_exits == []
        assert state_root_child_grand_running.parent.name == "Grand"
        assert state_root_child_grand_running.parent.path == ("Root", "Child", "Grand")
        assert state_root_child_grand_running.transitions_entering_children == []
        assert (
            len(state_root_child_grand_running.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_root_child_grand_running.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_root_child_grand_running.transitions_from) == 2
        assert (
            state_root_child_grand_running.transitions_from[0].from_state == "Running"
        )
        assert state_root_child_grand_running.transitions_from[0].to_state == "Tripped"
        assert state_root_child_grand_running.transitions_from[0].event == Event(
            name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
        )
        assert state_root_child_grand_running.transitions_from[0].guard is None
        assert state_root_child_grand_running.transitions_from[0].effects == []
        assert (
            state_root_child_grand_running.transitions_from[0].parent_ref().name
            == "Grand"
        )
        assert state_root_child_grand_running.transitions_from[0].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert (
            state_root_child_grand_running.transitions_from[1].from_state == "Running"
        )
        assert state_root_child_grand_running.transitions_from[1].to_state == "Idle"
        assert state_root_child_grand_running.transitions_from[1].event == Event(
            name="Stop", state_path=("Root", "Bus"), extra_name="Top Stop"
        )
        assert state_root_child_grand_running.transitions_from[1].guard is None
        assert state_root_child_grand_running.transitions_from[1].effects == []
        assert (
            state_root_child_grand_running.transitions_from[1].parent_ref().name
            == "Grand"
        )
        assert state_root_child_grand_running.transitions_from[1].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert len(state_root_child_grand_running.transitions_to) == 1
        assert state_root_child_grand_running.transitions_to[0].from_state == "Idle"
        assert state_root_child_grand_running.transitions_to[0].to_state == "Running"
        assert state_root_child_grand_running.transitions_to[0].event == Event(
            name="Start", state_path=("Root", "Bus"), extra_name="Top Start"
        )
        assert state_root_child_grand_running.transitions_to[0].guard is None
        assert state_root_child_grand_running.transitions_to[0].effects == []
        assert (
            state_root_child_grand_running.transitions_to[0].parent_ref().name
            == "Grand"
        )
        assert state_root_child_grand_running.transitions_to[0].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )

    def test_state_root_child_grand_running_to_ast_node(
        self, state_root_child_grand_running
    ):
        ast_node = state_root_child_grand_running.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Running",
            extra_name=None,
            events=[],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_root_child_grand_running_list_on_enters(
        self, state_root_child_grand_running
    ):
        lst = state_root_child_grand_running.list_on_enters()
        assert lst == []

        lst = state_root_child_grand_running.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_child_grand_running.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_child_grand_running.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_child_grand_running.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_root_child_grand_running.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_root_child_grand_running.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_child_grand_running.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_root_child_grand_running.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_root_child_grand_running_during_aspects(
        self, state_root_child_grand_running
    ):
        lst = state_root_child_grand_running.list_on_during_aspects()
        assert lst == []

        lst = state_root_child_grand_running.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_child_grand_running.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_child_grand_running.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_child_grand_running.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_child_grand_running.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_child_grand_running.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_child_grand_running.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_child_grand_running.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_root_child_grand_running_during_aspect_recursively(
        self, state_root_child_grand_running
    ):
        lst = state_root_child_grand_running.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_root_child_grand_running.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_root_child_grand_tripped(self, state_root_child_grand_tripped):
        assert state_root_child_grand_tripped.name == "Tripped"
        assert state_root_child_grand_tripped.path == (
            "Root",
            "Child",
            "Grand",
            "Tripped",
        )
        assert sorted(state_root_child_grand_tripped.substates.keys()) == []
        assert state_root_child_grand_tripped.events == {}
        assert state_root_child_grand_tripped.transitions == []
        assert state_root_child_grand_tripped.named_functions == {}
        assert state_root_child_grand_tripped.on_enters == []
        assert state_root_child_grand_tripped.on_durings == []
        assert state_root_child_grand_tripped.on_exits == []
        assert state_root_child_grand_tripped.on_during_aspects == []
        assert state_root_child_grand_tripped.parent_ref().name == "Grand"
        assert state_root_child_grand_tripped.parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand_tripped.substate_name_to_id == {}
        assert state_root_child_grand_tripped.extra_name is None
        assert not state_root_child_grand_tripped.is_pseudo
        assert state_root_child_grand_tripped.abstract_on_during_aspects == []
        assert state_root_child_grand_tripped.abstract_on_durings == []
        assert state_root_child_grand_tripped.abstract_on_enters == []
        assert state_root_child_grand_tripped.abstract_on_exits == []
        assert state_root_child_grand_tripped.init_transitions == []
        assert state_root_child_grand_tripped.is_leaf_state
        assert not state_root_child_grand_tripped.is_root_state
        assert state_root_child_grand_tripped.is_stoppable
        assert state_root_child_grand_tripped.non_abstract_on_during_aspects == []
        assert state_root_child_grand_tripped.non_abstract_on_durings == []
        assert state_root_child_grand_tripped.non_abstract_on_enters == []
        assert state_root_child_grand_tripped.non_abstract_on_exits == []
        assert state_root_child_grand_tripped.parent.name == "Grand"
        assert state_root_child_grand_tripped.parent.path == ("Root", "Child", "Grand")
        assert state_root_child_grand_tripped.transitions_entering_children == []
        assert (
            len(state_root_child_grand_tripped.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_root_child_grand_tripped.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_root_child_grand_tripped.transitions_from) == 1
        assert (
            state_root_child_grand_tripped.transitions_from[0].from_state == "Tripped"
        )
        assert state_root_child_grand_tripped.transitions_from[0].to_state == "Tripped"
        assert state_root_child_grand_tripped.transitions_from[0].event == Event(
            name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
        )
        assert state_root_child_grand_tripped.transitions_from[0].guard is None
        assert state_root_child_grand_tripped.transitions_from[0].effects == []
        assert (
            state_root_child_grand_tripped.transitions_from[0].parent_ref().name
            == "Grand"
        )
        assert state_root_child_grand_tripped.transitions_from[0].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert len(state_root_child_grand_tripped.transitions_to) == 3
        assert state_root_child_grand_tripped.transitions_to[0].from_state == "Idle"
        assert state_root_child_grand_tripped.transitions_to[0].to_state == "Tripped"
        assert state_root_child_grand_tripped.transitions_to[0].event == Event(
            name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
        )
        assert state_root_child_grand_tripped.transitions_to[0].guard is None
        assert state_root_child_grand_tripped.transitions_to[0].effects == []
        assert (
            state_root_child_grand_tripped.transitions_to[0].parent_ref().name
            == "Grand"
        )
        assert state_root_child_grand_tripped.transitions_to[0].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand_tripped.transitions_to[1].from_state == "Running"
        assert state_root_child_grand_tripped.transitions_to[1].to_state == "Tripped"
        assert state_root_child_grand_tripped.transitions_to[1].event == Event(
            name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
        )
        assert state_root_child_grand_tripped.transitions_to[1].guard is None
        assert state_root_child_grand_tripped.transitions_to[1].effects == []
        assert (
            state_root_child_grand_tripped.transitions_to[1].parent_ref().name
            == "Grand"
        )
        assert state_root_child_grand_tripped.transitions_to[1].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )
        assert state_root_child_grand_tripped.transitions_to[2].from_state == "Tripped"
        assert state_root_child_grand_tripped.transitions_to[2].to_state == "Tripped"
        assert state_root_child_grand_tripped.transitions_to[2].event == Event(
            name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
        )
        assert state_root_child_grand_tripped.transitions_to[2].guard is None
        assert state_root_child_grand_tripped.transitions_to[2].effects == []
        assert (
            state_root_child_grand_tripped.transitions_to[2].parent_ref().name
            == "Grand"
        )
        assert state_root_child_grand_tripped.transitions_to[2].parent_ref().path == (
            "Root",
            "Child",
            "Grand",
        )

    def test_state_root_child_grand_tripped_to_ast_node(
        self, state_root_child_grand_tripped
    ):
        ast_node = state_root_child_grand_tripped.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Tripped",
            extra_name=None,
            events=[],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_root_child_grand_tripped_list_on_enters(
        self, state_root_child_grand_tripped
    ):
        lst = state_root_child_grand_tripped.list_on_enters()
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_root_child_grand_tripped_during_aspects(
        self, state_root_child_grand_tripped
    ):
        lst = state_root_child_grand_tripped.list_on_during_aspects()
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_root_child_grand_tripped_during_aspect_recursively(
        self, state_root_child_grand_tripped
    ):
        lst = state_root_child_grand_tripped.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_root_child_grand_tripped.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_root_child_innerbus(self, state_root_child_innerbus):
        assert state_root_child_innerbus.name == "InnerBus"
        assert state_root_child_innerbus.path == ("Root", "Child", "InnerBus")
        assert sorted(state_root_child_innerbus.substates.keys()) == []
        assert state_root_child_innerbus.events == {}
        assert state_root_child_innerbus.transitions == []
        assert state_root_child_innerbus.named_functions == {}
        assert state_root_child_innerbus.on_enters == []
        assert state_root_child_innerbus.on_durings == []
        assert state_root_child_innerbus.on_exits == []
        assert state_root_child_innerbus.on_during_aspects == []
        assert state_root_child_innerbus.parent_ref().name == "Child"
        assert state_root_child_innerbus.parent_ref().path == ("Root", "Child")
        assert state_root_child_innerbus.substate_name_to_id == {}
        assert state_root_child_innerbus.extra_name is None
        assert not state_root_child_innerbus.is_pseudo
        assert state_root_child_innerbus.abstract_on_during_aspects == []
        assert state_root_child_innerbus.abstract_on_durings == []
        assert state_root_child_innerbus.abstract_on_enters == []
        assert state_root_child_innerbus.abstract_on_exits == []
        assert state_root_child_innerbus.init_transitions == []
        assert state_root_child_innerbus.is_leaf_state
        assert not state_root_child_innerbus.is_root_state
        assert state_root_child_innerbus.is_stoppable
        assert state_root_child_innerbus.non_abstract_on_during_aspects == []
        assert state_root_child_innerbus.non_abstract_on_durings == []
        assert state_root_child_innerbus.non_abstract_on_enters == []
        assert state_root_child_innerbus.non_abstract_on_exits == []
        assert state_root_child_innerbus.parent.name == "Child"
        assert state_root_child_innerbus.parent.path == ("Root", "Child")
        assert state_root_child_innerbus.transitions_entering_children == []
        assert (
            len(state_root_child_innerbus.transitions_entering_children_simplified) == 1
        )
        assert (
            state_root_child_innerbus.transitions_entering_children_simplified[0]
            is None
        )
        assert state_root_child_innerbus.transitions_from == []
        assert state_root_child_innerbus.transitions_to == []

    def test_state_root_child_innerbus_to_ast_node(self, state_root_child_innerbus):
        ast_node = state_root_child_innerbus.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="InnerBus",
            extra_name=None,
            events=[],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_root_child_innerbus_list_on_enters(self, state_root_child_innerbus):
        lst = state_root_child_innerbus.list_on_enters()
        assert lst == []

        lst = state_root_child_innerbus.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_child_innerbus.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_child_innerbus.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_child_innerbus.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_root_child_innerbus.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root_child_innerbus.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_child_innerbus.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root_child_innerbus.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_child_innerbus_during_aspects(self, state_root_child_innerbus):
        lst = state_root_child_innerbus.list_on_during_aspects()
        assert lst == []

        lst = state_root_child_innerbus.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_child_innerbus.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_child_innerbus.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_child_innerbus.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_root_child_innerbus.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_root_child_innerbus.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_child_innerbus.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_root_child_innerbus.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_root_child_innerbus_during_aspect_recursively(
        self, state_root_child_innerbus
    ):
        lst = state_root_child_innerbus.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_root_child_innerbus.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_root_bus(self, state_root_bus):
        assert state_root_bus.name == "Bus"
        assert state_root_bus.path == ("Root", "Bus")
        assert sorted(state_root_bus.substates.keys()) == []
        assert state_root_bus.events == {
            "Start": Event(
                name="Start", state_path=("Root", "Bus"), extra_name="Top Start"
            ),
            "Stop": Event(
                name="Stop", state_path=("Root", "Bus"), extra_name="Top Stop"
            ),
            "Trip": Event(
                name="Trip", state_path=("Root", "Bus"), extra_name="Top Trip"
            ),
        }
        assert state_root_bus.transitions == []
        assert state_root_bus.named_functions == {}
        assert state_root_bus.on_enters == []
        assert state_root_bus.on_durings == []
        assert state_root_bus.on_exits == []
        assert state_root_bus.on_during_aspects == []
        assert state_root_bus.parent_ref().name == "Root"
        assert state_root_bus.parent_ref().path == ("Root",)
        assert state_root_bus.substate_name_to_id == {}
        assert state_root_bus.extra_name is None
        assert not state_root_bus.is_pseudo
        assert state_root_bus.abstract_on_during_aspects == []
        assert state_root_bus.abstract_on_durings == []
        assert state_root_bus.abstract_on_enters == []
        assert state_root_bus.abstract_on_exits == []
        assert state_root_bus.init_transitions == []
        assert state_root_bus.is_leaf_state
        assert not state_root_bus.is_root_state
        assert state_root_bus.is_stoppable
        assert state_root_bus.non_abstract_on_during_aspects == []
        assert state_root_bus.non_abstract_on_durings == []
        assert state_root_bus.non_abstract_on_enters == []
        assert state_root_bus.non_abstract_on_exits == []
        assert state_root_bus.parent.name == "Root"
        assert state_root_bus.parent.path == ("Root",)
        assert state_root_bus.transitions_entering_children == []
        assert len(state_root_bus.transitions_entering_children_simplified) == 1
        assert state_root_bus.transitions_entering_children_simplified[0] is None
        assert state_root_bus.transitions_from == []
        assert state_root_bus.transitions_to == []

    def test_state_root_bus_to_ast_node(self, state_root_bus):
        ast_node = state_root_bus.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Bus",
            extra_name=None,
            events=[
                dsl_nodes.EventDefinition(name="Start", extra_name="Top Start"),
                dsl_nodes.EventDefinition(name="Stop", extra_name="Top Stop"),
                dsl_nodes.EventDefinition(name="Trip", extra_name="Top Trip"),
            ],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_root_bus_list_on_enters(self, state_root_bus):
        lst = state_root_bus.list_on_enters()
        assert lst == []

        lst = state_root_bus.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_root_bus.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_root_bus.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_root_bus.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_root_bus.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_root_bus.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_root_bus.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_root_bus.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_root_bus_during_aspects(self, state_root_bus):
        lst = state_root_bus.list_on_during_aspects()
        assert lst == []

        lst = state_root_bus.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_root_bus.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_root_bus.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_root_bus.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_root_bus.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_root_bus.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_root_bus.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_root_bus.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_root_bus_during_aspect_recursively(self, state_root_bus):
        lst = state_root_bus.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_root_bus.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
state Root {
    state Child named 'Child Layer' {
        state Grand named 'Grand Layer' {
            state Idle;
            state Running;
            state Tripped;
            Idle -> Tripped : /Bus.Trip;
            Running -> Tripped : /Bus.Trip;
            Tripped -> Tripped : /Bus.Trip;
            [*] -> Idle;
            Idle -> Running : /Bus.Start;
            Running -> Idle : /Bus.Stop;
        }
        state InnerBus;
        [*] -> Grand;
    }
    state Bus {
        event Start named 'Top Start';
        event Stop named 'Top Stop';
        event Trip named 'Top Trip';
    }
    [*] -> Child;
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

state "Root" as root <<composite>> {
    state "Child Layer" as root__child <<composite>> {
        state "Grand Layer" as root__child__grand <<composite>> {
            state "Idle" as root__child__grand__idle
            state "Running" as root__child__grand__running
            state "Tripped" as root__child__grand__tripped
            root__child__grand__idle --> root__child__grand__tripped : Top Trip (/Bus.Trip)
            root__child__grand__running --> root__child__grand__tripped : Top Trip (/Bus.Trip)
            root__child__grand__tripped --> root__child__grand__tripped : Top Trip (/Bus.Trip)
            [*] --> root__child__grand__idle
            root__child__grand__idle --> root__child__grand__running : Top Start (/Bus.Start)
            root__child__grand__running --> root__child__grand__idle : Top Stop (/Bus.Stop)
        }
        state "InnerBus" as root__child__inner_bus
        [*] --> root__child__grand
    }
    state "Bus" as root__bus
    [*] --> root__child
}
[*] --> root
root --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml(options="full")),
        )
