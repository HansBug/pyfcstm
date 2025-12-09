import textwrap

import pytest

from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.expr import *
from pyfcstm.model.model import *


@pytest.fixture()
def demo_model_1():
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
def root_state_1(demo_model_1):
    return demo_model_1.root_state


@pytest.fixture()
def in_service(root_state_1):
    return root_state_1.substates["InService"]


@pytest.fixture()
def idle(root_state_1):
    return root_state_1.substates["Idle"]


@pytest.fixture()
def red(in_service):
    return in_service.substates["Red"]


@pytest.fixture()
def yellow(in_service):
    return in_service.substates["Yellow"]


@pytest.fixture()
def green(in_service):
    return in_service.substates["Green"]


@pytest.fixture()
def transition_1(root_state_1):
    return root_state_1.transitions[-2]


@pytest.fixture()
def transition_2(in_service):
    return in_service.transitions[-2]


@pytest.fixture()
def transition_3(in_service):
    return in_service.transitions[-1]


@pytest.fixture()
def expected_to_str_result():
    return textwrap.dedent("""
def int a = 0;
def int b = 0;
def int round_count = 0;
state TrafficLight {
    state InService {
        state Red;
        state Yellow;
        state Green;
        event ServiceError;
        event Start;
        event Maintain;
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
        state ToBe {
            event E1;
        }
        state NotToBe {
            event E1;
            event E2;
        }
        event GiveUpThinking;
        event E2;
        ToBe -> [*] : GiveUpThinking;
        ToBe -> [*] : /GodDamnFuckUp;
        NotToBe -> [*] : GiveUpThinking;
        NotToBe -> [*] : /GodDamnFuckUp;
        [*] -> ToBe;
        ToBe -> NotToBe :: E1;
        NotToBe -> ToBe :: E1;
        NotToBe -> [*] :: E2;
    }
    event GodDamnFuckUp;
    event E2;
    InService -> [*] :: ServiceError;
    InService -> [*] : GodDamnFuckUp;
    Idle -> InService :: GiveUpThinking;
    Idle -> [*] : GodDamnFuckUp;
    [*] -> InService;
    InService -> Idle :: Maintain;
    Idle -> Idle :: E2;
    Idle -> [*];
}
    """).strip()


@pytest.mark.unittest
class TestModelModelDLC2:
    def test_model_basic(self, demo_model_1):
        assert demo_model_1.defines == {
            "a": VarDefine(name="a", type="int", init=Integer(value=0)),
            "b": VarDefine(name="b", type="int", init=Integer(value=0)),
            "round_count": VarDefine(
                name="round_count", type="int", init=Integer(value=0)
            ),
        }

        assert demo_model_1.root_state.name == "TrafficLight"
        assert demo_model_1.root_state.path == ("TrafficLight",)

    def test_model_to_ast_node(self, demo_model_1):
        ast_node = demo_model_1.to_ast_node()
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

    def test_transition_dlcs(self, transition_1, transition_2, transition_3):
        assert transition_1.from_state == "Idle"
        assert transition_1.to_state == "Idle"
        assert transition_1.event.name == "E2"
        assert transition_1.event.state_path == ("TrafficLight", "Idle")
        assert transition_1.event.path == ("TrafficLight", "Idle", "E2")

        assert transition_2.from_state == "Green"
        assert transition_2.to_state == "Yellow"
        assert transition_2.event.name == "E2"
        assert transition_2.event.state_path == ("TrafficLight", "Idle")
        assert transition_2.event.path == ("TrafficLight", "Idle", "E2")

        assert transition_3.from_state == "Yellow"
        assert transition_3.to_state == "Yellow"
        assert transition_3.event.name == "E2"
        assert transition_3.event.state_path == ("TrafficLight",)
        assert transition_3.event.path == ("TrafficLight", "E2")

    def test_to_ast_node_to_str(
            self, demo_model_1, expected_to_str_result, text_aligner
    ):
        with open("test_t.txt", "w") as f:
            print(demo_model_1.to_ast_node(), file=f)
        text_aligner.assert_equal(
            expect=expected_to_str_result, actual=str(demo_model_1.to_ast_node())
        )

    def test_parse_unknown_from_state_for_force_transition(self):
        ast_node = parse_with_grammar_entry(
            """
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                >> during before {
                    a = b + a * 2;
                    b = a + 2;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
            ! LX3 -> [*] : E1;
        }
        """,
            entry_name="state_machine_dsl",
        )

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown from state 'LX3' of force transition:" in err.msg
        assert "! LX3 -> [*] : E1;" in err.msg

    def test_parse_unknown_to_state_for_force_transition(self):
        ast_node = parse_with_grammar_entry(
            """
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                >> during before {
                    a = b + a * 2;
                    b = a + 2;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
            ! * -> LX3 : E1;
        }
        """,
            entry_name="state_machine_dsl",
        )

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown to state 'LX3' of force transition:" in err.msg
        assert "! * -> LX3 :: E1;" in err.msg

    def test_parse_unknown_event_parent_state_for_force_transition(self):
        ast_node = parse_with_grammar_entry(
            """
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                >> during before {
                    a = b + a * 2;
                    b = a + 2;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
            ! * -> LX1 : LX3.E1;
        }
        """,
            entry_name="state_machine_dsl",
        )

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Cannot find state LX.LX3 for transition:" in err.msg
        assert "! * -> LX1 : LX3.E1;" in err.msg

    def test_parse_unknown_var_in_condition_for_force_transition(self):
        ast_node = parse_with_grammar_entry(
            """
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                >> during before {
                    a = b + a * 2;
                    b = a + 2;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
            ! * -> LX1 : if [c == 0];
        }
        """,
            entry_name="state_machine_dsl",
        )

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown guard variable c in force transition:" in err.msg
        assert "! * -> LX1 : if [c == 0];" in err.msg

    def test_transitions_for_in_service(self, in_service):
        lst = in_service.transitions
        assert len(lst) == 12
        assert lst[0].from_state == "Red"
        assert lst[0].to_state == dsl_nodes.EXIT_STATE
        assert lst[0].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert lst[0].guard is None
        assert lst[0].effects == []
        assert lst[0].parent is in_service

        assert lst[1].from_state == "Red"
        assert lst[1].to_state == dsl_nodes.EXIT_STATE
        assert lst[1].event == Event(name="GodDamnFuckUp", state_path=("TrafficLight",))
        assert lst[1].guard is None
        assert lst[1].effects == []
        assert lst[1].parent is in_service

        assert lst[2].from_state == "Yellow"
        assert lst[2].to_state == dsl_nodes.EXIT_STATE
        assert lst[2].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert lst[2].guard is None
        assert lst[2].effects == []
        assert lst[2].parent is in_service

        assert lst[3].from_state == "Yellow"
        assert lst[3].to_state == dsl_nodes.EXIT_STATE
        assert lst[3].event == Event(name="GodDamnFuckUp", state_path=("TrafficLight",))
        assert lst[3].guard is None
        assert lst[3].effects == []
        assert lst[3].parent is in_service

        assert lst[4].from_state == "Green"
        assert lst[4].to_state == dsl_nodes.EXIT_STATE
        assert lst[4].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert lst[4].guard is None
        assert lst[4].effects == []
        assert lst[4].parent is in_service

        assert lst[5].from_state == "Green"
        assert lst[5].to_state == dsl_nodes.EXIT_STATE
        assert lst[5].event == Event(name="GodDamnFuckUp", state_path=("TrafficLight",))
        assert lst[5].guard is None
        assert lst[5].effects == []
        assert lst[5].parent is in_service

        assert lst[6].from_state == dsl_nodes.INIT_STATE
        assert lst[6].to_state == "Red"
        assert lst[6].event == Event(
            name="Start", state_path=("TrafficLight", "InService")
        )
        assert lst[6].guard is None
        assert lst[6].effects == [Operation(var_name="b", expr=Integer(value=1))]
        assert lst[6].parent is in_service

        assert lst[7].from_state == "Red"
        assert lst[7].to_state == "Green"
        assert lst[7].event is None
        assert lst[7].guard is None
        assert lst[7].effects == [Operation(var_name="b", expr=Integer(value=3))]
        assert lst[7].parent is in_service

        assert lst[8].from_state == "Green"
        assert lst[8].to_state == "Yellow"
        assert lst[8].event is None
        assert lst[8].guard is None
        assert lst[8].effects == [Operation(var_name="b", expr=Integer(value=2))]
        assert lst[8].parent is in_service

        assert lst[9].from_state == "Yellow"
        assert lst[9].to_state == "Red"
        assert lst[9].event is None
        assert lst[9].guard == BinaryOp(
            x=Variable(name="a"), op=">=", y=Integer(value=10)
        )
        assert lst[9].effects == [
            Operation(var_name="b", expr=Integer(value=1)),
            Operation(
                var_name="round_count",
                expr=BinaryOp(
                    x=Variable(name="round_count"), op="+", y=Integer(value=1)
                ),
            ),
        ]
        assert lst[9].parent is in_service

        assert lst[10].from_state == "Green"
        assert lst[10].to_state == "Yellow"
        assert lst[10].event == Event(name="E2", state_path=("TrafficLight", "Idle"))
        assert lst[10].guard is None
        assert lst[10].effects == []
        assert lst[10].parent is in_service

        assert lst[11].from_state == "Yellow"
        assert lst[11].to_state == "Yellow"
        assert lst[11].event == Event(name="E2", state_path=("TrafficLight",))
        assert lst[11].guard is None
        assert lst[11].effects == []
        assert lst[11].parent is in_service

    def test_transitions_for_idle(self, idle):
        lst = idle.transitions
        assert len(lst) == 8
        assert lst[0].from_state == "ToBe"
        assert lst[0].to_state == dsl_nodes.EXIT_STATE
        assert lst[0].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
        )
        assert lst[0].guard is None
        assert lst[0].effects == []
        assert lst[0].parent is idle

        assert lst[1].from_state == "ToBe"
        assert lst[1].to_state == dsl_nodes.EXIT_STATE
        assert lst[1].event == Event(name="GodDamnFuckUp", state_path=("TrafficLight",))
        assert lst[1].guard is None
        assert lst[1].effects == []
        assert lst[1].parent is idle

        assert lst[2].from_state == "NotToBe"
        assert lst[2].to_state == dsl_nodes.EXIT_STATE
        assert lst[2].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
        )
        assert lst[2].guard is None
        assert lst[2].effects == []
        assert lst[2].parent is idle

        assert lst[3].from_state == "NotToBe"
        assert lst[3].to_state == dsl_nodes.EXIT_STATE
        assert lst[3].event == Event(name="GodDamnFuckUp", state_path=("TrafficLight",))
        assert lst[3].guard is None
        assert lst[3].effects == []
        assert lst[3].parent is idle

        assert lst[4].from_state == dsl_nodes.INIT_STATE
        assert lst[4].to_state == "ToBe"
        assert lst[4].event is None
        assert lst[4].guard is None
        assert lst[4].effects == []
        assert lst[4].parent is idle

        assert lst[5].from_state == "ToBe"
        assert lst[5].to_state == "NotToBe"
        assert lst[5].event == Event(
            name="E1", state_path=("TrafficLight", "Idle", "ToBe")
        )
        assert lst[5].guard is None
        assert lst[5].effects == []
        assert lst[5].parent is idle

        assert lst[6].from_state == "NotToBe"
        assert lst[6].to_state == "ToBe"
        assert lst[6].event == Event(
            name="E1", state_path=("TrafficLight", "Idle", "NotToBe")
        )
        assert lst[6].guard is None
        assert lst[6].effects == []
        assert lst[6].parent is idle

        assert lst[7].from_state == "NotToBe"
        assert lst[7].to_state == dsl_nodes.EXIT_STATE
        assert lst[7].event == Event(
            name="E2", state_path=("TrafficLight", "Idle", "NotToBe")
        )
        assert lst[7].guard is None
        assert lst[7].effects == []
        assert lst[7].parent is idle

    def test_transitions_for_root_state_1(self, root_state_1):
        lst = root_state_1.transitions
        assert len(lst) == 8
        assert lst[0].from_state == "InService"
        assert lst[0].to_state == dsl_nodes.EXIT_STATE
        assert lst[0].event == Event(
            name="ServiceError", state_path=("TrafficLight", "InService")
        )
        assert lst[0].guard is None
        assert lst[0].effects == []
        assert lst[0].parent is root_state_1

        assert lst[1].from_state == "InService"
        assert lst[1].to_state == dsl_nodes.EXIT_STATE
        assert lst[1].event == Event(name="GodDamnFuckUp", state_path=("TrafficLight",))
        assert lst[1].guard is None
        assert lst[1].effects == []
        assert lst[1].parent is root_state_1

        assert lst[2].from_state == "Idle"
        assert lst[2].to_state == "InService"
        assert lst[2].event == Event(
            name="GiveUpThinking", state_path=("TrafficLight", "Idle")
        )
        assert lst[2].guard is None
        assert lst[2].effects == []
        assert lst[2].parent is root_state_1

        assert lst[3].from_state == "Idle"
        assert lst[3].to_state == dsl_nodes.EXIT_STATE
        assert lst[3].event == Event(name="GodDamnFuckUp", state_path=("TrafficLight",))
        assert lst[3].guard is None
        assert lst[3].effects == []
        assert lst[3].parent is root_state_1

        assert lst[4].from_state == dsl_nodes.INIT_STATE
        assert lst[4].to_state == "InService"
        assert lst[4].event is None
        assert lst[4].guard is None
        assert lst[4].effects == []
        assert lst[4].parent is root_state_1

        assert lst[5].from_state == "InService"
        assert lst[5].to_state == "Idle"
        assert lst[5].event == Event(
            name="Maintain", state_path=("TrafficLight", "InService")
        )
        assert lst[5].guard is None
        assert lst[5].effects == []
        assert lst[5].parent is root_state_1

        assert lst[6].from_state == "Idle"
        assert lst[6].to_state == "Idle"
        assert lst[6].event == Event(name="E2", state_path=("TrafficLight", "Idle"))
        assert lst[6].guard is None
        assert lst[6].effects == []
        assert lst[6].parent is root_state_1

        assert lst[7].from_state == "Idle"
        assert lst[7].to_state == dsl_nodes.EXIT_STATE
        assert lst[7].event is None
        assert lst[7].guard is None
        assert lst[7].effects == []
        assert lst[7].parent is root_state_1

        # print(f'lst = root_state_1.transitions')
        # print(f'assert len(lst) == {len(lst)!r}')
        # for i, item in enumerate(lst):
        #     item: Transition
        #     if item.from_state is dsl_nodes.INIT_STATE:
        #         print(f'assert lst[{i}].from_state == dsl_nodes.INIT_STATE')
        #     else:
        #         print(f'assert lst[{i}].from_state == {item.from_state!r}')
        #     if item.to_state is dsl_nodes.EXIT_STATE:
        #         print(f'assert lst[{i}].to_state == dsl_nodes.EXIT_STATE')
        #     else:
        #         print(f'assert lst[{i}].to_state == {item.to_state!r}')
        #     if item.event is None:
        #         print(f'assert lst[{i}].event is None')
        #     else:
        #         print(f'assert lst[{i}].event == {item.event!r}')
        #     if item.guard is None:
        #         print(f'assert lst[{i}].guard is None')
        #     else:
        #         print(f'assert lst[{i}].guard == {item.guard!r}')
        #     print(f'assert lst[{i}].effects == {item.effects!r}')
        #     print(f'assert lst[{i}].parent is root_state_1')
        #     print()
