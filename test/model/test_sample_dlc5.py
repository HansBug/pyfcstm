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
def int a  = 0;

state L1
{
    [*]->L2;
    L2->[*];

    during before
    {
        a = 1;
    }

    during before abstract mock;
    >> during before abstract user_B;
    >> during before abstract user_A;

    state L2
    {
        [*]->L21;
        L21->L22 :: E1;
        L22->[*] :: E1;

        >>during before abstract user_B;
        >>during before abstract user_A;

        pseudo state L21;
        state L22;
    }
}
    """,
        entry_name="state_machine_dsl",
    )
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.fixture()
def state_l1(model):
    return model.root_state


@pytest.fixture()
def state_l1_l2(state_l1):
    return state_l1.substates["L2"]


@pytest.fixture()
def state_l1_l2_l21(state_l1_l2):
    return state_l1_l2.substates["L21"]


@pytest.fixture()
def state_l1_l2_l22(state_l1_l2):
    return state_l1_l2.substates["L22"]


@pytest.mark.unittest
class TestModelStateL1:
    def test_model(self, model):
        assert model.defines == {
            "a": VarDefine(name="a", type="int", init=Integer(value=0))
        }
        assert model.root_state.name == "L1"
        assert model.root_state.path == ("L1",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="a", type="int", expr=dsl_nodes.Integer(raw="0")
            )
        ]
        assert ast_node.root_state.name == "L1"

    def test_state_l1(self, state_l1):
        assert state_l1.name == "L1"
        assert state_l1.path == ("L1",)
        assert sorted(state_l1.substates.keys()) == ["L2"]
        assert state_l1.events == {}
        assert len(state_l1.transitions) == 2
        assert state_l1.transitions[0].from_state == INIT_STATE
        assert state_l1.transitions[0].to_state == "L2"
        assert state_l1.transitions[0].event is None
        assert state_l1.transitions[0].guard is None
        assert state_l1.transitions[0].effects == []
        assert state_l1.transitions[0].parent_ref().name == "L1"
        assert state_l1.transitions[0].parent_ref().path == ("L1",)
        assert state_l1.transitions[1].from_state == "L2"
        assert state_l1.transitions[1].to_state == EXIT_STATE
        assert state_l1.transitions[1].event is None
        assert state_l1.transitions[1].guard is None
        assert state_l1.transitions[1].effects == []
        assert state_l1.transitions[1].parent_ref().name == "L1"
        assert state_l1.transitions[1].parent_ref().path == ("L1",)
        assert state_l1.named_functions == {
            "mock": OnStage(
                stage="during",
                aspect="before",
                name="mock",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "mock"),
            ),
            "user_B": OnAspect(
                stage="during",
                aspect="before",
                name="user_B",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "user_B"),
            ),
            "user_A": OnAspect(
                stage="during",
                aspect="before",
                name="user_A",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "user_A"),
            ),
        }
        assert state_l1.on_enters == []
        assert state_l1.on_durings == [
            OnStage(
                stage="during",
                aspect="before",
                name=None,
                doc=None,
                operations=[Operation(var_name="a", expr=Integer(value=1))],
                is_abstract=False,
                state_path=("L1", None),
            ),
            OnStage(
                stage="during",
                aspect="before",
                name="mock",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "mock"),
            ),
        ]
        assert state_l1.on_exits == []
        assert state_l1.on_during_aspects == [
            OnAspect(
                stage="during",
                aspect="before",
                name="user_B",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "user_B"),
            ),
            OnAspect(
                stage="during",
                aspect="before",
                name="user_A",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "user_A"),
            ),
        ]
        assert state_l1.parent_ref is None
        assert state_l1.substate_name_to_id == {"L2": 0}
        assert not state_l1.is_pseudo
        assert state_l1.abstract_on_during_aspects == [
            OnAspect(
                stage="during",
                aspect="before",
                name="user_B",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "user_B"),
            ),
            OnAspect(
                stage="during",
                aspect="before",
                name="user_A",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "user_A"),
            ),
        ]
        assert state_l1.abstract_on_durings == [
            OnStage(
                stage="during",
                aspect="before",
                name="mock",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "mock"),
            )
        ]
        assert state_l1.abstract_on_enters == []
        assert state_l1.abstract_on_exits == []
        assert not state_l1.is_leaf_state
        assert state_l1.is_root_state
        assert state_l1.non_abstract_on_during_aspects == []
        assert state_l1.non_abstract_on_durings == [
            OnStage(
                stage="during",
                aspect="before",
                name=None,
                doc=None,
                operations=[Operation(var_name="a", expr=Integer(value=1))],
                is_abstract=False,
                state_path=("L1", None),
            )
        ]
        assert state_l1.non_abstract_on_enters == []
        assert state_l1.non_abstract_on_exits == []
        assert state_l1.parent is None
        assert len(state_l1.transitions_entering_children) == 1
        assert state_l1.transitions_entering_children[0].from_state == INIT_STATE
        assert state_l1.transitions_entering_children[0].to_state == "L2"
        assert state_l1.transitions_entering_children[0].event is None
        assert state_l1.transitions_entering_children[0].guard is None
        assert state_l1.transitions_entering_children[0].effects == []
        assert state_l1.transitions_entering_children[0].parent_ref().name == "L1"
        assert state_l1.transitions_entering_children[0].parent_ref().path == ("L1",)
        assert len(state_l1.transitions_entering_children_simplified) == 1
        assert (
            state_l1.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert state_l1.transitions_entering_children_simplified[0].to_state == "L2"
        assert state_l1.transitions_entering_children_simplified[0].event is None
        assert state_l1.transitions_entering_children_simplified[0].guard is None
        assert state_l1.transitions_entering_children_simplified[0].effects == []
        assert (
            state_l1.transitions_entering_children_simplified[0].parent_ref().name
            == "L1"
        )
        assert state_l1.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("L1",)
        assert len(state_l1.transitions_from) == 1
        assert state_l1.transitions_from[0].from_state == "L1"
        assert state_l1.transitions_from[0].to_state == EXIT_STATE
        assert state_l1.transitions_from[0].event is None
        assert state_l1.transitions_from[0].guard is None
        assert state_l1.transitions_from[0].effects == []
        assert state_l1.transitions_from[0].parent_ref is None
        assert len(state_l1.transitions_to) == 1
        assert state_l1.transitions_to[0].from_state == INIT_STATE
        assert state_l1.transitions_to[0].to_state == "L1"
        assert state_l1.transitions_to[0].event is None
        assert state_l1.transitions_to[0].guard is None
        assert state_l1.transitions_to[0].effects == []
        assert state_l1.transitions_to[0].parent_ref is None

    def test_state_l1_to_ast_node(self, state_l1):
        ast_node = state_l1.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L1",
            substates=[
                dsl_nodes.StateDefinition(
                    name="L2",
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="L21",
                            substates=[],
                            transitions=[],
                            enters=[],
                            durings=[],
                            exits=[],
                            during_aspects=[],
                            force_transitions=[],
                            is_pseudo=True,
                        ),
                        dsl_nodes.StateDefinition(
                            name="L22",
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
                            to_state="L21",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L21",
                            to_state="L22",
                            event_id=dsl_nodes.ChainID(
                                path=["L21", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="L22",
                            to_state=EXIT_STATE,
                            event_id=dsl_nodes.ChainID(
                                path=["L22", "E1"], is_absolute=False
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                    ],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[
                        dsl_nodes.DuringAspectAbstractFunction(
                            name="user_B", aspect="before", doc=None
                        ),
                        dsl_nodes.DuringAspectAbstractFunction(
                            name="user_A", aspect="before", doc=None
                        ),
                    ],
                    force_transitions=[],
                    is_pseudo=False,
                )
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="L2",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L2",
                    to_state=EXIT_STATE,
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
            ],
            enters=[],
            durings=[
                dsl_nodes.DuringOperations(
                    aspect="before",
                    operations=[
                        dsl_nodes.OperationAssignment(
                            name="a", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                    name=None,
                ),
                dsl_nodes.DuringAbstractFunction(
                    name="mock", aspect="before", doc=None
                ),
            ],
            exits=[],
            during_aspects=[
                dsl_nodes.DuringAspectAbstractFunction(
                    name="user_B", aspect="before", doc=None
                ),
                dsl_nodes.DuringAspectAbstractFunction(
                    name="user_A", aspect="before", doc=None
                ),
            ],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_l1_l2(self, state_l1_l2):
        assert state_l1_l2.name == "L2"
        assert state_l1_l2.path == ("L1", "L2")
        assert sorted(state_l1_l2.substates.keys()) == ["L21", "L22"]
        assert state_l1_l2.events == {}
        assert len(state_l1_l2.transitions) == 3
        assert state_l1_l2.transitions[0].from_state == INIT_STATE
        assert state_l1_l2.transitions[0].to_state == "L21"
        assert state_l1_l2.transitions[0].event is None
        assert state_l1_l2.transitions[0].guard is None
        assert state_l1_l2.transitions[0].effects == []
        assert state_l1_l2.transitions[0].parent_ref().name == "L2"
        assert state_l1_l2.transitions[0].parent_ref().path == ("L1", "L2")
        assert state_l1_l2.transitions[1].from_state == "L21"
        assert state_l1_l2.transitions[1].to_state == "L22"
        assert state_l1_l2.transitions[1].event == Event(
            name="E1", state_path=("L1", "L2", "L21")
        )
        assert state_l1_l2.transitions[1].guard is None
        assert state_l1_l2.transitions[1].effects == []
        assert state_l1_l2.transitions[1].parent_ref().name == "L2"
        assert state_l1_l2.transitions[1].parent_ref().path == ("L1", "L2")
        assert state_l1_l2.transitions[2].from_state == "L22"
        assert state_l1_l2.transitions[2].to_state == EXIT_STATE
        assert state_l1_l2.transitions[2].event == Event(
            name="E1", state_path=("L1", "L2", "L22")
        )
        assert state_l1_l2.transitions[2].guard is None
        assert state_l1_l2.transitions[2].effects == []
        assert state_l1_l2.transitions[2].parent_ref().name == "L2"
        assert state_l1_l2.transitions[2].parent_ref().path == ("L1", "L2")
        assert state_l1_l2.named_functions == {
            "user_B": OnAspect(
                stage="during",
                aspect="before",
                name="user_B",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "L2", "user_B"),
            ),
            "user_A": OnAspect(
                stage="during",
                aspect="before",
                name="user_A",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "L2", "user_A"),
            ),
        }
        assert state_l1_l2.on_enters == []
        assert state_l1_l2.on_durings == []
        assert state_l1_l2.on_exits == []
        assert state_l1_l2.on_during_aspects == [
            OnAspect(
                stage="during",
                aspect="before",
                name="user_B",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "L2", "user_B"),
            ),
            OnAspect(
                stage="during",
                aspect="before",
                name="user_A",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "L2", "user_A"),
            ),
        ]
        assert state_l1_l2.parent_ref().name == "L1"
        assert state_l1_l2.parent_ref().path == ("L1",)
        assert state_l1_l2.substate_name_to_id == {"L21": 0, "L22": 1}
        assert not state_l1_l2.is_pseudo
        assert state_l1_l2.abstract_on_during_aspects == [
            OnAspect(
                stage="during",
                aspect="before",
                name="user_B",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "L2", "user_B"),
            ),
            OnAspect(
                stage="during",
                aspect="before",
                name="user_A",
                doc=None,
                operations=[],
                is_abstract=True,
                state_path=("L1", "L2", "user_A"),
            ),
        ]
        assert state_l1_l2.abstract_on_durings == []
        assert state_l1_l2.abstract_on_enters == []
        assert state_l1_l2.abstract_on_exits == []
        assert not state_l1_l2.is_leaf_state
        assert not state_l1_l2.is_root_state
        assert state_l1_l2.non_abstract_on_during_aspects == []
        assert state_l1_l2.non_abstract_on_durings == []
        assert state_l1_l2.non_abstract_on_enters == []
        assert state_l1_l2.non_abstract_on_exits == []
        assert state_l1_l2.parent.name == "L1"
        assert state_l1_l2.parent.path == ("L1",)
        assert len(state_l1_l2.transitions_entering_children) == 1
        assert state_l1_l2.transitions_entering_children[0].from_state == INIT_STATE
        assert state_l1_l2.transitions_entering_children[0].to_state == "L21"
        assert state_l1_l2.transitions_entering_children[0].event is None
        assert state_l1_l2.transitions_entering_children[0].guard is None
        assert state_l1_l2.transitions_entering_children[0].effects == []
        assert state_l1_l2.transitions_entering_children[0].parent_ref().name == "L2"
        assert state_l1_l2.transitions_entering_children[0].parent_ref().path == (
            "L1",
            "L2",
        )
        assert len(state_l1_l2.transitions_entering_children_simplified) == 1
        assert (
            state_l1_l2.transitions_entering_children_simplified[0].from_state
            == INIT_STATE
        )
        assert state_l1_l2.transitions_entering_children_simplified[0].to_state == "L21"
        assert state_l1_l2.transitions_entering_children_simplified[0].event is None
        assert state_l1_l2.transitions_entering_children_simplified[0].guard is None
        assert state_l1_l2.transitions_entering_children_simplified[0].effects == []
        assert (
            state_l1_l2.transitions_entering_children_simplified[0].parent_ref().name
            == "L2"
        )
        assert state_l1_l2.transitions_entering_children_simplified[
            0
        ].parent_ref().path == ("L1", "L2")
        assert len(state_l1_l2.transitions_from) == 1
        assert state_l1_l2.transitions_from[0].from_state == "L2"
        assert state_l1_l2.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l2.transitions_from[0].event is None
        assert state_l1_l2.transitions_from[0].guard is None
        assert state_l1_l2.transitions_from[0].effects == []
        assert state_l1_l2.transitions_from[0].parent_ref().name == "L1"
        assert state_l1_l2.transitions_from[0].parent_ref().path == ("L1",)
        assert len(state_l1_l2.transitions_to) == 1
        assert state_l1_l2.transitions_to[0].from_state == INIT_STATE
        assert state_l1_l2.transitions_to[0].to_state == "L2"
        assert state_l1_l2.transitions_to[0].event is None
        assert state_l1_l2.transitions_to[0].guard is None
        assert state_l1_l2.transitions_to[0].effects == []
        assert state_l1_l2.transitions_to[0].parent_ref().name == "L1"
        assert state_l1_l2.transitions_to[0].parent_ref().path == ("L1",)

    def test_state_l1_l2_to_ast_node(self, state_l1_l2):
        ast_node = state_l1_l2.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L2",
            substates=[
                dsl_nodes.StateDefinition(
                    name="L21",
                    substates=[],
                    transitions=[],
                    enters=[],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=True,
                ),
                dsl_nodes.StateDefinition(
                    name="L22",
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
                    to_state="L21",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L21",
                    to_state="L22",
                    event_id=dsl_nodes.ChainID(path=["L21", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
                dsl_nodes.TransitionDefinition(
                    from_state="L22",
                    to_state=EXIT_STATE,
                    event_id=dsl_nodes.ChainID(path=["L22", "E1"], is_absolute=False),
                    condition_expr=None,
                    post_operations=[],
                ),
            ],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[
                dsl_nodes.DuringAspectAbstractFunction(
                    name="user_B", aspect="before", doc=None
                ),
                dsl_nodes.DuringAspectAbstractFunction(
                    name="user_A", aspect="before", doc=None
                ),
            ],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_l1_l2_l21(self, state_l1_l2_l21):
        assert state_l1_l2_l21.name == "L21"
        assert state_l1_l2_l21.path == ("L1", "L2", "L21")
        assert sorted(state_l1_l2_l21.substates.keys()) == []
        assert state_l1_l2_l21.events == {
            "E1": Event(name="E1", state_path=("L1", "L2", "L21"))
        }
        assert state_l1_l2_l21.transitions == []
        assert state_l1_l2_l21.named_functions == {}
        assert state_l1_l2_l21.on_enters == []
        assert state_l1_l2_l21.on_durings == []
        assert state_l1_l2_l21.on_exits == []
        assert state_l1_l2_l21.on_during_aspects == []
        assert state_l1_l2_l21.parent_ref().name == "L2"
        assert state_l1_l2_l21.parent_ref().path == ("L1", "L2")
        assert state_l1_l2_l21.substate_name_to_id == {}
        assert state_l1_l2_l21.is_pseudo
        assert state_l1_l2_l21.abstract_on_during_aspects == []
        assert state_l1_l2_l21.abstract_on_durings == []
        assert state_l1_l2_l21.abstract_on_enters == []
        assert state_l1_l2_l21.abstract_on_exits == []
        assert state_l1_l2_l21.is_leaf_state
        assert not state_l1_l2_l21.is_root_state
        assert state_l1_l2_l21.non_abstract_on_during_aspects == []
        assert state_l1_l2_l21.non_abstract_on_durings == []
        assert state_l1_l2_l21.non_abstract_on_enters == []
        assert state_l1_l2_l21.non_abstract_on_exits == []
        assert state_l1_l2_l21.parent.name == "L2"
        assert state_l1_l2_l21.parent.path == ("L1", "L2")
        assert state_l1_l2_l21.transitions_entering_children == []
        assert len(state_l1_l2_l21.transitions_entering_children_simplified) == 1
        assert state_l1_l2_l21.transitions_entering_children_simplified[0] is None
        assert len(state_l1_l2_l21.transitions_from) == 1
        assert state_l1_l2_l21.transitions_from[0].from_state == "L21"
        assert state_l1_l2_l21.transitions_from[0].to_state == "L22"
        assert state_l1_l2_l21.transitions_from[0].event == Event(
            name="E1", state_path=("L1", "L2", "L21")
        )
        assert state_l1_l2_l21.transitions_from[0].guard is None
        assert state_l1_l2_l21.transitions_from[0].effects == []
        assert state_l1_l2_l21.transitions_from[0].parent_ref().name == "L2"
        assert state_l1_l2_l21.transitions_from[0].parent_ref().path == ("L1", "L2")
        assert len(state_l1_l2_l21.transitions_to) == 1
        assert state_l1_l2_l21.transitions_to[0].from_state == INIT_STATE
        assert state_l1_l2_l21.transitions_to[0].to_state == "L21"
        assert state_l1_l2_l21.transitions_to[0].event is None
        assert state_l1_l2_l21.transitions_to[0].guard is None
        assert state_l1_l2_l21.transitions_to[0].effects == []
        assert state_l1_l2_l21.transitions_to[0].parent_ref().name == "L2"
        assert state_l1_l2_l21.transitions_to[0].parent_ref().path == ("L1", "L2")

    def test_state_l1_l2_l21_to_ast_node(self, state_l1_l2_l21):
        ast_node = state_l1_l2_l21.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L21",
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=True,
        )

    def test_state_l1_l2_l21_during_aspect(self, state_l1_l2_l21):
        lst = state_l1_l2_l21.list_on_during_aspect_recursively()
        assert lst == []

        lst = state_l1_l2_l21.list_on_during_aspect_recursively(with_ids=True)
        assert lst == []

    def test_state_l1_l2_l22(self, state_l1_l2_l22):
        assert state_l1_l2_l22.name == "L22"
        assert state_l1_l2_l22.path == ("L1", "L2", "L22")
        assert sorted(state_l1_l2_l22.substates.keys()) == []
        assert state_l1_l2_l22.events == {
            "E1": Event(name="E1", state_path=("L1", "L2", "L22"))
        }
        assert state_l1_l2_l22.transitions == []
        assert state_l1_l2_l22.named_functions == {}
        assert state_l1_l2_l22.on_enters == []
        assert state_l1_l2_l22.on_durings == []
        assert state_l1_l2_l22.on_exits == []
        assert state_l1_l2_l22.on_during_aspects == []
        assert state_l1_l2_l22.parent_ref().name == "L2"
        assert state_l1_l2_l22.parent_ref().path == ("L1", "L2")
        assert state_l1_l2_l22.substate_name_to_id == {}
        assert not state_l1_l2_l22.is_pseudo
        assert state_l1_l2_l22.abstract_on_during_aspects == []
        assert state_l1_l2_l22.abstract_on_durings == []
        assert state_l1_l2_l22.abstract_on_enters == []
        assert state_l1_l2_l22.abstract_on_exits == []
        assert state_l1_l2_l22.is_leaf_state
        assert not state_l1_l2_l22.is_root_state
        assert state_l1_l2_l22.non_abstract_on_during_aspects == []
        assert state_l1_l2_l22.non_abstract_on_durings == []
        assert state_l1_l2_l22.non_abstract_on_enters == []
        assert state_l1_l2_l22.non_abstract_on_exits == []
        assert state_l1_l2_l22.parent.name == "L2"
        assert state_l1_l2_l22.parent.path == ("L1", "L2")
        assert state_l1_l2_l22.transitions_entering_children == []
        assert len(state_l1_l2_l22.transitions_entering_children_simplified) == 1
        assert state_l1_l2_l22.transitions_entering_children_simplified[0] is None
        assert len(state_l1_l2_l22.transitions_from) == 1
        assert state_l1_l2_l22.transitions_from[0].from_state == "L22"
        assert state_l1_l2_l22.transitions_from[0].to_state == EXIT_STATE
        assert state_l1_l2_l22.transitions_from[0].event == Event(
            name="E1", state_path=("L1", "L2", "L22")
        )
        assert state_l1_l2_l22.transitions_from[0].guard is None
        assert state_l1_l2_l22.transitions_from[0].effects == []
        assert state_l1_l2_l22.transitions_from[0].parent_ref().name == "L2"
        assert state_l1_l2_l22.transitions_from[0].parent_ref().path == ("L1", "L2")
        assert len(state_l1_l2_l22.transitions_to) == 1
        assert state_l1_l2_l22.transitions_to[0].from_state == "L21"
        assert state_l1_l2_l22.transitions_to[0].to_state == "L22"
        assert state_l1_l2_l22.transitions_to[0].event == Event(
            name="E1", state_path=("L1", "L2", "L21")
        )
        assert state_l1_l2_l22.transitions_to[0].guard is None
        assert state_l1_l2_l22.transitions_to[0].effects == []
        assert state_l1_l2_l22.transitions_to[0].parent_ref().name == "L2"
        assert state_l1_l2_l22.transitions_to[0].parent_ref().path == ("L1", "L2")

    def test_state_l1_l2_l22_to_ast_node(self, state_l1_l2_l22):
        ast_node = state_l1_l2_l22.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L22",
            substates=[],
            transitions=[],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_l1_l2_l22_during_aspect(self, state_l1_l2_l22):
        lst = state_l1_l2_l22.list_on_during_aspect_recursively()
        assert len(lst) == 4
        st, on_stage = lst[0]
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage == OnAspect(
            stage="during",
            aspect="before",
            name="user_B",
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=("L1", "user_B"),
        )
        st, on_stage = lst[1]
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage == OnAspect(
            stage="during",
            aspect="before",
            name="user_A",
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=("L1", "user_A"),
        )
        st, on_stage = lst[2]
        assert st.name == "L2"
        assert st.path == ("L1", "L2")
        assert on_stage == OnAspect(
            stage="during",
            aspect="before",
            name="user_B",
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=("L1", "L2", "user_B"),
        )
        st, on_stage = lst[3]
        assert st.name == "L2"
        assert st.path == ("L1", "L2")
        assert on_stage == OnAspect(
            stage="during",
            aspect="before",
            name="user_A",
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=("L1", "L2", "user_A"),
        )

        lst = state_l1_l2_l22.list_on_during_aspect_recursively(with_ids=True)
        assert len(lst) == 4
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage == OnAspect(
            stage="during",
            aspect="before",
            name="user_B",
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=("L1", "user_B"),
        )
        id_, st, on_stage = lst[1]
        assert id_ == 2
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage == OnAspect(
            stage="during",
            aspect="before",
            name="user_A",
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=("L1", "user_A"),
        )
        id_, st, on_stage = lst[2]
        assert id_ == 1
        assert st.name == "L2"
        assert st.path == ("L1", "L2")
        assert on_stage == OnAspect(
            stage="during",
            aspect="before",
            name="user_B",
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=("L1", "L2", "user_B"),
        )
        id_, st, on_stage = lst[3]
        assert id_ == 2
        assert st.name == "L2"
        assert st.path == ("L1", "L2")
        assert on_stage == OnAspect(
            stage="during",
            aspect="before",
            name="user_A",
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=("L1", "L2", "user_A"),
        )

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int a = 0;
state L1 {
    during before {
        a = 1;
    }
    during before abstract mock;
    >> during before abstract user_B;
    >> during before abstract user_A;
    state L2 {
        >> during before abstract user_B;
        >> during before abstract user_A;
        pseudo state L21;
        state L22;
        [*] -> L21;
        L21 -> L22 :: E1;
        L22 -> [*] :: E1;
    }
    [*] -> L2;
    L2 -> [*];
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
}
end note

state "L1" as l1 {
    state "L2" as l1__l2 {
        state "L21" as l1__l2__l21 #line.dotted
        state "L22" as l1__l2__l22
        [*] --> l1__l2__l21
        l1__l2__l21 --> l1__l2__l22 : L21.E1
        l1__l2__l22 --> [*] : L22.E1
    }
    l1__l2 : >> during before abstract user_B;\\n>> during before abstract user_A;
    [*] --> l1__l2
    l1__l2 --> [*]
}
l1 : during before {\\n    a = 1;\\n}\\nduring before abstract mock;\\n>> during before abstract user_B;\\n>> during before abstract user_A;
[*] --> l1
l1 --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml()),
        )
