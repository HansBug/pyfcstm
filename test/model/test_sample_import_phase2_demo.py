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
state System {
    import "./modules/motor.fcstm" as LeftMotor named "Left Motor";
    [*] -> LeftMotor;
}
        """,
        )
        _write_text_file(
            "modules/motor.fcstm",
            """
state MotorRoot named "Motor Module" {
    enter abstract InitMotor;
    state Idle;
    state Running {
        state Spin;
        [*] -> Spin;
    }
    [*] -> Idle;
    Idle -> Running :: Start;
    Running -> Idle : /Reset;
}
        """,
        )
        entry_file = pathlib.Path("main.fcstm")
        ast_node = parse_state_machine_dsl(entry_file.read_text(encoding="utf-8"))
        model = parse_dsl_node_to_state_machine(ast_node, path=entry_file)
        return model


@pytest.fixture()
def state_system(model):
    return model.root_state


@pytest.fixture()
def state_system_leftmotor(state_system):
    return state_system.substates["LeftMotor"]


@pytest.fixture()
def state_system_leftmotor_idle(state_system_leftmotor):
    return state_system_leftmotor.substates["Idle"]


@pytest.fixture()
def state_system_leftmotor_running(state_system_leftmotor):
    return state_system_leftmotor.substates["Running"]


@pytest.fixture()
def state_system_leftmotor_running_spin(state_system_leftmotor_running):
    return state_system_leftmotor_running.substates["Spin"]


@pytest.mark.unittest
class TestModelStateSystem:
    def test_model(self, model):
        assert model.defines == {}
        assert model.root_state.name == "System"
        assert model.root_state.path == ("System",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == []
        assert ast_node.root_state.name == "System"

    def test_state_system(self, state_system):
        assert state_system.name == "System"
        assert state_system.path == ("System",)
        assert sorted(state_system.substates.keys()) == ["LeftMotor"]
        assert state_system.events == {}
        assert len(state_system.transitions) == 1
        assert state_system.transitions[0].from_state == INIT_STATE
        assert state_system.transitions[0].to_state == "LeftMotor"
        assert state_system.transitions[0].event is None
        assert state_system.transitions[0].guard is None
        assert state_system.transitions[0].effects == []
        assert state_system.transitions[0].parent_ref().name == "System"
        assert state_system.transitions[0].parent_ref().path == ("System",)
        assert state_system.named_functions == {}
        assert state_system.on_enters == []
        assert state_system.on_durings == []
        assert state_system.on_exits == []
        assert state_system.on_during_aspects == []
        assert state_system.parent_ref is None
        assert state_system.substate_name_to_id == {"LeftMotor": 0}
        assert state_system.extra_name is None
        assert not state_system.is_pseudo
        assert state_system.abstract_on_during_aspects == []
        assert state_system.abstract_on_durings == []
        assert state_system.abstract_on_enters == []
        assert state_system.abstract_on_exits == []
        assert len(state_system.init_transitions) == 1
        assert state_system.init_transitions[0].from_state == INIT_STATE
        assert state_system.init_transitions[0].to_state == "LeftMotor"
        assert state_system.init_transitions[0].event is None
        assert state_system.init_transitions[0].guard is None
        assert state_system.init_transitions[0].effects == []
        assert state_system.init_transitions[0].parent_ref().name == "System"
        assert state_system.init_transitions[0].parent_ref().path == ("System",)
        assert not state_system.is_leaf_state
        assert state_system.is_root_state
        assert not state_system.is_stoppable
        assert state_system.non_abstract_on_during_aspects == []
        assert state_system.non_abstract_on_durings == []
        assert state_system.non_abstract_on_enters == []
        assert state_system.non_abstract_on_exits == []
        assert state_system.parent is None
        assert len(state_system.transitions_entering_children) == 1
        assert state_system.transitions_entering_children[0].from_state == INIT_STATE
        assert state_system.transitions_entering_children[0].to_state == "LeftMotor"
        assert state_system.transitions_entering_children[0].event is None
        assert state_system.transitions_entering_children[0].guard is None
        assert state_system.transitions_entering_children[0].effects == []
        assert (
            state_system.transitions_entering_children[0].parent_ref().name == "System"
        )
        assert state_system.transitions_entering_children[0].parent_ref().path == (
            "System",
        )
        assert len(state_system.transitions_entering_children_simplified) == 1
        assert (
            state_system.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_system.transitions_entering_children_simplified[0].to_state
            == "LeftMotor"
        )
        assert state_system.transitions_entering_children_simplified[0].event is None
        assert state_system.transitions_entering_children_simplified[0].guard is None
        assert state_system.transitions_entering_children_simplified[0].effects == []
        assert (
            state_system.transitions_entering_children_simplified[0].parent_ref().name
            == "System"
        )
        assert state_system.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("System",)
        assert len(state_system.transitions_from) == 1
        assert state_system.transitions_from[0].from_state == "System"
        assert state_system.transitions_from[0].to_state == EXIT_STATE
        assert state_system.transitions_from[0].event is None
        assert state_system.transitions_from[0].guard is None
        assert state_system.transitions_from[0].effects == []
        assert state_system.transitions_from[0].parent_ref is None
        assert len(state_system.transitions_to) == 1
        assert state_system.transitions_to[0].from_state == INIT_STATE
        assert state_system.transitions_to[0].to_state == "System"
        assert state_system.transitions_to[0].event is None
        assert state_system.transitions_to[0].guard is None
        assert state_system.transitions_to[0].effects == []
        assert state_system.transitions_to[0].parent_ref is None

    def test_state_system_to_ast_node(self, state_system):
        ast_node = state_system.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="System",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="LeftMotor",
                    extra_name="Left Motor",
                    events=[dsl_nodes.EventDefinition(name="Reset", extra_name=None)],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Idle",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(name="Start", extra_name=None)
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
                        dsl_nodes.StateDefinition(
                            name="Running",
                            extra_name=None,
                            events=[],
                            imports=[],
                            substates=[
                                dsl_nodes.StateDefinition(
                                    name="Spin",
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
                            ],
                            transitions=[
                                dsl_nodes.TransitionDefinition(
                                    from_state=INIT_STATE,
                                    to_state="Spin",
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
                            to_state="Running",
                            event_id=dsl_nodes.ChainID(
                                path=["Idle", "Start"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Running",
                            to_state="Idle",
                            event_id=dsl_nodes.ChainID(
                                path=["Reset"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                    ],
                    enters=[
                        dsl_nodes.EnterAbstractFunction(name="InitMotor", doc=None)
                    ],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                )
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="LeftMotor",
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

    def test_state_system_list_on_enters(self, state_system):
        lst = state_system.list_on_enters()
        assert lst == []

        lst = state_system.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_system.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_system.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_system.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_system.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_system.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_system.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_system.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_system_during_aspects(self, state_system):
        lst = state_system.list_on_during_aspects()
        assert lst == []

        lst = state_system.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_system.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_system.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_system.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_system.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_system.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_system.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_system.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_system_leftmotor(self, state_system_leftmotor):
        assert state_system_leftmotor.name == "LeftMotor"
        assert state_system_leftmotor.path == ("System", "LeftMotor")
        assert sorted(state_system_leftmotor.substates.keys()) == ["Idle", "Running"]
        assert state_system_leftmotor.events == {
            "Reset": Event(
                name="Reset", state_path=("System", "LeftMotor"), extra_name=None
            )
        }
        assert len(state_system_leftmotor.transitions) == 3
        assert state_system_leftmotor.transitions[0].from_state == INIT_STATE
        assert state_system_leftmotor.transitions[0].to_state == "Idle"
        assert state_system_leftmotor.transitions[0].event is None
        assert state_system_leftmotor.transitions[0].guard is None
        assert state_system_leftmotor.transitions[0].effects == []
        assert state_system_leftmotor.transitions[0].parent_ref().name == "LeftMotor"
        assert state_system_leftmotor.transitions[0].parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert state_system_leftmotor.transitions[1].from_state == "Idle"
        assert state_system_leftmotor.transitions[1].to_state == "Running"
        assert state_system_leftmotor.transitions[1].event == Event(
            name="Start", state_path=("System", "LeftMotor", "Idle"), extra_name=None
        )
        assert state_system_leftmotor.transitions[1].guard is None
        assert state_system_leftmotor.transitions[1].effects == []
        assert state_system_leftmotor.transitions[1].parent_ref().name == "LeftMotor"
        assert state_system_leftmotor.transitions[1].parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert state_system_leftmotor.transitions[2].from_state == "Running"
        assert state_system_leftmotor.transitions[2].to_state == "Idle"
        assert state_system_leftmotor.transitions[2].event == Event(
            name="Reset", state_path=("System", "LeftMotor"), extra_name=None
        )
        assert state_system_leftmotor.transitions[2].guard is None
        assert state_system_leftmotor.transitions[2].effects == []
        assert state_system_leftmotor.transitions[2].parent_ref().name == "LeftMotor"
        assert state_system_leftmotor.transitions[2].parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert sorted(state_system_leftmotor.named_functions.keys()) == ["InitMotor"]
        assert state_system_leftmotor.named_functions["InitMotor"].stage == "enter"
        assert state_system_leftmotor.named_functions["InitMotor"].aspect is None
        assert state_system_leftmotor.named_functions["InitMotor"].name == "InitMotor"
        assert state_system_leftmotor.named_functions["InitMotor"].doc is None
        assert state_system_leftmotor.named_functions["InitMotor"].operations == []
        assert state_system_leftmotor.named_functions["InitMotor"].is_abstract
        assert state_system_leftmotor.named_functions["InitMotor"].state_path == (
            "System",
            "LeftMotor",
            "InitMotor",
        )
        assert state_system_leftmotor.named_functions["InitMotor"].ref is None
        assert (
            state_system_leftmotor.named_functions["InitMotor"].ref_state_path is None
        )
        assert (
            state_system_leftmotor.named_functions["InitMotor"].parent_ref().name
            == "LeftMotor"
        )
        assert state_system_leftmotor.named_functions[
            "InitMotor"
        ].parent_ref().path == ("System", "LeftMotor")
        assert (
            state_system_leftmotor.named_functions["InitMotor"].func_name
            == "System.LeftMotor.InitMotor"
        )
        assert not state_system_leftmotor.named_functions["InitMotor"].is_aspect
        assert not state_system_leftmotor.named_functions["InitMotor"].is_ref
        assert (
            state_system_leftmotor.named_functions["InitMotor"].parent.name
            == "LeftMotor"
        )
        assert state_system_leftmotor.named_functions["InitMotor"].parent.path == (
            "System",
            "LeftMotor",
        )
        assert len(state_system_leftmotor.on_enters) == 1
        assert state_system_leftmotor.on_enters[0].stage == "enter"
        assert state_system_leftmotor.on_enters[0].aspect is None
        assert state_system_leftmotor.on_enters[0].name == "InitMotor"
        assert state_system_leftmotor.on_enters[0].doc is None
        assert state_system_leftmotor.on_enters[0].operations == []
        assert state_system_leftmotor.on_enters[0].is_abstract
        assert state_system_leftmotor.on_enters[0].state_path == (
            "System",
            "LeftMotor",
            "InitMotor",
        )
        assert state_system_leftmotor.on_enters[0].ref is None
        assert state_system_leftmotor.on_enters[0].ref_state_path is None
        assert state_system_leftmotor.on_enters[0].parent_ref().name == "LeftMotor"
        assert state_system_leftmotor.on_enters[0].parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert (
            state_system_leftmotor.on_enters[0].func_name
            == "System.LeftMotor.InitMotor"
        )
        assert not state_system_leftmotor.on_enters[0].is_aspect
        assert not state_system_leftmotor.on_enters[0].is_ref
        assert state_system_leftmotor.on_enters[0].parent.name == "LeftMotor"
        assert state_system_leftmotor.on_enters[0].parent.path == (
            "System",
            "LeftMotor",
        )
        assert state_system_leftmotor.on_durings == []
        assert state_system_leftmotor.on_exits == []
        assert state_system_leftmotor.on_during_aspects == []
        assert state_system_leftmotor.parent_ref().name == "System"
        assert state_system_leftmotor.parent_ref().path == ("System",)
        assert state_system_leftmotor.substate_name_to_id == {"Idle": 0, "Running": 1}
        assert state_system_leftmotor.extra_name == "Left Motor"
        assert not state_system_leftmotor.is_pseudo
        assert state_system_leftmotor.abstract_on_during_aspects == []
        assert state_system_leftmotor.abstract_on_durings == []
        assert len(state_system_leftmotor.abstract_on_enters) == 1
        assert state_system_leftmotor.abstract_on_enters[0].stage == "enter"
        assert state_system_leftmotor.abstract_on_enters[0].aspect is None
        assert state_system_leftmotor.abstract_on_enters[0].name == "InitMotor"
        assert state_system_leftmotor.abstract_on_enters[0].doc is None
        assert state_system_leftmotor.abstract_on_enters[0].operations == []
        assert state_system_leftmotor.abstract_on_enters[0].is_abstract
        assert state_system_leftmotor.abstract_on_enters[0].state_path == (
            "System",
            "LeftMotor",
            "InitMotor",
        )
        assert state_system_leftmotor.abstract_on_enters[0].ref is None
        assert state_system_leftmotor.abstract_on_enters[0].ref_state_path is None
        assert (
            state_system_leftmotor.abstract_on_enters[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_system_leftmotor.abstract_on_enters[0].parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert (
            state_system_leftmotor.abstract_on_enters[0].func_name
            == "System.LeftMotor.InitMotor"
        )
        assert not state_system_leftmotor.abstract_on_enters[0].is_aspect
        assert not state_system_leftmotor.abstract_on_enters[0].is_ref
        assert state_system_leftmotor.abstract_on_enters[0].parent.name == "LeftMotor"
        assert state_system_leftmotor.abstract_on_enters[0].parent.path == (
            "System",
            "LeftMotor",
        )
        assert state_system_leftmotor.abstract_on_exits == []
        assert len(state_system_leftmotor.init_transitions) == 1
        assert state_system_leftmotor.init_transitions[0].from_state == INIT_STATE
        assert state_system_leftmotor.init_transitions[0].to_state == "Idle"
        assert state_system_leftmotor.init_transitions[0].event is None
        assert state_system_leftmotor.init_transitions[0].guard is None
        assert state_system_leftmotor.init_transitions[0].effects == []
        assert (
            state_system_leftmotor.init_transitions[0].parent_ref().name == "LeftMotor"
        )
        assert state_system_leftmotor.init_transitions[0].parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert not state_system_leftmotor.is_leaf_state
        assert not state_system_leftmotor.is_root_state
        assert not state_system_leftmotor.is_stoppable
        assert state_system_leftmotor.non_abstract_on_during_aspects == []
        assert state_system_leftmotor.non_abstract_on_durings == []
        assert state_system_leftmotor.non_abstract_on_enters == []
        assert state_system_leftmotor.non_abstract_on_exits == []
        assert state_system_leftmotor.parent.name == "System"
        assert state_system_leftmotor.parent.path == ("System",)
        assert len(state_system_leftmotor.transitions_entering_children) == 1
        assert (
            state_system_leftmotor.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert (
            state_system_leftmotor.transitions_entering_children[0].to_state == "Idle"
        )
        assert state_system_leftmotor.transitions_entering_children[0].event is None
        assert state_system_leftmotor.transitions_entering_children[0].guard is None
        assert state_system_leftmotor.transitions_entering_children[0].effects == []
        assert (
            state_system_leftmotor.transitions_entering_children[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_system_leftmotor.transitions_entering_children[
            0
        ].parent_ref().path == ("System", "LeftMotor")
        assert len(state_system_leftmotor.transitions_entering_children_simplified) == 1
        assert (
            state_system_leftmotor.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_system_leftmotor.transitions_entering_children_simplified[0].to_state
            == "Idle"
        )
        assert (
            state_system_leftmotor.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_system_leftmotor.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_system_leftmotor.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_system_leftmotor.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "LeftMotor"
        )
        assert state_system_leftmotor.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("System", "LeftMotor")
        assert state_system_leftmotor.transitions_from == []
        assert len(state_system_leftmotor.transitions_to) == 1
        assert state_system_leftmotor.transitions_to[0].from_state == INIT_STATE
        assert state_system_leftmotor.transitions_to[0].to_state == "LeftMotor"
        assert state_system_leftmotor.transitions_to[0].event is None
        assert state_system_leftmotor.transitions_to[0].guard is None
        assert state_system_leftmotor.transitions_to[0].effects == []
        assert state_system_leftmotor.transitions_to[0].parent_ref().name == "System"
        assert state_system_leftmotor.transitions_to[0].parent_ref().path == ("System",)

    def test_state_system_leftmotor_to_ast_node(self, state_system_leftmotor):
        ast_node = state_system_leftmotor.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="LeftMotor",
            extra_name="Left Motor",
            events=[dsl_nodes.EventDefinition(name="Reset", extra_name=None)],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Idle",
                    extra_name=None,
                    events=[dsl_nodes.EventDefinition(name="Start", extra_name=None)],
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
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Spin",
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
                    ],
                    transitions=[
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="Spin",
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
                    to_state="Running",
                    event_id=dsl_nodes.ChainID(
                        path=["Idle", "Start"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Running",
                    to_state="Idle",
                    event_id=dsl_nodes.ChainID(path=["Reset"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
            ],
            enters=[dsl_nodes.EnterAbstractFunction(name="InitMotor", doc=None)],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_system_leftmotor_list_on_enters(self, state_system_leftmotor):
        lst = state_system_leftmotor.list_on_enters()
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InitMotor"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("System", "LeftMotor", "InitMotor")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LeftMotor"
        assert on_stage.parent_ref().path == ("System", "LeftMotor")
        assert on_stage.func_name == "System.LeftMotor.InitMotor"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LeftMotor"
        assert on_stage.parent.path == ("System", "LeftMotor")

        lst = state_system_leftmotor.list_on_enters(with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InitMotor"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("System", "LeftMotor", "InitMotor")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LeftMotor"
        assert on_stage.parent_ref().path == ("System", "LeftMotor")
        assert on_stage.func_name == "System.LeftMotor.InitMotor"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LeftMotor"
        assert on_stage.parent.path == ("System", "LeftMotor")

        lst = state_system_leftmotor.list_on_enters(with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InitMotor"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("System", "LeftMotor", "InitMotor")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LeftMotor"
        assert on_stage.parent_ref().path == ("System", "LeftMotor")
        assert on_stage.func_name == "System.LeftMotor.InitMotor"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LeftMotor"
        assert on_stage.parent.path == ("System", "LeftMotor")

        lst = state_system_leftmotor.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_system_leftmotor.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_system_leftmotor.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_system_leftmotor.list_on_enters(is_abstract=True)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InitMotor"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("System", "LeftMotor", "InitMotor")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LeftMotor"
        assert on_stage.parent_ref().path == ("System", "LeftMotor")
        assert on_stage.func_name == "System.LeftMotor.InitMotor"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LeftMotor"
        assert on_stage.parent.path == ("System", "LeftMotor")

        lst = state_system_leftmotor.list_on_enters(is_abstract=True, with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InitMotor"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("System", "LeftMotor", "InitMotor")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LeftMotor"
        assert on_stage.parent_ref().path == ("System", "LeftMotor")
        assert on_stage.func_name == "System.LeftMotor.InitMotor"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LeftMotor"
        assert on_stage.parent.path == ("System", "LeftMotor")

        lst = state_system_leftmotor.list_on_enters(is_abstract=True, with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InitMotor"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("System", "LeftMotor", "InitMotor")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "LeftMotor"
        assert on_stage.parent_ref().path == ("System", "LeftMotor")
        assert on_stage.func_name == "System.LeftMotor.InitMotor"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "LeftMotor"
        assert on_stage.parent.path == ("System", "LeftMotor")

    def test_state_system_leftmotor_during_aspects(self, state_system_leftmotor):
        lst = state_system_leftmotor.list_on_during_aspects()
        assert lst == []

        lst = state_system_leftmotor.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_system_leftmotor.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_system_leftmotor.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_system_leftmotor.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_system_leftmotor.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_system_leftmotor.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_system_leftmotor.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_system_leftmotor.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_system_leftmotor_idle(self, state_system_leftmotor_idle):
        assert state_system_leftmotor_idle.name == "Idle"
        assert state_system_leftmotor_idle.path == ("System", "LeftMotor", "Idle")
        assert sorted(state_system_leftmotor_idle.substates.keys()) == []
        assert state_system_leftmotor_idle.events == {
            "Start": Event(
                name="Start",
                state_path=("System", "LeftMotor", "Idle"),
                extra_name=None,
            )
        }
        assert state_system_leftmotor_idle.transitions == []
        assert state_system_leftmotor_idle.named_functions == {}
        assert state_system_leftmotor_idle.on_enters == []
        assert state_system_leftmotor_idle.on_durings == []
        assert state_system_leftmotor_idle.on_exits == []
        assert state_system_leftmotor_idle.on_during_aspects == []
        assert state_system_leftmotor_idle.parent_ref().name == "LeftMotor"
        assert state_system_leftmotor_idle.parent_ref().path == ("System", "LeftMotor")
        assert state_system_leftmotor_idle.substate_name_to_id == {}
        assert state_system_leftmotor_idle.extra_name is None
        assert not state_system_leftmotor_idle.is_pseudo
        assert state_system_leftmotor_idle.abstract_on_during_aspects == []
        assert state_system_leftmotor_idle.abstract_on_durings == []
        assert state_system_leftmotor_idle.abstract_on_enters == []
        assert state_system_leftmotor_idle.abstract_on_exits == []
        assert state_system_leftmotor_idle.init_transitions == []
        assert state_system_leftmotor_idle.is_leaf_state
        assert not state_system_leftmotor_idle.is_root_state
        assert state_system_leftmotor_idle.is_stoppable
        assert state_system_leftmotor_idle.non_abstract_on_during_aspects == []
        assert state_system_leftmotor_idle.non_abstract_on_durings == []
        assert state_system_leftmotor_idle.non_abstract_on_enters == []
        assert state_system_leftmotor_idle.non_abstract_on_exits == []
        assert state_system_leftmotor_idle.parent.name == "LeftMotor"
        assert state_system_leftmotor_idle.parent.path == ("System", "LeftMotor")
        assert state_system_leftmotor_idle.transitions_entering_children == []
        assert (
            len(state_system_leftmotor_idle.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_system_leftmotor_idle.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_system_leftmotor_idle.transitions_from) == 1
        assert state_system_leftmotor_idle.transitions_from[0].from_state == "Idle"
        assert state_system_leftmotor_idle.transitions_from[0].to_state == "Running"
        assert state_system_leftmotor_idle.transitions_from[0].event == Event(
            name="Start", state_path=("System", "LeftMotor", "Idle"), extra_name=None
        )
        assert state_system_leftmotor_idle.transitions_from[0].guard is None
        assert state_system_leftmotor_idle.transitions_from[0].effects == []
        assert (
            state_system_leftmotor_idle.transitions_from[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_system_leftmotor_idle.transitions_from[0].parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert len(state_system_leftmotor_idle.transitions_to) == 2
        assert state_system_leftmotor_idle.transitions_to[0].from_state == INIT_STATE
        assert state_system_leftmotor_idle.transitions_to[0].to_state == "Idle"
        assert state_system_leftmotor_idle.transitions_to[0].event is None
        assert state_system_leftmotor_idle.transitions_to[0].guard is None
        assert state_system_leftmotor_idle.transitions_to[0].effects == []
        assert (
            state_system_leftmotor_idle.transitions_to[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_system_leftmotor_idle.transitions_to[0].parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert state_system_leftmotor_idle.transitions_to[1].from_state == "Running"
        assert state_system_leftmotor_idle.transitions_to[1].to_state == "Idle"
        assert state_system_leftmotor_idle.transitions_to[1].event == Event(
            name="Reset", state_path=("System", "LeftMotor"), extra_name=None
        )
        assert state_system_leftmotor_idle.transitions_to[1].guard is None
        assert state_system_leftmotor_idle.transitions_to[1].effects == []
        assert (
            state_system_leftmotor_idle.transitions_to[1].parent_ref().name
            == "LeftMotor"
        )
        assert state_system_leftmotor_idle.transitions_to[1].parent_ref().path == (
            "System",
            "LeftMotor",
        )

    def test_state_system_leftmotor_idle_to_ast_node(self, state_system_leftmotor_idle):
        ast_node = state_system_leftmotor_idle.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Idle",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="Start", extra_name=None)],
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

    def test_state_system_leftmotor_idle_list_on_enters(
        self, state_system_leftmotor_idle
    ):
        lst = state_system_leftmotor_idle.list_on_enters()
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_system_leftmotor_idle_during_aspects(
        self, state_system_leftmotor_idle
    ):
        lst = state_system_leftmotor_idle.list_on_during_aspects()
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_system_leftmotor_idle_during_aspect_recursively(
        self, state_system_leftmotor_idle
    ):
        lst = state_system_leftmotor_idle.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_system_leftmotor_idle.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_system_leftmotor_running(self, state_system_leftmotor_running):
        assert state_system_leftmotor_running.name == "Running"
        assert state_system_leftmotor_running.path == ("System", "LeftMotor", "Running")
        assert sorted(state_system_leftmotor_running.substates.keys()) == ["Spin"]
        assert state_system_leftmotor_running.events == {}
        assert len(state_system_leftmotor_running.transitions) == 1
        assert state_system_leftmotor_running.transitions[0].from_state == INIT_STATE
        assert state_system_leftmotor_running.transitions[0].to_state == "Spin"
        assert state_system_leftmotor_running.transitions[0].event is None
        assert state_system_leftmotor_running.transitions[0].guard is None
        assert state_system_leftmotor_running.transitions[0].effects == []
        assert (
            state_system_leftmotor_running.transitions[0].parent_ref().name == "Running"
        )
        assert state_system_leftmotor_running.transitions[0].parent_ref().path == (
            "System",
            "LeftMotor",
            "Running",
        )
        assert state_system_leftmotor_running.named_functions == {}
        assert state_system_leftmotor_running.on_enters == []
        assert state_system_leftmotor_running.on_durings == []
        assert state_system_leftmotor_running.on_exits == []
        assert state_system_leftmotor_running.on_during_aspects == []
        assert state_system_leftmotor_running.parent_ref().name == "LeftMotor"
        assert state_system_leftmotor_running.parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert state_system_leftmotor_running.substate_name_to_id == {"Spin": 0}
        assert state_system_leftmotor_running.extra_name is None
        assert not state_system_leftmotor_running.is_pseudo
        assert state_system_leftmotor_running.abstract_on_during_aspects == []
        assert state_system_leftmotor_running.abstract_on_durings == []
        assert state_system_leftmotor_running.abstract_on_enters == []
        assert state_system_leftmotor_running.abstract_on_exits == []
        assert len(state_system_leftmotor_running.init_transitions) == 1
        assert (
            state_system_leftmotor_running.init_transitions[0].from_state == INIT_STATE
        )
        assert state_system_leftmotor_running.init_transitions[0].to_state == "Spin"
        assert state_system_leftmotor_running.init_transitions[0].event is None
        assert state_system_leftmotor_running.init_transitions[0].guard is None
        assert state_system_leftmotor_running.init_transitions[0].effects == []
        assert (
            state_system_leftmotor_running.init_transitions[0].parent_ref().name
            == "Running"
        )
        assert state_system_leftmotor_running.init_transitions[0].parent_ref().path == (
            "System",
            "LeftMotor",
            "Running",
        )
        assert not state_system_leftmotor_running.is_leaf_state
        assert not state_system_leftmotor_running.is_root_state
        assert not state_system_leftmotor_running.is_stoppable
        assert state_system_leftmotor_running.non_abstract_on_during_aspects == []
        assert state_system_leftmotor_running.non_abstract_on_durings == []
        assert state_system_leftmotor_running.non_abstract_on_enters == []
        assert state_system_leftmotor_running.non_abstract_on_exits == []
        assert state_system_leftmotor_running.parent.name == "LeftMotor"
        assert state_system_leftmotor_running.parent.path == ("System", "LeftMotor")
        assert len(state_system_leftmotor_running.transitions_entering_children) == 1
        assert (
            state_system_leftmotor_running.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children[0].to_state
            == "Spin"
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children[0].event
            is None
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children[0].guard
            is None
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children[0].effects
            == []
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children[0]
            .parent_ref()
            .name
            == "Running"
        )
        assert state_system_leftmotor_running.transitions_entering_children[
            0
        ].parent_ref().path == ("System", "LeftMotor", "Running")
        assert (
            len(state_system_leftmotor_running.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children_simplified[
                0
            ].to_state
            == "Spin"
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children_simplified[
                0
            ].event
            is None
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children_simplified[
                0
            ].guard
            is None
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children_simplified[
                0
            ].effects
            == []
        )
        assert (
            state_system_leftmotor_running.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "Running"
        )
        assert state_system_leftmotor_running.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("System", "LeftMotor", "Running")
        assert len(state_system_leftmotor_running.transitions_from) == 1
        assert (
            state_system_leftmotor_running.transitions_from[0].from_state == "Running"
        )
        assert state_system_leftmotor_running.transitions_from[0].to_state == "Idle"
        assert state_system_leftmotor_running.transitions_from[0].event == Event(
            name="Reset", state_path=("System", "LeftMotor"), extra_name=None
        )
        assert state_system_leftmotor_running.transitions_from[0].guard is None
        assert state_system_leftmotor_running.transitions_from[0].effects == []
        assert (
            state_system_leftmotor_running.transitions_from[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_system_leftmotor_running.transitions_from[0].parent_ref().path == (
            "System",
            "LeftMotor",
        )
        assert len(state_system_leftmotor_running.transitions_to) == 1
        assert state_system_leftmotor_running.transitions_to[0].from_state == "Idle"
        assert state_system_leftmotor_running.transitions_to[0].to_state == "Running"
        assert state_system_leftmotor_running.transitions_to[0].event == Event(
            name="Start", state_path=("System", "LeftMotor", "Idle"), extra_name=None
        )
        assert state_system_leftmotor_running.transitions_to[0].guard is None
        assert state_system_leftmotor_running.transitions_to[0].effects == []
        assert (
            state_system_leftmotor_running.transitions_to[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_system_leftmotor_running.transitions_to[0].parent_ref().path == (
            "System",
            "LeftMotor",
        )

    def test_state_system_leftmotor_running_to_ast_node(
        self, state_system_leftmotor_running
    ):
        ast_node = state_system_leftmotor_running.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Running",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Spin",
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
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="Spin",
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

    def test_state_system_leftmotor_running_list_on_enters(
        self, state_system_leftmotor_running
    ):
        lst = state_system_leftmotor_running.list_on_enters()
        assert lst == []

        lst = state_system_leftmotor_running.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_system_leftmotor_running.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_system_leftmotor_running.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_system_leftmotor_running.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_system_leftmotor_running.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_system_leftmotor_running.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_system_leftmotor_running.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_system_leftmotor_running.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_system_leftmotor_running_during_aspects(
        self, state_system_leftmotor_running
    ):
        lst = state_system_leftmotor_running.list_on_during_aspects()
        assert lst == []

        lst = state_system_leftmotor_running.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_system_leftmotor_running.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_system_leftmotor_running.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_system_leftmotor_running.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_system_leftmotor_running.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_system_leftmotor_running.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_system_leftmotor_running.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_system_leftmotor_running.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_system_leftmotor_running_spin(
        self, state_system_leftmotor_running_spin
    ):
        assert state_system_leftmotor_running_spin.name == "Spin"
        assert state_system_leftmotor_running_spin.path == (
            "System",
            "LeftMotor",
            "Running",
            "Spin",
        )
        assert sorted(state_system_leftmotor_running_spin.substates.keys()) == []
        assert state_system_leftmotor_running_spin.events == {}
        assert state_system_leftmotor_running_spin.transitions == []
        assert state_system_leftmotor_running_spin.named_functions == {}
        assert state_system_leftmotor_running_spin.on_enters == []
        assert state_system_leftmotor_running_spin.on_durings == []
        assert state_system_leftmotor_running_spin.on_exits == []
        assert state_system_leftmotor_running_spin.on_during_aspects == []
        assert state_system_leftmotor_running_spin.parent_ref().name == "Running"
        assert state_system_leftmotor_running_spin.parent_ref().path == (
            "System",
            "LeftMotor",
            "Running",
        )
        assert state_system_leftmotor_running_spin.substate_name_to_id == {}
        assert state_system_leftmotor_running_spin.extra_name is None
        assert not state_system_leftmotor_running_spin.is_pseudo
        assert state_system_leftmotor_running_spin.abstract_on_during_aspects == []
        assert state_system_leftmotor_running_spin.abstract_on_durings == []
        assert state_system_leftmotor_running_spin.abstract_on_enters == []
        assert state_system_leftmotor_running_spin.abstract_on_exits == []
        assert state_system_leftmotor_running_spin.init_transitions == []
        assert state_system_leftmotor_running_spin.is_leaf_state
        assert not state_system_leftmotor_running_spin.is_root_state
        assert state_system_leftmotor_running_spin.is_stoppable
        assert state_system_leftmotor_running_spin.non_abstract_on_during_aspects == []
        assert state_system_leftmotor_running_spin.non_abstract_on_durings == []
        assert state_system_leftmotor_running_spin.non_abstract_on_enters == []
        assert state_system_leftmotor_running_spin.non_abstract_on_exits == []
        assert state_system_leftmotor_running_spin.parent.name == "Running"
        assert state_system_leftmotor_running_spin.parent.path == (
            "System",
            "LeftMotor",
            "Running",
        )
        assert state_system_leftmotor_running_spin.transitions_entering_children == []
        assert (
            len(
                state_system_leftmotor_running_spin.transitions_entering_children_simplified
            )
            == 1
        )
        assert (
            state_system_leftmotor_running_spin.transitions_entering_children_simplified[
                0
            ]
            is None
        )
        assert state_system_leftmotor_running_spin.transitions_from == []
        assert len(state_system_leftmotor_running_spin.transitions_to) == 1
        assert (
            state_system_leftmotor_running_spin.transitions_to[0].from_state
            == INIT_STATE
        )
        assert state_system_leftmotor_running_spin.transitions_to[0].to_state == "Spin"
        assert state_system_leftmotor_running_spin.transitions_to[0].event is None
        assert state_system_leftmotor_running_spin.transitions_to[0].guard is None
        assert state_system_leftmotor_running_spin.transitions_to[0].effects == []
        assert (
            state_system_leftmotor_running_spin.transitions_to[0].parent_ref().name
            == "Running"
        )
        assert state_system_leftmotor_running_spin.transitions_to[
            0
        ].parent_ref().path == ("System", "LeftMotor", "Running")

    def test_state_system_leftmotor_running_spin_to_ast_node(
        self, state_system_leftmotor_running_spin
    ):
        ast_node = state_system_leftmotor_running_spin.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Spin",
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

    def test_state_system_leftmotor_running_spin_list_on_enters(
        self, state_system_leftmotor_running_spin
    ):
        lst = state_system_leftmotor_running_spin.list_on_enters()
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_system_leftmotor_running_spin_during_aspects(
        self, state_system_leftmotor_running_spin
    ):
        lst = state_system_leftmotor_running_spin.list_on_during_aspects()
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_during_aspects(
            aspect="before"
        )
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_during_aspects(
            is_abstract=False
        )
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_during_aspects(
            is_abstract=True
        )
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_system_leftmotor_running_spin_during_aspect_recursively(
        self, state_system_leftmotor_running_spin
    ):
        lst = state_system_leftmotor_running_spin.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_system_leftmotor_running_spin.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
state System {
    state LeftMotor named 'Left Motor' {
        enter abstract InitMotor;
        state Idle {
            event Start;
        }
        state Running {
            state Spin;
            [*] -> Spin;
        }
        event Reset;
        [*] -> Idle;
        Idle -> Running :: Start;
        Running -> Idle : Reset;
    }
    [*] -> LeftMotor;
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

state "System" as system <<composite>> {
    state "Left Motor" as system__left_motor <<composite>> {
        state "Idle" as system__left_motor__idle
        state "Running" as system__left_motor__running <<composite>> {
            state "Spin" as system__left_motor__running__spin
            [*] --> system__left_motor__running__spin
        }
        [*] --> system__left_motor__idle
        system__left_motor__idle --> system__left_motor__running : Idle.Start
        system__left_motor__running --> system__left_motor__idle : Reset
    }
    system__left_motor : enter abstract InitMotor;
    [*] --> system__left_motor
}
[*] --> system
system --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml(options="full")),
        )
