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
def int host_ticks = 0;
def int host_load = 0;

state Factory {
    import "./modules/line.fcstm" as Line named "Assembly Line" {
        def line_ticks -> host_ticks;
        def load -> host_load;
    }
    [*] -> Line;
}
        """,
        )
        _write_text_file(
            "modules/line.fcstm",
            """
def int line_ticks = 0;
def int load = 0;

state LineRoot {
    import "./subsystems/conveyor.fcstm" as Conveyor {
        def speed -> line_ticks;
        def load -> load;
    }
    import "./subsystems/robot.fcstm" as Robot {
        def cycle_count -> line_ticks;
        def arm_load -> load;
    }
    [*] -> Conveyor;
    Conveyor -> Robot : if [line_ticks >= 2];
    Robot -> Conveyor : if [load >= 4];
}
        """,
        )
        _write_text_file(
            "modules/subsystems/conveyor.fcstm",
            """
def int speed = 0;
def int load = 0;

state ConveyorRoot {
    state Feeding;
    [*] -> Feeding;
    Feeding -> Feeding : if [speed < 2] effect {
        speed = speed + 1;
        load = load + 1;
    }
}
        """,
        )
        _write_text_file(
            "modules/subsystems/robot.fcstm",
            """
def int cycle_count = 0;
def int arm_load = 0;

state RobotRoot {
    state Picking;
    [*] -> Picking;
    Picking -> Picking : if [arm_load < 4] effect {
        cycle_count = cycle_count + 1;
        arm_load = arm_load + 1;
    }
}
        """,
        )
        entry_file = pathlib.Path("main.fcstm")
        ast_node = parse_state_machine_dsl(entry_file.read_text(encoding="utf-8"))
        model = parse_dsl_node_to_state_machine(ast_node, path=entry_file)
        return model


@pytest.fixture()
def state_factory(model):
    return model.root_state


@pytest.fixture()
def state_factory_line(state_factory):
    return state_factory.substates["Line"]


@pytest.fixture()
def state_factory_line_conveyor(state_factory_line):
    return state_factory_line.substates["Conveyor"]


@pytest.fixture()
def state_factory_line_conveyor_feeding(state_factory_line_conveyor):
    return state_factory_line_conveyor.substates["Feeding"]


@pytest.fixture()
def state_factory_line_robot(state_factory_line):
    return state_factory_line.substates["Robot"]


@pytest.fixture()
def state_factory_line_robot_picking(state_factory_line_robot):
    return state_factory_line_robot.substates["Picking"]


@pytest.mark.unittest
class TestModelStateFactory:
    def test_model(self, model):
        assert model.defines == {
            "host_ticks": VarDefine(
                name="host_ticks", type="int", init=Integer(value=0)
            ),
            "host_load": VarDefine(name="host_load", type="int", init=Integer(value=0)),
        }
        assert model.root_state.name == "Factory"
        assert model.root_state.path == ("Factory",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="host_ticks", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
            dsl_nodes.DefAssignment(
                name="host_load", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
        ]
        assert ast_node.root_state.name == "Factory"

    def test_state_factory(self, state_factory):
        assert state_factory.name == "Factory"
        assert state_factory.path == ("Factory",)
        assert sorted(state_factory.substates.keys()) == ["Line"]
        assert state_factory.events == {}
        assert len(state_factory.transitions) == 1
        assert state_factory.transitions[0].from_state == INIT_STATE
        assert state_factory.transitions[0].to_state == "Line"
        assert state_factory.transitions[0].event is None
        assert state_factory.transitions[0].guard is None
        assert state_factory.transitions[0].effects == []
        assert state_factory.transitions[0].parent_ref().name == "Factory"
        assert state_factory.transitions[0].parent_ref().path == ("Factory",)
        assert state_factory.named_functions == {}
        assert state_factory.on_enters == []
        assert state_factory.on_durings == []
        assert state_factory.on_exits == []
        assert state_factory.on_during_aspects == []
        assert state_factory.parent_ref is None
        assert state_factory.substate_name_to_id == {"Line": 0}
        assert state_factory.extra_name is None
        assert not state_factory.is_pseudo
        assert state_factory.abstract_on_during_aspects == []
        assert state_factory.abstract_on_durings == []
        assert state_factory.abstract_on_enters == []
        assert state_factory.abstract_on_exits == []
        assert len(state_factory.init_transitions) == 1
        assert state_factory.init_transitions[0].from_state == INIT_STATE
        assert state_factory.init_transitions[0].to_state == "Line"
        assert state_factory.init_transitions[0].event is None
        assert state_factory.init_transitions[0].guard is None
        assert state_factory.init_transitions[0].effects == []
        assert state_factory.init_transitions[0].parent_ref().name == "Factory"
        assert state_factory.init_transitions[0].parent_ref().path == ("Factory",)
        assert not state_factory.is_leaf_state
        assert state_factory.is_root_state
        assert not state_factory.is_stoppable
        assert state_factory.non_abstract_on_during_aspects == []
        assert state_factory.non_abstract_on_durings == []
        assert state_factory.non_abstract_on_enters == []
        assert state_factory.non_abstract_on_exits == []
        assert state_factory.parent is None
        assert len(state_factory.transitions_entering_children) == 1
        assert state_factory.transitions_entering_children[0].from_state == INIT_STATE
        assert state_factory.transitions_entering_children[0].to_state == "Line"
        assert state_factory.transitions_entering_children[0].event is None
        assert state_factory.transitions_entering_children[0].guard is None
        assert state_factory.transitions_entering_children[0].effects == []
        assert (
            state_factory.transitions_entering_children[0].parent_ref().name
            == "Factory"
        )
        assert state_factory.transitions_entering_children[0].parent_ref().path == (
            "Factory",
        )
        assert len(state_factory.transitions_entering_children_simplified) == 1
        assert (
            state_factory.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_factory.transitions_entering_children_simplified[0].to_state == "Line"
        )
        assert state_factory.transitions_entering_children_simplified[0].event is None
        assert state_factory.transitions_entering_children_simplified[0].guard is None
        assert state_factory.transitions_entering_children_simplified[0].effects == []
        assert (
            state_factory.transitions_entering_children_simplified[0].parent_ref().name
            == "Factory"
        )
        assert state_factory.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Factory",)
        assert len(state_factory.transitions_from) == 1
        assert state_factory.transitions_from[0].from_state == "Factory"
        assert state_factory.transitions_from[0].to_state == EXIT_STATE
        assert state_factory.transitions_from[0].event is None
        assert state_factory.transitions_from[0].guard is None
        assert state_factory.transitions_from[0].effects == []
        assert state_factory.transitions_from[0].parent_ref is None
        assert len(state_factory.transitions_to) == 1
        assert state_factory.transitions_to[0].from_state == INIT_STATE
        assert state_factory.transitions_to[0].to_state == "Factory"
        assert state_factory.transitions_to[0].event is None
        assert state_factory.transitions_to[0].guard is None
        assert state_factory.transitions_to[0].effects == []
        assert state_factory.transitions_to[0].parent_ref is None

    def test_state_factory_to_ast_node(self, state_factory):
        ast_node = state_factory.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Factory",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Line",
                    extra_name="Assembly Line",
                    events=[],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Conveyor",
                            extra_name=None,
                            events=[],
                            imports=[],
                            substates=[
                                dsl_nodes.StateDefinition(
                                    name="Feeding",
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
                                    to_state="Feeding",
                                    event_id=None,
                                    condition_expr=None,
                                    post_operations=[],
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="Feeding",
                                    to_state="Feeding",
                                    event_id=None,
                                    condition_expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="host_ticks"),
                                        op="<",
                                        expr2=dsl_nodes.Integer(raw="2"),
                                    ),
                                    post_operations=[
                                        dsl_nodes.OperationAssignment(
                                            name="host_ticks",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(name="host_ticks"),
                                                op="+",
                                                expr2=dsl_nodes.Integer(raw="1"),
                                            ),
                                        ),
                                        dsl_nodes.OperationAssignment(
                                            name="host_load",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(name="host_load"),
                                                op="+",
                                                expr2=dsl_nodes.Integer(raw="1"),
                                            ),
                                        ),
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
                            name="Robot",
                            extra_name=None,
                            events=[],
                            imports=[],
                            substates=[
                                dsl_nodes.StateDefinition(
                                    name="Picking",
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
                                    to_state="Picking",
                                    event_id=None,
                                    condition_expr=None,
                                    post_operations=[],
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="Picking",
                                    to_state="Picking",
                                    event_id=None,
                                    condition_expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="host_load"),
                                        op="<",
                                        expr2=dsl_nodes.Integer(raw="4"),
                                    ),
                                    post_operations=[
                                        dsl_nodes.OperationAssignment(
                                            name="host_ticks",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(name="host_ticks"),
                                                op="+",
                                                expr2=dsl_nodes.Integer(raw="1"),
                                            ),
                                        ),
                                        dsl_nodes.OperationAssignment(
                                            name="host_load",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(name="host_load"),
                                                op="+",
                                                expr2=dsl_nodes.Integer(raw="1"),
                                            ),
                                        ),
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
                            to_state="Conveyor",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Conveyor",
                            to_state="Robot",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="host_ticks"),
                                op=">=",
                                expr2=dsl_nodes.Integer(raw="2"),
                            ),
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Robot",
                            to_state="Conveyor",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="host_load"),
                                op=">=",
                                expr2=dsl_nodes.Integer(raw="4"),
                            ),
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
                    from_state=INIT_STATE,
                    to_state="Line",
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

    def test_state_factory_list_on_enters(self, state_factory):
        lst = state_factory.list_on_enters()
        assert lst == []

        lst = state_factory.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_factory.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_factory.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_factory.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_factory.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_factory.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_factory.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_factory.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_factory_during_aspects(self, state_factory):
        lst = state_factory.list_on_during_aspects()
        assert lst == []

        lst = state_factory.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_factory.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_factory.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_factory.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_factory.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_factory.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_factory.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_factory.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_factory_line(self, state_factory_line):
        assert state_factory_line.name == "Line"
        assert state_factory_line.path == ("Factory", "Line")
        assert sorted(state_factory_line.substates.keys()) == ["Conveyor", "Robot"]
        assert state_factory_line.events == {}
        assert len(state_factory_line.transitions) == 3
        assert state_factory_line.transitions[0].from_state == INIT_STATE
        assert state_factory_line.transitions[0].to_state == "Conveyor"
        assert state_factory_line.transitions[0].event is None
        assert state_factory_line.transitions[0].guard is None
        assert state_factory_line.transitions[0].effects == []
        assert state_factory_line.transitions[0].parent_ref().name == "Line"
        assert state_factory_line.transitions[0].parent_ref().path == (
            "Factory",
            "Line",
        )
        assert state_factory_line.transitions[1].from_state == "Conveyor"
        assert state_factory_line.transitions[1].to_state == "Robot"
        assert state_factory_line.transitions[1].event is None
        assert state_factory_line.transitions[1].guard == BinaryOp(
            x=Variable(name="host_ticks"), op=">=", y=Integer(value=2)
        )
        assert state_factory_line.transitions[1].effects == []
        assert state_factory_line.transitions[1].parent_ref().name == "Line"
        assert state_factory_line.transitions[1].parent_ref().path == (
            "Factory",
            "Line",
        )
        assert state_factory_line.transitions[2].from_state == "Robot"
        assert state_factory_line.transitions[2].to_state == "Conveyor"
        assert state_factory_line.transitions[2].event is None
        assert state_factory_line.transitions[2].guard == BinaryOp(
            x=Variable(name="host_load"), op=">=", y=Integer(value=4)
        )
        assert state_factory_line.transitions[2].effects == []
        assert state_factory_line.transitions[2].parent_ref().name == "Line"
        assert state_factory_line.transitions[2].parent_ref().path == (
            "Factory",
            "Line",
        )
        assert state_factory_line.named_functions == {}
        assert state_factory_line.on_enters == []
        assert state_factory_line.on_durings == []
        assert state_factory_line.on_exits == []
        assert state_factory_line.on_during_aspects == []
        assert state_factory_line.parent_ref().name == "Factory"
        assert state_factory_line.parent_ref().path == ("Factory",)
        assert state_factory_line.substate_name_to_id == {"Conveyor": 0, "Robot": 1}
        assert state_factory_line.extra_name == "Assembly Line"
        assert not state_factory_line.is_pseudo
        assert state_factory_line.abstract_on_during_aspects == []
        assert state_factory_line.abstract_on_durings == []
        assert state_factory_line.abstract_on_enters == []
        assert state_factory_line.abstract_on_exits == []
        assert len(state_factory_line.init_transitions) == 1
        assert state_factory_line.init_transitions[0].from_state == INIT_STATE
        assert state_factory_line.init_transitions[0].to_state == "Conveyor"
        assert state_factory_line.init_transitions[0].event is None
        assert state_factory_line.init_transitions[0].guard is None
        assert state_factory_line.init_transitions[0].effects == []
        assert state_factory_line.init_transitions[0].parent_ref().name == "Line"
        assert state_factory_line.init_transitions[0].parent_ref().path == (
            "Factory",
            "Line",
        )
        assert not state_factory_line.is_leaf_state
        assert not state_factory_line.is_root_state
        assert not state_factory_line.is_stoppable
        assert state_factory_line.non_abstract_on_during_aspects == []
        assert state_factory_line.non_abstract_on_durings == []
        assert state_factory_line.non_abstract_on_enters == []
        assert state_factory_line.non_abstract_on_exits == []
        assert state_factory_line.parent.name == "Factory"
        assert state_factory_line.parent.path == ("Factory",)
        assert len(state_factory_line.transitions_entering_children) == 1
        assert (
            state_factory_line.transitions_entering_children[0].from_state == INIT_STATE
        )
        assert (
            state_factory_line.transitions_entering_children[0].to_state == "Conveyor"
        )
        assert state_factory_line.transitions_entering_children[0].event is None
        assert state_factory_line.transitions_entering_children[0].guard is None
        assert state_factory_line.transitions_entering_children[0].effects == []
        assert (
            state_factory_line.transitions_entering_children[0].parent_ref().name
            == "Line"
        )
        assert state_factory_line.transitions_entering_children[
            0
        ].parent_ref().path == ("Factory", "Line")
        assert len(state_factory_line.transitions_entering_children_simplified) == 1
        assert (
            state_factory_line.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_factory_line.transitions_entering_children_simplified[0].to_state
            == "Conveyor"
        )
        assert (
            state_factory_line.transitions_entering_children_simplified[0].event is None
        )
        assert (
            state_factory_line.transitions_entering_children_simplified[0].guard is None
        )
        assert (
            state_factory_line.transitions_entering_children_simplified[0].effects == []
        )
        assert (
            state_factory_line.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "Line"
        )
        assert state_factory_line.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Factory", "Line")
        assert state_factory_line.transitions_from == []
        assert len(state_factory_line.transitions_to) == 1
        assert state_factory_line.transitions_to[0].from_state == INIT_STATE
        assert state_factory_line.transitions_to[0].to_state == "Line"
        assert state_factory_line.transitions_to[0].event is None
        assert state_factory_line.transitions_to[0].guard is None
        assert state_factory_line.transitions_to[0].effects == []
        assert state_factory_line.transitions_to[0].parent_ref().name == "Factory"
        assert state_factory_line.transitions_to[0].parent_ref().path == ("Factory",)

    def test_state_factory_line_to_ast_node(self, state_factory_line):
        ast_node = state_factory_line.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Line",
            extra_name="Assembly Line",
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Conveyor",
                    extra_name=None,
                    events=[],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Feeding",
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
                            to_state="Feeding",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Feeding",
                            to_state="Feeding",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="host_ticks"),
                                op="<",
                                expr2=dsl_nodes.Integer(raw="2"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="host_ticks",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="host_ticks"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="host_load",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="host_load"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
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
                    name="Robot",
                    extra_name=None,
                    events=[],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Picking",
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
                            to_state="Picking",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Picking",
                            to_state="Picking",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="host_load"),
                                op="<",
                                expr2=dsl_nodes.Integer(raw="4"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="host_ticks",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="host_ticks"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="host_load",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="host_load"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
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
                    to_state="Conveyor",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Conveyor",
                    to_state="Robot",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="host_ticks"),
                        op=">=",
                        expr2=dsl_nodes.Integer(raw="2"),
                    ),
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Robot",
                    to_state="Conveyor",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="host_load"),
                        op=">=",
                        expr2=dsl_nodes.Integer(raw="4"),
                    ),
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

    def test_state_factory_line_list_on_enters(self, state_factory_line):
        lst = state_factory_line.list_on_enters()
        assert lst == []

        lst = state_factory_line.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_factory_line.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_factory_line.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_factory_line.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_factory_line.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_factory_line.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_factory_line.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_factory_line.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_factory_line_during_aspects(self, state_factory_line):
        lst = state_factory_line.list_on_during_aspects()
        assert lst == []

        lst = state_factory_line.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_factory_line.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_factory_line.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_factory_line.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_factory_line.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_factory_line.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_factory_line.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_factory_line.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_factory_line_conveyor(self, state_factory_line_conveyor):
        assert state_factory_line_conveyor.name == "Conveyor"
        assert state_factory_line_conveyor.path == ("Factory", "Line", "Conveyor")
        assert sorted(state_factory_line_conveyor.substates.keys()) == ["Feeding"]
        assert state_factory_line_conveyor.events == {}
        assert len(state_factory_line_conveyor.transitions) == 2
        assert state_factory_line_conveyor.transitions[0].from_state == INIT_STATE
        assert state_factory_line_conveyor.transitions[0].to_state == "Feeding"
        assert state_factory_line_conveyor.transitions[0].event is None
        assert state_factory_line_conveyor.transitions[0].guard is None
        assert state_factory_line_conveyor.transitions[0].effects == []
        assert (
            state_factory_line_conveyor.transitions[0].parent_ref().name == "Conveyor"
        )
        assert state_factory_line_conveyor.transitions[0].parent_ref().path == (
            "Factory",
            "Line",
            "Conveyor",
        )
        assert state_factory_line_conveyor.transitions[1].from_state == "Feeding"
        assert state_factory_line_conveyor.transitions[1].to_state == "Feeding"
        assert state_factory_line_conveyor.transitions[1].event is None
        assert state_factory_line_conveyor.transitions[1].guard == BinaryOp(
            x=Variable(name="host_ticks"), op="<", y=Integer(value=2)
        )
        assert state_factory_line_conveyor.transitions[1].effects == [
            Operation(
                var_name="host_ticks",
                expr=BinaryOp(
                    x=Variable(name="host_ticks"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(
                var_name="host_load",
                expr=BinaryOp(x=Variable(name="host_load"), op="+", y=Integer(value=1)),
            ),
        ]
        assert (
            state_factory_line_conveyor.transitions[1].parent_ref().name == "Conveyor"
        )
        assert state_factory_line_conveyor.transitions[1].parent_ref().path == (
            "Factory",
            "Line",
            "Conveyor",
        )
        assert state_factory_line_conveyor.named_functions == {}
        assert state_factory_line_conveyor.on_enters == []
        assert state_factory_line_conveyor.on_durings == []
        assert state_factory_line_conveyor.on_exits == []
        assert state_factory_line_conveyor.on_during_aspects == []
        assert state_factory_line_conveyor.parent_ref().name == "Line"
        assert state_factory_line_conveyor.parent_ref().path == ("Factory", "Line")
        assert state_factory_line_conveyor.substate_name_to_id == {"Feeding": 0}
        assert state_factory_line_conveyor.extra_name is None
        assert not state_factory_line_conveyor.is_pseudo
        assert state_factory_line_conveyor.abstract_on_during_aspects == []
        assert state_factory_line_conveyor.abstract_on_durings == []
        assert state_factory_line_conveyor.abstract_on_enters == []
        assert state_factory_line_conveyor.abstract_on_exits == []
        assert len(state_factory_line_conveyor.init_transitions) == 1
        assert state_factory_line_conveyor.init_transitions[0].from_state == INIT_STATE
        assert state_factory_line_conveyor.init_transitions[0].to_state == "Feeding"
        assert state_factory_line_conveyor.init_transitions[0].event is None
        assert state_factory_line_conveyor.init_transitions[0].guard is None
        assert state_factory_line_conveyor.init_transitions[0].effects == []
        assert (
            state_factory_line_conveyor.init_transitions[0].parent_ref().name
            == "Conveyor"
        )
        assert state_factory_line_conveyor.init_transitions[0].parent_ref().path == (
            "Factory",
            "Line",
            "Conveyor",
        )
        assert not state_factory_line_conveyor.is_leaf_state
        assert not state_factory_line_conveyor.is_root_state
        assert not state_factory_line_conveyor.is_stoppable
        assert state_factory_line_conveyor.non_abstract_on_during_aspects == []
        assert state_factory_line_conveyor.non_abstract_on_durings == []
        assert state_factory_line_conveyor.non_abstract_on_enters == []
        assert state_factory_line_conveyor.non_abstract_on_exits == []
        assert state_factory_line_conveyor.parent.name == "Line"
        assert state_factory_line_conveyor.parent.path == ("Factory", "Line")
        assert len(state_factory_line_conveyor.transitions_entering_children) == 1
        assert (
            state_factory_line_conveyor.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children[0].to_state
            == "Feeding"
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children[0].event is None
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children[0].guard is None
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children[0].effects == []
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children[0]
            .parent_ref()
            .name
            == "Conveyor"
        )
        assert state_factory_line_conveyor.transitions_entering_children[
            0
        ].parent_ref().path == ("Factory", "Line", "Conveyor")
        assert (
            len(state_factory_line_conveyor.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children_simplified[
                0
            ].to_state
            == "Feeding"
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children_simplified[
                0
            ].event
            is None
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children_simplified[
                0
            ].guard
            is None
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children_simplified[
                0
            ].effects
            == []
        )
        assert (
            state_factory_line_conveyor.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "Conveyor"
        )
        assert state_factory_line_conveyor.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Factory", "Line", "Conveyor")
        assert len(state_factory_line_conveyor.transitions_from) == 1
        assert state_factory_line_conveyor.transitions_from[0].from_state == "Conveyor"
        assert state_factory_line_conveyor.transitions_from[0].to_state == "Robot"
        assert state_factory_line_conveyor.transitions_from[0].event is None
        assert state_factory_line_conveyor.transitions_from[0].guard == BinaryOp(
            x=Variable(name="host_ticks"), op=">=", y=Integer(value=2)
        )
        assert state_factory_line_conveyor.transitions_from[0].effects == []
        assert (
            state_factory_line_conveyor.transitions_from[0].parent_ref().name == "Line"
        )
        assert state_factory_line_conveyor.transitions_from[0].parent_ref().path == (
            "Factory",
            "Line",
        )
        assert len(state_factory_line_conveyor.transitions_to) == 2
        assert state_factory_line_conveyor.transitions_to[0].from_state == INIT_STATE
        assert state_factory_line_conveyor.transitions_to[0].to_state == "Conveyor"
        assert state_factory_line_conveyor.transitions_to[0].event is None
        assert state_factory_line_conveyor.transitions_to[0].guard is None
        assert state_factory_line_conveyor.transitions_to[0].effects == []
        assert state_factory_line_conveyor.transitions_to[0].parent_ref().name == "Line"
        assert state_factory_line_conveyor.transitions_to[0].parent_ref().path == (
            "Factory",
            "Line",
        )
        assert state_factory_line_conveyor.transitions_to[1].from_state == "Robot"
        assert state_factory_line_conveyor.transitions_to[1].to_state == "Conveyor"
        assert state_factory_line_conveyor.transitions_to[1].event is None
        assert state_factory_line_conveyor.transitions_to[1].guard == BinaryOp(
            x=Variable(name="host_load"), op=">=", y=Integer(value=4)
        )
        assert state_factory_line_conveyor.transitions_to[1].effects == []
        assert state_factory_line_conveyor.transitions_to[1].parent_ref().name == "Line"
        assert state_factory_line_conveyor.transitions_to[1].parent_ref().path == (
            "Factory",
            "Line",
        )

    def test_state_factory_line_conveyor_to_ast_node(self, state_factory_line_conveyor):
        ast_node = state_factory_line_conveyor.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Conveyor",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Feeding",
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
                    to_state="Feeding",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Feeding",
                    to_state="Feeding",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="host_ticks"),
                        op="<",
                        expr2=dsl_nodes.Integer(raw="2"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="host_ticks",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="host_ticks"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
                        dsl_nodes.OperationAssignment(
                            name="host_load",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="host_load"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
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

    def test_state_factory_line_conveyor_list_on_enters(
        self, state_factory_line_conveyor
    ):
        lst = state_factory_line_conveyor.list_on_enters()
        assert lst == []

        lst = state_factory_line_conveyor.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_factory_line_conveyor.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_factory_line_conveyor.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_factory_line_conveyor.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_factory_line_conveyor.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_factory_line_conveyor.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_factory_line_conveyor.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_factory_line_conveyor.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_factory_line_conveyor_during_aspects(
        self, state_factory_line_conveyor
    ):
        lst = state_factory_line_conveyor.list_on_during_aspects()
        assert lst == []

        lst = state_factory_line_conveyor.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_factory_line_conveyor.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_factory_line_conveyor.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_factory_line_conveyor.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_factory_line_conveyor.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_factory_line_conveyor.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_factory_line_conveyor.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_factory_line_conveyor.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_factory_line_conveyor_feeding(
        self, state_factory_line_conveyor_feeding
    ):
        assert state_factory_line_conveyor_feeding.name == "Feeding"
        assert state_factory_line_conveyor_feeding.path == (
            "Factory",
            "Line",
            "Conveyor",
            "Feeding",
        )
        assert sorted(state_factory_line_conveyor_feeding.substates.keys()) == []
        assert state_factory_line_conveyor_feeding.events == {}
        assert state_factory_line_conveyor_feeding.transitions == []
        assert state_factory_line_conveyor_feeding.named_functions == {}
        assert state_factory_line_conveyor_feeding.on_enters == []
        assert state_factory_line_conveyor_feeding.on_durings == []
        assert state_factory_line_conveyor_feeding.on_exits == []
        assert state_factory_line_conveyor_feeding.on_during_aspects == []
        assert state_factory_line_conveyor_feeding.parent_ref().name == "Conveyor"
        assert state_factory_line_conveyor_feeding.parent_ref().path == (
            "Factory",
            "Line",
            "Conveyor",
        )
        assert state_factory_line_conveyor_feeding.substate_name_to_id == {}
        assert state_factory_line_conveyor_feeding.extra_name is None
        assert not state_factory_line_conveyor_feeding.is_pseudo
        assert state_factory_line_conveyor_feeding.abstract_on_during_aspects == []
        assert state_factory_line_conveyor_feeding.abstract_on_durings == []
        assert state_factory_line_conveyor_feeding.abstract_on_enters == []
        assert state_factory_line_conveyor_feeding.abstract_on_exits == []
        assert state_factory_line_conveyor_feeding.init_transitions == []
        assert state_factory_line_conveyor_feeding.is_leaf_state
        assert not state_factory_line_conveyor_feeding.is_root_state
        assert state_factory_line_conveyor_feeding.is_stoppable
        assert state_factory_line_conveyor_feeding.non_abstract_on_during_aspects == []
        assert state_factory_line_conveyor_feeding.non_abstract_on_durings == []
        assert state_factory_line_conveyor_feeding.non_abstract_on_enters == []
        assert state_factory_line_conveyor_feeding.non_abstract_on_exits == []
        assert state_factory_line_conveyor_feeding.parent.name == "Conveyor"
        assert state_factory_line_conveyor_feeding.parent.path == (
            "Factory",
            "Line",
            "Conveyor",
        )
        assert state_factory_line_conveyor_feeding.transitions_entering_children == []
        assert (
            len(
                state_factory_line_conveyor_feeding.transitions_entering_children_simplified
            )
            == 1
        )
        assert (
            state_factory_line_conveyor_feeding.transitions_entering_children_simplified[
                0
            ]
            is None
        )
        assert len(state_factory_line_conveyor_feeding.transitions_from) == 1
        assert (
            state_factory_line_conveyor_feeding.transitions_from[0].from_state
            == "Feeding"
        )
        assert (
            state_factory_line_conveyor_feeding.transitions_from[0].to_state
            == "Feeding"
        )
        assert state_factory_line_conveyor_feeding.transitions_from[0].event is None
        assert state_factory_line_conveyor_feeding.transitions_from[
            0
        ].guard == BinaryOp(x=Variable(name="host_ticks"), op="<", y=Integer(value=2))
        assert state_factory_line_conveyor_feeding.transitions_from[0].effects == [
            Operation(
                var_name="host_ticks",
                expr=BinaryOp(
                    x=Variable(name="host_ticks"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(
                var_name="host_load",
                expr=BinaryOp(x=Variable(name="host_load"), op="+", y=Integer(value=1)),
            ),
        ]
        assert (
            state_factory_line_conveyor_feeding.transitions_from[0].parent_ref().name
            == "Conveyor"
        )
        assert state_factory_line_conveyor_feeding.transitions_from[
            0
        ].parent_ref().path == ("Factory", "Line", "Conveyor")
        assert len(state_factory_line_conveyor_feeding.transitions_to) == 2
        assert (
            state_factory_line_conveyor_feeding.transitions_to[0].from_state
            == INIT_STATE
        )
        assert (
            state_factory_line_conveyor_feeding.transitions_to[0].to_state == "Feeding"
        )
        assert state_factory_line_conveyor_feeding.transitions_to[0].event is None
        assert state_factory_line_conveyor_feeding.transitions_to[0].guard is None
        assert state_factory_line_conveyor_feeding.transitions_to[0].effects == []
        assert (
            state_factory_line_conveyor_feeding.transitions_to[0].parent_ref().name
            == "Conveyor"
        )
        assert state_factory_line_conveyor_feeding.transitions_to[
            0
        ].parent_ref().path == ("Factory", "Line", "Conveyor")
        assert (
            state_factory_line_conveyor_feeding.transitions_to[1].from_state
            == "Feeding"
        )
        assert (
            state_factory_line_conveyor_feeding.transitions_to[1].to_state == "Feeding"
        )
        assert state_factory_line_conveyor_feeding.transitions_to[1].event is None
        assert state_factory_line_conveyor_feeding.transitions_to[1].guard == BinaryOp(
            x=Variable(name="host_ticks"), op="<", y=Integer(value=2)
        )
        assert state_factory_line_conveyor_feeding.transitions_to[1].effects == [
            Operation(
                var_name="host_ticks",
                expr=BinaryOp(
                    x=Variable(name="host_ticks"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(
                var_name="host_load",
                expr=BinaryOp(x=Variable(name="host_load"), op="+", y=Integer(value=1)),
            ),
        ]
        assert (
            state_factory_line_conveyor_feeding.transitions_to[1].parent_ref().name
            == "Conveyor"
        )
        assert state_factory_line_conveyor_feeding.transitions_to[
            1
        ].parent_ref().path == ("Factory", "Line", "Conveyor")

    def test_state_factory_line_conveyor_feeding_to_ast_node(
        self, state_factory_line_conveyor_feeding
    ):
        ast_node = state_factory_line_conveyor_feeding.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Feeding",
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

    def test_state_factory_line_conveyor_feeding_list_on_enters(
        self, state_factory_line_conveyor_feeding
    ):
        lst = state_factory_line_conveyor_feeding.list_on_enters()
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_factory_line_conveyor_feeding_during_aspects(
        self, state_factory_line_conveyor_feeding
    ):
        lst = state_factory_line_conveyor_feeding.list_on_during_aspects()
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_during_aspects(
            aspect="before"
        )
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_during_aspects(
            is_abstract=False
        )
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_during_aspects(
            is_abstract=True
        )
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_factory_line_conveyor_feeding_during_aspect_recursively(
        self, state_factory_line_conveyor_feeding
    ):
        lst = state_factory_line_conveyor_feeding.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_factory_line_conveyor_feeding.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_factory_line_robot(self, state_factory_line_robot):
        assert state_factory_line_robot.name == "Robot"
        assert state_factory_line_robot.path == ("Factory", "Line", "Robot")
        assert sorted(state_factory_line_robot.substates.keys()) == ["Picking"]
        assert state_factory_line_robot.events == {}
        assert len(state_factory_line_robot.transitions) == 2
        assert state_factory_line_robot.transitions[0].from_state == INIT_STATE
        assert state_factory_line_robot.transitions[0].to_state == "Picking"
        assert state_factory_line_robot.transitions[0].event is None
        assert state_factory_line_robot.transitions[0].guard is None
        assert state_factory_line_robot.transitions[0].effects == []
        assert state_factory_line_robot.transitions[0].parent_ref().name == "Robot"
        assert state_factory_line_robot.transitions[0].parent_ref().path == (
            "Factory",
            "Line",
            "Robot",
        )
        assert state_factory_line_robot.transitions[1].from_state == "Picking"
        assert state_factory_line_robot.transitions[1].to_state == "Picking"
        assert state_factory_line_robot.transitions[1].event is None
        assert state_factory_line_robot.transitions[1].guard == BinaryOp(
            x=Variable(name="host_load"), op="<", y=Integer(value=4)
        )
        assert state_factory_line_robot.transitions[1].effects == [
            Operation(
                var_name="host_ticks",
                expr=BinaryOp(
                    x=Variable(name="host_ticks"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(
                var_name="host_load",
                expr=BinaryOp(x=Variable(name="host_load"), op="+", y=Integer(value=1)),
            ),
        ]
        assert state_factory_line_robot.transitions[1].parent_ref().name == "Robot"
        assert state_factory_line_robot.transitions[1].parent_ref().path == (
            "Factory",
            "Line",
            "Robot",
        )
        assert state_factory_line_robot.named_functions == {}
        assert state_factory_line_robot.on_enters == []
        assert state_factory_line_robot.on_durings == []
        assert state_factory_line_robot.on_exits == []
        assert state_factory_line_robot.on_during_aspects == []
        assert state_factory_line_robot.parent_ref().name == "Line"
        assert state_factory_line_robot.parent_ref().path == ("Factory", "Line")
        assert state_factory_line_robot.substate_name_to_id == {"Picking": 0}
        assert state_factory_line_robot.extra_name is None
        assert not state_factory_line_robot.is_pseudo
        assert state_factory_line_robot.abstract_on_during_aspects == []
        assert state_factory_line_robot.abstract_on_durings == []
        assert state_factory_line_robot.abstract_on_enters == []
        assert state_factory_line_robot.abstract_on_exits == []
        assert len(state_factory_line_robot.init_transitions) == 1
        assert state_factory_line_robot.init_transitions[0].from_state == INIT_STATE
        assert state_factory_line_robot.init_transitions[0].to_state == "Picking"
        assert state_factory_line_robot.init_transitions[0].event is None
        assert state_factory_line_robot.init_transitions[0].guard is None
        assert state_factory_line_robot.init_transitions[0].effects == []
        assert state_factory_line_robot.init_transitions[0].parent_ref().name == "Robot"
        assert state_factory_line_robot.init_transitions[0].parent_ref().path == (
            "Factory",
            "Line",
            "Robot",
        )
        assert not state_factory_line_robot.is_leaf_state
        assert not state_factory_line_robot.is_root_state
        assert not state_factory_line_robot.is_stoppable
        assert state_factory_line_robot.non_abstract_on_during_aspects == []
        assert state_factory_line_robot.non_abstract_on_durings == []
        assert state_factory_line_robot.non_abstract_on_enters == []
        assert state_factory_line_robot.non_abstract_on_exits == []
        assert state_factory_line_robot.parent.name == "Line"
        assert state_factory_line_robot.parent.path == ("Factory", "Line")
        assert len(state_factory_line_robot.transitions_entering_children) == 1
        assert (
            state_factory_line_robot.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert (
            state_factory_line_robot.transitions_entering_children[0].to_state
            == "Picking"
        )
        assert state_factory_line_robot.transitions_entering_children[0].event is None
        assert state_factory_line_robot.transitions_entering_children[0].guard is None
        assert state_factory_line_robot.transitions_entering_children[0].effects == []
        assert (
            state_factory_line_robot.transitions_entering_children[0].parent_ref().name
            == "Robot"
        )
        assert state_factory_line_robot.transitions_entering_children[
            0
        ].parent_ref().path == ("Factory", "Line", "Robot")
        assert (
            len(state_factory_line_robot.transitions_entering_children_simplified) == 1
        )
        assert (
            state_factory_line_robot.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_factory_line_robot.transitions_entering_children_simplified[
                0
            ].to_state
            == "Picking"
        )
        assert (
            state_factory_line_robot.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_factory_line_robot.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_factory_line_robot.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_factory_line_robot.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "Robot"
        )
        assert state_factory_line_robot.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Factory", "Line", "Robot")
        assert len(state_factory_line_robot.transitions_from) == 1
        assert state_factory_line_robot.transitions_from[0].from_state == "Robot"
        assert state_factory_line_robot.transitions_from[0].to_state == "Conveyor"
        assert state_factory_line_robot.transitions_from[0].event is None
        assert state_factory_line_robot.transitions_from[0].guard == BinaryOp(
            x=Variable(name="host_load"), op=">=", y=Integer(value=4)
        )
        assert state_factory_line_robot.transitions_from[0].effects == []
        assert state_factory_line_robot.transitions_from[0].parent_ref().name == "Line"
        assert state_factory_line_robot.transitions_from[0].parent_ref().path == (
            "Factory",
            "Line",
        )
        assert len(state_factory_line_robot.transitions_to) == 1
        assert state_factory_line_robot.transitions_to[0].from_state == "Conveyor"
        assert state_factory_line_robot.transitions_to[0].to_state == "Robot"
        assert state_factory_line_robot.transitions_to[0].event is None
        assert state_factory_line_robot.transitions_to[0].guard == BinaryOp(
            x=Variable(name="host_ticks"), op=">=", y=Integer(value=2)
        )
        assert state_factory_line_robot.transitions_to[0].effects == []
        assert state_factory_line_robot.transitions_to[0].parent_ref().name == "Line"
        assert state_factory_line_robot.transitions_to[0].parent_ref().path == (
            "Factory",
            "Line",
        )

    def test_state_factory_line_robot_to_ast_node(self, state_factory_line_robot):
        ast_node = state_factory_line_robot.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Robot",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Picking",
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
                    to_state="Picking",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Picking",
                    to_state="Picking",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="host_load"),
                        op="<",
                        expr2=dsl_nodes.Integer(raw="4"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="host_ticks",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="host_ticks"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
                        dsl_nodes.OperationAssignment(
                            name="host_load",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="host_load"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
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

    def test_state_factory_line_robot_list_on_enters(self, state_factory_line_robot):
        lst = state_factory_line_robot.list_on_enters()
        assert lst == []

        lst = state_factory_line_robot.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_factory_line_robot.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_factory_line_robot.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_factory_line_robot.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_factory_line_robot.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_factory_line_robot.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_factory_line_robot.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_factory_line_robot.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_factory_line_robot_during_aspects(self, state_factory_line_robot):
        lst = state_factory_line_robot.list_on_during_aspects()
        assert lst == []

        lst = state_factory_line_robot.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_factory_line_robot.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_factory_line_robot.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_factory_line_robot.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_factory_line_robot.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_factory_line_robot.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_factory_line_robot.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_factory_line_robot.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_factory_line_robot_picking(self, state_factory_line_robot_picking):
        assert state_factory_line_robot_picking.name == "Picking"
        assert state_factory_line_robot_picking.path == (
            "Factory",
            "Line",
            "Robot",
            "Picking",
        )
        assert sorted(state_factory_line_robot_picking.substates.keys()) == []
        assert state_factory_line_robot_picking.events == {}
        assert state_factory_line_robot_picking.transitions == []
        assert state_factory_line_robot_picking.named_functions == {}
        assert state_factory_line_robot_picking.on_enters == []
        assert state_factory_line_robot_picking.on_durings == []
        assert state_factory_line_robot_picking.on_exits == []
        assert state_factory_line_robot_picking.on_during_aspects == []
        assert state_factory_line_robot_picking.parent_ref().name == "Robot"
        assert state_factory_line_robot_picking.parent_ref().path == (
            "Factory",
            "Line",
            "Robot",
        )
        assert state_factory_line_robot_picking.substate_name_to_id == {}
        assert state_factory_line_robot_picking.extra_name is None
        assert not state_factory_line_robot_picking.is_pseudo
        assert state_factory_line_robot_picking.abstract_on_during_aspects == []
        assert state_factory_line_robot_picking.abstract_on_durings == []
        assert state_factory_line_robot_picking.abstract_on_enters == []
        assert state_factory_line_robot_picking.abstract_on_exits == []
        assert state_factory_line_robot_picking.init_transitions == []
        assert state_factory_line_robot_picking.is_leaf_state
        assert not state_factory_line_robot_picking.is_root_state
        assert state_factory_line_robot_picking.is_stoppable
        assert state_factory_line_robot_picking.non_abstract_on_during_aspects == []
        assert state_factory_line_robot_picking.non_abstract_on_durings == []
        assert state_factory_line_robot_picking.non_abstract_on_enters == []
        assert state_factory_line_robot_picking.non_abstract_on_exits == []
        assert state_factory_line_robot_picking.parent.name == "Robot"
        assert state_factory_line_robot_picking.parent.path == (
            "Factory",
            "Line",
            "Robot",
        )
        assert state_factory_line_robot_picking.transitions_entering_children == []
        assert (
            len(
                state_factory_line_robot_picking.transitions_entering_children_simplified
            )
            == 1
        )
        assert (
            state_factory_line_robot_picking.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_factory_line_robot_picking.transitions_from) == 1
        assert (
            state_factory_line_robot_picking.transitions_from[0].from_state == "Picking"
        )
        assert (
            state_factory_line_robot_picking.transitions_from[0].to_state == "Picking"
        )
        assert state_factory_line_robot_picking.transitions_from[0].event is None
        assert state_factory_line_robot_picking.transitions_from[0].guard == BinaryOp(
            x=Variable(name="host_load"), op="<", y=Integer(value=4)
        )
        assert state_factory_line_robot_picking.transitions_from[0].effects == [
            Operation(
                var_name="host_ticks",
                expr=BinaryOp(
                    x=Variable(name="host_ticks"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(
                var_name="host_load",
                expr=BinaryOp(x=Variable(name="host_load"), op="+", y=Integer(value=1)),
            ),
        ]
        assert (
            state_factory_line_robot_picking.transitions_from[0].parent_ref().name
            == "Robot"
        )
        assert state_factory_line_robot_picking.transitions_from[
            0
        ].parent_ref().path == ("Factory", "Line", "Robot")
        assert len(state_factory_line_robot_picking.transitions_to) == 2
        assert (
            state_factory_line_robot_picking.transitions_to[0].from_state == INIT_STATE
        )
        assert state_factory_line_robot_picking.transitions_to[0].to_state == "Picking"
        assert state_factory_line_robot_picking.transitions_to[0].event is None
        assert state_factory_line_robot_picking.transitions_to[0].guard is None
        assert state_factory_line_robot_picking.transitions_to[0].effects == []
        assert (
            state_factory_line_robot_picking.transitions_to[0].parent_ref().name
            == "Robot"
        )
        assert state_factory_line_robot_picking.transitions_to[0].parent_ref().path == (
            "Factory",
            "Line",
            "Robot",
        )
        assert (
            state_factory_line_robot_picking.transitions_to[1].from_state == "Picking"
        )
        assert state_factory_line_robot_picking.transitions_to[1].to_state == "Picking"
        assert state_factory_line_robot_picking.transitions_to[1].event is None
        assert state_factory_line_robot_picking.transitions_to[1].guard == BinaryOp(
            x=Variable(name="host_load"), op="<", y=Integer(value=4)
        )
        assert state_factory_line_robot_picking.transitions_to[1].effects == [
            Operation(
                var_name="host_ticks",
                expr=BinaryOp(
                    x=Variable(name="host_ticks"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(
                var_name="host_load",
                expr=BinaryOp(x=Variable(name="host_load"), op="+", y=Integer(value=1)),
            ),
        ]
        assert (
            state_factory_line_robot_picking.transitions_to[1].parent_ref().name
            == "Robot"
        )
        assert state_factory_line_robot_picking.transitions_to[1].parent_ref().path == (
            "Factory",
            "Line",
            "Robot",
        )

    def test_state_factory_line_robot_picking_to_ast_node(
        self, state_factory_line_robot_picking
    ):
        ast_node = state_factory_line_robot_picking.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Picking",
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

    def test_state_factory_line_robot_picking_list_on_enters(
        self, state_factory_line_robot_picking
    ):
        lst = state_factory_line_robot_picking.list_on_enters()
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_factory_line_robot_picking_during_aspects(
        self, state_factory_line_robot_picking
    ):
        lst = state_factory_line_robot_picking.list_on_during_aspects()
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_factory_line_robot_picking_during_aspect_recursively(
        self, state_factory_line_robot_picking
    ):
        lst = state_factory_line_robot_picking.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_factory_line_robot_picking.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int host_ticks = 0;
def int host_load = 0;
state Factory {
    state Line named 'Assembly Line' {
        state Conveyor {
            state Feeding;
            [*] -> Feeding;
            Feeding -> Feeding : if [host_ticks < 2] effect {
                host_ticks = host_ticks + 1;
                host_load = host_load + 1;
            }
        }
        state Robot {
            state Picking;
            [*] -> Picking;
            Picking -> Picking : if [host_load < 4] effect {
                host_ticks = host_ticks + 1;
                host_load = host_load + 1;
            }
        }
        [*] -> Conveyor;
        Conveyor -> Robot : if [host_ticks >= 2];
        Robot -> Conveyor : if [host_load >= 4];
    }
    [*] -> Line;
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
| host_ticks | int | 0 |
| host_load | int | 0 |
endlegend

state "Factory" as factory <<composite>> {
    state "Assembly Line" as factory__line <<composite>> {
        state "Conveyor" as factory__line__conveyor <<composite>> {
            state "Feeding" as factory__line__conveyor__feeding
            [*] --> factory__line__conveyor__feeding
            factory__line__conveyor__feeding --> factory__line__conveyor__feeding : host_ticks < 2
            note on link
            effect {
                host_ticks = host_ticks + 1;
                host_load = host_load + 1;
            }
            end note
        }
        state "Robot" as factory__line__robot <<composite>> {
            state "Picking" as factory__line__robot__picking
            [*] --> factory__line__robot__picking
            factory__line__robot__picking --> factory__line__robot__picking : host_load < 4
            note on link
            effect {
                host_ticks = host_ticks + 1;
                host_load = host_load + 1;
            }
            end note
        }
        [*] --> factory__line__conveyor
        factory__line__conveyor --> factory__line__robot : host_ticks >= 2
        factory__line__robot --> factory__line__conveyor : host_load >= 4
    }
    [*] --> factory__line
}
[*] --> factory
factory --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml(options="full")),
        )
