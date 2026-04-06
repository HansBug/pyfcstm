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
state Lab {
    import "./modules/worker.fcstm" as Worker named "Mapping Matrix" {
        def counter -> exact_counter;
        def {status_flag, a, b, c} -> set_*;
        def sensor_* -> sensor_$1;
        def a_*_b_* -> pair_${1}_${2}_${0};
        def * -> fallback_$0;
    }
    [*] -> Worker;
}
        """,
        )
        _write_text_file(
            "modules/worker.fcstm",
            """
def int counter = 1;
def int status_flag = 2;
def int sensor_temp = 3;
def int a_main_b_low = 4;
def int timeout = 5;
def int a = 6;
def int b = 7;
def int c = 8;

state WorkerRoot named "Matrix Worker" {
    state Idle {
        during {
            counter = counter + status_flag;
            status_flag = status_flag + a + b + c;
            sensor_temp = sensor_temp + 1;
        }
    }
    state Active {
        during {
            timeout = timeout + a_main_b_low;
        }
    }
    [*] -> Idle;
    Idle -> Active : if [sensor_temp > status_flag];
    Active -> Idle : if [timeout > a_main_b_low] effect {
        counter = counter + timeout;
    }
}
        """,
        )
        entry_file = pathlib.Path("main.fcstm")
        ast_node = parse_state_machine_dsl(entry_file.read_text(encoding="utf-8"))
        model = parse_dsl_node_to_state_machine(ast_node, path=entry_file)
        return model


@pytest.fixture()
def state_lab(model):
    return model.root_state


@pytest.fixture()
def state_lab_worker(state_lab):
    return state_lab.substates["Worker"]


@pytest.fixture()
def state_lab_worker_idle(state_lab_worker):
    return state_lab_worker.substates["Idle"]


@pytest.fixture()
def state_lab_worker_active(state_lab_worker):
    return state_lab_worker.substates["Active"]


@pytest.mark.unittest
class TestModelStateLab:
    def test_model(self, model):
        assert model.defines == {
            "exact_counter": VarDefine(
                name="exact_counter", type="int", init=Integer(value=1)
            ),
            "set_status_flag": VarDefine(
                name="set_status_flag", type="int", init=Integer(value=2)
            ),
            "sensor_temp": VarDefine(
                name="sensor_temp", type="int", init=Integer(value=3)
            ),
            "pair_main_low_a_main_b_low": VarDefine(
                name="pair_main_low_a_main_b_low", type="int", init=Integer(value=4)
            ),
            "fallback_timeout": VarDefine(
                name="fallback_timeout", type="int", init=Integer(value=5)
            ),
            "set_a": VarDefine(name="set_a", type="int", init=Integer(value=6)),
            "set_b": VarDefine(name="set_b", type="int", init=Integer(value=7)),
            "set_c": VarDefine(name="set_c", type="int", init=Integer(value=8)),
        }
        assert model.root_state.name == "Lab"
        assert model.root_state.path == ("Lab",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="exact_counter", type="int", expr=dsl_nodes.Integer(raw="1")
            ),
            dsl_nodes.DefAssignment(
                name="set_status_flag", type="int", expr=dsl_nodes.Integer(raw="2")
            ),
            dsl_nodes.DefAssignment(
                name="sensor_temp", type="int", expr=dsl_nodes.Integer(raw="3")
            ),
            dsl_nodes.DefAssignment(
                name="pair_main_low_a_main_b_low",
                type="int",
                expr=dsl_nodes.Integer(raw="4"),
            ),
            dsl_nodes.DefAssignment(
                name="fallback_timeout", type="int", expr=dsl_nodes.Integer(raw="5")
            ),
            dsl_nodes.DefAssignment(
                name="set_a", type="int", expr=dsl_nodes.Integer(raw="6")
            ),
            dsl_nodes.DefAssignment(
                name="set_b", type="int", expr=dsl_nodes.Integer(raw="7")
            ),
            dsl_nodes.DefAssignment(
                name="set_c", type="int", expr=dsl_nodes.Integer(raw="8")
            ),
        ]
        assert ast_node.root_state.name == "Lab"

    def test_state_lab(self, state_lab):
        assert state_lab.name == "Lab"
        assert state_lab.path == ("Lab",)
        assert sorted(state_lab.substates.keys()) == ["Worker"]
        assert state_lab.events == {}
        assert len(state_lab.transitions) == 1
        assert state_lab.transitions[0].from_state == INIT_STATE
        assert state_lab.transitions[0].to_state == "Worker"
        assert state_lab.transitions[0].event is None
        assert state_lab.transitions[0].guard is None
        assert state_lab.transitions[0].effects == []
        assert state_lab.transitions[0].parent_ref().name == "Lab"
        assert state_lab.transitions[0].parent_ref().path == ("Lab",)
        assert state_lab.named_functions == {}
        assert state_lab.on_enters == []
        assert state_lab.on_durings == []
        assert state_lab.on_exits == []
        assert state_lab.on_during_aspects == []
        assert state_lab.parent_ref is None
        assert state_lab.substate_name_to_id == {"Worker": 0}
        assert state_lab.extra_name is None
        assert not state_lab.is_pseudo
        assert state_lab.abstract_on_during_aspects == []
        assert state_lab.abstract_on_durings == []
        assert state_lab.abstract_on_enters == []
        assert state_lab.abstract_on_exits == []
        assert len(state_lab.init_transitions) == 1
        assert state_lab.init_transitions[0].from_state == INIT_STATE
        assert state_lab.init_transitions[0].to_state == "Worker"
        assert state_lab.init_transitions[0].event is None
        assert state_lab.init_transitions[0].guard is None
        assert state_lab.init_transitions[0].effects == []
        assert state_lab.init_transitions[0].parent_ref().name == "Lab"
        assert state_lab.init_transitions[0].parent_ref().path == ("Lab",)
        assert not state_lab.is_leaf_state
        assert state_lab.is_root_state
        assert not state_lab.is_stoppable
        assert state_lab.non_abstract_on_during_aspects == []
        assert state_lab.non_abstract_on_durings == []
        assert state_lab.non_abstract_on_enters == []
        assert state_lab.non_abstract_on_exits == []
        assert state_lab.parent is None
        assert len(state_lab.transitions_entering_children) == 1
        assert state_lab.transitions_entering_children[0].from_state == INIT_STATE
        assert state_lab.transitions_entering_children[0].to_state == "Worker"
        assert state_lab.transitions_entering_children[0].event is None
        assert state_lab.transitions_entering_children[0].guard is None
        assert state_lab.transitions_entering_children[0].effects == []
        assert state_lab.transitions_entering_children[0].parent_ref().name == "Lab"
        assert state_lab.transitions_entering_children[0].parent_ref().path == ("Lab",)
        assert len(state_lab.transitions_entering_children_simplified) == 1
        assert (
            state_lab.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_lab.transitions_entering_children_simplified[0].to_state == "Worker"
        )
        assert state_lab.transitions_entering_children_simplified[0].event is None
        assert state_lab.transitions_entering_children_simplified[0].guard is None
        assert state_lab.transitions_entering_children_simplified[0].effects == []
        assert (
            state_lab.transitions_entering_children_simplified[0].parent_ref().name
            == "Lab"
        )
        assert state_lab.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Lab",)
        assert len(state_lab.transitions_from) == 1
        assert state_lab.transitions_from[0].from_state == "Lab"
        assert state_lab.transitions_from[0].to_state == EXIT_STATE
        assert state_lab.transitions_from[0].event is None
        assert state_lab.transitions_from[0].guard is None
        assert state_lab.transitions_from[0].effects == []
        assert state_lab.transitions_from[0].parent_ref is None
        assert len(state_lab.transitions_to) == 1
        assert state_lab.transitions_to[0].from_state == INIT_STATE
        assert state_lab.transitions_to[0].to_state == "Lab"
        assert state_lab.transitions_to[0].event is None
        assert state_lab.transitions_to[0].guard is None
        assert state_lab.transitions_to[0].effects == []
        assert state_lab.transitions_to[0].parent_ref is None

    def test_state_lab_to_ast_node(self, state_lab):
        ast_node = state_lab.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Lab",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Worker",
                    extra_name="Mapping Matrix",
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
                            durings=[
                                dsl_nodes.DuringOperations(
                                    aspect=None,
                                    operations=[
                                        dsl_nodes.OperationAssignment(
                                            name="exact_counter",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(
                                                    name="exact_counter"
                                                ),
                                                op="+",
                                                expr2=dsl_nodes.Name(
                                                    name="set_status_flag"
                                                ),
                                            ),
                                        ),
                                        dsl_nodes.OperationAssignment(
                                            name="set_status_flag",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.BinaryOp(
                                                    expr1=dsl_nodes.BinaryOp(
                                                        expr1=dsl_nodes.Name(
                                                            name="set_status_flag"
                                                        ),
                                                        op="+",
                                                        expr2=dsl_nodes.Name(
                                                            name="set_a"
                                                        ),
                                                    ),
                                                    op="+",
                                                    expr2=dsl_nodes.Name(name="set_b"),
                                                ),
                                                op="+",
                                                expr2=dsl_nodes.Name(name="set_c"),
                                            ),
                                        ),
                                        dsl_nodes.OperationAssignment(
                                            name="sensor_temp",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(
                                                    name="sensor_temp"
                                                ),
                                                op="+",
                                                expr2=dsl_nodes.Integer(raw="1"),
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
                        ),
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
                                            name="fallback_timeout",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(
                                                    name="fallback_timeout"
                                                ),
                                                op="+",
                                                expr2=dsl_nodes.Name(
                                                    name="pair_main_low_a_main_b_low"
                                                ),
                                            ),
                                        )
                                    ],
                                    name=None,
                                )
                            ],
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
                            to_state="Active",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="sensor_temp"),
                                op=">",
                                expr2=dsl_nodes.Name(name="set_status_flag"),
                            ),
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Active",
                            to_state="Idle",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="fallback_timeout"),
                                op=">",
                                expr2=dsl_nodes.Name(name="pair_main_low_a_main_b_low"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="exact_counter",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="exact_counter"),
                                        op="+",
                                        expr2=dsl_nodes.Name(name="fallback_timeout"),
                                    ),
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

    def test_state_lab_list_on_enters(self, state_lab):
        lst = state_lab.list_on_enters()
        assert lst == []

        lst = state_lab.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_lab.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_lab.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_lab.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_lab.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_lab.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_lab.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_lab.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_lab_during_aspects(self, state_lab):
        lst = state_lab.list_on_during_aspects()
        assert lst == []

        lst = state_lab.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lab.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lab.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lab.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_lab.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_lab.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lab.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_lab.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_lab_worker(self, state_lab_worker):
        assert state_lab_worker.name == "Worker"
        assert state_lab_worker.path == ("Lab", "Worker")
        assert sorted(state_lab_worker.substates.keys()) == ["Active", "Idle"]
        assert state_lab_worker.events == {}
        assert len(state_lab_worker.transitions) == 3
        assert state_lab_worker.transitions[0].from_state == INIT_STATE
        assert state_lab_worker.transitions[0].to_state == "Idle"
        assert state_lab_worker.transitions[0].event is None
        assert state_lab_worker.transitions[0].guard is None
        assert state_lab_worker.transitions[0].effects == []
        assert state_lab_worker.transitions[0].parent_ref().name == "Worker"
        assert state_lab_worker.transitions[0].parent_ref().path == ("Lab", "Worker")
        assert state_lab_worker.transitions[1].from_state == "Idle"
        assert state_lab_worker.transitions[1].to_state == "Active"
        assert state_lab_worker.transitions[1].event is None
        assert state_lab_worker.transitions[1].guard == BinaryOp(
            x=Variable(name="sensor_temp"), op=">", y=Variable(name="set_status_flag")
        )
        assert state_lab_worker.transitions[1].effects == []
        assert state_lab_worker.transitions[1].parent_ref().name == "Worker"
        assert state_lab_worker.transitions[1].parent_ref().path == ("Lab", "Worker")
        assert state_lab_worker.transitions[2].from_state == "Active"
        assert state_lab_worker.transitions[2].to_state == "Idle"
        assert state_lab_worker.transitions[2].event is None
        assert state_lab_worker.transitions[2].guard == BinaryOp(
            x=Variable(name="fallback_timeout"),
            op=">",
            y=Variable(name="pair_main_low_a_main_b_low"),
        )
        assert state_lab_worker.transitions[2].effects == [
            Operation(
                var_name="exact_counter",
                expr=BinaryOp(
                    x=Variable(name="exact_counter"),
                    op="+",
                    y=Variable(name="fallback_timeout"),
                ),
            )
        ]
        assert state_lab_worker.transitions[2].parent_ref().name == "Worker"
        assert state_lab_worker.transitions[2].parent_ref().path == ("Lab", "Worker")
        assert state_lab_worker.named_functions == {}
        assert state_lab_worker.on_enters == []
        assert state_lab_worker.on_durings == []
        assert state_lab_worker.on_exits == []
        assert state_lab_worker.on_during_aspects == []
        assert state_lab_worker.parent_ref().name == "Lab"
        assert state_lab_worker.parent_ref().path == ("Lab",)
        assert state_lab_worker.substate_name_to_id == {"Idle": 0, "Active": 1}
        assert state_lab_worker.extra_name == "Mapping Matrix"
        assert not state_lab_worker.is_pseudo
        assert state_lab_worker.abstract_on_during_aspects == []
        assert state_lab_worker.abstract_on_durings == []
        assert state_lab_worker.abstract_on_enters == []
        assert state_lab_worker.abstract_on_exits == []
        assert len(state_lab_worker.init_transitions) == 1
        assert state_lab_worker.init_transitions[0].from_state == INIT_STATE
        assert state_lab_worker.init_transitions[0].to_state == "Idle"
        assert state_lab_worker.init_transitions[0].event is None
        assert state_lab_worker.init_transitions[0].guard is None
        assert state_lab_worker.init_transitions[0].effects == []
        assert state_lab_worker.init_transitions[0].parent_ref().name == "Worker"
        assert state_lab_worker.init_transitions[0].parent_ref().path == (
            "Lab",
            "Worker",
        )
        assert not state_lab_worker.is_leaf_state
        assert not state_lab_worker.is_root_state
        assert not state_lab_worker.is_stoppable
        assert state_lab_worker.non_abstract_on_during_aspects == []
        assert state_lab_worker.non_abstract_on_durings == []
        assert state_lab_worker.non_abstract_on_enters == []
        assert state_lab_worker.non_abstract_on_exits == []
        assert state_lab_worker.parent.name == "Lab"
        assert state_lab_worker.parent.path == ("Lab",)
        assert len(state_lab_worker.transitions_entering_children) == 1
        assert (
            state_lab_worker.transitions_entering_children[0].from_state == INIT_STATE
        )
        assert state_lab_worker.transitions_entering_children[0].to_state == "Idle"
        assert state_lab_worker.transitions_entering_children[0].event is None
        assert state_lab_worker.transitions_entering_children[0].guard is None
        assert state_lab_worker.transitions_entering_children[0].effects == []
        assert (
            state_lab_worker.transitions_entering_children[0].parent_ref().name
            == "Worker"
        )
        assert state_lab_worker.transitions_entering_children[0].parent_ref().path == (
            "Lab",
            "Worker",
        )
        assert len(state_lab_worker.transitions_entering_children_simplified) == 1
        assert (
            state_lab_worker.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_lab_worker.transitions_entering_children_simplified[0].to_state
            == "Idle"
        )
        assert (
            state_lab_worker.transitions_entering_children_simplified[0].event is None
        )
        assert (
            state_lab_worker.transitions_entering_children_simplified[0].guard is None
        )
        assert (
            state_lab_worker.transitions_entering_children_simplified[0].effects == []
        )
        assert (
            state_lab_worker.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "Worker"
        )
        assert state_lab_worker.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("Lab", "Worker")
        assert state_lab_worker.transitions_from == []
        assert len(state_lab_worker.transitions_to) == 1
        assert state_lab_worker.transitions_to[0].from_state == INIT_STATE
        assert state_lab_worker.transitions_to[0].to_state == "Worker"
        assert state_lab_worker.transitions_to[0].event is None
        assert state_lab_worker.transitions_to[0].guard is None
        assert state_lab_worker.transitions_to[0].effects == []
        assert state_lab_worker.transitions_to[0].parent_ref().name == "Lab"
        assert state_lab_worker.transitions_to[0].parent_ref().path == ("Lab",)

    def test_state_lab_worker_to_ast_node(self, state_lab_worker):
        ast_node = state_lab_worker.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Worker",
            extra_name="Mapping Matrix",
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
                    durings=[
                        dsl_nodes.DuringOperations(
                            aspect=None,
                            operations=[
                                dsl_nodes.OperationAssignment(
                                    name="exact_counter",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="exact_counter"),
                                        op="+",
                                        expr2=dsl_nodes.Name(name="set_status_flag"),
                                    ),
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="set_status_flag",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.BinaryOp(
                                            expr1=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Name(
                                                    name="set_status_flag"
                                                ),
                                                op="+",
                                                expr2=dsl_nodes.Name(name="set_a"),
                                            ),
                                            op="+",
                                            expr2=dsl_nodes.Name(name="set_b"),
                                        ),
                                        op="+",
                                        expr2=dsl_nodes.Name(name="set_c"),
                                    ),
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="sensor_temp",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="sensor_temp"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
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
                ),
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
                                    name="fallback_timeout",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="fallback_timeout"),
                                        op="+",
                                        expr2=dsl_nodes.Name(
                                            name="pair_main_low_a_main_b_low"
                                        ),
                                    ),
                                )
                            ],
                            name=None,
                        )
                    ],
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
                    to_state="Active",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="sensor_temp"),
                        op=">",
                        expr2=dsl_nodes.Name(name="set_status_flag"),
                    ),
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Active",
                    to_state="Idle",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="fallback_timeout"),
                        op=">",
                        expr2=dsl_nodes.Name(name="pair_main_low_a_main_b_low"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="exact_counter",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="exact_counter"),
                                op="+",
                                expr2=dsl_nodes.Name(name="fallback_timeout"),
                            ),
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

    def test_state_lab_worker_list_on_enters(self, state_lab_worker):
        lst = state_lab_worker.list_on_enters()
        assert lst == []

        lst = state_lab_worker.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_lab_worker.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_lab_worker.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_lab_worker.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_lab_worker.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_lab_worker.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_lab_worker.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_lab_worker.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_lab_worker_during_aspects(self, state_lab_worker):
        lst = state_lab_worker.list_on_during_aspects()
        assert lst == []

        lst = state_lab_worker.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lab_worker.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lab_worker.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lab_worker.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_lab_worker.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_lab_worker.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lab_worker.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_lab_worker.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_lab_worker_idle(self, state_lab_worker_idle):
        assert state_lab_worker_idle.name == "Idle"
        assert state_lab_worker_idle.path == ("Lab", "Worker", "Idle")
        assert sorted(state_lab_worker_idle.substates.keys()) == []
        assert state_lab_worker_idle.events == {}
        assert state_lab_worker_idle.transitions == []
        assert state_lab_worker_idle.named_functions == {}
        assert state_lab_worker_idle.on_enters == []
        assert len(state_lab_worker_idle.on_durings) == 1
        assert state_lab_worker_idle.on_durings[0].stage == "during"
        assert state_lab_worker_idle.on_durings[0].aspect is None
        assert state_lab_worker_idle.on_durings[0].name is None
        assert state_lab_worker_idle.on_durings[0].doc is None
        assert state_lab_worker_idle.on_durings[0].operations == [
            Operation(
                var_name="exact_counter",
                expr=BinaryOp(
                    x=Variable(name="exact_counter"),
                    op="+",
                    y=Variable(name="set_status_flag"),
                ),
            ),
            Operation(
                var_name="set_status_flag",
                expr=BinaryOp(
                    x=BinaryOp(
                        x=BinaryOp(
                            x=Variable(name="set_status_flag"),
                            op="+",
                            y=Variable(name="set_a"),
                        ),
                        op="+",
                        y=Variable(name="set_b"),
                    ),
                    op="+",
                    y=Variable(name="set_c"),
                ),
            ),
            Operation(
                var_name="sensor_temp",
                expr=BinaryOp(
                    x=Variable(name="sensor_temp"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert not state_lab_worker_idle.on_durings[0].is_abstract
        assert state_lab_worker_idle.on_durings[0].state_path == (
            "Lab",
            "Worker",
            "Idle",
            None,
        )
        assert state_lab_worker_idle.on_durings[0].ref is None
        assert state_lab_worker_idle.on_durings[0].ref_state_path is None
        assert state_lab_worker_idle.on_durings[0].parent_ref().name == "Idle"
        assert state_lab_worker_idle.on_durings[0].parent_ref().path == (
            "Lab",
            "Worker",
            "Idle",
        )
        assert (
            state_lab_worker_idle.on_durings[0].func_name == "Lab.Worker.Idle.<unnamed>"
        )
        assert not state_lab_worker_idle.on_durings[0].is_aspect
        assert not state_lab_worker_idle.on_durings[0].is_ref
        assert state_lab_worker_idle.on_durings[0].parent.name == "Idle"
        assert state_lab_worker_idle.on_durings[0].parent.path == (
            "Lab",
            "Worker",
            "Idle",
        )
        assert state_lab_worker_idle.on_exits == []
        assert state_lab_worker_idle.on_during_aspects == []
        assert state_lab_worker_idle.parent_ref().name == "Worker"
        assert state_lab_worker_idle.parent_ref().path == ("Lab", "Worker")
        assert state_lab_worker_idle.substate_name_to_id == {}
        assert state_lab_worker_idle.extra_name is None
        assert not state_lab_worker_idle.is_pseudo
        assert state_lab_worker_idle.abstract_on_during_aspects == []
        assert state_lab_worker_idle.abstract_on_durings == []
        assert state_lab_worker_idle.abstract_on_enters == []
        assert state_lab_worker_idle.abstract_on_exits == []
        assert state_lab_worker_idle.init_transitions == []
        assert state_lab_worker_idle.is_leaf_state
        assert not state_lab_worker_idle.is_root_state
        assert state_lab_worker_idle.is_stoppable
        assert state_lab_worker_idle.non_abstract_on_during_aspects == []
        assert len(state_lab_worker_idle.non_abstract_on_durings) == 1
        assert state_lab_worker_idle.non_abstract_on_durings[0].stage == "during"
        assert state_lab_worker_idle.non_abstract_on_durings[0].aspect is None
        assert state_lab_worker_idle.non_abstract_on_durings[0].name is None
        assert state_lab_worker_idle.non_abstract_on_durings[0].doc is None
        assert state_lab_worker_idle.non_abstract_on_durings[0].operations == [
            Operation(
                var_name="exact_counter",
                expr=BinaryOp(
                    x=Variable(name="exact_counter"),
                    op="+",
                    y=Variable(name="set_status_flag"),
                ),
            ),
            Operation(
                var_name="set_status_flag",
                expr=BinaryOp(
                    x=BinaryOp(
                        x=BinaryOp(
                            x=Variable(name="set_status_flag"),
                            op="+",
                            y=Variable(name="set_a"),
                        ),
                        op="+",
                        y=Variable(name="set_b"),
                    ),
                    op="+",
                    y=Variable(name="set_c"),
                ),
            ),
            Operation(
                var_name="sensor_temp",
                expr=BinaryOp(
                    x=Variable(name="sensor_temp"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert not state_lab_worker_idle.non_abstract_on_durings[0].is_abstract
        assert state_lab_worker_idle.non_abstract_on_durings[0].state_path == (
            "Lab",
            "Worker",
            "Idle",
            None,
        )
        assert state_lab_worker_idle.non_abstract_on_durings[0].ref is None
        assert state_lab_worker_idle.non_abstract_on_durings[0].ref_state_path is None
        assert (
            state_lab_worker_idle.non_abstract_on_durings[0].parent_ref().name == "Idle"
        )
        assert state_lab_worker_idle.non_abstract_on_durings[0].parent_ref().path == (
            "Lab",
            "Worker",
            "Idle",
        )
        assert (
            state_lab_worker_idle.non_abstract_on_durings[0].func_name
            == "Lab.Worker.Idle.<unnamed>"
        )
        assert not state_lab_worker_idle.non_abstract_on_durings[0].is_aspect
        assert not state_lab_worker_idle.non_abstract_on_durings[0].is_ref
        assert state_lab_worker_idle.non_abstract_on_durings[0].parent.name == "Idle"
        assert state_lab_worker_idle.non_abstract_on_durings[0].parent.path == (
            "Lab",
            "Worker",
            "Idle",
        )
        assert state_lab_worker_idle.non_abstract_on_enters == []
        assert state_lab_worker_idle.non_abstract_on_exits == []
        assert state_lab_worker_idle.parent.name == "Worker"
        assert state_lab_worker_idle.parent.path == ("Lab", "Worker")
        assert state_lab_worker_idle.transitions_entering_children == []
        assert len(state_lab_worker_idle.transitions_entering_children_simplified) == 1
        assert state_lab_worker_idle.transitions_entering_children_simplified[0] is None
        assert len(state_lab_worker_idle.transitions_from) == 1
        assert state_lab_worker_idle.transitions_from[0].from_state == "Idle"
        assert state_lab_worker_idle.transitions_from[0].to_state == "Active"
        assert state_lab_worker_idle.transitions_from[0].event is None
        assert state_lab_worker_idle.transitions_from[0].guard == BinaryOp(
            x=Variable(name="sensor_temp"), op=">", y=Variable(name="set_status_flag")
        )
        assert state_lab_worker_idle.transitions_from[0].effects == []
        assert state_lab_worker_idle.transitions_from[0].parent_ref().name == "Worker"
        assert state_lab_worker_idle.transitions_from[0].parent_ref().path == (
            "Lab",
            "Worker",
        )
        assert len(state_lab_worker_idle.transitions_to) == 2
        assert state_lab_worker_idle.transitions_to[0].from_state == INIT_STATE
        assert state_lab_worker_idle.transitions_to[0].to_state == "Idle"
        assert state_lab_worker_idle.transitions_to[0].event is None
        assert state_lab_worker_idle.transitions_to[0].guard is None
        assert state_lab_worker_idle.transitions_to[0].effects == []
        assert state_lab_worker_idle.transitions_to[0].parent_ref().name == "Worker"
        assert state_lab_worker_idle.transitions_to[0].parent_ref().path == (
            "Lab",
            "Worker",
        )
        assert state_lab_worker_idle.transitions_to[1].from_state == "Active"
        assert state_lab_worker_idle.transitions_to[1].to_state == "Idle"
        assert state_lab_worker_idle.transitions_to[1].event is None
        assert state_lab_worker_idle.transitions_to[1].guard == BinaryOp(
            x=Variable(name="fallback_timeout"),
            op=">",
            y=Variable(name="pair_main_low_a_main_b_low"),
        )
        assert state_lab_worker_idle.transitions_to[1].effects == [
            Operation(
                var_name="exact_counter",
                expr=BinaryOp(
                    x=Variable(name="exact_counter"),
                    op="+",
                    y=Variable(name="fallback_timeout"),
                ),
            )
        ]
        assert state_lab_worker_idle.transitions_to[1].parent_ref().name == "Worker"
        assert state_lab_worker_idle.transitions_to[1].parent_ref().path == (
            "Lab",
            "Worker",
        )

    def test_state_lab_worker_idle_to_ast_node(self, state_lab_worker_idle):
        ast_node = state_lab_worker_idle.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Idle",
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
                            name="exact_counter",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="exact_counter"),
                                op="+",
                                expr2=dsl_nodes.Name(name="set_status_flag"),
                            ),
                        ),
                        dsl_nodes.OperationAssignment(
                            name="set_status_flag",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.BinaryOp(
                                    expr1=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="set_status_flag"),
                                        op="+",
                                        expr2=dsl_nodes.Name(name="set_a"),
                                    ),
                                    op="+",
                                    expr2=dsl_nodes.Name(name="set_b"),
                                ),
                                op="+",
                                expr2=dsl_nodes.Name(name="set_c"),
                            ),
                        ),
                        dsl_nodes.OperationAssignment(
                            name="sensor_temp",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="sensor_temp"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
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

    def test_state_lab_worker_idle_list_on_enters(self, state_lab_worker_idle):
        lst = state_lab_worker_idle.list_on_enters()
        assert lst == []

        lst = state_lab_worker_idle.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_lab_worker_idle.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_lab_worker_idle.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_lab_worker_idle.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_lab_worker_idle.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_lab_worker_idle.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_lab_worker_idle.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_lab_worker_idle.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_lab_worker_idle_during_aspects(self, state_lab_worker_idle):
        lst = state_lab_worker_idle.list_on_during_aspects()
        assert lst == []

        lst = state_lab_worker_idle.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lab_worker_idle.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lab_worker_idle.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lab_worker_idle.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_lab_worker_idle.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_lab_worker_idle.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lab_worker_idle.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_lab_worker_idle.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_lab_worker_idle_during_aspect_recursively(
        self, state_lab_worker_idle
    ):
        lst = state_lab_worker_idle.list_on_during_aspect_recursively()
        assert len(lst) == 1
        st, on_stage = lst[0]
        assert st.name == "Idle"
        assert st.path == ("Lab", "Worker", "Idle")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(
                var_name="exact_counter",
                expr=BinaryOp(
                    x=Variable(name="exact_counter"),
                    op="+",
                    y=Variable(name="set_status_flag"),
                ),
            ),
            Operation(
                var_name="set_status_flag",
                expr=BinaryOp(
                    x=BinaryOp(
                        x=BinaryOp(
                            x=Variable(name="set_status_flag"),
                            op="+",
                            y=Variable(name="set_a"),
                        ),
                        op="+",
                        y=Variable(name="set_b"),
                    ),
                    op="+",
                    y=Variable(name="set_c"),
                ),
            ),
            Operation(
                var_name="sensor_temp",
                expr=BinaryOp(
                    x=Variable(name="sensor_temp"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("Lab", "Worker", "Idle", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "Idle"
        assert on_stage.parent_ref().path == ("Lab", "Worker", "Idle")
        assert on_stage.func_name == "Lab.Worker.Idle.<unnamed>"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "Idle"
        assert on_stage.parent.path == ("Lab", "Worker", "Idle")

        lst = state_lab_worker_idle.list_on_during_aspect_recursively(with_ids=True)
        assert len(lst) == 1
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "Idle"
        assert st.path == ("Lab", "Worker", "Idle")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(
                var_name="exact_counter",
                expr=BinaryOp(
                    x=Variable(name="exact_counter"),
                    op="+",
                    y=Variable(name="set_status_flag"),
                ),
            ),
            Operation(
                var_name="set_status_flag",
                expr=BinaryOp(
                    x=BinaryOp(
                        x=BinaryOp(
                            x=Variable(name="set_status_flag"),
                            op="+",
                            y=Variable(name="set_a"),
                        ),
                        op="+",
                        y=Variable(name="set_b"),
                    ),
                    op="+",
                    y=Variable(name="set_c"),
                ),
            ),
            Operation(
                var_name="sensor_temp",
                expr=BinaryOp(
                    x=Variable(name="sensor_temp"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("Lab", "Worker", "Idle", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "Idle"
        assert on_stage.parent_ref().path == ("Lab", "Worker", "Idle")
        assert on_stage.func_name == "Lab.Worker.Idle.<unnamed>"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "Idle"
        assert on_stage.parent.path == ("Lab", "Worker", "Idle")

    def test_state_lab_worker_active(self, state_lab_worker_active):
        assert state_lab_worker_active.name == "Active"
        assert state_lab_worker_active.path == ("Lab", "Worker", "Active")
        assert sorted(state_lab_worker_active.substates.keys()) == []
        assert state_lab_worker_active.events == {}
        assert state_lab_worker_active.transitions == []
        assert state_lab_worker_active.named_functions == {}
        assert state_lab_worker_active.on_enters == []
        assert len(state_lab_worker_active.on_durings) == 1
        assert state_lab_worker_active.on_durings[0].stage == "during"
        assert state_lab_worker_active.on_durings[0].aspect is None
        assert state_lab_worker_active.on_durings[0].name is None
        assert state_lab_worker_active.on_durings[0].doc is None
        assert state_lab_worker_active.on_durings[0].operations == [
            Operation(
                var_name="fallback_timeout",
                expr=BinaryOp(
                    x=Variable(name="fallback_timeout"),
                    op="+",
                    y=Variable(name="pair_main_low_a_main_b_low"),
                ),
            )
        ]
        assert not state_lab_worker_active.on_durings[0].is_abstract
        assert state_lab_worker_active.on_durings[0].state_path == (
            "Lab",
            "Worker",
            "Active",
            None,
        )
        assert state_lab_worker_active.on_durings[0].ref is None
        assert state_lab_worker_active.on_durings[0].ref_state_path is None
        assert state_lab_worker_active.on_durings[0].parent_ref().name == "Active"
        assert state_lab_worker_active.on_durings[0].parent_ref().path == (
            "Lab",
            "Worker",
            "Active",
        )
        assert (
            state_lab_worker_active.on_durings[0].func_name
            == "Lab.Worker.Active.<unnamed>"
        )
        assert not state_lab_worker_active.on_durings[0].is_aspect
        assert not state_lab_worker_active.on_durings[0].is_ref
        assert state_lab_worker_active.on_durings[0].parent.name == "Active"
        assert state_lab_worker_active.on_durings[0].parent.path == (
            "Lab",
            "Worker",
            "Active",
        )
        assert state_lab_worker_active.on_exits == []
        assert state_lab_worker_active.on_during_aspects == []
        assert state_lab_worker_active.parent_ref().name == "Worker"
        assert state_lab_worker_active.parent_ref().path == ("Lab", "Worker")
        assert state_lab_worker_active.substate_name_to_id == {}
        assert state_lab_worker_active.extra_name is None
        assert not state_lab_worker_active.is_pseudo
        assert state_lab_worker_active.abstract_on_during_aspects == []
        assert state_lab_worker_active.abstract_on_durings == []
        assert state_lab_worker_active.abstract_on_enters == []
        assert state_lab_worker_active.abstract_on_exits == []
        assert state_lab_worker_active.init_transitions == []
        assert state_lab_worker_active.is_leaf_state
        assert not state_lab_worker_active.is_root_state
        assert state_lab_worker_active.is_stoppable
        assert state_lab_worker_active.non_abstract_on_during_aspects == []
        assert len(state_lab_worker_active.non_abstract_on_durings) == 1
        assert state_lab_worker_active.non_abstract_on_durings[0].stage == "during"
        assert state_lab_worker_active.non_abstract_on_durings[0].aspect is None
        assert state_lab_worker_active.non_abstract_on_durings[0].name is None
        assert state_lab_worker_active.non_abstract_on_durings[0].doc is None
        assert state_lab_worker_active.non_abstract_on_durings[0].operations == [
            Operation(
                var_name="fallback_timeout",
                expr=BinaryOp(
                    x=Variable(name="fallback_timeout"),
                    op="+",
                    y=Variable(name="pair_main_low_a_main_b_low"),
                ),
            )
        ]
        assert not state_lab_worker_active.non_abstract_on_durings[0].is_abstract
        assert state_lab_worker_active.non_abstract_on_durings[0].state_path == (
            "Lab",
            "Worker",
            "Active",
            None,
        )
        assert state_lab_worker_active.non_abstract_on_durings[0].ref is None
        assert state_lab_worker_active.non_abstract_on_durings[0].ref_state_path is None
        assert (
            state_lab_worker_active.non_abstract_on_durings[0].parent_ref().name
            == "Active"
        )
        assert state_lab_worker_active.non_abstract_on_durings[0].parent_ref().path == (
            "Lab",
            "Worker",
            "Active",
        )
        assert (
            state_lab_worker_active.non_abstract_on_durings[0].func_name
            == "Lab.Worker.Active.<unnamed>"
        )
        assert not state_lab_worker_active.non_abstract_on_durings[0].is_aspect
        assert not state_lab_worker_active.non_abstract_on_durings[0].is_ref
        assert (
            state_lab_worker_active.non_abstract_on_durings[0].parent.name == "Active"
        )
        assert state_lab_worker_active.non_abstract_on_durings[0].parent.path == (
            "Lab",
            "Worker",
            "Active",
        )
        assert state_lab_worker_active.non_abstract_on_enters == []
        assert state_lab_worker_active.non_abstract_on_exits == []
        assert state_lab_worker_active.parent.name == "Worker"
        assert state_lab_worker_active.parent.path == ("Lab", "Worker")
        assert state_lab_worker_active.transitions_entering_children == []
        assert (
            len(state_lab_worker_active.transitions_entering_children_simplified) == 1
        )
        assert (
            state_lab_worker_active.transitions_entering_children_simplified[0] is None
        )
        assert len(state_lab_worker_active.transitions_from) == 1
        assert state_lab_worker_active.transitions_from[0].from_state == "Active"
        assert state_lab_worker_active.transitions_from[0].to_state == "Idle"
        assert state_lab_worker_active.transitions_from[0].event is None
        assert state_lab_worker_active.transitions_from[0].guard == BinaryOp(
            x=Variable(name="fallback_timeout"),
            op=">",
            y=Variable(name="pair_main_low_a_main_b_low"),
        )
        assert state_lab_worker_active.transitions_from[0].effects == [
            Operation(
                var_name="exact_counter",
                expr=BinaryOp(
                    x=Variable(name="exact_counter"),
                    op="+",
                    y=Variable(name="fallback_timeout"),
                ),
            )
        ]
        assert state_lab_worker_active.transitions_from[0].parent_ref().name == "Worker"
        assert state_lab_worker_active.transitions_from[0].parent_ref().path == (
            "Lab",
            "Worker",
        )
        assert len(state_lab_worker_active.transitions_to) == 1
        assert state_lab_worker_active.transitions_to[0].from_state == "Idle"
        assert state_lab_worker_active.transitions_to[0].to_state == "Active"
        assert state_lab_worker_active.transitions_to[0].event is None
        assert state_lab_worker_active.transitions_to[0].guard == BinaryOp(
            x=Variable(name="sensor_temp"), op=">", y=Variable(name="set_status_flag")
        )
        assert state_lab_worker_active.transitions_to[0].effects == []
        assert state_lab_worker_active.transitions_to[0].parent_ref().name == "Worker"
        assert state_lab_worker_active.transitions_to[0].parent_ref().path == (
            "Lab",
            "Worker",
        )

    def test_state_lab_worker_active_to_ast_node(self, state_lab_worker_active):
        ast_node = state_lab_worker_active.to_ast_node()
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
                            name="fallback_timeout",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="fallback_timeout"),
                                op="+",
                                expr2=dsl_nodes.Name(name="pair_main_low_a_main_b_low"),
                            ),
                        )
                    ],
                    name=None,
                )
            ],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_lab_worker_active_list_on_enters(self, state_lab_worker_active):
        lst = state_lab_worker_active.list_on_enters()
        assert lst == []

        lst = state_lab_worker_active.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_lab_worker_active.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_lab_worker_active.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_lab_worker_active.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_lab_worker_active.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_lab_worker_active.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_lab_worker_active.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_lab_worker_active.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_lab_worker_active_during_aspects(self, state_lab_worker_active):
        lst = state_lab_worker_active.list_on_during_aspects()
        assert lst == []

        lst = state_lab_worker_active.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_lab_worker_active.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_lab_worker_active.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_lab_worker_active.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_lab_worker_active.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_lab_worker_active.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_lab_worker_active.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_lab_worker_active.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_lab_worker_active_during_aspect_recursively(
        self, state_lab_worker_active
    ):
        lst = state_lab_worker_active.list_on_during_aspect_recursively()
        assert len(lst) == 1
        st, on_stage = lst[0]
        assert st.name == "Active"
        assert st.path == ("Lab", "Worker", "Active")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(
                var_name="fallback_timeout",
                expr=BinaryOp(
                    x=Variable(name="fallback_timeout"),
                    op="+",
                    y=Variable(name="pair_main_low_a_main_b_low"),
                ),
            )
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("Lab", "Worker", "Active", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "Active"
        assert on_stage.parent_ref().path == ("Lab", "Worker", "Active")
        assert on_stage.func_name == "Lab.Worker.Active.<unnamed>"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "Active"
        assert on_stage.parent.path == ("Lab", "Worker", "Active")

        lst = state_lab_worker_active.list_on_during_aspect_recursively(with_ids=True)
        assert len(lst) == 1
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "Active"
        assert st.path == ("Lab", "Worker", "Active")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(
                var_name="fallback_timeout",
                expr=BinaryOp(
                    x=Variable(name="fallback_timeout"),
                    op="+",
                    y=Variable(name="pair_main_low_a_main_b_low"),
                ),
            )
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("Lab", "Worker", "Active", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "Active"
        assert on_stage.parent_ref().path == ("Lab", "Worker", "Active")
        assert on_stage.func_name == "Lab.Worker.Active.<unnamed>"
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "Active"
        assert on_stage.parent.path == ("Lab", "Worker", "Active")

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int exact_counter = 1;
def int set_status_flag = 2;
def int sensor_temp = 3;
def int pair_main_low_a_main_b_low = 4;
def int fallback_timeout = 5;
def int set_a = 6;
def int set_b = 7;
def int set_c = 8;
state Lab {
    state Worker named 'Mapping Matrix' {
        state Idle {
            during {
                exact_counter = exact_counter + set_status_flag;
                set_status_flag = set_status_flag + set_a + set_b + set_c;
                sensor_temp = sensor_temp + 1;
            }
        }
        state Active {
            during {
                fallback_timeout = fallback_timeout + pair_main_low_a_main_b_low;
            }
        }
        [*] -> Idle;
        Idle -> Active : if [sensor_temp > set_status_flag];
        Active -> Idle : if [fallback_timeout > pair_main_low_a_main_b_low] effect {
            exact_counter = exact_counter + fallback_timeout;
        }
    }
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

legend top left
|= Variable |= Type |= Initial Value |
| exact_counter | int | 1 |
| set_status_flag | int | 2 |
| sensor_temp | int | 3 |
| pair_main_low_a_main_b_low | int | 4 |
| fallback_timeout | int | 5 |
| set_a | int | 6 |
| set_b | int | 7 |
| set_c | int | 8 |
endlegend

state "Lab" as lab <<composite>> {
    state "Mapping Matrix" as lab__worker <<composite>> {
        state "Idle" as lab__worker__idle
        lab__worker__idle : during {\\n    exact_counter = exact_counter + set_status_flag;\\n    set_status_flag = set_status_flag + set_a + set_b + set_c;\\n    sensor_temp = sensor_temp + 1;\\n}
        state "Active" as lab__worker__active
        lab__worker__active : during {\\n    fallback_timeout = fallback_timeout + pair_main_low_a_main_b_low;\\n}
        [*] --> lab__worker__idle
        lab__worker__idle --> lab__worker__active : sensor_temp > set_status_flag
        lab__worker__active --> lab__worker__idle : fallback_timeout > pair_main_low_a_main_b_low
        note on link
        effect {
            exact_counter = exact_counter + fallback_timeout;
        }
        end note
    }
    [*] --> lab__worker
}
[*] --> lab
lab --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml(options="full")),
        )
