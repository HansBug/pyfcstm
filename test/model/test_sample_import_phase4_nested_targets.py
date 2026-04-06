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
state Plant {
    state Bus;
    import "./modules/worker.fcstm" as Worker named "Mapped Worker" {
        event /Stop -> Bus.Stop named "Plant Stop";
        event /Fault -> /GlobalFault named "Global Fault";
        event /Reset -> Bus.Reset;
    }
    [*] -> Worker;
}
        """,
        )
        _write_text_file(
            "modules/worker.fcstm",
            """
state WorkerRoot {
    event Fault named "Local Fault";
    event Reset named "Local Reset";
    state Idle;
    state Failed;
    state Halted;
    [*] -> Idle;
    Idle -> Failed : Fault;
    Failed -> Halted : /Stop;
    Halted -> Idle : Reset;
}
        """,
        )
        entry_file = pathlib.Path("main.fcstm")
        ast_node = parse_state_machine_dsl(entry_file.read_text(encoding="utf-8"))
        model = parse_dsl_node_to_state_machine(ast_node, path=entry_file)
        return model


@pytest.fixture()
def state_plant(model):
    return model.root_state


@pytest.fixture()
def state_plant_worker(state_plant):
    return state_plant.substates["Worker"]


@pytest.fixture()
def state_plant_worker_idle(state_plant_worker):
    return state_plant_worker.substates["Idle"]


@pytest.fixture()
def state_plant_worker_failed(state_plant_worker):
    return state_plant_worker.substates["Failed"]


@pytest.fixture()
def state_plant_worker_halted(state_plant_worker):
    return state_plant_worker.substates["Halted"]


@pytest.fixture()
def state_plant_bus(state_plant):
    return state_plant.substates["Bus"]


@pytest.mark.unittest
class TestModelStatePlant:
    def test_model(self, model):
        assert model.defines == {}
        assert model.root_state.name == "Plant"
        assert model.root_state.path == ("Plant",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == []
        assert ast_node.root_state.name == "Plant"

    def test_state_plant(self, state_plant):
        assert state_plant.name == "Plant"
        assert state_plant.path == ("Plant",)
        assert sorted(state_plant.substates.keys()) == ["Bus", "Worker"]
        assert state_plant.events == {
            "GlobalFault": Event(
                name="GlobalFault", state_path=("Plant",), extra_name="Global Fault"
            )
        }
        assert len(state_plant.transitions) == 1
        assert state_plant.transitions[0].from_state == INIT_STATE
        assert state_plant.transitions[0].to_state == "Worker"
        assert state_plant.transitions[0].event is None
        assert state_plant.transitions[0].guard is None
        assert state_plant.transitions[0].effects == []
        assert state_plant.transitions[0].parent_ref().name == "Plant"
        assert state_plant.transitions[0].parent_ref().path == ("Plant",)
        assert state_plant.named_functions == {}
        assert state_plant.on_enters == []
        assert state_plant.on_durings == []
        assert state_plant.on_exits == []
        assert state_plant.on_during_aspects == []
        assert state_plant.parent_ref is None
        assert state_plant.substate_name_to_id == {"Worker": 0, "Bus": 1}
        assert state_plant.extra_name is None
        assert not state_plant.is_pseudo
        assert state_plant.abstract_on_during_aspects == []
        assert state_plant.abstract_on_durings == []
        assert state_plant.abstract_on_enters == []
        assert state_plant.abstract_on_exits == []
        assert len(state_plant.init_transitions) == 1
        assert state_plant.init_transitions[0].from_state == INIT_STATE
        assert state_plant.init_transitions[0].to_state == "Worker"
        assert state_plant.init_transitions[0].event is None
        assert state_plant.init_transitions[0].guard is None
        assert state_plant.init_transitions[0].effects == []
        assert state_plant.init_transitions[0].parent_ref().name == "Plant"
        assert state_plant.init_transitions[0].parent_ref().path == ("Plant",)
        assert not state_plant.is_leaf_state
        assert state_plant.is_root_state
        assert not state_plant.is_stoppable
        assert state_plant.non_abstract_on_during_aspects == []
        assert state_plant.non_abstract_on_durings == []
        assert state_plant.non_abstract_on_enters == []
        assert state_plant.non_abstract_on_exits == []
        assert state_plant.parent is None
        assert len(state_plant.transitions_entering_children) == 1
        assert state_plant.transitions_entering_children[0].from_state == INIT_STATE
        assert state_plant.transitions_entering_children[0].to_state == "Worker"
        assert state_plant.transitions_entering_children[0].event is None
        assert state_plant.transitions_entering_children[0].guard is None
        assert state_plant.transitions_entering_children[0].effects == []
        assert state_plant.transitions_entering_children[0].parent_ref().name == "Plant"
        assert state_plant.transitions_entering_children[0].parent_ref().path == (
            "Plant",
        )
        assert len(state_plant.transitions_entering_children_simplified) == 1
        assert (
            state_plant.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_plant.transitions_entering_children_simplified[0].to_state == "Worker"
        )
        assert state_plant.transitions_entering_children_simplified[0].event is None
        assert state_plant.transitions_entering_children_simplified[0].guard is None
        assert state_plant.transitions_entering_children_simplified[0].effects == []
        assert (
            state_plant.transitions_entering_children_simplified[0].parent_ref().name
            == "Plant"
        )
        assert state_plant.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Plant",)
        assert len(state_plant.transitions_from) == 1
        assert state_plant.transitions_from[0].from_state == "Plant"
        assert state_plant.transitions_from[0].to_state == EXIT_STATE
        assert state_plant.transitions_from[0].event is None
        assert state_plant.transitions_from[0].guard is None
        assert state_plant.transitions_from[0].effects == []
        assert state_plant.transitions_from[0].parent_ref is None
        assert len(state_plant.transitions_to) == 1
        assert state_plant.transitions_to[0].from_state == INIT_STATE
        assert state_plant.transitions_to[0].to_state == "Plant"
        assert state_plant.transitions_to[0].event is None
        assert state_plant.transitions_to[0].guard is None
        assert state_plant.transitions_to[0].effects == []
        assert state_plant.transitions_to[0].parent_ref is None

    def test_state_plant_to_ast_node(self, state_plant):
        ast_node = state_plant.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Plant",
            extra_name=None,
            events=[
                dsl_nodes.EventDefinition(name="GlobalFault", extra_name="Global Fault")
            ],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Worker",
                    extra_name="Mapped Worker",
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
                            name="Failed",
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
                            name="Halted",
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
                            to_state="Idle",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Idle",
                            to_state="Failed",
                            event_id=dsl_nodes.ChainID(
                                path=["GlobalFault"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Failed",
                            to_state="Halted",
                            event_id=dsl_nodes.ChainID(
                                path=["Bus", "Stop"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Halted",
                            to_state="Idle",
                            event_id=dsl_nodes.ChainID(
                                path=["Bus", "Reset"], is_absolute=True
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
                    name="Bus",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="Stop", extra_name="Plant Stop"),
                        dsl_nodes.EventDefinition(
                            name="Reset", extra_name="Local Reset"
                        ),
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
                    to_state="Worker",
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

    def test_state_plant_list_on_enters(self, state_plant):
        lst = state_plant.list_on_enters()
        assert lst == []

        lst = state_plant.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_plant.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_during_aspects(self, state_plant):
        lst = state_plant.list_on_during_aspects()
        assert lst == []

        lst = state_plant.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_plant.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_plant.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_plant.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_plant_worker(self, state_plant_worker):
        assert state_plant_worker.name == "Worker"
        assert state_plant_worker.path == ("Plant", "Worker")
        assert sorted(state_plant_worker.substates.keys()) == [
            "Failed",
            "Halted",
            "Idle",
        ]
        assert state_plant_worker.events == {}
        assert len(state_plant_worker.transitions) == 4
        assert state_plant_worker.transitions[0].from_state == INIT_STATE
        assert state_plant_worker.transitions[0].to_state == "Idle"
        assert state_plant_worker.transitions[0].event is None
        assert state_plant_worker.transitions[0].guard is None
        assert state_plant_worker.transitions[0].effects == []
        assert state_plant_worker.transitions[0].parent_ref().name == "Worker"
        assert state_plant_worker.transitions[0].parent_ref().path == (
            "Plant",
            "Worker",
        )
        assert state_plant_worker.transitions[1].from_state == "Idle"
        assert state_plant_worker.transitions[1].to_state == "Failed"
        assert state_plant_worker.transitions[1].event == Event(
            name="GlobalFault", state_path=("Plant",), extra_name="Global Fault"
        )
        assert state_plant_worker.transitions[1].guard is None
        assert state_plant_worker.transitions[1].effects == []
        assert state_plant_worker.transitions[1].parent_ref().name == "Worker"
        assert state_plant_worker.transitions[1].parent_ref().path == (
            "Plant",
            "Worker",
        )
        assert state_plant_worker.transitions[2].from_state == "Failed"
        assert state_plant_worker.transitions[2].to_state == "Halted"
        assert state_plant_worker.transitions[2].event == Event(
            name="Stop", state_path=("Plant", "Bus"), extra_name="Plant Stop"
        )
        assert state_plant_worker.transitions[2].guard is None
        assert state_plant_worker.transitions[2].effects == []
        assert state_plant_worker.transitions[2].parent_ref().name == "Worker"
        assert state_plant_worker.transitions[2].parent_ref().path == (
            "Plant",
            "Worker",
        )
        assert state_plant_worker.transitions[3].from_state == "Halted"
        assert state_plant_worker.transitions[3].to_state == "Idle"
        assert state_plant_worker.transitions[3].event == Event(
            name="Reset", state_path=("Plant", "Bus"), extra_name="Local Reset"
        )
        assert state_plant_worker.transitions[3].guard is None
        assert state_plant_worker.transitions[3].effects == []
        assert state_plant_worker.transitions[3].parent_ref().name == "Worker"
        assert state_plant_worker.transitions[3].parent_ref().path == (
            "Plant",
            "Worker",
        )
        assert state_plant_worker.named_functions == {}
        assert state_plant_worker.on_enters == []
        assert state_plant_worker.on_durings == []
        assert state_plant_worker.on_exits == []
        assert state_plant_worker.on_during_aspects == []
        assert state_plant_worker.parent_ref().name == "Plant"
        assert state_plant_worker.parent_ref().path == ("Plant",)
        assert state_plant_worker.substate_name_to_id == {
            "Idle": 0,
            "Failed": 1,
            "Halted": 2,
        }
        assert state_plant_worker.extra_name == "Mapped Worker"
        assert not state_plant_worker.is_pseudo
        assert state_plant_worker.abstract_on_during_aspects == []
        assert state_plant_worker.abstract_on_durings == []
        assert state_plant_worker.abstract_on_enters == []
        assert state_plant_worker.abstract_on_exits == []
        assert len(state_plant_worker.init_transitions) == 1
        assert state_plant_worker.init_transitions[0].from_state == INIT_STATE
        assert state_plant_worker.init_transitions[0].to_state == "Idle"
        assert state_plant_worker.init_transitions[0].event is None
        assert state_plant_worker.init_transitions[0].guard is None
        assert state_plant_worker.init_transitions[0].effects == []
        assert state_plant_worker.init_transitions[0].parent_ref().name == "Worker"
        assert state_plant_worker.init_transitions[0].parent_ref().path == (
            "Plant",
            "Worker",
        )
        assert not state_plant_worker.is_leaf_state
        assert not state_plant_worker.is_root_state
        assert not state_plant_worker.is_stoppable
        assert state_plant_worker.non_abstract_on_during_aspects == []
        assert state_plant_worker.non_abstract_on_durings == []
        assert state_plant_worker.non_abstract_on_enters == []
        assert state_plant_worker.non_abstract_on_exits == []
        assert state_plant_worker.parent.name == "Plant"
        assert state_plant_worker.parent.path == ("Plant",)
        assert len(state_plant_worker.transitions_entering_children) == 1
        assert (
            state_plant_worker.transitions_entering_children[0].from_state == INIT_STATE
        )
        assert state_plant_worker.transitions_entering_children[0].to_state == "Idle"
        assert state_plant_worker.transitions_entering_children[0].event is None
        assert state_plant_worker.transitions_entering_children[0].guard is None
        assert state_plant_worker.transitions_entering_children[0].effects == []
        assert (
            state_plant_worker.transitions_entering_children[0].parent_ref().name
            == "Worker"
        )
        assert state_plant_worker.transitions_entering_children[
            0
        ].parent_ref().path == ("Plant", "Worker")
        assert len(state_plant_worker.transitions_entering_children_simplified) == 1
        assert (
            state_plant_worker.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_plant_worker.transitions_entering_children_simplified[0].to_state
            == "Idle"
        )
        assert (
            state_plant_worker.transitions_entering_children_simplified[0].event is None
        )
        assert (
            state_plant_worker.transitions_entering_children_simplified[0].guard is None
        )
        assert (
            state_plant_worker.transitions_entering_children_simplified[0].effects == []
        )
        assert (
            state_plant_worker.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "Worker"
        )
        assert state_plant_worker.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Plant", "Worker")
        assert state_plant_worker.transitions_from == []
        assert len(state_plant_worker.transitions_to) == 1
        assert state_plant_worker.transitions_to[0].from_state == INIT_STATE
        assert state_plant_worker.transitions_to[0].to_state == "Worker"
        assert state_plant_worker.transitions_to[0].event is None
        assert state_plant_worker.transitions_to[0].guard is None
        assert state_plant_worker.transitions_to[0].effects == []
        assert state_plant_worker.transitions_to[0].parent_ref().name == "Plant"
        assert state_plant_worker.transitions_to[0].parent_ref().path == ("Plant",)

    def test_state_plant_worker_to_ast_node(self, state_plant_worker):
        ast_node = state_plant_worker.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Worker",
            extra_name="Mapped Worker",
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
                    name="Failed",
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
                    name="Halted",
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
                    to_state="Idle",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Idle",
                    to_state="Failed",
                    event_id=dsl_nodes.ChainID(path=["GlobalFault"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Failed",
                    to_state="Halted",
                    event_id=dsl_nodes.ChainID(path=["Bus", "Stop"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Halted",
                    to_state="Idle",
                    event_id=dsl_nodes.ChainID(path=["Bus", "Reset"], is_absolute=True),
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

    def test_state_plant_worker_list_on_enters(self, state_plant_worker):
        lst = state_plant_worker.list_on_enters()
        assert lst == []

        lst = state_plant_worker.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_worker.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_worker.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_worker.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_plant_worker.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant_worker.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_worker.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant_worker.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_worker_during_aspects(self, state_plant_worker):
        lst = state_plant_worker.list_on_during_aspects()
        assert lst == []

        lst = state_plant_worker.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_worker.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_worker.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_worker.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_worker.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_worker.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_worker.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_worker.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_worker_idle(self, state_plant_worker_idle):
        assert state_plant_worker_idle.name == "Idle"
        assert state_plant_worker_idle.path == ("Plant", "Worker", "Idle")
        assert sorted(state_plant_worker_idle.substates.keys()) == []
        assert state_plant_worker_idle.events == {}
        assert state_plant_worker_idle.transitions == []
        assert state_plant_worker_idle.named_functions == {}
        assert state_plant_worker_idle.on_enters == []
        assert state_plant_worker_idle.on_durings == []
        assert state_plant_worker_idle.on_exits == []
        assert state_plant_worker_idle.on_during_aspects == []
        assert state_plant_worker_idle.parent_ref().name == "Worker"
        assert state_plant_worker_idle.parent_ref().path == ("Plant", "Worker")
        assert state_plant_worker_idle.substate_name_to_id == {}
        assert state_plant_worker_idle.extra_name is None
        assert not state_plant_worker_idle.is_pseudo
        assert state_plant_worker_idle.abstract_on_during_aspects == []
        assert state_plant_worker_idle.abstract_on_durings == []
        assert state_plant_worker_idle.abstract_on_enters == []
        assert state_plant_worker_idle.abstract_on_exits == []
        assert state_plant_worker_idle.init_transitions == []
        assert state_plant_worker_idle.is_leaf_state
        assert not state_plant_worker_idle.is_root_state
        assert state_plant_worker_idle.is_stoppable
        assert state_plant_worker_idle.non_abstract_on_during_aspects == []
        assert state_plant_worker_idle.non_abstract_on_durings == []
        assert state_plant_worker_idle.non_abstract_on_enters == []
        assert state_plant_worker_idle.non_abstract_on_exits == []
        assert state_plant_worker_idle.parent.name == "Worker"
        assert state_plant_worker_idle.parent.path == ("Plant", "Worker")
        assert state_plant_worker_idle.transitions_entering_children == []
        assert (
            len(state_plant_worker_idle.transitions_entering_children_simplified) == 1
        )
        assert (
            state_plant_worker_idle.transitions_entering_children_simplified[0] is None
        )
        assert len(state_plant_worker_idle.transitions_from) == 1
        assert state_plant_worker_idle.transitions_from[0].from_state == "Idle"
        assert state_plant_worker_idle.transitions_from[0].to_state == "Failed"
        assert state_plant_worker_idle.transitions_from[0].event == Event(
            name="GlobalFault", state_path=("Plant",), extra_name="Global Fault"
        )
        assert state_plant_worker_idle.transitions_from[0].guard is None
        assert state_plant_worker_idle.transitions_from[0].effects == []
        assert state_plant_worker_idle.transitions_from[0].parent_ref().name == "Worker"
        assert state_plant_worker_idle.transitions_from[0].parent_ref().path == (
            "Plant",
            "Worker",
        )
        assert len(state_plant_worker_idle.transitions_to) == 2
        assert state_plant_worker_idle.transitions_to[0].from_state == INIT_STATE
        assert state_plant_worker_idle.transitions_to[0].to_state == "Idle"
        assert state_plant_worker_idle.transitions_to[0].event is None
        assert state_plant_worker_idle.transitions_to[0].guard is None
        assert state_plant_worker_idle.transitions_to[0].effects == []
        assert state_plant_worker_idle.transitions_to[0].parent_ref().name == "Worker"
        assert state_plant_worker_idle.transitions_to[0].parent_ref().path == (
            "Plant",
            "Worker",
        )
        assert state_plant_worker_idle.transitions_to[1].from_state == "Halted"
        assert state_plant_worker_idle.transitions_to[1].to_state == "Idle"
        assert state_plant_worker_idle.transitions_to[1].event == Event(
            name="Reset", state_path=("Plant", "Bus"), extra_name="Local Reset"
        )
        assert state_plant_worker_idle.transitions_to[1].guard is None
        assert state_plant_worker_idle.transitions_to[1].effects == []
        assert state_plant_worker_idle.transitions_to[1].parent_ref().name == "Worker"
        assert state_plant_worker_idle.transitions_to[1].parent_ref().path == (
            "Plant",
            "Worker",
        )

    def test_state_plant_worker_idle_to_ast_node(self, state_plant_worker_idle):
        ast_node = state_plant_worker_idle.to_ast_node()
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

    def test_state_plant_worker_idle_list_on_enters(self, state_plant_worker_idle):
        lst = state_plant_worker_idle.list_on_enters()
        assert lst == []

        lst = state_plant_worker_idle.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_worker_idle.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_worker_idle.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_worker_idle.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_plant_worker_idle.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant_worker_idle.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_worker_idle.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant_worker_idle.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_worker_idle_during_aspects(self, state_plant_worker_idle):
        lst = state_plant_worker_idle.list_on_during_aspects()
        assert lst == []

        lst = state_plant_worker_idle.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_worker_idle.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_worker_idle.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_worker_idle.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_worker_idle.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_worker_idle.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_worker_idle.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_worker_idle.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_worker_idle_during_aspect_recursively(
        self, state_plant_worker_idle
    ):
        lst = state_plant_worker_idle.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_plant_worker_idle.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_plant_worker_failed(self, state_plant_worker_failed):
        assert state_plant_worker_failed.name == "Failed"
        assert state_plant_worker_failed.path == ("Plant", "Worker", "Failed")
        assert sorted(state_plant_worker_failed.substates.keys()) == []
        assert state_plant_worker_failed.events == {}
        assert state_plant_worker_failed.transitions == []
        assert state_plant_worker_failed.named_functions == {}
        assert state_plant_worker_failed.on_enters == []
        assert state_plant_worker_failed.on_durings == []
        assert state_plant_worker_failed.on_exits == []
        assert state_plant_worker_failed.on_during_aspects == []
        assert state_plant_worker_failed.parent_ref().name == "Worker"
        assert state_plant_worker_failed.parent_ref().path == ("Plant", "Worker")
        assert state_plant_worker_failed.substate_name_to_id == {}
        assert state_plant_worker_failed.extra_name is None
        assert not state_plant_worker_failed.is_pseudo
        assert state_plant_worker_failed.abstract_on_during_aspects == []
        assert state_plant_worker_failed.abstract_on_durings == []
        assert state_plant_worker_failed.abstract_on_enters == []
        assert state_plant_worker_failed.abstract_on_exits == []
        assert state_plant_worker_failed.init_transitions == []
        assert state_plant_worker_failed.is_leaf_state
        assert not state_plant_worker_failed.is_root_state
        assert state_plant_worker_failed.is_stoppable
        assert state_plant_worker_failed.non_abstract_on_during_aspects == []
        assert state_plant_worker_failed.non_abstract_on_durings == []
        assert state_plant_worker_failed.non_abstract_on_enters == []
        assert state_plant_worker_failed.non_abstract_on_exits == []
        assert state_plant_worker_failed.parent.name == "Worker"
        assert state_plant_worker_failed.parent.path == ("Plant", "Worker")
        assert state_plant_worker_failed.transitions_entering_children == []
        assert (
            len(state_plant_worker_failed.transitions_entering_children_simplified) == 1
        )
        assert (
            state_plant_worker_failed.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_plant_worker_failed.transitions_from) == 1
        assert state_plant_worker_failed.transitions_from[0].from_state == "Failed"
        assert state_plant_worker_failed.transitions_from[0].to_state == "Halted"
        assert state_plant_worker_failed.transitions_from[0].event == Event(
            name="Stop", state_path=("Plant", "Bus"), extra_name="Plant Stop"
        )
        assert state_plant_worker_failed.transitions_from[0].guard is None
        assert state_plant_worker_failed.transitions_from[0].effects == []
        assert (
            state_plant_worker_failed.transitions_from[0].parent_ref().name == "Worker"
        )
        assert state_plant_worker_failed.transitions_from[0].parent_ref().path == (
            "Plant",
            "Worker",
        )
        assert len(state_plant_worker_failed.transitions_to) == 1
        assert state_plant_worker_failed.transitions_to[0].from_state == "Idle"
        assert state_plant_worker_failed.transitions_to[0].to_state == "Failed"
        assert state_plant_worker_failed.transitions_to[0].event == Event(
            name="GlobalFault", state_path=("Plant",), extra_name="Global Fault"
        )
        assert state_plant_worker_failed.transitions_to[0].guard is None
        assert state_plant_worker_failed.transitions_to[0].effects == []
        assert state_plant_worker_failed.transitions_to[0].parent_ref().name == "Worker"
        assert state_plant_worker_failed.transitions_to[0].parent_ref().path == (
            "Plant",
            "Worker",
        )

    def test_state_plant_worker_failed_to_ast_node(self, state_plant_worker_failed):
        ast_node = state_plant_worker_failed.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Failed",
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

    def test_state_plant_worker_failed_list_on_enters(self, state_plant_worker_failed):
        lst = state_plant_worker_failed.list_on_enters()
        assert lst == []

        lst = state_plant_worker_failed.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_worker_failed.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_worker_failed.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_worker_failed.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_plant_worker_failed.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant_worker_failed.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_worker_failed.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant_worker_failed.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_worker_failed_during_aspects(self, state_plant_worker_failed):
        lst = state_plant_worker_failed.list_on_during_aspects()
        assert lst == []

        lst = state_plant_worker_failed.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_worker_failed.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_worker_failed.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_worker_failed.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_worker_failed.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_worker_failed.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_worker_failed.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_worker_failed.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_worker_failed_during_aspect_recursively(
        self, state_plant_worker_failed
    ):
        lst = state_plant_worker_failed.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_plant_worker_failed.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_plant_worker_halted(self, state_plant_worker_halted):
        assert state_plant_worker_halted.name == "Halted"
        assert state_plant_worker_halted.path == ("Plant", "Worker", "Halted")
        assert sorted(state_plant_worker_halted.substates.keys()) == []
        assert state_plant_worker_halted.events == {}
        assert state_plant_worker_halted.transitions == []
        assert state_plant_worker_halted.named_functions == {}
        assert state_plant_worker_halted.on_enters == []
        assert state_plant_worker_halted.on_durings == []
        assert state_plant_worker_halted.on_exits == []
        assert state_plant_worker_halted.on_during_aspects == []
        assert state_plant_worker_halted.parent_ref().name == "Worker"
        assert state_plant_worker_halted.parent_ref().path == ("Plant", "Worker")
        assert state_plant_worker_halted.substate_name_to_id == {}
        assert state_plant_worker_halted.extra_name is None
        assert not state_plant_worker_halted.is_pseudo
        assert state_plant_worker_halted.abstract_on_during_aspects == []
        assert state_plant_worker_halted.abstract_on_durings == []
        assert state_plant_worker_halted.abstract_on_enters == []
        assert state_plant_worker_halted.abstract_on_exits == []
        assert state_plant_worker_halted.init_transitions == []
        assert state_plant_worker_halted.is_leaf_state
        assert not state_plant_worker_halted.is_root_state
        assert state_plant_worker_halted.is_stoppable
        assert state_plant_worker_halted.non_abstract_on_during_aspects == []
        assert state_plant_worker_halted.non_abstract_on_durings == []
        assert state_plant_worker_halted.non_abstract_on_enters == []
        assert state_plant_worker_halted.non_abstract_on_exits == []
        assert state_plant_worker_halted.parent.name == "Worker"
        assert state_plant_worker_halted.parent.path == ("Plant", "Worker")
        assert state_plant_worker_halted.transitions_entering_children == []
        assert (
            len(state_plant_worker_halted.transitions_entering_children_simplified) == 1
        )
        assert (
            state_plant_worker_halted.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_plant_worker_halted.transitions_from) == 1
        assert state_plant_worker_halted.transitions_from[0].from_state == "Halted"
        assert state_plant_worker_halted.transitions_from[0].to_state == "Idle"
        assert state_plant_worker_halted.transitions_from[0].event == Event(
            name="Reset", state_path=("Plant", "Bus"), extra_name="Local Reset"
        )
        assert state_plant_worker_halted.transitions_from[0].guard is None
        assert state_plant_worker_halted.transitions_from[0].effects == []
        assert (
            state_plant_worker_halted.transitions_from[0].parent_ref().name == "Worker"
        )
        assert state_plant_worker_halted.transitions_from[0].parent_ref().path == (
            "Plant",
            "Worker",
        )
        assert len(state_plant_worker_halted.transitions_to) == 1
        assert state_plant_worker_halted.transitions_to[0].from_state == "Failed"
        assert state_plant_worker_halted.transitions_to[0].to_state == "Halted"
        assert state_plant_worker_halted.transitions_to[0].event == Event(
            name="Stop", state_path=("Plant", "Bus"), extra_name="Plant Stop"
        )
        assert state_plant_worker_halted.transitions_to[0].guard is None
        assert state_plant_worker_halted.transitions_to[0].effects == []
        assert state_plant_worker_halted.transitions_to[0].parent_ref().name == "Worker"
        assert state_plant_worker_halted.transitions_to[0].parent_ref().path == (
            "Plant",
            "Worker",
        )

    def test_state_plant_worker_halted_to_ast_node(self, state_plant_worker_halted):
        ast_node = state_plant_worker_halted.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Halted",
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

    def test_state_plant_worker_halted_list_on_enters(self, state_plant_worker_halted):
        lst = state_plant_worker_halted.list_on_enters()
        assert lst == []

        lst = state_plant_worker_halted.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_worker_halted.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_worker_halted.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_worker_halted.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_plant_worker_halted.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant_worker_halted.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_worker_halted.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant_worker_halted.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_worker_halted_during_aspects(self, state_plant_worker_halted):
        lst = state_plant_worker_halted.list_on_during_aspects()
        assert lst == []

        lst = state_plant_worker_halted.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_worker_halted.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_worker_halted.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_worker_halted.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_worker_halted.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_worker_halted.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_worker_halted.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_worker_halted.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_worker_halted_during_aspect_recursively(
        self, state_plant_worker_halted
    ):
        lst = state_plant_worker_halted.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_plant_worker_halted.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_plant_bus(self, state_plant_bus):
        assert state_plant_bus.name == "Bus"
        assert state_plant_bus.path == ("Plant", "Bus")
        assert sorted(state_plant_bus.substates.keys()) == []
        assert state_plant_bus.events == {
            "Stop": Event(
                name="Stop", state_path=("Plant", "Bus"), extra_name="Plant Stop"
            ),
            "Reset": Event(
                name="Reset", state_path=("Plant", "Bus"), extra_name="Local Reset"
            ),
        }
        assert state_plant_bus.transitions == []
        assert state_plant_bus.named_functions == {}
        assert state_plant_bus.on_enters == []
        assert state_plant_bus.on_durings == []
        assert state_plant_bus.on_exits == []
        assert state_plant_bus.on_during_aspects == []
        assert state_plant_bus.parent_ref().name == "Plant"
        assert state_plant_bus.parent_ref().path == ("Plant",)
        assert state_plant_bus.substate_name_to_id == {}
        assert state_plant_bus.extra_name is None
        assert not state_plant_bus.is_pseudo
        assert state_plant_bus.abstract_on_during_aspects == []
        assert state_plant_bus.abstract_on_durings == []
        assert state_plant_bus.abstract_on_enters == []
        assert state_plant_bus.abstract_on_exits == []
        assert state_plant_bus.init_transitions == []
        assert state_plant_bus.is_leaf_state
        assert not state_plant_bus.is_root_state
        assert state_plant_bus.is_stoppable
        assert state_plant_bus.non_abstract_on_during_aspects == []
        assert state_plant_bus.non_abstract_on_durings == []
        assert state_plant_bus.non_abstract_on_enters == []
        assert state_plant_bus.non_abstract_on_exits == []
        assert state_plant_bus.parent.name == "Plant"
        assert state_plant_bus.parent.path == ("Plant",)
        assert state_plant_bus.transitions_entering_children == []
        assert len(state_plant_bus.transitions_entering_children_simplified) == 1
        assert state_plant_bus.transitions_entering_children_simplified[0] is None
        assert state_plant_bus.transitions_from == []
        assert state_plant_bus.transitions_to == []

    def test_state_plant_bus_to_ast_node(self, state_plant_bus):
        ast_node = state_plant_bus.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Bus",
            extra_name=None,
            events=[
                dsl_nodes.EventDefinition(name="Stop", extra_name="Plant Stop"),
                dsl_nodes.EventDefinition(name="Reset", extra_name="Local Reset"),
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

    def test_state_plant_bus_list_on_enters(self, state_plant_bus):
        lst = state_plant_bus.list_on_enters()
        assert lst == []

        lst = state_plant_bus.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_bus.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_bus.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_bus.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_plant_bus.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant_bus.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_bus.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant_bus.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_bus_during_aspects(self, state_plant_bus):
        lst = state_plant_bus.list_on_during_aspects()
        assert lst == []

        lst = state_plant_bus.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_bus.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_bus.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_bus.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_plant_bus.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_plant_bus.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_bus.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_plant_bus.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_plant_bus_during_aspect_recursively(self, state_plant_bus):
        lst = state_plant_bus.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_plant_bus.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
state Plant {
    state Worker named 'Mapped Worker' {
        state Idle;
        state Failed;
        state Halted;
        [*] -> Idle;
        Idle -> Failed : /GlobalFault;
        Failed -> Halted : /Bus.Stop;
        Halted -> Idle : /Bus.Reset;
    }
    state Bus {
        event Stop named 'Plant Stop';
        event Reset named 'Local Reset';
    }
    event GlobalFault named 'Global Fault';
    [*] -> Worker;
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

state "Plant" as plant <<composite>> {
    state "Mapped Worker" as plant__worker <<composite>> {
        state "Idle" as plant__worker__idle
        state "Failed" as plant__worker__failed
        state "Halted" as plant__worker__halted
        [*] --> plant__worker__idle
        plant__worker__idle --> plant__worker__failed : Global Fault (/GlobalFault)
        plant__worker__failed --> plant__worker__halted : Plant Stop (/Bus.Stop)
        plant__worker__halted --> plant__worker__idle : Local Reset (/Bus.Reset)
    }
    state "Bus" as plant__bus
    [*] --> plant__worker
}
[*] --> plant
plant --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml(options="full")),
        )
