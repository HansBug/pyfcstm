import textwrap

import pytest

from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.expr import *
from pyfcstm.model.model import *


@pytest.fixture()
def demo_model_1():
    ast_node = parse_with_grammar_entry("""
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
    """, entry_name='state_machine_dsl')
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.fixture()
def root_state_1(demo_model_1):
    return demo_model_1.root_state


@pytest.fixture()
def in_service(root_state_1):
    return root_state_1.substates['InService']


@pytest.fixture()
def idle(root_state_1):
    return root_state_1.substates['Idle']


@pytest.fixture()
def red(in_service):
    return in_service.substates['Red']


@pytest.fixture()
def yellow(in_service):
    return in_service.substates['Yellow']


@pytest.fixture()
def green(in_service):
    return in_service.substates['Green']


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
    state Idle;
    [*] -> InService;
    InService -> Idle :: Maintain;
    Idle -> Idle :: E2;
    Idle -> [*];
}
    """).strip()


@pytest.mark.unittest
class TestModelModelDLC1:
    def test_model_basic(self, demo_model_1):
        assert demo_model_1.defines == {
            'a': VarDefine(name='a', type='int', init=Integer(value=0)),
            'b': VarDefine(name='b', type='int', init=BinaryOp(x=Integer(value=0), op='*', y=Integer(value=0))),
            'round_count': VarDefine(name='round_count', type='int', init=Integer(value=0))}

        assert demo_model_1.root_state.name == 'TrafficLight'
        assert demo_model_1.root_state.path == ('TrafficLight',)

    def test_model_to_ast_node(self, demo_model_1):
        ast_node = demo_model_1.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(name='a', type='int', expr=dsl_nodes.Integer(raw='0')),
            dsl_nodes.DefAssignment(name='b', type='int',
                                    expr=dsl_nodes.BinaryOp(expr1=dsl_nodes.Integer(raw='0'), op='*',
                                                            expr2=dsl_nodes.Integer(raw='0'))),
            dsl_nodes.DefAssignment(name='round_count', type='int', expr=dsl_nodes.Integer(raw='0'))
        ]
        assert ast_node.root_state.name == "TrafficLight"

    def test_on_during_aspects(self, root_state_1):
        assert root_state_1.on_during_aspects == [
            OnAspect(stage='during', aspect='before', name=None, doc=None,
                     operations=[Operation(var_name='a', expr=Integer(value=0))]),
            OnAspect(stage='during', aspect='before', name='FFT', doc=None, operations=[]),
            OnAspect(stage='during', aspect='before', name='TTT', doc='this is the line', operations=[]),
            OnAspect(stage='during', aspect='after', name=None, doc=None,
                     operations=[Operation(var_name='a', expr=Integer(value=255)),
                                 Operation(var_name='b', expr=Integer(value=1))])
        ]

    def test_list_on_during_aspects(self, root_state_1):
        assert root_state_1.list_on_during_aspects() == [
            OnAspect(stage='during', aspect='before', name=None, doc=None,
                     operations=[Operation(var_name='a', expr=Integer(value=0))]),
            OnAspect(stage='during', aspect='before', name='FFT', doc=None, operations=[]),
            OnAspect(stage='during', aspect='before', name='TTT', doc='this is the line', operations=[]),
            OnAspect(stage='during', aspect='after', name=None, doc=None,
                     operations=[Operation(var_name='a', expr=Integer(value=255)),
                                 Operation(var_name='b', expr=Integer(value=1))])
        ]
        assert root_state_1.list_on_during_aspects(is_abstract=True) == [
            OnAspect(stage='during', aspect='before', name='FFT', doc=None, operations=[]),
            OnAspect(stage='during', aspect='before', name='TTT', doc='this is the line', operations=[]),
        ]
        assert root_state_1.list_on_during_aspects(is_abstract=False) == [
            OnAspect(stage='during', aspect='before', name=None, doc=None,
                     operations=[Operation(var_name='a', expr=Integer(value=0))]),
            OnAspect(stage='during', aspect='after', name=None, doc=None,
                     operations=[Operation(var_name='a', expr=Integer(value=255)),
                                 Operation(var_name='b', expr=Integer(value=1))])
        ]
        assert root_state_1.list_on_during_aspects(aspect='before') == [
            OnAspect(stage='during', aspect='before', name=None, doc=None,
                     operations=[Operation(var_name='a', expr=Integer(value=0))]),
            OnAspect(stage='during', aspect='before', name='FFT', doc=None, operations=[]),
            OnAspect(stage='during', aspect='before', name='TTT', doc='this is the line', operations=[]),
        ]
        assert root_state_1.list_on_during_aspects(aspect='after') == [
            OnAspect(stage='during', aspect='after', name=None, doc=None,
                     operations=[Operation(var_name='a', expr=Integer(value=255)),
                                 Operation(var_name='b', expr=Integer(value=1))])
        ]

    def test_transition_dlcs(self, transition_1, transition_2, transition_3):
        assert transition_1.from_state == 'Idle'
        assert transition_1.to_state == 'Idle'
        assert transition_1.event.name == 'E2'
        assert transition_1.event.state_path == ('TrafficLight', 'Idle')
        assert transition_1.event.path == ('TrafficLight', 'Idle', 'E2')

        assert transition_2.from_state == 'Green'
        assert transition_2.to_state == 'Yellow'
        assert transition_2.event.name == 'E2'
        assert transition_2.event.state_path == ('TrafficLight', 'Idle')
        assert transition_2.event.path == ('TrafficLight', 'Idle', 'E2')

        assert transition_3.from_state == 'Yellow'
        assert transition_3.to_state == 'Yellow'
        assert transition_3.event.name == 'E2'
        assert transition_3.event.state_path == ('TrafficLight',)
        assert transition_3.event.path == ('TrafficLight', 'E2')

    def test_to_ast_node_to_str(self, demo_model_1, expected_to_str_result, text_aligner):
        text_aligner.assert_equal(
            expect=expected_to_str_result,
            actual=str(demo_model_1.to_ast_node())
        )

    def test_parse_unknown_state_for_event(self):
        ast_node = parse_with_grammar_entry("""
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
            LX1 -> LX1 : LX3.E2;
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Cannot find state LX.LX3 for transition:" in err.msg
        assert "LX1 -> LX1 : LX3.E2;" in err.msg

    def test_parse_unknown_state_for_event_abs(self):
        ast_node = parse_with_grammar_entry("""
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
            LX1 -> LX1 : /LX1.LXXX.E2;
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Cannot find state LX.LX1.LXXX for transition:" in err.msg
        assert "LX1 -> LX1 : /LX1.LXXX.E2;" in err.msg

    def test_list_on_during_aspect_recursively(self, red):
        lst = red.list_on_during_aspect_recursively()
        assert len(lst) == 5
        assert lst[0][0].name == 'TrafficLight'
        assert lst[0][0].path == ('TrafficLight',)
        assert lst[0][1].name == None
        assert lst[0][1].stage == 'during'
        assert lst[0][1].aspect == 'before'
        assert not lst[0][1].is_abstract
        assert lst[0][1].is_aspect

        assert lst[1][0].name == 'TrafficLight'
        assert lst[1][0].path == ('TrafficLight',)
        assert lst[1][1].name == 'FFT'
        assert lst[1][1].stage == 'during'
        assert lst[1][1].aspect == 'before'
        assert lst[1][1].is_abstract
        assert lst[1][1].is_aspect

        assert lst[2][0].name == 'TrafficLight'
        assert lst[2][0].path == ('TrafficLight',)
        assert lst[2][1].name == 'TTT'
        assert lst[2][1].stage == 'during'
        assert lst[2][1].aspect == 'before'
        assert lst[2][1].is_abstract
        assert lst[2][1].is_aspect

        assert lst[3][0].name == 'Red'
        assert lst[3][0].path == ('TrafficLight', 'InService', 'Red')
        assert lst[3][1].name == None
        assert lst[3][1].stage == 'during'
        assert lst[3][1].aspect is None
        assert not lst[3][1].is_abstract
        assert not lst[3][1].is_aspect

        assert lst[4][0].name == 'TrafficLight'
        assert lst[4][0].path == ('TrafficLight',)
        assert lst[4][1].name == None
        assert lst[4][1].stage == 'during'
        assert lst[4][1].aspect == 'after'
        assert not lst[4][1].is_abstract
        assert lst[4][1].is_aspect

        # print(f'lst = red.list_on_during_aspect_recursively()')
        # print(f'assert len(lst) == {len(lst)}')
        # for i, (state, item) in enumerate(lst):
        #     item: Union[OnStage, OnAspect]
        #     print(f'assert lst[{i}][0].name == {state.name!r}')
        #     print(f'assert lst[{i}][0].path == {state.path!r}')
        #     print(f'assert lst[{i}][1].name == {item.name!r}')
        #     if item.stage is not None:
        #         print(f'assert lst[{i}][1].stage == {item.stage!r}')
        #     else:
        #         print(f'assert lst[{i}][1].stage is None')
        #     if item.aspect:
        #         print(f'assert lst[{i}][1].aspect == {item.aspect!r}')
        #     else:
        #         print(f'assert lst[{i}][1].aspect is None')
        #     if item.is_abstract:
        #         print(f'assert lst[{i}][1].is_abstract')
        #     else:
        #         print(f'assert not lst[{i}][1].is_abstract')
        #     if item.is_aspect:
        #         print(f'assert lst[{i}][1].is_aspect')
        #     else:
        #         print(f'assert not lst[{i}][1].is_aspect')
        #     print()

    def test_list_on_during_aspect_recursively_with_ids(self, red):
        lst = red.list_on_during_aspect_recursively(with_ids=True)
        assert len(lst) == 5
        assert lst[0][0] == 1
        assert lst[0][1].name == 'TrafficLight'
        assert lst[0][1].path == ('TrafficLight',)
        assert lst[0][2].name == None
        assert lst[0][2].stage == 'during'
        assert lst[0][2].aspect == 'before'
        assert not lst[0][2].is_abstract
        assert lst[0][2].is_aspect

        assert lst[1][0] == 2
        assert lst[1][1].name == 'TrafficLight'
        assert lst[1][1].path == ('TrafficLight',)
        assert lst[1][2].name == 'FFT'
        assert lst[1][2].stage == 'during'
        assert lst[1][2].aspect == 'before'
        assert lst[1][2].is_abstract
        assert lst[1][2].is_aspect

        assert lst[2][0] == 3
        assert lst[2][1].name == 'TrafficLight'
        assert lst[2][1].path == ('TrafficLight',)
        assert lst[2][2].name == 'TTT'
        assert lst[2][2].stage == 'during'
        assert lst[2][2].aspect == 'before'
        assert lst[2][2].is_abstract
        assert lst[2][2].is_aspect

        assert lst[3][0] == 1
        assert lst[3][1].name == 'Red'
        assert lst[3][1].path == ('TrafficLight', 'InService', 'Red')
        assert lst[3][2].name == None
        assert lst[3][2].stage == 'during'
        assert lst[3][2].aspect is None
        assert not lst[3][2].is_abstract
        assert not lst[3][2].is_aspect

        assert lst[4][0] == 4
        assert lst[4][1].name == 'TrafficLight'
        assert lst[4][1].path == ('TrafficLight',)
        assert lst[4][2].name == None
        assert lst[4][2].stage == 'during'
        assert lst[4][2].aspect == 'after'
        assert not lst[4][2].is_abstract
        assert lst[4][2].is_aspect

        # print(f'lst = red.list_on_during_aspect_recursively(with_ids=True)')
        # print(f'assert len(lst) == {len(lst)}')
        # for i, (id_, state, item) in enumerate(lst):
        #     item: Union[OnStage, OnAspect]
        #     print(f'assert lst[{i}][0] == {id_!r}')
        #     print(f'assert lst[{i}][1].name == {state.name!r}')
        #     print(f'assert lst[{i}][1].path == {state.path!r}')
        #     print(f'assert lst[{i}][2].name == {item.name!r}')
        #     if item.stage is not None:
        #         print(f'assert lst[{i}][2].stage == {item.stage!r}')
        #     else:
        #         print(f'assert lst[{i}][2].stage is None')
        #     if item.aspect:
        #         print(f'assert lst[{i}][2].aspect == {item.aspect!r}')
        #     else:
        #         print(f'assert lst[{i}][2].aspect is None')
        #     if item.is_abstract:
        #         print(f'assert lst[{i}][2].is_abstract')
        #     else:
        #         print(f'assert not lst[{i}][2].is_abstract')
        #     if item.is_aspect:
        #         print(f'assert lst[{i}][2].is_aspect')
        #     else:
        #         print(f'assert not lst[{i}][2].is_aspect')
        #     print()

    def test_abstract_on_during_aspects(self, root_state_1):
        lst = root_state_1.abstract_on_during_aspects
        assert len(lst) == 2
        assert lst[0].name == 'FFT'
        assert lst[0].stage == 'during'
        assert lst[0].aspect == 'before'
        assert lst[0].is_abstract
        assert lst[0].is_aspect

        assert lst[1].name == 'TTT'
        assert lst[1].stage == 'during'
        assert lst[1].aspect == 'before'
        assert lst[1].is_abstract
        assert lst[1].is_aspect

        # print(f'lst = root_state_1.abstract_on_during_aspects')
        # print(f'assert len(lst) == {len(lst)}')
        # for i, item in enumerate(lst):
        #     item: Union[OnStage, OnAspect]
        #     print(f'assert lst[{i}].name == {item.name!r}')
        #     if item.stage is not None:
        #         print(f'assert lst[{i}].stage == {item.stage!r}')
        #     else:
        #         print(f'assert lst[{i}].stage is None')
        #     if item.aspect:
        #         print(f'assert lst[{i}].aspect == {item.aspect!r}')
        #     else:
        #         print(f'assert lst[{i}].aspect is None')
        #     if item.is_abstract:
        #         print(f'assert lst[{i}].is_abstract')
        #     else:
        #         print(f'assert not lst[{i}].is_abstract')
        #     if item.is_aspect:
        #         print(f'assert lst[{i}].is_aspect')
        #     else:
        #         print(f'assert not lst[{i}].is_aspect')
        #     print()

    def test_non_abstract_on_during_aspects(self, root_state_1):
        lst = root_state_1.non_abstract_on_during_aspects
        lst = root_state_1.non_abstract_on_during_aspects
        assert len(lst) == 2
        assert lst[0].name == None
        assert lst[0].stage == 'during'
        assert lst[0].aspect == 'before'
        assert not lst[0].is_abstract
        assert lst[0].is_aspect
        assert lst[0].to_ast_node().operations == [
            dsl_nodes.OperationAssignment(name='a', expr=dsl_nodes.Integer(raw='0'))]

        assert lst[1].name == None
        assert lst[1].stage == 'during'
        assert lst[1].aspect == 'after'
        assert not lst[1].is_abstract
        assert lst[1].is_aspect
        assert lst[1].to_ast_node().operations == [
            dsl_nodes.OperationAssignment(name='a', expr=dsl_nodes.Integer(raw='255')),
            dsl_nodes.OperationAssignment(name='b', expr=dsl_nodes.Integer(raw='1'))]

        # print(f'lst = root_state_1.non_abstract_on_during_aspects')
        # print(f'assert len(lst) == {len(lst)}')
        # for i, item in enumerate(lst):
        #     item: Union[OnStage, OnAspect]
        #     print(f'assert lst[{i}].name == {item.name!r}')
        #     if item.stage is not None:
        #         print(f'assert lst[{i}].stage == {item.stage!r}')
        #     else:
        #         print(f'assert lst[{i}].stage is None')
        #     if item.aspect:
        #         print(f'assert lst[{i}].aspect == {item.aspect!r}')
        #     else:
        #         print(f'assert lst[{i}].aspect is None')
        #     if item.is_abstract:
        #         print(f'assert lst[{i}].is_abstract')
        #     else:
        #         print(f'assert not lst[{i}].is_abstract')
        #     if item.is_aspect:
        #         print(f'assert lst[{i}].is_aspect')
        #     else:
        #         print(f'assert not lst[{i}].is_aspect')
        #     print(f'assert lst[{i}].to_ast_node().operations == {item.to_ast_node().operations!r}')
        #     print()
