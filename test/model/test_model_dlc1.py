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
