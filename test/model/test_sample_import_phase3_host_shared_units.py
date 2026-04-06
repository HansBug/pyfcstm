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
def int shared_counter = 100;
def int shared_ready = 1;
def int left_limit = 5;
def int right_limit = 6;
def int left_result = 0;
def int right_result = 0;

state Plant {
    import "./modules/left.fcstm" as LeftUnit named "Left Unit" {
        def counter -> shared_counter;
        def ready_flag -> shared_ready;
        def limit -> left_limit;
        def result -> left_result;
    }
    import "./modules/right.fcstm" as RightUnit named "Right Unit" {
        def pulse_count -> shared_counter;
        def armed_flag -> shared_ready;
        def limit -> right_limit;
        def result -> right_result;
    }
    [*] -> LeftUnit;
    LeftUnit -> RightUnit;
}
        """,
        )
        _write_text_file(
            "modules/left.fcstm",
            """
def int counter = 0;
def int ready_flag = 1;
def int limit = 5;
def int result = 0;

state LeftRoot {
    state Idle;
    state Busy;
    [*] -> Idle;
    Idle -> Busy : if [ready_flag > 0] effect {
        result = counter + limit;
    }
    Busy -> Idle : if [counter < limit] effect {
        counter = counter + 1;
        result = counter;
    }
}
        """,
        )
        _write_text_file(
            "modules/right.fcstm",
            """
def int pulse_count = 100;
def int armed_flag = 1;
def int limit = 6;
def int result = 0;

state RightRoot {
    state Idle;
    state Busy;
    [*] -> Idle;
    Idle -> Busy : if [armed_flag > 0] effect {
        result = pulse_count + limit;
    }
    Busy -> Idle : if [pulse_count >= limit] effect {
        pulse_count = pulse_count + 1;
        result = pulse_count;
    }
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
def state_plant_leftunit(state_plant):
    return state_plant.substates["LeftUnit"]


@pytest.fixture()
def state_plant_leftunit_idle(state_plant_leftunit):
    return state_plant_leftunit.substates["Idle"]


@pytest.fixture()
def state_plant_leftunit_busy(state_plant_leftunit):
    return state_plant_leftunit.substates["Busy"]


@pytest.fixture()
def state_plant_rightunit(state_plant):
    return state_plant.substates["RightUnit"]


@pytest.fixture()
def state_plant_rightunit_idle(state_plant_rightunit):
    return state_plant_rightunit.substates["Idle"]


@pytest.fixture()
def state_plant_rightunit_busy(state_plant_rightunit):
    return state_plant_rightunit.substates["Busy"]


@pytest.mark.unittest
class TestModelStatePlant:
    def test_model(self, model):
        assert model.defines == {
            "shared_counter": VarDefine(
                name="shared_counter", type="int", init=Integer(value=100)
            ),
            "shared_ready": VarDefine(
                name="shared_ready", type="int", init=Integer(value=1)
            ),
            "left_limit": VarDefine(
                name="left_limit", type="int", init=Integer(value=5)
            ),
            "right_limit": VarDefine(
                name="right_limit", type="int", init=Integer(value=6)
            ),
            "left_result": VarDefine(
                name="left_result", type="int", init=Integer(value=0)
            ),
            "right_result": VarDefine(
                name="right_result", type="int", init=Integer(value=0)
            ),
        }
        assert model.root_state.name == "Plant"
        assert model.root_state.path == ("Plant",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="shared_counter", type="int", expr=dsl_nodes.Integer(raw="100")
            ),
            dsl_nodes.DefAssignment(
                name="shared_ready", type="int", expr=dsl_nodes.Integer(raw="1")
            ),
            dsl_nodes.DefAssignment(
                name="left_limit", type="int", expr=dsl_nodes.Integer(raw="5")
            ),
            dsl_nodes.DefAssignment(
                name="right_limit", type="int", expr=dsl_nodes.Integer(raw="6")
            ),
            dsl_nodes.DefAssignment(
                name="left_result", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
            dsl_nodes.DefAssignment(
                name="right_result", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
        ]
        assert ast_node.root_state.name == "Plant"

    def test_state_plant(self, state_plant):
        assert state_plant.name == "Plant"
        assert state_plant.path == ("Plant",)
        assert sorted(state_plant.substates.keys()) == ["LeftUnit", "RightUnit"]
        assert state_plant.events == {}
        assert len(state_plant.transitions) == 2
        assert state_plant.transitions[0].from_state == INIT_STATE
        assert state_plant.transitions[0].to_state == "LeftUnit"
        assert state_plant.transitions[0].event is None
        assert state_plant.transitions[0].guard is None
        assert state_plant.transitions[0].effects == []
        assert state_plant.transitions[0].parent_ref().name == "Plant"
        assert state_plant.transitions[0].parent_ref().path == ("Plant",)
        assert state_plant.transitions[1].from_state == "LeftUnit"
        assert state_plant.transitions[1].to_state == "RightUnit"
        assert state_plant.transitions[1].event is None
        assert state_plant.transitions[1].guard is None
        assert state_plant.transitions[1].effects == []
        assert state_plant.transitions[1].parent_ref().name == "Plant"
        assert state_plant.transitions[1].parent_ref().path == ("Plant",)
        assert state_plant.named_functions == {}
        assert state_plant.on_enters == []
        assert state_plant.on_durings == []
        assert state_plant.on_exits == []
        assert state_plant.on_during_aspects == []
        assert state_plant.parent_ref is None
        assert state_plant.substate_name_to_id == {"LeftUnit": 0, "RightUnit": 1}
        assert state_plant.extra_name is None
        assert not state_plant.is_pseudo
        assert state_plant.abstract_on_during_aspects == []
        assert state_plant.abstract_on_durings == []
        assert state_plant.abstract_on_enters == []
        assert state_plant.abstract_on_exits == []
        assert len(state_plant.init_transitions) == 1
        assert state_plant.init_transitions[0].from_state == INIT_STATE
        assert state_plant.init_transitions[0].to_state == "LeftUnit"
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
        assert state_plant.transitions_entering_children[0].to_state == "LeftUnit"
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
            state_plant.transitions_entering_children_simplified[0].to_state
            == "LeftUnit"
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
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="LeftUnit",
                    extra_name="Left Unit",
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
                            name="Busy",
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
                            to_state="Busy",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="shared_ready"),
                                op=">",
                                expr2=dsl_nodes.Integer(raw="0"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="left_result",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="shared_counter"),
                                        op="+",
                                        expr2=dsl_nodes.Name(name="left_limit"),
                                    ),
                                )
                            ],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Busy",
                            to_state="Idle",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="shared_counter"),
                                op="<",
                                expr2=dsl_nodes.Name(name="left_limit"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="shared_counter",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="shared_counter"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="left_result",
                                    expr=dsl_nodes.Name(name="shared_counter"),
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
                    name="RightUnit",
                    extra_name="Right Unit",
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
                            name="Busy",
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
                            to_state="Busy",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="shared_ready"),
                                op=">",
                                expr2=dsl_nodes.Integer(raw="0"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="right_result",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="shared_counter"),
                                        op="+",
                                        expr2=dsl_nodes.Name(name="right_limit"),
                                    ),
                                )
                            ],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Busy",
                            to_state="Idle",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="shared_counter"),
                                op=">=",
                                expr2=dsl_nodes.Name(name="right_limit"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="shared_counter",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="shared_counter"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="right_result",
                                    expr=dsl_nodes.Name(name="shared_counter"),
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
                    to_state="LeftUnit",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="LeftUnit",
                    to_state="RightUnit",
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

    def test_state_plant_leftunit(self, state_plant_leftunit):
        assert state_plant_leftunit.name == "LeftUnit"
        assert state_plant_leftunit.path == ("Plant", "LeftUnit")
        assert sorted(state_plant_leftunit.substates.keys()) == ["Busy", "Idle"]
        assert state_plant_leftunit.events == {}
        assert len(state_plant_leftunit.transitions) == 3
        assert state_plant_leftunit.transitions[0].from_state == INIT_STATE
        assert state_plant_leftunit.transitions[0].to_state == "Idle"
        assert state_plant_leftunit.transitions[0].event is None
        assert state_plant_leftunit.transitions[0].guard is None
        assert state_plant_leftunit.transitions[0].effects == []
        assert state_plant_leftunit.transitions[0].parent_ref().name == "LeftUnit"
        assert state_plant_leftunit.transitions[0].parent_ref().path == (
            "Plant",
            "LeftUnit",
        )
        assert state_plant_leftunit.transitions[1].from_state == "Idle"
        assert state_plant_leftunit.transitions[1].to_state == "Busy"
        assert state_plant_leftunit.transitions[1].event is None
        assert state_plant_leftunit.transitions[1].guard == BinaryOp(
            x=Variable(name="shared_ready"), op=">", y=Integer(value=0)
        )
        assert state_plant_leftunit.transitions[1].effects == [
            Operation(
                var_name="left_result",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"),
                    op="+",
                    y=Variable(name="left_limit"),
                ),
            )
        ]
        assert state_plant_leftunit.transitions[1].parent_ref().name == "LeftUnit"
        assert state_plant_leftunit.transitions[1].parent_ref().path == (
            "Plant",
            "LeftUnit",
        )
        assert state_plant_leftunit.transitions[2].from_state == "Busy"
        assert state_plant_leftunit.transitions[2].to_state == "Idle"
        assert state_plant_leftunit.transitions[2].event is None
        assert state_plant_leftunit.transitions[2].guard == BinaryOp(
            x=Variable(name="shared_counter"), op="<", y=Variable(name="left_limit")
        )
        assert state_plant_leftunit.transitions[2].effects == [
            Operation(
                var_name="shared_counter",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(var_name="left_result", expr=Variable(name="shared_counter")),
        ]
        assert state_plant_leftunit.transitions[2].parent_ref().name == "LeftUnit"
        assert state_plant_leftunit.transitions[2].parent_ref().path == (
            "Plant",
            "LeftUnit",
        )
        assert state_plant_leftunit.named_functions == {}
        assert state_plant_leftunit.on_enters == []
        assert state_plant_leftunit.on_durings == []
        assert state_plant_leftunit.on_exits == []
        assert state_plant_leftunit.on_during_aspects == []
        assert state_plant_leftunit.parent_ref().name == "Plant"
        assert state_plant_leftunit.parent_ref().path == ("Plant",)
        assert state_plant_leftunit.substate_name_to_id == {"Idle": 0, "Busy": 1}
        assert state_plant_leftunit.extra_name == "Left Unit"
        assert not state_plant_leftunit.is_pseudo
        assert state_plant_leftunit.abstract_on_during_aspects == []
        assert state_plant_leftunit.abstract_on_durings == []
        assert state_plant_leftunit.abstract_on_enters == []
        assert state_plant_leftunit.abstract_on_exits == []
        assert len(state_plant_leftunit.init_transitions) == 1
        assert state_plant_leftunit.init_transitions[0].from_state == INIT_STATE
        assert state_plant_leftunit.init_transitions[0].to_state == "Idle"
        assert state_plant_leftunit.init_transitions[0].event is None
        assert state_plant_leftunit.init_transitions[0].guard is None
        assert state_plant_leftunit.init_transitions[0].effects == []
        assert state_plant_leftunit.init_transitions[0].parent_ref().name == "LeftUnit"
        assert state_plant_leftunit.init_transitions[0].parent_ref().path == (
            "Plant",
            "LeftUnit",
        )
        assert not state_plant_leftunit.is_leaf_state
        assert not state_plant_leftunit.is_root_state
        assert not state_plant_leftunit.is_stoppable
        assert state_plant_leftunit.non_abstract_on_during_aspects == []
        assert state_plant_leftunit.non_abstract_on_durings == []
        assert state_plant_leftunit.non_abstract_on_enters == []
        assert state_plant_leftunit.non_abstract_on_exits == []
        assert state_plant_leftunit.parent.name == "Plant"
        assert state_plant_leftunit.parent.path == ("Plant",)
        assert len(state_plant_leftunit.transitions_entering_children) == 1
        assert (
            state_plant_leftunit.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert state_plant_leftunit.transitions_entering_children[0].to_state == "Idle"
        assert state_plant_leftunit.transitions_entering_children[0].event is None
        assert state_plant_leftunit.transitions_entering_children[0].guard is None
        assert state_plant_leftunit.transitions_entering_children[0].effects == []
        assert (
            state_plant_leftunit.transitions_entering_children[0].parent_ref().name
            == "LeftUnit"
        )
        assert state_plant_leftunit.transitions_entering_children[
            0
        ].parent_ref().path == ("Plant", "LeftUnit")
        assert len(state_plant_leftunit.transitions_entering_children_simplified) == 1
        assert (
            state_plant_leftunit.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_plant_leftunit.transitions_entering_children_simplified[0].to_state
            == "Idle"
        )
        assert (
            state_plant_leftunit.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_plant_leftunit.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_plant_leftunit.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_plant_leftunit.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "LeftUnit"
        )
        assert state_plant_leftunit.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Plant", "LeftUnit")
        assert len(state_plant_leftunit.transitions_from) == 1
        assert state_plant_leftunit.transitions_from[0].from_state == "LeftUnit"
        assert state_plant_leftunit.transitions_from[0].to_state == "RightUnit"
        assert state_plant_leftunit.transitions_from[0].event is None
        assert state_plant_leftunit.transitions_from[0].guard is None
        assert state_plant_leftunit.transitions_from[0].effects == []
        assert state_plant_leftunit.transitions_from[0].parent_ref().name == "Plant"
        assert state_plant_leftunit.transitions_from[0].parent_ref().path == ("Plant",)
        assert len(state_plant_leftunit.transitions_to) == 1
        assert state_plant_leftunit.transitions_to[0].from_state == INIT_STATE
        assert state_plant_leftunit.transitions_to[0].to_state == "LeftUnit"
        assert state_plant_leftunit.transitions_to[0].event is None
        assert state_plant_leftunit.transitions_to[0].guard is None
        assert state_plant_leftunit.transitions_to[0].effects == []
        assert state_plant_leftunit.transitions_to[0].parent_ref().name == "Plant"
        assert state_plant_leftunit.transitions_to[0].parent_ref().path == ("Plant",)

    def test_state_plant_leftunit_to_ast_node(self, state_plant_leftunit):
        ast_node = state_plant_leftunit.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="LeftUnit",
            extra_name="Left Unit",
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
                    name="Busy",
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
                    to_state="Busy",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="shared_ready"),
                        op=">",
                        expr2=dsl_nodes.Integer(raw="0"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="left_result",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="shared_counter"),
                                op="+",
                                expr2=dsl_nodes.Name(name="left_limit"),
                            ),
                        )
                    ],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Busy",
                    to_state="Idle",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="shared_counter"),
                        op="<",
                        expr2=dsl_nodes.Name(name="left_limit"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="shared_counter",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="shared_counter"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
                        dsl_nodes.OperationAssignment(
                            name="left_result",
                            expr=dsl_nodes.Name(name="shared_counter"),
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

    def test_state_plant_leftunit_list_on_enters(self, state_plant_leftunit):
        lst = state_plant_leftunit.list_on_enters()
        assert lst == []

        lst = state_plant_leftunit.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_leftunit.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_leftunit.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_leftunit.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_plant_leftunit.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant_leftunit.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_leftunit.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant_leftunit.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_leftunit_during_aspects(self, state_plant_leftunit):
        lst = state_plant_leftunit.list_on_during_aspects()
        assert lst == []

        lst = state_plant_leftunit.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_leftunit.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_leftunit.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_leftunit.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_leftunit.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_leftunit.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_leftunit.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_leftunit.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_leftunit_idle(self, state_plant_leftunit_idle):
        assert state_plant_leftunit_idle.name == "Idle"
        assert state_plant_leftunit_idle.path == ("Plant", "LeftUnit", "Idle")
        assert sorted(state_plant_leftunit_idle.substates.keys()) == []
        assert state_plant_leftunit_idle.events == {}
        assert state_plant_leftunit_idle.transitions == []
        assert state_plant_leftunit_idle.named_functions == {}
        assert state_plant_leftunit_idle.on_enters == []
        assert state_plant_leftunit_idle.on_durings == []
        assert state_plant_leftunit_idle.on_exits == []
        assert state_plant_leftunit_idle.on_during_aspects == []
        assert state_plant_leftunit_idle.parent_ref().name == "LeftUnit"
        assert state_plant_leftunit_idle.parent_ref().path == ("Plant", "LeftUnit")
        assert state_plant_leftunit_idle.substate_name_to_id == {}
        assert state_plant_leftunit_idle.extra_name is None
        assert not state_plant_leftunit_idle.is_pseudo
        assert state_plant_leftunit_idle.abstract_on_during_aspects == []
        assert state_plant_leftunit_idle.abstract_on_durings == []
        assert state_plant_leftunit_idle.abstract_on_enters == []
        assert state_plant_leftunit_idle.abstract_on_exits == []
        assert state_plant_leftunit_idle.init_transitions == []
        assert state_plant_leftunit_idle.is_leaf_state
        assert not state_plant_leftunit_idle.is_root_state
        assert state_plant_leftunit_idle.is_stoppable
        assert state_plant_leftunit_idle.non_abstract_on_during_aspects == []
        assert state_plant_leftunit_idle.non_abstract_on_durings == []
        assert state_plant_leftunit_idle.non_abstract_on_enters == []
        assert state_plant_leftunit_idle.non_abstract_on_exits == []
        assert state_plant_leftunit_idle.parent.name == "LeftUnit"
        assert state_plant_leftunit_idle.parent.path == ("Plant", "LeftUnit")
        assert state_plant_leftunit_idle.transitions_entering_children == []
        assert (
            len(state_plant_leftunit_idle.transitions_entering_children_simplified) == 1
        )
        assert (
            state_plant_leftunit_idle.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_plant_leftunit_idle.transitions_from) == 1
        assert state_plant_leftunit_idle.transitions_from[0].from_state == "Idle"
        assert state_plant_leftunit_idle.transitions_from[0].to_state == "Busy"
        assert state_plant_leftunit_idle.transitions_from[0].event is None
        assert state_plant_leftunit_idle.transitions_from[0].guard == BinaryOp(
            x=Variable(name="shared_ready"), op=">", y=Integer(value=0)
        )
        assert state_plant_leftunit_idle.transitions_from[0].effects == [
            Operation(
                var_name="left_result",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"),
                    op="+",
                    y=Variable(name="left_limit"),
                ),
            )
        ]
        assert (
            state_plant_leftunit_idle.transitions_from[0].parent_ref().name
            == "LeftUnit"
        )
        assert state_plant_leftunit_idle.transitions_from[0].parent_ref().path == (
            "Plant",
            "LeftUnit",
        )
        assert len(state_plant_leftunit_idle.transitions_to) == 2
        assert state_plant_leftunit_idle.transitions_to[0].from_state == INIT_STATE
        assert state_plant_leftunit_idle.transitions_to[0].to_state == "Idle"
        assert state_plant_leftunit_idle.transitions_to[0].event is None
        assert state_plant_leftunit_idle.transitions_to[0].guard is None
        assert state_plant_leftunit_idle.transitions_to[0].effects == []
        assert (
            state_plant_leftunit_idle.transitions_to[0].parent_ref().name == "LeftUnit"
        )
        assert state_plant_leftunit_idle.transitions_to[0].parent_ref().path == (
            "Plant",
            "LeftUnit",
        )
        assert state_plant_leftunit_idle.transitions_to[1].from_state == "Busy"
        assert state_plant_leftunit_idle.transitions_to[1].to_state == "Idle"
        assert state_plant_leftunit_idle.transitions_to[1].event is None
        assert state_plant_leftunit_idle.transitions_to[1].guard == BinaryOp(
            x=Variable(name="shared_counter"), op="<", y=Variable(name="left_limit")
        )
        assert state_plant_leftunit_idle.transitions_to[1].effects == [
            Operation(
                var_name="shared_counter",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(var_name="left_result", expr=Variable(name="shared_counter")),
        ]
        assert (
            state_plant_leftunit_idle.transitions_to[1].parent_ref().name == "LeftUnit"
        )
        assert state_plant_leftunit_idle.transitions_to[1].parent_ref().path == (
            "Plant",
            "LeftUnit",
        )

    def test_state_plant_leftunit_idle_to_ast_node(self, state_plant_leftunit_idle):
        ast_node = state_plant_leftunit_idle.to_ast_node()
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

    def test_state_plant_leftunit_idle_list_on_enters(self, state_plant_leftunit_idle):
        lst = state_plant_leftunit_idle.list_on_enters()
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_leftunit_idle_during_aspects(self, state_plant_leftunit_idle):
        lst = state_plant_leftunit_idle.list_on_during_aspects()
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_leftunit_idle_during_aspect_recursively(
        self, state_plant_leftunit_idle
    ):
        lst = state_plant_leftunit_idle.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_plant_leftunit_idle.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_plant_leftunit_busy(self, state_plant_leftunit_busy):
        assert state_plant_leftunit_busy.name == "Busy"
        assert state_plant_leftunit_busy.path == ("Plant", "LeftUnit", "Busy")
        assert sorted(state_plant_leftunit_busy.substates.keys()) == []
        assert state_plant_leftunit_busy.events == {}
        assert state_plant_leftunit_busy.transitions == []
        assert state_plant_leftunit_busy.named_functions == {}
        assert state_plant_leftunit_busy.on_enters == []
        assert state_plant_leftunit_busy.on_durings == []
        assert state_plant_leftunit_busy.on_exits == []
        assert state_plant_leftunit_busy.on_during_aspects == []
        assert state_plant_leftunit_busy.parent_ref().name == "LeftUnit"
        assert state_plant_leftunit_busy.parent_ref().path == ("Plant", "LeftUnit")
        assert state_plant_leftunit_busy.substate_name_to_id == {}
        assert state_plant_leftunit_busy.extra_name is None
        assert not state_plant_leftunit_busy.is_pseudo
        assert state_plant_leftunit_busy.abstract_on_during_aspects == []
        assert state_plant_leftunit_busy.abstract_on_durings == []
        assert state_plant_leftunit_busy.abstract_on_enters == []
        assert state_plant_leftunit_busy.abstract_on_exits == []
        assert state_plant_leftunit_busy.init_transitions == []
        assert state_plant_leftunit_busy.is_leaf_state
        assert not state_plant_leftunit_busy.is_root_state
        assert state_plant_leftunit_busy.is_stoppable
        assert state_plant_leftunit_busy.non_abstract_on_during_aspects == []
        assert state_plant_leftunit_busy.non_abstract_on_durings == []
        assert state_plant_leftunit_busy.non_abstract_on_enters == []
        assert state_plant_leftunit_busy.non_abstract_on_exits == []
        assert state_plant_leftunit_busy.parent.name == "LeftUnit"
        assert state_plant_leftunit_busy.parent.path == ("Plant", "LeftUnit")
        assert state_plant_leftunit_busy.transitions_entering_children == []
        assert (
            len(state_plant_leftunit_busy.transitions_entering_children_simplified) == 1
        )
        assert (
            state_plant_leftunit_busy.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_plant_leftunit_busy.transitions_from) == 1
        assert state_plant_leftunit_busy.transitions_from[0].from_state == "Busy"
        assert state_plant_leftunit_busy.transitions_from[0].to_state == "Idle"
        assert state_plant_leftunit_busy.transitions_from[0].event is None
        assert state_plant_leftunit_busy.transitions_from[0].guard == BinaryOp(
            x=Variable(name="shared_counter"), op="<", y=Variable(name="left_limit")
        )
        assert state_plant_leftunit_busy.transitions_from[0].effects == [
            Operation(
                var_name="shared_counter",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(var_name="left_result", expr=Variable(name="shared_counter")),
        ]
        assert (
            state_plant_leftunit_busy.transitions_from[0].parent_ref().name
            == "LeftUnit"
        )
        assert state_plant_leftunit_busy.transitions_from[0].parent_ref().path == (
            "Plant",
            "LeftUnit",
        )
        assert len(state_plant_leftunit_busy.transitions_to) == 1
        assert state_plant_leftunit_busy.transitions_to[0].from_state == "Idle"
        assert state_plant_leftunit_busy.transitions_to[0].to_state == "Busy"
        assert state_plant_leftunit_busy.transitions_to[0].event is None
        assert state_plant_leftunit_busy.transitions_to[0].guard == BinaryOp(
            x=Variable(name="shared_ready"), op=">", y=Integer(value=0)
        )
        assert state_plant_leftunit_busy.transitions_to[0].effects == [
            Operation(
                var_name="left_result",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"),
                    op="+",
                    y=Variable(name="left_limit"),
                ),
            )
        ]
        assert (
            state_plant_leftunit_busy.transitions_to[0].parent_ref().name == "LeftUnit"
        )
        assert state_plant_leftunit_busy.transitions_to[0].parent_ref().path == (
            "Plant",
            "LeftUnit",
        )

    def test_state_plant_leftunit_busy_to_ast_node(self, state_plant_leftunit_busy):
        ast_node = state_plant_leftunit_busy.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Busy",
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

    def test_state_plant_leftunit_busy_list_on_enters(self, state_plant_leftunit_busy):
        lst = state_plant_leftunit_busy.list_on_enters()
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_leftunit_busy_during_aspects(self, state_plant_leftunit_busy):
        lst = state_plant_leftunit_busy.list_on_during_aspects()
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_leftunit_busy_during_aspect_recursively(
        self, state_plant_leftunit_busy
    ):
        lst = state_plant_leftunit_busy.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_plant_leftunit_busy.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_plant_rightunit(self, state_plant_rightunit):
        assert state_plant_rightunit.name == "RightUnit"
        assert state_plant_rightunit.path == ("Plant", "RightUnit")
        assert sorted(state_plant_rightunit.substates.keys()) == ["Busy", "Idle"]
        assert state_plant_rightunit.events == {}
        assert len(state_plant_rightunit.transitions) == 3
        assert state_plant_rightunit.transitions[0].from_state == INIT_STATE
        assert state_plant_rightunit.transitions[0].to_state == "Idle"
        assert state_plant_rightunit.transitions[0].event is None
        assert state_plant_rightunit.transitions[0].guard is None
        assert state_plant_rightunit.transitions[0].effects == []
        assert state_plant_rightunit.transitions[0].parent_ref().name == "RightUnit"
        assert state_plant_rightunit.transitions[0].parent_ref().path == (
            "Plant",
            "RightUnit",
        )
        assert state_plant_rightunit.transitions[1].from_state == "Idle"
        assert state_plant_rightunit.transitions[1].to_state == "Busy"
        assert state_plant_rightunit.transitions[1].event is None
        assert state_plant_rightunit.transitions[1].guard == BinaryOp(
            x=Variable(name="shared_ready"), op=">", y=Integer(value=0)
        )
        assert state_plant_rightunit.transitions[1].effects == [
            Operation(
                var_name="right_result",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"),
                    op="+",
                    y=Variable(name="right_limit"),
                ),
            )
        ]
        assert state_plant_rightunit.transitions[1].parent_ref().name == "RightUnit"
        assert state_plant_rightunit.transitions[1].parent_ref().path == (
            "Plant",
            "RightUnit",
        )
        assert state_plant_rightunit.transitions[2].from_state == "Busy"
        assert state_plant_rightunit.transitions[2].to_state == "Idle"
        assert state_plant_rightunit.transitions[2].event is None
        assert state_plant_rightunit.transitions[2].guard == BinaryOp(
            x=Variable(name="shared_counter"), op=">=", y=Variable(name="right_limit")
        )
        assert state_plant_rightunit.transitions[2].effects == [
            Operation(
                var_name="shared_counter",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(var_name="right_result", expr=Variable(name="shared_counter")),
        ]
        assert state_plant_rightunit.transitions[2].parent_ref().name == "RightUnit"
        assert state_plant_rightunit.transitions[2].parent_ref().path == (
            "Plant",
            "RightUnit",
        )
        assert state_plant_rightunit.named_functions == {}
        assert state_plant_rightunit.on_enters == []
        assert state_plant_rightunit.on_durings == []
        assert state_plant_rightunit.on_exits == []
        assert state_plant_rightunit.on_during_aspects == []
        assert state_plant_rightunit.parent_ref().name == "Plant"
        assert state_plant_rightunit.parent_ref().path == ("Plant",)
        assert state_plant_rightunit.substate_name_to_id == {"Idle": 0, "Busy": 1}
        assert state_plant_rightunit.extra_name == "Right Unit"
        assert not state_plant_rightunit.is_pseudo
        assert state_plant_rightunit.abstract_on_during_aspects == []
        assert state_plant_rightunit.abstract_on_durings == []
        assert state_plant_rightunit.abstract_on_enters == []
        assert state_plant_rightunit.abstract_on_exits == []
        assert len(state_plant_rightunit.init_transitions) == 1
        assert state_plant_rightunit.init_transitions[0].from_state == INIT_STATE
        assert state_plant_rightunit.init_transitions[0].to_state == "Idle"
        assert state_plant_rightunit.init_transitions[0].event is None
        assert state_plant_rightunit.init_transitions[0].guard is None
        assert state_plant_rightunit.init_transitions[0].effects == []
        assert (
            state_plant_rightunit.init_transitions[0].parent_ref().name == "RightUnit"
        )
        assert state_plant_rightunit.init_transitions[0].parent_ref().path == (
            "Plant",
            "RightUnit",
        )
        assert not state_plant_rightunit.is_leaf_state
        assert not state_plant_rightunit.is_root_state
        assert not state_plant_rightunit.is_stoppable
        assert state_plant_rightunit.non_abstract_on_during_aspects == []
        assert state_plant_rightunit.non_abstract_on_durings == []
        assert state_plant_rightunit.non_abstract_on_enters == []
        assert state_plant_rightunit.non_abstract_on_exits == []
        assert state_plant_rightunit.parent.name == "Plant"
        assert state_plant_rightunit.parent.path == ("Plant",)
        assert len(state_plant_rightunit.transitions_entering_children) == 1
        assert (
            state_plant_rightunit.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert state_plant_rightunit.transitions_entering_children[0].to_state == "Idle"
        assert state_plant_rightunit.transitions_entering_children[0].event is None
        assert state_plant_rightunit.transitions_entering_children[0].guard is None
        assert state_plant_rightunit.transitions_entering_children[0].effects == []
        assert (
            state_plant_rightunit.transitions_entering_children[0].parent_ref().name
            == "RightUnit"
        )
        assert state_plant_rightunit.transitions_entering_children[
            0
        ].parent_ref().path == ("Plant", "RightUnit")
        assert len(state_plant_rightunit.transitions_entering_children_simplified) == 1
        assert (
            state_plant_rightunit.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_plant_rightunit.transitions_entering_children_simplified[0].to_state
            == "Idle"
        )
        assert (
            state_plant_rightunit.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_plant_rightunit.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_plant_rightunit.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_plant_rightunit.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "RightUnit"
        )
        assert state_plant_rightunit.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Plant", "RightUnit")
        assert state_plant_rightunit.transitions_from == []
        assert len(state_plant_rightunit.transitions_to) == 1
        assert state_plant_rightunit.transitions_to[0].from_state == "LeftUnit"
        assert state_plant_rightunit.transitions_to[0].to_state == "RightUnit"
        assert state_plant_rightunit.transitions_to[0].event is None
        assert state_plant_rightunit.transitions_to[0].guard is None
        assert state_plant_rightunit.transitions_to[0].effects == []
        assert state_plant_rightunit.transitions_to[0].parent_ref().name == "Plant"
        assert state_plant_rightunit.transitions_to[0].parent_ref().path == ("Plant",)

    def test_state_plant_rightunit_to_ast_node(self, state_plant_rightunit):
        ast_node = state_plant_rightunit.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="RightUnit",
            extra_name="Right Unit",
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
                    name="Busy",
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
                    to_state="Busy",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="shared_ready"),
                        op=">",
                        expr2=dsl_nodes.Integer(raw="0"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="right_result",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="shared_counter"),
                                op="+",
                                expr2=dsl_nodes.Name(name="right_limit"),
                            ),
                        )
                    ],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Busy",
                    to_state="Idle",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="shared_counter"),
                        op=">=",
                        expr2=dsl_nodes.Name(name="right_limit"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="shared_counter",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="shared_counter"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
                        dsl_nodes.OperationAssignment(
                            name="right_result",
                            expr=dsl_nodes.Name(name="shared_counter"),
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

    def test_state_plant_rightunit_list_on_enters(self, state_plant_rightunit):
        lst = state_plant_rightunit.list_on_enters()
        assert lst == []

        lst = state_plant_rightunit.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_rightunit.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_rightunit.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_rightunit.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_plant_rightunit.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_plant_rightunit.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_rightunit.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_plant_rightunit.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_rightunit_during_aspects(self, state_plant_rightunit):
        lst = state_plant_rightunit.list_on_during_aspects()
        assert lst == []

        lst = state_plant_rightunit.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_rightunit.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_rightunit.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_rightunit.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_rightunit.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_rightunit.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_rightunit.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_rightunit.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_rightunit_idle(self, state_plant_rightunit_idle):
        assert state_plant_rightunit_idle.name == "Idle"
        assert state_plant_rightunit_idle.path == ("Plant", "RightUnit", "Idle")
        assert sorted(state_plant_rightunit_idle.substates.keys()) == []
        assert state_plant_rightunit_idle.events == {}
        assert state_plant_rightunit_idle.transitions == []
        assert state_plant_rightunit_idle.named_functions == {}
        assert state_plant_rightunit_idle.on_enters == []
        assert state_plant_rightunit_idle.on_durings == []
        assert state_plant_rightunit_idle.on_exits == []
        assert state_plant_rightunit_idle.on_during_aspects == []
        assert state_plant_rightunit_idle.parent_ref().name == "RightUnit"
        assert state_plant_rightunit_idle.parent_ref().path == ("Plant", "RightUnit")
        assert state_plant_rightunit_idle.substate_name_to_id == {}
        assert state_plant_rightunit_idle.extra_name is None
        assert not state_plant_rightunit_idle.is_pseudo
        assert state_plant_rightunit_idle.abstract_on_during_aspects == []
        assert state_plant_rightunit_idle.abstract_on_durings == []
        assert state_plant_rightunit_idle.abstract_on_enters == []
        assert state_plant_rightunit_idle.abstract_on_exits == []
        assert state_plant_rightunit_idle.init_transitions == []
        assert state_plant_rightunit_idle.is_leaf_state
        assert not state_plant_rightunit_idle.is_root_state
        assert state_plant_rightunit_idle.is_stoppable
        assert state_plant_rightunit_idle.non_abstract_on_during_aspects == []
        assert state_plant_rightunit_idle.non_abstract_on_durings == []
        assert state_plant_rightunit_idle.non_abstract_on_enters == []
        assert state_plant_rightunit_idle.non_abstract_on_exits == []
        assert state_plant_rightunit_idle.parent.name == "RightUnit"
        assert state_plant_rightunit_idle.parent.path == ("Plant", "RightUnit")
        assert state_plant_rightunit_idle.transitions_entering_children == []
        assert (
            len(state_plant_rightunit_idle.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_plant_rightunit_idle.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_plant_rightunit_idle.transitions_from) == 1
        assert state_plant_rightunit_idle.transitions_from[0].from_state == "Idle"
        assert state_plant_rightunit_idle.transitions_from[0].to_state == "Busy"
        assert state_plant_rightunit_idle.transitions_from[0].event is None
        assert state_plant_rightunit_idle.transitions_from[0].guard == BinaryOp(
            x=Variable(name="shared_ready"), op=">", y=Integer(value=0)
        )
        assert state_plant_rightunit_idle.transitions_from[0].effects == [
            Operation(
                var_name="right_result",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"),
                    op="+",
                    y=Variable(name="right_limit"),
                ),
            )
        ]
        assert (
            state_plant_rightunit_idle.transitions_from[0].parent_ref().name
            == "RightUnit"
        )
        assert state_plant_rightunit_idle.transitions_from[0].parent_ref().path == (
            "Plant",
            "RightUnit",
        )
        assert len(state_plant_rightunit_idle.transitions_to) == 2
        assert state_plant_rightunit_idle.transitions_to[0].from_state == INIT_STATE
        assert state_plant_rightunit_idle.transitions_to[0].to_state == "Idle"
        assert state_plant_rightunit_idle.transitions_to[0].event is None
        assert state_plant_rightunit_idle.transitions_to[0].guard is None
        assert state_plant_rightunit_idle.transitions_to[0].effects == []
        assert (
            state_plant_rightunit_idle.transitions_to[0].parent_ref().name
            == "RightUnit"
        )
        assert state_plant_rightunit_idle.transitions_to[0].parent_ref().path == (
            "Plant",
            "RightUnit",
        )
        assert state_plant_rightunit_idle.transitions_to[1].from_state == "Busy"
        assert state_plant_rightunit_idle.transitions_to[1].to_state == "Idle"
        assert state_plant_rightunit_idle.transitions_to[1].event is None
        assert state_plant_rightunit_idle.transitions_to[1].guard == BinaryOp(
            x=Variable(name="shared_counter"), op=">=", y=Variable(name="right_limit")
        )
        assert state_plant_rightunit_idle.transitions_to[1].effects == [
            Operation(
                var_name="shared_counter",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(var_name="right_result", expr=Variable(name="shared_counter")),
        ]
        assert (
            state_plant_rightunit_idle.transitions_to[1].parent_ref().name
            == "RightUnit"
        )
        assert state_plant_rightunit_idle.transitions_to[1].parent_ref().path == (
            "Plant",
            "RightUnit",
        )

    def test_state_plant_rightunit_idle_to_ast_node(self, state_plant_rightunit_idle):
        ast_node = state_plant_rightunit_idle.to_ast_node()
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

    def test_state_plant_rightunit_idle_list_on_enters(
        self, state_plant_rightunit_idle
    ):
        lst = state_plant_rightunit_idle.list_on_enters()
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_rightunit_idle_during_aspects(
        self, state_plant_rightunit_idle
    ):
        lst = state_plant_rightunit_idle.list_on_during_aspects()
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_rightunit_idle_during_aspect_recursively(
        self, state_plant_rightunit_idle
    ):
        lst = state_plant_rightunit_idle.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_plant_rightunit_idle.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_plant_rightunit_busy(self, state_plant_rightunit_busy):
        assert state_plant_rightunit_busy.name == "Busy"
        assert state_plant_rightunit_busy.path == ("Plant", "RightUnit", "Busy")
        assert sorted(state_plant_rightunit_busy.substates.keys()) == []
        assert state_plant_rightunit_busy.events == {}
        assert state_plant_rightunit_busy.transitions == []
        assert state_plant_rightunit_busy.named_functions == {}
        assert state_plant_rightunit_busy.on_enters == []
        assert state_plant_rightunit_busy.on_durings == []
        assert state_plant_rightunit_busy.on_exits == []
        assert state_plant_rightunit_busy.on_during_aspects == []
        assert state_plant_rightunit_busy.parent_ref().name == "RightUnit"
        assert state_plant_rightunit_busy.parent_ref().path == ("Plant", "RightUnit")
        assert state_plant_rightunit_busy.substate_name_to_id == {}
        assert state_plant_rightunit_busy.extra_name is None
        assert not state_plant_rightunit_busy.is_pseudo
        assert state_plant_rightunit_busy.abstract_on_during_aspects == []
        assert state_plant_rightunit_busy.abstract_on_durings == []
        assert state_plant_rightunit_busy.abstract_on_enters == []
        assert state_plant_rightunit_busy.abstract_on_exits == []
        assert state_plant_rightunit_busy.init_transitions == []
        assert state_plant_rightunit_busy.is_leaf_state
        assert not state_plant_rightunit_busy.is_root_state
        assert state_plant_rightunit_busy.is_stoppable
        assert state_plant_rightunit_busy.non_abstract_on_during_aspects == []
        assert state_plant_rightunit_busy.non_abstract_on_durings == []
        assert state_plant_rightunit_busy.non_abstract_on_enters == []
        assert state_plant_rightunit_busy.non_abstract_on_exits == []
        assert state_plant_rightunit_busy.parent.name == "RightUnit"
        assert state_plant_rightunit_busy.parent.path == ("Plant", "RightUnit")
        assert state_plant_rightunit_busy.transitions_entering_children == []
        assert (
            len(state_plant_rightunit_busy.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_plant_rightunit_busy.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_plant_rightunit_busy.transitions_from) == 1
        assert state_plant_rightunit_busy.transitions_from[0].from_state == "Busy"
        assert state_plant_rightunit_busy.transitions_from[0].to_state == "Idle"
        assert state_plant_rightunit_busy.transitions_from[0].event is None
        assert state_plant_rightunit_busy.transitions_from[0].guard == BinaryOp(
            x=Variable(name="shared_counter"), op=">=", y=Variable(name="right_limit")
        )
        assert state_plant_rightunit_busy.transitions_from[0].effects == [
            Operation(
                var_name="shared_counter",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"), op="+", y=Integer(value=1)
                ),
            ),
            Operation(var_name="right_result", expr=Variable(name="shared_counter")),
        ]
        assert (
            state_plant_rightunit_busy.transitions_from[0].parent_ref().name
            == "RightUnit"
        )
        assert state_plant_rightunit_busy.transitions_from[0].parent_ref().path == (
            "Plant",
            "RightUnit",
        )
        assert len(state_plant_rightunit_busy.transitions_to) == 1
        assert state_plant_rightunit_busy.transitions_to[0].from_state == "Idle"
        assert state_plant_rightunit_busy.transitions_to[0].to_state == "Busy"
        assert state_plant_rightunit_busy.transitions_to[0].event is None
        assert state_plant_rightunit_busy.transitions_to[0].guard == BinaryOp(
            x=Variable(name="shared_ready"), op=">", y=Integer(value=0)
        )
        assert state_plant_rightunit_busy.transitions_to[0].effects == [
            Operation(
                var_name="right_result",
                expr=BinaryOp(
                    x=Variable(name="shared_counter"),
                    op="+",
                    y=Variable(name="right_limit"),
                ),
            )
        ]
        assert (
            state_plant_rightunit_busy.transitions_to[0].parent_ref().name
            == "RightUnit"
        )
        assert state_plant_rightunit_busy.transitions_to[0].parent_ref().path == (
            "Plant",
            "RightUnit",
        )

    def test_state_plant_rightunit_busy_to_ast_node(self, state_plant_rightunit_busy):
        ast_node = state_plant_rightunit_busy.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Busy",
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

    def test_state_plant_rightunit_busy_list_on_enters(
        self, state_plant_rightunit_busy
    ):
        lst = state_plant_rightunit_busy.list_on_enters()
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_plant_rightunit_busy_during_aspects(
        self, state_plant_rightunit_busy
    ):
        lst = state_plant_rightunit_busy.list_on_during_aspects()
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_plant_rightunit_busy_during_aspect_recursively(
        self, state_plant_rightunit_busy
    ):
        lst = state_plant_rightunit_busy.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_plant_rightunit_busy.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int shared_counter = 100;
def int shared_ready = 1;
def int left_limit = 5;
def int right_limit = 6;
def int left_result = 0;
def int right_result = 0;
state Plant {
    state LeftUnit named 'Left Unit' {
        state Idle;
        state Busy;
        [*] -> Idle;
        Idle -> Busy : if [shared_ready > 0] effect {
            left_result = shared_counter + left_limit;
        }
        Busy -> Idle : if [shared_counter < left_limit] effect {
            shared_counter = shared_counter + 1;
            left_result = shared_counter;
        }
    }
    state RightUnit named 'Right Unit' {
        state Idle;
        state Busy;
        [*] -> Idle;
        Idle -> Busy : if [shared_ready > 0] effect {
            right_result = shared_counter + right_limit;
        }
        Busy -> Idle : if [shared_counter >= right_limit] effect {
            shared_counter = shared_counter + 1;
            right_result = shared_counter;
        }
    }
    [*] -> LeftUnit;
    LeftUnit -> RightUnit;
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
| shared_counter | int | 100 |
| shared_ready | int | 1 |
| left_limit | int | 5 |
| right_limit | int | 6 |
| left_result | int | 0 |
| right_result | int | 0 |
endlegend

state "Plant" as plant <<composite>> {
    state "Left Unit" as plant__left_unit <<composite>> {
        state "Idle" as plant__left_unit__idle
        state "Busy" as plant__left_unit__busy
        [*] --> plant__left_unit__idle
        plant__left_unit__idle --> plant__left_unit__busy : shared_ready > 0
        note on link
        effect {
            left_result = shared_counter + left_limit;
        }
        end note
        plant__left_unit__busy --> plant__left_unit__idle : shared_counter < left_limit
        note on link
        effect {
            shared_counter = shared_counter + 1;
            left_result = shared_counter;
        }
        end note
    }
    state "Right Unit" as plant__right_unit <<composite>> {
        state "Idle" as plant__right_unit__idle
        state "Busy" as plant__right_unit__busy
        [*] --> plant__right_unit__idle
        plant__right_unit__idle --> plant__right_unit__busy : shared_ready > 0
        note on link
        effect {
            right_result = shared_counter + right_limit;
        }
        end note
        plant__right_unit__busy --> plant__right_unit__idle : shared_counter >= right_limit
        note on link
        effect {
            shared_counter = shared_counter + 1;
            right_result = shared_counter;
        }
        end note
    }
    [*] --> plant__left_unit
    plant__left_unit --> plant__right_unit
}
[*] --> plant
plant --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml(options="full")),
        )
