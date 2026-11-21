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
state L1
{
    [*] -> L11;
    !L11 -> [*] :: E1;
    L12 -> [*];

    state L11
    {
        [*] -> L111;
        L111 -> L112 :: E1;
        L111 -> L113 :: E2;
        L112 -> [*] :: E1;
        L113 -> [*] :: E1;

        state L111
        {
            [*] -> L1111;
            L1111 -> L1112 :: E1;
            L1111 -> L1113 :: E2;
            L1112 -> [*] :: E1;
            L1113 -> [*] :: E1;

            state L1111
            {
                [*] -> L11111;
                L11111 -> L11112 :: E1;
                L11111 -> L11113 :: E2;
                L11112 -> [*] :: E1;
                L11113 -> [*] :: E1;

                state L11111
                {}

                state L11112
                {}

                state L11113
                {}
            }

            state L1112
            {}

            state L1113
            {}
        }

        state L112
        {}

        state L113
        {}
    }

    state L12
    {

    }
}
    """,
        entry_name="state_machine_dsl",
    )
    model = parse_dsl_node_to_state_machine(
        ast_node, path="test/testfile/sample_codes/dlc4.fcstm"
    )
    return model


@pytest.fixture()
def state_l1(model):
    return model.root_state


@pytest.fixture()
def state_l1_l11(state_l1):
    return state_l1.substates["L11"]


@pytest.fixture()
def state_l1_l11_l111(state_l1_l11):
    return state_l1_l11.substates["L111"]


@pytest.fixture()
def state_l1_l11_l111_l1111(state_l1_l11_l111):
    return state_l1_l11_l111.substates["L1111"]


@pytest.fixture()
def state_l1_l11_l111_l1111_l11111(state_l1_l11_l111_l1111):
    return state_l1_l11_l111_l1111.substates["L11111"]


@pytest.fixture()
def state_l1_l11_l111_l1111_l11112(state_l1_l11_l111_l1111):
    return state_l1_l11_l111_l1111.substates["L11112"]


@pytest.fixture()
def state_l1_l11_l111_l1111_l11113(state_l1_l11_l111_l1111):
    return state_l1_l11_l111_l1111.substates["L11113"]


@pytest.fixture()
def state_l1_l11_l111_l1112(state_l1_l11_l111):
    return state_l1_l11_l111.substates["L1112"]


@pytest.fixture()
def state_l1_l11_l111_l1113(state_l1_l11_l111):
    return state_l1_l11_l111.substates["L1113"]


@pytest.fixture()
def state_l1_l11_l111_forced_gate_0(state_l1_l11_l111):
    return state_l1_l11_l111.substates["__forced_gate_0"]


@pytest.fixture()
def state_l1_l11_l111_forced_gate_1(state_l1_l11_l111):
    return state_l1_l11_l111.substates["__forced_gate_1"]


@pytest.fixture()
def state_l1_l11_l112(state_l1_l11):
    return state_l1_l11.substates["L112"]


@pytest.fixture()
def state_l1_l11_l113(state_l1_l11):
    return state_l1_l11.substates["L113"]


@pytest.fixture()
def state_l1_l11_forced_gate_0(state_l1_l11):
    return state_l1_l11.substates["__forced_gate_0"]


@pytest.fixture()
def state_l1_l11_forced_gate_1(state_l1_l11):
    return state_l1_l11.substates["__forced_gate_1"]


@pytest.fixture()
def state_l1_l12(state_l1):
    return state_l1.substates["L12"]


@pytest.fixture()
def state_l1_forced_gate_0(state_l1):
    return state_l1.substates["__forced_gate_0"]


@pytest.mark.unittest
class TestModelStateL1:
    def test_model(self, model):
        assert model.defines == {
            "__forced_0": VarDefine(
                name="__forced_0", type="int", init=Integer(value=0), doc=None
            )
        }
        assert model.root_state.name == "L1"
        assert model.root_state.path == ("L1",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="__forced_0",
                type="int",
                expr=dsl_nodes.Integer(raw="0"),
                doc=None,
                spelling=None,
            )
        ]
        assert ast_node.root_state.name == "L1"

    def test_state_l1(self, state_l1):
        assert state_l1.name == "L1"
        assert state_l1.path == ("L1",)
        assert sorted(state_l1.substates.keys()) == ["L11", "L12", "__forced_gate_0"]
        assert state_l1.regions == {}
        assert state_l1.events == {}
        assert len(state_l1.transitions) == 5
        assert state_l1.transitions[0].from_state == "L11"
        assert state_l1.transitions[0].to_state == EXIT_STATE
        assert state_l1.transitions[0].event is None
        assert state_l1.transitions[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=1)
        )
        assert state_l1.transitions[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=0))
        ]
        assert state_l1.transitions[0].doc is None
        assert state_l1.transitions[0].parent_ref().name == "L1"
        assert state_l1.transitions[0].parent_ref().path == ("L1",)
        assert state_l1.transitions[0].target_history is None
        assert state_l1.transitions[0].history_role is None
        assert state_l1.transitions[0].history_user_guard is None
        assert state_l1.transitions[1].from_state == "L11"
        assert state_l1.transitions[1].to_state == "__forced_gate_0"
        assert state_l1.transitions[1].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1.transitions[1].guard is None
        assert state_l1.transitions[1].effects == []
        assert state_l1.transitions[1].doc is None
        assert state_l1.transitions[1].parent_ref().name == "L1"
        assert state_l1.transitions[1].parent_ref().path == ("L1",)
        assert state_l1.transitions[1].target_history is None
        assert state_l1.transitions[1].history_role is None
        assert state_l1.transitions[1].history_user_guard is None
        assert state_l1.transitions[2].from_state == INIT_STATE
        assert state_l1.transitions[2].to_state == "L11"
        assert state_l1.transitions[2].event is None
        assert state_l1.transitions[2].guard is None
        assert state_l1.transitions[2].effects == []
        assert state_l1.transitions[2].doc is None
        assert state_l1.transitions[2].parent_ref().name == "L1"
        assert state_l1.transitions[2].parent_ref().path == ("L1",)
        assert state_l1.transitions[2].target_history is None
        assert state_l1.transitions[2].history_role is None
        assert state_l1.transitions[2].history_user_guard is None
        assert state_l1.transitions[3].from_state == "L12"
        assert state_l1.transitions[3].to_state == EXIT_STATE
        assert state_l1.transitions[3].event is None
        assert state_l1.transitions[3].guard is None
        assert state_l1.transitions[3].effects == []
        assert state_l1.transitions[3].doc is None
        assert state_l1.transitions[3].parent_ref().name == "L1"
        assert state_l1.transitions[3].parent_ref().path == ("L1",)
        assert state_l1.transitions[3].target_history is None
        assert state_l1.transitions[3].history_role is None
        assert state_l1.transitions[3].history_user_guard is None
        assert state_l1.transitions[4].from_state == "__forced_gate_0"
        assert state_l1.transitions[4].to_state == EXIT_STATE
        assert state_l1.transitions[4].event is None
        assert state_l1.transitions[4].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1.transitions[4].effects == []
        assert state_l1.transitions[4].doc is None
        assert state_l1.transitions[4].parent_ref().name == "L1"
        assert state_l1.transitions[4].parent_ref().path == ("L1",)
        assert state_l1.transitions[4].target_history is None
        assert state_l1.transitions[4].history_role is None
        assert state_l1.transitions[4].history_user_guard is None
        assert state_l1.named_functions == {}
        assert state_l1.on_enters == []
        assert state_l1.on_durings == []
        assert state_l1.on_exits == []
        assert state_l1.on_during_aspects == []
        assert state_l1.parent_ref is None
        assert state_l1.substate_name_to_id == {
            "L11": 0,
            "L12": 1,
            "__forced_gate_0": 2,
        }
        assert state_l1.extra_name is None
        assert not state_l1.is_pseudo
        assert state_l1.doc is None
        assert not state_l1.is_history_gate
        assert not state_l1.is_forced_gate
        assert state_l1.abstract_on_during_aspects == []
        assert state_l1.abstract_on_durings == []
        assert state_l1.abstract_on_enters == []
        assert state_l1.abstract_on_exits == []
        assert len(state_l1.init_transitions) == 1
        assert state_l1.init_transitions[0].from_state == INIT_STATE
        assert state_l1.init_transitions[0].to_state == "L11"
        assert state_l1.init_transitions[0].event is None
        assert state_l1.init_transitions[0].guard is None
        assert state_l1.init_transitions[0].effects == []
        assert state_l1.init_transitions[0].doc is None
        assert state_l1.init_transitions[0].parent_ref().name == "L1"
        assert state_l1.init_transitions[0].parent_ref().path == ("L1",)
        assert state_l1.init_transitions[0].target_history is None
        assert state_l1.init_transitions[0].history_role is None
        assert state_l1.init_transitions[0].history_user_guard is None
        assert not state_l1.is_leaf_state
        assert state_l1.is_root_state
        assert not state_l1.is_stoppable
        assert state_l1.non_abstract_on_during_aspects == []
        assert state_l1.non_abstract_on_durings == []
        assert state_l1.non_abstract_on_enters == []
        assert state_l1.non_abstract_on_exits == []
        assert state_l1.parent is None
        assert len(state_l1.transitions_entering_children) == 1
        assert state_l1.transitions_entering_children[0].from_state == INIT_STATE
        assert state_l1.transitions_entering_children[0].to_state == "L11"
        assert state_l1.transitions_entering_children[0].event is None
        assert state_l1.transitions_entering_children[0].guard is None
        assert state_l1.transitions_entering_children[0].effects == []
        assert state_l1.transitions_entering_children[0].doc is None
        assert state_l1.transitions_entering_children[0].parent_ref().name == "L1"
        assert state_l1.transitions_entering_children[0].parent_ref().path == ("L1",)
        assert state_l1.transitions_entering_children[0].target_history is None
        assert state_l1.transitions_entering_children[0].history_role is None
        assert state_l1.transitions_entering_children[0].history_user_guard is None
        assert len(state_l1.transitions_entering_children_simplified) == 1
        assert (
            state_l1.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert state_l1.transitions_entering_children_simplified[0].to_state == "L11"
        assert state_l1.transitions_entering_children_simplified[0].event is None
        assert state_l1.transitions_entering_children_simplified[0].guard is None
        assert state_l1.transitions_entering_children_simplified[0].effects == []
        assert state_l1.transitions_entering_children_simplified[0].doc is None
        assert (
            state_l1.transitions_entering_children_simplified[0].parent_ref().name
            == "L1"
        )
        assert state_l1.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("L1",)
        assert (
            state_l1.transitions_entering_children_simplified[0].target_history is None
        )
        assert state_l1.transitions_entering_children_simplified[0].history_role is None
        assert (
            state_l1.transitions_entering_children_simplified[0].history_user_guard
            is None
        )
        assert len(state_l1.transitions_from) == 1
        assert state_l1.transitions_from[0].from_state == "L1"
        assert state_l1.transitions_from[0].to_state == EXIT_STATE
        assert state_l1.transitions_from[0].event is None
        assert state_l1.transitions_from[0].guard is None
        assert state_l1.transitions_from[0].effects == []
        assert state_l1.transitions_from[0].doc is None
        assert state_l1.transitions_from[0].parent_ref is None
        assert state_l1.transitions_from[0].target_history is None
        assert state_l1.transitions_from[0].history_role is None
        assert state_l1.transitions_from[0].history_user_guard is None
        assert len(state_l1.transitions_to) == 1
        assert state_l1.transitions_to[0].from_state == INIT_STATE
        assert state_l1.transitions_to[0].to_state == "L1"
        assert state_l1.transitions_to[0].event is None
        assert state_l1.transitions_to[0].guard is None
        assert state_l1.transitions_to[0].effects == []
        assert state_l1.transitions_to[0].doc is None
        assert state_l1.transitions_to[0].parent_ref is None
        assert state_l1.transitions_to[0].target_history is None
        assert state_l1.transitions_to[0].history_role is None
        assert state_l1.transitions_to[0].history_user_guard is None

    def test_state_l1_to_ast_node(self, state_l1):
        ast_node = state_l1.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L1",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="L11",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)
                    ],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="L111",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(
                                    name="E1", extra_name=None, doc=None
                                ),
                                dsl_nodes.EventDefinition(
                                    name="E2", extra_name=None, doc=None
                                ),
                            ],
                            imports=[],
                            substates=[
                                dsl_nodes.StateDefinition(
                                    name="L1111",
                                    extra_name=None,
                                    events=[
                                        dsl_nodes.EventDefinition(
                                            name="E1", extra_name=None, doc=None
                                        ),
                                        dsl_nodes.EventDefinition(
                                            name="E2", extra_name=None, doc=None
                                        ),
                                    ],
                                    imports=[],
                                    substates=[
                                        dsl_nodes.StateDefinition(
                                            name="L11111",
                                            extra_name=None,
                                            events=[
                                                dsl_nodes.EventDefinition(
                                                    name="E1", extra_name=None, doc=None
                                                ),
                                                dsl_nodes.EventDefinition(
                                                    name="E2", extra_name=None, doc=None
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
                                            doc=None,
                                            histories=[],
                                            regions=[],
                                        ),
                                        dsl_nodes.StateDefinition(
                                            name="L11112",
                                            extra_name=None,
                                            events=[
                                                dsl_nodes.EventDefinition(
                                                    name="E1", extra_name=None, doc=None
                                                )
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
                                            doc=None,
                                            histories=[],
                                            regions=[],
                                        ),
                                        dsl_nodes.StateDefinition(
                                            name="L11113",
                                            extra_name=None,
                                            events=[
                                                dsl_nodes.EventDefinition(
                                                    name="E1", extra_name=None, doc=None
                                                )
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
                                            doc=None,
                                            histories=[],
                                            regions=[],
                                        ),
                                    ],
                                    transitions=[
                                        dsl_nodes.TransitionDefinition(
                                            from_state="L11111",
                                            to_state=EXIT_STATE,
                                            event_id=dsl_nodes.ChainID(
                                                path=["L11", "E1"], is_absolute=True
                                            ),
                                            condition_expr=None,
                                            post_operations=[
                                                dsl_nodes.OperationAssignment(
                                                    name="__forced_0",
                                                    expr=dsl_nodes.Integer(raw="1"),
                                                )
                                            ],
                                            doc=None,
                                            target_history=None,
                                        ),
                                        dsl_nodes.TransitionDefinition(
                                            from_state="L11112",
                                            to_state=EXIT_STATE,
                                            event_id=dsl_nodes.ChainID(
                                                path=["L11", "E1"], is_absolute=True
                                            ),
                                            condition_expr=None,
                                            post_operations=[
                                                dsl_nodes.OperationAssignment(
                                                    name="__forced_0",
                                                    expr=dsl_nodes.Integer(raw="1"),
                                                )
                                            ],
                                            doc=None,
                                            target_history=None,
                                        ),
                                        dsl_nodes.TransitionDefinition(
                                            from_state="L11113",
                                            to_state=EXIT_STATE,
                                            event_id=dsl_nodes.ChainID(
                                                path=["L11", "E1"], is_absolute=True
                                            ),
                                            condition_expr=None,
                                            post_operations=[
                                                dsl_nodes.OperationAssignment(
                                                    name="__forced_0",
                                                    expr=dsl_nodes.Integer(raw="1"),
                                                )
                                            ],
                                            doc=None,
                                            target_history=None,
                                        ),
                                        dsl_nodes.TransitionDefinition(
                                            from_state=INIT_STATE,
                                            to_state="L11111",
                                            event_id=None,
                                            condition_expr=None,
                                            post_operations=[],
                                            doc=None,
                                            target_history=None,
                                        ),
                                        dsl_nodes.TransitionDefinition(
                                            from_state="L11111",
                                            to_state="L11112",
                                            event_id=dsl_nodes.ChainID(
                                                path=["L11111", "E1"], is_absolute=False
                                            ),
                                            condition_expr=None,
                                            post_operations=[],
                                            doc=None,
                                            target_history=None,
                                        ),
                                        dsl_nodes.TransitionDefinition(
                                            from_state="L11111",
                                            to_state="L11113",
                                            event_id=dsl_nodes.ChainID(
                                                path=["L11111", "E2"], is_absolute=False
                                            ),
                                            condition_expr=None,
                                            post_operations=[],
                                            doc=None,
                                            target_history=None,
                                        ),
                                        dsl_nodes.TransitionDefinition(
                                            from_state="L11112",
                                            to_state=EXIT_STATE,
                                            event_id=dsl_nodes.ChainID(
                                                path=["L11112", "E1"], is_absolute=False
                                            ),
                                            condition_expr=None,
                                            post_operations=[],
                                            doc=None,
                                            target_history=None,
                                        ),
                                        dsl_nodes.TransitionDefinition(
                                            from_state="L11113",
                                            to_state=EXIT_STATE,
                                            event_id=dsl_nodes.ChainID(
                                                path=["L11113", "E1"], is_absolute=False
                                            ),
                                            condition_expr=None,
                                            post_operations=[],
                                            doc=None,
                                            target_history=None,
                                        ),
                                    ],
                                    enters=[],
                                    durings=[],
                                    exits=[],
                                    during_aspects=[],
                                    force_transitions=[],
                                    is_pseudo=False,
                                    doc=None,
                                    histories=[],
                                    regions=[],
                                ),
                                dsl_nodes.StateDefinition(
                                    name="L1112",
                                    extra_name=None,
                                    events=[
                                        dsl_nodes.EventDefinition(
                                            name="E1", extra_name=None, doc=None
                                        )
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
                                    doc=None,
                                    histories=[],
                                    regions=[],
                                ),
                                dsl_nodes.StateDefinition(
                                    name="L1113",
                                    extra_name=None,
                                    events=[
                                        dsl_nodes.EventDefinition(
                                            name="E1", extra_name=None, doc=None
                                        )
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
                                    doc=None,
                                    histories=[],
                                    regions=[],
                                ),
                                dsl_nodes.StateDefinition(
                                    name="__forced_gate_0",
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
                                    is_pseudo=True,
                                    doc=None,
                                    histories=[],
                                    regions=[],
                                ),
                                dsl_nodes.StateDefinition(
                                    name="__forced_gate_1",
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
                                    is_pseudo=True,
                                    doc=None,
                                    histories=[],
                                    regions=[],
                                ),
                            ],
                            transitions=[
                                dsl_nodes.TransitionDefinition(
                                    from_state="L1111",
                                    to_state=EXIT_STATE,
                                    event_id=None,
                                    condition_expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="__forced_0"),
                                        op="==",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L1112",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["L11", "E1"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[
                                        dsl_nodes.OperationAssignment(
                                            name="__forced_0",
                                            expr=dsl_nodes.Integer(raw="1"),
                                        )
                                    ],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L1113",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["L11", "E1"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[
                                        dsl_nodes.OperationAssignment(
                                            name="__forced_0",
                                            expr=dsl_nodes.Integer(raw="1"),
                                        )
                                    ],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state=INIT_STATE,
                                    to_state="L1111",
                                    event_id=None,
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L1111",
                                    to_state="__forced_gate_0",
                                    event_id=dsl_nodes.ChainID(
                                        path=["L1111", "E1"], is_absolute=False
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L1111",
                                    to_state="__forced_gate_1",
                                    event_id=dsl_nodes.ChainID(
                                        path=["L1111", "E2"], is_absolute=False
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L1112",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["L1112", "E1"], is_absolute=False
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L1113",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["L1113", "E1"], is_absolute=False
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="__forced_gate_0",
                                    to_state="L1112",
                                    event_id=None,
                                    condition_expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="__forced_0"),
                                        op="==",
                                        expr2=dsl_nodes.Integer(raw="0"),
                                    ),
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="__forced_gate_1",
                                    to_state="L1113",
                                    event_id=None,
                                    condition_expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="__forced_0"),
                                        op="==",
                                        expr2=dsl_nodes.Integer(raw="0"),
                                    ),
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                            ],
                            enters=[],
                            durings=[],
                            exits=[],
                            during_aspects=[],
                            force_transitions=[],
                            is_pseudo=False,
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="L112",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(
                                    name="E1", extra_name=None, doc=None
                                )
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
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="L113",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(
                                    name="E1", extra_name=None, doc=None
                                )
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
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="__forced_gate_0",
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
                            is_pseudo=True,
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="__forced_gate_1",
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
                            is_pseudo=True,
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                    ],
                    transitions=[
                        dsl_nodes.TransitionDefinition(
                            from_state="L111",
                            to_state=EXIT_STATE,
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="__forced_0"),
                                op="==",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L112",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=False),
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                                )
                            ],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L113",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=False),
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                                )
                            ],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="L111",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L111",
                            to_state="__forced_gate_0",
                            event_id=dsl_nodes.ChainID(
                                path=["L111", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L111",
                            to_state="__forced_gate_1",
                            event_id=dsl_nodes.ChainID(
                                path=["L111", "E2"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L112",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L112", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L113",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L113", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="__forced_gate_0",
                            to_state="L112",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="__forced_0"),
                                op="==",
                                expr2=dsl_nodes.Integer(raw="0"),
                            ),
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="__forced_gate_1",
                            to_state="L113",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="__forced_0"),
                                op="==",
                                expr2=dsl_nodes.Integer(raw="0"),
                            ),
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                    ],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="L12",
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
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="__forced_gate_0",
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
                    is_pseudo=True,
                    doc=None,
                    histories=[],
                    regions=[],
                ),
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="L11",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="__forced_0"),
                        op="==",
                        expr2=dsl_nodes.Integer(raw="1"),
                    ),
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="__forced_0", expr=dsl_nodes.Integer(raw="0")
                        )
                    ],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L11",
                    to_state="__forced_gate_0",
                    event_id=dsl_nodes.ChainID(path=["L11", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="L11",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L12",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="__forced_gate_0",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="__forced_0"),
                        op="==",
                        expr2=dsl_nodes.Integer(raw="0"),
                    ),
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
            ],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_list_on_enters(self, state_l1):
        lst = state_l1.list_on_enters()
        assert lst == []

        lst = state_l1.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_during_aspects(self, state_l1):
        lst = state_l1.list_on_during_aspects()
        assert lst == []

        lst = state_l1.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_l1.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_l1.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_l1.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_l1_l11(self, state_l1_l11):
        assert state_l1_l11.name == "L11"
        assert state_l1_l11.path == ("L1", "L11")
        assert sorted(state_l1_l11.substates.keys()) == [
            "L111",
            "L112",
            "L113",
            "__forced_gate_0",
            "__forced_gate_1",
        ]
        assert state_l1_l11.regions == {}
        assert state_l1_l11.events == {
            "E1": Event(name="E1", state_path=("L1", "L11"), extra_name=None, doc=None)
        }
        assert len(state_l1_l11.transitions) == 10
        assert state_l1_l11.transitions[0].from_state == "L111"
        assert state_l1_l11.transitions[0].to_state == EXIT_STATE
        assert state_l1_l11.transitions[0].event is None
        assert state_l1_l11.transitions[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=1)
        )
        assert state_l1_l11.transitions[0].effects == []
        assert state_l1_l11.transitions[0].doc is None
        assert state_l1_l11.transitions[0].parent_ref().name == "L11"
        assert state_l1_l11.transitions[0].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[0].target_history is None
        assert state_l1_l11.transitions[0].history_role is None
        assert state_l1_l11.transitions[0].history_user_guard is None
        assert state_l1_l11.transitions[1].from_state == "L112"
        assert state_l1_l11.transitions[1].to_state == EXIT_STATE
        assert state_l1_l11.transitions[1].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11.transitions[1].guard is None
        assert state_l1_l11.transitions[1].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11.transitions[1].doc is None
        assert state_l1_l11.transitions[1].parent_ref().name == "L11"
        assert state_l1_l11.transitions[1].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[1].target_history is None
        assert state_l1_l11.transitions[1].history_role is None
        assert state_l1_l11.transitions[1].history_user_guard is None
        assert state_l1_l11.transitions[2].from_state == "L113"
        assert state_l1_l11.transitions[2].to_state == EXIT_STATE
        assert state_l1_l11.transitions[2].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11.transitions[2].guard is None
        assert state_l1_l11.transitions[2].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11.transitions[2].doc is None
        assert state_l1_l11.transitions[2].parent_ref().name == "L11"
        assert state_l1_l11.transitions[2].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[2].target_history is None
        assert state_l1_l11.transitions[2].history_role is None
        assert state_l1_l11.transitions[2].history_user_guard is None
        assert state_l1_l11.transitions[3].from_state == INIT_STATE
        assert state_l1_l11.transitions[3].to_state == "L111"
        assert state_l1_l11.transitions[3].event is None
        assert state_l1_l11.transitions[3].guard is None
        assert state_l1_l11.transitions[3].effects == []
        assert state_l1_l11.transitions[3].doc is None
        assert state_l1_l11.transitions[3].parent_ref().name == "L11"
        assert state_l1_l11.transitions[3].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[3].target_history is None
        assert state_l1_l11.transitions[3].history_role is None
        assert state_l1_l11.transitions[3].history_user_guard is None
        assert state_l1_l11.transitions[4].from_state == "L111"
        assert state_l1_l11.transitions[4].to_state == "__forced_gate_0"
        assert state_l1_l11.transitions[4].event == Event(
            name="E1", state_path=("L1", "L11", "L111"), extra_name=None, doc=None
        )
        assert state_l1_l11.transitions[4].guard is None
        assert state_l1_l11.transitions[4].effects == []
        assert state_l1_l11.transitions[4].doc is None
        assert state_l1_l11.transitions[4].parent_ref().name == "L11"
        assert state_l1_l11.transitions[4].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[4].target_history is None
        assert state_l1_l11.transitions[4].history_role is None
        assert state_l1_l11.transitions[4].history_user_guard is None
        assert state_l1_l11.transitions[5].from_state == "L111"
        assert state_l1_l11.transitions[5].to_state == "__forced_gate_1"
        assert state_l1_l11.transitions[5].event == Event(
            name="E2", state_path=("L1", "L11", "L111"), extra_name=None, doc=None
        )
        assert state_l1_l11.transitions[5].guard is None
        assert state_l1_l11.transitions[5].effects == []
        assert state_l1_l11.transitions[5].doc is None
        assert state_l1_l11.transitions[5].parent_ref().name == "L11"
        assert state_l1_l11.transitions[5].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[5].target_history is None
        assert state_l1_l11.transitions[5].history_role is None
        assert state_l1_l11.transitions[5].history_user_guard is None
        assert state_l1_l11.transitions[6].from_state == "L112"
        assert state_l1_l11.transitions[6].to_state == EXIT_STATE
        assert state_l1_l11.transitions[6].event == Event(
            name="E1", state_path=("L1", "L11", "L112"), extra_name=None, doc=None
        )
        assert state_l1_l11.transitions[6].guard is None
        assert state_l1_l11.transitions[6].effects == []
        assert state_l1_l11.transitions[6].doc is None
        assert state_l1_l11.transitions[6].parent_ref().name == "L11"
        assert state_l1_l11.transitions[6].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[6].target_history is None
        assert state_l1_l11.transitions[6].history_role is None
        assert state_l1_l11.transitions[6].history_user_guard is None
        assert state_l1_l11.transitions[7].from_state == "L113"
        assert state_l1_l11.transitions[7].to_state == EXIT_STATE
        assert state_l1_l11.transitions[7].event == Event(
            name="E1", state_path=("L1", "L11", "L113"), extra_name=None, doc=None
        )
        assert state_l1_l11.transitions[7].guard is None
        assert state_l1_l11.transitions[7].effects == []
        assert state_l1_l11.transitions[7].doc is None
        assert state_l1_l11.transitions[7].parent_ref().name == "L11"
        assert state_l1_l11.transitions[7].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[7].target_history is None
        assert state_l1_l11.transitions[7].history_role is None
        assert state_l1_l11.transitions[7].history_user_guard is None
        assert state_l1_l11.transitions[8].from_state == "__forced_gate_0"
        assert state_l1_l11.transitions[8].to_state == "L112"
        assert state_l1_l11.transitions[8].event is None
        assert state_l1_l11.transitions[8].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11.transitions[8].effects == []
        assert state_l1_l11.transitions[8].doc is None
        assert state_l1_l11.transitions[8].parent_ref().name == "L11"
        assert state_l1_l11.transitions[8].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[8].target_history is None
        assert state_l1_l11.transitions[8].history_role is None
        assert state_l1_l11.transitions[8].history_user_guard is None
        assert state_l1_l11.transitions[9].from_state == "__forced_gate_1"
        assert state_l1_l11.transitions[9].to_state == "L113"
        assert state_l1_l11.transitions[9].event is None
        assert state_l1_l11.transitions[9].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11.transitions[9].effects == []
        assert state_l1_l11.transitions[9].doc is None
        assert state_l1_l11.transitions[9].parent_ref().name == "L11"
        assert state_l1_l11.transitions[9].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.transitions[9].target_history is None
        assert state_l1_l11.transitions[9].history_role is None
        assert state_l1_l11.transitions[9].history_user_guard is None
        assert state_l1_l11.named_functions == {}
        assert state_l1_l11.on_enters == []
        assert state_l1_l11.on_durings == []
        assert state_l1_l11.on_exits == []
        assert state_l1_l11.on_during_aspects == []
        assert state_l1_l11.parent_ref().name == "L1"
        assert state_l1_l11.parent_ref().path == ("L1",)
        assert state_l1_l11.substate_name_to_id == {
            "L111": 0,
            "L112": 1,
            "L113": 2,
            "__forced_gate_0": 3,
            "__forced_gate_1": 4,
        }
        assert state_l1_l11.extra_name is None
        assert not state_l1_l11.is_pseudo
        assert state_l1_l11.doc is None
        assert not state_l1_l11.is_history_gate
        assert not state_l1_l11.is_forced_gate
        assert state_l1_l11.abstract_on_during_aspects == []
        assert state_l1_l11.abstract_on_durings == []
        assert state_l1_l11.abstract_on_enters == []
        assert state_l1_l11.abstract_on_exits == []
        assert len(state_l1_l11.init_transitions) == 1
        assert state_l1_l11.init_transitions[0].from_state == INIT_STATE
        assert state_l1_l11.init_transitions[0].to_state == "L111"
        assert state_l1_l11.init_transitions[0].event is None
        assert state_l1_l11.init_transitions[0].guard is None
        assert state_l1_l11.init_transitions[0].effects == []
        assert state_l1_l11.init_transitions[0].doc is None
        assert state_l1_l11.init_transitions[0].parent_ref().name == "L11"
        assert state_l1_l11.init_transitions[0].parent_ref().path == ("L1", "L11")
        assert state_l1_l11.init_transitions[0].target_history is None
        assert state_l1_l11.init_transitions[0].history_role is None
        assert state_l1_l11.init_transitions[0].history_user_guard is None
        assert not state_l1_l11.is_leaf_state
        assert not state_l1_l11.is_root_state
        assert not state_l1_l11.is_stoppable
        assert state_l1_l11.non_abstract_on_during_aspects == []
        assert state_l1_l11.non_abstract_on_durings == []
        assert state_l1_l11.non_abstract_on_enters == []
        assert state_l1_l11.non_abstract_on_exits == []
        assert state_l1_l11.parent.name == "L1"
        assert state_l1_l11.parent.path == ("L1",)
        assert len(state_l1_l11.transitions_entering_children) == 1
        assert state_l1_l11.transitions_entering_children[0].from_state == INIT_STATE
        assert state_l1_l11.transitions_entering_children[0].to_state == "L111"
        assert state_l1_l11.transitions_entering_children[0].event is None
        assert state_l1_l11.transitions_entering_children[0].guard is None
        assert state_l1_l11.transitions_entering_children[0].effects == []
        assert state_l1_l11.transitions_entering_children[0].doc is None
        assert state_l1_l11.transitions_entering_children[0].parent_ref().name == "L11"
        assert state_l1_l11.transitions_entering_children[0].parent_ref().path == (
            "L1",
            "L11",
        )
        assert state_l1_l11.transitions_entering_children[0].target_history is None
        assert state_l1_l11.transitions_entering_children[0].history_role is None
        assert state_l1_l11.transitions_entering_children[0].history_user_guard is None
        assert len(state_l1_l11.transitions_entering_children_simplified) == 1
        assert (
            state_l1_l11.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_l1_l11.transitions_entering_children_simplified[0].to_state == "L111"
        )
        assert state_l1_l11.transitions_entering_children_simplified[0].event is None
        assert state_l1_l11.transitions_entering_children_simplified[0].guard is None
        assert state_l1_l11.transitions_entering_children_simplified[0].effects == []
        assert state_l1_l11.transitions_entering_children_simplified[0].doc is None
        assert (
            state_l1_l11.transitions_entering_children_simplified[0].parent_ref().name
            == "L11"
        )
        assert state_l1_l11.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("L1", "L11")
        assert (
            state_l1_l11.transitions_entering_children_simplified[0].target_history
            is None
        )
        assert (
            state_l1_l11.transitions_entering_children_simplified[0].history_role
            is None
        )
        assert (
            state_l1_l11.transitions_entering_children_simplified[0].history_user_guard
            is None
        )
        assert len(state_l1_l11.transitions_from) == 2
        assert state_l1_l11.transitions_from[0].from_state == "L11"
        assert state_l1_l11.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11.transitions_from[0].event is None
        assert state_l1_l11.transitions_from[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=1)
        )
        assert state_l1_l11.transitions_from[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=0))
        ]
        assert state_l1_l11.transitions_from[0].doc is None
        assert state_l1_l11.transitions_from[0].parent_ref().name == "L1"
        assert state_l1_l11.transitions_from[0].parent_ref().path == ("L1",)
        assert state_l1_l11.transitions_from[0].target_history is None
        assert state_l1_l11.transitions_from[0].history_role is None
        assert state_l1_l11.transitions_from[0].history_user_guard is None
        assert state_l1_l11.transitions_from[1].from_state == "L11"
        assert state_l1_l11.transitions_from[1].to_state == "__forced_gate_0"
        assert state_l1_l11.transitions_from[1].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11.transitions_from[1].guard is None
        assert state_l1_l11.transitions_from[1].effects == []
        assert state_l1_l11.transitions_from[1].doc is None
        assert state_l1_l11.transitions_from[1].parent_ref().name == "L1"
        assert state_l1_l11.transitions_from[1].parent_ref().path == ("L1",)
        assert state_l1_l11.transitions_from[1].target_history is None
        assert state_l1_l11.transitions_from[1].history_role is None
        assert state_l1_l11.transitions_from[1].history_user_guard is None
        assert len(state_l1_l11.transitions_to) == 1
        assert state_l1_l11.transitions_to[0].from_state == INIT_STATE
        assert state_l1_l11.transitions_to[0].to_state == "L11"
        assert state_l1_l11.transitions_to[0].event is None
        assert state_l1_l11.transitions_to[0].guard is None
        assert state_l1_l11.transitions_to[0].effects == []
        assert state_l1_l11.transitions_to[0].doc is None
        assert state_l1_l11.transitions_to[0].parent_ref().name == "L1"
        assert state_l1_l11.transitions_to[0].parent_ref().path == ("L1",)
        assert state_l1_l11.transitions_to[0].target_history is None
        assert state_l1_l11.transitions_to[0].history_role is None
        assert state_l1_l11.transitions_to[0].history_user_guard is None

    def test_state_l1_l11_to_ast_node(self, state_l1_l11):
        ast_node = state_l1_l11.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L11",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="L111",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None),
                        dsl_nodes.EventDefinition(name="E2", extra_name=None, doc=None),
                    ],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="L1111",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(
                                    name="E1", extra_name=None, doc=None
                                ),
                                dsl_nodes.EventDefinition(
                                    name="E2", extra_name=None, doc=None
                                ),
                            ],
                            imports=[],
                            substates=[
                                dsl_nodes.StateDefinition(
                                    name="L11111",
                                    extra_name=None,
                                    events=[
                                        dsl_nodes.EventDefinition(
                                            name="E1", extra_name=None, doc=None
                                        ),
                                        dsl_nodes.EventDefinition(
                                            name="E2", extra_name=None, doc=None
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
                                    doc=None,
                                    histories=[],
                                    regions=[],
                                ),
                                dsl_nodes.StateDefinition(
                                    name="L11112",
                                    extra_name=None,
                                    events=[
                                        dsl_nodes.EventDefinition(
                                            name="E1", extra_name=None, doc=None
                                        )
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
                                    doc=None,
                                    histories=[],
                                    regions=[],
                                ),
                                dsl_nodes.StateDefinition(
                                    name="L11113",
                                    extra_name=None,
                                    events=[
                                        dsl_nodes.EventDefinition(
                                            name="E1", extra_name=None, doc=None
                                        )
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
                                    doc=None,
                                    histories=[],
                                    regions=[],
                                ),
                            ],
                            transitions=[
                                dsl_nodes.TransitionDefinition(
                                    from_state="L11111",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["L11", "E1"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[
                                        dsl_nodes.OperationAssignment(
                                            name="__forced_0",
                                            expr=dsl_nodes.Integer(raw="1"),
                                        )
                                    ],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L11112",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["L11", "E1"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[
                                        dsl_nodes.OperationAssignment(
                                            name="__forced_0",
                                            expr=dsl_nodes.Integer(raw="1"),
                                        )
                                    ],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L11113",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["L11", "E1"], is_absolute=True
                                    ),
                                    condition_expr=None,
                                    post_operations=[
                                        dsl_nodes.OperationAssignment(
                                            name="__forced_0",
                                            expr=dsl_nodes.Integer(raw="1"),
                                        )
                                    ],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state=INIT_STATE,
                                    to_state="L11111",
                                    event_id=None,
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L11111",
                                    to_state="L11112",
                                    event_id=dsl_nodes.ChainID(
                                        path=["L11111", "E1"], is_absolute=False
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L11111",
                                    to_state="L11113",
                                    event_id=dsl_nodes.ChainID(
                                        path=["L11111", "E2"], is_absolute=False
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L11112",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["L11112", "E1"], is_absolute=False
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                                dsl_nodes.TransitionDefinition(
                                    from_state="L11113",
                                    to_state=EXIT_STATE,
                                    event_id=dsl_nodes.ChainID(
                                        path=["L11113", "E1"], is_absolute=False
                                    ),
                                    condition_expr=None,
                                    post_operations=[],
                                    doc=None,
                                    target_history=None,
                                ),
                            ],
                            enters=[],
                            durings=[],
                            exits=[],
                            during_aspects=[],
                            force_transitions=[],
                            is_pseudo=False,
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="L1112",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(
                                    name="E1", extra_name=None, doc=None
                                )
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
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="L1113",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(
                                    name="E1", extra_name=None, doc=None
                                )
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
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="__forced_gate_0",
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
                            is_pseudo=True,
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="__forced_gate_1",
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
                            is_pseudo=True,
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                    ],
                    transitions=[
                        dsl_nodes.TransitionDefinition(
                            from_state="L1111",
                            to_state=EXIT_STATE,
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="__forced_0"),
                                op="==",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L1112",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L11", "E1"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                                )
                            ],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L1113",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L11", "E1"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                                )
                            ],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="L1111",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L1111",
                            to_state="__forced_gate_0",
                            event_id=dsl_nodes.ChainID(
                                path=["L1111", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L1111",
                            to_state="__forced_gate_1",
                            event_id=dsl_nodes.ChainID(
                                path=["L1111", "E2"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L1112",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L1112", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L1113",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L1113", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="__forced_gate_0",
                            to_state="L1112",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="__forced_0"),
                                op="==",
                                expr2=dsl_nodes.Integer(raw="0"),
                            ),
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="__forced_gate_1",
                            to_state="L1113",
                            event_id=None,
                            condition_expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="__forced_0"),
                                op="==",
                                expr2=dsl_nodes.Integer(raw="0"),
                            ),
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                    ],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="L112",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)
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
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="L113",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)
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
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="__forced_gate_0",
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
                    is_pseudo=True,
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="__forced_gate_1",
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
                    is_pseudo=True,
                    doc=None,
                    histories=[],
                    regions=[],
                ),
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="L111",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="__forced_0"),
                        op="==",
                        expr2=dsl_nodes.Integer(raw="1"),
                    ),
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L112",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L113",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="L111",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L111",
                    to_state="__forced_gate_0",
                    event_id=dsl_nodes.ChainID(path=["L111", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L111",
                    to_state="__forced_gate_1",
                    event_id=dsl_nodes.ChainID(path=["L111", "E2"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L112",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L112", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L113",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L113", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="__forced_gate_0",
                    to_state="L112",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="__forced_0"),
                        op="==",
                        expr2=dsl_nodes.Integer(raw="0"),
                    ),
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="__forced_gate_1",
                    to_state="L113",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="__forced_0"),
                        op="==",
                        expr2=dsl_nodes.Integer(raw="0"),
                    ),
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
            ],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_list_on_enters(self, state_l1_l11):
        lst = state_l1_l11.list_on_enters()
        assert lst == []

        lst = state_l1_l11.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1_l11.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1_l11.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l11.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l11_during_aspects(self, state_l1_l11):
        lst = state_l1_l11.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_l1_l11.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_l1_l11.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_l1_l11.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_l1_l11_l111(self, state_l1_l11_l111):
        assert state_l1_l11_l111.name == "L111"
        assert state_l1_l11_l111.path == ("L1", "L11", "L111")
        assert sorted(state_l1_l11_l111.substates.keys()) == [
            "L1111",
            "L1112",
            "L1113",
            "__forced_gate_0",
            "__forced_gate_1",
        ]
        assert state_l1_l11_l111.regions == {}
        assert state_l1_l11_l111.events == {
            "E1": Event(
                name="E1", state_path=("L1", "L11", "L111"), extra_name=None, doc=None
            ),
            "E2": Event(
                name="E2", state_path=("L1", "L11", "L111"), extra_name=None, doc=None
            ),
        }
        assert len(state_l1_l11_l111.transitions) == 10
        assert state_l1_l11_l111.transitions[0].from_state == "L1111"
        assert state_l1_l11_l111.transitions[0].to_state == EXIT_STATE
        assert state_l1_l11_l111.transitions[0].event is None
        assert state_l1_l11_l111.transitions[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=1)
        )
        assert state_l1_l11_l111.transitions[0].effects == []
        assert state_l1_l11_l111.transitions[0].doc is None
        assert state_l1_l11_l111.transitions[0].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[0].target_history is None
        assert state_l1_l11_l111.transitions[0].history_role is None
        assert state_l1_l11_l111.transitions[0].history_user_guard is None
        assert state_l1_l11_l111.transitions[1].from_state == "L1112"
        assert state_l1_l11_l111.transitions[1].to_state == EXIT_STATE
        assert state_l1_l11_l111.transitions[1].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111.transitions[1].guard is None
        assert state_l1_l11_l111.transitions[1].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111.transitions[1].doc is None
        assert state_l1_l11_l111.transitions[1].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[1].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[1].target_history is None
        assert state_l1_l11_l111.transitions[1].history_role is None
        assert state_l1_l11_l111.transitions[1].history_user_guard is None
        assert state_l1_l11_l111.transitions[2].from_state == "L1113"
        assert state_l1_l11_l111.transitions[2].to_state == EXIT_STATE
        assert state_l1_l11_l111.transitions[2].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111.transitions[2].guard is None
        assert state_l1_l11_l111.transitions[2].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111.transitions[2].doc is None
        assert state_l1_l11_l111.transitions[2].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[2].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[2].target_history is None
        assert state_l1_l11_l111.transitions[2].history_role is None
        assert state_l1_l11_l111.transitions[2].history_user_guard is None
        assert state_l1_l11_l111.transitions[3].from_state == INIT_STATE
        assert state_l1_l11_l111.transitions[3].to_state == "L1111"
        assert state_l1_l11_l111.transitions[3].event is None
        assert state_l1_l11_l111.transitions[3].guard is None
        assert state_l1_l11_l111.transitions[3].effects == []
        assert state_l1_l11_l111.transitions[3].doc is None
        assert state_l1_l11_l111.transitions[3].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[3].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[3].target_history is None
        assert state_l1_l11_l111.transitions[3].history_role is None
        assert state_l1_l11_l111.transitions[3].history_user_guard is None
        assert state_l1_l11_l111.transitions[4].from_state == "L1111"
        assert state_l1_l11_l111.transitions[4].to_state == "__forced_gate_0"
        assert state_l1_l11_l111.transitions[4].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111.transitions[4].guard is None
        assert state_l1_l11_l111.transitions[4].effects == []
        assert state_l1_l11_l111.transitions[4].doc is None
        assert state_l1_l11_l111.transitions[4].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[4].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[4].target_history is None
        assert state_l1_l11_l111.transitions[4].history_role is None
        assert state_l1_l11_l111.transitions[4].history_user_guard is None
        assert state_l1_l11_l111.transitions[5].from_state == "L1111"
        assert state_l1_l11_l111.transitions[5].to_state == "__forced_gate_1"
        assert state_l1_l11_l111.transitions[5].event == Event(
            name="E2",
            state_path=("L1", "L11", "L111", "L1111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111.transitions[5].guard is None
        assert state_l1_l11_l111.transitions[5].effects == []
        assert state_l1_l11_l111.transitions[5].doc is None
        assert state_l1_l11_l111.transitions[5].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[5].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[5].target_history is None
        assert state_l1_l11_l111.transitions[5].history_role is None
        assert state_l1_l11_l111.transitions[5].history_user_guard is None
        assert state_l1_l11_l111.transitions[6].from_state == "L1112"
        assert state_l1_l11_l111.transitions[6].to_state == EXIT_STATE
        assert state_l1_l11_l111.transitions[6].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1112"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111.transitions[6].guard is None
        assert state_l1_l11_l111.transitions[6].effects == []
        assert state_l1_l11_l111.transitions[6].doc is None
        assert state_l1_l11_l111.transitions[6].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[6].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[6].target_history is None
        assert state_l1_l11_l111.transitions[6].history_role is None
        assert state_l1_l11_l111.transitions[6].history_user_guard is None
        assert state_l1_l11_l111.transitions[7].from_state == "L1113"
        assert state_l1_l11_l111.transitions[7].to_state == EXIT_STATE
        assert state_l1_l11_l111.transitions[7].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1113"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111.transitions[7].guard is None
        assert state_l1_l11_l111.transitions[7].effects == []
        assert state_l1_l11_l111.transitions[7].doc is None
        assert state_l1_l11_l111.transitions[7].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[7].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[7].target_history is None
        assert state_l1_l11_l111.transitions[7].history_role is None
        assert state_l1_l11_l111.transitions[7].history_user_guard is None
        assert state_l1_l11_l111.transitions[8].from_state == "__forced_gate_0"
        assert state_l1_l11_l111.transitions[8].to_state == "L1112"
        assert state_l1_l11_l111.transitions[8].event is None
        assert state_l1_l11_l111.transitions[8].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_l111.transitions[8].effects == []
        assert state_l1_l11_l111.transitions[8].doc is None
        assert state_l1_l11_l111.transitions[8].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[8].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[8].target_history is None
        assert state_l1_l11_l111.transitions[8].history_role is None
        assert state_l1_l11_l111.transitions[8].history_user_guard is None
        assert state_l1_l11_l111.transitions[9].from_state == "__forced_gate_1"
        assert state_l1_l11_l111.transitions[9].to_state == "L1113"
        assert state_l1_l11_l111.transitions[9].event is None
        assert state_l1_l11_l111.transitions[9].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_l111.transitions[9].effects == []
        assert state_l1_l11_l111.transitions[9].doc is None
        assert state_l1_l11_l111.transitions[9].parent_ref().name == "L111"
        assert state_l1_l11_l111.transitions[9].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions[9].target_history is None
        assert state_l1_l11_l111.transitions[9].history_role is None
        assert state_l1_l11_l111.transitions[9].history_user_guard is None
        assert state_l1_l11_l111.named_functions == {}
        assert state_l1_l11_l111.on_enters == []
        assert state_l1_l11_l111.on_durings == []
        assert state_l1_l11_l111.on_exits == []
        assert state_l1_l11_l111.on_during_aspects == []
        assert state_l1_l11_l111.parent_ref().name == "L11"
        assert state_l1_l11_l111.parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l111.substate_name_to_id == {
            "L1111": 0,
            "L1112": 1,
            "L1113": 2,
            "__forced_gate_0": 3,
            "__forced_gate_1": 4,
        }
        assert state_l1_l11_l111.extra_name is None
        assert not state_l1_l11_l111.is_pseudo
        assert state_l1_l11_l111.doc is None
        assert not state_l1_l11_l111.is_history_gate
        assert not state_l1_l11_l111.is_forced_gate
        assert state_l1_l11_l111.abstract_on_during_aspects == []
        assert state_l1_l11_l111.abstract_on_durings == []
        assert state_l1_l11_l111.abstract_on_enters == []
        assert state_l1_l11_l111.abstract_on_exits == []
        assert len(state_l1_l11_l111.init_transitions) == 1
        assert state_l1_l11_l111.init_transitions[0].from_state == INIT_STATE
        assert state_l1_l11_l111.init_transitions[0].to_state == "L1111"
        assert state_l1_l11_l111.init_transitions[0].event is None
        assert state_l1_l11_l111.init_transitions[0].guard is None
        assert state_l1_l11_l111.init_transitions[0].effects == []
        assert state_l1_l11_l111.init_transitions[0].doc is None
        assert state_l1_l11_l111.init_transitions[0].parent_ref().name == "L111"
        assert state_l1_l11_l111.init_transitions[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.init_transitions[0].target_history is None
        assert state_l1_l11_l111.init_transitions[0].history_role is None
        assert state_l1_l11_l111.init_transitions[0].history_user_guard is None
        assert not state_l1_l11_l111.is_leaf_state
        assert not state_l1_l11_l111.is_root_state
        assert not state_l1_l11_l111.is_stoppable
        assert state_l1_l11_l111.non_abstract_on_during_aspects == []
        assert state_l1_l11_l111.non_abstract_on_durings == []
        assert state_l1_l11_l111.non_abstract_on_enters == []
        assert state_l1_l11_l111.non_abstract_on_exits == []
        assert state_l1_l11_l111.parent.name == "L11"
        assert state_l1_l11_l111.parent.path == ("L1", "L11")
        assert len(state_l1_l11_l111.transitions_entering_children) == 1
        assert (
            state_l1_l11_l111.transitions_entering_children[0].from_state == INIT_STATE
        )
        assert state_l1_l11_l111.transitions_entering_children[0].to_state == "L1111"
        assert state_l1_l11_l111.transitions_entering_children[0].event is None
        assert state_l1_l11_l111.transitions_entering_children[0].guard is None
        assert state_l1_l11_l111.transitions_entering_children[0].effects == []
        assert state_l1_l11_l111.transitions_entering_children[0].doc is None
        assert (
            state_l1_l11_l111.transitions_entering_children[0].parent_ref().name
            == "L111"
        )
        assert state_l1_l11_l111.transitions_entering_children[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111.transitions_entering_children[0].target_history is None
        assert state_l1_l11_l111.transitions_entering_children[0].history_role is None
        assert (
            state_l1_l11_l111.transitions_entering_children[0].history_user_guard
            is None
        )
        assert len(state_l1_l11_l111.transitions_entering_children_simplified) == 1
        assert (
            state_l1_l11_l111.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert (
            state_l1_l11_l111.transitions_entering_children_simplified[0].to_state
            == "L1111"
        )
        assert (
            state_l1_l11_l111.transitions_entering_children_simplified[0].event is None
        )
        assert (
            state_l1_l11_l111.transitions_entering_children_simplified[0].guard is None
        )
        assert (
            state_l1_l11_l111.transitions_entering_children_simplified[0].effects == []
        )
        assert state_l1_l11_l111.transitions_entering_children_simplified[0].doc is None
        assert (
            state_l1_l11_l111.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "L111"
        )
        assert state_l1_l11_l111.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("L1", "L11", "L111")
        assert (
            state_l1_l11_l111.transitions_entering_children_simplified[0].target_history
            is None
        )
        assert (
            state_l1_l11_l111.transitions_entering_children_simplified[0].history_role
            is None
        )
        assert (
            state_l1_l11_l111.transitions_entering_children_simplified[
                0
            ].history_user_guard
            is None
        )
        assert len(state_l1_l11_l111.transitions_from) == 3
        assert state_l1_l11_l111.transitions_from[0].from_state == "L111"
        assert state_l1_l11_l111.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11_l111.transitions_from[0].event is None
        assert state_l1_l11_l111.transitions_from[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=1)
        )
        assert state_l1_l11_l111.transitions_from[0].effects == []
        assert state_l1_l11_l111.transitions_from[0].doc is None
        assert state_l1_l11_l111.transitions_from[0].parent_ref().name == "L11"
        assert state_l1_l11_l111.transitions_from[0].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l111.transitions_from[0].target_history is None
        assert state_l1_l11_l111.transitions_from[0].history_role is None
        assert state_l1_l11_l111.transitions_from[0].history_user_guard is None
        assert state_l1_l11_l111.transitions_from[1].from_state == "L111"
        assert state_l1_l11_l111.transitions_from[1].to_state == "__forced_gate_0"
        assert state_l1_l11_l111.transitions_from[1].event == Event(
            name="E1", state_path=("L1", "L11", "L111"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111.transitions_from[1].guard is None
        assert state_l1_l11_l111.transitions_from[1].effects == []
        assert state_l1_l11_l111.transitions_from[1].doc is None
        assert state_l1_l11_l111.transitions_from[1].parent_ref().name == "L11"
        assert state_l1_l11_l111.transitions_from[1].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l111.transitions_from[1].target_history is None
        assert state_l1_l11_l111.transitions_from[1].history_role is None
        assert state_l1_l11_l111.transitions_from[1].history_user_guard is None
        assert state_l1_l11_l111.transitions_from[2].from_state == "L111"
        assert state_l1_l11_l111.transitions_from[2].to_state == "__forced_gate_1"
        assert state_l1_l11_l111.transitions_from[2].event == Event(
            name="E2", state_path=("L1", "L11", "L111"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111.transitions_from[2].guard is None
        assert state_l1_l11_l111.transitions_from[2].effects == []
        assert state_l1_l11_l111.transitions_from[2].doc is None
        assert state_l1_l11_l111.transitions_from[2].parent_ref().name == "L11"
        assert state_l1_l11_l111.transitions_from[2].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l111.transitions_from[2].target_history is None
        assert state_l1_l11_l111.transitions_from[2].history_role is None
        assert state_l1_l11_l111.transitions_from[2].history_user_guard is None
        assert len(state_l1_l11_l111.transitions_to) == 1
        assert state_l1_l11_l111.transitions_to[0].from_state == INIT_STATE
        assert state_l1_l11_l111.transitions_to[0].to_state == "L111"
        assert state_l1_l11_l111.transitions_to[0].event is None
        assert state_l1_l11_l111.transitions_to[0].guard is None
        assert state_l1_l11_l111.transitions_to[0].effects == []
        assert state_l1_l11_l111.transitions_to[0].doc is None
        assert state_l1_l11_l111.transitions_to[0].parent_ref().name == "L11"
        assert state_l1_l11_l111.transitions_to[0].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l111.transitions_to[0].target_history is None
        assert state_l1_l11_l111.transitions_to[0].history_role is None
        assert state_l1_l11_l111.transitions_to[0].history_user_guard is None

    def test_state_l1_l11_l111_to_ast_node(self, state_l1_l11_l111):
        ast_node = state_l1_l11_l111.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L111",
            extra_name=None,
            events=[
                dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None),
                dsl_nodes.EventDefinition(name="E2", extra_name=None, doc=None),
            ],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="L1111",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None),
                        dsl_nodes.EventDefinition(name="E2", extra_name=None, doc=None),
                    ],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="L11111",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(
                                    name="E1", extra_name=None, doc=None
                                ),
                                dsl_nodes.EventDefinition(
                                    name="E2", extra_name=None, doc=None
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
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="L11112",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(
                                    name="E1", extra_name=None, doc=None
                                )
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
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                        dsl_nodes.StateDefinition(
                            name="L11113",
                            extra_name=None,
                            events=[
                                dsl_nodes.EventDefinition(
                                    name="E1", extra_name=None, doc=None
                                )
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
                            doc=None,
                            histories=[],
                            regions=[],
                        ),
                    ],
                    transitions=[
                        dsl_nodes.TransitionDefinition(
                            from_state="L11111",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L11", "E1"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                                )
                            ],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L11112",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L11", "E1"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                                )
                            ],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L11113",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L11", "E1"], is_absolute=True
                            ),
                            condition_expr=None,
                            post_operations=[
                                dsl_nodes.OperationAssignment(
                                    name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                                )
                            ],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="L11111",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L11111",
                            to_state="L11112",
                            event_id=dsl_nodes.ChainID(
                                path=["L11111", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L11111",
                            to_state="L11113",
                            event_id=dsl_nodes.ChainID(
                                path=["L11111", "E2"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L11112",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L11112", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L11113",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L11113", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                            doc=None,
                            target_history=None,
                        ),
                    ],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="L1112",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)
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
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="L1113",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)
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
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="__forced_gate_0",
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
                    is_pseudo=True,
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="__forced_gate_1",
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
                    is_pseudo=True,
                    doc=None,
                    histories=[],
                    regions=[],
                ),
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="L1111",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="__forced_0"),
                        op="==",
                        expr2=dsl_nodes.Integer(raw="1"),
                    ),
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L1112",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L11", "E1"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L1113",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L11", "E1"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="L1111",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L1111",
                    to_state="__forced_gate_0",
                    event_id=dsl_nodes.ChainID(path=["L1111", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L1111",
                    to_state="__forced_gate_1",
                    event_id=dsl_nodes.ChainID(path=["L1111", "E2"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L1112",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L1112", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L1113",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L1113", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="__forced_gate_0",
                    to_state="L1112",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="__forced_0"),
                        op="==",
                        expr2=dsl_nodes.Integer(raw="0"),
                    ),
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="__forced_gate_1",
                    to_state="L1113",
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="__forced_0"),
                        op="==",
                        expr2=dsl_nodes.Integer(raw="0"),
                    ),
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
            ],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l111_list_on_enters(self, state_l1_l11_l111):
        lst = state_l1_l11_l111.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l111.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l11_l111_during_aspects(self, state_l1_l11_l111):
        lst = state_l1_l11_l111.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l111.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l111.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l111.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l111.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_l1_l11_l111_l1111(self, state_l1_l11_l111_l1111):
        assert state_l1_l11_l111_l1111.name == "L1111"
        assert state_l1_l11_l111_l1111.path == ("L1", "L11", "L111", "L1111")
        assert sorted(state_l1_l11_l111_l1111.substates.keys()) == [
            "L11111",
            "L11112",
            "L11113",
        ]
        assert state_l1_l11_l111_l1111.regions == {}
        assert state_l1_l11_l111_l1111.events == {
            "E1": Event(
                name="E1",
                state_path=("L1", "L11", "L111", "L1111"),
                extra_name=None,
                doc=None,
            ),
            "E2": Event(
                name="E2",
                state_path=("L1", "L11", "L111", "L1111"),
                extra_name=None,
                doc=None,
            ),
        }
        assert len(state_l1_l11_l111_l1111.transitions) == 8
        assert state_l1_l11_l111_l1111.transitions[0].from_state == "L11111"
        assert state_l1_l11_l111_l1111.transitions[0].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111.transitions[0].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111_l1111.transitions[0].guard is None
        assert state_l1_l11_l111_l1111.transitions[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111_l1111.transitions[0].doc is None
        assert state_l1_l11_l111_l1111.transitions[0].parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111.transitions[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111.transitions[0].target_history is None
        assert state_l1_l11_l111_l1111.transitions[0].history_role is None
        assert state_l1_l11_l111_l1111.transitions[0].history_user_guard is None
        assert state_l1_l11_l111_l1111.transitions[1].from_state == "L11112"
        assert state_l1_l11_l111_l1111.transitions[1].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111.transitions[1].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111_l1111.transitions[1].guard is None
        assert state_l1_l11_l111_l1111.transitions[1].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111_l1111.transitions[1].doc is None
        assert state_l1_l11_l111_l1111.transitions[1].parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111.transitions[1].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111.transitions[1].target_history is None
        assert state_l1_l11_l111_l1111.transitions[1].history_role is None
        assert state_l1_l11_l111_l1111.transitions[1].history_user_guard is None
        assert state_l1_l11_l111_l1111.transitions[2].from_state == "L11113"
        assert state_l1_l11_l111_l1111.transitions[2].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111.transitions[2].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111_l1111.transitions[2].guard is None
        assert state_l1_l11_l111_l1111.transitions[2].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111_l1111.transitions[2].doc is None
        assert state_l1_l11_l111_l1111.transitions[2].parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111.transitions[2].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111.transitions[2].target_history is None
        assert state_l1_l11_l111_l1111.transitions[2].history_role is None
        assert state_l1_l11_l111_l1111.transitions[2].history_user_guard is None
        assert state_l1_l11_l111_l1111.transitions[3].from_state == INIT_STATE
        assert state_l1_l11_l111_l1111.transitions[3].to_state == "L11111"
        assert state_l1_l11_l111_l1111.transitions[3].event is None
        assert state_l1_l11_l111_l1111.transitions[3].guard is None
        assert state_l1_l11_l111_l1111.transitions[3].effects == []
        assert state_l1_l11_l111_l1111.transitions[3].doc is None
        assert state_l1_l11_l111_l1111.transitions[3].parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111.transitions[3].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111.transitions[3].target_history is None
        assert state_l1_l11_l111_l1111.transitions[3].history_role is None
        assert state_l1_l11_l111_l1111.transitions[3].history_user_guard is None
        assert state_l1_l11_l111_l1111.transitions[4].from_state == "L11111"
        assert state_l1_l11_l111_l1111.transitions[4].to_state == "L11112"
        assert state_l1_l11_l111_l1111.transitions[4].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111", "L11111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111.transitions[4].guard is None
        assert state_l1_l11_l111_l1111.transitions[4].effects == []
        assert state_l1_l11_l111_l1111.transitions[4].doc is None
        assert state_l1_l11_l111_l1111.transitions[4].parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111.transitions[4].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111.transitions[4].target_history is None
        assert state_l1_l11_l111_l1111.transitions[4].history_role is None
        assert state_l1_l11_l111_l1111.transitions[4].history_user_guard is None
        assert state_l1_l11_l111_l1111.transitions[5].from_state == "L11111"
        assert state_l1_l11_l111_l1111.transitions[5].to_state == "L11113"
        assert state_l1_l11_l111_l1111.transitions[5].event == Event(
            name="E2",
            state_path=("L1", "L11", "L111", "L1111", "L11111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111.transitions[5].guard is None
        assert state_l1_l11_l111_l1111.transitions[5].effects == []
        assert state_l1_l11_l111_l1111.transitions[5].doc is None
        assert state_l1_l11_l111_l1111.transitions[5].parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111.transitions[5].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111.transitions[5].target_history is None
        assert state_l1_l11_l111_l1111.transitions[5].history_role is None
        assert state_l1_l11_l111_l1111.transitions[5].history_user_guard is None
        assert state_l1_l11_l111_l1111.transitions[6].from_state == "L11112"
        assert state_l1_l11_l111_l1111.transitions[6].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111.transitions[6].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111", "L11112"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111.transitions[6].guard is None
        assert state_l1_l11_l111_l1111.transitions[6].effects == []
        assert state_l1_l11_l111_l1111.transitions[6].doc is None
        assert state_l1_l11_l111_l1111.transitions[6].parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111.transitions[6].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111.transitions[6].target_history is None
        assert state_l1_l11_l111_l1111.transitions[6].history_role is None
        assert state_l1_l11_l111_l1111.transitions[6].history_user_guard is None
        assert state_l1_l11_l111_l1111.transitions[7].from_state == "L11113"
        assert state_l1_l11_l111_l1111.transitions[7].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111.transitions[7].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111", "L11113"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111.transitions[7].guard is None
        assert state_l1_l11_l111_l1111.transitions[7].effects == []
        assert state_l1_l11_l111_l1111.transitions[7].doc is None
        assert state_l1_l11_l111_l1111.transitions[7].parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111.transitions[7].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111.transitions[7].target_history is None
        assert state_l1_l11_l111_l1111.transitions[7].history_role is None
        assert state_l1_l11_l111_l1111.transitions[7].history_user_guard is None
        assert state_l1_l11_l111_l1111.named_functions == {}
        assert state_l1_l11_l111_l1111.on_enters == []
        assert state_l1_l11_l111_l1111.on_durings == []
        assert state_l1_l11_l111_l1111.on_exits == []
        assert state_l1_l11_l111_l1111.on_during_aspects == []
        assert state_l1_l11_l111_l1111.parent_ref().name == "L111"
        assert state_l1_l11_l111_l1111.parent_ref().path == ("L1", "L11", "L111")
        assert state_l1_l11_l111_l1111.substate_name_to_id == {
            "L11111": 0,
            "L11112": 1,
            "L11113": 2,
        }
        assert state_l1_l11_l111_l1111.extra_name is None
        assert not state_l1_l11_l111_l1111.is_pseudo
        assert state_l1_l11_l111_l1111.doc is None
        assert not state_l1_l11_l111_l1111.is_history_gate
        assert not state_l1_l11_l111_l1111.is_forced_gate
        assert state_l1_l11_l111_l1111.abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1111.abstract_on_durings == []
        assert state_l1_l11_l111_l1111.abstract_on_enters == []
        assert state_l1_l11_l111_l1111.abstract_on_exits == []
        assert len(state_l1_l11_l111_l1111.init_transitions) == 1
        assert state_l1_l11_l111_l1111.init_transitions[0].from_state == INIT_STATE
        assert state_l1_l11_l111_l1111.init_transitions[0].to_state == "L11111"
        assert state_l1_l11_l111_l1111.init_transitions[0].event is None
        assert state_l1_l11_l111_l1111.init_transitions[0].guard is None
        assert state_l1_l11_l111_l1111.init_transitions[0].effects == []
        assert state_l1_l11_l111_l1111.init_transitions[0].doc is None
        assert state_l1_l11_l111_l1111.init_transitions[0].parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111.init_transitions[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111.init_transitions[0].target_history is None
        assert state_l1_l11_l111_l1111.init_transitions[0].history_role is None
        assert state_l1_l11_l111_l1111.init_transitions[0].history_user_guard is None
        assert not state_l1_l11_l111_l1111.is_leaf_state
        assert not state_l1_l11_l111_l1111.is_root_state
        assert not state_l1_l11_l111_l1111.is_stoppable
        assert state_l1_l11_l111_l1111.non_abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1111.non_abstract_on_durings == []
        assert state_l1_l11_l111_l1111.non_abstract_on_enters == []
        assert state_l1_l11_l111_l1111.non_abstract_on_exits == []
        assert state_l1_l11_l111_l1111.parent.name == "L111"
        assert state_l1_l11_l111_l1111.parent.path == ("L1", "L11", "L111")
        assert len(state_l1_l11_l111_l1111.transitions_entering_children) == 1
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children[0].from_state
            == INIT_STATE
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children[0].to_state
            == "L11111"
        )
        assert state_l1_l11_l111_l1111.transitions_entering_children[0].event is None
        assert state_l1_l11_l111_l1111.transitions_entering_children[0].guard is None
        assert state_l1_l11_l111_l1111.transitions_entering_children[0].effects == []
        assert state_l1_l11_l111_l1111.transitions_entering_children[0].doc is None
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children[0].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111.transitions_entering_children[
            0
        ].parent_ref().path == ("L1", "L11", "L111", "L1111")
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children[0].target_history
            is None
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children[0].history_role
            is None
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children[0].history_user_guard
            is None
        )
        assert (
            len(state_l1_l11_l111_l1111.transitions_entering_children_simplified) == 1
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[
                0
            ].from_state
            == INIT_STATE
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[0].to_state
            == "L11111"
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[0].event
            is None
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[0].guard
            is None
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[0].effects
            == []
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[0].doc
            is None
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[0]
            .parent_ref()
            .name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("L1", "L11", "L111", "L1111")
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[
                0
            ].target_history
            is None
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[
                0
            ].history_role
            is None
        )
        assert (
            state_l1_l11_l111_l1111.transitions_entering_children_simplified[
                0
            ].history_user_guard
            is None
        )
        assert len(state_l1_l11_l111_l1111.transitions_from) == 3
        assert state_l1_l11_l111_l1111.transitions_from[0].from_state == "L1111"
        assert state_l1_l11_l111_l1111.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111.transitions_from[0].event is None
        assert state_l1_l11_l111_l1111.transitions_from[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=1)
        )
        assert state_l1_l11_l111_l1111.transitions_from[0].effects == []
        assert state_l1_l11_l111_l1111.transitions_from[0].doc is None
        assert state_l1_l11_l111_l1111.transitions_from[0].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1111.transitions_from[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1111.transitions_from[0].target_history is None
        assert state_l1_l11_l111_l1111.transitions_from[0].history_role is None
        assert state_l1_l11_l111_l1111.transitions_from[0].history_user_guard is None
        assert state_l1_l11_l111_l1111.transitions_from[1].from_state == "L1111"
        assert state_l1_l11_l111_l1111.transitions_from[1].to_state == "__forced_gate_0"
        assert state_l1_l11_l111_l1111.transitions_from[1].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111.transitions_from[1].guard is None
        assert state_l1_l11_l111_l1111.transitions_from[1].effects == []
        assert state_l1_l11_l111_l1111.transitions_from[1].doc is None
        assert state_l1_l11_l111_l1111.transitions_from[1].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1111.transitions_from[1].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1111.transitions_from[1].target_history is None
        assert state_l1_l11_l111_l1111.transitions_from[1].history_role is None
        assert state_l1_l11_l111_l1111.transitions_from[1].history_user_guard is None
        assert state_l1_l11_l111_l1111.transitions_from[2].from_state == "L1111"
        assert state_l1_l11_l111_l1111.transitions_from[2].to_state == "__forced_gate_1"
        assert state_l1_l11_l111_l1111.transitions_from[2].event == Event(
            name="E2",
            state_path=("L1", "L11", "L111", "L1111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111.transitions_from[2].guard is None
        assert state_l1_l11_l111_l1111.transitions_from[2].effects == []
        assert state_l1_l11_l111_l1111.transitions_from[2].doc is None
        assert state_l1_l11_l111_l1111.transitions_from[2].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1111.transitions_from[2].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1111.transitions_from[2].target_history is None
        assert state_l1_l11_l111_l1111.transitions_from[2].history_role is None
        assert state_l1_l11_l111_l1111.transitions_from[2].history_user_guard is None
        assert len(state_l1_l11_l111_l1111.transitions_to) == 1
        assert state_l1_l11_l111_l1111.transitions_to[0].from_state == INIT_STATE
        assert state_l1_l11_l111_l1111.transitions_to[0].to_state == "L1111"
        assert state_l1_l11_l111_l1111.transitions_to[0].event is None
        assert state_l1_l11_l111_l1111.transitions_to[0].guard is None
        assert state_l1_l11_l111_l1111.transitions_to[0].effects == []
        assert state_l1_l11_l111_l1111.transitions_to[0].doc is None
        assert state_l1_l11_l111_l1111.transitions_to[0].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1111.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1111.transitions_to[0].target_history is None
        assert state_l1_l11_l111_l1111.transitions_to[0].history_role is None
        assert state_l1_l11_l111_l1111.transitions_to[0].history_user_guard is None

    def test_state_l1_l11_l111_l1111_to_ast_node(self, state_l1_l11_l111_l1111):
        ast_node = state_l1_l11_l111_l1111.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L1111",
            extra_name=None,
            events=[
                dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None),
                dsl_nodes.EventDefinition(name="E2", extra_name=None, doc=None),
            ],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="L11111",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None),
                        dsl_nodes.EventDefinition(name="E2", extra_name=None, doc=None),
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
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="L11112",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)
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
                    doc=None,
                    histories=[],
                    regions=[],
                ),
                dsl_nodes.StateDefinition(
                    name="L11113",
                    extra_name=None,
                    events=[
                        dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)
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
                    doc=None,
                    histories=[],
                    regions=[],
                ),
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="L11111",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L11", "E1"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L11112",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L11", "E1"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L11113",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L11", "E1"], is_absolute=True),
                    condition_expr=None,
                    post_operations=[
                        dsl_nodes.OperationAssignment(
                            name="__forced_0", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="L11111",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L11111",
                    to_state="L11112",
                    event_id=dsl_nodes.ChainID(
                        path=["L11111", "E1"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L11111",
                    to_state="L11113",
                    event_id=dsl_nodes.ChainID(
                        path=["L11111", "E2"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L11112",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["L11112", "E1"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L11113",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(
                        path=["L11113", "E1"], is_absolute=False
                    ),
                    condition_expr=None,
                    post_operations=[],
                    doc=None,
                    target_history=None,
                ),
            ],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l111_l1111_list_on_enters(self, state_l1_l11_l111_l1111):
        lst = state_l1_l11_l111_l1111.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l11_l111_l1111_during_aspects(self, state_l1_l11_l111_l1111):
        lst = state_l1_l11_l111_l1111.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_l111_l1111_l11111(self, state_l1_l11_l111_l1111_l11111):
        assert state_l1_l11_l111_l1111_l11111.name == "L11111"
        assert state_l1_l11_l111_l1111_l11111.path == (
            "L1",
            "L11",
            "L111",
            "L1111",
            "L11111",
        )
        assert sorted(state_l1_l11_l111_l1111_l11111.substates.keys()) == []
        assert state_l1_l11_l111_l1111_l11111.regions == {}
        assert state_l1_l11_l111_l1111_l11111.events == {
            "E1": Event(
                name="E1",
                state_path=("L1", "L11", "L111", "L1111", "L11111"),
                extra_name=None,
                doc=None,
            ),
            "E2": Event(
                name="E2",
                state_path=("L1", "L11", "L111", "L1111", "L11111"),
                extra_name=None,
                doc=None,
            ),
        }
        assert state_l1_l11_l111_l1111_l11111.transitions == []
        assert state_l1_l11_l111_l1111_l11111.named_functions == {}
        assert state_l1_l11_l111_l1111_l11111.on_enters == []
        assert state_l1_l11_l111_l1111_l11111.on_durings == []
        assert state_l1_l11_l111_l1111_l11111.on_exits == []
        assert state_l1_l11_l111_l1111_l11111.on_during_aspects == []
        assert state_l1_l11_l111_l1111_l11111.parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111_l11111.parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11111.substate_name_to_id == {}
        assert state_l1_l11_l111_l1111_l11111.extra_name is None
        assert not state_l1_l11_l111_l1111_l11111.is_pseudo
        assert state_l1_l11_l111_l1111_l11111.doc is None
        assert not state_l1_l11_l111_l1111_l11111.is_history_gate
        assert not state_l1_l11_l111_l1111_l11111.is_forced_gate
        assert state_l1_l11_l111_l1111_l11111.abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1111_l11111.abstract_on_durings == []
        assert state_l1_l11_l111_l1111_l11111.abstract_on_enters == []
        assert state_l1_l11_l111_l1111_l11111.abstract_on_exits == []
        assert state_l1_l11_l111_l1111_l11111.init_transitions == []
        assert state_l1_l11_l111_l1111_l11111.is_leaf_state
        assert not state_l1_l11_l111_l1111_l11111.is_root_state
        assert state_l1_l11_l111_l1111_l11111.is_stoppable
        assert state_l1_l11_l111_l1111_l11111.non_abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1111_l11111.non_abstract_on_durings == []
        assert state_l1_l11_l111_l1111_l11111.non_abstract_on_enters == []
        assert state_l1_l11_l111_l1111_l11111.non_abstract_on_exits == []
        assert state_l1_l11_l111_l1111_l11111.parent.name == "L1111"
        assert state_l1_l11_l111_l1111_l11111.parent.path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_entering_children == []
        assert (
            len(state_l1_l11_l111_l1111_l11111.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_l1_l11_l111_l1111_l11111.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_l1_l11_l111_l1111_l11111.transitions_from) == 3
        assert state_l1_l11_l111_l1111_l11111.transitions_from[0].from_state == "L11111"
        assert state_l1_l11_l111_l1111_l11111.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111_l11111.transitions_from[0].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[0].guard is None
        assert state_l1_l11_l111_l1111_l11111.transitions_from[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111_l1111_l11111.transitions_from[0].doc is None
        assert (
            state_l1_l11_l111_l1111_l11111.transitions_from[0].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[0].target_history is None
        assert state_l1_l11_l111_l1111_l11111.transitions_from[0].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11111.transitions_from[0].history_user_guard
            is None
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[1].from_state == "L11111"
        assert state_l1_l11_l111_l1111_l11111.transitions_from[1].to_state == "L11112"
        assert state_l1_l11_l111_l1111_l11111.transitions_from[1].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111", "L11111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[1].guard is None
        assert state_l1_l11_l111_l1111_l11111.transitions_from[1].effects == []
        assert state_l1_l11_l111_l1111_l11111.transitions_from[1].doc is None
        assert (
            state_l1_l11_l111_l1111_l11111.transitions_from[1].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[1].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[1].target_history is None
        assert state_l1_l11_l111_l1111_l11111.transitions_from[1].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11111.transitions_from[1].history_user_guard
            is None
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[2].from_state == "L11111"
        assert state_l1_l11_l111_l1111_l11111.transitions_from[2].to_state == "L11113"
        assert state_l1_l11_l111_l1111_l11111.transitions_from[2].event == Event(
            name="E2",
            state_path=("L1", "L11", "L111", "L1111", "L11111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[2].guard is None
        assert state_l1_l11_l111_l1111_l11111.transitions_from[2].effects == []
        assert state_l1_l11_l111_l1111_l11111.transitions_from[2].doc is None
        assert (
            state_l1_l11_l111_l1111_l11111.transitions_from[2].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[2].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_from[2].target_history is None
        assert state_l1_l11_l111_l1111_l11111.transitions_from[2].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11111.transitions_from[2].history_user_guard
            is None
        )
        assert len(state_l1_l11_l111_l1111_l11111.transitions_to) == 1
        assert state_l1_l11_l111_l1111_l11111.transitions_to[0].from_state == INIT_STATE
        assert state_l1_l11_l111_l1111_l11111.transitions_to[0].to_state == "L11111"
        assert state_l1_l11_l111_l1111_l11111.transitions_to[0].event is None
        assert state_l1_l11_l111_l1111_l11111.transitions_to[0].guard is None
        assert state_l1_l11_l111_l1111_l11111.transitions_to[0].effects == []
        assert state_l1_l11_l111_l1111_l11111.transitions_to[0].doc is None
        assert (
            state_l1_l11_l111_l1111_l11111.transitions_to[0].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11111.transitions_to[0].target_history is None
        assert state_l1_l11_l111_l1111_l11111.transitions_to[0].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11111.transitions_to[0].history_user_guard is None
        )

    def test_state_l1_l11_l111_l1111_l11111_to_ast_node(
        self, state_l1_l11_l111_l1111_l11111
    ):
        ast_node = state_l1_l11_l111_l1111_l11111.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L11111",
            extra_name=None,
            events=[
                dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None),
                dsl_nodes.EventDefinition(name="E2", extra_name=None, doc=None),
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
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l111_l1111_l11111_list_on_enters(
        self, state_l1_l11_l111_l1111_l11111
    ):
        lst = state_l1_l11_l111_l1111_l11111.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l111_l1111_l11111_during_aspects(
        self, state_l1_l11_l111_l1111_l11111
    ):
        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_l111_l1111_l11111_during_aspect_recursively(
        self, state_l1_l11_l111_l1111_l11111
    ):
        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11111.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l111_l1111_l11112(self, state_l1_l11_l111_l1111_l11112):
        assert state_l1_l11_l111_l1111_l11112.name == "L11112"
        assert state_l1_l11_l111_l1111_l11112.path == (
            "L1",
            "L11",
            "L111",
            "L1111",
            "L11112",
        )
        assert sorted(state_l1_l11_l111_l1111_l11112.substates.keys()) == []
        assert state_l1_l11_l111_l1111_l11112.regions == {}
        assert state_l1_l11_l111_l1111_l11112.events == {
            "E1": Event(
                name="E1",
                state_path=("L1", "L11", "L111", "L1111", "L11112"),
                extra_name=None,
                doc=None,
            )
        }
        assert state_l1_l11_l111_l1111_l11112.transitions == []
        assert state_l1_l11_l111_l1111_l11112.named_functions == {}
        assert state_l1_l11_l111_l1111_l11112.on_enters == []
        assert state_l1_l11_l111_l1111_l11112.on_durings == []
        assert state_l1_l11_l111_l1111_l11112.on_exits == []
        assert state_l1_l11_l111_l1111_l11112.on_during_aspects == []
        assert state_l1_l11_l111_l1111_l11112.parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111_l11112.parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11112.substate_name_to_id == {}
        assert state_l1_l11_l111_l1111_l11112.extra_name is None
        assert not state_l1_l11_l111_l1111_l11112.is_pseudo
        assert state_l1_l11_l111_l1111_l11112.doc is None
        assert not state_l1_l11_l111_l1111_l11112.is_history_gate
        assert not state_l1_l11_l111_l1111_l11112.is_forced_gate
        assert state_l1_l11_l111_l1111_l11112.abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1111_l11112.abstract_on_durings == []
        assert state_l1_l11_l111_l1111_l11112.abstract_on_enters == []
        assert state_l1_l11_l111_l1111_l11112.abstract_on_exits == []
        assert state_l1_l11_l111_l1111_l11112.init_transitions == []
        assert state_l1_l11_l111_l1111_l11112.is_leaf_state
        assert not state_l1_l11_l111_l1111_l11112.is_root_state
        assert state_l1_l11_l111_l1111_l11112.is_stoppable
        assert state_l1_l11_l111_l1111_l11112.non_abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1111_l11112.non_abstract_on_durings == []
        assert state_l1_l11_l111_l1111_l11112.non_abstract_on_enters == []
        assert state_l1_l11_l111_l1111_l11112.non_abstract_on_exits == []
        assert state_l1_l11_l111_l1111_l11112.parent.name == "L1111"
        assert state_l1_l11_l111_l1111_l11112.parent.path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_entering_children == []
        assert (
            len(state_l1_l11_l111_l1111_l11112.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_l1_l11_l111_l1111_l11112.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_l1_l11_l111_l1111_l11112.transitions_from) == 2
        assert state_l1_l11_l111_l1111_l11112.transitions_from[0].from_state == "L11112"
        assert state_l1_l11_l111_l1111_l11112.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111_l11112.transitions_from[0].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_from[0].guard is None
        assert state_l1_l11_l111_l1111_l11112.transitions_from[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111_l1111_l11112.transitions_from[0].doc is None
        assert (
            state_l1_l11_l111_l1111_l11112.transitions_from[0].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_from[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_from[0].target_history is None
        assert state_l1_l11_l111_l1111_l11112.transitions_from[0].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11112.transitions_from[0].history_user_guard
            is None
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_from[1].from_state == "L11112"
        assert state_l1_l11_l111_l1111_l11112.transitions_from[1].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111_l11112.transitions_from[1].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111", "L11112"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_from[1].guard is None
        assert state_l1_l11_l111_l1111_l11112.transitions_from[1].effects == []
        assert state_l1_l11_l111_l1111_l11112.transitions_from[1].doc is None
        assert (
            state_l1_l11_l111_l1111_l11112.transitions_from[1].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_from[1].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_from[1].target_history is None
        assert state_l1_l11_l111_l1111_l11112.transitions_from[1].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11112.transitions_from[1].history_user_guard
            is None
        )
        assert len(state_l1_l11_l111_l1111_l11112.transitions_to) == 1
        assert state_l1_l11_l111_l1111_l11112.transitions_to[0].from_state == "L11111"
        assert state_l1_l11_l111_l1111_l11112.transitions_to[0].to_state == "L11112"
        assert state_l1_l11_l111_l1111_l11112.transitions_to[0].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111", "L11111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_to[0].guard is None
        assert state_l1_l11_l111_l1111_l11112.transitions_to[0].effects == []
        assert state_l1_l11_l111_l1111_l11112.transitions_to[0].doc is None
        assert (
            state_l1_l11_l111_l1111_l11112.transitions_to[0].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11112.transitions_to[0].target_history is None
        assert state_l1_l11_l111_l1111_l11112.transitions_to[0].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11112.transitions_to[0].history_user_guard is None
        )

    def test_state_l1_l11_l111_l1111_l11112_to_ast_node(
        self, state_l1_l11_l111_l1111_l11112
    ):
        ast_node = state_l1_l11_l111_l1111_l11112.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L11112",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l111_l1111_l11112_list_on_enters(
        self, state_l1_l11_l111_l1111_l11112
    ):
        lst = state_l1_l11_l111_l1111_l11112.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l111_l1111_l11112_during_aspects(
        self, state_l1_l11_l111_l1111_l11112
    ):
        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_l111_l1111_l11112_during_aspect_recursively(
        self, state_l1_l11_l111_l1111_l11112
    ):
        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11112.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l111_l1111_l11113(self, state_l1_l11_l111_l1111_l11113):
        assert state_l1_l11_l111_l1111_l11113.name == "L11113"
        assert state_l1_l11_l111_l1111_l11113.path == (
            "L1",
            "L11",
            "L111",
            "L1111",
            "L11113",
        )
        assert sorted(state_l1_l11_l111_l1111_l11113.substates.keys()) == []
        assert state_l1_l11_l111_l1111_l11113.regions == {}
        assert state_l1_l11_l111_l1111_l11113.events == {
            "E1": Event(
                name="E1",
                state_path=("L1", "L11", "L111", "L1111", "L11113"),
                extra_name=None,
                doc=None,
            )
        }
        assert state_l1_l11_l111_l1111_l11113.transitions == []
        assert state_l1_l11_l111_l1111_l11113.named_functions == {}
        assert state_l1_l11_l111_l1111_l11113.on_enters == []
        assert state_l1_l11_l111_l1111_l11113.on_durings == []
        assert state_l1_l11_l111_l1111_l11113.on_exits == []
        assert state_l1_l11_l111_l1111_l11113.on_during_aspects == []
        assert state_l1_l11_l111_l1111_l11113.parent_ref().name == "L1111"
        assert state_l1_l11_l111_l1111_l11113.parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11113.substate_name_to_id == {}
        assert state_l1_l11_l111_l1111_l11113.extra_name is None
        assert not state_l1_l11_l111_l1111_l11113.is_pseudo
        assert state_l1_l11_l111_l1111_l11113.doc is None
        assert not state_l1_l11_l111_l1111_l11113.is_history_gate
        assert not state_l1_l11_l111_l1111_l11113.is_forced_gate
        assert state_l1_l11_l111_l1111_l11113.abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1111_l11113.abstract_on_durings == []
        assert state_l1_l11_l111_l1111_l11113.abstract_on_enters == []
        assert state_l1_l11_l111_l1111_l11113.abstract_on_exits == []
        assert state_l1_l11_l111_l1111_l11113.init_transitions == []
        assert state_l1_l11_l111_l1111_l11113.is_leaf_state
        assert not state_l1_l11_l111_l1111_l11113.is_root_state
        assert state_l1_l11_l111_l1111_l11113.is_stoppable
        assert state_l1_l11_l111_l1111_l11113.non_abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1111_l11113.non_abstract_on_durings == []
        assert state_l1_l11_l111_l1111_l11113.non_abstract_on_enters == []
        assert state_l1_l11_l111_l1111_l11113.non_abstract_on_exits == []
        assert state_l1_l11_l111_l1111_l11113.parent.name == "L1111"
        assert state_l1_l11_l111_l1111_l11113.parent.path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_entering_children == []
        assert (
            len(state_l1_l11_l111_l1111_l11113.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_l1_l11_l111_l1111_l11113.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_l1_l11_l111_l1111_l11113.transitions_from) == 2
        assert state_l1_l11_l111_l1111_l11113.transitions_from[0].from_state == "L11113"
        assert state_l1_l11_l111_l1111_l11113.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111_l11113.transitions_from[0].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_from[0].guard is None
        assert state_l1_l11_l111_l1111_l11113.transitions_from[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111_l1111_l11113.transitions_from[0].doc is None
        assert (
            state_l1_l11_l111_l1111_l11113.transitions_from[0].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_from[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_from[0].target_history is None
        assert state_l1_l11_l111_l1111_l11113.transitions_from[0].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11113.transitions_from[0].history_user_guard
            is None
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_from[1].from_state == "L11113"
        assert state_l1_l11_l111_l1111_l11113.transitions_from[1].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1111_l11113.transitions_from[1].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111", "L11113"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_from[1].guard is None
        assert state_l1_l11_l111_l1111_l11113.transitions_from[1].effects == []
        assert state_l1_l11_l111_l1111_l11113.transitions_from[1].doc is None
        assert (
            state_l1_l11_l111_l1111_l11113.transitions_from[1].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_from[1].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_from[1].target_history is None
        assert state_l1_l11_l111_l1111_l11113.transitions_from[1].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11113.transitions_from[1].history_user_guard
            is None
        )
        assert len(state_l1_l11_l111_l1111_l11113.transitions_to) == 1
        assert state_l1_l11_l111_l1111_l11113.transitions_to[0].from_state == "L11111"
        assert state_l1_l11_l111_l1111_l11113.transitions_to[0].to_state == "L11113"
        assert state_l1_l11_l111_l1111_l11113.transitions_to[0].event == Event(
            name="E2",
            state_path=("L1", "L11", "L111", "L1111", "L11111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_to[0].guard is None
        assert state_l1_l11_l111_l1111_l11113.transitions_to[0].effects == []
        assert state_l1_l11_l111_l1111_l11113.transitions_to[0].doc is None
        assert (
            state_l1_l11_l111_l1111_l11113.transitions_to[0].parent_ref().name
            == "L1111"
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
            "L1111",
        )
        assert state_l1_l11_l111_l1111_l11113.transitions_to[0].target_history is None
        assert state_l1_l11_l111_l1111_l11113.transitions_to[0].history_role is None
        assert (
            state_l1_l11_l111_l1111_l11113.transitions_to[0].history_user_guard is None
        )

    def test_state_l1_l11_l111_l1111_l11113_to_ast_node(
        self, state_l1_l11_l111_l1111_l11113
    ):
        ast_node = state_l1_l11_l111_l1111_l11113.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L11113",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l111_l1111_l11113_list_on_enters(
        self, state_l1_l11_l111_l1111_l11113
    ):
        lst = state_l1_l11_l111_l1111_l11113.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l111_l1111_l11113_during_aspects(
        self, state_l1_l11_l111_l1111_l11113
    ):
        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_l111_l1111_l11113_during_aspect_recursively(
        self, state_l1_l11_l111_l1111_l11113
    ):
        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_l111_l1111_l11113.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l111_l1112(self, state_l1_l11_l111_l1112):
        assert state_l1_l11_l111_l1112.name == "L1112"
        assert state_l1_l11_l111_l1112.path == ("L1", "L11", "L111", "L1112")
        assert sorted(state_l1_l11_l111_l1112.substates.keys()) == []
        assert state_l1_l11_l111_l1112.regions == {}
        assert state_l1_l11_l111_l1112.events == {
            "E1": Event(
                name="E1",
                state_path=("L1", "L11", "L111", "L1112"),
                extra_name=None,
                doc=None,
            )
        }
        assert state_l1_l11_l111_l1112.transitions == []
        assert state_l1_l11_l111_l1112.named_functions == {}
        assert state_l1_l11_l111_l1112.on_enters == []
        assert state_l1_l11_l111_l1112.on_durings == []
        assert state_l1_l11_l111_l1112.on_exits == []
        assert state_l1_l11_l111_l1112.on_during_aspects == []
        assert state_l1_l11_l111_l1112.parent_ref().name == "L111"
        assert state_l1_l11_l111_l1112.parent_ref().path == ("L1", "L11", "L111")
        assert state_l1_l11_l111_l1112.substate_name_to_id == {}
        assert state_l1_l11_l111_l1112.extra_name is None
        assert not state_l1_l11_l111_l1112.is_pseudo
        assert state_l1_l11_l111_l1112.doc is None
        assert not state_l1_l11_l111_l1112.is_history_gate
        assert not state_l1_l11_l111_l1112.is_forced_gate
        assert state_l1_l11_l111_l1112.abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1112.abstract_on_durings == []
        assert state_l1_l11_l111_l1112.abstract_on_enters == []
        assert state_l1_l11_l111_l1112.abstract_on_exits == []
        assert state_l1_l11_l111_l1112.init_transitions == []
        assert state_l1_l11_l111_l1112.is_leaf_state
        assert not state_l1_l11_l111_l1112.is_root_state
        assert state_l1_l11_l111_l1112.is_stoppable
        assert state_l1_l11_l111_l1112.non_abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1112.non_abstract_on_durings == []
        assert state_l1_l11_l111_l1112.non_abstract_on_enters == []
        assert state_l1_l11_l111_l1112.non_abstract_on_exits == []
        assert state_l1_l11_l111_l1112.parent.name == "L111"
        assert state_l1_l11_l111_l1112.parent.path == ("L1", "L11", "L111")
        assert state_l1_l11_l111_l1112.transitions_entering_children == []
        assert (
            len(state_l1_l11_l111_l1112.transitions_entering_children_simplified) == 1
        )
        assert (
            state_l1_l11_l111_l1112.transitions_entering_children_simplified[0] is None
        )
        assert len(state_l1_l11_l111_l1112.transitions_from) == 2
        assert state_l1_l11_l111_l1112.transitions_from[0].from_state == "L1112"
        assert state_l1_l11_l111_l1112.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1112.transitions_from[0].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111_l1112.transitions_from[0].guard is None
        assert state_l1_l11_l111_l1112.transitions_from[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111_l1112.transitions_from[0].doc is None
        assert state_l1_l11_l111_l1112.transitions_from[0].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1112.transitions_from[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1112.transitions_from[0].target_history is None
        assert state_l1_l11_l111_l1112.transitions_from[0].history_role is None
        assert state_l1_l11_l111_l1112.transitions_from[0].history_user_guard is None
        assert state_l1_l11_l111_l1112.transitions_from[1].from_state == "L1112"
        assert state_l1_l11_l111_l1112.transitions_from[1].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1112.transitions_from[1].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1112"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1112.transitions_from[1].guard is None
        assert state_l1_l11_l111_l1112.transitions_from[1].effects == []
        assert state_l1_l11_l111_l1112.transitions_from[1].doc is None
        assert state_l1_l11_l111_l1112.transitions_from[1].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1112.transitions_from[1].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1112.transitions_from[1].target_history is None
        assert state_l1_l11_l111_l1112.transitions_from[1].history_role is None
        assert state_l1_l11_l111_l1112.transitions_from[1].history_user_guard is None
        assert len(state_l1_l11_l111_l1112.transitions_to) == 1
        assert state_l1_l11_l111_l1112.transitions_to[0].from_state == "__forced_gate_0"
        assert state_l1_l11_l111_l1112.transitions_to[0].to_state == "L1112"
        assert state_l1_l11_l111_l1112.transitions_to[0].event is None
        assert state_l1_l11_l111_l1112.transitions_to[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_l111_l1112.transitions_to[0].effects == []
        assert state_l1_l11_l111_l1112.transitions_to[0].doc is None
        assert state_l1_l11_l111_l1112.transitions_to[0].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1112.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1112.transitions_to[0].target_history is None
        assert state_l1_l11_l111_l1112.transitions_to[0].history_role is None
        assert state_l1_l11_l111_l1112.transitions_to[0].history_user_guard is None

    def test_state_l1_l11_l111_l1112_to_ast_node(self, state_l1_l11_l111_l1112):
        ast_node = state_l1_l11_l111_l1112.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L1112",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l111_l1112_list_on_enters(self, state_l1_l11_l111_l1112):
        lst = state_l1_l11_l111_l1112.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l11_l111_l1112_during_aspects(self, state_l1_l11_l111_l1112):
        lst = state_l1_l11_l111_l1112.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_l111_l1112_during_aspect_recursively(
        self, state_l1_l11_l111_l1112
    ):
        lst = state_l1_l11_l111_l1112.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_l111_l1112.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_l1_l11_l111_l1113(self, state_l1_l11_l111_l1113):
        assert state_l1_l11_l111_l1113.name == "L1113"
        assert state_l1_l11_l111_l1113.path == ("L1", "L11", "L111", "L1113")
        assert sorted(state_l1_l11_l111_l1113.substates.keys()) == []
        assert state_l1_l11_l111_l1113.regions == {}
        assert state_l1_l11_l111_l1113.events == {
            "E1": Event(
                name="E1",
                state_path=("L1", "L11", "L111", "L1113"),
                extra_name=None,
                doc=None,
            )
        }
        assert state_l1_l11_l111_l1113.transitions == []
        assert state_l1_l11_l111_l1113.named_functions == {}
        assert state_l1_l11_l111_l1113.on_enters == []
        assert state_l1_l11_l111_l1113.on_durings == []
        assert state_l1_l11_l111_l1113.on_exits == []
        assert state_l1_l11_l111_l1113.on_during_aspects == []
        assert state_l1_l11_l111_l1113.parent_ref().name == "L111"
        assert state_l1_l11_l111_l1113.parent_ref().path == ("L1", "L11", "L111")
        assert state_l1_l11_l111_l1113.substate_name_to_id == {}
        assert state_l1_l11_l111_l1113.extra_name is None
        assert not state_l1_l11_l111_l1113.is_pseudo
        assert state_l1_l11_l111_l1113.doc is None
        assert not state_l1_l11_l111_l1113.is_history_gate
        assert not state_l1_l11_l111_l1113.is_forced_gate
        assert state_l1_l11_l111_l1113.abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1113.abstract_on_durings == []
        assert state_l1_l11_l111_l1113.abstract_on_enters == []
        assert state_l1_l11_l111_l1113.abstract_on_exits == []
        assert state_l1_l11_l111_l1113.init_transitions == []
        assert state_l1_l11_l111_l1113.is_leaf_state
        assert not state_l1_l11_l111_l1113.is_root_state
        assert state_l1_l11_l111_l1113.is_stoppable
        assert state_l1_l11_l111_l1113.non_abstract_on_during_aspects == []
        assert state_l1_l11_l111_l1113.non_abstract_on_durings == []
        assert state_l1_l11_l111_l1113.non_abstract_on_enters == []
        assert state_l1_l11_l111_l1113.non_abstract_on_exits == []
        assert state_l1_l11_l111_l1113.parent.name == "L111"
        assert state_l1_l11_l111_l1113.parent.path == ("L1", "L11", "L111")
        assert state_l1_l11_l111_l1113.transitions_entering_children == []
        assert (
            len(state_l1_l11_l111_l1113.transitions_entering_children_simplified) == 1
        )
        assert (
            state_l1_l11_l111_l1113.transitions_entering_children_simplified[0] is None
        )
        assert len(state_l1_l11_l111_l1113.transitions_from) == 2
        assert state_l1_l11_l111_l1113.transitions_from[0].from_state == "L1113"
        assert state_l1_l11_l111_l1113.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1113.transitions_from[0].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l111_l1113.transitions_from[0].guard is None
        assert state_l1_l11_l111_l1113.transitions_from[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l111_l1113.transitions_from[0].doc is None
        assert state_l1_l11_l111_l1113.transitions_from[0].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1113.transitions_from[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1113.transitions_from[0].target_history is None
        assert state_l1_l11_l111_l1113.transitions_from[0].history_role is None
        assert state_l1_l11_l111_l1113.transitions_from[0].history_user_guard is None
        assert state_l1_l11_l111_l1113.transitions_from[1].from_state == "L1113"
        assert state_l1_l11_l111_l1113.transitions_from[1].to_state == EXIT_STATE
        assert state_l1_l11_l111_l1113.transitions_from[1].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1113"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_l1113.transitions_from[1].guard is None
        assert state_l1_l11_l111_l1113.transitions_from[1].effects == []
        assert state_l1_l11_l111_l1113.transitions_from[1].doc is None
        assert state_l1_l11_l111_l1113.transitions_from[1].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1113.transitions_from[1].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1113.transitions_from[1].target_history is None
        assert state_l1_l11_l111_l1113.transitions_from[1].history_role is None
        assert state_l1_l11_l111_l1113.transitions_from[1].history_user_guard is None
        assert len(state_l1_l11_l111_l1113.transitions_to) == 1
        assert state_l1_l11_l111_l1113.transitions_to[0].from_state == "__forced_gate_1"
        assert state_l1_l11_l111_l1113.transitions_to[0].to_state == "L1113"
        assert state_l1_l11_l111_l1113.transitions_to[0].event is None
        assert state_l1_l11_l111_l1113.transitions_to[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_l111_l1113.transitions_to[0].effects == []
        assert state_l1_l11_l111_l1113.transitions_to[0].doc is None
        assert state_l1_l11_l111_l1113.transitions_to[0].parent_ref().name == "L111"
        assert state_l1_l11_l111_l1113.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_l1113.transitions_to[0].target_history is None
        assert state_l1_l11_l111_l1113.transitions_to[0].history_role is None
        assert state_l1_l11_l111_l1113.transitions_to[0].history_user_guard is None

    def test_state_l1_l11_l111_l1113_to_ast_node(self, state_l1_l11_l111_l1113):
        ast_node = state_l1_l11_l111_l1113.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L1113",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l111_l1113_list_on_enters(self, state_l1_l11_l111_l1113):
        lst = state_l1_l11_l111_l1113.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l11_l111_l1113_during_aspects(self, state_l1_l11_l111_l1113):
        lst = state_l1_l11_l111_l1113.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_l111_l1113_during_aspect_recursively(
        self, state_l1_l11_l111_l1113
    ):
        lst = state_l1_l11_l111_l1113.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_l111_l1113.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_l1_l11_l111_forced_gate_0(self, state_l1_l11_l111_forced_gate_0):
        assert state_l1_l11_l111_forced_gate_0.name == "__forced_gate_0"
        assert state_l1_l11_l111_forced_gate_0.path == (
            "L1",
            "L11",
            "L111",
            "__forced_gate_0",
        )
        assert sorted(state_l1_l11_l111_forced_gate_0.substates.keys()) == []
        assert state_l1_l11_l111_forced_gate_0.regions == {}
        assert state_l1_l11_l111_forced_gate_0.events == {}
        assert state_l1_l11_l111_forced_gate_0.transitions == []
        assert state_l1_l11_l111_forced_gate_0.named_functions == {}
        assert state_l1_l11_l111_forced_gate_0.on_enters == []
        assert state_l1_l11_l111_forced_gate_0.on_durings == []
        assert state_l1_l11_l111_forced_gate_0.on_exits == []
        assert state_l1_l11_l111_forced_gate_0.on_during_aspects == []
        assert state_l1_l11_l111_forced_gate_0.parent_ref().name == "L111"
        assert state_l1_l11_l111_forced_gate_0.parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_forced_gate_0.substate_name_to_id == {}
        assert state_l1_l11_l111_forced_gate_0.extra_name is None
        assert state_l1_l11_l111_forced_gate_0.is_pseudo
        assert state_l1_l11_l111_forced_gate_0.doc is None
        assert not state_l1_l11_l111_forced_gate_0.is_history_gate
        assert state_l1_l11_l111_forced_gate_0.is_forced_gate
        assert state_l1_l11_l111_forced_gate_0.abstract_on_during_aspects == []
        assert state_l1_l11_l111_forced_gate_0.abstract_on_durings == []
        assert state_l1_l11_l111_forced_gate_0.abstract_on_enters == []
        assert state_l1_l11_l111_forced_gate_0.abstract_on_exits == []
        assert state_l1_l11_l111_forced_gate_0.init_transitions == []
        assert state_l1_l11_l111_forced_gate_0.is_leaf_state
        assert not state_l1_l11_l111_forced_gate_0.is_root_state
        assert not state_l1_l11_l111_forced_gate_0.is_stoppable
        assert state_l1_l11_l111_forced_gate_0.non_abstract_on_during_aspects == []
        assert state_l1_l11_l111_forced_gate_0.non_abstract_on_durings == []
        assert state_l1_l11_l111_forced_gate_0.non_abstract_on_enters == []
        assert state_l1_l11_l111_forced_gate_0.non_abstract_on_exits == []
        assert state_l1_l11_l111_forced_gate_0.parent.name == "L111"
        assert state_l1_l11_l111_forced_gate_0.parent.path == ("L1", "L11", "L111")
        assert state_l1_l11_l111_forced_gate_0.transitions_entering_children == []
        assert (
            len(
                state_l1_l11_l111_forced_gate_0.transitions_entering_children_simplified
            )
            == 1
        )
        assert (
            state_l1_l11_l111_forced_gate_0.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_l1_l11_l111_forced_gate_0.transitions_from) == 1
        assert (
            state_l1_l11_l111_forced_gate_0.transitions_from[0].from_state
            == "__forced_gate_0"
        )
        assert state_l1_l11_l111_forced_gate_0.transitions_from[0].to_state == "L1112"
        assert state_l1_l11_l111_forced_gate_0.transitions_from[0].event is None
        assert state_l1_l11_l111_forced_gate_0.transitions_from[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_l111_forced_gate_0.transitions_from[0].effects == []
        assert state_l1_l11_l111_forced_gate_0.transitions_from[0].doc is None
        assert (
            state_l1_l11_l111_forced_gate_0.transitions_from[0].parent_ref().name
            == "L111"
        )
        assert state_l1_l11_l111_forced_gate_0.transitions_from[
            0
        ].parent_ref().path == ("L1", "L11", "L111")
        assert (
            state_l1_l11_l111_forced_gate_0.transitions_from[0].target_history is None
        )
        assert state_l1_l11_l111_forced_gate_0.transitions_from[0].history_role is None
        assert (
            state_l1_l11_l111_forced_gate_0.transitions_from[0].history_user_guard
            is None
        )
        assert len(state_l1_l11_l111_forced_gate_0.transitions_to) == 1
        assert state_l1_l11_l111_forced_gate_0.transitions_to[0].from_state == "L1111"
        assert (
            state_l1_l11_l111_forced_gate_0.transitions_to[0].to_state
            == "__forced_gate_0"
        )
        assert state_l1_l11_l111_forced_gate_0.transitions_to[0].event == Event(
            name="E1",
            state_path=("L1", "L11", "L111", "L1111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_forced_gate_0.transitions_to[0].guard is None
        assert state_l1_l11_l111_forced_gate_0.transitions_to[0].effects == []
        assert state_l1_l11_l111_forced_gate_0.transitions_to[0].doc is None
        assert (
            state_l1_l11_l111_forced_gate_0.transitions_to[0].parent_ref().name
            == "L111"
        )
        assert state_l1_l11_l111_forced_gate_0.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_forced_gate_0.transitions_to[0].target_history is None
        assert state_l1_l11_l111_forced_gate_0.transitions_to[0].history_role is None
        assert (
            state_l1_l11_l111_forced_gate_0.transitions_to[0].history_user_guard is None
        )

    def test_state_l1_l11_l111_forced_gate_0_to_ast_node(
        self, state_l1_l11_l111_forced_gate_0
    ):
        ast_node = state_l1_l11_l111_forced_gate_0.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="__forced_gate_0",
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
            is_pseudo=True,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l111_forced_gate_0_list_on_enters(
        self, state_l1_l11_l111_forced_gate_0
    ):
        lst = state_l1_l11_l111_forced_gate_0.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l111_forced_gate_0_during_aspects(
        self, state_l1_l11_l111_forced_gate_0
    ):
        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_l111_forced_gate_0_during_aspect_recursively(
        self, state_l1_l11_l111_forced_gate_0
    ):
        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_0.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l111_forced_gate_1(self, state_l1_l11_l111_forced_gate_1):
        assert state_l1_l11_l111_forced_gate_1.name == "__forced_gate_1"
        assert state_l1_l11_l111_forced_gate_1.path == (
            "L1",
            "L11",
            "L111",
            "__forced_gate_1",
        )
        assert sorted(state_l1_l11_l111_forced_gate_1.substates.keys()) == []
        assert state_l1_l11_l111_forced_gate_1.regions == {}
        assert state_l1_l11_l111_forced_gate_1.events == {}
        assert state_l1_l11_l111_forced_gate_1.transitions == []
        assert state_l1_l11_l111_forced_gate_1.named_functions == {}
        assert state_l1_l11_l111_forced_gate_1.on_enters == []
        assert state_l1_l11_l111_forced_gate_1.on_durings == []
        assert state_l1_l11_l111_forced_gate_1.on_exits == []
        assert state_l1_l11_l111_forced_gate_1.on_during_aspects == []
        assert state_l1_l11_l111_forced_gate_1.parent_ref().name == "L111"
        assert state_l1_l11_l111_forced_gate_1.parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_forced_gate_1.substate_name_to_id == {}
        assert state_l1_l11_l111_forced_gate_1.extra_name is None
        assert state_l1_l11_l111_forced_gate_1.is_pseudo
        assert state_l1_l11_l111_forced_gate_1.doc is None
        assert not state_l1_l11_l111_forced_gate_1.is_history_gate
        assert state_l1_l11_l111_forced_gate_1.is_forced_gate
        assert state_l1_l11_l111_forced_gate_1.abstract_on_during_aspects == []
        assert state_l1_l11_l111_forced_gate_1.abstract_on_durings == []
        assert state_l1_l11_l111_forced_gate_1.abstract_on_enters == []
        assert state_l1_l11_l111_forced_gate_1.abstract_on_exits == []
        assert state_l1_l11_l111_forced_gate_1.init_transitions == []
        assert state_l1_l11_l111_forced_gate_1.is_leaf_state
        assert not state_l1_l11_l111_forced_gate_1.is_root_state
        assert not state_l1_l11_l111_forced_gate_1.is_stoppable
        assert state_l1_l11_l111_forced_gate_1.non_abstract_on_during_aspects == []
        assert state_l1_l11_l111_forced_gate_1.non_abstract_on_durings == []
        assert state_l1_l11_l111_forced_gate_1.non_abstract_on_enters == []
        assert state_l1_l11_l111_forced_gate_1.non_abstract_on_exits == []
        assert state_l1_l11_l111_forced_gate_1.parent.name == "L111"
        assert state_l1_l11_l111_forced_gate_1.parent.path == ("L1", "L11", "L111")
        assert state_l1_l11_l111_forced_gate_1.transitions_entering_children == []
        assert (
            len(
                state_l1_l11_l111_forced_gate_1.transitions_entering_children_simplified
            )
            == 1
        )
        assert (
            state_l1_l11_l111_forced_gate_1.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_l1_l11_l111_forced_gate_1.transitions_from) == 1
        assert (
            state_l1_l11_l111_forced_gate_1.transitions_from[0].from_state
            == "__forced_gate_1"
        )
        assert state_l1_l11_l111_forced_gate_1.transitions_from[0].to_state == "L1113"
        assert state_l1_l11_l111_forced_gate_1.transitions_from[0].event is None
        assert state_l1_l11_l111_forced_gate_1.transitions_from[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_l111_forced_gate_1.transitions_from[0].effects == []
        assert state_l1_l11_l111_forced_gate_1.transitions_from[0].doc is None
        assert (
            state_l1_l11_l111_forced_gate_1.transitions_from[0].parent_ref().name
            == "L111"
        )
        assert state_l1_l11_l111_forced_gate_1.transitions_from[
            0
        ].parent_ref().path == ("L1", "L11", "L111")
        assert (
            state_l1_l11_l111_forced_gate_1.transitions_from[0].target_history is None
        )
        assert state_l1_l11_l111_forced_gate_1.transitions_from[0].history_role is None
        assert (
            state_l1_l11_l111_forced_gate_1.transitions_from[0].history_user_guard
            is None
        )
        assert len(state_l1_l11_l111_forced_gate_1.transitions_to) == 1
        assert state_l1_l11_l111_forced_gate_1.transitions_to[0].from_state == "L1111"
        assert (
            state_l1_l11_l111_forced_gate_1.transitions_to[0].to_state
            == "__forced_gate_1"
        )
        assert state_l1_l11_l111_forced_gate_1.transitions_to[0].event == Event(
            name="E2",
            state_path=("L1", "L11", "L111", "L1111"),
            extra_name=None,
            doc=None,
        )
        assert state_l1_l11_l111_forced_gate_1.transitions_to[0].guard is None
        assert state_l1_l11_l111_forced_gate_1.transitions_to[0].effects == []
        assert state_l1_l11_l111_forced_gate_1.transitions_to[0].doc is None
        assert (
            state_l1_l11_l111_forced_gate_1.transitions_to[0].parent_ref().name
            == "L111"
        )
        assert state_l1_l11_l111_forced_gate_1.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
            "L111",
        )
        assert state_l1_l11_l111_forced_gate_1.transitions_to[0].target_history is None
        assert state_l1_l11_l111_forced_gate_1.transitions_to[0].history_role is None
        assert (
            state_l1_l11_l111_forced_gate_1.transitions_to[0].history_user_guard is None
        )

    def test_state_l1_l11_l111_forced_gate_1_to_ast_node(
        self, state_l1_l11_l111_forced_gate_1
    ):
        ast_node = state_l1_l11_l111_forced_gate_1.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="__forced_gate_1",
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
            is_pseudo=True,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l111_forced_gate_1_list_on_enters(
        self, state_l1_l11_l111_forced_gate_1
    ):
        lst = state_l1_l11_l111_forced_gate_1.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_enters(
            is_abstract=True, with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l111_forced_gate_1_during_aspects(
        self, state_l1_l11_l111_forced_gate_1
    ):
        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_l111_forced_gate_1_during_aspect_recursively(
        self, state_l1_l11_l111_forced_gate_1
    ):
        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_l111_forced_gate_1.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_l112(self, state_l1_l11_l112):
        assert state_l1_l11_l112.name == "L112"
        assert state_l1_l11_l112.path == ("L1", "L11", "L112")
        assert sorted(state_l1_l11_l112.substates.keys()) == []
        assert state_l1_l11_l112.regions == {}
        assert state_l1_l11_l112.events == {
            "E1": Event(
                name="E1", state_path=("L1", "L11", "L112"), extra_name=None, doc=None
            )
        }
        assert state_l1_l11_l112.transitions == []
        assert state_l1_l11_l112.named_functions == {}
        assert state_l1_l11_l112.on_enters == []
        assert state_l1_l11_l112.on_durings == []
        assert state_l1_l11_l112.on_exits == []
        assert state_l1_l11_l112.on_during_aspects == []
        assert state_l1_l11_l112.parent_ref().name == "L11"
        assert state_l1_l11_l112.parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l112.substate_name_to_id == {}
        assert state_l1_l11_l112.extra_name is None
        assert not state_l1_l11_l112.is_pseudo
        assert state_l1_l11_l112.doc is None
        assert not state_l1_l11_l112.is_history_gate
        assert not state_l1_l11_l112.is_forced_gate
        assert state_l1_l11_l112.abstract_on_during_aspects == []
        assert state_l1_l11_l112.abstract_on_durings == []
        assert state_l1_l11_l112.abstract_on_enters == []
        assert state_l1_l11_l112.abstract_on_exits == []
        assert state_l1_l11_l112.init_transitions == []
        assert state_l1_l11_l112.is_leaf_state
        assert not state_l1_l11_l112.is_root_state
        assert state_l1_l11_l112.is_stoppable
        assert state_l1_l11_l112.non_abstract_on_during_aspects == []
        assert state_l1_l11_l112.non_abstract_on_durings == []
        assert state_l1_l11_l112.non_abstract_on_enters == []
        assert state_l1_l11_l112.non_abstract_on_exits == []
        assert state_l1_l11_l112.parent.name == "L11"
        assert state_l1_l11_l112.parent.path == ("L1", "L11")
        assert state_l1_l11_l112.transitions_entering_children == []
        assert len(state_l1_l11_l112.transitions_entering_children_simplified) == 1
        assert state_l1_l11_l112.transitions_entering_children_simplified[0] is None
        assert len(state_l1_l11_l112.transitions_from) == 2
        assert state_l1_l11_l112.transitions_from[0].from_state == "L112"
        assert state_l1_l11_l112.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11_l112.transitions_from[0].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l112.transitions_from[0].guard is None
        assert state_l1_l11_l112.transitions_from[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l112.transitions_from[0].doc is None
        assert state_l1_l11_l112.transitions_from[0].parent_ref().name == "L11"
        assert state_l1_l11_l112.transitions_from[0].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l112.transitions_from[0].target_history is None
        assert state_l1_l11_l112.transitions_from[0].history_role is None
        assert state_l1_l11_l112.transitions_from[0].history_user_guard is None
        assert state_l1_l11_l112.transitions_from[1].from_state == "L112"
        assert state_l1_l11_l112.transitions_from[1].to_state == EXIT_STATE
        assert state_l1_l11_l112.transitions_from[1].event == Event(
            name="E1", state_path=("L1", "L11", "L112"), extra_name=None, doc=None
        )
        assert state_l1_l11_l112.transitions_from[1].guard is None
        assert state_l1_l11_l112.transitions_from[1].effects == []
        assert state_l1_l11_l112.transitions_from[1].doc is None
        assert state_l1_l11_l112.transitions_from[1].parent_ref().name == "L11"
        assert state_l1_l11_l112.transitions_from[1].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l112.transitions_from[1].target_history is None
        assert state_l1_l11_l112.transitions_from[1].history_role is None
        assert state_l1_l11_l112.transitions_from[1].history_user_guard is None
        assert len(state_l1_l11_l112.transitions_to) == 1
        assert state_l1_l11_l112.transitions_to[0].from_state == "__forced_gate_0"
        assert state_l1_l11_l112.transitions_to[0].to_state == "L112"
        assert state_l1_l11_l112.transitions_to[0].event is None
        assert state_l1_l11_l112.transitions_to[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_l112.transitions_to[0].effects == []
        assert state_l1_l11_l112.transitions_to[0].doc is None
        assert state_l1_l11_l112.transitions_to[0].parent_ref().name == "L11"
        assert state_l1_l11_l112.transitions_to[0].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l112.transitions_to[0].target_history is None
        assert state_l1_l11_l112.transitions_to[0].history_role is None
        assert state_l1_l11_l112.transitions_to[0].history_user_guard is None

    def test_state_l1_l11_l112_to_ast_node(self, state_l1_l11_l112):
        ast_node = state_l1_l11_l112.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L112",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l112_list_on_enters(self, state_l1_l11_l112):
        lst = state_l1_l11_l112.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l112.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l112.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l112.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l112.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l112.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1_l11_l112.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l112.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l112.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l11_l112_during_aspects(self, state_l1_l11_l112):
        lst = state_l1_l11_l112.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l112.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l112.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l112.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l112.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l112.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l112.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l112.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l112.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_l1_l11_l112_during_aspect_recursively(self, state_l1_l11_l112):
        lst = state_l1_l11_l112.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_l112.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_l1_l11_l113(self, state_l1_l11_l113):
        assert state_l1_l11_l113.name == "L113"
        assert state_l1_l11_l113.path == ("L1", "L11", "L113")
        assert sorted(state_l1_l11_l113.substates.keys()) == []
        assert state_l1_l11_l113.regions == {}
        assert state_l1_l11_l113.events == {
            "E1": Event(
                name="E1", state_path=("L1", "L11", "L113"), extra_name=None, doc=None
            )
        }
        assert state_l1_l11_l113.transitions == []
        assert state_l1_l11_l113.named_functions == {}
        assert state_l1_l11_l113.on_enters == []
        assert state_l1_l11_l113.on_durings == []
        assert state_l1_l11_l113.on_exits == []
        assert state_l1_l11_l113.on_during_aspects == []
        assert state_l1_l11_l113.parent_ref().name == "L11"
        assert state_l1_l11_l113.parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l113.substate_name_to_id == {}
        assert state_l1_l11_l113.extra_name is None
        assert not state_l1_l11_l113.is_pseudo
        assert state_l1_l11_l113.doc is None
        assert not state_l1_l11_l113.is_history_gate
        assert not state_l1_l11_l113.is_forced_gate
        assert state_l1_l11_l113.abstract_on_during_aspects == []
        assert state_l1_l11_l113.abstract_on_durings == []
        assert state_l1_l11_l113.abstract_on_enters == []
        assert state_l1_l11_l113.abstract_on_exits == []
        assert state_l1_l11_l113.init_transitions == []
        assert state_l1_l11_l113.is_leaf_state
        assert not state_l1_l11_l113.is_root_state
        assert state_l1_l11_l113.is_stoppable
        assert state_l1_l11_l113.non_abstract_on_during_aspects == []
        assert state_l1_l11_l113.non_abstract_on_durings == []
        assert state_l1_l11_l113.non_abstract_on_enters == []
        assert state_l1_l11_l113.non_abstract_on_exits == []
        assert state_l1_l11_l113.parent.name == "L11"
        assert state_l1_l11_l113.parent.path == ("L1", "L11")
        assert state_l1_l11_l113.transitions_entering_children == []
        assert len(state_l1_l11_l113.transitions_entering_children_simplified) == 1
        assert state_l1_l11_l113.transitions_entering_children_simplified[0] is None
        assert len(state_l1_l11_l113.transitions_from) == 2
        assert state_l1_l11_l113.transitions_from[0].from_state == "L113"
        assert state_l1_l11_l113.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l11_l113.transitions_from[0].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_l11_l113.transitions_from[0].guard is None
        assert state_l1_l11_l113.transitions_from[0].effects == [
            Operation(var_name="__forced_0", expr=Integer(value=1))
        ]
        assert state_l1_l11_l113.transitions_from[0].doc is None
        assert state_l1_l11_l113.transitions_from[0].parent_ref().name == "L11"
        assert state_l1_l11_l113.transitions_from[0].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l113.transitions_from[0].target_history is None
        assert state_l1_l11_l113.transitions_from[0].history_role is None
        assert state_l1_l11_l113.transitions_from[0].history_user_guard is None
        assert state_l1_l11_l113.transitions_from[1].from_state == "L113"
        assert state_l1_l11_l113.transitions_from[1].to_state == EXIT_STATE
        assert state_l1_l11_l113.transitions_from[1].event == Event(
            name="E1", state_path=("L1", "L11", "L113"), extra_name=None, doc=None
        )
        assert state_l1_l11_l113.transitions_from[1].guard is None
        assert state_l1_l11_l113.transitions_from[1].effects == []
        assert state_l1_l11_l113.transitions_from[1].doc is None
        assert state_l1_l11_l113.transitions_from[1].parent_ref().name == "L11"
        assert state_l1_l11_l113.transitions_from[1].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l113.transitions_from[1].target_history is None
        assert state_l1_l11_l113.transitions_from[1].history_role is None
        assert state_l1_l11_l113.transitions_from[1].history_user_guard is None
        assert len(state_l1_l11_l113.transitions_to) == 1
        assert state_l1_l11_l113.transitions_to[0].from_state == "__forced_gate_1"
        assert state_l1_l11_l113.transitions_to[0].to_state == "L113"
        assert state_l1_l11_l113.transitions_to[0].event is None
        assert state_l1_l11_l113.transitions_to[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_l113.transitions_to[0].effects == []
        assert state_l1_l11_l113.transitions_to[0].doc is None
        assert state_l1_l11_l113.transitions_to[0].parent_ref().name == "L11"
        assert state_l1_l11_l113.transitions_to[0].parent_ref().path == ("L1", "L11")
        assert state_l1_l11_l113.transitions_to[0].target_history is None
        assert state_l1_l11_l113.transitions_to[0].history_role is None
        assert state_l1_l11_l113.transitions_to[0].history_user_guard is None

    def test_state_l1_l11_l113_to_ast_node(self, state_l1_l11_l113):
        ast_node = state_l1_l11_l113.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L113",
            extra_name=None,
            events=[dsl_nodes.EventDefinition(name="E1", extra_name=None, doc=None)],
            imports=[],
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_l113_list_on_enters(self, state_l1_l11_l113):
        lst = state_l1_l11_l113.list_on_enters()
        assert lst == []

        lst = state_l1_l11_l113.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_l113.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_l113.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l113.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l113.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1_l11_l113.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l113.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l11_l113.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l11_l113_during_aspects(self, state_l1_l11_l113):
        lst = state_l1_l11_l113.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_l113.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_l113.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_l113.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_l113.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l113.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_l113.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_l113.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_l113.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_l1_l11_l113_during_aspect_recursively(self, state_l1_l11_l113):
        lst = state_l1_l11_l113.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_l113.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_l1_l11_forced_gate_0(self, state_l1_l11_forced_gate_0):
        assert state_l1_l11_forced_gate_0.name == "__forced_gate_0"
        assert state_l1_l11_forced_gate_0.path == ("L1", "L11", "__forced_gate_0")
        assert sorted(state_l1_l11_forced_gate_0.substates.keys()) == []
        assert state_l1_l11_forced_gate_0.regions == {}
        assert state_l1_l11_forced_gate_0.events == {}
        assert state_l1_l11_forced_gate_0.transitions == []
        assert state_l1_l11_forced_gate_0.named_functions == {}
        assert state_l1_l11_forced_gate_0.on_enters == []
        assert state_l1_l11_forced_gate_0.on_durings == []
        assert state_l1_l11_forced_gate_0.on_exits == []
        assert state_l1_l11_forced_gate_0.on_during_aspects == []
        assert state_l1_l11_forced_gate_0.parent_ref().name == "L11"
        assert state_l1_l11_forced_gate_0.parent_ref().path == ("L1", "L11")
        assert state_l1_l11_forced_gate_0.substate_name_to_id == {}
        assert state_l1_l11_forced_gate_0.extra_name is None
        assert state_l1_l11_forced_gate_0.is_pseudo
        assert state_l1_l11_forced_gate_0.doc is None
        assert not state_l1_l11_forced_gate_0.is_history_gate
        assert state_l1_l11_forced_gate_0.is_forced_gate
        assert state_l1_l11_forced_gate_0.abstract_on_during_aspects == []
        assert state_l1_l11_forced_gate_0.abstract_on_durings == []
        assert state_l1_l11_forced_gate_0.abstract_on_enters == []
        assert state_l1_l11_forced_gate_0.abstract_on_exits == []
        assert state_l1_l11_forced_gate_0.init_transitions == []
        assert state_l1_l11_forced_gate_0.is_leaf_state
        assert not state_l1_l11_forced_gate_0.is_root_state
        assert not state_l1_l11_forced_gate_0.is_stoppable
        assert state_l1_l11_forced_gate_0.non_abstract_on_during_aspects == []
        assert state_l1_l11_forced_gate_0.non_abstract_on_durings == []
        assert state_l1_l11_forced_gate_0.non_abstract_on_enters == []
        assert state_l1_l11_forced_gate_0.non_abstract_on_exits == []
        assert state_l1_l11_forced_gate_0.parent.name == "L11"
        assert state_l1_l11_forced_gate_0.parent.path == ("L1", "L11")
        assert state_l1_l11_forced_gate_0.transitions_entering_children == []
        assert (
            len(state_l1_l11_forced_gate_0.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_l1_l11_forced_gate_0.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_l1_l11_forced_gate_0.transitions_from) == 1
        assert (
            state_l1_l11_forced_gate_0.transitions_from[0].from_state
            == "__forced_gate_0"
        )
        assert state_l1_l11_forced_gate_0.transitions_from[0].to_state == "L112"
        assert state_l1_l11_forced_gate_0.transitions_from[0].event is None
        assert state_l1_l11_forced_gate_0.transitions_from[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_forced_gate_0.transitions_from[0].effects == []
        assert state_l1_l11_forced_gate_0.transitions_from[0].doc is None
        assert state_l1_l11_forced_gate_0.transitions_from[0].parent_ref().name == "L11"
        assert state_l1_l11_forced_gate_0.transitions_from[0].parent_ref().path == (
            "L1",
            "L11",
        )
        assert state_l1_l11_forced_gate_0.transitions_from[0].target_history is None
        assert state_l1_l11_forced_gate_0.transitions_from[0].history_role is None
        assert state_l1_l11_forced_gate_0.transitions_from[0].history_user_guard is None
        assert len(state_l1_l11_forced_gate_0.transitions_to) == 1
        assert state_l1_l11_forced_gate_0.transitions_to[0].from_state == "L111"
        assert (
            state_l1_l11_forced_gate_0.transitions_to[0].to_state == "__forced_gate_0"
        )
        assert state_l1_l11_forced_gate_0.transitions_to[0].event == Event(
            name="E1", state_path=("L1", "L11", "L111"), extra_name=None, doc=None
        )
        assert state_l1_l11_forced_gate_0.transitions_to[0].guard is None
        assert state_l1_l11_forced_gate_0.transitions_to[0].effects == []
        assert state_l1_l11_forced_gate_0.transitions_to[0].doc is None
        assert state_l1_l11_forced_gate_0.transitions_to[0].parent_ref().name == "L11"
        assert state_l1_l11_forced_gate_0.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
        )
        assert state_l1_l11_forced_gate_0.transitions_to[0].target_history is None
        assert state_l1_l11_forced_gate_0.transitions_to[0].history_role is None
        assert state_l1_l11_forced_gate_0.transitions_to[0].history_user_guard is None

    def test_state_l1_l11_forced_gate_0_to_ast_node(self, state_l1_l11_forced_gate_0):
        ast_node = state_l1_l11_forced_gate_0.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="__forced_gate_0",
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
            is_pseudo=True,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_forced_gate_0_list_on_enters(
        self, state_l1_l11_forced_gate_0
    ):
        lst = state_l1_l11_forced_gate_0.list_on_enters()
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l11_forced_gate_0_during_aspects(
        self, state_l1_l11_forced_gate_0
    ):
        lst = state_l1_l11_forced_gate_0.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_forced_gate_0_during_aspect_recursively(
        self, state_l1_l11_forced_gate_0
    ):
        lst = state_l1_l11_forced_gate_0.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_forced_gate_0.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_l1_l11_forced_gate_1(self, state_l1_l11_forced_gate_1):
        assert state_l1_l11_forced_gate_1.name == "__forced_gate_1"
        assert state_l1_l11_forced_gate_1.path == ("L1", "L11", "__forced_gate_1")
        assert sorted(state_l1_l11_forced_gate_1.substates.keys()) == []
        assert state_l1_l11_forced_gate_1.regions == {}
        assert state_l1_l11_forced_gate_1.events == {}
        assert state_l1_l11_forced_gate_1.transitions == []
        assert state_l1_l11_forced_gate_1.named_functions == {}
        assert state_l1_l11_forced_gate_1.on_enters == []
        assert state_l1_l11_forced_gate_1.on_durings == []
        assert state_l1_l11_forced_gate_1.on_exits == []
        assert state_l1_l11_forced_gate_1.on_during_aspects == []
        assert state_l1_l11_forced_gate_1.parent_ref().name == "L11"
        assert state_l1_l11_forced_gate_1.parent_ref().path == ("L1", "L11")
        assert state_l1_l11_forced_gate_1.substate_name_to_id == {}
        assert state_l1_l11_forced_gate_1.extra_name is None
        assert state_l1_l11_forced_gate_1.is_pseudo
        assert state_l1_l11_forced_gate_1.doc is None
        assert not state_l1_l11_forced_gate_1.is_history_gate
        assert state_l1_l11_forced_gate_1.is_forced_gate
        assert state_l1_l11_forced_gate_1.abstract_on_during_aspects == []
        assert state_l1_l11_forced_gate_1.abstract_on_durings == []
        assert state_l1_l11_forced_gate_1.abstract_on_enters == []
        assert state_l1_l11_forced_gate_1.abstract_on_exits == []
        assert state_l1_l11_forced_gate_1.init_transitions == []
        assert state_l1_l11_forced_gate_1.is_leaf_state
        assert not state_l1_l11_forced_gate_1.is_root_state
        assert not state_l1_l11_forced_gate_1.is_stoppable
        assert state_l1_l11_forced_gate_1.non_abstract_on_during_aspects == []
        assert state_l1_l11_forced_gate_1.non_abstract_on_durings == []
        assert state_l1_l11_forced_gate_1.non_abstract_on_enters == []
        assert state_l1_l11_forced_gate_1.non_abstract_on_exits == []
        assert state_l1_l11_forced_gate_1.parent.name == "L11"
        assert state_l1_l11_forced_gate_1.parent.path == ("L1", "L11")
        assert state_l1_l11_forced_gate_1.transitions_entering_children == []
        assert (
            len(state_l1_l11_forced_gate_1.transitions_entering_children_simplified)
            == 1
        )
        assert (
            state_l1_l11_forced_gate_1.transitions_entering_children_simplified[0]
            is None
        )
        assert len(state_l1_l11_forced_gate_1.transitions_from) == 1
        assert (
            state_l1_l11_forced_gate_1.transitions_from[0].from_state
            == "__forced_gate_1"
        )
        assert state_l1_l11_forced_gate_1.transitions_from[0].to_state == "L113"
        assert state_l1_l11_forced_gate_1.transitions_from[0].event is None
        assert state_l1_l11_forced_gate_1.transitions_from[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_l11_forced_gate_1.transitions_from[0].effects == []
        assert state_l1_l11_forced_gate_1.transitions_from[0].doc is None
        assert state_l1_l11_forced_gate_1.transitions_from[0].parent_ref().name == "L11"
        assert state_l1_l11_forced_gate_1.transitions_from[0].parent_ref().path == (
            "L1",
            "L11",
        )
        assert state_l1_l11_forced_gate_1.transitions_from[0].target_history is None
        assert state_l1_l11_forced_gate_1.transitions_from[0].history_role is None
        assert state_l1_l11_forced_gate_1.transitions_from[0].history_user_guard is None
        assert len(state_l1_l11_forced_gate_1.transitions_to) == 1
        assert state_l1_l11_forced_gate_1.transitions_to[0].from_state == "L111"
        assert (
            state_l1_l11_forced_gate_1.transitions_to[0].to_state == "__forced_gate_1"
        )
        assert state_l1_l11_forced_gate_1.transitions_to[0].event == Event(
            name="E2", state_path=("L1", "L11", "L111"), extra_name=None, doc=None
        )
        assert state_l1_l11_forced_gate_1.transitions_to[0].guard is None
        assert state_l1_l11_forced_gate_1.transitions_to[0].effects == []
        assert state_l1_l11_forced_gate_1.transitions_to[0].doc is None
        assert state_l1_l11_forced_gate_1.transitions_to[0].parent_ref().name == "L11"
        assert state_l1_l11_forced_gate_1.transitions_to[0].parent_ref().path == (
            "L1",
            "L11",
        )
        assert state_l1_l11_forced_gate_1.transitions_to[0].target_history is None
        assert state_l1_l11_forced_gate_1.transitions_to[0].history_role is None
        assert state_l1_l11_forced_gate_1.transitions_to[0].history_user_guard is None

    def test_state_l1_l11_forced_gate_1_to_ast_node(self, state_l1_l11_forced_gate_1):
        ast_node = state_l1_l11_forced_gate_1.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="__forced_gate_1",
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
            is_pseudo=True,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l11_forced_gate_1_list_on_enters(
        self, state_l1_l11_forced_gate_1
    ):
        lst = state_l1_l11_forced_gate_1.list_on_enters()
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_enters(
            is_abstract=False, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_enters(
            is_abstract=False, with_ids=True
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_enters(
            is_abstract=True, with_ids=False
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l11_forced_gate_1_during_aspects(
        self, state_l1_l11_forced_gate_1
    ):
        lst = state_l1_l11_forced_gate_1.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_l11_forced_gate_1_during_aspect_recursively(
        self, state_l1_l11_forced_gate_1
    ):
        lst = state_l1_l11_forced_gate_1.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l11_forced_gate_1.list_on_during_aspect_recursively(
            with_ids=True
        )
        assert lst == []

    def test_state_l1_l12(self, state_l1_l12):
        assert state_l1_l12.name == "L12"
        assert state_l1_l12.path == ("L1", "L12")
        assert sorted(state_l1_l12.substates.keys()) == []
        assert state_l1_l12.regions == {}
        assert state_l1_l12.events == {}
        assert state_l1_l12.transitions == []
        assert state_l1_l12.named_functions == {}
        assert state_l1_l12.on_enters == []
        assert state_l1_l12.on_durings == []
        assert state_l1_l12.on_exits == []
        assert state_l1_l12.on_during_aspects == []
        assert state_l1_l12.parent_ref().name == "L1"
        assert state_l1_l12.parent_ref().path == ("L1",)
        assert state_l1_l12.substate_name_to_id == {}
        assert state_l1_l12.extra_name is None
        assert not state_l1_l12.is_pseudo
        assert state_l1_l12.doc is None
        assert not state_l1_l12.is_history_gate
        assert not state_l1_l12.is_forced_gate
        assert state_l1_l12.abstract_on_during_aspects == []
        assert state_l1_l12.abstract_on_durings == []
        assert state_l1_l12.abstract_on_enters == []
        assert state_l1_l12.abstract_on_exits == []
        assert state_l1_l12.init_transitions == []
        assert state_l1_l12.is_leaf_state
        assert not state_l1_l12.is_root_state
        assert state_l1_l12.is_stoppable
        assert state_l1_l12.non_abstract_on_during_aspects == []
        assert state_l1_l12.non_abstract_on_durings == []
        assert state_l1_l12.non_abstract_on_enters == []
        assert state_l1_l12.non_abstract_on_exits == []
        assert state_l1_l12.parent.name == "L1"
        assert state_l1_l12.parent.path == ("L1",)
        assert state_l1_l12.transitions_entering_children == []
        assert len(state_l1_l12.transitions_entering_children_simplified) == 1
        assert state_l1_l12.transitions_entering_children_simplified[0] is None
        assert len(state_l1_l12.transitions_from) == 1
        assert state_l1_l12.transitions_from[0].from_state == "L12"
        assert state_l1_l12.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l12.transitions_from[0].event is None
        assert state_l1_l12.transitions_from[0].guard is None
        assert state_l1_l12.transitions_from[0].effects == []
        assert state_l1_l12.transitions_from[0].doc is None
        assert state_l1_l12.transitions_from[0].parent_ref().name == "L1"
        assert state_l1_l12.transitions_from[0].parent_ref().path == ("L1",)
        assert state_l1_l12.transitions_from[0].target_history is None
        assert state_l1_l12.transitions_from[0].history_role is None
        assert state_l1_l12.transitions_from[0].history_user_guard is None
        assert state_l1_l12.transitions_to == []

    def test_state_l1_l12_to_ast_node(self, state_l1_l12):
        ast_node = state_l1_l12.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L12",
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
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_l12_list_on_enters(self, state_l1_l12):
        lst = state_l1_l12.list_on_enters()
        assert lst == []

        lst = state_l1_l12.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_l12.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_l12.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_l12.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1_l12.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1_l12.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l12.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l12.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l12_during_aspects(self, state_l1_l12):
        lst = state_l1_l12.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l12.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l12.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l12.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l12.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_l1_l12.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_l1_l12.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l12.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_l1_l12.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_l1_l12_during_aspect_recursively(self, state_l1_l12):
        lst = state_l1_l12.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l12.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_l1_forced_gate_0(self, state_l1_forced_gate_0):
        assert state_l1_forced_gate_0.name == "__forced_gate_0"
        assert state_l1_forced_gate_0.path == ("L1", "__forced_gate_0")
        assert sorted(state_l1_forced_gate_0.substates.keys()) == []
        assert state_l1_forced_gate_0.regions == {}
        assert state_l1_forced_gate_0.events == {}
        assert state_l1_forced_gate_0.transitions == []
        assert state_l1_forced_gate_0.named_functions == {}
        assert state_l1_forced_gate_0.on_enters == []
        assert state_l1_forced_gate_0.on_durings == []
        assert state_l1_forced_gate_0.on_exits == []
        assert state_l1_forced_gate_0.on_during_aspects == []
        assert state_l1_forced_gate_0.parent_ref().name == "L1"
        assert state_l1_forced_gate_0.parent_ref().path == ("L1",)
        assert state_l1_forced_gate_0.substate_name_to_id == {}
        assert state_l1_forced_gate_0.extra_name is None
        assert state_l1_forced_gate_0.is_pseudo
        assert state_l1_forced_gate_0.doc is None
        assert not state_l1_forced_gate_0.is_history_gate
        assert state_l1_forced_gate_0.is_forced_gate
        assert state_l1_forced_gate_0.abstract_on_during_aspects == []
        assert state_l1_forced_gate_0.abstract_on_durings == []
        assert state_l1_forced_gate_0.abstract_on_enters == []
        assert state_l1_forced_gate_0.abstract_on_exits == []
        assert state_l1_forced_gate_0.init_transitions == []
        assert state_l1_forced_gate_0.is_leaf_state
        assert not state_l1_forced_gate_0.is_root_state
        assert not state_l1_forced_gate_0.is_stoppable
        assert state_l1_forced_gate_0.non_abstract_on_during_aspects == []
        assert state_l1_forced_gate_0.non_abstract_on_durings == []
        assert state_l1_forced_gate_0.non_abstract_on_enters == []
        assert state_l1_forced_gate_0.non_abstract_on_exits == []
        assert state_l1_forced_gate_0.parent.name == "L1"
        assert state_l1_forced_gate_0.parent.path == ("L1",)
        assert state_l1_forced_gate_0.transitions_entering_children == []
        assert len(state_l1_forced_gate_0.transitions_entering_children_simplified) == 1
        assert (
            state_l1_forced_gate_0.transitions_entering_children_simplified[0] is None
        )
        assert len(state_l1_forced_gate_0.transitions_from) == 1
        assert (
            state_l1_forced_gate_0.transitions_from[0].from_state == "__forced_gate_0"
        )
        assert state_l1_forced_gate_0.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_forced_gate_0.transitions_from[0].event is None
        assert state_l1_forced_gate_0.transitions_from[0].guard == BinaryOp(
            x=Variable(name="__forced_0"), op="==", y=Integer(value=0)
        )
        assert state_l1_forced_gate_0.transitions_from[0].effects == []
        assert state_l1_forced_gate_0.transitions_from[0].doc is None
        assert state_l1_forced_gate_0.transitions_from[0].parent_ref().name == "L1"
        assert state_l1_forced_gate_0.transitions_from[0].parent_ref().path == ("L1",)
        assert state_l1_forced_gate_0.transitions_from[0].target_history is None
        assert state_l1_forced_gate_0.transitions_from[0].history_role is None
        assert state_l1_forced_gate_0.transitions_from[0].history_user_guard is None
        assert len(state_l1_forced_gate_0.transitions_to) == 1
        assert state_l1_forced_gate_0.transitions_to[0].from_state == "L11"
        assert state_l1_forced_gate_0.transitions_to[0].to_state == "__forced_gate_0"
        assert state_l1_forced_gate_0.transitions_to[0].event == Event(
            name="E1", state_path=("L1", "L11"), extra_name=None, doc=None
        )
        assert state_l1_forced_gate_0.transitions_to[0].guard is None
        assert state_l1_forced_gate_0.transitions_to[0].effects == []
        assert state_l1_forced_gate_0.transitions_to[0].doc is None
        assert state_l1_forced_gate_0.transitions_to[0].parent_ref().name == "L1"
        assert state_l1_forced_gate_0.transitions_to[0].parent_ref().path == ("L1",)
        assert state_l1_forced_gate_0.transitions_to[0].target_history is None
        assert state_l1_forced_gate_0.transitions_to[0].history_role is None
        assert state_l1_forced_gate_0.transitions_to[0].history_user_guard is None

    def test_state_l1_forced_gate_0_to_ast_node(self, state_l1_forced_gate_0):
        ast_node = state_l1_forced_gate_0.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="__forced_gate_0",
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
            is_pseudo=True,
            doc=None,
            histories=[],
            regions=[],
        )

    def test_state_l1_forced_gate_0_list_on_enters(self, state_l1_forced_gate_0):
        lst = state_l1_forced_gate_0.list_on_enters()
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_enters(with_ids=False)
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_enters(with_ids=True)
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_forced_gate_0_during_aspects(self, state_l1_forced_gate_0):
        lst = state_l1_forced_gate_0.list_on_during_aspects()
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_during_aspects(
            is_abstract=False, aspect="before"
        )
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_during_aspects(
            is_abstract=False, aspect="after"
        )
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_during_aspects(
            is_abstract=True, aspect="before"
        )
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_during_aspects(
            is_abstract=True, aspect="after"
        )
        assert lst == []

    def test_state_l1_forced_gate_0_during_aspect_recursively(
        self, state_l1_forced_gate_0
    ):
        lst = state_l1_forced_gate_0.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_forced_gate_0.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int __forced_0 = 0;
state L1 {
    state L11 {
        state L111 {
            state L1111 {
                state L11111 {
                    event E1;
                    event E2;
                }
                state L11112 {
                    event E1;
                }
                state L11113 {
                    event E1;
                }
                event E1;
                event E2;
                L11111 -> [*] : /L11.E1 effect {
                    __forced_0 = 1;
                }
                L11112 -> [*] : /L11.E1 effect {
                    __forced_0 = 1;
                }
                L11113 -> [*] : /L11.E1 effect {
                    __forced_0 = 1;
                }
                [*] -> L11111;
                L11111 -> L11112 :: E1;
                L11111 -> L11113 :: E2;
                L11112 -> [*] :: E1;
                L11113 -> [*] :: E1;
            }
            state L1112 {
                event E1;
            }
            state L1113 {
                event E1;
            }
            pseudo state __forced_gate_0;
            pseudo state __forced_gate_1;
            event E1;
            event E2;
            L1111 -> [*] : if [__forced_0 == 1];
            L1112 -> [*] : /L11.E1 effect {
                __forced_0 = 1;
            }
            L1113 -> [*] : /L11.E1 effect {
                __forced_0 = 1;
            }
            [*] -> L1111;
            L1111 -> __forced_gate_0 :: E1;
            L1111 -> __forced_gate_1 :: E2;
            L1112 -> [*] :: E1;
            L1113 -> [*] :: E1;
            __forced_gate_0 -> L1112 : if [__forced_0 == 0];
            __forced_gate_1 -> L1113 : if [__forced_0 == 0];
        }
        state L112 {
            event E1;
        }
        state L113 {
            event E1;
        }
        pseudo state __forced_gate_0;
        pseudo state __forced_gate_1;
        event E1;
        L111 -> [*] : if [__forced_0 == 1];
        L112 -> [*] : E1 effect {
            __forced_0 = 1;
        }
        L113 -> [*] : E1 effect {
            __forced_0 = 1;
        }
        [*] -> L111;
        L111 -> __forced_gate_0 :: E1;
        L111 -> __forced_gate_1 :: E2;
        L112 -> [*] :: E1;
        L113 -> [*] :: E1;
        __forced_gate_0 -> L112 : if [__forced_0 == 0];
        __forced_gate_1 -> L113 : if [__forced_0 == 0];
    }
    state L12;
    pseudo state __forced_gate_0;
    L11 -> [*] : if [__forced_0 == 1] effect {
        __forced_0 = 0;
    }
    L11 -> __forced_gate_0 :: E1;
    [*] -> L11;
    L12 -> [*];
    __forced_gate_0 -> [*] : if [__forced_0 == 0];
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

state "L1" as l1 <<composite>> {
    state "L11" as l1__l11 <<composite>> {
        state "L111" as l1__l11__l111 <<composite>> {
            state "L1111" as l1__l11__l111__l1111 <<composite>> {
                state "L11111" as l1__l11__l111__l1111__l11111
                state "L11112" as l1__l11__l111__l1111__l11112
                state "L11113" as l1__l11__l111__l1111__l11113
                l1__l11__l111__l1111__l11111 --> [*] : /L11.E1
                l1__l11__l111__l1111__l11112 --> [*] : /L11.E1
                l1__l11__l111__l1111__l11113 --> [*] : /L11.E1
                [*] --> l1__l11__l111__l1111__l11111
                l1__l11__l111__l1111__l11111 --> l1__l11__l111__l1111__l11112 : L11111.E1
                l1__l11__l111__l1111__l11111 --> l1__l11__l111__l1111__l11113 : L11111.E2
                l1__l11__l111__l1111__l11112 --> [*] : L11112.E1
                l1__l11__l111__l1111__l11113 --> [*] : L11113.E1
            }
            state "L1112" as l1__l11__l111__l1112
            state "L1113" as l1__l11__l111__l1113
            l1__l11__l111__l1111 --> [*] : /L11.E1
            l1__l11__l111__l1112 --> [*] : /L11.E1
            l1__l11__l111__l1113 --> [*] : /L11.E1
            [*] --> l1__l11__l111__l1111
            l1__l11__l111__l1111 --> l1__l11__l111__l1112 : L1111.E1
            l1__l11__l111__l1111 --> l1__l11__l111__l1113 : L1111.E2
            l1__l11__l111__l1112 --> [*] : L1112.E1
            l1__l11__l111__l1113 --> [*] : L1113.E1
        }
        state "L112" as l1__l11__l112
        state "L113" as l1__l11__l113
        l1__l11__l111 --> [*] : E1
        l1__l11__l112 --> [*] : E1
        l1__l11__l113 --> [*] : E1
        [*] --> l1__l11__l111
        l1__l11__l111 --> l1__l11__l112 : L111.E1
        l1__l11__l111 --> l1__l11__l113 : L111.E2
        l1__l11__l112 --> [*] : L112.E1
        l1__l11__l113 --> [*] : L113.E1
    }
    state "L12" as l1__l12
    l1__l11 --> [*] : L11.E1
    [*] --> l1__l11
    l1__l12 --> [*]
}
[*] --> l1
l1 --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml(options="full")),
        )
