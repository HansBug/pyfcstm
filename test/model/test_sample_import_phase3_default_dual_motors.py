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
state Fleet {
    import "./modules/motor.fcstm" as LeftMotor;
    import "./modules/motor.fcstm" as RightMotor;
    [*] -> LeftMotor;
    LeftMotor -> RightMotor;
}
        """,
        )
        _write_text_file(
            "modules/motor.fcstm",
            """
def int counter = 0;
def int limit = 3;

state MotorRoot {
    state Idle;
    state Running;
    [*] -> Idle;
    Idle -> Running : if [counter < limit] effect {
        counter = counter + 1;
    }
    Running -> Idle : if [counter >= limit] effect {
        counter = 0;
    }
}
        """,
        )
        entry_file = pathlib.Path("main.fcstm")
        ast_node = parse_state_machine_dsl(entry_file.read_text(encoding="utf-8"))
        model = parse_dsl_node_to_state_machine(ast_node, path=entry_file)
        return model


@pytest.fixture()
def state_fleet(model):
    return model.root_state


@pytest.fixture()
def state_fleet_leftmotor(state_fleet):
    return state_fleet.substates["LeftMotor"]


@pytest.fixture()
def state_fleet_leftmotor_idle(state_fleet_leftmotor):
    return state_fleet_leftmotor.substates["Idle"]


@pytest.fixture()
def state_fleet_leftmotor_running(state_fleet_leftmotor):
    return state_fleet_leftmotor.substates["Running"]


@pytest.fixture()
def state_fleet_rightmotor(state_fleet):
    return state_fleet.substates["RightMotor"]


@pytest.fixture()
def state_fleet_rightmotor_idle(state_fleet_rightmotor):
    return state_fleet_rightmotor.substates["Idle"]


@pytest.fixture()
def state_fleet_rightmotor_running(state_fleet_rightmotor):
    return state_fleet_rightmotor.substates["Running"]


@pytest.mark.unittest
class TestModelStateFleet:
    def test_model(self, model):
        assert model.defines == {
            "LeftMotor_counter": VarDefine(
                name="LeftMotor_counter", type="int", init=Integer(value=0)
            ),
            "LeftMotor_limit": VarDefine(
                name="LeftMotor_limit", type="int", init=Integer(value=3)
            ),
            "RightMotor_counter": VarDefine(
                name="RightMotor_counter", type="int", init=Integer(value=0)
            ),
            "RightMotor_limit": VarDefine(
                name="RightMotor_limit", type="int", init=Integer(value=3)
            ),
        }
        assert model.root_state.name == "Fleet"
        assert model.root_state.path == ("Fleet",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="LeftMotor_counter", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
            dsl_nodes.DefAssignment(
                name="LeftMotor_limit", type="int", expr=dsl_nodes.Integer(raw="3")
            ),
            dsl_nodes.DefAssignment(
                name="RightMotor_counter", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
            dsl_nodes.DefAssignment(
                name="RightMotor_limit", type="int", expr=dsl_nodes.Integer(raw="3")
            ),
        ]
        assert ast_node.root_state.name == "Fleet"

    def test_state_fleet(self, state_fleet):
        assert state_fleet.name == "Fleet"
        assert state_fleet.path == ("Fleet",)
        assert sorted(state_fleet.substates.keys()) == ["LeftMotor", "RightMotor"]
        assert state_fleet.events == {}
        assert len(state_fleet.transitions) == 2
        assert state_fleet.transitions[0].from_state == INIT_STATE
        assert state_fleet.transitions[0].to_state == "LeftMotor"
        assert state_fleet.transitions[0].event is None
        assert state_fleet.transitions[0].guard is None
        assert state_fleet.transitions[0].effects == []
        assert state_fleet.transitions[0].parent_ref().name == "Fleet"
        assert state_fleet.transitions[0].parent_ref().path == ("Fleet",)
        assert state_fleet.transitions[1].from_state == "LeftMotor"
        assert state_fleet.transitions[1].to_state == "RightMotor"
        assert state_fleet.transitions[1].event is None
        assert state_fleet.transitions[1].guard is None
        assert state_fleet.transitions[1].effects == []
        assert state_fleet.transitions[1].parent_ref().name == "Fleet"
        assert state_fleet.transitions[1].parent_ref().path == ("Fleet",)
        assert state_fleet.named_functions == {}
        assert state_fleet.on_enters == []
        assert state_fleet.on_durings == []
        assert state_fleet.on_exits == []
        assert state_fleet.on_during_aspects == []
        assert state_fleet.parent_ref is None
        assert state_fleet.substate_name_to_id == {"LeftMotor": 0, "RightMotor": 1}
        assert state_fleet.extra_name is None
        assert not state_fleet.is_pseudo
        assert state_fleet.abstract_on_during_aspects == []
        assert state_fleet.abstract_on_durings == []
        assert state_fleet.abstract_on_enters == []
        assert state_fleet.abstract_on_exits == []
        assert len(state_fleet.init_transitions) == 1
        assert state_fleet.init_transitions[0].from_state == INIT_STATE
        assert state_fleet.init_transitions[0].to_state == "LeftMotor"
        assert state_fleet.init_transitions[0].event is None
        assert state_fleet.init_transitions[0].guard is None
        assert state_fleet.init_transitions[0].effects == []
        assert state_fleet.init_transitions[0].parent_ref().name == "Fleet"
        assert state_fleet.init_transitions[0].parent_ref().path == ("Fleet",)
        assert not state_fleet.is_leaf_state
        assert state_fleet.is_root_state
        assert not state_fleet.is_stoppable
        assert state_fleet.non_abstract_on_during_aspects == []
        assert state_fleet.non_abstract_on_durings == []
        assert state_fleet.non_abstract_on_enters == []
        assert state_fleet.non_abstract_on_exits == []
        assert state_fleet.parent is None
        assert len(state_fleet.transitions_entering_children) == 1
        assert state_fleet.transitions_entering_children[0].from_state == INIT_STATE
        assert state_fleet.transitions_entering_children[0].to_state == "LeftMotor"
        assert state_fleet.transitions_entering_children[0].event is None
        assert state_fleet.transitions_entering_children[0].guard is None
        assert state_fleet.transitions_entering_children[0].effects == []
        assert state_fleet.transitions_entering_children[0].parent_ref().name == "Fleet"
        assert state_fleet.transitions_entering_children[0].parent_ref().path == (
            "Fleet",
        )
        assert len(state_fleet.transitions_entering_children_simplified) == 1
        assert (
            state_fleet.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_fleet.transitions_entering_children_simplified[0].to_state
            == "LeftMotor"
        )
        assert state_fleet.transitions_entering_children_simplified[0].event is None
        assert state_fleet.transitions_entering_children_simplified[0].guard is None
        assert state_fleet.transitions_entering_children_simplified[0].effects == []
        assert (
            state_fleet.transitions_entering_children_simplified[0].parent_ref().name
            == "Fleet"
        )
        assert state_fleet.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Fleet",)
        assert len(state_fleet.transitions_from) == 1
        assert state_fleet.transitions_from[0].from_state == "Fleet"
        assert state_fleet.transitions_from[0].to_state == EXIT_STATE
        assert state_fleet.transitions_from[0].event is None
        assert state_fleet.transitions_from[0].guard is None
        assert state_fleet.transitions_from[0].effects == []
        assert state_fleet.transitions_from[0].parent_ref is None
        assert len(state_fleet.transitions_to) == 1
        assert state_fleet.transitions_to[0].from_state == INIT_STATE
        assert state_fleet.transitions_to[0].to_state == "Fleet"
        assert state_fleet.transitions_to[0].event is None
        assert state_fleet.transitions_to[0].guard is None
        assert state_fleet.transitions_to[0].effects == []
        assert state_fleet.transitions_to[0].parent_ref is None

    def test_state_fleet_to_ast_node(self, state_fleet):
        ast_node = state_fleet.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Fleet",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="LeftMotor",
                    extra_name=None,
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
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="LeftMotor_counter"),
                                op="<",
                                expr2=dsl_nodes.Name(name="LeftMotor_limit"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="LeftMotor_counter",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="LeftMotor_counter"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                )
                            ],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Running",
                            to_state="Idle",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="LeftMotor_counter"),
                                op=">=",
                                expr2=dsl_nodes.Name(name="LeftMotor_limit"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="LeftMotor_counter",
                                    expr=dsl_nodes.Integer(raw="0"),
                                )
                            ],
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
                    name="RightMotor",
                    extra_name=None,
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
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="RightMotor_counter"),
                                op="<",
                                expr2=dsl_nodes.Name(name="RightMotor_limit"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="RightMotor_counter",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="RightMotor_counter"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                )
                            ],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Running",
                            to_state="Idle",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="RightMotor_counter"),
                                op=">=",
                                expr2=dsl_nodes.Name(name="RightMotor_limit"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="RightMotor_counter",
                                    expr=dsl_nodes.Integer(raw="0"),
                                )
                            ],
                        ),
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
                    to_state="LeftMotor",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="LeftMotor",
                    to_state="RightMotor",
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

    def test_state_fleet_list_on_enters(self, state_fleet):
        lst = state_fleet.list_on_enters()
        assert lst == []

        lst = state_fleet.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_fleet.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_fleet.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_fleet.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_fleet.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_fleet.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_fleet.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_fleet.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_fleet_during_aspects(self, state_fleet):
        lst = state_fleet.list_on_during_aspects()
        assert lst == []

        lst = state_fleet.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_fleet.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_fleet.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_fleet.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_fleet.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_fleet.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_fleet.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_fleet.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_fleet_leftmotor(self, state_fleet_leftmotor):
        assert state_fleet_leftmotor.name == "LeftMotor"
        assert state_fleet_leftmotor.path == ("Fleet", "LeftMotor")
        assert sorted(state_fleet_leftmotor.substates.keys()) == ["Idle", "Running"]
        assert state_fleet_leftmotor.events == {}
        assert len(state_fleet_leftmotor.transitions) == 3
        assert state_fleet_leftmotor.transitions[0].from_state == INIT_STATE
        assert state_fleet_leftmotor.transitions[0].to_state == "Idle"
        assert state_fleet_leftmotor.transitions[0].event is None
        assert state_fleet_leftmotor.transitions[0].guard is None
        assert state_fleet_leftmotor.transitions[0].effects == []
        assert state_fleet_leftmotor.transitions[0].parent_ref().name == "LeftMotor"
        assert state_fleet_leftmotor.transitions[0].parent_ref().path == (
            "Fleet",
            "LeftMotor",
        )
        assert state_fleet_leftmotor.transitions[1].from_state == "Idle"
        assert state_fleet_leftmotor.transitions[1].to_state == "Running"
        assert state_fleet_leftmotor.transitions[1].event is None
        assert state_fleet_leftmotor.transitions[1].guard == BinaryOp(
            x=Variable(name="LeftMotor_counter"),
            op="<",
            y=Variable(name="LeftMotor_limit"),
        )
        assert state_fleet_leftmotor.transitions[1].effects == [
            Operation(
                var_name="LeftMotor_counter",
                expr=BinaryOp(
                    x=Variable(name="LeftMotor_counter"), op="+", y=Integer(value=1)
                ),
            )
        ]
        assert state_fleet_leftmotor.transitions[1].parent_ref().name == "LeftMotor"
        assert state_fleet_leftmotor.transitions[1].parent_ref().path == (
            "Fleet",
            "LeftMotor",
        )
        assert state_fleet_leftmotor.transitions[2].from_state == "Running"
        assert state_fleet_leftmotor.transitions[2].to_state == "Idle"
        assert state_fleet_leftmotor.transitions[2].event is None
        assert state_fleet_leftmotor.transitions[2].guard == BinaryOp(
            x=Variable(name="LeftMotor_counter"),
            op=">=",
            y=Variable(name="LeftMotor_limit"),
        )
        assert state_fleet_leftmotor.transitions[2].effects == [
            Operation(var_name="LeftMotor_counter", expr=Integer(value=0))
        ]
        assert state_fleet_leftmotor.transitions[2].parent_ref().name == "LeftMotor"
        assert state_fleet_leftmotor.transitions[2].parent_ref().path == (
            "Fleet",
            "LeftMotor",
        )
        assert state_fleet_leftmotor.named_functions == {}
        assert state_fleet_leftmotor.on_enters == []
        assert state_fleet_leftmotor.on_durings == []
        assert state_fleet_leftmotor.on_exits == []
        assert state_fleet_leftmotor.on_during_aspects == []
        assert state_fleet_leftmotor.parent_ref().name == "Fleet"
        assert state_fleet_leftmotor.parent_ref().path == ("Fleet",)
        assert state_fleet_leftmotor.substate_name_to_id == {"Idle": 0, "Running": 1}
        assert state_fleet_leftmotor.extra_name is None
        assert not state_fleet_leftmotor.is_pseudo
        assert state_fleet_leftmotor.abstract_on_during_aspects == []
        assert state_fleet_leftmotor.abstract_on_durings == []
        assert state_fleet_leftmotor.abstract_on_enters == []
        assert state_fleet_leftmotor.abstract_on_exits == []
        assert len(state_fleet_leftmotor.init_transitions) == 1
        assert state_fleet_leftmotor.init_transitions[0].from_state == INIT_STATE
        assert state_fleet_leftmotor.init_transitions[0].to_state == "Idle"
        assert state_fleet_leftmotor.init_transitions[0].event is None
        assert state_fleet_leftmotor.init_transitions[0].guard is None
        assert state_fleet_leftmotor.init_transitions[0].effects == []
        assert (
            state_fleet_leftmotor.init_transitions[0].parent_ref().name == "LeftMotor"
        )
        assert state_fleet_leftmotor.init_transitions[0].parent_ref().path == (
            "Fleet",
            "LeftMotor",
        )
        assert not state_fleet_leftmotor.is_leaf_state
        assert not state_fleet_leftmotor.is_root_state
        assert not state_fleet_leftmotor.is_stoppable
        assert state_fleet_leftmotor.non_abstract_on_during_aspects == []
        assert state_fleet_leftmotor.non_abstract_on_durings == []
        assert state_fleet_leftmotor.non_abstract_on_enters == []
        assert state_fleet_leftmotor.non_abstract_on_exits == []
        assert state_fleet_leftmotor.parent.name == "Fleet"
        assert state_fleet_leftmotor.parent.path == ("Fleet",)
        assert len(state_fleet_leftmotor.transitions_entering_children) == 1
        assert (
            state_fleet_leftmotor.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert state_fleet_leftmotor.transitions_entering_children[0].to_state == "Idle"
        assert state_fleet_leftmotor.transitions_entering_children[0].event is None
        assert state_fleet_leftmotor.transitions_entering_children[0].guard is None
        assert state_fleet_leftmotor.transitions_entering_children[0].effects == []
        assert (
            state_fleet_leftmotor.transitions_entering_children[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_fleet_leftmotor.transitions_entering_children[
            0
        ].parent_ref().path == ("Fleet", "LeftMotor")
        assert len(state_fleet_leftmotor.transitions_entering_children_simplified) == 1
        assert (
            state_fleet_leftmotor.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_fleet_leftmotor.transitions_entering_children_simplified[0].to_state
            == "Idle"
        )
        assert (
            state_fleet_leftmotor.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_fleet_leftmotor.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_fleet_leftmotor.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_fleet_leftmotor.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "LeftMotor"
        )
        assert state_fleet_leftmotor.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Fleet", "LeftMotor")
        assert len(state_fleet_leftmotor.transitions_from) == 1
        assert state_fleet_leftmotor.transitions_from[0].from_state == "LeftMotor"
        assert state_fleet_leftmotor.transitions_from[0].to_state == "RightMotor"
        assert state_fleet_leftmotor.transitions_from[0].event is None
        assert state_fleet_leftmotor.transitions_from[0].guard is None
        assert state_fleet_leftmotor.transitions_from[0].effects == []
        assert state_fleet_leftmotor.transitions_from[0].parent_ref().name == "Fleet"
        assert state_fleet_leftmotor.transitions_from[0].parent_ref().path == ("Fleet",)
        assert len(state_fleet_leftmotor.transitions_to) == 1
        assert state_fleet_leftmotor.transitions_to[0].from_state == INIT_STATE
        assert state_fleet_leftmotor.transitions_to[0].to_state == "LeftMotor"
        assert state_fleet_leftmotor.transitions_to[0].event is None
        assert state_fleet_leftmotor.transitions_to[0].guard is None
        assert state_fleet_leftmotor.transitions_to[0].effects == []
        assert state_fleet_leftmotor.transitions_to[0].parent_ref().name == "Fleet"
        assert state_fleet_leftmotor.transitions_to[0].parent_ref().path == ("Fleet",)

    def test_state_fleet_leftmotor_to_ast_node(self, state_fleet_leftmotor):
        ast_node = state_fleet_leftmotor.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="LeftMotor",
            extra_name=None,
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
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="LeftMotor_counter"),
                        op="<",
                        expr2=dsl_nodes.Name(name="LeftMotor_limit"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="LeftMotor_counter",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="LeftMotor_counter"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        )
                    ],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Running",
                    to_state="Idle",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="LeftMotor_counter"),
                        op=">=",
                        expr2=dsl_nodes.Name(name="LeftMotor_limit"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="LeftMotor_counter", expr=dsl_nodes.Integer(raw="0")
                        )
                    ],
                ),
            ],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_fleet_leftmotor_list_on_enters(self, state_fleet_leftmotor):
        lst = state_fleet_leftmotor.list_on_enters()
        assert lst == []

        lst = state_fleet_leftmotor.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_fleet_leftmotor.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_fleet_leftmotor.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_fleet_leftmotor.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_fleet_leftmotor.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_fleet_leftmotor.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_fleet_leftmotor.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_fleet_leftmotor.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_fleet_leftmotor_during_aspects(self, state_fleet_leftmotor):
        lst = state_fleet_leftmotor.list_on_during_aspects()
        assert lst == []

        lst = state_fleet_leftmotor.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_fleet_leftmotor.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_fleet_leftmotor.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_fleet_leftmotor.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_fleet_leftmotor.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_fleet_leftmotor.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_fleet_leftmotor.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_fleet_leftmotor.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_fleet_leftmotor_idle(self, state_fleet_leftmotor_idle):
        assert state_fleet_leftmotor_idle.name == "Idle"
        assert state_fleet_leftmotor_idle.path == ("Fleet", "LeftMotor", "Idle")
        assert sorted(state_fleet_leftmotor_idle.substates.keys()) == []
        assert state_fleet_leftmotor_idle.events == {}
        assert state_fleet_leftmotor_idle.transitions == []
        assert state_fleet_leftmotor_idle.named_functions == {}
        assert state_fleet_leftmotor_idle.on_enters == []
        assert state_fleet_leftmotor_idle.on_durings == []
        assert state_fleet_leftmotor_idle.on_exits == []
        assert state_fleet_leftmotor_idle.on_during_aspects == []
        assert state_fleet_leftmotor_idle.parent_ref().name == "LeftMotor"
        assert state_fleet_leftmotor_idle.parent_ref().path == ("Fleet", "LeftMotor")
        assert state_fleet_leftmotor_idle.substate_name_to_id == {}
        assert state_fleet_leftmotor_idle.extra_name is None
        assert not state_fleet_leftmotor_idle.is_pseudo
        assert state_fleet_leftmotor_idle.abstract_on_during_aspects == []
        assert state_fleet_leftmotor_idle.abstract_on_durings == []
        assert state_fleet_leftmotor_idle.abstract_on_enters == []
        assert state_fleet_leftmotor_idle.abstract_on_exits == []
        assert state_fleet_leftmotor_idle.init_transitions == []
        assert state_fleet_leftmotor_idle.is_leaf_state
        assert not state_fleet_leftmotor_idle.is_root_state
        assert state_fleet_leftmotor_idle.is_stoppable
        assert state_fleet_leftmotor_idle.non_abstract_on_during_aspects == []
        assert state_fleet_leftmotor_idle.non_abstract_on_durings == []
        assert state_fleet_leftmotor_idle.non_abstract_on_enters == []
        assert state_fleet_leftmotor_idle.non_abstract_on_exits == []
        assert state_fleet_leftmotor_idle.parent.name == "LeftMotor"
        assert state_fleet_leftmotor_idle.parent.path == ("Fleet", "LeftMotor")
        assert state_fleet_leftmotor_idle.transitions_entering_children == []
        assert (
            len(state_fleet_leftmotor_idle.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_fleet_leftmotor_idle.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_fleet_leftmotor_idle.transitions_from) == 1
        assert state_fleet_leftmotor_idle.transitions_from[0].from_state == "Idle"
        assert state_fleet_leftmotor_idle.transitions_from[0].to_state == "Running"
        assert state_fleet_leftmotor_idle.transitions_from[0].event is None
        assert state_fleet_leftmotor_idle.transitions_from[0].guard == BinaryOp(
            x=Variable(name="LeftMotor_counter"),
            op="<",
            y=Variable(name="LeftMotor_limit"),
        )
        assert state_fleet_leftmotor_idle.transitions_from[0].effects == [
            Operation(
                var_name="LeftMotor_counter",
                expr=BinaryOp(
                    x=Variable(name="LeftMotor_counter"), op="+", y=Integer(value=1)
                ),
            )
        ]
        assert (
            state_fleet_leftmotor_idle.transitions_from[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_fleet_leftmotor_idle.transitions_from[0].parent_ref().path == (
            "Fleet",
            "LeftMotor",
        )
        assert len(state_fleet_leftmotor_idle.transitions_to) == 2
        assert state_fleet_leftmotor_idle.transitions_to[0].from_state == INIT_STATE
        assert state_fleet_leftmotor_idle.transitions_to[0].to_state == "Idle"
        assert state_fleet_leftmotor_idle.transitions_to[0].event is None
        assert state_fleet_leftmotor_idle.transitions_to[0].guard is None
        assert state_fleet_leftmotor_idle.transitions_to[0].effects == []
        assert (
            state_fleet_leftmotor_idle.transitions_to[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_fleet_leftmotor_idle.transitions_to[0].parent_ref().path == (
            "Fleet",
            "LeftMotor",
        )
        assert state_fleet_leftmotor_idle.transitions_to[1].from_state == "Running"
        assert state_fleet_leftmotor_idle.transitions_to[1].to_state == "Idle"
        assert state_fleet_leftmotor_idle.transitions_to[1].event is None
        assert state_fleet_leftmotor_idle.transitions_to[1].guard == BinaryOp(
            x=Variable(name="LeftMotor_counter"),
            op=">=",
            y=Variable(name="LeftMotor_limit"),
        )
        assert state_fleet_leftmotor_idle.transitions_to[1].effects == [
            Operation(var_name="LeftMotor_counter", expr=Integer(value=0))
        ]
        assert (
            state_fleet_leftmotor_idle.transitions_to[1].parent_ref().name
            == "LeftMotor"
        )
        assert state_fleet_leftmotor_idle.transitions_to[1].parent_ref().path == (
            "Fleet",
            "LeftMotor",
        )

    def test_state_fleet_leftmotor_idle_to_ast_node(self, state_fleet_leftmotor_idle):
        ast_node = state_fleet_leftmotor_idle.to_ast_node()
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

    def test_state_fleet_leftmotor_idle_list_on_enters(
        self, state_fleet_leftmotor_idle
    ):
        lst = state_fleet_leftmotor_idle.list_on_enters()
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_fleet_leftmotor_idle_during_aspects(
        self, state_fleet_leftmotor_idle
    ):
        lst = state_fleet_leftmotor_idle.list_on_during_aspects()
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_fleet_leftmotor_idle_during_aspect_recursively(
        self, state_fleet_leftmotor_idle
    ):
        lst = state_fleet_leftmotor_idle.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_fleet_leftmotor_idle.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_fleet_leftmotor_running(self, state_fleet_leftmotor_running):
        assert state_fleet_leftmotor_running.name == "Running"
        assert state_fleet_leftmotor_running.path == ("Fleet", "LeftMotor", "Running")
        assert sorted(state_fleet_leftmotor_running.substates.keys()) == []
        assert state_fleet_leftmotor_running.events == {}
        assert state_fleet_leftmotor_running.transitions == []
        assert state_fleet_leftmotor_running.named_functions == {}
        assert state_fleet_leftmotor_running.on_enters == []
        assert state_fleet_leftmotor_running.on_durings == []
        assert state_fleet_leftmotor_running.on_exits == []
        assert state_fleet_leftmotor_running.on_during_aspects == []
        assert state_fleet_leftmotor_running.parent_ref().name == "LeftMotor"
        assert state_fleet_leftmotor_running.parent_ref().path == ("Fleet", "LeftMotor")
        assert state_fleet_leftmotor_running.substate_name_to_id == {}
        assert state_fleet_leftmotor_running.extra_name is None
        assert not state_fleet_leftmotor_running.is_pseudo
        assert state_fleet_leftmotor_running.abstract_on_during_aspects == []
        assert state_fleet_leftmotor_running.abstract_on_durings == []
        assert state_fleet_leftmotor_running.abstract_on_enters == []
        assert state_fleet_leftmotor_running.abstract_on_exits == []
        assert state_fleet_leftmotor_running.init_transitions == []
        assert state_fleet_leftmotor_running.is_leaf_state
        assert not state_fleet_leftmotor_running.is_root_state
        assert state_fleet_leftmotor_running.is_stoppable
        assert state_fleet_leftmotor_running.non_abstract_on_during_aspects == []
        assert state_fleet_leftmotor_running.non_abstract_on_durings == []
        assert state_fleet_leftmotor_running.non_abstract_on_enters == []
        assert state_fleet_leftmotor_running.non_abstract_on_exits == []
        assert state_fleet_leftmotor_running.parent.name == "LeftMotor"
        assert state_fleet_leftmotor_running.parent.path == ("Fleet", "LeftMotor")
        assert state_fleet_leftmotor_running.transitions_entering_children == []
        assert (
            len(state_fleet_leftmotor_running.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_fleet_leftmotor_running.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_fleet_leftmotor_running.transitions_from) == 1
        assert state_fleet_leftmotor_running.transitions_from[0].from_state == "Running"
        assert state_fleet_leftmotor_running.transitions_from[0].to_state == "Idle"
        assert state_fleet_leftmotor_running.transitions_from[0].event is None
        assert state_fleet_leftmotor_running.transitions_from[0].guard == BinaryOp(
            x=Variable(name="LeftMotor_counter"),
            op=">=",
            y=Variable(name="LeftMotor_limit"),
        )
        assert state_fleet_leftmotor_running.transitions_from[0].effects == [
            Operation(var_name="LeftMotor_counter", expr=Integer(value=0))
        ]
        assert (
            state_fleet_leftmotor_running.transitions_from[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_fleet_leftmotor_running.transitions_from[0].parent_ref().path == (
            "Fleet",
            "LeftMotor",
        )
        assert len(state_fleet_leftmotor_running.transitions_to) == 1
        assert state_fleet_leftmotor_running.transitions_to[0].from_state == "Idle"
        assert state_fleet_leftmotor_running.transitions_to[0].to_state == "Running"
        assert state_fleet_leftmotor_running.transitions_to[0].event is None
        assert state_fleet_leftmotor_running.transitions_to[0].guard == BinaryOp(
            x=Variable(name="LeftMotor_counter"),
            op="<",
            y=Variable(name="LeftMotor_limit"),
        )
        assert state_fleet_leftmotor_running.transitions_to[0].effects == [
            Operation(
                var_name="LeftMotor_counter",
                expr=BinaryOp(
                    x=Variable(name="LeftMotor_counter"), op="+", y=Integer(value=1)
                ),
            )
        ]
        assert (
            state_fleet_leftmotor_running.transitions_to[0].parent_ref().name
            == "LeftMotor"
        )
        assert state_fleet_leftmotor_running.transitions_to[0].parent_ref().path == (
            "Fleet",
            "LeftMotor",
        )

    def test_state_fleet_leftmotor_running_to_ast_node(
        self, state_fleet_leftmotor_running
    ):
        ast_node = state_fleet_leftmotor_running.to_ast_node()
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

    def test_state_fleet_leftmotor_running_list_on_enters(
        self, state_fleet_leftmotor_running
    ):
        lst = state_fleet_leftmotor_running.list_on_enters()
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_fleet_leftmotor_running_during_aspects(
        self, state_fleet_leftmotor_running
    ):
        lst = state_fleet_leftmotor_running.list_on_during_aspects()
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_fleet_leftmotor_running_during_aspect_recursively(
        self, state_fleet_leftmotor_running
    ):
        lst = state_fleet_leftmotor_running.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_fleet_leftmotor_running.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_fleet_rightmotor(self, state_fleet_rightmotor):
        assert state_fleet_rightmotor.name == "RightMotor"
        assert state_fleet_rightmotor.path == ("Fleet", "RightMotor")
        assert sorted(state_fleet_rightmotor.substates.keys()) == ["Idle", "Running"]
        assert state_fleet_rightmotor.events == {}
        assert len(state_fleet_rightmotor.transitions) == 3
        assert state_fleet_rightmotor.transitions[0].from_state == INIT_STATE
        assert state_fleet_rightmotor.transitions[0].to_state == "Idle"
        assert state_fleet_rightmotor.transitions[0].event is None
        assert state_fleet_rightmotor.transitions[0].guard is None
        assert state_fleet_rightmotor.transitions[0].effects == []
        assert state_fleet_rightmotor.transitions[0].parent_ref().name == "RightMotor"
        assert state_fleet_rightmotor.transitions[0].parent_ref().path == (
            "Fleet",
            "RightMotor",
        )
        assert state_fleet_rightmotor.transitions[1].from_state == "Idle"
        assert state_fleet_rightmotor.transitions[1].to_state == "Running"
        assert state_fleet_rightmotor.transitions[1].event is None
        assert state_fleet_rightmotor.transitions[1].guard == BinaryOp(
            x=Variable(name="RightMotor_counter"),
            op="<",
            y=Variable(name="RightMotor_limit"),
        )
        assert state_fleet_rightmotor.transitions[1].effects == [
            Operation(
                var_name="RightMotor_counter",
                expr=BinaryOp(
                    x=Variable(name="RightMotor_counter"), op="+", y=Integer(value=1)
                ),
            )
        ]
        assert state_fleet_rightmotor.transitions[1].parent_ref().name == "RightMotor"
        assert state_fleet_rightmotor.transitions[1].parent_ref().path == (
            "Fleet",
            "RightMotor",
        )
        assert state_fleet_rightmotor.transitions[2].from_state == "Running"
        assert state_fleet_rightmotor.transitions[2].to_state == "Idle"
        assert state_fleet_rightmotor.transitions[2].event is None
        assert state_fleet_rightmotor.transitions[2].guard == BinaryOp(
            x=Variable(name="RightMotor_counter"),
            op=">=",
            y=Variable(name="RightMotor_limit"),
        )
        assert state_fleet_rightmotor.transitions[2].effects == [
            Operation(var_name="RightMotor_counter", expr=Integer(value=0))
        ]
        assert state_fleet_rightmotor.transitions[2].parent_ref().name == "RightMotor"
        assert state_fleet_rightmotor.transitions[2].parent_ref().path == (
            "Fleet",
            "RightMotor",
        )
        assert state_fleet_rightmotor.named_functions == {}
        assert state_fleet_rightmotor.on_enters == []
        assert state_fleet_rightmotor.on_durings == []
        assert state_fleet_rightmotor.on_exits == []
        assert state_fleet_rightmotor.on_during_aspects == []
        assert state_fleet_rightmotor.parent_ref().name == "Fleet"
        assert state_fleet_rightmotor.parent_ref().path == ("Fleet",)
        assert state_fleet_rightmotor.substate_name_to_id == {"Idle": 0, "Running": 1}
        assert state_fleet_rightmotor.extra_name is None
        assert not state_fleet_rightmotor.is_pseudo
        assert state_fleet_rightmotor.abstract_on_during_aspects == []
        assert state_fleet_rightmotor.abstract_on_durings == []
        assert state_fleet_rightmotor.abstract_on_enters == []
        assert state_fleet_rightmotor.abstract_on_exits == []
        assert len(state_fleet_rightmotor.init_transitions) == 1
        assert state_fleet_rightmotor.init_transitions[0].from_state == INIT_STATE
        assert state_fleet_rightmotor.init_transitions[0].to_state == "Idle"
        assert state_fleet_rightmotor.init_transitions[0].event is None
        assert state_fleet_rightmotor.init_transitions[0].guard is None
        assert state_fleet_rightmotor.init_transitions[0].effects == []
        assert (
            state_fleet_rightmotor.init_transitions[0].parent_ref().name == "RightMotor"
        )
        assert state_fleet_rightmotor.init_transitions[0].parent_ref().path == (
            "Fleet",
            "RightMotor",
        )
        assert not state_fleet_rightmotor.is_leaf_state
        assert not state_fleet_rightmotor.is_root_state
        assert not state_fleet_rightmotor.is_stoppable
        assert state_fleet_rightmotor.non_abstract_on_during_aspects == []
        assert state_fleet_rightmotor.non_abstract_on_durings == []
        assert state_fleet_rightmotor.non_abstract_on_enters == []
        assert state_fleet_rightmotor.non_abstract_on_exits == []
        assert state_fleet_rightmotor.parent.name == "Fleet"
        assert state_fleet_rightmotor.parent.path == ("Fleet",)
        assert len(state_fleet_rightmotor.transitions_entering_children) == 1
        assert (
            state_fleet_rightmotor.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert (
            state_fleet_rightmotor.transitions_entering_children[0].to_state == "Idle"
        )
        assert state_fleet_rightmotor.transitions_entering_children[0].event is None
        assert state_fleet_rightmotor.transitions_entering_children[0].guard is None
        assert state_fleet_rightmotor.transitions_entering_children[0].effects == []
        assert (
            state_fleet_rightmotor.transitions_entering_children[0].parent_ref().name
            == "RightMotor"
        )
        assert state_fleet_rightmotor.transitions_entering_children[
            0
        ].parent_ref().path == ("Fleet", "RightMotor")
        assert len(state_fleet_rightmotor.transitions_entering_children_simplified) == 1
        assert (
            state_fleet_rightmotor.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_fleet_rightmotor.transitions_entering_children_simplified[0].to_state
            == "Idle"
        )
        assert (
            state_fleet_rightmotor.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_fleet_rightmotor.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_fleet_rightmotor.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_fleet_rightmotor.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "RightMotor"
        )
        assert state_fleet_rightmotor.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Fleet", "RightMotor")
        assert state_fleet_rightmotor.transitions_from == []
        assert len(state_fleet_rightmotor.transitions_to) == 1
        assert state_fleet_rightmotor.transitions_to[0].from_state == "LeftMotor"
        assert state_fleet_rightmotor.transitions_to[0].to_state == "RightMotor"
        assert state_fleet_rightmotor.transitions_to[0].event is None
        assert state_fleet_rightmotor.transitions_to[0].guard is None
        assert state_fleet_rightmotor.transitions_to[0].effects == []
        assert state_fleet_rightmotor.transitions_to[0].parent_ref().name == "Fleet"
        assert state_fleet_rightmotor.transitions_to[0].parent_ref().path == ("Fleet",)

    def test_state_fleet_rightmotor_to_ast_node(self, state_fleet_rightmotor):
        ast_node = state_fleet_rightmotor.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="RightMotor",
            extra_name=None,
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
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="RightMotor_counter"),
                        op="<",
                        expr2=dsl_nodes.Name(name="RightMotor_limit"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="RightMotor_counter",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="RightMotor_counter"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        )
                    ],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Running",
                    to_state="Idle",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="RightMotor_counter"),
                        op=">=",
                        expr2=dsl_nodes.Name(name="RightMotor_limit"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="RightMotor_counter", expr=dsl_nodes.Integer(raw="0")
                        )
                    ],
                ),
            ],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_fleet_rightmotor_list_on_enters(self, state_fleet_rightmotor):
        lst = state_fleet_rightmotor.list_on_enters()
        assert lst == []

        lst = state_fleet_rightmotor.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_fleet_rightmotor.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_fleet_rightmotor.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_fleet_rightmotor.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_fleet_rightmotor.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_fleet_rightmotor.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_fleet_rightmotor.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_fleet_rightmotor.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_fleet_rightmotor_during_aspects(self, state_fleet_rightmotor):
        lst = state_fleet_rightmotor.list_on_during_aspects()
        assert lst == []

        lst = state_fleet_rightmotor.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_fleet_rightmotor.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_fleet_rightmotor.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_fleet_rightmotor.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_fleet_rightmotor.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_fleet_rightmotor.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_fleet_rightmotor.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_fleet_rightmotor.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_fleet_rightmotor_idle(self, state_fleet_rightmotor_idle):
        assert state_fleet_rightmotor_idle.name == "Idle"
        assert state_fleet_rightmotor_idle.path == ("Fleet", "RightMotor", "Idle")
        assert sorted(state_fleet_rightmotor_idle.substates.keys()) == []
        assert state_fleet_rightmotor_idle.events == {}
        assert state_fleet_rightmotor_idle.transitions == []
        assert state_fleet_rightmotor_idle.named_functions == {}
        assert state_fleet_rightmotor_idle.on_enters == []
        assert state_fleet_rightmotor_idle.on_durings == []
        assert state_fleet_rightmotor_idle.on_exits == []
        assert state_fleet_rightmotor_idle.on_during_aspects == []
        assert state_fleet_rightmotor_idle.parent_ref().name == "RightMotor"
        assert state_fleet_rightmotor_idle.parent_ref().path == ("Fleet", "RightMotor")
        assert state_fleet_rightmotor_idle.substate_name_to_id == {}
        assert state_fleet_rightmotor_idle.extra_name is None
        assert not state_fleet_rightmotor_idle.is_pseudo
        assert state_fleet_rightmotor_idle.abstract_on_during_aspects == []
        assert state_fleet_rightmotor_idle.abstract_on_durings == []
        assert state_fleet_rightmotor_idle.abstract_on_enters == []
        assert state_fleet_rightmotor_idle.abstract_on_exits == []
        assert state_fleet_rightmotor_idle.init_transitions == []
        assert state_fleet_rightmotor_idle.is_leaf_state
        assert not state_fleet_rightmotor_idle.is_root_state
        assert state_fleet_rightmotor_idle.is_stoppable
        assert state_fleet_rightmotor_idle.non_abstract_on_during_aspects == []
        assert state_fleet_rightmotor_idle.non_abstract_on_durings == []
        assert state_fleet_rightmotor_idle.non_abstract_on_enters == []
        assert state_fleet_rightmotor_idle.non_abstract_on_exits == []
        assert state_fleet_rightmotor_idle.parent.name == "RightMotor"
        assert state_fleet_rightmotor_idle.parent.path == ("Fleet", "RightMotor")
        assert state_fleet_rightmotor_idle.transitions_entering_children == []
        assert (
            len(state_fleet_rightmotor_idle.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_fleet_rightmotor_idle.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_fleet_rightmotor_idle.transitions_from) == 1
        assert state_fleet_rightmotor_idle.transitions_from[0].from_state == "Idle"
        assert state_fleet_rightmotor_idle.transitions_from[0].to_state == "Running"
        assert state_fleet_rightmotor_idle.transitions_from[0].event is None
        assert state_fleet_rightmotor_idle.transitions_from[0].guard == BinaryOp(
            x=Variable(name="RightMotor_counter"),
            op="<",
            y=Variable(name="RightMotor_limit"),
        )
        assert state_fleet_rightmotor_idle.transitions_from[0].effects == [
            Operation(
                var_name="RightMotor_counter",
                expr=BinaryOp(
                    x=Variable(name="RightMotor_counter"), op="+", y=Integer(value=1)
                ),
            )
        ]
        assert (
            state_fleet_rightmotor_idle.transitions_from[0].parent_ref().name
            == "RightMotor"
        )
        assert state_fleet_rightmotor_idle.transitions_from[0].parent_ref().path == (
            "Fleet",
            "RightMotor",
        )
        assert len(state_fleet_rightmotor_idle.transitions_to) == 2
        assert state_fleet_rightmotor_idle.transitions_to[0].from_state == INIT_STATE
        assert state_fleet_rightmotor_idle.transitions_to[0].to_state == "Idle"
        assert state_fleet_rightmotor_idle.transitions_to[0].event is None
        assert state_fleet_rightmotor_idle.transitions_to[0].guard is None
        assert state_fleet_rightmotor_idle.transitions_to[0].effects == []
        assert (
            state_fleet_rightmotor_idle.transitions_to[0].parent_ref().name
            == "RightMotor"
        )
        assert state_fleet_rightmotor_idle.transitions_to[0].parent_ref().path == (
            "Fleet",
            "RightMotor",
        )
        assert state_fleet_rightmotor_idle.transitions_to[1].from_state == "Running"
        assert state_fleet_rightmotor_idle.transitions_to[1].to_state == "Idle"
        assert state_fleet_rightmotor_idle.transitions_to[1].event is None
        assert state_fleet_rightmotor_idle.transitions_to[1].guard == BinaryOp(
            x=Variable(name="RightMotor_counter"),
            op=">=",
            y=Variable(name="RightMotor_limit"),
        )
        assert state_fleet_rightmotor_idle.transitions_to[1].effects == [
            Operation(var_name="RightMotor_counter", expr=Integer(value=0))
        ]
        assert (
            state_fleet_rightmotor_idle.transitions_to[1].parent_ref().name
            == "RightMotor"
        )
        assert state_fleet_rightmotor_idle.transitions_to[1].parent_ref().path == (
            "Fleet",
            "RightMotor",
        )

    def test_state_fleet_rightmotor_idle_to_ast_node(self, state_fleet_rightmotor_idle):
        ast_node = state_fleet_rightmotor_idle.to_ast_node()
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

    def test_state_fleet_rightmotor_idle_list_on_enters(
        self, state_fleet_rightmotor_idle
    ):
        lst = state_fleet_rightmotor_idle.list_on_enters()
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_fleet_rightmotor_idle_during_aspects(
        self, state_fleet_rightmotor_idle
    ):
        lst = state_fleet_rightmotor_idle.list_on_during_aspects()
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_fleet_rightmotor_idle_during_aspect_recursively(
        self, state_fleet_rightmotor_idle
    ):
        lst = state_fleet_rightmotor_idle.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_fleet_rightmotor_idle.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_fleet_rightmotor_running(self, state_fleet_rightmotor_running):
        assert state_fleet_rightmotor_running.name == "Running"
        assert state_fleet_rightmotor_running.path == ("Fleet", "RightMotor", "Running")
        assert sorted(state_fleet_rightmotor_running.substates.keys()) == []
        assert state_fleet_rightmotor_running.events == {}
        assert state_fleet_rightmotor_running.transitions == []
        assert state_fleet_rightmotor_running.named_functions == {}
        assert state_fleet_rightmotor_running.on_enters == []
        assert state_fleet_rightmotor_running.on_durings == []
        assert state_fleet_rightmotor_running.on_exits == []
        assert state_fleet_rightmotor_running.on_during_aspects == []
        assert state_fleet_rightmotor_running.parent_ref().name == "RightMotor"
        assert state_fleet_rightmotor_running.parent_ref().path == (
            "Fleet",
            "RightMotor",
        )
        assert state_fleet_rightmotor_running.substate_name_to_id == {}
        assert state_fleet_rightmotor_running.extra_name is None
        assert not state_fleet_rightmotor_running.is_pseudo
        assert state_fleet_rightmotor_running.abstract_on_during_aspects == []
        assert state_fleet_rightmotor_running.abstract_on_durings == []
        assert state_fleet_rightmotor_running.abstract_on_enters == []
        assert state_fleet_rightmotor_running.abstract_on_exits == []
        assert state_fleet_rightmotor_running.init_transitions == []
        assert state_fleet_rightmotor_running.is_leaf_state
        assert not state_fleet_rightmotor_running.is_root_state
        assert state_fleet_rightmotor_running.is_stoppable
        assert state_fleet_rightmotor_running.non_abstract_on_during_aspects == []
        assert state_fleet_rightmotor_running.non_abstract_on_durings == []
        assert state_fleet_rightmotor_running.non_abstract_on_enters == []
        assert state_fleet_rightmotor_running.non_abstract_on_exits == []
        assert state_fleet_rightmotor_running.parent.name == "RightMotor"
        assert state_fleet_rightmotor_running.parent.path == ("Fleet", "RightMotor")
        assert state_fleet_rightmotor_running.transitions_entering_children == []
        assert (
            len(state_fleet_rightmotor_running.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_fleet_rightmotor_running.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_fleet_rightmotor_running.transitions_from) == 1
        assert (
            state_fleet_rightmotor_running.transitions_from[0].from_state == "Running"
        )
        assert state_fleet_rightmotor_running.transitions_from[0].to_state == "Idle"
        assert state_fleet_rightmotor_running.transitions_from[0].event is None
        assert state_fleet_rightmotor_running.transitions_from[0].guard == BinaryOp(
            x=Variable(name="RightMotor_counter"),
            op=">=",
            y=Variable(name="RightMotor_limit"),
        )
        assert state_fleet_rightmotor_running.transitions_from[0].effects == [
            Operation(var_name="RightMotor_counter", expr=Integer(value=0))
        ]
        assert (
            state_fleet_rightmotor_running.transitions_from[0].parent_ref().name
            == "RightMotor"
        )
        assert state_fleet_rightmotor_running.transitions_from[0].parent_ref().path == (
            "Fleet",
            "RightMotor",
        )
        assert len(state_fleet_rightmotor_running.transitions_to) == 1
        assert state_fleet_rightmotor_running.transitions_to[0].from_state == "Idle"
        assert state_fleet_rightmotor_running.transitions_to[0].to_state == "Running"
        assert state_fleet_rightmotor_running.transitions_to[0].event is None
        assert state_fleet_rightmotor_running.transitions_to[0].guard == BinaryOp(
            x=Variable(name="RightMotor_counter"),
            op="<",
            y=Variable(name="RightMotor_limit"),
        )
        assert state_fleet_rightmotor_running.transitions_to[0].effects == [
            Operation(
                var_name="RightMotor_counter",
                expr=BinaryOp(
                    x=Variable(name="RightMotor_counter"), op="+", y=Integer(value=1)
                ),
            )
        ]
        assert (
            state_fleet_rightmotor_running.transitions_to[0].parent_ref().name
            == "RightMotor"
        )
        assert state_fleet_rightmotor_running.transitions_to[0].parent_ref().path == (
            "Fleet",
            "RightMotor",
        )

    def test_state_fleet_rightmotor_running_to_ast_node(
        self, state_fleet_rightmotor_running
    ):
        ast_node = state_fleet_rightmotor_running.to_ast_node()
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

    def test_state_fleet_rightmotor_running_list_on_enters(
        self, state_fleet_rightmotor_running
    ):
        lst = state_fleet_rightmotor_running.list_on_enters()
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_fleet_rightmotor_running_during_aspects(
        self, state_fleet_rightmotor_running
    ):
        lst = state_fleet_rightmotor_running.list_on_during_aspects()
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_fleet_rightmotor_running_during_aspect_recursively(
        self, state_fleet_rightmotor_running
    ):
        lst = state_fleet_rightmotor_running.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_fleet_rightmotor_running.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int LeftMotor_counter = 0;
def int LeftMotor_limit = 3;
def int RightMotor_counter = 0;
def int RightMotor_limit = 3;
state Fleet {
    state LeftMotor {
        state Idle;
        state Running;
        [*] -> Idle;
        Idle -> Running : if [LeftMotor_counter < LeftMotor_limit] effect {
            LeftMotor_counter = LeftMotor_counter + 1;
        }
        Running -> Idle : if [LeftMotor_counter >= LeftMotor_limit] effect {
            LeftMotor_counter = 0;
        }
    }
    state RightMotor {
        state Idle;
        state Running;
        [*] -> Idle;
        Idle -> Running : if [RightMotor_counter < RightMotor_limit] effect {
            RightMotor_counter = RightMotor_counter + 1;
        }
        Running -> Idle : if [RightMotor_counter >= RightMotor_limit] effect {
            RightMotor_counter = 0;
        }
    }
    [*] -> LeftMotor;
    LeftMotor -> RightMotor;
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
| LeftMotor_counter | int | 0 |
| LeftMotor_limit | int | 3 |
| RightMotor_counter | int | 0 |
| RightMotor_limit | int | 3 |
endlegend

state "Fleet" as fleet <<composite>> {
    state "LeftMotor" as fleet__left_motor <<composite>> {
        state "Idle" as fleet__left_motor__idle
        state "Running" as fleet__left_motor__running
        [*] --> fleet__left_motor__idle
        fleet__left_motor__idle --> fleet__left_motor__running : LeftMotor_counter < LeftMotor_limit
        note on link
        effect {
            LeftMotor_counter = LeftMotor_counter + 1;
        }
        end note
        fleet__left_motor__running --> fleet__left_motor__idle : LeftMotor_counter >= LeftMotor_limit
        note on link
        effect {
            LeftMotor_counter = 0;
        }
        end note
    }
    state "RightMotor" as fleet__right_motor <<composite>> {
        state "Idle" as fleet__right_motor__idle
        state "Running" as fleet__right_motor__running
        [*] --> fleet__right_motor__idle
        fleet__right_motor__idle --> fleet__right_motor__running : RightMotor_counter < RightMotor_limit
        note on link
        effect {
            RightMotor_counter = RightMotor_counter + 1;
        }
        end note
        fleet__right_motor__running --> fleet__right_motor__idle : RightMotor_counter >= RightMotor_limit
        note on link
        effect {
            RightMotor_counter = 0;
        }
        end note
    }
    [*] --> fleet__left_motor
    fleet__left_motor --> fleet__right_motor
}
[*] --> fleet
fleet --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml(options="full")),
        )
