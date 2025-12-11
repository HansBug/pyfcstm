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
def int x = 0;
def int y = 0;
state L1 {

    enter abstract F1;
    during before F12 {
        x = 0x1;
    };
    during after abstract F13;
    exit F1x ref F1;

    [*] -> L21;
    L21 -> L22 : if [x > 0];

    >> during before ref L21.F1;
    >> during after ref L22.F1;


    state L21 {
        enter F1 {
            x = 0;
            y = y + 1;
        }

        >> during after ref /F1x;

        exit ref /F1x;
    }

    state L22 {
        exit F1 {
            x = x + 1;
            y = 0;
        }

        enter ref /F1x;
        during ref /F1x;
        during ref F1;
        exit ref /F1;
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
def state_l1_l21(state_l1):
    return state_l1.substates["L21"]


@pytest.fixture()
def state_l1_l22(state_l1):
    return state_l1.substates["L22"]


@pytest.mark.unittest
class TestModelStateL1:
    def test_model(self, model):
        assert model.defines == {
            "x": VarDefine(name="x", type="int", init=Integer(value=0)),
            "y": VarDefine(name="y", type="int", init=Integer(value=0)),
        }
        assert model.root_state.name == "L1"
        assert model.root_state.path == ("L1",)

    def test_model_to_ast(self, model):
        ast_node = model.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="x", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
            dsl_nodes.DefAssignment(
                name="y", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
        ]
        assert ast_node.root_state.name == "L1"

    def test_state_l1(self, state_l1):
        assert state_l1.name == "L1"
        assert state_l1.path == ("L1",)
        assert sorted(state_l1.substates.keys()) == ["L21", "L22"]
        assert state_l1.events == {}
        assert len(state_l1.transitions) == 2
        assert state_l1.transitions[0].from_state == INIT_STATE
        assert state_l1.transitions[0].to_state == "L21"
        assert state_l1.transitions[0].event is None
        assert state_l1.transitions[0].guard is None
        assert state_l1.transitions[0].effects == []
        assert state_l1.transitions[0].parent_ref().name == "L1"
        assert state_l1.transitions[0].parent_ref().path == ("L1",)
        assert state_l1.transitions[1].from_state == "L21"
        assert state_l1.transitions[1].to_state == "L22"
        assert state_l1.transitions[1].event is None
        assert state_l1.transitions[1].guard == BinaryOp(
            x=Variable(name="x"), op=">", y=Integer(value=0)
        )
        assert state_l1.transitions[1].effects == []
        assert state_l1.transitions[1].parent_ref().name == "L1"
        assert state_l1.transitions[1].parent_ref().path == ("L1",)
        assert sorted(state_l1.named_functions.keys()) == ["F1", "F12", "F13", "F1x"]
        assert state_l1.named_functions["F1"].stage == "enter"
        assert state_l1.named_functions["F1"].aspect is None
        assert state_l1.named_functions["F1"].name == "F1"
        assert state_l1.named_functions["F1"].doc is None
        assert state_l1.named_functions["F1"].operations == []
        assert state_l1.named_functions["F1"].is_abstract
        assert state_l1.named_functions["F1"].state_path == ("L1", "F1")
        assert state_l1.named_functions["F1"].ref is None
        assert state_l1.named_functions["F1"].ref_state_path is None
        assert state_l1.named_functions["F1"].parent_ref().name == "L1"
        assert state_l1.named_functions["F1"].parent_ref().path == ("L1",)
        assert not state_l1.named_functions["F1"].is_aspect
        assert not state_l1.named_functions["F1"].is_ref
        assert state_l1.named_functions["F1"].parent.name == "L1"
        assert state_l1.named_functions["F1"].parent.path == ("L1",)
        assert state_l1.named_functions["F12"].stage == "during"
        assert state_l1.named_functions["F12"].aspect == "before"
        assert state_l1.named_functions["F12"].name == "F12"
        assert state_l1.named_functions["F12"].doc is None
        assert state_l1.named_functions["F12"].operations == [
            Operation(var_name="x", expr=Integer(value=1))
        ]
        assert not state_l1.named_functions["F12"].is_abstract
        assert state_l1.named_functions["F12"].state_path == ("L1", "F12")
        assert state_l1.named_functions["F12"].ref is None
        assert state_l1.named_functions["F12"].ref_state_path is None
        assert state_l1.named_functions["F12"].parent_ref().name == "L1"
        assert state_l1.named_functions["F12"].parent_ref().path == ("L1",)
        assert not state_l1.named_functions["F12"].is_aspect
        assert not state_l1.named_functions["F12"].is_ref
        assert state_l1.named_functions["F12"].parent.name == "L1"
        assert state_l1.named_functions["F12"].parent.path == ("L1",)
        assert state_l1.named_functions["F13"].stage == "during"
        assert state_l1.named_functions["F13"].aspect == "after"
        assert state_l1.named_functions["F13"].name == "F13"
        assert state_l1.named_functions["F13"].doc is None
        assert state_l1.named_functions["F13"].operations == []
        assert state_l1.named_functions["F13"].is_abstract
        assert state_l1.named_functions["F13"].state_path == ("L1", "F13")
        assert state_l1.named_functions["F13"].ref is None
        assert state_l1.named_functions["F13"].ref_state_path is None
        assert state_l1.named_functions["F13"].parent_ref().name == "L1"
        assert state_l1.named_functions["F13"].parent_ref().path == ("L1",)
        assert not state_l1.named_functions["F13"].is_aspect
        assert not state_l1.named_functions["F13"].is_ref
        assert state_l1.named_functions["F13"].parent.name == "L1"
        assert state_l1.named_functions["F13"].parent.path == ("L1",)
        assert state_l1.named_functions["F1x"].stage == "exit"
        assert state_l1.named_functions["F1x"].aspect is None
        assert state_l1.named_functions["F1x"].name == "F1x"
        assert state_l1.named_functions["F1x"].doc is None
        assert state_l1.named_functions["F1x"].operations == []
        assert not state_l1.named_functions["F1x"].is_abstract
        assert state_l1.named_functions["F1x"].state_path == ("L1", "F1x")
        assert state_l1.named_functions["F1x"].ref.name == "F1"
        assert state_l1.named_functions["F1x"].ref.aspect == None
        assert state_l1.named_functions["F1x"].ref.state_path == ("L1", "F1")
        assert state_l1.named_functions["F1x"].ref_state_path == ("L1", "F1")
        assert state_l1.named_functions["F1x"].parent_ref().name == "L1"
        assert state_l1.named_functions["F1x"].parent_ref().path == ("L1",)
        assert not state_l1.named_functions["F1x"].is_aspect
        assert state_l1.named_functions["F1x"].is_ref
        assert state_l1.named_functions["F1x"].parent.name == "L1"
        assert state_l1.named_functions["F1x"].parent.path == ("L1",)
        assert len(state_l1.on_enters) == 1
        assert state_l1.on_enters[0].stage == "enter"
        assert state_l1.on_enters[0].aspect is None
        assert state_l1.on_enters[0].name == "F1"
        assert state_l1.on_enters[0].doc is None
        assert state_l1.on_enters[0].operations == []
        assert state_l1.on_enters[0].is_abstract
        assert state_l1.on_enters[0].state_path == ("L1", "F1")
        assert state_l1.on_enters[0].ref is None
        assert state_l1.on_enters[0].ref_state_path is None
        assert state_l1.on_enters[0].parent_ref().name == "L1"
        assert state_l1.on_enters[0].parent_ref().path == ("L1",)
        assert not state_l1.on_enters[0].is_aspect
        assert not state_l1.on_enters[0].is_ref
        assert state_l1.on_enters[0].parent.name == "L1"
        assert state_l1.on_enters[0].parent.path == ("L1",)
        assert len(state_l1.on_durings) == 2
        assert state_l1.on_durings[0].stage == "during"
        assert state_l1.on_durings[0].aspect == "before"
        assert state_l1.on_durings[0].name == "F12"
        assert state_l1.on_durings[0].doc is None
        assert state_l1.on_durings[0].operations == [
            Operation(var_name="x", expr=Integer(value=1))
        ]
        assert not state_l1.on_durings[0].is_abstract
        assert state_l1.on_durings[0].state_path == ("L1", "F12")
        assert state_l1.on_durings[0].ref is None
        assert state_l1.on_durings[0].ref_state_path is None
        assert state_l1.on_durings[0].parent_ref().name == "L1"
        assert state_l1.on_durings[0].parent_ref().path == ("L1",)
        assert not state_l1.on_durings[0].is_aspect
        assert not state_l1.on_durings[0].is_ref
        assert state_l1.on_durings[0].parent.name == "L1"
        assert state_l1.on_durings[0].parent.path == ("L1",)
        assert state_l1.on_durings[1].stage == "during"
        assert state_l1.on_durings[1].aspect == "after"
        assert state_l1.on_durings[1].name == "F13"
        assert state_l1.on_durings[1].doc is None
        assert state_l1.on_durings[1].operations == []
        assert state_l1.on_durings[1].is_abstract
        assert state_l1.on_durings[1].state_path == ("L1", "F13")
        assert state_l1.on_durings[1].ref is None
        assert state_l1.on_durings[1].ref_state_path is None
        assert state_l1.on_durings[1].parent_ref().name == "L1"
        assert state_l1.on_durings[1].parent_ref().path == ("L1",)
        assert not state_l1.on_durings[1].is_aspect
        assert not state_l1.on_durings[1].is_ref
        assert state_l1.on_durings[1].parent.name == "L1"
        assert state_l1.on_durings[1].parent.path == ("L1",)
        assert len(state_l1.on_exits) == 1
        assert state_l1.on_exits[0].stage == "exit"
        assert state_l1.on_exits[0].aspect is None
        assert state_l1.on_exits[0].name == "F1x"
        assert state_l1.on_exits[0].doc is None
        assert state_l1.on_exits[0].operations == []
        assert not state_l1.on_exits[0].is_abstract
        assert state_l1.on_exits[0].state_path == ("L1", "F1x")
        assert state_l1.on_exits[0].ref.name == "F1"
        assert state_l1.on_exits[0].ref.aspect == None
        assert state_l1.on_exits[0].ref.state_path == ("L1", "F1")
        assert state_l1.on_exits[0].ref_state_path == ("L1", "F1")
        assert state_l1.on_exits[0].parent_ref().name == "L1"
        assert state_l1.on_exits[0].parent_ref().path == ("L1",)
        assert not state_l1.on_exits[0].is_aspect
        assert state_l1.on_exits[0].is_ref
        assert state_l1.on_exits[0].parent.name == "L1"
        assert state_l1.on_exits[0].parent.path == ("L1",)
        assert len(state_l1.on_during_aspects) == 2
        assert state_l1.on_during_aspects[0].stage == "during"
        assert state_l1.on_during_aspects[0].aspect == "before"
        assert state_l1.on_during_aspects[0].name is None
        assert state_l1.on_during_aspects[0].doc is None
        assert state_l1.on_during_aspects[0].operations == []
        assert not state_l1.on_during_aspects[0].is_abstract
        assert state_l1.on_during_aspects[0].state_path == ("L1", None)
        assert state_l1.on_during_aspects[0].ref.name == "F1"
        assert state_l1.on_during_aspects[0].ref.aspect == None
        assert state_l1.on_during_aspects[0].ref.state_path == ("L1", "L21", "F1")
        assert state_l1.on_during_aspects[0].ref_state_path == ("L1", "L21", "F1")
        assert state_l1.on_during_aspects[0].parent_ref().name == "L1"
        assert state_l1.on_during_aspects[0].parent_ref().path == ("L1",)
        assert state_l1.on_during_aspects[0].is_aspect
        assert state_l1.on_during_aspects[0].is_ref
        assert state_l1.on_during_aspects[0].parent.name == "L1"
        assert state_l1.on_during_aspects[0].parent.path == ("L1",)
        assert state_l1.on_during_aspects[1].stage == "during"
        assert state_l1.on_during_aspects[1].aspect == "after"
        assert state_l1.on_during_aspects[1].name is None
        assert state_l1.on_during_aspects[1].doc is None
        assert state_l1.on_during_aspects[1].operations == []
        assert not state_l1.on_during_aspects[1].is_abstract
        assert state_l1.on_during_aspects[1].state_path == ("L1", None)
        assert state_l1.on_during_aspects[1].ref.name == "F1"
        assert state_l1.on_during_aspects[1].ref.aspect == None
        assert state_l1.on_during_aspects[1].ref.state_path == ("L1", "L22", "F1")
        assert state_l1.on_during_aspects[1].ref_state_path == ("L1", "L22", "F1")
        assert state_l1.on_during_aspects[1].parent_ref().name == "L1"
        assert state_l1.on_during_aspects[1].parent_ref().path == ("L1",)
        assert state_l1.on_during_aspects[1].is_aspect
        assert state_l1.on_during_aspects[1].is_ref
        assert state_l1.on_during_aspects[1].parent.name == "L1"
        assert state_l1.on_during_aspects[1].parent.path == ("L1",)
        assert state_l1.parent_ref is None
        assert state_l1.substate_name_to_id == {"L21": 0, "L22": 1}
        assert state_l1.extra_name is None
        assert not state_l1.is_pseudo
        assert state_l1.abstract_on_during_aspects == []
        assert len(state_l1.abstract_on_durings) == 1
        assert state_l1.abstract_on_durings[0].stage == "during"
        assert state_l1.abstract_on_durings[0].aspect == "after"
        assert state_l1.abstract_on_durings[0].name == "F13"
        assert state_l1.abstract_on_durings[0].doc is None
        assert state_l1.abstract_on_durings[0].operations == []
        assert state_l1.abstract_on_durings[0].is_abstract
        assert state_l1.abstract_on_durings[0].state_path == ("L1", "F13")
        assert state_l1.abstract_on_durings[0].ref is None
        assert state_l1.abstract_on_durings[0].ref_state_path is None
        assert state_l1.abstract_on_durings[0].parent_ref().name == "L1"
        assert state_l1.abstract_on_durings[0].parent_ref().path == ("L1",)
        assert not state_l1.abstract_on_durings[0].is_aspect
        assert not state_l1.abstract_on_durings[0].is_ref
        assert state_l1.abstract_on_durings[0].parent.name == "L1"
        assert state_l1.abstract_on_durings[0].parent.path == ("L1",)
        assert len(state_l1.abstract_on_enters) == 1
        assert state_l1.abstract_on_enters[0].stage == "enter"
        assert state_l1.abstract_on_enters[0].aspect is None
        assert state_l1.abstract_on_enters[0].name == "F1"
        assert state_l1.abstract_on_enters[0].doc is None
        assert state_l1.abstract_on_enters[0].operations == []
        assert state_l1.abstract_on_enters[0].is_abstract
        assert state_l1.abstract_on_enters[0].state_path == ("L1", "F1")
        assert state_l1.abstract_on_enters[0].ref is None
        assert state_l1.abstract_on_enters[0].ref_state_path is None
        assert state_l1.abstract_on_enters[0].parent_ref().name == "L1"
        assert state_l1.abstract_on_enters[0].parent_ref().path == ("L1",)
        assert not state_l1.abstract_on_enters[0].is_aspect
        assert not state_l1.abstract_on_enters[0].is_ref
        assert state_l1.abstract_on_enters[0].parent.name == "L1"
        assert state_l1.abstract_on_enters[0].parent.path == ("L1",)
        assert state_l1.abstract_on_exits == []
        assert len(state_l1.init_transitions) == 1
        assert state_l1.init_transitions[0].from_state == INIT_STATE
        assert state_l1.init_transitions[0].to_state == "L21"
        assert state_l1.init_transitions[0].event is None
        assert state_l1.init_transitions[0].guard is None
        assert state_l1.init_transitions[0].effects == []
        assert state_l1.init_transitions[0].parent_ref().name == "L1"
        assert state_l1.init_transitions[0].parent_ref().path == ("L1",)
        assert not state_l1.is_leaf_state
        assert state_l1.is_root_state
        assert not state_l1.is_stoppable
        assert len(state_l1.non_abstract_on_during_aspects) == 2
        assert state_l1.non_abstract_on_during_aspects[0].stage == "during"
        assert state_l1.non_abstract_on_during_aspects[0].aspect == "before"
        assert state_l1.non_abstract_on_during_aspects[0].name is None
        assert state_l1.non_abstract_on_during_aspects[0].doc is None
        assert state_l1.non_abstract_on_during_aspects[0].operations == []
        assert not state_l1.non_abstract_on_during_aspects[0].is_abstract
        assert state_l1.non_abstract_on_during_aspects[0].state_path == ("L1", None)
        assert state_l1.non_abstract_on_during_aspects[0].ref.name == "F1"
        assert state_l1.non_abstract_on_during_aspects[0].ref.aspect == None
        assert state_l1.non_abstract_on_during_aspects[0].ref.state_path == (
            "L1",
            "L21",
            "F1",
        )
        assert state_l1.non_abstract_on_during_aspects[0].ref_state_path == (
            "L1",
            "L21",
            "F1",
        )
        assert state_l1.non_abstract_on_during_aspects[0].parent_ref().name == "L1"
        assert state_l1.non_abstract_on_during_aspects[0].parent_ref().path == ("L1",)
        assert state_l1.non_abstract_on_during_aspects[0].is_aspect
        assert state_l1.non_abstract_on_during_aspects[0].is_ref
        assert state_l1.non_abstract_on_during_aspects[0].parent.name == "L1"
        assert state_l1.non_abstract_on_during_aspects[0].parent.path == ("L1",)
        assert state_l1.non_abstract_on_during_aspects[1].stage == "during"
        assert state_l1.non_abstract_on_during_aspects[1].aspect == "after"
        assert state_l1.non_abstract_on_during_aspects[1].name is None
        assert state_l1.non_abstract_on_during_aspects[1].doc is None
        assert state_l1.non_abstract_on_during_aspects[1].operations == []
        assert not state_l1.non_abstract_on_during_aspects[1].is_abstract
        assert state_l1.non_abstract_on_during_aspects[1].state_path == ("L1", None)
        assert state_l1.non_abstract_on_during_aspects[1].ref.name == "F1"
        assert state_l1.non_abstract_on_during_aspects[1].ref.aspect == None
        assert state_l1.non_abstract_on_during_aspects[1].ref.state_path == (
            "L1",
            "L22",
            "F1",
        )
        assert state_l1.non_abstract_on_during_aspects[1].ref_state_path == (
            "L1",
            "L22",
            "F1",
        )
        assert state_l1.non_abstract_on_during_aspects[1].parent_ref().name == "L1"
        assert state_l1.non_abstract_on_during_aspects[1].parent_ref().path == ("L1",)
        assert state_l1.non_abstract_on_during_aspects[1].is_aspect
        assert state_l1.non_abstract_on_during_aspects[1].is_ref
        assert state_l1.non_abstract_on_during_aspects[1].parent.name == "L1"
        assert state_l1.non_abstract_on_during_aspects[1].parent.path == ("L1",)
        assert len(state_l1.non_abstract_on_durings) == 1
        assert state_l1.non_abstract_on_durings[0].stage == "during"
        assert state_l1.non_abstract_on_durings[0].aspect == "before"
        assert state_l1.non_abstract_on_durings[0].name == "F12"
        assert state_l1.non_abstract_on_durings[0].doc is None
        assert state_l1.non_abstract_on_durings[0].operations == [
            Operation(var_name="x", expr=Integer(value=1))
        ]
        assert not state_l1.non_abstract_on_durings[0].is_abstract
        assert state_l1.non_abstract_on_durings[0].state_path == ("L1", "F12")
        assert state_l1.non_abstract_on_durings[0].ref is None
        assert state_l1.non_abstract_on_durings[0].ref_state_path is None
        assert state_l1.non_abstract_on_durings[0].parent_ref().name == "L1"
        assert state_l1.non_abstract_on_durings[0].parent_ref().path == ("L1",)
        assert not state_l1.non_abstract_on_durings[0].is_aspect
        assert not state_l1.non_abstract_on_durings[0].is_ref
        assert state_l1.non_abstract_on_durings[0].parent.name == "L1"
        assert state_l1.non_abstract_on_durings[0].parent.path == ("L1",)
        assert state_l1.non_abstract_on_enters == []
        assert len(state_l1.non_abstract_on_exits) == 1
        assert state_l1.non_abstract_on_exits[0].stage == "exit"
        assert state_l1.non_abstract_on_exits[0].aspect is None
        assert state_l1.non_abstract_on_exits[0].name == "F1x"
        assert state_l1.non_abstract_on_exits[0].doc is None
        assert state_l1.non_abstract_on_exits[0].operations == []
        assert not state_l1.non_abstract_on_exits[0].is_abstract
        assert state_l1.non_abstract_on_exits[0].state_path == ("L1", "F1x")
        assert state_l1.non_abstract_on_exits[0].ref.name == "F1"
        assert state_l1.non_abstract_on_exits[0].ref.aspect == None
        assert state_l1.non_abstract_on_exits[0].ref.state_path == ("L1", "F1")
        assert state_l1.non_abstract_on_exits[0].ref_state_path == ("L1", "F1")
        assert state_l1.non_abstract_on_exits[0].parent_ref().name == "L1"
        assert state_l1.non_abstract_on_exits[0].parent_ref().path == ("L1",)
        assert not state_l1.non_abstract_on_exits[0].is_aspect
        assert state_l1.non_abstract_on_exits[0].is_ref
        assert state_l1.non_abstract_on_exits[0].parent.name == "L1"
        assert state_l1.non_abstract_on_exits[0].parent.path == ("L1",)
        assert state_l1.parent is None
        assert len(state_l1.transitions_entering_children) == 1
        assert state_l1.transitions_entering_children[0].from_state == INIT_STATE
        assert state_l1.transitions_entering_children[0].to_state == "L21"
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
        assert state_l1.transitions_entering_children_simplified[0].to_state == "L21"
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
            extra_name=None,
            events=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="L21",
                    extra_name=None,
                    events=[],
                    substates=[],
                    transitions=[],
                    enters=[
                        dsl_nodes.EnterOperations(
                            operations=[
                                dsl_nodes.OperationAssignment(
                                    name="x", expr=dsl_nodes.Integer(raw="0")
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="y",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="y"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
                            ],
                            name="F1",
                        )
                    ],
                    durings=[],
                    exits=[
                        dsl_nodes.ExitRefFunction(
                            name=None,
                            ref=dsl_nodes.ChainID(path=["F1x"], is_absolute=True),
                        )
                    ],
                    during_aspects=[
                        dsl_nodes.DuringAspectRefFunction(
                            name=None,
                            aspect="after",
                            ref=dsl_nodes.ChainID(path=["F1x"], is_absolute=True),
                        )
                    ],
                    force_transitions=[],
                    is_pseudo=False,
                ),
                dsl_nodes.StateDefinition(
                    name="L22",
                    extra_name=None,
                    events=[],
                    substates=[],
                    transitions=[],
                    enters=[
                        dsl_nodes.EnterRefFunction(
                            name=None,
                            ref=dsl_nodes.ChainID(path=["F1x"], is_absolute=True),
                        )
                    ],
                    durings=[
                        dsl_nodes.DuringRefFunction(
                            name=None,
                            aspect=None,
                            ref=dsl_nodes.ChainID(path=["F1x"], is_absolute=True),
                        ),
                        dsl_nodes.DuringRefFunction(
                            name=None,
                            aspect=None,
                            ref=dsl_nodes.ChainID(path=["F1"], is_absolute=False),
                        ),
                    ],
                    exits=[
                        dsl_nodes.ExitOperations(
                            operations=[
                                dsl_nodes.OperationAssignment(
                                    name="x",
                                    expr=dsl_nodes.BinaryOp(
                                        expr1=dsl_nodes.Name(name="x"),
                                        op="+",
                                        expr2=dsl_nodes.Integer(raw="1"),
                                    ),
                                ),
                                dsl_nodes.OperationAssignment(
                                    name="y", expr=dsl_nodes.Integer(raw="0")
                                ),
                            ],
                            name="F1",
                        ),
                        dsl_nodes.ExitRefFunction(
                            name=None,
                            ref=dsl_nodes.ChainID(path=["F1"], is_absolute=True),
                        ),
                    ],
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
                    event_id=None,
                    condition_expr=dsl_nodes.BinaryOp(
                        expr1=dsl_nodes.Name(name="x"),
                        op=">",
                        expr2=dsl_nodes.Integer(raw="0"),
                    ),
                    post_operations=[],
                ),
            ],
            enters=[dsl_nodes.EnterAbstractFunction(name="F1", doc=None)],
            durings=[
                dsl_nodes.DuringOperations(
                    aspect="before",
                    operations=[
                        dsl_nodes.OperationAssignment(
                            name="x", expr=dsl_nodes.Integer(raw="1")
                        )
                    ],
                    name="F12",
                ),
                dsl_nodes.DuringAbstractFunction(name="F13", aspect="after", doc=None),
            ],
            exits=[
                dsl_nodes.ExitRefFunction(
                    name="F1x", ref=dsl_nodes.ChainID(path=["F1"], is_absolute=False)
                )
            ],
            during_aspects=[
                dsl_nodes.DuringAspectRefFunction(
                    name=None,
                    aspect="before",
                    ref=dsl_nodes.ChainID(path=["L21", "F1"], is_absolute=False),
                ),
                dsl_nodes.DuringAspectRefFunction(
                    name=None,
                    aspect="after",
                    ref=dsl_nodes.ChainID(path=["L22", "F1"], is_absolute=False),
                ),
            ],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_l1_list_on_enters(self, state_l1):
        lst = state_l1.list_on_enters()
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("L1", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_enters(with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("L1", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_enters(with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("L1", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_enters(is_abstract=False)
        assert lst == []

        lst = state_l1.list_on_enters(is_abstract=False, with_ids=False)
        assert lst == []

        lst = state_l1.list_on_enters(is_abstract=False, with_ids=True)
        assert lst == []

        lst = state_l1.list_on_enters(is_abstract=True)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("L1", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_enters(is_abstract=True, with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("L1", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_enters(is_abstract=True, with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert on_stage.is_abstract
        assert on_stage.state_path == ("L1", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

    def test_state_l1_during_aspects(self, state_l1):
        lst = state_l1.list_on_during_aspects()
        assert len(lst) == 2
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L21", "F1")
        assert on_stage.ref_state_path == ("L1", "L21", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)
        on_stage = lst[1]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_during_aspects(aspect="before")
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L21", "F1")
        assert on_stage.ref_state_path == ("L1", "L21", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_during_aspects(aspect="after")
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_during_aspects(is_abstract=False)
        assert len(lst) == 2
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L21", "F1")
        assert on_stage.ref_state_path == ("L1", "L21", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)
        on_stage = lst[1]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_during_aspects(is_abstract=False, aspect="before")
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L21", "F1")
        assert on_stage.ref_state_path == ("L1", "L21", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_during_aspects(is_abstract=False, aspect="after")
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_l1.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_l1_l21(self, state_l1_l21):
        assert state_l1_l21.name == "L21"
        assert state_l1_l21.path == ("L1", "L21")
        assert sorted(state_l1_l21.substates.keys()) == []
        assert state_l1_l21.events == {}
        assert state_l1_l21.transitions == []
        assert sorted(state_l1_l21.named_functions.keys()) == ["F1"]
        assert state_l1_l21.named_functions["F1"].stage == "enter"
        assert state_l1_l21.named_functions["F1"].aspect is None
        assert state_l1_l21.named_functions["F1"].name == "F1"
        assert state_l1_l21.named_functions["F1"].doc is None
        assert state_l1_l21.named_functions["F1"].operations == [
            Operation(var_name="x", expr=Integer(value=0)),
            Operation(
                var_name="y",
                expr=BinaryOp(x=Variable(name="y"), op="+", y=Integer(value=1)),
            ),
        ]
        assert not state_l1_l21.named_functions["F1"].is_abstract
        assert state_l1_l21.named_functions["F1"].state_path == ("L1", "L21", "F1")
        assert state_l1_l21.named_functions["F1"].ref is None
        assert state_l1_l21.named_functions["F1"].ref_state_path is None
        assert state_l1_l21.named_functions["F1"].parent_ref().name == "L21"
        assert state_l1_l21.named_functions["F1"].parent_ref().path == ("L1", "L21")
        assert not state_l1_l21.named_functions["F1"].is_aspect
        assert not state_l1_l21.named_functions["F1"].is_ref
        assert state_l1_l21.named_functions["F1"].parent.name == "L21"
        assert state_l1_l21.named_functions["F1"].parent.path == ("L1", "L21")
        assert len(state_l1_l21.on_enters) == 1
        assert state_l1_l21.on_enters[0].stage == "enter"
        assert state_l1_l21.on_enters[0].aspect is None
        assert state_l1_l21.on_enters[0].name == "F1"
        assert state_l1_l21.on_enters[0].doc is None
        assert state_l1_l21.on_enters[0].operations == [
            Operation(var_name="x", expr=Integer(value=0)),
            Operation(
                var_name="y",
                expr=BinaryOp(x=Variable(name="y"), op="+", y=Integer(value=1)),
            ),
        ]
        assert not state_l1_l21.on_enters[0].is_abstract
        assert state_l1_l21.on_enters[0].state_path == ("L1", "L21", "F1")
        assert state_l1_l21.on_enters[0].ref is None
        assert state_l1_l21.on_enters[0].ref_state_path is None
        assert state_l1_l21.on_enters[0].parent_ref().name == "L21"
        assert state_l1_l21.on_enters[0].parent_ref().path == ("L1", "L21")
        assert not state_l1_l21.on_enters[0].is_aspect
        assert not state_l1_l21.on_enters[0].is_ref
        assert state_l1_l21.on_enters[0].parent.name == "L21"
        assert state_l1_l21.on_enters[0].parent.path == ("L1", "L21")
        assert state_l1_l21.on_durings == []
        assert len(state_l1_l21.on_exits) == 1
        assert state_l1_l21.on_exits[0].stage == "exit"
        assert state_l1_l21.on_exits[0].aspect is None
        assert state_l1_l21.on_exits[0].name is None
        assert state_l1_l21.on_exits[0].doc is None
        assert state_l1_l21.on_exits[0].operations == []
        assert not state_l1_l21.on_exits[0].is_abstract
        assert state_l1_l21.on_exits[0].state_path == ("L1", "L21", None)
        assert state_l1_l21.on_exits[0].ref.name == "F1x"
        assert state_l1_l21.on_exits[0].ref.aspect == None
        assert state_l1_l21.on_exits[0].ref.state_path == ("L1", "F1x")
        assert state_l1_l21.on_exits[0].ref_state_path == ("L1", "F1x")
        assert state_l1_l21.on_exits[0].parent_ref().name == "L21"
        assert state_l1_l21.on_exits[0].parent_ref().path == ("L1", "L21")
        assert not state_l1_l21.on_exits[0].is_aspect
        assert state_l1_l21.on_exits[0].is_ref
        assert state_l1_l21.on_exits[0].parent.name == "L21"
        assert state_l1_l21.on_exits[0].parent.path == ("L1", "L21")
        assert len(state_l1_l21.on_during_aspects) == 1
        assert state_l1_l21.on_during_aspects[0].stage == "during"
        assert state_l1_l21.on_during_aspects[0].aspect == "after"
        assert state_l1_l21.on_during_aspects[0].name is None
        assert state_l1_l21.on_during_aspects[0].doc is None
        assert state_l1_l21.on_during_aspects[0].operations == []
        assert not state_l1_l21.on_during_aspects[0].is_abstract
        assert state_l1_l21.on_during_aspects[0].state_path == ("L1", "L21", None)
        assert state_l1_l21.on_during_aspects[0].ref.name == "F1x"
        assert state_l1_l21.on_during_aspects[0].ref.aspect == None
        assert state_l1_l21.on_during_aspects[0].ref.state_path == ("L1", "F1x")
        assert state_l1_l21.on_during_aspects[0].ref_state_path == ("L1", "F1x")
        assert state_l1_l21.on_during_aspects[0].parent_ref().name == "L21"
        assert state_l1_l21.on_during_aspects[0].parent_ref().path == ("L1", "L21")
        assert state_l1_l21.on_during_aspects[0].is_aspect
        assert state_l1_l21.on_during_aspects[0].is_ref
        assert state_l1_l21.on_during_aspects[0].parent.name == "L21"
        assert state_l1_l21.on_during_aspects[0].parent.path == ("L1", "L21")
        assert state_l1_l21.parent_ref().name == "L1"
        assert state_l1_l21.parent_ref().path == ("L1",)
        assert state_l1_l21.substate_name_to_id == {}
        assert state_l1_l21.extra_name is None
        assert not state_l1_l21.is_pseudo
        assert state_l1_l21.abstract_on_during_aspects == []
        assert state_l1_l21.abstract_on_durings == []
        assert state_l1_l21.abstract_on_enters == []
        assert state_l1_l21.abstract_on_exits == []
        assert state_l1_l21.init_transitions == []
        assert state_l1_l21.is_leaf_state
        assert not state_l1_l21.is_root_state
        assert state_l1_l21.is_stoppable
        assert len(state_l1_l21.non_abstract_on_during_aspects) == 1
        assert state_l1_l21.non_abstract_on_during_aspects[0].stage == "during"
        assert state_l1_l21.non_abstract_on_during_aspects[0].aspect == "after"
        assert state_l1_l21.non_abstract_on_during_aspects[0].name is None
        assert state_l1_l21.non_abstract_on_during_aspects[0].doc is None
        assert state_l1_l21.non_abstract_on_during_aspects[0].operations == []
        assert not state_l1_l21.non_abstract_on_during_aspects[0].is_abstract
        assert state_l1_l21.non_abstract_on_during_aspects[0].state_path == (
            "L1",
            "L21",
            None,
        )
        assert state_l1_l21.non_abstract_on_during_aspects[0].ref.name == "F1x"
        assert state_l1_l21.non_abstract_on_during_aspects[0].ref.aspect == None
        assert state_l1_l21.non_abstract_on_during_aspects[0].ref.state_path == (
            "L1",
            "F1x",
        )
        assert state_l1_l21.non_abstract_on_during_aspects[0].ref_state_path == (
            "L1",
            "F1x",
        )
        assert state_l1_l21.non_abstract_on_during_aspects[0].parent_ref().name == "L21"
        assert state_l1_l21.non_abstract_on_during_aspects[0].parent_ref().path == (
            "L1",
            "L21",
        )
        assert state_l1_l21.non_abstract_on_during_aspects[0].is_aspect
        assert state_l1_l21.non_abstract_on_during_aspects[0].is_ref
        assert state_l1_l21.non_abstract_on_during_aspects[0].parent.name == "L21"
        assert state_l1_l21.non_abstract_on_during_aspects[0].parent.path == (
            "L1",
            "L21",
        )
        assert state_l1_l21.non_abstract_on_durings == []
        assert len(state_l1_l21.non_abstract_on_enters) == 1
        assert state_l1_l21.non_abstract_on_enters[0].stage == "enter"
        assert state_l1_l21.non_abstract_on_enters[0].aspect is None
        assert state_l1_l21.non_abstract_on_enters[0].name == "F1"
        assert state_l1_l21.non_abstract_on_enters[0].doc is None
        assert state_l1_l21.non_abstract_on_enters[0].operations == [
            Operation(var_name="x", expr=Integer(value=0)),
            Operation(
                var_name="y",
                expr=BinaryOp(x=Variable(name="y"), op="+", y=Integer(value=1)),
            ),
        ]
        assert not state_l1_l21.non_abstract_on_enters[0].is_abstract
        assert state_l1_l21.non_abstract_on_enters[0].state_path == ("L1", "L21", "F1")
        assert state_l1_l21.non_abstract_on_enters[0].ref is None
        assert state_l1_l21.non_abstract_on_enters[0].ref_state_path is None
        assert state_l1_l21.non_abstract_on_enters[0].parent_ref().name == "L21"
        assert state_l1_l21.non_abstract_on_enters[0].parent_ref().path == ("L1", "L21")
        assert not state_l1_l21.non_abstract_on_enters[0].is_aspect
        assert not state_l1_l21.non_abstract_on_enters[0].is_ref
        assert state_l1_l21.non_abstract_on_enters[0].parent.name == "L21"
        assert state_l1_l21.non_abstract_on_enters[0].parent.path == ("L1", "L21")
        assert len(state_l1_l21.non_abstract_on_exits) == 1
        assert state_l1_l21.non_abstract_on_exits[0].stage == "exit"
        assert state_l1_l21.non_abstract_on_exits[0].aspect is None
        assert state_l1_l21.non_abstract_on_exits[0].name is None
        assert state_l1_l21.non_abstract_on_exits[0].doc is None
        assert state_l1_l21.non_abstract_on_exits[0].operations == []
        assert not state_l1_l21.non_abstract_on_exits[0].is_abstract
        assert state_l1_l21.non_abstract_on_exits[0].state_path == ("L1", "L21", None)
        assert state_l1_l21.non_abstract_on_exits[0].ref.name == "F1x"
        assert state_l1_l21.non_abstract_on_exits[0].ref.aspect == None
        assert state_l1_l21.non_abstract_on_exits[0].ref.state_path == ("L1", "F1x")
        assert state_l1_l21.non_abstract_on_exits[0].ref_state_path == ("L1", "F1x")
        assert state_l1_l21.non_abstract_on_exits[0].parent_ref().name == "L21"
        assert state_l1_l21.non_abstract_on_exits[0].parent_ref().path == ("L1", "L21")
        assert not state_l1_l21.non_abstract_on_exits[0].is_aspect
        assert state_l1_l21.non_abstract_on_exits[0].is_ref
        assert state_l1_l21.non_abstract_on_exits[0].parent.name == "L21"
        assert state_l1_l21.non_abstract_on_exits[0].parent.path == ("L1", "L21")
        assert state_l1_l21.parent.name == "L1"
        assert state_l1_l21.parent.path == ("L1",)
        assert state_l1_l21.transitions_entering_children == []
        assert len(state_l1_l21.transitions_entering_children_simplified) == 1
        assert state_l1_l21.transitions_entering_children_simplified[0] is None
        assert len(state_l1_l21.transitions_from) == 1
        assert state_l1_l21.transitions_from[0].from_state == "L21"
        assert state_l1_l21.transitions_from[0].to_state == "L22"
        assert state_l1_l21.transitions_from[0].event is None
        assert state_l1_l21.transitions_from[0].guard == BinaryOp(
            x=Variable(name="x"), op=">", y=Integer(value=0)
        )
        assert state_l1_l21.transitions_from[0].effects == []
        assert state_l1_l21.transitions_from[0].parent_ref().name == "L1"
        assert state_l1_l21.transitions_from[0].parent_ref().path == ("L1",)
        assert len(state_l1_l21.transitions_to) == 1
        assert state_l1_l21.transitions_to[0].from_state == INIT_STATE
        assert state_l1_l21.transitions_to[0].to_state == "L21"
        assert state_l1_l21.transitions_to[0].event is None
        assert state_l1_l21.transitions_to[0].guard is None
        assert state_l1_l21.transitions_to[0].effects == []
        assert state_l1_l21.transitions_to[0].parent_ref().name == "L1"
        assert state_l1_l21.transitions_to[0].parent_ref().path == ("L1",)

    def test_state_l1_l21_to_ast_node(self, state_l1_l21):
        ast_node = state_l1_l21.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L21",
            extra_name=None,
            events=[],
            substates=[],
            transitions=[],
            enters=[
                dsl_nodes.EnterOperations(
                    operations=[
                        dsl_nodes.OperationAssignment(
                            name="x", expr=dsl_nodes.Integer(raw="0")
                        ),
                        dsl_nodes.OperationAssignment(
                            name="y",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="y"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
                    ],
                    name="F1",
                )
            ],
            durings=[],
            exits=[
                dsl_nodes.ExitRefFunction(
                    name=None, ref=dsl_nodes.ChainID(path=["F1x"], is_absolute=True)
                )
            ],
            during_aspects=[
                dsl_nodes.DuringAspectRefFunction(
                    name=None,
                    aspect="after",
                    ref=dsl_nodes.ChainID(path=["F1x"], is_absolute=True),
                )
            ],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_l1_l21_list_on_enters(self, state_l1_l21):
        lst = state_l1_l21.list_on_enters()
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="x", expr=Integer(value=0)),
            Operation(
                var_name="y",
                expr=BinaryOp(x=Variable(name="y"), op="+", y=Integer(value=1)),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_enters(with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="x", expr=Integer(value=0)),
            Operation(
                var_name="y",
                expr=BinaryOp(x=Variable(name="y"), op="+", y=Integer(value=1)),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_enters(with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="x", expr=Integer(value=0)),
            Operation(
                var_name="y",
                expr=BinaryOp(x=Variable(name="y"), op="+", y=Integer(value=1)),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_enters(is_abstract=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="x", expr=Integer(value=0)),
            Operation(
                var_name="y",
                expr=BinaryOp(x=Variable(name="y"), op="+", y=Integer(value=1)),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_enters(is_abstract=False, with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="x", expr=Integer(value=0)),
            Operation(
                var_name="y",
                expr=BinaryOp(x=Variable(name="y"), op="+", y=Integer(value=1)),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_enters(is_abstract=False, with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name == "F1"
        assert on_stage.doc is None
        assert on_stage.operations == [
            Operation(var_name="x", expr=Integer(value=0)),
            Operation(
                var_name="y",
                expr=BinaryOp(x=Variable(name="y"), op="+", y=Integer(value=1)),
            ),
        ]
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", "F1")
        assert on_stage.ref is None
        assert on_stage.ref_state_path is None
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert not on_stage.is_aspect
        assert not on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l21.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l21.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l21_during_aspects(self, state_l1_l21):
        lst = state_l1_l21.list_on_during_aspects()
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l21.list_on_during_aspects(aspect="after")
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_during_aspects(is_abstract=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_l1_l21.list_on_during_aspects(is_abstract=False, aspect="after")
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")

        lst = state_l1_l21.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l21.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_l1_l21.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_l1_l21_during_aspect_recursively(self, state_l1_l21):
        lst = state_l1_l21.list_on_during_aspect_recursively()
        assert len(lst) == 3
        st, on_stage = lst[0]
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L21", "F1")
        assert on_stage.ref_state_path == ("L1", "L21", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)
        st, on_stage = lst[1]
        assert st.name == "L21"
        assert st.path == ("L1", "L21")
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")
        st, on_stage = lst[2]
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1_l21.list_on_during_aspect_recursively(with_ids=True)
        assert len(lst) == 3
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L21", "F1")
        assert on_stage.ref_state_path == ("L1", "L21", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)
        id_, st, on_stage = lst[1]
        assert id_ == 1
        assert st.name == "L21"
        assert st.path == ("L1", "L21")
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L21", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L21"
        assert on_stage.parent_ref().path == ("L1", "L21")
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L21"
        assert on_stage.parent.path == ("L1", "L21")
        id_, st, on_stage = lst[2]
        assert id_ == 2
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

    def test_state_l1_l22(self, state_l1_l22):
        assert state_l1_l22.name == "L22"
        assert state_l1_l22.path == ("L1", "L22")
        assert sorted(state_l1_l22.substates.keys()) == []
        assert state_l1_l22.events == {}
        assert state_l1_l22.transitions == []
        assert sorted(state_l1_l22.named_functions.keys()) == ["F1"]
        assert state_l1_l22.named_functions["F1"].stage == "exit"
        assert state_l1_l22.named_functions["F1"].aspect is None
        assert state_l1_l22.named_functions["F1"].name == "F1"
        assert state_l1_l22.named_functions["F1"].doc is None
        assert state_l1_l22.named_functions["F1"].operations == [
            Operation(
                var_name="x",
                expr=BinaryOp(x=Variable(name="x"), op="+", y=Integer(value=1)),
            ),
            Operation(var_name="y", expr=Integer(value=0)),
        ]
        assert not state_l1_l22.named_functions["F1"].is_abstract
        assert state_l1_l22.named_functions["F1"].state_path == ("L1", "L22", "F1")
        assert state_l1_l22.named_functions["F1"].ref is None
        assert state_l1_l22.named_functions["F1"].ref_state_path is None
        assert state_l1_l22.named_functions["F1"].parent_ref().name == "L22"
        assert state_l1_l22.named_functions["F1"].parent_ref().path == ("L1", "L22")
        assert not state_l1_l22.named_functions["F1"].is_aspect
        assert not state_l1_l22.named_functions["F1"].is_ref
        assert state_l1_l22.named_functions["F1"].parent.name == "L22"
        assert state_l1_l22.named_functions["F1"].parent.path == ("L1", "L22")
        assert len(state_l1_l22.on_enters) == 1
        assert state_l1_l22.on_enters[0].stage == "enter"
        assert state_l1_l22.on_enters[0].aspect is None
        assert state_l1_l22.on_enters[0].name is None
        assert state_l1_l22.on_enters[0].doc is None
        assert state_l1_l22.on_enters[0].operations == []
        assert not state_l1_l22.on_enters[0].is_abstract
        assert state_l1_l22.on_enters[0].state_path == ("L1", "L22", None)
        assert state_l1_l22.on_enters[0].ref.name == "F1x"
        assert state_l1_l22.on_enters[0].ref.aspect == None
        assert state_l1_l22.on_enters[0].ref.state_path == ("L1", "F1x")
        assert state_l1_l22.on_enters[0].ref_state_path == ("L1", "F1x")
        assert state_l1_l22.on_enters[0].parent_ref().name == "L22"
        assert state_l1_l22.on_enters[0].parent_ref().path == ("L1", "L22")
        assert not state_l1_l22.on_enters[0].is_aspect
        assert state_l1_l22.on_enters[0].is_ref
        assert state_l1_l22.on_enters[0].parent.name == "L22"
        assert state_l1_l22.on_enters[0].parent.path == ("L1", "L22")
        assert len(state_l1_l22.on_durings) == 2
        assert state_l1_l22.on_durings[0].stage == "during"
        assert state_l1_l22.on_durings[0].aspect is None
        assert state_l1_l22.on_durings[0].name is None
        assert state_l1_l22.on_durings[0].doc is None
        assert state_l1_l22.on_durings[0].operations == []
        assert not state_l1_l22.on_durings[0].is_abstract
        assert state_l1_l22.on_durings[0].state_path == ("L1", "L22", None)
        assert state_l1_l22.on_durings[0].ref.name == "F1x"
        assert state_l1_l22.on_durings[0].ref.aspect == None
        assert state_l1_l22.on_durings[0].ref.state_path == ("L1", "F1x")
        assert state_l1_l22.on_durings[0].ref_state_path == ("L1", "F1x")
        assert state_l1_l22.on_durings[0].parent_ref().name == "L22"
        assert state_l1_l22.on_durings[0].parent_ref().path == ("L1", "L22")
        assert not state_l1_l22.on_durings[0].is_aspect
        assert state_l1_l22.on_durings[0].is_ref
        assert state_l1_l22.on_durings[0].parent.name == "L22"
        assert state_l1_l22.on_durings[0].parent.path == ("L1", "L22")
        assert state_l1_l22.on_durings[1].stage == "during"
        assert state_l1_l22.on_durings[1].aspect is None
        assert state_l1_l22.on_durings[1].name is None
        assert state_l1_l22.on_durings[1].doc is None
        assert state_l1_l22.on_durings[1].operations == []
        assert not state_l1_l22.on_durings[1].is_abstract
        assert state_l1_l22.on_durings[1].state_path == ("L1", "L22", None)
        assert state_l1_l22.on_durings[1].ref.name == "F1"
        assert state_l1_l22.on_durings[1].ref.aspect == None
        assert state_l1_l22.on_durings[1].ref.state_path == ("L1", "L22", "F1")
        assert state_l1_l22.on_durings[1].ref_state_path == ("L1", "L22", "F1")
        assert state_l1_l22.on_durings[1].parent_ref().name == "L22"
        assert state_l1_l22.on_durings[1].parent_ref().path == ("L1", "L22")
        assert not state_l1_l22.on_durings[1].is_aspect
        assert state_l1_l22.on_durings[1].is_ref
        assert state_l1_l22.on_durings[1].parent.name == "L22"
        assert state_l1_l22.on_durings[1].parent.path == ("L1", "L22")
        assert len(state_l1_l22.on_exits) == 2
        assert state_l1_l22.on_exits[0].stage == "exit"
        assert state_l1_l22.on_exits[0].aspect is None
        assert state_l1_l22.on_exits[0].name == "F1"
        assert state_l1_l22.on_exits[0].doc is None
        assert state_l1_l22.on_exits[0].operations == [
            Operation(
                var_name="x",
                expr=BinaryOp(x=Variable(name="x"), op="+", y=Integer(value=1)),
            ),
            Operation(var_name="y", expr=Integer(value=0)),
        ]
        assert not state_l1_l22.on_exits[0].is_abstract
        assert state_l1_l22.on_exits[0].state_path == ("L1", "L22", "F1")
        assert state_l1_l22.on_exits[0].ref is None
        assert state_l1_l22.on_exits[0].ref_state_path is None
        assert state_l1_l22.on_exits[0].parent_ref().name == "L22"
        assert state_l1_l22.on_exits[0].parent_ref().path == ("L1", "L22")
        assert not state_l1_l22.on_exits[0].is_aspect
        assert not state_l1_l22.on_exits[0].is_ref
        assert state_l1_l22.on_exits[0].parent.name == "L22"
        assert state_l1_l22.on_exits[0].parent.path == ("L1", "L22")
        assert state_l1_l22.on_exits[1].stage == "exit"
        assert state_l1_l22.on_exits[1].aspect is None
        assert state_l1_l22.on_exits[1].name is None
        assert state_l1_l22.on_exits[1].doc is None
        assert state_l1_l22.on_exits[1].operations == []
        assert not state_l1_l22.on_exits[1].is_abstract
        assert state_l1_l22.on_exits[1].state_path == ("L1", "L22", None)
        assert state_l1_l22.on_exits[1].ref.name == "F1"
        assert state_l1_l22.on_exits[1].ref.aspect == None
        assert state_l1_l22.on_exits[1].ref.state_path == ("L1", "F1")
        assert state_l1_l22.on_exits[1].ref_state_path == ("L1", "F1")
        assert state_l1_l22.on_exits[1].parent_ref().name == "L22"
        assert state_l1_l22.on_exits[1].parent_ref().path == ("L1", "L22")
        assert not state_l1_l22.on_exits[1].is_aspect
        assert state_l1_l22.on_exits[1].is_ref
        assert state_l1_l22.on_exits[1].parent.name == "L22"
        assert state_l1_l22.on_exits[1].parent.path == ("L1", "L22")
        assert state_l1_l22.on_during_aspects == []
        assert state_l1_l22.parent_ref().name == "L1"
        assert state_l1_l22.parent_ref().path == ("L1",)
        assert state_l1_l22.substate_name_to_id == {}
        assert state_l1_l22.extra_name is None
        assert not state_l1_l22.is_pseudo
        assert state_l1_l22.abstract_on_during_aspects == []
        assert state_l1_l22.abstract_on_durings == []
        assert state_l1_l22.abstract_on_enters == []
        assert state_l1_l22.abstract_on_exits == []
        assert state_l1_l22.init_transitions == []
        assert state_l1_l22.is_leaf_state
        assert not state_l1_l22.is_root_state
        assert state_l1_l22.is_stoppable
        assert state_l1_l22.non_abstract_on_during_aspects == []
        assert len(state_l1_l22.non_abstract_on_durings) == 2
        assert state_l1_l22.non_abstract_on_durings[0].stage == "during"
        assert state_l1_l22.non_abstract_on_durings[0].aspect is None
        assert state_l1_l22.non_abstract_on_durings[0].name is None
        assert state_l1_l22.non_abstract_on_durings[0].doc is None
        assert state_l1_l22.non_abstract_on_durings[0].operations == []
        assert not state_l1_l22.non_abstract_on_durings[0].is_abstract
        assert state_l1_l22.non_abstract_on_durings[0].state_path == ("L1", "L22", None)
        assert state_l1_l22.non_abstract_on_durings[0].ref.name == "F1x"
        assert state_l1_l22.non_abstract_on_durings[0].ref.aspect == None
        assert state_l1_l22.non_abstract_on_durings[0].ref.state_path == ("L1", "F1x")
        assert state_l1_l22.non_abstract_on_durings[0].ref_state_path == ("L1", "F1x")
        assert state_l1_l22.non_abstract_on_durings[0].parent_ref().name == "L22"
        assert state_l1_l22.non_abstract_on_durings[0].parent_ref().path == (
            "L1",
            "L22",
        )
        assert not state_l1_l22.non_abstract_on_durings[0].is_aspect
        assert state_l1_l22.non_abstract_on_durings[0].is_ref
        assert state_l1_l22.non_abstract_on_durings[0].parent.name == "L22"
        assert state_l1_l22.non_abstract_on_durings[0].parent.path == ("L1", "L22")
        assert state_l1_l22.non_abstract_on_durings[1].stage == "during"
        assert state_l1_l22.non_abstract_on_durings[1].aspect is None
        assert state_l1_l22.non_abstract_on_durings[1].name is None
        assert state_l1_l22.non_abstract_on_durings[1].doc is None
        assert state_l1_l22.non_abstract_on_durings[1].operations == []
        assert not state_l1_l22.non_abstract_on_durings[1].is_abstract
        assert state_l1_l22.non_abstract_on_durings[1].state_path == ("L1", "L22", None)
        assert state_l1_l22.non_abstract_on_durings[1].ref.name == "F1"
        assert state_l1_l22.non_abstract_on_durings[1].ref.aspect == None
        assert state_l1_l22.non_abstract_on_durings[1].ref.state_path == (
            "L1",
            "L22",
            "F1",
        )
        assert state_l1_l22.non_abstract_on_durings[1].ref_state_path == (
            "L1",
            "L22",
            "F1",
        )
        assert state_l1_l22.non_abstract_on_durings[1].parent_ref().name == "L22"
        assert state_l1_l22.non_abstract_on_durings[1].parent_ref().path == (
            "L1",
            "L22",
        )
        assert not state_l1_l22.non_abstract_on_durings[1].is_aspect
        assert state_l1_l22.non_abstract_on_durings[1].is_ref
        assert state_l1_l22.non_abstract_on_durings[1].parent.name == "L22"
        assert state_l1_l22.non_abstract_on_durings[1].parent.path == ("L1", "L22")
        assert len(state_l1_l22.non_abstract_on_enters) == 1
        assert state_l1_l22.non_abstract_on_enters[0].stage == "enter"
        assert state_l1_l22.non_abstract_on_enters[0].aspect is None
        assert state_l1_l22.non_abstract_on_enters[0].name is None
        assert state_l1_l22.non_abstract_on_enters[0].doc is None
        assert state_l1_l22.non_abstract_on_enters[0].operations == []
        assert not state_l1_l22.non_abstract_on_enters[0].is_abstract
        assert state_l1_l22.non_abstract_on_enters[0].state_path == ("L1", "L22", None)
        assert state_l1_l22.non_abstract_on_enters[0].ref.name == "F1x"
        assert state_l1_l22.non_abstract_on_enters[0].ref.aspect == None
        assert state_l1_l22.non_abstract_on_enters[0].ref.state_path == ("L1", "F1x")
        assert state_l1_l22.non_abstract_on_enters[0].ref_state_path == ("L1", "F1x")
        assert state_l1_l22.non_abstract_on_enters[0].parent_ref().name == "L22"
        assert state_l1_l22.non_abstract_on_enters[0].parent_ref().path == ("L1", "L22")
        assert not state_l1_l22.non_abstract_on_enters[0].is_aspect
        assert state_l1_l22.non_abstract_on_enters[0].is_ref
        assert state_l1_l22.non_abstract_on_enters[0].parent.name == "L22"
        assert state_l1_l22.non_abstract_on_enters[0].parent.path == ("L1", "L22")
        assert len(state_l1_l22.non_abstract_on_exits) == 2
        assert state_l1_l22.non_abstract_on_exits[0].stage == "exit"
        assert state_l1_l22.non_abstract_on_exits[0].aspect is None
        assert state_l1_l22.non_abstract_on_exits[0].name == "F1"
        assert state_l1_l22.non_abstract_on_exits[0].doc is None
        assert state_l1_l22.non_abstract_on_exits[0].operations == [
            Operation(
                var_name="x",
                expr=BinaryOp(x=Variable(name="x"), op="+", y=Integer(value=1)),
            ),
            Operation(var_name="y", expr=Integer(value=0)),
        ]
        assert not state_l1_l22.non_abstract_on_exits[0].is_abstract
        assert state_l1_l22.non_abstract_on_exits[0].state_path == ("L1", "L22", "F1")
        assert state_l1_l22.non_abstract_on_exits[0].ref is None
        assert state_l1_l22.non_abstract_on_exits[0].ref_state_path is None
        assert state_l1_l22.non_abstract_on_exits[0].parent_ref().name == "L22"
        assert state_l1_l22.non_abstract_on_exits[0].parent_ref().path == ("L1", "L22")
        assert not state_l1_l22.non_abstract_on_exits[0].is_aspect
        assert not state_l1_l22.non_abstract_on_exits[0].is_ref
        assert state_l1_l22.non_abstract_on_exits[0].parent.name == "L22"
        assert state_l1_l22.non_abstract_on_exits[0].parent.path == ("L1", "L22")
        assert state_l1_l22.non_abstract_on_exits[1].stage == "exit"
        assert state_l1_l22.non_abstract_on_exits[1].aspect is None
        assert state_l1_l22.non_abstract_on_exits[1].name is None
        assert state_l1_l22.non_abstract_on_exits[1].doc is None
        assert state_l1_l22.non_abstract_on_exits[1].operations == []
        assert not state_l1_l22.non_abstract_on_exits[1].is_abstract
        assert state_l1_l22.non_abstract_on_exits[1].state_path == ("L1", "L22", None)
        assert state_l1_l22.non_abstract_on_exits[1].ref.name == "F1"
        assert state_l1_l22.non_abstract_on_exits[1].ref.aspect == None
        assert state_l1_l22.non_abstract_on_exits[1].ref.state_path == ("L1", "F1")
        assert state_l1_l22.non_abstract_on_exits[1].ref_state_path == ("L1", "F1")
        assert state_l1_l22.non_abstract_on_exits[1].parent_ref().name == "L22"
        assert state_l1_l22.non_abstract_on_exits[1].parent_ref().path == ("L1", "L22")
        assert not state_l1_l22.non_abstract_on_exits[1].is_aspect
        assert state_l1_l22.non_abstract_on_exits[1].is_ref
        assert state_l1_l22.non_abstract_on_exits[1].parent.name == "L22"
        assert state_l1_l22.non_abstract_on_exits[1].parent.path == ("L1", "L22")
        assert state_l1_l22.parent.name == "L1"
        assert state_l1_l22.parent.path == ("L1",)
        assert state_l1_l22.transitions_entering_children == []
        assert len(state_l1_l22.transitions_entering_children_simplified) == 1
        assert state_l1_l22.transitions_entering_children_simplified[0] is None
        assert state_l1_l22.transitions_from == []
        assert len(state_l1_l22.transitions_to) == 1
        assert state_l1_l22.transitions_to[0].from_state == "L21"
        assert state_l1_l22.transitions_to[0].to_state == "L22"
        assert state_l1_l22.transitions_to[0].event is None
        assert state_l1_l22.transitions_to[0].guard == BinaryOp(
            x=Variable(name="x"), op=">", y=Integer(value=0)
        )
        assert state_l1_l22.transitions_to[0].effects == []
        assert state_l1_l22.transitions_to[0].parent_ref().name == "L1"
        assert state_l1_l22.transitions_to[0].parent_ref().path == ("L1",)

    def test_state_l1_l22_to_ast_node(self, state_l1_l22):
        ast_node = state_l1_l22.to_ast_node()
        assert ast_node == dsl_nodes.StateDefinition(
            name="L22",
            extra_name=None,
            events=[],
            substates=[],
            transitions=[],
            enters=[
                dsl_nodes.EnterRefFunction(
                    name=None, ref=dsl_nodes.ChainID(path=["F1x"], is_absolute=True)
                )
            ],
            durings=[
                dsl_nodes.DuringRefFunction(
                    name=None,
                    aspect=None,
                    ref=dsl_nodes.ChainID(path=["F1x"], is_absolute=True),
                ),
                dsl_nodes.DuringRefFunction(
                    name=None,
                    aspect=None,
                    ref=dsl_nodes.ChainID(path=["F1"], is_absolute=False),
                ),
            ],
            exits=[
                dsl_nodes.ExitOperations(
                    operations=[
                        dsl_nodes.OperationAssignment(
                            name="x",
                            expr=dsl_nodes.BinaryOp(
                                expr1=dsl_nodes.Name(name="x"),
                                op="+",
                                expr2=dsl_nodes.Integer(raw="1"),
                            ),
                        ),
                        dsl_nodes.OperationAssignment(
                            name="y", expr=dsl_nodes.Integer(raw="0")
                        ),
                    ],
                    name="F1",
                ),
                dsl_nodes.ExitRefFunction(
                    name=None, ref=dsl_nodes.ChainID(path=["F1"], is_absolute=True)
                ),
            ],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )

    def test_state_l1_l22_list_on_enters(self, state_l1_l22):
        lst = state_l1_l22.list_on_enters()
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")

        lst = state_l1_l22.list_on_enters(with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")

        lst = state_l1_l22.list_on_enters(with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")

        lst = state_l1_l22.list_on_enters(is_abstract=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")

        lst = state_l1_l22.list_on_enters(is_abstract=False, with_ids=False)
        assert len(lst) == 1
        on_stage = lst[0]
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")

        lst = state_l1_l22.list_on_enters(is_abstract=False, with_ids=True)
        assert len(lst) == 1
        id_, on_stage = lst[0]
        assert id_ == 1
        assert on_stage.stage == "enter"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")

        lst = state_l1_l22.list_on_enters(is_abstract=True)
        assert lst == []

        lst = state_l1_l22.list_on_enters(is_abstract=True, with_ids=False)
        assert lst == []

        lst = state_l1_l22.list_on_enters(is_abstract=True, with_ids=True)
        assert lst == []

    def test_state_l1_l22_during_aspects(self, state_l1_l22):
        lst = state_l1_l22.list_on_during_aspects()
        assert lst == []

        lst = state_l1_l22.list_on_during_aspects(aspect="before")
        assert lst == []

        lst = state_l1_l22.list_on_during_aspects(aspect="after")
        assert lst == []

        lst = state_l1_l22.list_on_during_aspects(is_abstract=False)
        assert lst == []

        lst = state_l1_l22.list_on_during_aspects(is_abstract=False, aspect="before")
        assert lst == []

        lst = state_l1_l22.list_on_during_aspects(is_abstract=False, aspect="after")
        assert lst == []

        lst = state_l1_l22.list_on_during_aspects(is_abstract=True)
        assert lst == []

        lst = state_l1_l22.list_on_during_aspects(is_abstract=True, aspect="before")
        assert lst == []

        lst = state_l1_l22.list_on_during_aspects(is_abstract=True, aspect="after")
        assert lst == []

    def test_state_l1_l22_during_aspect_recursively(self, state_l1_l22):
        lst = state_l1_l22.list_on_during_aspect_recursively()
        assert len(lst) == 4
        st, on_stage = lst[0]
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L21", "F1")
        assert on_stage.ref_state_path == ("L1", "L21", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)
        st, on_stage = lst[1]
        assert st.name == "L22"
        assert st.path == ("L1", "L22")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")
        st, on_stage = lst[2]
        assert st.name == "L22"
        assert st.path == ("L1", "L22")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")
        st, on_stage = lst[3]
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

        lst = state_l1_l22.list_on_during_aspect_recursively(with_ids=True)
        assert len(lst) == 4
        id_, st, on_stage = lst[0]
        assert id_ == 1
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "before"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L21", "F1")
        assert on_stage.ref_state_path == ("L1", "L21", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)
        id_, st, on_stage = lst[1]
        assert id_ == 1
        assert st.name == "L22"
        assert st.path == ("L1", "L22")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1x"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "F1x")
        assert on_stage.ref_state_path == ("L1", "F1x")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")
        id_, st, on_stage = lst[2]
        assert id_ == 2
        assert st.name == "L22"
        assert st.path == ("L1", "L22")
        assert on_stage.stage == "during"
        assert on_stage.aspect is None
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", "L22", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L22"
        assert on_stage.parent_ref().path == ("L1", "L22")
        assert not on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L22"
        assert on_stage.parent.path == ("L1", "L22")
        id_, st, on_stage = lst[3]
        assert id_ == 2
        assert st.name == "L1"
        assert st.path == ("L1",)
        assert on_stage.stage == "during"
        assert on_stage.aspect == "after"
        assert on_stage.name is None
        assert on_stage.doc is None
        assert on_stage.operations == []
        assert not on_stage.is_abstract
        assert on_stage.state_path == ("L1", None)
        assert on_stage.ref.name == "F1"
        assert on_stage.ref.aspect == None
        assert on_stage.ref.state_path == ("L1", "L22", "F1")
        assert on_stage.ref_state_path == ("L1", "L22", "F1")
        assert on_stage.parent_ref().name == "L1"
        assert on_stage.parent_ref().path == ("L1",)
        assert on_stage.is_aspect
        assert on_stage.is_ref
        assert on_stage.parent.name == "L1"
        assert on_stage.parent.path == ("L1",)

    def test_to_ast_node_str(self, model, text_aligner):
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
def int x = 0;
def int y = 0;
state L1 {
    enter abstract F1;
    during before F12 {
        x = 1;
    }
    during after abstract F13;
    exit F1x ref F1;
    >> during before ref L21.F1;
    >> during after ref L22.F1;
    state L21 {
        enter F1 {
            x = 0;
            y = y + 1;
        }
        exit ref /F1x;
        >> during after ref /F1x;
    }
    state L22 {
        enter ref /F1x;
        during ref /F1x;
        during ref F1;
        exit F1 {
            x = x + 1;
            y = 0;
        }
        exit ref /F1;
    }
    [*] -> L21;
    L21 -> L22 : if [x > 0];
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
    def int x = 0;
    def int y = 0;
}
end note

state "L1" as l1 {
    state "L21" as l1__l21
    l1__l21 : enter F1 {\\n    x = 0;\\n    y = y + 1;\\n}\\nexit ref /F1x;\\n>> during after ref /F1x;
    state "L22" as l1__l22
    l1__l22 : enter ref /F1x;\\nduring ref /F1x;\\nduring ref F1;\\nexit F1 {\\n    x = x + 1;\\n    y = 0;\\n}\\nexit ref /F1;
    [*] --> l1__l21
    l1__l21 --> l1__l22 : x > 0
}
l1 : enter abstract F1;\\nduring before F12 {\\n    x = 1;\\n}\\nduring after abstract F13;\\nexit F1x ref F1;\\n>> during before ref L21.F1;\\n>> during after ref L22.F1;
[*] --> l1
l1 --> [*]
@enduml
            """).strip(),
            actual=str(model.to_plantuml()),
        )
