import pytest

from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.expr import *
from pyfcstm.model.model import *


@pytest.fixture()
def demo_model_1():
    ast_node = parse_with_grammar_entry(
        """
def int Event  = 0;

state LX
{
    [*] -> LX2;
    !*->ERROR :: E1;

    enter {}
    enter abstract act1;

    state LX2{
        [*] -> start;
         state start {
            [*] -> LX4;
            state LX4 {
                [*] -> LX5;
                state LX5;
            }
         }
    }


    state ERROR 
    {}
    ERROR ->[*];
}
    """,
        entry_name="state_machine_dsl",
    )
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.fixture()
def lx(demo_model_1):
    return demo_model_1.root_state


@pytest.fixture()
def lx2(lx):
    return lx.substates["LX2"]


@pytest.fixture()
def error(lx):
    return lx.substates["ERROR"]


@pytest.fixture()
def start(lx2):
    return lx2.substates["start"]


@pytest.fixture()
def lx4(start):
    return start.substates["LX4"]


@pytest.fixture()
def lx5(lx4):
    return lx4.substates["LX5"]


@pytest.mark.unittest
class TestModelModelDLC3:
    def test_model_basic(self, demo_model_1):
        assert demo_model_1.defines == {
            "Event": VarDefine(name="Event", type="int", init=Integer(value=0)),
        }

        assert demo_model_1.root_state.name == "LX"
        assert demo_model_1.root_state.path == ("LX",)

    def test_model_to_ast_node(self, demo_model_1):
        ast_node = demo_model_1.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(
                name="Event", type="int", expr=dsl_nodes.Integer(raw="0")
            ),
        ]
        assert ast_node.root_state.name == "LX"

    def test_lx_transitions(self, lx):
        lst = lx.transitions
        assert len(lst) == 4
        assert lst[0].from_state == "LX2"
        assert lst[0].to_state == "ERROR"
        assert lst[0].event == Event(name="E1", state_path=("LX",))
        assert lst[0].guard is None
        assert lst[0].effects == []
        assert lst[0].parent is lx

        assert lst[1].from_state == "ERROR"
        assert lst[1].to_state == "ERROR"
        assert lst[1].event == Event(name="E1", state_path=("LX",))
        assert lst[1].guard is None
        assert lst[1].effects == []
        assert lst[1].parent is lx

        assert lst[2].from_state == dsl_nodes.INIT_STATE
        assert lst[2].to_state == "LX2"
        assert lst[2].event is None
        assert lst[2].guard is None
        assert lst[2].effects == []
        assert lst[2].parent is lx

        assert lst[3].from_state == "ERROR"
        assert lst[3].to_state == dsl_nodes.EXIT_STATE
        assert lst[3].event is None
        assert lst[3].guard is None
        assert lst[3].effects == []
        assert lst[3].parent is lx

    def test_lx2_transitions(self, lx2):
        lst = lx2.transitions
        assert len(lst) == 2
        assert lst[0].from_state == "start"
        assert lst[0].to_state == dsl_nodes.EXIT_STATE
        assert lst[0].event == Event(name="E1", state_path=("LX",))
        assert lst[0].guard is None
        assert lst[0].effects == []
        assert lst[0].parent is lx2

        assert lst[1].from_state == dsl_nodes.INIT_STATE
        assert lst[1].to_state == "start"
        assert lst[1].event is None
        assert lst[1].guard is None
        assert lst[1].effects == []
        assert lst[1].parent is lx2

    def test_start_transitions(self, start):
        lst = start.transitions
        assert len(lst) == 2
        assert lst[0].from_state == "LX4"
        assert lst[0].to_state == dsl_nodes.EXIT_STATE
        assert lst[0].event == Event(name="E1", state_path=("LX",))
        assert lst[0].guard is None
        assert lst[0].effects == []
        assert lst[0].parent is start

        assert lst[1].from_state == dsl_nodes.INIT_STATE
        assert lst[1].to_state == "LX4"
        assert lst[1].event is None
        assert lst[1].guard is None
        assert lst[1].effects == []
        assert lst[1].parent is start

    def test_lx4_transitions(self, lx4):
        lst = lx4.transitions
        assert len(lst) == 2
        assert lst[0].from_state == "LX5"
        assert lst[0].to_state == dsl_nodes.EXIT_STATE
        assert lst[0].event == Event(name="E1", state_path=("LX",))
        assert lst[0].guard is None
        assert lst[0].effects == []
        assert lst[0].parent is lx4

        assert lst[1].from_state == dsl_nodes.INIT_STATE
        assert lst[1].to_state == "LX5"
        assert lst[1].event is None
        assert lst[1].guard is None
        assert lst[1].effects == []
        assert lst[1].parent is lx4

    def test_lx5_transitions(self, lx5):
        lst = lx5.transitions
        assert len(lst) == 0
