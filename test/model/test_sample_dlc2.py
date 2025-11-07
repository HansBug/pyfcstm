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
def int b = 0x0;
def int round_count = 0;  // define variables
state TrafficLight {
    !InService -> [*] :: ServiceError;
    !Idle -> InService :: GiveUpThinking;
    !* -> [*] :: GodDamnFuckUp; 
    state InService {
        state Red;
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
    state Idle {
        state ToBe;
        state NotToBe;

        [*] -> ToBe;
        ToBe -> NotToBe :: E1;
        NotToBe -> ToBe :: E1;
        NotToBe -> [*] :: E2;
    }

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


@pytest.fixture()
def state_trafficlight_idle_tobe(state_trafficlight_idle):
    return state_trafficlight_idle.substates["ToBe"]


@pytest.fixture()
def state_trafficlight_idle_nottobe(state_trafficlight_idle):
    return state_trafficlight_idle.substates["NotToBe"]


@pytest.mark.unittest
class TestModelStateTrafficLight:
    def test_model(self, model):
        assert model.defines == {
            "a": VarDefine(name="a", type="int", init=Integer(value=0)),
            "b": VarDefine(name="b", type="int", init=Integer(value=0)),
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
                name="b", type="int", expr=dsl_nodes.Integer(raw="0")
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
            "GodDamnFuckUp": Event(name="GodDamnFuckUp", state_path=("TrafficLight",)),
            "E2": Event(name="E2", state_path=("TrafficLight",)),
        }
        assert len(state_trafficlight.transitions) == 8
        assert state_trafficlight.transitions[0].from_state == "InService"
        assert state_trafficlight.transitions[0].to_state == EXIT_STATE
        assert state_trafficlight.transitions[0].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert state_trafficlight.transitions[0].guard is None
        assert state_trafficlight.transitions[0].effects == []
        assert state_trafficlight.transitions[0].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[0].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[1].from_state == "InService"
        assert state_trafficlight.transitions[1].to_state == EXIT_STATE
        assert state_trafficlight.transitions[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight.transitions[1].guard is None
        assert state_trafficlight.transitions[1].effects == []
        assert state_trafficlight.transitions[1].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[1].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[2].from_state == "Idle"
        assert state_trafficlight.transitions[2].to_state == "InService"
        assert state_trafficlight.transitions[2].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight.transitions[2].guard is None
        assert state_trafficlight.transitions[2].effects == []
        assert state_trafficlight.transitions[2].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[2].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[3].from_state == "Idle"
        assert state_trafficlight.transitions[3].to_state == EXIT_STATE
        assert state_trafficlight.transitions[3].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight.transitions[3].guard is None
        assert state_trafficlight.transitions[3].effects == []
        assert state_trafficlight.transitions[3].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[3].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[4].from_state == INIT_STATE
        assert state_trafficlight.transitions[4].to_state == "InService"
        assert state_trafficlight.transitions[4].event is None
        assert state_trafficlight.transitions[4].guard is None
        assert state_trafficlight.transitions[4].effects == []
        assert state_trafficlight.transitions[4].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[4].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[5].from_state == "InService"
        assert state_trafficlight.transitions[5].to_state == "Idle"
        assert state_trafficlight.transitions[5].event == Event(
            name="Maintain", state_path=("TrafficLight", "InService")
        )
        assert state_trafficlight.transitions[5].guard is None
        assert state_trafficlight.transitions[5].effects == []
        assert state_trafficlight.transitions[5].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[5].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[6].from_state == "Idle"
        assert state_trafficlight.transitions[6].to_state == "Idle"
        assert state_trafficlight.transitions[6].event == Event(
            name="E2", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight.transitions[6].guard is None
        assert state_trafficlight.transitions[6].effects == []
        assert state_trafficlight.transitions[6].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[6].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.transitions[7].from_state == "Idle"
        assert state_trafficlight.transitions[7].to_state == EXIT_STATE
        assert state_trafficlight.transitions[7].event is None
        assert state_trafficlight.transitions[7].guard is None
        assert state_trafficlight.transitions[7].effects == []
        assert state_trafficlight.transitions[7].parent_ref().name == "TrafficLight"
        assert state_trafficlight.transitions[7].parent_ref().path == ("TrafficLight",)
        assert state_trafficlight.on_enters == []
        assert state_trafficlight.on_durings == []
        assert state_trafficlight.on_exits == []
        assert state_trafficlight.on_during_aspects == []
        assert state_trafficlight.parent_ref is None
        assert state_trafficlight.substate_name_to_id == {"InService": 0, "Idle": 1}
        assert not state_trafficlight.is_pseudo
        assert state_trafficlight.abstract_on_during_aspects == []
        assert state_trafficlight.abstract_on_durings == []
        assert state_trafficlight.abstract_on_enters == []
        assert state_trafficlight.abstract_on_exits == []
        assert not state_trafficlight.is_leaf_state
        assert state_trafficlight.is_root_state
        assert state_trafficlight.non_abstract_on_during_aspects == []
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
            substates=[
                dsl_nodes.StateDefinition(
                    name="InService",
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Red",
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
                            name="Yellow",
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
                            from_state="Red",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["ServiceError"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Red",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["GodDamnFuckUp"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Yellow",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["ServiceError"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Yellow",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["GodDamnFuckUp"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Green",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["ServiceError"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Green",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["GodDamnFuckUp"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
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
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                ),
                dsl_nodes.StateDefinition(
                    name="Idle",
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="ToBe",
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
                            name="NotToBe",
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
                            from_state="ToBe",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["GiveUpThinking"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="ToBe",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["GodDamnFuckUp"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="NotToBe",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["GiveUpThinking"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="NotToBe",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["GodDamnFuckUp"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="ToBe",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="ToBe",
                            to_state="NotToBe",
                            event_id=dsl_nodes.ChainID(
                                path=["ToBe", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="NotToBe",
                            to_state="ToBe",
                            event_id=dsl_nodes.ChainID(
                                path=["NotToBe", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="NotToBe",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["NotToBe", "E2"], is_absolute=False
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
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="InService",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["InService", "ServiceError"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="InService",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["GodDamnFuckUp"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Idle",
                    to_state="InService",
                    event_id=dsl_nodes.ChainID(
                        path=["Idle", "GiveUpThinking"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Idle",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["GodDamnFuckUp"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
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
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_trafficlight_inservice(self, state_trafficlight_inservice):
        assert state_trafficlight_inservice.name == "InService"
        assert state_trafficlight_inservice.path == ("TrafficLight", "InService")
        assert sorted(state_trafficlight_inservice.substates.keys()) == [
            "Green",
            "Red",
            "Yellow",
        ]
        assert state_trafficlight_inservice.events == {
            "ServiceError": Event(
                name="ServiceError", state_path=("TrafficLight", "InService")
            ),
            "Start": Event(name="Start", state_path=("TrafficLight", "InService")),
            "Maintain": Event(
                name="Maintain", state_path=("TrafficLight", "InService")
            ),
        }
        assert len(state_trafficlight_inservice.transitions) == 12
        assert state_trafficlight_inservice.transitions[0].from_state == "Red"
        assert state_trafficlight_inservice.transitions[0].to_state == EXIT_STATE
        assert state_trafficlight_inservice.transitions[0].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert state_trafficlight_inservice.transitions[0].guard is None
        assert state_trafficlight_inservice.transitions[0].effects == []
        assert (
            state_trafficlight_inservice.transitions[0].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[0].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[1].from_state == "Red"
        assert state_trafficlight_inservice.transitions[1].to_state == EXIT_STATE
        assert state_trafficlight_inservice.transitions[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight_inservice.transitions[1].guard is None
        assert state_trafficlight_inservice.transitions[1].effects == []
        assert (
            state_trafficlight_inservice.transitions[1].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[1].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[2].from_state == "Yellow"
        assert state_trafficlight_inservice.transitions[2].to_state == EXIT_STATE
        assert state_trafficlight_inservice.transitions[2].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert state_trafficlight_inservice.transitions[2].guard is None
        assert state_trafficlight_inservice.transitions[2].effects == []
        assert (
            state_trafficlight_inservice.transitions[2].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[2].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[3].from_state == "Yellow"
        assert state_trafficlight_inservice.transitions[3].to_state == EXIT_STATE
        assert state_trafficlight_inservice.transitions[3].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight_inservice.transitions[3].guard is None
        assert state_trafficlight_inservice.transitions[3].effects == []
        assert (
            state_trafficlight_inservice.transitions[3].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[3].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[4].from_state == "Green"
        assert state_trafficlight_inservice.transitions[4].to_state == EXIT_STATE
        assert state_trafficlight_inservice.transitions[4].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
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
        assert state_trafficlight_inservice.transitions[5].from_state == "Green"
        assert state_trafficlight_inservice.transitions[5].to_state == EXIT_STATE
        assert state_trafficlight_inservice.transitions[5].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
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
        assert state_trafficlight_inservice.transitions[6].from_state == INIT_STATE
        assert state_trafficlight_inservice.transitions[6].to_state == "Red"
        assert state_trafficlight_inservice.transitions[6].event == Event(
            name="Start", state_path=("TrafficLight", "InService")
        )
        assert state_trafficlight_inservice.transitions[6].guard is None
        assert state_trafficlight_inservice.transitions[6].effects == [
            Operation(var_name="b", expr=Integer(value=1))
        ]
        assert (
            state_trafficlight_inservice.transitions[6].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[6].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[7].from_state == "Red"
        assert state_trafficlight_inservice.transitions[7].to_state == "Green"
        assert state_trafficlight_inservice.transitions[7].event is None
        assert state_trafficlight_inservice.transitions[7].guard is None
        assert state_trafficlight_inservice.transitions[7].effects == [
            Operation(var_name="b", expr=Integer(value=3))
        ]
        assert (
            state_trafficlight_inservice.transitions[7].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[7].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[8].from_state == "Green"
        assert state_trafficlight_inservice.transitions[8].to_state == "Yellow"
        assert state_trafficlight_inservice.transitions[8].event is None
        assert state_trafficlight_inservice.transitions[8].guard is None
        assert state_trafficlight_inservice.transitions[8].effects == [
            Operation(var_name="b", expr=Integer(value=2))
        ]
        assert (
            state_trafficlight_inservice.transitions[8].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[8].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[9].from_state == "Yellow"
        assert state_trafficlight_inservice.transitions[9].to_state == "Red"
        assert state_trafficlight_inservice.transitions[9].event is None
        assert state_trafficlight_inservice.transitions[9].guard == BinaryOp(
            x=Variable(name="a"), op=">=", y=Integer(value=10)
        )
        assert state_trafficlight_inservice.transitions[9].effects == [
            Operation(var_name="b", expr=Integer(value=1)),
            Operation(
                var_name="round_count",
                expr=BinaryOp(
                    x=Variable(name="round_count"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert (
            state_trafficlight_inservice.transitions[9].parent_ref().name == "InService"
        )
        assert state_trafficlight_inservice.transitions[9].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[10].from_state == "Green"
        assert state_trafficlight_inservice.transitions[10].to_state == "Yellow"
        assert state_trafficlight_inservice.transitions[10].event == Event(
            name="E2", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight_inservice.transitions[10].guard is None
        assert state_trafficlight_inservice.transitions[10].effects == []
        assert (
            state_trafficlight_inservice.transitions[10].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice.transitions[10].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.transitions[11].from_state == "Yellow"
        assert state_trafficlight_inservice.transitions[11].to_state == "Yellow"
        assert state_trafficlight_inservice.transitions[11].event == Event(
            name="E2", state_path=("TrafficLight",)
        )
        assert state_trafficlight_inservice.transitions[11].guard is None
        assert state_trafficlight_inservice.transitions[11].effects == []
        assert (
            state_trafficlight_inservice.transitions[11].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice.transitions[11].parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice.on_enters == []
        assert state_trafficlight_inservice.on_durings == []
        assert state_trafficlight_inservice.on_exits == []
        assert state_trafficlight_inservice.on_during_aspects == []
        assert state_trafficlight_inservice.parent_ref().name == "TrafficLight"
        assert state_trafficlight_inservice.parent_ref().path == ("TrafficLight",)
        assert state_trafficlight_inservice.substate_name_to_id == {
            "Red": 0,
            "Yellow": 1,
            "Green": 2,
        }
        assert not state_trafficlight_inservice.is_pseudo
        assert state_trafficlight_inservice.abstract_on_during_aspects == []
        assert state_trafficlight_inservice.abstract_on_durings == []
        assert state_trafficlight_inservice.abstract_on_enters == []
        assert state_trafficlight_inservice.abstract_on_exits == []
        assert not state_trafficlight_inservice.is_leaf_state
        assert not state_trafficlight_inservice.is_root_state
        assert state_trafficlight_inservice.non_abstract_on_during_aspects == []
        assert state_trafficlight_inservice.non_abstract_on_durings == []
        assert state_trafficlight_inservice.non_abstract_on_enters == []
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
        ].event == Event(name="Start", state_path=("TrafficLight", "InService"))
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
        ].event == Event(name="Start", state_path=("TrafficLight", "InService"))
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
        assert len(state_trafficlight_inservice.transitions_from) == 3
        assert (
            state_trafficlight_inservice.transitions_from[0].from_state == "InService"
        )
        assert state_trafficlight_inservice.transitions_from[0].to_state == EXIT_STATE
        assert state_trafficlight_inservice.transitions_from[0].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
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
        assert (
            state_trafficlight_inservice.transitions_from[1].from_state == "InService"
        )
        assert state_trafficlight_inservice.transitions_from[1].to_state == EXIT_STATE
        assert state_trafficlight_inservice.transitions_from[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight_inservice.transitions_from[1].guard is None
        assert state_trafficlight_inservice.transitions_from[1].effects == []
        assert (
            state_trafficlight_inservice.transitions_from[1].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_inservice.transitions_from[1].parent_ref().path == (
            "TrafficLight",
        )
        assert (
            state_trafficlight_inservice.transitions_from[2].from_state == "InService"
        )
        assert state_trafficlight_inservice.transitions_from[2].to_state == "Idle"
        assert state_trafficlight_inservice.transitions_from[2].event == Event(
            name="Maintain", state_path=("TrafficLight", "InService")
        )
        assert state_trafficlight_inservice.transitions_from[2].guard is None
        assert state_trafficlight_inservice.transitions_from[2].effects == []
        assert (
            state_trafficlight_inservice.transitions_from[2].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_inservice.transitions_from[2].parent_ref().path == (
            "TrafficLight",
        )
        assert len(state_trafficlight_inservice.transitions_to) == 2
        assert state_trafficlight_inservice.transitions_to[0].from_state == "Idle"
        assert state_trafficlight_inservice.transitions_to[0].to_state == "InService"
        assert state_trafficlight_inservice.transitions_to[0].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight_inservice.transitions_to[0].guard is None
        assert state_trafficlight_inservice.transitions_to[0].effects == []
        assert (
            state_trafficlight_inservice.transitions_to[0].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_inservice.transitions_to[0].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight_inservice.transitions_to[1].from_state == INIT_STATE
        assert state_trafficlight_inservice.transitions_to[1].to_state == "InService"
        assert state_trafficlight_inservice.transitions_to[1].event is None
        assert state_trafficlight_inservice.transitions_to[1].guard is None
        assert state_trafficlight_inservice.transitions_to[1].effects == []
        assert (
            state_trafficlight_inservice.transitions_to[1].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_inservice.transitions_to[1].parent_ref().path == (
            "TrafficLight",
        )

    def test_state_trafficlight_inservice_to_ast_node(
        self, state_trafficlight_inservice
    ):
        ast_node = state_trafficlight_inservice.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="InService",
            substates=[
                dsl_nodes.StateDefinition(
                    name="Red",
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
                    name="Yellow",
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
                    from_state="Red",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["ServiceError"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Red",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["GodDamnFuckUp"], is_absolute=True
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Yellow",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["ServiceError"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Yellow",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["GodDamnFuckUp"], is_absolute=True
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Green",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["ServiceError"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="Green",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["GodDamnFuckUp"], is_absolute=True
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
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
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

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
        assert state_trafficlight_inservice_red.on_enters == []
        assert state_trafficlight_inservice_red.on_durings == []
        assert state_trafficlight_inservice_red.on_exits == []
        assert state_trafficlight_inservice_red.on_during_aspects == []
        assert state_trafficlight_inservice_red.parent_ref().name == "InService"
        assert state_trafficlight_inservice_red.parent_ref().path == (
            "TrafficLight",
            "InService",
        )
        assert state_trafficlight_inservice_red.substate_name_to_id == {}
        assert not state_trafficlight_inservice_red.is_pseudo
        assert state_trafficlight_inservice_red.abstract_on_during_aspects == []
        assert state_trafficlight_inservice_red.abstract_on_durings == []
        assert state_trafficlight_inservice_red.abstract_on_enters == []
        assert state_trafficlight_inservice_red.abstract_on_exits == []
        assert state_trafficlight_inservice_red.is_leaf_state
        assert not state_trafficlight_inservice_red.is_root_state
        assert state_trafficlight_inservice_red.non_abstract_on_during_aspects == []
        assert state_trafficlight_inservice_red.non_abstract_on_durings == []
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
        assert len(state_trafficlight_inservice_red.transitions_from) == 3
        assert state_trafficlight_inservice_red.transitions_from[0].from_state == "Red"
        assert (
            state_trafficlight_inservice_red.transitions_from[0].to_state == EXIT_STATE
        )
        assert state_trafficlight_inservice_red.transitions_from[0].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert state_trafficlight_inservice_red.transitions_from[0].guard is None
        assert state_trafficlight_inservice_red.transitions_from[0].effects == []
        assert (
            state_trafficlight_inservice_red.transitions_from[0].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_red.transitions_from[
            0
        ].parent_ref().path == ("TrafficLight", "InService")
        assert state_trafficlight_inservice_red.transitions_from[1].from_state == "Red"
        assert (
            state_trafficlight_inservice_red.transitions_from[1].to_state == EXIT_STATE
        )
        assert state_trafficlight_inservice_red.transitions_from[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight_inservice_red.transitions_from[1].guard is None
        assert state_trafficlight_inservice_red.transitions_from[1].effects == []
        assert (
            state_trafficlight_inservice_red.transitions_from[1].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_red.transitions_from[
            1
        ].parent_ref().path == ("TrafficLight", "InService")
        assert state_trafficlight_inservice_red.transitions_from[2].from_state == "Red"
        assert state_trafficlight_inservice_red.transitions_from[2].to_state == "Green"
        assert state_trafficlight_inservice_red.transitions_from[2].event is None
        assert state_trafficlight_inservice_red.transitions_from[2].guard is None
        assert state_trafficlight_inservice_red.transitions_from[2].effects == [
            Operation(var_name="b", expr=Integer(value=3))
        ]
        assert (
            state_trafficlight_inservice_red.transitions_from[2].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_red.transitions_from[
            2
        ].parent_ref().path == ("TrafficLight", "InService")
        assert len(state_trafficlight_inservice_red.transitions_to) == 2
        assert (
            state_trafficlight_inservice_red.transitions_to[0].from_state == INIT_STATE
        )
        assert state_trafficlight_inservice_red.transitions_to[0].to_state == "Red"
        assert state_trafficlight_inservice_red.transitions_to[0].event == Event(
            name="Start", state_path=("TrafficLight", "InService")
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
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_trafficlight_inservice_red_during_aspect(
        self, state_trafficlight_inservice_red
    ):
        lst = state_trafficlight_inservice_red.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_trafficlight_inservice_red.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

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
        assert not state_trafficlight_inservice_yellow.is_pseudo
        assert state_trafficlight_inservice_yellow.abstract_on_during_aspects == []
        assert state_trafficlight_inservice_yellow.abstract_on_durings == []
        assert state_trafficlight_inservice_yellow.abstract_on_enters == []
        assert state_trafficlight_inservice_yellow.abstract_on_exits == []
        assert state_trafficlight_inservice_yellow.is_leaf_state
        assert not state_trafficlight_inservice_yellow.is_root_state
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
        assert len(state_trafficlight_inservice_yellow.transitions_from) == 4
        assert (
            state_trafficlight_inservice_yellow.transitions_from[0].from_state
            == "Yellow"
        )
        assert (
            state_trafficlight_inservice_yellow.transitions_from[0].to_state
            == EXIT_STATE
        )
        assert state_trafficlight_inservice_yellow.transitions_from[0].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert state_trafficlight_inservice_yellow.transitions_from[0].guard is None
        assert state_trafficlight_inservice_yellow.transitions_from[0].effects == []
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
            state_trafficlight_inservice_yellow.transitions_from[1].to_state
            == EXIT_STATE
        )
        assert state_trafficlight_inservice_yellow.transitions_from[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
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
        assert (
            state_trafficlight_inservice_yellow.transitions_from[2].from_state
            == "Yellow"
        )
        assert state_trafficlight_inservice_yellow.transitions_from[2].to_state == "Red"
        assert state_trafficlight_inservice_yellow.transitions_from[2].event is None
        assert state_trafficlight_inservice_yellow.transitions_from[
            2
        ].guard == BinaryOp(x=Variable(name="a"), op=">=", y=Integer(value=10))
        assert state_trafficlight_inservice_yellow.transitions_from[2].effects == [
            Operation(var_name="b", expr=Integer(value=1)),
            Operation(
                var_name="round_count",
                expr=BinaryOp(
                    x=Variable(name="round_count"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert (
            state_trafficlight_inservice_yellow.transitions_from[2].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_yellow.transitions_from[
            2
        ].parent_ref().path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice_yellow.transitions_from[3].from_state
            == "Yellow"
        )
        assert (
            state_trafficlight_inservice_yellow.transitions_from[3].to_state == "Yellow"
        )
        assert state_trafficlight_inservice_yellow.transitions_from[3].event == Event(
            name="E2", state_path=("TrafficLight",)
        )
        assert state_trafficlight_inservice_yellow.transitions_from[3].guard is None
        assert state_trafficlight_inservice_yellow.transitions_from[3].effects == []
        assert (
            state_trafficlight_inservice_yellow.transitions_from[3].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_yellow.transitions_from[
            3
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
            name="E2", state_path=("TrafficLight", "Idle")
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
            name="E2", state_path=("TrafficLight",)
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
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_trafficlight_inservice_yellow_during_aspect(
        self, state_trafficlight_inservice_yellow
    ):
        lst = state_trafficlight_inservice_yellow.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_trafficlight_inservice_yellow.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

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
        assert not state_trafficlight_inservice_green.is_pseudo
        assert state_trafficlight_inservice_green.abstract_on_during_aspects == []
        assert state_trafficlight_inservice_green.abstract_on_durings == []
        assert state_trafficlight_inservice_green.abstract_on_enters == []
        assert state_trafficlight_inservice_green.abstract_on_exits == []
        assert state_trafficlight_inservice_green.is_leaf_state
        assert not state_trafficlight_inservice_green.is_root_state
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
        assert len(state_trafficlight_inservice_green.transitions_from) == 4
        assert (
            state_trafficlight_inservice_green.transitions_from[0].from_state == "Green"
        )
        assert (
            state_trafficlight_inservice_green.transitions_from[0].to_state
            == EXIT_STATE
        )
        assert state_trafficlight_inservice_green.transitions_from[0].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert state_trafficlight_inservice_green.transitions_from[0].guard is None
        assert state_trafficlight_inservice_green.transitions_from[0].effects == []
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
            state_trafficlight_inservice_green.transitions_from[1].to_state
            == EXIT_STATE
        )
        assert state_trafficlight_inservice_green.transitions_from[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
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
        assert (
            state_trafficlight_inservice_green.transitions_from[2].from_state == "Green"
        )
        assert (
            state_trafficlight_inservice_green.transitions_from[2].to_state == "Yellow"
        )
        assert state_trafficlight_inservice_green.transitions_from[2].event is None
        assert state_trafficlight_inservice_green.transitions_from[2].guard is None
        assert state_trafficlight_inservice_green.transitions_from[2].effects == [
            Operation(var_name="b", expr=Integer(value=2))
        ]
        assert (
            state_trafficlight_inservice_green.transitions_from[2].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_green.transitions_from[
            2
        ].parent_ref().path == ("TrafficLight", "InService")
        assert (
            state_trafficlight_inservice_green.transitions_from[3].from_state == "Green"
        )
        assert (
            state_trafficlight_inservice_green.transitions_from[3].to_state == "Yellow"
        )
        assert state_trafficlight_inservice_green.transitions_from[3].event == Event(
            name="E2", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight_inservice_green.transitions_from[3].guard is None
        assert state_trafficlight_inservice_green.transitions_from[3].effects == []
        assert (
            state_trafficlight_inservice_green.transitions_from[3].parent_ref().name
            == "InService"
        )
        assert state_trafficlight_inservice_green.transitions_from[
            3
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
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_trafficlight_inservice_green_during_aspect(
        self, state_trafficlight_inservice_green
    ):
        lst = state_trafficlight_inservice_green.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_trafficlight_inservice_green.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_trafficlight_idle(self, state_trafficlight_idle):
        assert state_trafficlight_idle.name == "Idle"
        assert state_trafficlight_idle.path == ("TrafficLight", "Idle")
        assert sorted(state_trafficlight_idle.substates.keys()) == ["NotToBe", "ToBe"]
        assert state_trafficlight_idle.events == {
            "GiveUpThinking": Event(
                name="GiveUpThinking", state_path=("TrafficLight", "Idle")
            ),
            "E2": Event(name="E2", state_path=("TrafficLight", "Idle")),
        }
        assert len(state_trafficlight_idle.transitions) == 8
        assert state_trafficlight_idle.transitions[0].from_state == "ToBe"
        assert state_trafficlight_idle.transitions[0].to_state == EXIT_STATE
        assert state_trafficlight_idle.transitions[0].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight_idle.transitions[0].guard is None
        assert state_trafficlight_idle.transitions[0].effects == []
        assert state_trafficlight_idle.transitions[0].parent_ref().name == "Idle"
        assert state_trafficlight_idle.transitions[0].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle.transitions[1].from_state == "ToBe"
        assert state_trafficlight_idle.transitions[1].to_state == EXIT_STATE
        assert state_trafficlight_idle.transitions[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight_idle.transitions[1].guard is None
        assert state_trafficlight_idle.transitions[1].effects == []
        assert state_trafficlight_idle.transitions[1].parent_ref().name == "Idle"
        assert state_trafficlight_idle.transitions[1].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle.transitions[2].from_state == "NotToBe"
        assert state_trafficlight_idle.transitions[2].to_state == EXIT_STATE
        assert state_trafficlight_idle.transitions[2].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight_idle.transitions[2].guard is None
        assert state_trafficlight_idle.transitions[2].effects == []
        assert state_trafficlight_idle.transitions[2].parent_ref().name == "Idle"
        assert state_trafficlight_idle.transitions[2].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle.transitions[3].from_state == "NotToBe"
        assert state_trafficlight_idle.transitions[3].to_state == EXIT_STATE
        assert state_trafficlight_idle.transitions[3].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight_idle.transitions[3].guard is None
        assert state_trafficlight_idle.transitions[3].effects == []
        assert state_trafficlight_idle.transitions[3].parent_ref().name == "Idle"
        assert state_trafficlight_idle.transitions[3].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle.transitions[4].from_state == INIT_STATE
        assert state_trafficlight_idle.transitions[4].to_state == "ToBe"
        assert state_trafficlight_idle.transitions[4].event is None
        assert state_trafficlight_idle.transitions[4].guard is None
        assert state_trafficlight_idle.transitions[4].effects == []
        assert state_trafficlight_idle.transitions[4].parent_ref().name == "Idle"
        assert state_trafficlight_idle.transitions[4].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle.transitions[5].from_state == "ToBe"
        assert state_trafficlight_idle.transitions[5].to_state == "NotToBe"
        assert state_trafficlight_idle.transitions[5].event == Event(
            name="E1", state_path=("TrafficLight", "Idle", "ToBe")
        )
        assert state_trafficlight_idle.transitions[5].guard is None
        assert state_trafficlight_idle.transitions[5].effects == []
        assert state_trafficlight_idle.transitions[5].parent_ref().name == "Idle"
        assert state_trafficlight_idle.transitions[5].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle.transitions[6].from_state == "NotToBe"
        assert state_trafficlight_idle.transitions[6].to_state == "ToBe"
        assert state_trafficlight_idle.transitions[6].event == Event(
            name="E1", state_path=("TrafficLight", "Idle", "NotToBe")
        )
        assert state_trafficlight_idle.transitions[6].guard is None
        assert state_trafficlight_idle.transitions[6].effects == []
        assert state_trafficlight_idle.transitions[6].parent_ref().name == "Idle"
        assert state_trafficlight_idle.transitions[6].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle.transitions[7].from_state == "NotToBe"
        assert state_trafficlight_idle.transitions[7].to_state == EXIT_STATE
        assert state_trafficlight_idle.transitions[7].event == Event(
            name="E2", state_path=("TrafficLight", "Idle", "NotToBe")
        )
        assert state_trafficlight_idle.transitions[7].guard is None
        assert state_trafficlight_idle.transitions[7].effects == []
        assert state_trafficlight_idle.transitions[7].parent_ref().name == "Idle"
        assert state_trafficlight_idle.transitions[7].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle.on_enters == []
        assert state_trafficlight_idle.on_durings == []
        assert state_trafficlight_idle.on_exits == []
        assert state_trafficlight_idle.on_during_aspects == []
        assert state_trafficlight_idle.parent_ref().name == "TrafficLight"
        assert state_trafficlight_idle.parent_ref().path == ("TrafficLight",)
        assert state_trafficlight_idle.substate_name_to_id == {"ToBe": 0, "NotToBe": 1}
        assert not state_trafficlight_idle.is_pseudo
        assert state_trafficlight_idle.abstract_on_during_aspects == []
        assert state_trafficlight_idle.abstract_on_durings == []
        assert state_trafficlight_idle.abstract_on_enters == []
        assert state_trafficlight_idle.abstract_on_exits == []
        assert not state_trafficlight_idle.is_leaf_state
        assert not state_trafficlight_idle.is_root_state
        assert state_trafficlight_idle.non_abstract_on_during_aspects == []
        assert state_trafficlight_idle.non_abstract_on_durings == []
        assert state_trafficlight_idle.non_abstract_on_enters == []
        assert state_trafficlight_idle.non_abstract_on_exits == []
        assert state_trafficlight_idle.parent.name == "TrafficLight"
        assert state_trafficlight_idle.parent.path == ("TrafficLight",)
        assert len(state_trafficlight_idle.transitions_entering_children) == 1
        assert (
            state_trafficlight_idle.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert (
            state_trafficlight_idle.transitions_entering_children[0].to_state == "ToBe"
        )
        assert state_trafficlight_idle.transitions_entering_children[0].event is None
        assert state_trafficlight_idle.transitions_entering_children[0].guard is None
        assert state_trafficlight_idle.transitions_entering_children[0].effects == []
        assert (
            state_trafficlight_idle.transitions_entering_children[0].parent_ref().name
            == "Idle"
        )
        assert state_trafficlight_idle.transitions_entering_children[
            0
        ].parent_ref().path == ("TrafficLight", "Idle")
        assert (
            len(state_trafficlight_idle.transitions_entering_children_simplified) == 1
        )
        assert (
            state_trafficlight_idle.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_trafficlight_idle.transitions_entering_children_simplified[0].to_state
            == "ToBe"
        )
        assert (
            state_trafficlight_idle.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_trafficlight_idle.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_trafficlight_idle.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_trafficlight_idle.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "Idle"
        )
        assert state_trafficlight_idle.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("TrafficLight", "Idle")
        assert len(state_trafficlight_idle.transitions_from) == 4
        assert state_trafficlight_idle.transitions_from[0].from_state == "Idle"
        assert state_trafficlight_idle.transitions_from[0].to_state == "InService"
        assert state_trafficlight_idle.transitions_from[0].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
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
        assert state_trafficlight_idle.transitions_from[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight_idle.transitions_from[1].guard is None
        assert state_trafficlight_idle.transitions_from[1].effects == []
        assert (
            state_trafficlight_idle.transitions_from[1].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_idle.transitions_from[1].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight_idle.transitions_from[2].from_state == "Idle"
        assert state_trafficlight_idle.transitions_from[2].to_state == "Idle"
        assert state_trafficlight_idle.transitions_from[2].event == Event(
            name="E2", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight_idle.transitions_from[2].guard is None
        assert state_trafficlight_idle.transitions_from[2].effects == []
        assert (
            state_trafficlight_idle.transitions_from[2].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_idle.transitions_from[2].parent_ref().path == (
            "TrafficLight",
        )
        assert state_trafficlight_idle.transitions_from[3].from_state == "Idle"
        assert state_trafficlight_idle.transitions_from[3].to_state == EXIT_STATE
        assert state_trafficlight_idle.transitions_from[3].event is None
        assert state_trafficlight_idle.transitions_from[3].guard is None
        assert state_trafficlight_idle.transitions_from[3].effects == []
        assert (
            state_trafficlight_idle.transitions_from[3].parent_ref().name
            == "TrafficLight"
        )
        assert state_trafficlight_idle.transitions_from[3].parent_ref().path == (
            "TrafficLight",
        )
        assert len(state_trafficlight_idle.transitions_to) == 2
        assert state_trafficlight_idle.transitions_to[0].from_state == "InService"
        assert state_trafficlight_idle.transitions_to[0].to_state == "Idle"
        assert state_trafficlight_idle.transitions_to[0].event == Event(
            name="Maintain", state_path=("TrafficLight", "InService")
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
            name="E2", state_path=("TrafficLight", "Idle")
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
            substates=[
                dsl_nodes.StateDefinition(
                    name="ToBe",
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
                    name="NotToBe",
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
                    from_state="ToBe",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["GiveUpThinking"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="ToBe",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["GodDamnFuckUp"], is_absolute=True
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="NotToBe",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["GiveUpThinking"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="NotToBe",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["GodDamnFuckUp"], is_absolute=True
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="ToBe",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="ToBe",
                    to_state="NotToBe",
                    event_id=dsl_nodes.ChainID(path=["ToBe", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="NotToBe",
                    to_state="ToBe",
                    event_id=dsl_nodes.ChainID(
                        path=["NotToBe", "E1"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="NotToBe",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["NotToBe", "E2"], is_absolute=False
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

    def test_state_trafficlight_idle_tobe(self, state_trafficlight_idle_tobe):
        assert state_trafficlight_idle_tobe.name == "ToBe"
        assert state_trafficlight_idle_tobe.path == ("TrafficLight", "Idle", "ToBe")
        assert sorted(state_trafficlight_idle_tobe.substates.keys()) == []
        assert state_trafficlight_idle_tobe.events == {
            "E1": Event(name="E1", state_path=("TrafficLight", "Idle", "ToBe"))
        }
        assert state_trafficlight_idle_tobe.transitions == []
        assert state_trafficlight_idle_tobe.on_enters == []
        assert state_trafficlight_idle_tobe.on_durings == []
        assert state_trafficlight_idle_tobe.on_exits == []
        assert state_trafficlight_idle_tobe.on_during_aspects == []
        assert state_trafficlight_idle_tobe.parent_ref().name == "Idle"
        assert state_trafficlight_idle_tobe.parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle_tobe.substate_name_to_id == {}
        assert not state_trafficlight_idle_tobe.is_pseudo
        assert state_trafficlight_idle_tobe.abstract_on_during_aspects == []
        assert state_trafficlight_idle_tobe.abstract_on_durings == []
        assert state_trafficlight_idle_tobe.abstract_on_enters == []
        assert state_trafficlight_idle_tobe.abstract_on_exits == []
        assert state_trafficlight_idle_tobe.is_leaf_state
        assert not state_trafficlight_idle_tobe.is_root_state
        assert state_trafficlight_idle_tobe.non_abstract_on_during_aspects == []
        assert state_trafficlight_idle_tobe.non_abstract_on_durings == []
        assert state_trafficlight_idle_tobe.non_abstract_on_enters == []
        assert state_trafficlight_idle_tobe.non_abstract_on_exits == []
        assert state_trafficlight_idle_tobe.parent.name == "Idle"
        assert state_trafficlight_idle_tobe.parent.path == ("TrafficLight", "Idle")
        assert state_trafficlight_idle_tobe.transitions_entering_children == []
        assert (
            len(state_trafficlight_idle_tobe.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_trafficlight_idle_tobe.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_trafficlight_idle_tobe.transitions_from) == 3
        assert state_trafficlight_idle_tobe.transitions_from[0].from_state == "ToBe"
        assert state_trafficlight_idle_tobe.transitions_from[0].to_state == EXIT_STATE
        assert state_trafficlight_idle_tobe.transitions_from[0].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight_idle_tobe.transitions_from[0].guard is None
        assert state_trafficlight_idle_tobe.transitions_from[0].effects == []
        assert (
            state_trafficlight_idle_tobe.transitions_from[0].parent_ref().name == "Idle"
        )
        assert state_trafficlight_idle_tobe.transitions_from[0].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle_tobe.transitions_from[1].from_state == "ToBe"
        assert state_trafficlight_idle_tobe.transitions_from[1].to_state == EXIT_STATE
        assert state_trafficlight_idle_tobe.transitions_from[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight_idle_tobe.transitions_from[1].guard is None
        assert state_trafficlight_idle_tobe.transitions_from[1].effects == []
        assert (
            state_trafficlight_idle_tobe.transitions_from[1].parent_ref().name == "Idle"
        )
        assert state_trafficlight_idle_tobe.transitions_from[1].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle_tobe.transitions_from[2].from_state == "ToBe"
        assert state_trafficlight_idle_tobe.transitions_from[2].to_state == "NotToBe"
        assert state_trafficlight_idle_tobe.transitions_from[2].event == Event(
            name="E1", state_path=("TrafficLight", "Idle", "ToBe")
        )
        assert state_trafficlight_idle_tobe.transitions_from[2].guard is None
        assert state_trafficlight_idle_tobe.transitions_from[2].effects == []
        assert (
            state_trafficlight_idle_tobe.transitions_from[2].parent_ref().name == "Idle"
        )
        assert state_trafficlight_idle_tobe.transitions_from[2].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert len(state_trafficlight_idle_tobe.transitions_to) == 2
        assert state_trafficlight_idle_tobe.transitions_to[0].from_state == INIT_STATE
        assert state_trafficlight_idle_tobe.transitions_to[0].to_state == "ToBe"
        assert state_trafficlight_idle_tobe.transitions_to[0].event is None
        assert state_trafficlight_idle_tobe.transitions_to[0].guard is None
        assert state_trafficlight_idle_tobe.transitions_to[0].effects == []
        assert (
            state_trafficlight_idle_tobe.transitions_to[0].parent_ref().name == "Idle"
        )
        assert state_trafficlight_idle_tobe.transitions_to[0].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle_tobe.transitions_to[1].from_state == "NotToBe"
        assert state_trafficlight_idle_tobe.transitions_to[1].to_state == "ToBe"
        assert state_trafficlight_idle_tobe.transitions_to[1].event == Event(
            name="E1", state_path=("TrafficLight", "Idle", "NotToBe")
        )
        assert state_trafficlight_idle_tobe.transitions_to[1].guard is None
        assert state_trafficlight_idle_tobe.transitions_to[1].effects == []
        assert (
            state_trafficlight_idle_tobe.transitions_to[1].parent_ref().name == "Idle"
        )
        assert state_trafficlight_idle_tobe.transitions_to[1].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )

    def test_state_trafficlight_idle_tobe_to_ast_node(
        self, state_trafficlight_idle_tobe
    ):
        ast_node = state_trafficlight_idle_tobe.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="ToBe",
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_trafficlight_idle_tobe_during_aspect(
        self, state_trafficlight_idle_tobe
    ):
        lst = state_trafficlight_idle_tobe.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_trafficlight_idle_tobe.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_trafficlight_idle_nottobe(self, state_trafficlight_idle_nottobe):
        assert state_trafficlight_idle_nottobe.name == "NotToBe"
        assert state_trafficlight_idle_nottobe.path == (
            "TrafficLight",
            "Idle",
            "NotToBe",
        )
        assert sorted(state_trafficlight_idle_nottobe.substates.keys()) == []
        assert state_trafficlight_idle_nottobe.events == {
            "E1": Event(name="E1", state_path=("TrafficLight", "Idle", "NotToBe")),
            "E2": Event(name="E2", state_path=("TrafficLight", "Idle", "NotToBe")),
        }
        assert state_trafficlight_idle_nottobe.transitions == []
        assert state_trafficlight_idle_nottobe.on_enters == []
        assert state_trafficlight_idle_nottobe.on_durings == []
        assert state_trafficlight_idle_nottobe.on_exits == []
        assert state_trafficlight_idle_nottobe.on_during_aspects == []
        assert state_trafficlight_idle_nottobe.parent_ref().name == "Idle"
        assert state_trafficlight_idle_nottobe.parent_ref().path == (
            "TrafficLight",
            "Idle",
        )
        assert state_trafficlight_idle_nottobe.substate_name_to_id == {}
        assert not state_trafficlight_idle_nottobe.is_pseudo
        assert state_trafficlight_idle_nottobe.abstract_on_during_aspects == []
        assert state_trafficlight_idle_nottobe.abstract_on_durings == []
        assert state_trafficlight_idle_nottobe.abstract_on_enters == []
        assert state_trafficlight_idle_nottobe.abstract_on_exits == []
        assert state_trafficlight_idle_nottobe.is_leaf_state
        assert not state_trafficlight_idle_nottobe.is_root_state
        assert state_trafficlight_idle_nottobe.non_abstract_on_during_aspects == []
        assert state_trafficlight_idle_nottobe.non_abstract_on_durings == []
        assert state_trafficlight_idle_nottobe.non_abstract_on_enters == []
        assert state_trafficlight_idle_nottobe.non_abstract_on_exits == []
        assert state_trafficlight_idle_nottobe.parent.name == "Idle"
        assert state_trafficlight_idle_nottobe.parent.path == ("TrafficLight", "Idle")
        assert state_trafficlight_idle_nottobe.transitions_entering_children == []
        assert (
            len(
                state_trafficlight_idle_nottobe.transitions_entering_children_simplified
            )
            == 1
        )
        assert (
            state_trafficlight_idle_nottobe.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_trafficlight_idle_nottobe.transitions_from) == 4
        assert (
            state_trafficlight_idle_nottobe.transitions_from[0].from_state == "NotToBe"
        )
        assert (
            state_trafficlight_idle_nottobe.transitions_from[0].to_state == EXIT_STATE
        )
        assert state_trafficlight_idle_nottobe.transitions_from[0].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
        )
        assert state_trafficlight_idle_nottobe.transitions_from[0].guard is None
        assert state_trafficlight_idle_nottobe.transitions_from[0].effects == []
        assert (
            state_trafficlight_idle_nottobe.transitions_from[0].parent_ref().name
            == "Idle"
        )
        assert state_trafficlight_idle_nottobe.transitions_from[
            0
        ].parent_ref().path == ("TrafficLight", "Idle")
        assert (
            state_trafficlight_idle_nottobe.transitions_from[1].from_state == "NotToBe"
        )
        assert (
            state_trafficlight_idle_nottobe.transitions_from[1].to_state == EXIT_STATE
        )
        assert state_trafficlight_idle_nottobe.transitions_from[1].event == Event(
            name="GodDamnFuckUp", state_path=("TrafficLight",)
        )
        assert state_trafficlight_idle_nottobe.transitions_from[1].guard is None
        assert state_trafficlight_idle_nottobe.transitions_from[1].effects == []
        assert (
            state_trafficlight_idle_nottobe.transitions_from[1].parent_ref().name
            == "Idle"
        )
        assert state_trafficlight_idle_nottobe.transitions_from[
            1
        ].parent_ref().path == ("TrafficLight", "Idle")
        assert (
            state_trafficlight_idle_nottobe.transitions_from[2].from_state == "NotToBe"
        )
        assert state_trafficlight_idle_nottobe.transitions_from[2].to_state == "ToBe"
        assert state_trafficlight_idle_nottobe.transitions_from[2].event == Event(
            name="E1", state_path=("TrafficLight", "Idle", "NotToBe")
        )
        assert state_trafficlight_idle_nottobe.transitions_from[2].guard is None
        assert state_trafficlight_idle_nottobe.transitions_from[2].effects == []
        assert (
            state_trafficlight_idle_nottobe.transitions_from[2].parent_ref().name
            == "Idle"
        )
        assert state_trafficlight_idle_nottobe.transitions_from[
            2
        ].parent_ref().path == ("TrafficLight", "Idle")
        assert (
            state_trafficlight_idle_nottobe.transitions_from[3].from_state == "NotToBe"
        )
        assert (
            state_trafficlight_idle_nottobe.transitions_from[3].to_state == EXIT_STATE
        )
        assert state_trafficlight_idle_nottobe.transitions_from[3].event == Event(
            name="E2", state_path=("TrafficLight", "Idle", "NotToBe")
        )
        assert state_trafficlight_idle_nottobe.transitions_from[3].guard is None
        assert state_trafficlight_idle_nottobe.transitions_from[3].effects == []
        assert (
            state_trafficlight_idle_nottobe.transitions_from[3].parent_ref().name
            == "Idle"
        )
        assert state_trafficlight_idle_nottobe.transitions_from[
            3
        ].parent_ref().path == ("TrafficLight", "Idle")
        assert len(state_trafficlight_idle_nottobe.transitions_to) == 1
        assert state_trafficlight_idle_nottobe.transitions_to[0].from_state == "ToBe"
        assert state_trafficlight_idle_nottobe.transitions_to[0].to_state == "NotToBe"
        assert state_trafficlight_idle_nottobe.transitions_to[0].event == Event(
            name="E1", state_path=("TrafficLight", "Idle", "ToBe")
        )
        assert state_trafficlight_idle_nottobe.transitions_to[0].guard is None
        assert state_trafficlight_idle_nottobe.transitions_to[0].effects == []
        assert (
            state_trafficlight_idle_nottobe.transitions_to[0].parent_ref().name
            == "Idle"
        )
        assert state_trafficlight_idle_nottobe.transitions_to[0].parent_ref().path == (
            "TrafficLight",
            "Idle",
        )

    def test_state_trafficlight_idle_nottobe_to_ast_node(
        self, state_trafficlight_idle_nottobe
    ):
        ast_node = state_trafficlight_idle_nottobe.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="NotToBe",
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_trafficlight_idle_nottobe_during_aspect(
        self, state_trafficlight_idle_nottobe
    ):
        lst = state_trafficlight_idle_nottobe.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_trafficlight_idle_nottobe.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int a = 0;
def int b = 0;
def int round_count = 0;
state TrafficLight {
    state InService {
        state Red;
        state Yellow;
        state Green;
        Red -> [*] : ServiceError;
        Red -> [*] : /GodDamnFuckUp;
        Yellow -> [*] : ServiceError;
        Yellow -> [*] : /GodDamnFuckUp;
        Green -> [*] : ServiceError;
        Green -> [*] : /GodDamnFuckUp;
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
        state ToBe;
        state NotToBe;
        ToBe -> [*] : GiveUpThinking;
        ToBe -> [*] : /GodDamnFuckUp;
        NotToBe -> [*] : GiveUpThinking;
        NotToBe -> [*] : /GodDamnFuckUp;
        [*] -> ToBe;
        ToBe -> NotToBe :: E1;
        NotToBe -> ToBe :: E1;
        NotToBe -> [*] :: E2;
    }
    InService -> [*] :: ServiceError;
    InService -> [*] : GodDamnFuckUp;
    Idle -> InService :: GiveUpThinking;
    Idle -> [*] : GodDamnFuckUp;
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
    def int b = 0;
    def int round_count = 0;
}
end note

state "TrafficLight" as traffic_light {
    state "InService" as traffic_light__in_service {
        state "Red" as traffic_light__in_service__red
        state "Yellow" as traffic_light__in_service__yellow
        state "Green" as traffic_light__in_service__green
        traffic_light__in_service__red --> [*] : ServiceError
        traffic_light__in_service__red --> [*] : /GodDamnFuckUp
        traffic_light__in_service__yellow --> [*] : ServiceError
        traffic_light__in_service__yellow --> [*] : /GodDamnFuckUp
        traffic_light__in_service__green --> [*] : ServiceError
        traffic_light__in_service__green --> [*] : /GodDamnFuckUp
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
    state "Idle" as traffic_light__idle {
        state "ToBe" as traffic_light__idle__to_be
        state "NotToBe" as traffic_light__idle__not_to_be
        traffic_light__idle__to_be --> [*] : GiveUpThinking
        traffic_light__idle__to_be --> [*] : /GodDamnFuckUp
        traffic_light__idle__not_to_be --> [*] : GiveUpThinking
        traffic_light__idle__not_to_be --> [*] : /GodDamnFuckUp
        [*] --> traffic_light__idle__to_be
        traffic_light__idle__to_be --> traffic_light__idle__not_to_be : ToBe.E1
        traffic_light__idle__not_to_be --> traffic_light__idle__to_be : NotToBe.E1
        traffic_light__idle__not_to_be --> [*] : NotToBe.E2
    }
    traffic_light__in_service --> [*] : InService.ServiceError
    traffic_light__in_service --> [*] : GodDamnFuckUp
    traffic_light__idle --> traffic_light__in_service : Idle.GiveUpThinking
    traffic_light__idle --> [*] : GodDamnFuckUp
    [*] --> traffic_light__in_service
    traffic_light__in_service --> traffic_light__idle : InService.Maintain
    traffic_light__idle --> traffic_light__idle : Idle.E2
    traffic_light__idle --> [*]
}
[*] --> traffic_light
traffic_light --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml()),
        )
