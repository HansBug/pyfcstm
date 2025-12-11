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
def int a = 0;
def int b = 0x0 * 0;
def int round_count = 0;  // define variables
state TrafficLight {
    >> during before {
        a = 0;
    }
    >> during before abstract FFT;
    >> during before abstract TTT /* this is the line */;
    >> during after {
        a = 0xff;
        b = 0x1;
    }

    state InService {
        enter {
            a = 0;
            b = 0;
            round_count = 0;
        }

        enter abstract InServiceAbstractEnter /*
            Abstract Operation When Entering State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */

        // for non-leaf state, either 'before' or 'after' aspect keyword should be used for during block
        during before abstract InServiceBeforeEnterChild /*
            Abstract Operation Before Entering Child States of State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */

        during after abstract InServiceAfterEnterChild /*
            Abstract Operation After Entering Child States of State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */

        exit abstract InServiceAbstractExit /*
            Abstract Operation When Leaving State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */

        state Red {
            during {  // no aspect keywords ('before', 'after') should be used for during block of leaf state
                a = 0x1 << 2;
            }
        }
        state Yellow;
        state Green;
        [*] -> Red :: Start effect {
            b = 0x1;
        };
        Red -> Green effect {
            b = 0x3;
        };
        Green -> Yellow effect {
            b = 0x2;
        };
        Yellow -> Red : if [a >= 10] effect {
            b = 0x1;
            round_count = round_count + 1;
        };
        Green -> Yellow : /Idle.E2;
        Yellow -> Yellow : /E2;
    }
    state Idle;

    [*] -> InService;
    InService -> Idle :: Maintain;
    Idle -> Idle :: E2;
    Idle -> [*];
}
    """,
        entry_name="state_machine_dsl",
    )
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.fixture()
def state_trafficlight(model):
    return model.root_state


@pytest.fixture()
def state_trafficlight_inservice(state_trafficlight):
    return state_trafficlight.substates["InService"]


@pytest.fixture()
def state_trafficlight_inservice_red(state_trafficlight_inservice):
    return state_trafficlight_inservice.substates["Red"]


@pytest.fixture()
def state_trafficlight_inservice_yellow(state_trafficlight_inservice):
    return state_trafficlight_inservice.substates["Yellow"]


@pytest.fixture()
def state_trafficlight_inservice_green(state_trafficlight_inservice):
    return state_trafficlight_inservice.substates["Green"]


@pytest.fixture()
def state_trafficlight_idle(state_trafficlight):
    return state_trafficlight.substates["Idle"]


@pytest.mark.unittest
class TestModelStateTrafficLight:
    def test_model(self, model):
        assert model.defines == {
            "a": VarDefine(name="a", type="int", init=Integer(value=0)),
            "b": VarDefine(
                name="b",
                type="int",
                init=BinaryOp(x=Integer(value=0), op="*", y=Integer(value=0)),
            ),
            "round_count": VarDefine(
                name="round_count", type="int", init=Integer(value=0)
            ),
        }
        assert model.root_state.name == "TrafficLight"
        assert model.root_state.path == ("TrafficLight",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="a", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
            dsl_nodes.DefAssignment(
                name="b",
                type="int",
                expr=dsl_nodes.BinaryOp(
                    expr1=dsl_nodes.Integer(raw="0"),
                    op="*",
                    expr2=dsl_nodes.Integer(raw="0"),
                ),
            ),
            dsl_nodes.DefAssignment(
                name="round_count", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
        ]
        assert ast_node.root_state.name == "TrafficLight"

    def test_state_trafficlight(self, state_trafficlight):
        assert state_trafficlight.name == "TrafficLight"
        assert state_trafficlight.path == ("TrafficLight",)
        assert sorted(state_trafficlight.substates.keys()) == ["Idle", "InService"]
        assert state_trafficlight.events == {
            "E2": Event(name="E2", state_path=("TrafficLight",), extra_name=None)
        }
        assert len(state_trafficlight.transitions) == 4
        assert state_trafficlight.transitions[0].from_state == INIT_STATE
        assert state_trafficlight.transitions[0].to_state == "InService"
        assert state_trafficlight.transitions[0].event is None
        assert state_trafficlight.transitions[0].guard is None
        assert state_trafficlight.transitions[0].effects == []
        assert state_trafficlight.transitions[0].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[0].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[1].from_state == "InService"
        assert state_trafficlight.transitions[1].to_state == "Idle"
        assert state_trafficlight.transitions[1].event == Event(
            name="Maintain", state_path=("TrafficLight", "InService"), extra_name=None
        )
        assert state_trafficlight.transitions[1].guard is None
        assert state_trafficlight.transitions[1].effects == []
        assert state_trafficlight.transitions[1].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[1].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[2].from_state == "Idle"
        assert state_trafficlight.transitions[2].to_state == "Idle"
        assert state_trafficlight.transitions[2].event == Event(
            name="E2", state_path=("TrafficLight", "Idle"), extra_name=None
        )
        assert state_trafficlight.transitions[2].guard is None
        assert state_trafficlight.transitions[2].effects == []
        assert state_trafficlight.transitions[2].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[2].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[3].from_state == "Idle"
        assert state_trafficlight.transitions[3].to_state == EXIT_STATE
        assert state_trafficlight.transitions[3].event is None
        assert state_trafficlight.transitions[3].guard is None
        assert state_trafficlight.transitions[3].effects == []
        assert state_trafficlight.transitions[3].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[3].parent_ref().path == ("TrafficLight",)
        assert sorted(state_trafficlight.named_functions.keys()) == ["FFT", "TTT"]
        assert state_trafficlight.named_functions["FFT"].stage == "during"
        assert state_trafficlight.named_functions["FFT"].aspect == "before"
        assert state_trafficlight.named_functions["FFT"].name == "FFT"
        assert state_trafficlight.named_functions["FFT"].doc is None
        assert state_trafficlight.named_functions["FFT"].operations == []
        assert state_trafficlight.named_functions["FFT"].is_abstract
        assert state_trafficlight.named_functions["FFT"].state_path == (
            "TrafficLight",
            "FFT",
        )
        assert state_trafficlight.named_functions["FFT"].ref is None
        assert state_trafficlight.named_functions["FFT"].ref_state_path is None
        assert (
            state_trafficlight.named_functions["FFT"].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight.named_functions["FFT"].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight.named_functions["FFT"].is_aspect
        assert not state_trafficlight.named_functions["FFT"].is_ref
        assert state_trafficlight.named_functions["FFT"].parent.name == "TrafficLight"
        assert state_trafficlight.named_functions["FFT"].parent.path == (
            "TrafficLight",
        )
        assert state_trafficlight.named_functions["TTT"].stage == "during"
        assert state_trafficlight.named_functions["TTT"].aspect == "before"
        assert state_trafficlight.named_functions["TTT"].name == "TTT"
        assert state_trafficlight.named_functions["TTT"].doc == "this is the line"
        assert state_trafficlight.named_functions["TTT"].operations == []
        assert state_trafficlight.named_functions["TTT"].is_abstract
        assert state_trafficlight.named_functions["TTT"].state_path == (
            "TrafficLight",
            "TTT",
        )
        assert state_trafficlight.named_functions["TTT"].ref is None
        assert state_trafficlight.named_functions["TTT"].ref_state_path is None
        assert (
            state_trafficlight.named_functions["TTT"].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight.named_functions["TTT"].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight.named_functions["TTT"].is_aspect
        assert not state_trafficlight.named_functions["TTT"].is_ref
        assert state_trafficlight.named_functions["TTT"].parent.name == "TrafficLight"
        assert state_trafficlight.named_functions["TTT"].parent.path == (
            "TrafficLight",
        )
        assert state_trafficlight.on_enters == []
        assert state_trafficlight.on_durings == []
        assert state_trafficlight.on_exits == []
        assert len(state_trafficlight.on_during_aspects) == 4
        assert state_trafficlight.on_during_aspects[0].stage == "during"
        assert state_trafficlight.on_during_aspects[0].aspect == "before"
        assert state_trafficlight.on_during_aspects[0].name is None
        assert state_trafficlight.on_during_aspects[0].doc is None
        assert state_trafficlight.on_during_aspects[0].operations == [
            Operation(var_name="a", expr=Integer(value=0))
        ]
        assert not state_trafficlight.on_during_aspects[0].is_abstract
        assert state_trafficlight.on_during_aspects[0].state_path == (
            "TrafficLight",
            None,
        )
        assert state_trafficlight.on_during_aspects[0].ref is None
        assert state_trafficlight.on_during_aspects[0].ref_state_path is None
        assert (
            state_trafficlight.on_during_aspects[0].parent_ref().name == "TrafficLight"
        )
        assert state_trafficlight.on_during_aspects[0].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight.on_during_aspects[0].is_aspect
        assert not state_trafficlight.on_during_aspects[0].is_ref
        assert state_trafficlight.on_during_aspects[0].parent.name == "TrafficLight"
        assert state_trafficlight.on_during_aspects[0].parent.path == ("TrafficLight",)
        assert state_trafficlight.on_during_aspects[1].stage == "during"
        assert state_trafficlight.on_during_aspects[1].aspect == "before"
        assert state_trafficlight.on_during_aspects[1].name == "FFT"
        assert state_trafficlight.on_during_aspects[1].doc is None
        assert state_trafficlight.on_during_aspects[1].operations == []
        assert state_trafficlight.on_during_aspects[1].is_abstract
        assert state_trafficlight.on_during_aspects[1].state_path == (
            "TrafficLight",
            "FFT",
        )
        assert state_trafficlight.on_during_aspects[1].ref is None
        assert state_trafficlight.on_during_aspects[1].ref_state_path is None
        assert (
            state_trafficlight.on_during_aspects[1].parent_ref().name == "TrafficLight"
        )
        assert state_trafficlight.on_during_aspects[1].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight.on_during_aspects[1].is_aspect
        assert not state_trafficlight.on_during_aspects[1].is_ref
        assert state_trafficlight.on_during_aspects[1].parent.name == "TrafficLight"
        assert state_trafficlight.on_during_aspects[1].parent.path == ("TrafficLight",)
        assert state_trafficlight.on_during_aspects[2].stage == "during"
        assert state_trafficlight.on_during_aspects[2].aspect == "before"
        assert state_trafficlight.on_during_aspects[2].name == "TTT"
        assert state_trafficlight.on_during_aspects[2].doc == "this is the line"
        assert state_trafficlight.on_during_aspects[2].operations == []
        assert state_trafficlight.on_during_aspects[2].is_abstract
        assert state_trafficlight.on_during_aspects[2].state_path == (
            "TrafficLight",
            "TTT",
        )
        assert state_trafficlight.on_during_aspects[2].ref is None
        assert state_trafficlight.on_during_aspects[2].ref_state_path is None
        assert (
            state_trafficlight.on_during_aspects[2].parent_ref().name == "TrafficLight"
        )
        assert state_trafficlight.on_during_aspects[2].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight.on_during_aspects[2].is_aspect
        assert not state_trafficlight.on_during_aspects[2].is_ref
        assert state_trafficlight.on_during_aspects[2].parent.name == "TrafficLight"
        assert state_trafficlight.on_during_aspects[2].parent.path == ("TrafficLight",)
        assert state_trafficlight.on_during_aspects[3].stage == "during"
        assert state_trafficlight.on_during_aspects[3].aspect == "after"
        assert state_trafficlight.on_during_aspects[3].name is None
        assert state_trafficlight.on_during_aspects[3].doc is None
        assert state_trafficlight.on_during_aspects[3].operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not state_trafficlight.on_during_aspects[3].is_abstract
        assert state_trafficlight.on_during_aspects[3].state_path == (
            "TrafficLight",
            None,
        )
        assert state_trafficlight.on_during_aspects[3].ref is None
        assert state_trafficlight.on_during_aspects[3].ref_state_path is None
        assert (
            state_trafficlight.on_during_aspects[3].parent_ref().name == "TrafficLight"
        )
        assert state_trafficlight.on_during_aspects[3].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight.on_during_aspects[3].is_aspect
        assert not state_trafficlight.on_during_aspects[3].is_ref
        assert state_trafficlight.on_during_aspects[3].parent.name == "TrafficLight"
        assert state_trafficlight.on_during_aspects[3].parent.path == ("TrafficLight",)
        assert state_trafficlight.parent_ref is None
        assert state_trafficlight.substate_name_to_id == {"InService": 0, "Idle": 1}
        assert state_trafficlight.extra_name is None
        assert not state_trafficlight.is_pseudo
        assert len(state_trafficlight.abstract_on_during_aspects) == 2
        assert state_trafficlight.abstract_on_during_aspects[0].stage == "during"
        assert state_trafficlight.abstract_on_during_aspects[0].aspect == "before"
        assert state_trafficlight.abstract_on_during_aspects[0].name == "FFT"
        assert state_trafficlight.abstract_on_during_aspects[0].doc is None
        assert state_trafficlight.abstract_on_during_aspects[0].operations == []
        assert state_trafficlight.abstract_on_during_aspects[0].is_abstract
        assert state_trafficlight.abstract_on_during_aspects[0].state_path == (
            "TrafficLight",
            "FFT",
        )
        assert state_trafficlight.abstract_on_during_aspects[0].ref is None
        assert state_trafficlight.abstract_on_during_aspects[0].ref_state_path is None
        assert (
            state_trafficlight.abstract_on_during_aspects[0].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight.abstract_on_during_aspects[0].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight.abstract_on_during_aspects[0].is_aspect
        assert not state_trafficlight.abstract_on_during_aspects[0].is_ref
        assert (
            state_trafficlight.abstract_on_during_aspects[0].parent.name
            == "TrafficLight"
        )
        assert state_trafficlight.abstract_on_during_aspects[0].parent.path == (
            "TrafficLight",
        )
        assert state_trafficlight.abstract_on_during_aspects[1].stage == "during"
        assert state_trafficlight.abstract_on_during_aspects[1].aspect == "before"
        assert state_trafficlight.abstract_on_during_aspects[1].name == "TTT"
        assert (
            state_trafficlight.abstract_on_during_aspects[1].doc == "this is the line"
        )
        assert state_trafficlight.abstract_on_during_aspects[1].operations == []
        assert state_trafficlight.abstract_on_during_aspects[1].is_abstract
        assert state_trafficlight.abstract_on_during_aspects[1].state_path == (
            "TrafficLight",
            "TTT",
        )
        assert state_trafficlight.abstract_on_during_aspects[1].ref is None
        assert state_trafficlight.abstract_on_during_aspects[1].ref_state_path is None
        assert (
            state_trafficlight.abstract_on_during_aspects[1].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight.abstract_on_during_aspects[1].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight.abstract_on_during_aspects[1].is_aspect
        assert not state_trafficlight.abstract_on_during_aspects[1].is_ref
        assert (
            state_trafficlight.abstract_on_during_aspects[1].parent.name
            == "TrafficLight"
        )
        assert state_trafficlight.abstract_on_during_aspects[1].parent.path == (
            "TrafficLight",
        )
        assert state_trafficlight.abstract_on_durings == []
        assert state_trafficlight.abstract_on_enters == []
        assert state_trafficlight.abstract_on_exits == []
        assert len(state_trafficlight.init_transitions) == 1
        assert state_trafficlight.init_transitions[0].from_state == INIT_STATE
        assert state_trafficlight.init_transitions[0].to_state == "InService"
        assert state_trafficlight.init_transitions[0].event is None
        assert state_trafficlight.init_transitions[0].guard is None
        assert state_trafficlight.init_transitions[0].effects == []
        assert (
            state_trafficlight.init_transitions[0].parent_ref().name == "TrafficLight"
        )
        assert state_trafficlight.init_transitions[0].parent_ref().path == (
            "TrafficLight",
        )
        assert not state_trafficlight.is_leaf_state
        assert state_trafficlight.is_root_state
        assert not state_trafficlight.is_stoppable
        assert len(state_trafficlight.non_abstract_on_during_aspects) == 2
        assert state_trafficlight.non_abstract_on_during_aspects[0].stage == "during"
        assert state_trafficlight.non_abstract_on_during_aspects[0].aspect == "before"
        assert state_trafficlight.non_abstract_on_during_aspects[0].name is None
        assert state_trafficlight.non_abstract_on_during_aspects[0].doc is None
        assert state_trafficlight.non_abstract_on_during_aspects[0].operations == [
            Operation(var_name="a", expr=Integer(value=0))
        ]
        assert not state_trafficlight.non_abstract_on_during_aspects[0].is_abstract
        assert state_trafficlight.non_abstract_on_during_aspects[0].state_path == (
            "TrafficLight",
            None,
        )
        assert state_trafficlight.non_abstract_on_during_aspects[0].ref is None
        assert (
            state_trafficlight.non_abstract_on_during_aspects[0].ref_state_path is None
        )
        assert (
            state_trafficlight.non_abstract_on_during_aspects[0].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight.non_abstract_on_during_aspects[
            0
        ].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.non_abstract_on_during_aspects[0].is_aspect
        assert not state_trafficlight.non_abstract_on_during_aspects[0].is_ref
        assert (
            state_trafficlight.non_abstract_on_during_aspects[0].parent.name
            == "TrafficLight"
        )
        assert state_trafficlight.non_abstract_on_during_aspects[0].parent.path == (
            "TrafficLight",
        )
        assert state_trafficlight.non_abstract_on_during_aspects[1].stage == "during"
        assert state_trafficlight.non_abstract_on_during_aspects[1].aspect == "after"
        assert state_trafficlight.non_abstract_on_during_aspects[1].name is None
        assert state_trafficlight.non_abstract_on_during_aspects[1].doc is None
        assert state_trafficlight.non_abstract_on_during_aspects[1].operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not state_trafficlight.non_abstract_on_during_aspects[1].is_abstract
        assert state_trafficlight.non_abstract_on_during_aspects[1].state_path == (
            "TrafficLight",
            None,
        )
        assert state_trafficlight.non_abstract_on_during_aspects[1].ref is None
        assert (
            state_trafficlight.non_abstract_on_during_aspects[1].ref_state_path is None
        )
        assert (
            state_trafficlight.non_abstract_on_during_aspects[1].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight.non_abstract_on_during_aspects[
            1
        ].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.non_abstract_on_during_aspects[1].is_aspect
        assert not state_trafficlight.non_abstract_on_during_aspects[1].is_ref
        assert (
            state_trafficlight.non_abstract_on_during_aspects[1].parent.name
            == "TrafficLight"
        )
        assert state_trafficlight.non_abstract_on_during_aspects[1].parent.path == (
            "TrafficLight",
        )
        assert state_trafficlight.non_abstract_on_durings == []
        assert state_trafficlight.non_abstract_on_enters == []
        assert state_trafficlight.non_abstract_on_exits == []
        assert state_trafficlight.parent is None
        assert len(state_trafficlight.transitions_entering_children) == 1
        assert (
            state_trafficlight.transitions_entering_children[0].from_state == INIT_STATE
        )
        assert (
            state_trafficlight.transitions_entering_children[0].to_state == "InService"
        )
        assert state_trafficlight.transitions_entering_children[0].event is None
        assert state_trafficlight.transitions_entering_children[0].guard is None
        assert state_trafficlight.transitions_entering_children[0].effects == []
        assert (
            state_trafficlight.transitions_entering_children[0].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight.transitions_entering_children[
            0
        ].parent_ref().path == ("TrafficLight",)
        assert len(state_trafficlight.transitions_entering_children_simplified) == 1
        assert (
            state_trafficlight.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_trafficlight.transitions_entering_children_simplified[0].to_state
            == "InService"
        )
        assert (
            state_trafficlight.transitions_entering_children_simplified[0].event is None
        )
        assert (
            state_trafficlight.transitions_entering_children_simplified[0].guard is None
        )
        assert (
            state_trafficlight.transitions_entering_children_simplified[0].effects == []
        )
        assert (
            state_trafficlight.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "TrafficLight"
        )
        assert state_trafficlight.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("TrafficLight",)
        assert len(state_trafficlight.transitions_from) == 1
        assert state_trafficlight.transitions_from[0].from_state == "TrafficLight"
        assert state_trafficlight.transitions_from[0].to_state == EXIT_STATE
        assert state_trafficlight.transitions_from[0].event is None
        assert state_trafficlight.transitions_from[0].guard is None
        assert state_trafficlight.transitions_from[0].effects == []
        assert state_trafficlight.transitions_from[0].parent_ref is None
        assert len(state_trafficlight.transitions_to) == 1
        assert state_trafficlight.transitions_to[0].from_state == INIT_STATE
        assert state_trafficlight.transitions_to[0].to_state == "TrafficLight"
        assert state_trafficlight.transitions_to[0].event is None
        assert state_trafficlight.transitions_to[0].guard is None
        assert state_trafficlight.transitions_to[0].effects == []
        assert state_trafficlight.transitions_to[0].parent_ref is None

    def test_state_trafficlight_to_ast_node(self, state_trafficlight):
        ast_node = state_trafficlight.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="TrafficLight",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E2", extra_name=None)],
            substates=[
                dsl_nodes.StateDefinition(
                    name="InService",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="Start", extra_name=None),
                        dsl_nodes.EventDefinition(name="Maintain", extra_name=None),
                    ],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Red",
                            extra_name=None,
                            events=[],
                            substates=[],
                            transitions=[],
                            enters=[],
                            durings=[
                                dsl_nodes.DuringOperations(
                                    aspect=None,
                                    operations=[
                                        dsl_nodes.OperationAssignment(
                                            name="a",
                                            expr=dsl_nodes.BinaryOp(
                                                expr1=dsl_nodes.Integer(raw="1"),
                                                op="<<",
                                                expr2=dsl_nodes.Integer(raw="2"),
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
                        dsl_nodes.StateDefinition(
                            name="Yellow",
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
                            name="Green",
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
                            to_state="Red",
                            event_id=dsl_nodes.ChainID(
                                path=["Start"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="b", expr=dsl_nodes.Integer(raw="1")
                                )
                            ],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Red",
                            to_state="Green",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="b", expr=dsl_nodes.Integer(raw="3")
                                )
                            ],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Green",
                            to_state="Yellow",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="b", expr=dsl_nodes.Integer(raw="2")
                                )
                            ],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Yellow",
                            to_state="Red",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="a"),
                                op=">=",
                                expr2=dsl_nodes.Integer(raw="10"),
                            ),
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="b", expr=dsl_nodes.Integer(raw="1")
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="round_count",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="round_count"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
                            ],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Green",
                            to_state="Yellow",
                            event_id=dsl_nodes.ChainID(
                                path=["Idle", "E2"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Yellow",
                            to_state="Yellow",
                            event_id=dsl_nodes.ChainID(path=["E2"], is_absolute=True),
                            condition_expr=None,
                            post_operations=[],
                        ),
                    ],
                    enters=[
                        dsl_nodes.EnterOperations(
                            operations=[
                                dsl_nodes.OperationAssignment(
                                    name="a", expr=dsl_nodes.Integer(raw="0")
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="b", expr=dsl_nodes.Integer(raw="0")
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="round_count", expr=dsl_nodes.Integer(raw="0")
                                ),
                            ],
                            name=None,
                        ),
                        dsl_nodes.EnterAbstractFunction(
                            name="InServiceAbstractEnter",
                            doc="Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework",
                        ),
                    ],
                    durings=[
                        dsl_nodes.DuringAbstractFunction(
                            name="InServiceBeforeEnterChild",
                            aspect="before",
                            doc="Abstract Operation Before Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework",
                        ),
                        dsl_nodes.DuringAbstractFunction(
                            name="InServiceAfterEnterChild",
                            aspect="after",
                            doc="Abstract Operation After Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework",
                        ),
                    ],
                    exits=[
                        dsl_nodes.ExitAbstractFunction(
                            name="InServiceAbstractExit",
                            doc="Abstract Operation When Leaving State 'InService'\nTODO: Should be Implemented In Generated Code Framework",
                        )
                    ],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                ),
                dsl_nodes.StateDefinition(
                    name="Idle",
                    extra_name=None,
                    events=[dsl_nodes.EventDefinition(name="E2", extra_name=None)],
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
                    to_state="InService",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="InService",
                    to_state="Idle",
                    event_id=dsl_nodes.ChainID(
                        path=["InService", "Maintain"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Idle",
                    to_state="Idle",
                    event_id=dsl_nodes.ChainID(path=["Idle", "E2"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Idle",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
            ],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[
                dsl_nodes.DuringAspectOperations(
                    aspect="before",
                    operations=[
                        dsl_nodes.OperationAssignment(
                            name="a", expr=dsl_nodes.Integer(raw="0")
                        )
                    ],
                    name=None,
                ),
                dsl_nodes.DuringAspectAbstractFunction(
                    name="FFT", aspect="before", doc=None
                ),
                dsl_nodes.DuringAspectAbstractFunction(
                    name="TTT", aspect="before", doc="this is the line"
                ),
                dsl_nodes.DuringAspectOperations(
                    aspect="after",
                    operations=[
                        dsl_nodes.OperationAssignment(
                            name="a", expr=dsl_nodes.Integer(raw="255")
                        ),
                        dsl_nodes.OperationAssignment(
                            name="b", expr=dsl_nodes.Integer(raw="1")
                        ),
                    ],
                    name=None,
                ),
            ],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_trafficlight_list_on_enters(self, state_trafficlight):
        lst = state_trafficlight.list_on_enters()
        assert lst == []

        lst = state_trafficlight.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_trafficlight.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_trafficlight.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_trafficlight.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_trafficlight.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_trafficlight.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_trafficlight.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_trafficlight.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_trafficlight_during_aspects(self, state_trafficlight):
        lst = state_trafficlight.list_on_during_aspects()
        assert len(lst) == 4
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        on_stage = lst[1]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        on_stage = lst[2]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        on_stage = lst[3]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight.list_on_during_aspects(aspect="before")
        assert len(lst) == 3
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        on_stage = lst[1]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        on_stage = lst[2]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight.list_on_during_aspects(aspect="after")
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight.list_on_during_aspects(is_abstract=False)
        assert len(lst) == 2
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        on_stage = lst[1]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight.list_on_during_aspects(is_abstract=True)
        assert len(lst) == 2
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        on_stage = lst[1]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert len(lst) == 2
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        on_stage = lst[1]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_trafficlight_inservice(self, state_trafficlight_inservice):
        assert state_trafficlight_inservice.name == "InService"
        assert state_trafficlight_inservice.path == ("TrafficLight", "InService")
        assert sorted(state_trafficlight_inservice.substates.keys()) == [
            "Green",
            "Red",
            "Yellow",
        ]
        assert state_trafficlight_inservice.events == {
            "Start": Event(
                name="Start", state_path=("TrafficLight", "InService"), extra_name=None
            ),
            "Maintain": Event(
                name="Maintain",
                state_path=("TrafficLight", "InService"),
                extra_name=None,
            ),
        }
        assert len(state_trafficlight_inservice.transitions) == 6
        assert state_trafficlight_inservice.transitions[0].from_state == INIT_STATE
        assert state_trafficlight_inservice.transitions[0].to_state == "Red"
        assert state_trafficlight_inservice.transitions[0].event == Event(
            name="Start", state_path=("TrafficLight", "InService"), extra_name=None
        )
        assert state_trafficlight_inservice.transitions[0].guard is None
        assert state_trafficlight_inservice.transitions[0].effects == [
            Operation(var_name="b", expr=Integer(value=1))
        ]
        assert (
            state_trafficlight_inservice.transitions[0].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[0].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[1].from_state == "Red"
        assert state_trafficlight_inservice.transitions[1].to_state == "Green"
        assert state_trafficlight_inservice.transitions[1].event is None
        assert state_trafficlight_inservice.transitions[1].guard is None
        assert state_trafficlight_inservice.transitions[1].effects == [
            Operation(var_name="b", expr=Integer(value=3))
        ]
        assert (
            state_trafficlight_inservice.transitions[1].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[1].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[2].from_state == "Green"
        assert state_trafficlight_inservice.transitions[2].to_state == "Yellow"
        assert state_trafficlight_inservice.transitions[2].event is None
        assert state_trafficlight_inservice.transitions[2].guard is None
        assert state_trafficlight_inservice.transitions[2].effects == [
            Operation(var_name="b", expr=Integer(value=2))
        ]
        assert (
            state_trafficlight_inservice.transitions[2].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[2].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[3].from_state == "Yellow"
        assert state_trafficlight_inservice.transitions[3].to_state == "Red"
        assert state_trafficlight_inservice.transitions[3].event is None
        assert state_trafficlight_inservice.transitions[3].guard == BinaryOp(
            x=Variable(name="a"), op=">=", y=Integer(value=10)
        )
        assert state_trafficlight_inservice.transitions[3].effects == [
            Operation(var_name="b", expr=Integer(value=1)),
            Operation(
                var_name="round_count",
                expr=BinaryOp(
                    x=Variable(name="round_count"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert (
            state_trafficlight_inservice.transitions[3].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[3].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[4].from_state == "Green"
        assert state_trafficlight_inservice.transitions[4].to_state == "Yellow"
        assert state_trafficlight_inservice.transitions[4].event == Event(
            name="E2", state_path=("TrafficLight", "Idle"), extra_name=None
        )
        assert state_trafficlight_inservice.transitions[4].guard is None
        assert state_trafficlight_inservice.transitions[4].effects == []
        assert (
            state_trafficlight_inservice.transitions[4].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[4].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[5].from_state == "Yellow"
        assert state_trafficlight_inservice.transitions[5].to_state == "Yellow"
        assert state_trafficlight_inservice.transitions[5].event == Event(
            name="E2", state_path=("TrafficLight",), extra_name=None
        )
        assert state_trafficlight_inservice.transitions[5].guard is None
        assert state_trafficlight_inservice.transitions[5].effects == []
        assert (
            state_trafficlight_inservice.transitions[5].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[5].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert sorted(state_trafficlight_inservice.named_functions.keys()) == [
            "InServiceAbstractEnter",
            "InServiceAbstractExit",
            "InServiceAfterEnterChild",
            "InServiceBeforeEnterChild",
        ]
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractEnter"].stage
            == "enter"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAbstractEnter"
            ].aspect
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractEnter"].name
            == "InServiceAbstractEnter"
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractEnter"].doc
            == "Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAbstractEnter"
            ].operations
            == []
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceAbstractEnter"
        ].is_abstract
        assert state_trafficlight_inservice.named_functions[
            "InServiceAbstractEnter"
        ].state_path == ("TrafficLight", "InService", "InServiceAbstractEnter")
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractEnter"].ref
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAbstractEnter"
            ].ref_state_path
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractEnter"]
            .parent_ref()
            .name
            == "InService"
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceAbstractEnter"
        ].parent_ref().path == ("TrafficLight", "InService")
        assert not state_trafficlight_inservice.named_functions[
            "InServiceAbstractEnter"
        ].is_aspect
        assert not state_trafficlight_inservice.named_functions[
            "InServiceAbstractEnter"
        ].is_ref
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAbstractEnter"
            ].parent.name
            == "InService"
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceAbstractEnter"
        ].parent.path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceBeforeEnterChild"
            ].stage
            == "during"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceBeforeEnterChild"
            ].aspect
            == "before"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceBeforeEnterChild"
            ].name
            == "InServiceBeforeEnterChild"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceBeforeEnterChild"
            ].doc
            == "Abstract Operation Before Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceBeforeEnterChild"
            ].operations
            == []
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceBeforeEnterChild"
        ].is_abstract
        assert state_trafficlight_inservice.named_functions[
            "InServiceBeforeEnterChild"
        ].state_path == ("TrafficLight", "InService", "InServiceBeforeEnterChild")
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceBeforeEnterChild"
            ].ref
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceBeforeEnterChild"
            ].ref_state_path
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceBeforeEnterChild"]
            .parent_ref()
            .name
            == "InService"
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceBeforeEnterChild"
        ].parent_ref().path == ("TrafficLight", "InService")
        assert not state_trafficlight_inservice.named_functions[
            "InServiceBeforeEnterChild"
        ].is_aspect
        assert not state_trafficlight_inservice.named_functions[
            "InServiceBeforeEnterChild"
        ].is_ref
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceBeforeEnterChild"
            ].parent.name
            == "InService"
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceBeforeEnterChild"
        ].parent.path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAfterEnterChild"
            ].stage
            == "during"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAfterEnterChild"
            ].aspect
            == "after"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAfterEnterChild"
            ].name
            == "InServiceAfterEnterChild"
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceAfterEnterChild"].doc
            == "Abstract Operation After Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAfterEnterChild"
            ].operations
            == []
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceAfterEnterChild"
        ].is_abstract
        assert state_trafficlight_inservice.named_functions[
            "InServiceAfterEnterChild"
        ].state_path == ("TrafficLight", "InService", "InServiceAfterEnterChild")
        assert (
            state_trafficlight_inservice.named_functions["InServiceAfterEnterChild"].ref
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAfterEnterChild"
            ].ref_state_path
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceAfterEnterChild"]
            .parent_ref()
            .name
            == "InService"
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceAfterEnterChild"
        ].parent_ref().path == ("TrafficLight", "InService")
        assert not state_trafficlight_inservice.named_functions[
            "InServiceAfterEnterChild"
        ].is_aspect
        assert not state_trafficlight_inservice.named_functions[
            "InServiceAfterEnterChild"
        ].is_ref
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAfterEnterChild"
            ].parent.name
            == "InService"
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceAfterEnterChild"
        ].parent.path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractExit"].stage
            == "exit"
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractExit"].aspect
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractExit"].name
            == "InServiceAbstractExit"
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractExit"].doc
            == "Abstract Operation When Leaving State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAbstractExit"
            ].operations
            == []
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceAbstractExit"
        ].is_abstract
        assert state_trafficlight_inservice.named_functions[
            "InServiceAbstractExit"
        ].state_path == ("TrafficLight", "InService", "InServiceAbstractExit")
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractExit"].ref
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAbstractExit"
            ].ref_state_path
            is None
        )
        assert (
            state_trafficlight_inservice.named_functions["InServiceAbstractExit"]
            .parent_ref()
            .name
            == "InService"
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceAbstractExit"
        ].parent_ref().path == ("TrafficLight", "InService")
        assert not state_trafficlight_inservice.named_functions[
            "InServiceAbstractExit"
        ].is_aspect
        assert not state_trafficlight_inservice.named_functions[
            "InServiceAbstractExit"
        ].is_ref
        assert (
            state_trafficlight_inservice.named_functions[
                "InServiceAbstractExit"
            ].parent.name
            == "InService"
        )
        assert state_trafficlight_inservice.named_functions[
            "InServiceAbstractExit"
        ].parent.path == ("TrafficLight", "InService")
        assert len(state_trafficlight_inservice.on_enters) == 2
        assert state_trafficlight_inservice.on_enters[0].stage == "enter"
        assert state_trafficlight_inservice.on_enters[0].aspect is None
        assert state_trafficlight_inservice.on_enters[0].name is None
        assert state_trafficlight_inservice.on_enters[0].doc is None
        assert state_trafficlight_inservice.on_enters[0].operations == [
            Operation(var_name="a", expr=Integer(value=0)),
            Operation(var_name="b", expr=Integer(value=0)),
            Operation(var_name="round_count", expr=Integer(value=0)),
        ]
        assert not state_trafficlight_inservice.on_enters[0].is_abstract
        assert state_trafficlight_inservice.on_enters[0].state_path == (
            "TrafficLight",
            "InService",
            None,
        )
        assert state_trafficlight_inservice.on_enters[0].ref is None
        assert state_trafficlight_inservice.on_enters[0].ref_state_path is None
        assert (
            state_trafficlight_inservice.on_enters[0].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.on_enters[0].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert not state_trafficlight_inservice.on_enters[0].is_aspect
        assert not state_trafficlight_inservice.on_enters[0].is_ref
        assert state_trafficlight_inservice.on_enters[0].parent.name == "InService"
        assert state_trafficlight_inservice.on_enters[0].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.on_enters[1].stage == "enter"
        assert state_trafficlight_inservice.on_enters[1].aspect is None
        assert (
            state_trafficlight_inservice.on_enters[1].name == "InServiceAbstractEnter"
        )
        assert (
            state_trafficlight_inservice.on_enters[1].doc
            == "Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert state_trafficlight_inservice.on_enters[1].operations == []
        assert state_trafficlight_inservice.on_enters[1].is_abstract
        assert state_trafficlight_inservice.on_enters[1].state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractEnter",
        )
        assert state_trafficlight_inservice.on_enters[1].ref is None
        assert state_trafficlight_inservice.on_enters[1].ref_state_path is None
        assert (
            state_trafficlight_inservice.on_enters[1].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.on_enters[1].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert not state_trafficlight_inservice.on_enters[1].is_aspect
        assert not state_trafficlight_inservice.on_enters[1].is_ref
        assert state_trafficlight_inservice.on_enters[1].parent.name == "InService"
        assert state_trafficlight_inservice.on_enters[1].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert len(state_trafficlight_inservice.on_durings) == 2
        assert state_trafficlight_inservice.on_durings[0].stage == "during"
        assert state_trafficlight_inservice.on_durings[0].aspect == "before"
        assert (
            state_trafficlight_inservice.on_durings[0].name
            == "InServiceBeforeEnterChild"
        )
        assert (
            state_trafficlight_inservice.on_durings[0].doc
            == "Abstract Operation Before Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert state_trafficlight_inservice.on_durings[0].operations == []
        assert state_trafficlight_inservice.on_durings[0].is_abstract
        assert state_trafficlight_inservice.on_durings[0].state_path == (
            "TrafficLight",
            "InService",
            "InServiceBeforeEnterChild",
        )
        assert state_trafficlight_inservice.on_durings[0].ref is None
        assert state_trafficlight_inservice.on_durings[0].ref_state_path is None
        assert (
            state_trafficlight_inservice.on_durings[0].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.on_durings[0].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert not state_trafficlight_inservice.on_durings[0].is_aspect
        assert not state_trafficlight_inservice.on_durings[0].is_ref
        assert state_trafficlight_inservice.on_durings[0].parent.name == "InService"
        assert state_trafficlight_inservice.on_durings[0].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.on_durings[1].stage == "during"
        assert state_trafficlight_inservice.on_durings[1].aspect == "after"
        assert (
            state_trafficlight_inservice.on_durings[1].name
            == "InServiceAfterEnterChild"
        )
        assert (
            state_trafficlight_inservice.on_durings[1].doc
            == "Abstract Operation After Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert state_trafficlight_inservice.on_durings[1].operations == []
        assert state_trafficlight_inservice.on_durings[1].is_abstract
        assert state_trafficlight_inservice.on_durings[1].state_path == (
            "TrafficLight",
            "InService",
            "InServiceAfterEnterChild",
        )
        assert state_trafficlight_inservice.on_durings[1].ref is None
        assert state_trafficlight_inservice.on_durings[1].ref_state_path is None
        assert (
            state_trafficlight_inservice.on_durings[1].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.on_durings[1].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert not state_trafficlight_inservice.on_durings[1].is_aspect
        assert not state_trafficlight_inservice.on_durings[1].is_ref
        assert state_trafficlight_inservice.on_durings[1].parent.name == "InService"
        assert state_trafficlight_inservice.on_durings[1].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert len(state_trafficlight_inservice.on_exits) == 1
        assert state_trafficlight_inservice.on_exits[0].stage == "exit"
        assert state_trafficlight_inservice.on_exits[0].aspect is None
        assert state_trafficlight_inservice.on_exits[0].name == "InServiceAbstractExit"
        assert (
            state_trafficlight_inservice.on_exits[0].doc
            == "Abstract Operation When Leaving State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert state_trafficlight_inservice.on_exits[0].operations == []
        assert state_trafficlight_inservice.on_exits[0].is_abstract
        assert state_trafficlight_inservice.on_exits[0].state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractExit",
        )
        assert state_trafficlight_inservice.on_exits[0].ref is None
        assert state_trafficlight_inservice.on_exits[0].ref_state_path is None
        assert state_trafficlight_inservice.on_exits[0].parent_ref().name == "InService"
        assert state_trafficlight_inservice.on_exits[0].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert not state_trafficlight_inservice.on_exits[0].is_aspect
        assert not state_trafficlight_inservice.on_exits[0].is_ref
        assert state_trafficlight_inservice.on_exits[0].parent.name == "InService"
        assert state_trafficlight_inservice.on_exits[0].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.on_during_aspects == []
        assert state_trafficlight_inservice.parent_ref().name == "TrafficLight"
        assert state_trafficlight_inservice.parent_ref().path == ("TrafficLight",)
        assert state_trafficlight_inservice.substate_name_to_id == {
            "Red": 0,
            "Yellow": 1,
            "Green": 2,
        }
        assert state_trafficlight_inservice.extra_name is None
        assert not state_trafficlight_inservice.is_pseudo
        assert state_trafficlight_inservice.abstract_on_during_aspects == []
        assert len(state_trafficlight_inservice.abstract_on_durings) == 2
        assert state_trafficlight_inservice.abstract_on_durings[0].stage == "during"
        assert state_trafficlight_inservice.abstract_on_durings[0].aspect == "before"
        assert (
            state_trafficlight_inservice.abstract_on_durings[0].name
            == "InServiceBeforeEnterChild"
        )
        assert (
            state_trafficlight_inservice.abstract_on_durings[0].doc
            == "Abstract Operation Before Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert state_trafficlight_inservice.abstract_on_durings[0].operations == []
        assert state_trafficlight_inservice.abstract_on_durings[0].is_abstract
        assert state_trafficlight_inservice.abstract_on_durings[0].state_path == (
            "TrafficLight",
            "InService",
            "InServiceBeforeEnterChild",
        )
        assert state_trafficlight_inservice.abstract_on_durings[0].ref is None
        assert (
            state_trafficlight_inservice.abstract_on_durings[0].ref_state_path is None
        )
        assert (
            state_trafficlight_inservice.abstract_on_durings[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice.abstract_on_durings[
            0
        ].parent_ref().path == ("TrafficLight", "InService")
        assert not state_trafficlight_inservice.abstract_on_durings[0].is_aspect
        assert not state_trafficlight_inservice.abstract_on_durings[0].is_ref
        assert (
            state_trafficlight_inservice.abstract_on_durings[0].parent.name
            == "InService"
        )
        assert state_trafficlight_inservice.abstract_on_durings[0].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.abstract_on_durings[1].stage == "during"
        assert state_trafficlight_inservice.abstract_on_durings[1].aspect == "after"
        assert (
            state_trafficlight_inservice.abstract_on_durings[1].name
            == "InServiceAfterEnterChild"
        )
        assert (
            state_trafficlight_inservice.abstract_on_durings[1].doc
            == "Abstract Operation After Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert state_trafficlight_inservice.abstract_on_durings[1].operations == []
        assert state_trafficlight_inservice.abstract_on_durings[1].is_abstract
        assert state_trafficlight_inservice.abstract_on_durings[1].state_path == (
            "TrafficLight",
            "InService",
            "InServiceAfterEnterChild",
        )
        assert state_trafficlight_inservice.abstract_on_durings[1].ref is None
        assert (
            state_trafficlight_inservice.abstract_on_durings[1].ref_state_path is None
        )
        assert (
            state_trafficlight_inservice.abstract_on_durings[1].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice.abstract_on_durings[
            1
        ].parent_ref().path == ("TrafficLight", "InService")
        assert not state_trafficlight_inservice.abstract_on_durings[1].is_aspect
        assert not state_trafficlight_inservice.abstract_on_durings[1].is_ref
        assert (
            state_trafficlight_inservice.abstract_on_durings[1].parent.name
            == "InService"
        )
        assert state_trafficlight_inservice.abstract_on_durings[1].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert len(state_trafficlight_inservice.abstract_on_enters) == 1
        assert state_trafficlight_inservice.abstract_on_enters[0].stage == "enter"
        assert state_trafficlight_inservice.abstract_on_enters[0].aspect is None
        assert (
            state_trafficlight_inservice.abstract_on_enters[0].name
            == "InServiceAbstractEnter"
        )
        assert (
            state_trafficlight_inservice.abstract_on_enters[0].doc
            == "Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert state_trafficlight_inservice.abstract_on_enters[0].operations == []
        assert state_trafficlight_inservice.abstract_on_enters[0].is_abstract
        assert state_trafficlight_inservice.abstract_on_enters[0].state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractEnter",
        )
        assert state_trafficlight_inservice.abstract_on_enters[0].ref is None
        assert state_trafficlight_inservice.abstract_on_enters[0].ref_state_path is None
        assert (
            state_trafficlight_inservice.abstract_on_enters[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice.abstract_on_enters[0].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert not state_trafficlight_inservice.abstract_on_enters[0].is_aspect
        assert not state_trafficlight_inservice.abstract_on_enters[0].is_ref
        assert (
            state_trafficlight_inservice.abstract_on_enters[0].parent.name
            == "InService"
        )
        assert state_trafficlight_inservice.abstract_on_enters[0].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert len(state_trafficlight_inservice.abstract_on_exits) == 1
        assert state_trafficlight_inservice.abstract_on_exits[0].stage == "exit"
        assert state_trafficlight_inservice.abstract_on_exits[0].aspect is None
        assert (
            state_trafficlight_inservice.abstract_on_exits[0].name
            == "InServiceAbstractExit"
        )
        assert (
            state_trafficlight_inservice.abstract_on_exits[0].doc
            == "Abstract Operation When Leaving State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert state_trafficlight_inservice.abstract_on_exits[0].operations == []
        assert state_trafficlight_inservice.abstract_on_exits[0].is_abstract
        assert state_trafficlight_inservice.abstract_on_exits[0].state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractExit",
        )
        assert state_trafficlight_inservice.abstract_on_exits[0].ref is None
        assert state_trafficlight_inservice.abstract_on_exits[0].ref_state_path is None
        assert (
            state_trafficlight_inservice.abstract_on_exits[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice.abstract_on_exits[0].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert not state_trafficlight_inservice.abstract_on_exits[0].is_aspect
        assert not state_trafficlight_inservice.abstract_on_exits[0].is_ref
        assert (
            state_trafficlight_inservice.abstract_on_exits[0].parent.name == "InService"
        )
        assert state_trafficlight_inservice.abstract_on_exits[0].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert len(state_trafficlight_inservice.init_transitions) == 1
        assert state_trafficlight_inservice.init_transitions[0].from_state == INIT_STATE
        assert state_trafficlight_inservice.init_transitions[0].to_state == "Red"
        assert state_trafficlight_inservice.init_transitions[0].event == Event(
            name="Start", state_path=("TrafficLight", "InService"), extra_name=None
        )
        assert state_trafficlight_inservice.init_transitions[0].guard is None
        assert state_trafficlight_inservice.init_transitions[0].effects == [
            Operation(var_name="b", expr=Integer(value=1))
        ]
        assert (
            state_trafficlight_inservice.init_transitions[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice.init_transitions[0].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert not state_trafficlight_inservice.is_leaf_state
        assert not state_trafficlight_inservice.is_root_state
        assert not state_trafficlight_inservice.is_stoppable
        assert state_trafficlight_inservice.non_abstract_on_during_aspects == []
        assert state_trafficlight_inservice.non_abstract_on_durings == []
        assert len(state_trafficlight_inservice.non_abstract_on_enters) == 1
        assert state_trafficlight_inservice.non_abstract_on_enters[0].stage == "enter"
        assert state_trafficlight_inservice.non_abstract_on_enters[0].aspect is None
        assert state_trafficlight_inservice.non_abstract_on_enters[0].name is None
        assert state_trafficlight_inservice.non_abstract_on_enters[0].doc is None
        assert state_trafficlight_inservice.non_abstract_on_enters[0].operations == [
            Operation(var_name="a", expr=Integer(value=0)),
            Operation(var_name="b", expr=Integer(value=0)),
            Operation(var_name="round_count", expr=Integer(value=0)),
        ]
        assert not state_trafficlight_inservice.non_abstract_on_enters[0].is_abstract
        assert state_trafficlight_inservice.non_abstract_on_enters[0].state_path == (
            "TrafficLight",
            "InService",
            None,
        )
        assert state_trafficlight_inservice.non_abstract_on_enters[0].ref is None
        assert (
            state_trafficlight_inservice.non_abstract_on_enters[0].ref_state_path
            is None
        )
        assert (
            state_trafficlight_inservice.non_abstract_on_enters[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice.non_abstract_on_enters[
            0
        ].parent_ref().path == ("TrafficLight", "InService")
        assert not state_trafficlight_inservice.non_abstract_on_enters[0].is_aspect
        assert not state_trafficlight_inservice.non_abstract_on_enters[0].is_ref
        assert (
            state_trafficlight_inservice.non_abstract_on_enters[0].parent.name
            == "InService"
        )
        assert state_trafficlight_inservice.non_abstract_on_enters[0].parent.path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.non_abstract_on_exits == []
        assert state_trafficlight_inservice.parent.name == "TrafficLight"
        assert state_trafficlight_inservice.parent.path == ("TrafficLight",)
        assert len(state_trafficlight_inservice.transitions_entering_children) == 1
        assert (
            state_trafficlight_inservice.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert (
            state_trafficlight_inservice.transitions_entering_children[0].to_state
            == "Red"
        )
        assert state_trafficlight_inservice.transitions_entering_children[
            0
        ].event == Event(
            name="Start", state_path=("TrafficLight", "InService"), extra_name=None
        )
        assert (
            state_trafficlight_inservice.transitions_entering_children[0].guard is None
        )
        assert state_trafficlight_inservice.transitions_entering_children[
            0
        ].effects == [Operation(var_name="b", expr=Integer(value=1))]
        assert (
            state_trafficlight_inservice.transitions_entering_children[0]
            .parent_ref()
            .name
            == "InService"
        )
        assert state_trafficlight_inservice.transitions_entering_children[
            0
        ].parent_ref().path == ("TrafficLight", "InService")
        assert (
            len(state_trafficlight_inservice.transitions_entering_children_simplified)
            == 2
        )
        assert (
            state_trafficlight_inservice.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_trafficlight_inservice.transitions_entering_children_simplified[
                0
            ].to_state
            == "Red"
        )
        assert state_trafficlight_inservice.transitions_entering_children_simplified[
            0
        ].event == Event(
            name="Start", state_path=("TrafficLight", "InService"), extra_name=None
        )
        assert (
            state_trafficlight_inservice.transitions_entering_children_simplified[
                0
            ].guard
            is None
        )
        assert state_trafficlight_inservice.transitions_entering_children_simplified[
            0
        ].effects == [Operation(var_name="b", expr=Integer(value=1))]
        assert (
            state_trafficlight_inservice.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "InService"
        )
        assert state_trafficlight_inservice.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice.transitions_entering_children_simplified[1]
            is None
        )
        assert len(state_trafficlight_inservice.transitions_from) == 1
        assert (
            state_trafficlight_inservice.transitions_from[0].from_state == "InService"
        )
        assert state_trafficlight_inservice.transitions_from[0].to_state == "Idle"
        assert state_trafficlight_inservice.transitions_from[0].event == Event(
            name="Maintain", state_path=("TrafficLight", "InService"), extra_name=None
        )
        assert state_trafficlight_inservice.transitions_from[0].guard is None
        assert state_trafficlight_inservice.transitions_from[0].effects == []
        assert (
            state_trafficlight_inservice.transitions_from[0].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_inservice.transitions_from[0].parent_ref().path == (
            "TrafficLight",
        )
        assert len(state_trafficlight_inservice.transitions_to) == 1
        assert state_trafficlight_inservice.transitions_to[0].from_state == INIT_STATE
        assert state_trafficlight_inservice.transitions_to[0].to_state == "InService"
        assert state_trafficlight_inservice.transitions_to[0].event is None
        assert state_trafficlight_inservice.transitions_to[0].guard is None
        assert state_trafficlight_inservice.transitions_to[0].effects == []
        assert (
            state_trafficlight_inservice.transitions_to[0].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_inservice.transitions_to[0].parent_ref().path == (
            "TrafficLight",
        )

    def test_state_trafficlight_inservice_to_ast_node(
        self, state_trafficlight_inservice
    ):
        ast_node = state_trafficlight_inservice.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="InService",
            extra_name=None,
            events=[
                dsl_nodes.EventDefinition(name="Start", extra_name=None),
                dsl_nodes.EventDefinition(name="Maintain", extra_name=None),
            ],
            substates=[
                dsl_nodes.StateDefinition(
                    name="Red",
                    extra_name=None,
                    events=[],
                    substates=[],
                    transitions=[],
                    enters=[],
                    durings=[
                        dsl_nodes.DuringOperations(
                            aspect=None,
                            operations=[
                                dsl_nodes.OperationAssignment(
                                    name="a",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Integer(raw="1"),
                                        op="<<",
                                        expr2=dsl_nodes.Integer(raw="2"),
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
                dsl_nodes.StateDefinition(
                    name="Yellow",
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
                    name="Green",
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
                    to_state="Red",
                    event_id=dsl_nodes.ChainID(path=["Start"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="b", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Red",
                    to_state="Green",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="b", expr=dsl_nodes.Integer(raw="3")
                        )
                    ],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Green",
                    to_state="Yellow",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="b", expr=dsl_nodes.Integer(raw="2")
                        )
                    ],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Yellow",
                    to_state="Red",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="a"),
                        op=">=",
                        expr2=dsl_nodes.Integer(raw="10"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="b", expr=dsl_nodes.Integer(raw="1")
                        ),
                        dsl_nodes.OperationAssignment(
                            name="round_count",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="round_count"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
                    ],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Green",
                    to_state="Yellow",
                    event_id=dsl_nodes.ChainID(path=["Idle", "E2"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Yellow",
                    to_state="Yellow",
                    event_id=dsl_nodes.ChainID(path=["E2"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[],
                ),
            ],
            enters=[
                dsl_nodes.EnterOperations(
                    operations=[
                        dsl_nodes.OperationAssignment(
                            name="a", expr=dsl_nodes.Integer(raw="0")
                        ),
                        dsl_nodes.OperationAssignment(
                            name="b", expr=dsl_nodes.Integer(raw="0")
                        ),
                        dsl_nodes.OperationAssignment(
                            name="round_count", expr=dsl_nodes.Integer(raw="0")
                        ),
                    ],
                    name=None,
                ),
                dsl_nodes.EnterAbstractFunction(
                    name="InServiceAbstractEnter",
                    doc="Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework",
                ),
            ],
            durings=[
                dsl_nodes.DuringAbstractFunction(
                    name="InServiceBeforeEnterChild",
                    aspect="before",
                    doc="Abstract Operation Before Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework",
                ),
                dsl_nodes.DuringAbstractFunction(
                    name="InServiceAfterEnterChild",
                    aspect="after",
                    doc="Abstract Operation After Entering Child States of State 'InService'\nTODO: Should be Implemented In Generated Code Framework",
                ),
            ],
            exits=[
                dsl_nodes.ExitAbstractFunction(
                    name="InServiceAbstractExit",
                    doc="Abstract Operation When Leaving State 'InService'\nTODO: Should be Implemented In Generated Code Framework",
                )
            ],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_trafficlight_inservice_list_on_enters(
        self, state_trafficlight_inservice
    ):
        lst = state_trafficlight_inservice.list_on_enters()
        assert len(lst) == 2
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=0)),
            Operation(var_name="b", expr=Integer(value=0)),
            Operation(var_name="round_count", expr=Integer(value=0)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "InService", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")
        on_stage = lst[1]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InServiceAbstractEnter"
        assert (
            on_stage.doc
            == "Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractEnter",
        )
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")

        lst = state_trafficlight_inservice.list_on_enters(with_ids=False)
        assert len(lst) == 2
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=0)),
            Operation(var_name="b", expr=Integer(value=0)),
            Operation(var_name="round_count", expr=Integer(value=0)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "InService", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")
        on_stage = lst[1]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InServiceAbstractEnter"
        assert (
            on_stage.doc
            == "Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractEnter",
        )
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")

        lst = state_trafficlight_inservice.list_on_enters(with_ids=True)
        assert len(lst) == 2
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=0)),
            Operation(var_name="b", expr=Integer(value=0)),
            Operation(var_name="round_count", expr=Integer(value=0)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "InService", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")
        id_, on_stage = lst[1]
        assert id_ == 2
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InServiceAbstractEnter"
        assert (
            on_stage.doc
            == "Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractEnter",
        )
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")

        lst = state_trafficlight_inservice.list_on_enters(is_abstract=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=0)),
            Operation(var_name="b", expr=Integer(value=0)),
            Operation(var_name="round_count", expr=Integer(value=0)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "InService", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")

        lst = state_trafficlight_inservice.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=0)),
            Operation(var_name="b", expr=Integer(value=0)),
            Operation(var_name="round_count", expr=Integer(value=0)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "InService", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")

        lst = state_trafficlight_inservice.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=0)),
            Operation(var_name="b", expr=Integer(value=0)),
            Operation(var_name="round_count", expr=Integer(value=0)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "InService", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")

        lst = state_trafficlight_inservice.list_on_enters(is_abstract=True)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InServiceAbstractEnter"
        assert (
            on_stage.doc
            == "Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractEnter",
        )
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")

        lst = state_trafficlight_inservice.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InServiceAbstractEnter"
        assert (
            on_stage.doc
            == "Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractEnter",
        )
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")

        lst = state_trafficlight_inservice.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 2
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "InServiceAbstractEnter"
        assert (
            on_stage.doc
            == "Abstract Operation When Entering State 'InService'\nTODO: Should be Implemented In Generated Code Framework"
        )
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == (
            "TrafficLight",
            "InService",
            "InServiceAbstractEnter",
        )
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "InService"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "InService"
        assert on_stage.parent.path == ("TrafficLight", "InService")

    def test_state_trafficlight_inservice_during_aspects(
        self, state_trafficlight_inservice
    ):
        lst = state_trafficlight_inservice.list_on_during_aspects()
        assert lst == []

        lst = state_trafficlight_inservice.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_trafficlight_inservice.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_trafficlight_inservice.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_trafficlight_inservice.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_inservice.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_trafficlight_inservice.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_trafficlight_inservice.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_inservice.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_trafficlight_inservice_red(self, state_trafficlight_inservice_red):
        assert state_trafficlight_inservice_red.name == "Red"
        assert state_trafficlight_inservice_red.path == (
            "TrafficLight",
            "InService",
            "Red",
        )
        assert sorted(state_trafficlight_inservice_red.substates.keys()) == []
        assert state_trafficlight_inservice_red.events == {}
        assert state_trafficlight_inservice_red.transitions == []
        assert state_trafficlight_inservice_red.named_functions == {}
        assert state_trafficlight_inservice_red.on_enters == []
        assert len(state_trafficlight_inservice_red.on_durings) == 1
        assert state_trafficlight_inservice_red.on_durings[0].stage == "during"
        assert state_trafficlight_inservice_red.on_durings[0].aspect is None
        assert state_trafficlight_inservice_red.on_durings[0].name is None
        assert state_trafficlight_inservice_red.on_durings[0].doc is None
        assert state_trafficlight_inservice_red.on_durings[0].operations == [
            Operation(
                var_name="a",
                expr=BinaryOp(x=Integer(value=1), op="<<", y=Integer(value=2)),
            )
        ]
        assert not state_trafficlight_inservice_red.on_durings[0].is_abstract
        assert state_trafficlight_inservice_red.on_durings[0].state_path == (
            "TrafficLight",
            "InService",
            "Red",
            None,
        )
        assert state_trafficlight_inservice_red.on_durings[0].ref is None
        assert state_trafficlight_inservice_red.on_durings[0].ref_state_path is None
        assert state_trafficlight_inservice_red.on_durings[0].parent_ref().name == "Red"
        assert state_trafficlight_inservice_red.on_durings[0].parent_ref().path == (
            "TrafficLight",
            "InService",
            "Red",
        )
        assert not state_trafficlight_inservice_red.on_durings[0].is_aspect
        assert not state_trafficlight_inservice_red.on_durings[0].is_ref
        assert state_trafficlight_inservice_red.on_durings[0].parent.name == "Red"
        assert state_trafficlight_inservice_red.on_durings[0].parent.path == (
            "TrafficLight",
            "InService",
            "Red",
        )
        assert state_trafficlight_inservice_red.on_exits == []
        assert state_trafficlight_inservice_red.on_during_aspects == []
        assert state_trafficlight_inservice_red.parent_ref().name == "InService"
        assert state_trafficlight_inservice_red.parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice_red.substate_name_to_id == {}
        assert state_trafficlight_inservice_red.extra_name is None
        assert not state_trafficlight_inservice_red.is_pseudo
        assert state_trafficlight_inservice_red.abstract_on_during_aspects == []
        assert state_trafficlight_inservice_red.abstract_on_durings == []
        assert state_trafficlight_inservice_red.abstract_on_enters == []
        assert state_trafficlight_inservice_red.abstract_on_exits == []
        assert state_trafficlight_inservice_red.init_transitions == []
        assert state_trafficlight_inservice_red.is_leaf_state
        assert not state_trafficlight_inservice_red.is_root_state
        assert state_trafficlight_inservice_red.is_stoppable
        assert state_trafficlight_inservice_red.non_abstract_on_during_aspects == []
        assert len(state_trafficlight_inservice_red.non_abstract_on_durings) == 1
        assert (
            state_trafficlight_inservice_red.non_abstract_on_durings[0].stage
            == "during"
        )
        assert (
            state_trafficlight_inservice_red.non_abstract_on_durings[0].aspect is None
        )
        assert state_trafficlight_inservice_red.non_abstract_on_durings[0].name is None
        assert state_trafficlight_inservice_red.non_abstract_on_durings[0].doc is None
        assert state_trafficlight_inservice_red.non_abstract_on_durings[
            0
        ].operations == [
            Operation(
                var_name="a",
                expr=BinaryOp(x=Integer(value=1), op="<<", y=Integer(value=2)),
            )
        ]
        assert not state_trafficlight_inservice_red.non_abstract_on_durings[
            0
        ].is_abstract
        assert state_trafficlight_inservice_red.non_abstract_on_durings[
            0
        ].state_path == ("TrafficLight", "InService", "Red", None)
        assert state_trafficlight_inservice_red.non_abstract_on_durings[0].ref is None
        assert (
            state_trafficlight_inservice_red.non_abstract_on_durings[0].ref_state_path
            is None
        )
        assert (
            state_trafficlight_inservice_red.non_abstract_on_durings[0]
            .parent_ref()
            .name
            == "Red"
        )
        assert state_trafficlight_inservice_red.non_abstract_on_durings[
            0
        ].parent_ref().path == ("TrafficLight", "InService", "Red")
        assert not state_trafficlight_inservice_red.non_abstract_on_durings[0].is_aspect
        assert not state_trafficlight_inservice_red.non_abstract_on_durings[0].is_ref
        assert (
            state_trafficlight_inservice_red.non_abstract_on_durings[0].parent.name
            == "Red"
        )
        assert state_trafficlight_inservice_red.non_abstract_on_durings[
            0
        ].parent.path == ("TrafficLight", "InService", "Red")
        assert state_trafficlight_inservice_red.non_abstract_on_enters == []
        assert state_trafficlight_inservice_red.non_abstract_on_exits == []
        assert state_trafficlight_inservice_red.parent.name == "InService"
        assert state_trafficlight_inservice_red.parent.path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice_red.transitions_entering_children == []
        assert (
            len(
                state_trafficlight_inservice_red.transitions_entering_children_simplified
            )
            == 1
        )
        assert (
            state_trafficlight_inservice_red.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_trafficlight_inservice_red.transitions_from) == 1
        assert state_trafficlight_inservice_red.transitions_from[0].from_state == "Red"
        assert state_trafficlight_inservice_red.transitions_from[0].to_state == "Green"
        assert state_trafficlight_inservice_red.transitions_from[0].event is None
        assert state_trafficlight_inservice_red.transitions_from[0].guard is None
        assert state_trafficlight_inservice_red.transitions_from[0].effects == [
            Operation(var_name="b", expr=Integer(value=3))
        ]
        assert (
            state_trafficlight_inservice_red.transitions_from[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_red.transitions_from[
            0
        ].parent_ref().path == ("TrafficLight", "InService")
        assert len(state_trafficlight_inservice_red.transitions_to) == 2
        assert (
            state_trafficlight_inservice_red.transitions_to[0].from_state == INIT_STATE
        )
        assert state_trafficlight_inservice_red.transitions_to[0].to_state == "Red"
        assert state_trafficlight_inservice_red.transitions_to[0].event == Event(
            name="Start", state_path=("TrafficLight", "InService"), extra_name=None
        )
        assert state_trafficlight_inservice_red.transitions_to[0].guard is None
        assert state_trafficlight_inservice_red.transitions_to[0].effects == [
            Operation(var_name="b", expr=Integer(value=1))
        ]
        assert (
            state_trafficlight_inservice_red.transitions_to[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_red.transitions_to[0].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice_red.transitions_to[1].from_state == "Yellow"
        assert state_trafficlight_inservice_red.transitions_to[1].to_state == "Red"
        assert state_trafficlight_inservice_red.transitions_to[1].event is None
        assert state_trafficlight_inservice_red.transitions_to[1].guard == BinaryOp(
            x=Variable(name="a"), op=">=", y=Integer(value=10)
        )
        assert state_trafficlight_inservice_red.transitions_to[1].effects == [
            Operation(var_name="b", expr=Integer(value=1)),
            Operation(
                var_name="round_count",
                expr=BinaryOp(
                    x=Variable(name="round_count"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert (
            state_trafficlight_inservice_red.transitions_to[1].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_red.transitions_to[1].parent_ref().path == (
            "TrafficLight",
            "InService",
        )

    def test_state_trafficlight_inservice_red_to_ast_node(
        self, state_trafficlight_inservice_red
    ):
        ast_node = state_trafficlight_inservice_red.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Red",
            extra_name=None,
            events=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[
                dsl_nodes.DuringOperations(
                    aspect=None,
                    operations=[
                        dsl_nodes.OperationAssignment(
                            name="a",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Integer(raw="1"),
                                op="<<",
                                expr2=dsl_nodes.Integer(raw="2"),
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

    def test_state_trafficlight_inservice_red_list_on_enters(
        self, state_trafficlight_inservice_red
    ):
        lst = state_trafficlight_inservice_red.list_on_enters()
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_trafficlight_inservice_red_during_aspects(
        self, state_trafficlight_inservice_red
    ):
        lst = state_trafficlight_inservice_red.list_on_during_aspects()
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_trafficlight_inservice_red_during_aspect_recursively(
        self, state_trafficlight_inservice_red
    ):
        lst = state_trafficlight_inservice_red.list_on_during_aspect_recursively()
        assert len(lst) == 5
        st, on_stage = lst[0]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[1]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[2]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[3]
        assert st.name == "Red"
        assert st.path == ("TrafficLight", "InService", "Red")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(
                var_name="a",
                expr=BinaryOp(x=Integer(value=1), op="<<", y=Integer(value=2)),
            )
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "InService", "Red", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "Red"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService", "Red")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "Red"
        assert on_stage.parent.path == ("TrafficLight", "InService", "Red")
        st, on_stage = lst[4]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight_inservice_red.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert len(lst) == 5
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[1]
        assert id_ == 2
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[2]
        assert id_ == 3
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[3]
        assert id_ == 1
        assert st.name == "Red"
        assert st.path == ("TrafficLight", "InService", "Red")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(
                var_name="a",
                expr=BinaryOp(x=Integer(value=1), op="<<", y=Integer(value=2)),
            )
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "InService", "Red", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "Red"
        assert on_stage.parent_ref().path == ("TrafficLight", "InService", "Red")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "Red"
        assert on_stage.parent.path == ("TrafficLight", "InService", "Red")
        id_, st, on_stage = lst[4]
        assert id_ == 4
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

    def test_state_trafficlight_inservice_yellow(
        self, state_trafficlight_inservice_yellow
    ):
        assert state_trafficlight_inservice_yellow.name == "Yellow"
        assert state_trafficlight_inservice_yellow.path == (
            "TrafficLight",
            "InService",
            "Yellow",
        )
        assert sorted(state_trafficlight_inservice_yellow.substates.keys()) == []
        assert state_trafficlight_inservice_yellow.events == {}
        assert state_trafficlight_inservice_yellow.transitions == []
        assert state_trafficlight_inservice_yellow.named_functions == {}
        assert state_trafficlight_inservice_yellow.on_enters == []
        assert state_trafficlight_inservice_yellow.on_durings == []
        assert state_trafficlight_inservice_yellow.on_exits == []
        assert state_trafficlight_inservice_yellow.on_during_aspects == []
        assert state_trafficlight_inservice_yellow.parent_ref().name == "InService"
        assert state_trafficlight_inservice_yellow.parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice_yellow.substate_name_to_id == {}
        assert state_trafficlight_inservice_yellow.extra_name is None
        assert not state_trafficlight_inservice_yellow.is_pseudo
        assert state_trafficlight_inservice_yellow.abstract_on_during_aspects == []
        assert state_trafficlight_inservice_yellow.abstract_on_durings == []
        assert state_trafficlight_inservice_yellow.abstract_on_enters == []
        assert state_trafficlight_inservice_yellow.abstract_on_exits == []
        assert state_trafficlight_inservice_yellow.init_transitions == []
        assert state_trafficlight_inservice_yellow.is_leaf_state
        assert not state_trafficlight_inservice_yellow.is_root_state
        assert state_trafficlight_inservice_yellow.is_stoppable
        assert state_trafficlight_inservice_yellow.non_abstract_on_during_aspects == []
        assert state_trafficlight_inservice_yellow.non_abstract_on_durings == []
        assert state_trafficlight_inservice_yellow.non_abstract_on_enters == []
        assert state_trafficlight_inservice_yellow.non_abstract_on_exits == []
        assert state_trafficlight_inservice_yellow.parent.name == "InService"
        assert state_trafficlight_inservice_yellow.parent.path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice_yellow.transitions_entering_children == []
        assert (
            len(
                state_trafficlight_inservice_yellow.transitions_entering_children_simplified
            )
            == 1
        )
        assert (
            state_trafficlight_inservice_yellow.transitions_entering_children_simplified[
                0
            ]
            is None
        )
        assert len(state_trafficlight_inservice_yellow.transitions_from) == 2
        assert (
            state_trafficlight_inservice_yellow.transitions_from[0].from_state
            == "Yellow"
        )
        assert state_trafficlight_inservice_yellow.transitions_from[0].to_state == "Red"
        assert state_trafficlight_inservice_yellow.transitions_from[0].event is None
        assert state_trafficlight_inservice_yellow.transitions_from[
            0
        ].guard == BinaryOp(x=Variable(name="a"), op=">=", y=Integer(value=10))
        assert state_trafficlight_inservice_yellow.transitions_from[0].effects == [
            Operation(var_name="b", expr=Integer(value=1)),
            Operation(
                var_name="round_count",
                expr=BinaryOp(
                    x=Variable(name="round_count"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert (
            state_trafficlight_inservice_yellow.transitions_from[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_yellow.transitions_from[
            0
        ].parent_ref().path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice_yellow.transitions_from[1].from_state
            == "Yellow"
        )
        assert (
            state_trafficlight_inservice_yellow.transitions_from[1].to_state == "Yellow"
        )
        assert state_trafficlight_inservice_yellow.transitions_from[1].event == Event(
            name="E2", state_path=("TrafficLight",), extra_name=None
        )
        assert state_trafficlight_inservice_yellow.transitions_from[1].guard is None
        assert state_trafficlight_inservice_yellow.transitions_from[1].effects == []
        assert (
            state_trafficlight_inservice_yellow.transitions_from[1].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_yellow.transitions_from[
            1
        ].parent_ref().path == ("TrafficLight", "InService")
        assert len(state_trafficlight_inservice_yellow.transitions_to) == 3
        assert (
            state_trafficlight_inservice_yellow.transitions_to[0].from_state == "Green"
        )
        assert (
            state_trafficlight_inservice_yellow.transitions_to[0].to_state == "Yellow"
        )
        assert state_trafficlight_inservice_yellow.transitions_to[0].event is None
        assert state_trafficlight_inservice_yellow.transitions_to[0].guard is None
        assert state_trafficlight_inservice_yellow.transitions_to[0].effects == [
            Operation(var_name="b", expr=Integer(value=2))
        ]
        assert (
            state_trafficlight_inservice_yellow.transitions_to[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_yellow.transitions_to[
            0
        ].parent_ref().path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice_yellow.transitions_to[1].from_state == "Green"
        )
        assert (
            state_trafficlight_inservice_yellow.transitions_to[1].to_state == "Yellow"
        )
        assert state_trafficlight_inservice_yellow.transitions_to[1].event == Event(
            name="E2", state_path=("TrafficLight", "Idle"), extra_name=None
        )
        assert state_trafficlight_inservice_yellow.transitions_to[1].guard is None
        assert state_trafficlight_inservice_yellow.transitions_to[1].effects == []
        assert (
            state_trafficlight_inservice_yellow.transitions_to[1].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_yellow.transitions_to[
            1
        ].parent_ref().path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice_yellow.transitions_to[2].from_state == "Yellow"
        )
        assert (
            state_trafficlight_inservice_yellow.transitions_to[2].to_state == "Yellow"
        )
        assert state_trafficlight_inservice_yellow.transitions_to[2].event == Event(
            name="E2", state_path=("TrafficLight",), extra_name=None
        )
        assert state_trafficlight_inservice_yellow.transitions_to[2].guard is None
        assert state_trafficlight_inservice_yellow.transitions_to[2].effects == []
        assert (
            state_trafficlight_inservice_yellow.transitions_to[2].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_yellow.transitions_to[
            2
        ].parent_ref().path == ("TrafficLight", "InService")

    def test_state_trafficlight_inservice_yellow_to_ast_node(
        self, state_trafficlight_inservice_yellow
    ):
        ast_node = state_trafficlight_inservice_yellow.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Yellow",
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

    def test_state_trafficlight_inservice_yellow_list_on_enters(
        self, state_trafficlight_inservice_yellow
    ):
        lst = state_trafficlight_inservice_yellow.list_on_enters()
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_trafficlight_inservice_yellow_during_aspects(
        self, state_trafficlight_inservice_yellow
    ):
        lst = state_trafficlight_inservice_yellow.list_on_during_aspects()
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_during_aspects(
            aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_during_aspects(
            is_abstract=False
        )
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_during_aspects(
            is_abstract=True
        )
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_trafficlight_inservice_yellow_during_aspect_recursively(
        self, state_trafficlight_inservice_yellow
    ):
        lst = state_trafficlight_inservice_yellow.list_on_during_aspect_recursively()
        assert len(lst) == 4
        st, on_stage = lst[0]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[1]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[2]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[3]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight_inservice_yellow.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert len(lst) == 4
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[1]
        assert id_ == 2
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[2]
        assert id_ == 3
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[3]
        assert id_ == 4
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

    def test_state_trafficlight_inservice_green(
        self, state_trafficlight_inservice_green
    ):
        assert state_trafficlight_inservice_green.name == "Green"
        assert state_trafficlight_inservice_green.path == (
            "TrafficLight",
            "InService",
            "Green",
        )
        assert sorted(state_trafficlight_inservice_green.substates.keys()) == []
        assert state_trafficlight_inservice_green.events == {}
        assert state_trafficlight_inservice_green.transitions == []
        assert state_trafficlight_inservice_green.named_functions == {}
        assert state_trafficlight_inservice_green.on_enters == []
        assert state_trafficlight_inservice_green.on_durings == []
        assert state_trafficlight_inservice_green.on_exits == []
        assert state_trafficlight_inservice_green.on_during_aspects == []
        assert state_trafficlight_inservice_green.parent_ref().name == "InService"
        assert state_trafficlight_inservice_green.parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice_green.substate_name_to_id == {}
        assert state_trafficlight_inservice_green.extra_name is None
        assert not state_trafficlight_inservice_green.is_pseudo
        assert state_trafficlight_inservice_green.abstract_on_during_aspects == []
        assert state_trafficlight_inservice_green.abstract_on_durings == []
        assert state_trafficlight_inservice_green.abstract_on_enters == []
        assert state_trafficlight_inservice_green.abstract_on_exits == []
        assert state_trafficlight_inservice_green.init_transitions == []
        assert state_trafficlight_inservice_green.is_leaf_state
        assert not state_trafficlight_inservice_green.is_root_state
        assert state_trafficlight_inservice_green.is_stoppable
        assert state_trafficlight_inservice_green.non_abstract_on_during_aspects == []
        assert state_trafficlight_inservice_green.non_abstract_on_durings == []
        assert state_trafficlight_inservice_green.non_abstract_on_enters == []
        assert state_trafficlight_inservice_green.non_abstract_on_exits == []
        assert state_trafficlight_inservice_green.parent.name == "InService"
        assert state_trafficlight_inservice_green.parent.path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice_green.transitions_entering_children == []
        assert (
            len(
                state_trafficlight_inservice_green.transitions_entering_children_simplified
            )
            == 1
        )
        assert (
            state_trafficlight_inservice_green.transitions_entering_children_simplified[
                0
            ]
            is None
        )
        assert len(state_trafficlight_inservice_green.transitions_from) == 2
        assert (
            state_trafficlight_inservice_green.transitions_from[0].from_state == "Green"
        )
        assert (
            state_trafficlight_inservice_green.transitions_from[0].to_state == "Yellow"
        )
        assert state_trafficlight_inservice_green.transitions_from[0].event is None
        assert state_trafficlight_inservice_green.transitions_from[0].guard is None
        assert state_trafficlight_inservice_green.transitions_from[0].effects == [
            Operation(var_name="b", expr=Integer(value=2))
        ]
        assert (
            state_trafficlight_inservice_green.transitions_from[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_green.transitions_from[
            0
        ].parent_ref().path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice_green.transitions_from[1].from_state == "Green"
        )
        assert (
            state_trafficlight_inservice_green.transitions_from[1].to_state == "Yellow"
        )
        assert state_trafficlight_inservice_green.transitions_from[1].event == Event(
            name="E2", state_path=("TrafficLight", "Idle"), extra_name=None
        )
        assert state_trafficlight_inservice_green.transitions_from[1].guard is None
        assert state_trafficlight_inservice_green.transitions_from[1].effects == []
        assert (
            state_trafficlight_inservice_green.transitions_from[1].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_green.transitions_from[
            1
        ].parent_ref().path == ("TrafficLight", "InService")
        assert len(state_trafficlight_inservice_green.transitions_to) == 1
        assert state_trafficlight_inservice_green.transitions_to[0].from_state == "Red"
        assert state_trafficlight_inservice_green.transitions_to[0].to_state == "Green"
        assert state_trafficlight_inservice_green.transitions_to[0].event is None
        assert state_trafficlight_inservice_green.transitions_to[0].guard is None
        assert state_trafficlight_inservice_green.transitions_to[0].effects == [
            Operation(var_name="b", expr=Integer(value=3))
        ]
        assert (
            state_trafficlight_inservice_green.transitions_to[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_green.transitions_to[
            0
        ].parent_ref().path == ("TrafficLight", "InService")

    def test_state_trafficlight_inservice_green_to_ast_node(
        self, state_trafficlight_inservice_green
    ):
        ast_node = state_trafficlight_inservice_green.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Green",
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

    def test_state_trafficlight_inservice_green_list_on_enters(
        self, state_trafficlight_inservice_green
    ):
        lst = state_trafficlight_inservice_green.list_on_enters()
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_trafficlight_inservice_green_during_aspects(
        self, state_trafficlight_inservice_green
    ):
        lst = state_trafficlight_inservice_green.list_on_during_aspects()
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_during_aspects(
            is_abstract=False
        )
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_during_aspects(
            is_abstract=True
        )
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_trafficlight_inservice_green_during_aspect_recursively(
        self, state_trafficlight_inservice_green
    ):
        lst = state_trafficlight_inservice_green.list_on_during_aspect_recursively()
        assert len(lst) == 4
        st, on_stage = lst[0]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[1]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[2]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[3]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight_inservice_green.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert len(lst) == 4
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[1]
        assert id_ == 2
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[2]
        assert id_ == 3
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[3]
        assert id_ == 4
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

    def test_state_trafficlight_idle(self, state_trafficlight_idle):
        assert state_trafficlight_idle.name == "Idle"
        assert state_trafficlight_idle.path == ("TrafficLight", "Idle")
        assert sorted(state_trafficlight_idle.substates.keys()) == []
        assert state_trafficlight_idle.events == {
            "E2": Event(name="E2", state_path=("TrafficLight", "Idle"), extra_name=None)
        }
        assert state_trafficlight_idle.transitions == []
        assert state_trafficlight_idle.named_functions == {}
        assert state_trafficlight_idle.on_enters == []
        assert state_trafficlight_idle.on_durings == []
        assert state_trafficlight_idle.on_exits == []
        assert state_trafficlight_idle.on_during_aspects == []
        assert state_trafficlight_idle.parent_ref().name == "TrafficLight"
        assert state_trafficlight_idle.parent_ref().path == ("TrafficLight",)
        assert state_trafficlight_idle.substate_name_to_id == {}
        assert state_trafficlight_idle.extra_name is None
        assert not state_trafficlight_idle.is_pseudo
        assert state_trafficlight_idle.abstract_on_during_aspects == []
        assert state_trafficlight_idle.abstract_on_durings == []
        assert state_trafficlight_idle.abstract_on_enters == []
        assert state_trafficlight_idle.abstract_on_exits == []
        assert state_trafficlight_idle.init_transitions == []
        assert state_trafficlight_idle.is_leaf_state
        assert not state_trafficlight_idle.is_root_state
        assert state_trafficlight_idle.is_stoppable
        assert state_trafficlight_idle.non_abstract_on_during_aspects == []
        assert state_trafficlight_idle.non_abstract_on_durings == []
        assert state_trafficlight_idle.non_abstract_on_enters == []
        assert state_trafficlight_idle.non_abstract_on_exits == []
        assert state_trafficlight_idle.parent.name == "TrafficLight"
        assert state_trafficlight_idle.parent.path == ("TrafficLight",)
        assert state_trafficlight_idle.transitions_entering_children == []
        assert (
            len(state_trafficlight_idle.transitions_entering_children_simplified) == 1
        )
        assert (
            state_trafficlight_idle.transitions_entering_children_simplified[0] is None
        )
        assert len(state_trafficlight_idle.transitions_from) == 2
        assert state_trafficlight_idle.transitions_from[0].from_state == "Idle"
        assert state_trafficlight_idle.transitions_from[0].to_state == "Idle"
        assert state_trafficlight_idle.transitions_from[0].event == Event(
            name="E2", state_path=("TrafficLight", "Idle"), extra_name=None
        )
        assert state_trafficlight_idle.transitions_from[0].guard is None
        assert state_trafficlight_idle.transitions_from[0].effects == []
        assert (
            state_trafficlight_idle.transitions_from[0].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_idle.transitions_from[0].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight_idle.transitions_from[1].from_state == "Idle"
        assert state_trafficlight_idle.transitions_from[1].to_state == EXIT_STATE
        assert state_trafficlight_idle.transitions_from[1].event is None
        assert state_trafficlight_idle.transitions_from[1].guard is None
        assert state_trafficlight_idle.transitions_from[1].effects == []
        assert (
            state_trafficlight_idle.transitions_from[1].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_idle.transitions_from[1].parent_ref().path == (
            "TrafficLight",
        )
        assert len(state_trafficlight_idle.transitions_to) == 2
        assert state_trafficlight_idle.transitions_to[0].from_state == "InService"
        assert state_trafficlight_idle.transitions_to[0].to_state == "Idle"
        assert state_trafficlight_idle.transitions_to[0].event == Event(
            name="Maintain", state_path=("TrafficLight", "InService"), extra_name=None
        )
        assert state_trafficlight_idle.transitions_to[0].guard is None
        assert state_trafficlight_idle.transitions_to[0].effects == []
        assert (
            state_trafficlight_idle.transitions_to[0].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_idle.transitions_to[0].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight_idle.transitions_to[1].from_state == "Idle"
        assert state_trafficlight_idle.transitions_to[1].to_state == "Idle"
        assert state_trafficlight_idle.transitions_to[1].event == Event(
            name="E2", state_path=("TrafficLight", "Idle"), extra_name=None
        )
        assert state_trafficlight_idle.transitions_to[1].guard is None
        assert state_trafficlight_idle.transitions_to[1].effects == []
        assert (
            state_trafficlight_idle.transitions_to[1].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_idle.transitions_to[1].parent_ref().path == (
            "TrafficLight",
        )

    def test_state_trafficlight_idle_to_ast_node(self, state_trafficlight_idle):
        ast_node = state_trafficlight_idle.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="Idle",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E2", extra_name=None)],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_trafficlight_idle_list_on_enters(self, state_trafficlight_idle):
        lst = state_trafficlight_idle.list_on_enters()
        assert lst == []

        lst = state_trafficlight_idle.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_trafficlight_idle.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_trafficlight_idle.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_trafficlight_idle.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_trafficlight_idle.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_trafficlight_idle.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_trafficlight_idle.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_trafficlight_idle.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_trafficlight_idle_during_aspects(self, state_trafficlight_idle):
        lst = state_trafficlight_idle.list_on_during_aspects()
        assert lst == []

        lst = state_trafficlight_idle.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_trafficlight_idle.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_trafficlight_idle.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_trafficlight_idle.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_idle.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_trafficlight_idle.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_trafficlight_idle.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_trafficlight_idle.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_trafficlight_idle_during_aspect_recursively(
        self, state_trafficlight_idle
    ):
        lst = state_trafficlight_idle.list_on_during_aspect_recursively()
        assert len(lst) == 4
        st, on_stage = lst[0]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[1]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[2]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        st, on_stage = lst[3]
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

        lst = state_trafficlight_idle.list_on_during_aspect_recursively(with_ids=True)
        assert len(lst) == 4
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [Operation(var_name="a", expr=Integer(value=0))]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[1]
        assert id_ == 2
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "FFT"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "FFT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[2]
        assert id_ == 3
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name == "TTT"
        assert on_stage.doc == "this is the line"
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", "TTT")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)
        id_, st, on_stage = lst[3]
        assert id_ == 4
        assert st.name == "TrafficLight"
        assert st.path == ("TrafficLight",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="a", expr=Integer(value=255)),
            Operation(var_name="b", expr=Integer(value=1)),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("TrafficLight", None)
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "TrafficLight"
        assert on_stage.parent_ref().path == ("TrafficLight",)
        assert on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "TrafficLight"
        assert on_stage.parent.path == ("TrafficLight",)

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int a = 0;
def int b = 0 * 0;
def int round_count = 0;
state TrafficLight {
    >> during before {
        a = 0;
    }
    >> during before abstract FFT;
    >> during before abstract TTT /*
        this is the line
    */
    >> during after {
        a = 255;
        b = 1;
    }
    state InService {
        enter {
            a = 0;
            b = 0;
            round_count = 0;
        }
        enter abstract InServiceAbstractEnter /*
            Abstract Operation When Entering State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */
        during before abstract InServiceBeforeEnterChild /*
            Abstract Operation Before Entering Child States of State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */
        during after abstract InServiceAfterEnterChild /*
            Abstract Operation After Entering Child States of State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */
        exit abstract InServiceAbstractExit /*
            Abstract Operation When Leaving State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */
        state Red {
            during {
                a = 1 << 2;
            }
        }
        state Yellow;
        state Green;
        event Start;
        event Maintain;
        [*] -> Red :: Start effect {
            b = 1;
        }
        Red -> Green effect {
            b = 3;
        }
        Green -> Yellow effect {
            b = 2;
        }
        Yellow -> Red : if [a >= 10] effect {
            b = 1;
            round_count = round_count + 1;
        }
        Green -> Yellow : /Idle.E2;
        Yellow -> Yellow : /E2;
    }
    state Idle {
        event E2;
    }
    event E2;
    [*] -> InService;
    InService -> Idle :: Maintain;
    Idle -> Idle :: E2;
    Idle -> [*];
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
    def int a = 0;
    def int b = 0 * 0;
    def int round_count = 0;
}
end note

state "TrafficLight" as traffic_light {
    state "InService" as traffic_light__in_service {
        state "Red" as traffic_light__in_service__red
        traffic_light__in_service__red : during {\\n    a = 1 << 2;\\n}
        state "Yellow" as traffic_light__in_service__yellow
        state "Green" as traffic_light__in_service__green
        [*] --> traffic_light__in_service__red : Start
        note on link
        effect {
            b = 1;
        }
        end note
        traffic_light__in_service__red --> traffic_light__in_service__green
        note on link
        effect {
            b = 3;
        }
        end note
        traffic_light__in_service__green --> traffic_light__in_service__yellow
        note on link
        effect {
            b = 2;
        }
        end note
        traffic_light__in_service__yellow --> traffic_light__in_service__red : a >= 10
        note on link
        effect {
            b = 1;
            round_count = round_count + 1;
        }
        end note
        traffic_light__in_service__green --> traffic_light__in_service__yellow : /Idle.E2
        traffic_light__in_service__yellow --> traffic_light__in_service__yellow : /E2
    }
    traffic_light__in_service : enter {\\n    a = 0;\\n    b = 0;\\n    round_count = 0;\\n}\\nenter abstract InServiceAbstractEnter /*\\n    Abstract Operation When Entering State 'InService'\\n    TODO: Should be Implemented In Generated Code Framework\\n*/\\nduring before abstract InServiceBeforeEnterChild /*\\n    Abstract Operation Before Entering Child States of State 'InService'\\n    TODO: Should be Implemented In Generated Code Framework\\n*/\\nduring after abstract InServiceAfterEnterChild /*\\n    Abstract Operation After Entering Child States of State 'InService'\\n    TODO: Should be Implemented In Generated Code Framework\\n*/\\nexit abstract InServiceAbstractExit /*\\n    Abstract Operation When Leaving State 'InService'\\n    TODO: Should be Implemented In Generated Code Framework\\n*/
    state "Idle" as traffic_light__idle
    [*] --> traffic_light__in_service
    traffic_light__in_service --> traffic_light__idle : InService.Maintain
    traffic_light__idle --> traffic_light__idle : Idle.E2
    traffic_light__idle --> [*]
}
traffic_light : >> during before {\\n    a = 0;\\n}\\n>> during before abstract FFT;\\n>> during before abstract TTT /*\\n    this is the line\\n*/\\n>> during after {\\n    a = 255;\\n    b = 1;\\n}
[*] --> traffic_light
traffic_light --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml()),
        )
