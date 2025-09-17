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
    def int b = 0x2 | 0x5;

    state LX {
        [*] -> LX1;
        [*] -> LX2 :: EEE;

        enter {
            b = 0 + b;
            b = 3 + a * (2 + b);
        }

        exit {
            b = 0;
            b = a << 2;
        }

        state LX1 {
            during before abstract BeforeLX1Enter;
            during after abstract AfterLX1Enter /*
                this is the comment line
            */
            during before {
                b = 1 + 2;
            }
            during after {
                b = 3 - 2;
                b = 3 + 2 + a;
            }

            state LX11 {
                enter abstract LX11Enter;
                exit abstract LX11Exit;
                during abstract LX11During; 
                enter abstract /*
                    This is X
                */
                during {
                    b = 0x2 << 0x3;
                    b = b + -1;
                }
            }
            state LX12;
            state LX13;
            state LX14;

            [*] -> LX11;
            LX11 -> LX12 :: E1;
            LX12 -> LX13 :: E1;
            LX12 -> LX14 :: E2;

            LX13 -> [*] :: E1 effect {
                a = 0x2;
            }
            LX13 -> [*] :: E2 effect {
                a = 0x3;
            }
            LX13 -> LX14 :: E3;
            LX13 -> LX14 :: E4;
            LX14 -> LX12 :: E1;
            LX14 -> [*] :: E2 effect {
                a = 0x1;
            }
        }

        state LX2 {
            [*] -> LX21;
            state LX21 {
                state LX211;
                state LX212;
                [*] -> LX211 : if [a == 0x2];
                [*] -> LX212 : if [a == 0x3];
                LX211 -> [*] :: E1 effect {
                    a = 0x1;
                }
                LX211 -> LX212 :: E2;
                LX212 -> [*] :: E1 effect {
                    a = 0x1;
                }
                LX212 -> LX211 : E2;
            }
            LX21 -> [*] : if [a == 0x1];
        }

        LX1 -> LX2 : if [a == 0x2 || a == 0x3];
        LX1 -> LX1 : if [a == 0x1];
        LX2 -> LX1 : if [a == 0x1];
    }
    """, entry_name='state_machine_dsl')
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.fixture()
def root_state_1(demo_model_1):
    return demo_model_1.root_state


@pytest.fixture()
def operation_1(root_state_1):
    return root_state_1.on_enters[0].operations[0]


@pytest.fixture()
def operation_2(root_state_1):
    return root_state_1.on_enters[0].operations[1]


@pytest.fixture()
def state_LX_LX1(root_state_1):
    return root_state_1.substates['LX1']


@pytest.fixture()
def state_LX_LX1_LX11(state_LX_LX1):
    return state_LX_LX1.substates['LX11']


@pytest.fixture()
def var_define_a(demo_model_1):
    return demo_model_1.defines['a']


@pytest.fixture()
def var_define_b(demo_model_1):
    return demo_model_1.defines['b']


@pytest.fixture()
def transition_1(root_state_1):
    return root_state_1.transitions_to[0]


@pytest.fixture()
def transition_2(root_state_1):
    return root_state_1.transitions_from[0]


@pytest.fixture()
def transition_3(root_state_1):
    return root_state_1.transitions[0]


@pytest.fixture()
def transition_4(root_state_1):
    return root_state_1.transitions[1]


@pytest.fixture()
def transition_5(state_LX_LX1):
    return state_LX_LX1.transitions[3]


@pytest.fixture()
def transition_6(state_LX_LX1):
    return state_LX_LX1.transitions[4]


@pytest.fixture()
def transition_7(root_state_1):
    return root_state_1.transitions[-1]


@pytest.fixture()
def expected_plantuml_code():
    return textwrap.dedent("""
@startuml
note as DefinitionNote
defines {
    def int a = 0;
    def int b = 2 | 5;
}
end note

state "LX" as lx {
    state "LX1" as lx__lx1 {
        state "LX11" as lx__lx1__lx11
        lx__lx1__lx11 : enter abstract LX11Enter;\\nenter abstract /*\\n    This is X\\n*/\\nduring abstract LX11During;\\nduring {\\n    b = 2 << 3;\\n    b = b + -1;\\n}\\nexit abstract LX11Exit;
        state "LX12" as lx__lx1__lx12
        state "LX13" as lx__lx1__lx13
        state "LX14" as lx__lx1__lx14
        [*] --> lx__lx1__lx11
        lx__lx1__lx11 --> lx__lx1__lx12 : LX11.E1
        lx__lx1__lx12 --> lx__lx1__lx13 : LX12.E1
        lx__lx1__lx12 --> lx__lx1__lx14 : LX12.E2
        lx__lx1__lx13 --> [*] : LX13.E1
        note on link
        effect {
            a = 2;
        }
        end note
        lx__lx1__lx13 --> [*] : LX13.E2
        note on link
        effect {
            a = 3;
        }
        end note
        lx__lx1__lx13 --> lx__lx1__lx14 : LX13.E3
        lx__lx1__lx13 --> lx__lx1__lx14 : LX13.E4
        lx__lx1__lx14 --> lx__lx1__lx12 : LX14.E1
        lx__lx1__lx14 --> [*] : LX14.E2
        note on link
        effect {
            a = 1;
        }
        end note
    }
    lx__lx1 : during before abstract BeforeLX1Enter;\\nduring after abstract AfterLX1Enter /*\\n    this is the comment line\\n*/\\nduring before {\\n    b = 1 + 2;\\n}\\nduring after {\\n    b = 3 - 2;\\n    b = 3 + 2 + a;\\n}
    state "LX2" as lx__lx2 {
        state "LX21" as lx__lx2__lx21 {
            state "LX211" as lx__lx2__lx21__lx211
            state "LX212" as lx__lx2__lx21__lx212
            [*] --> lx__lx2__lx21__lx211 : a == 2
            [*] --> lx__lx2__lx21__lx212 : a == 3
            lx__lx2__lx21__lx211 --> [*] : LX211.E1
            note on link
            effect {
                a = 1;
            }
            end note
            lx__lx2__lx21__lx211 --> lx__lx2__lx21__lx212 : LX211.E2
            lx__lx2__lx21__lx212 --> [*] : LX212.E1
            note on link
            effect {
                a = 1;
            }
            end note
            lx__lx2__lx21__lx212 --> lx__lx2__lx21__lx211 : E2
        }
        [*] --> lx__lx2__lx21
        lx__lx2__lx21 --> [*] : a == 1
    }
    [*] --> lx__lx1
    [*] --> lx__lx2 : EEE
    lx__lx1 --> lx__lx2 : a == 2 || a == 3
    lx__lx1 --> lx__lx1 : a == 1
    lx__lx2 --> lx__lx1 : a == 1
}
lx : enter {\\n    b = 0 + b;\\n    b = 3 + a * (2 + b);\\n}\\nexit {\\n    b = 0;\\n    b = a << 2;\\n}
[*] --> lx
lx --> [*]
@enduml
    """).strip()


@pytest.mark.unittest
class TestModelModel:
    def test_model_basic(self, demo_model_1):
        assert demo_model_1.defines == {'a': VarDefine(name='a', type='int', init=Integer(value=0)),
                                        'b': VarDefine(name='b', type='int',
                                                       init=BinaryOp(x=Integer(value=2), op='|', y=Integer(value=5)))}

        assert demo_model_1.root_state.name == 'LX'
        assert demo_model_1.root_state.path == ('LX',)

    def test_model_to_ast_node(self, demo_model_1):
        ast_node = demo_model_1.to_ast_node()
        assert ast_node.definitions == [
            dsl_nodes.DefAssignment(name='a', type='int', expr=dsl_nodes.Integer(raw='0')),
            dsl_nodes.DefAssignment(name='b', type='int',
                                    expr=dsl_nodes.BinaryOp(expr1=dsl_nodes.Integer(raw='2'), op='|',
                                                            expr2=dsl_nodes.Integer(raw='5')))
        ]
        assert ast_node.root_state.name == "LX"

    def test_root_state_basic(self, root_state_1):
        assert root_state_1.parent is None
        assert root_state_1.name == 'LX'
        assert root_state_1.is_root_state
        assert not root_state_1.is_leaf_state

        assert len(root_state_1.transitions) == 5
        assert root_state_1.transitions[0].from_state == dsl_nodes.INIT_STATE
        assert root_state_1.transitions[0].to_state == 'LX1'
        assert root_state_1.transitions[0].parent is root_state_1
        assert root_state_1.transitions[1].from_state == dsl_nodes.INIT_STATE
        assert root_state_1.transitions[1].to_state == 'LX2'
        assert root_state_1.transitions[1].parent is root_state_1
        assert root_state_1.transitions[2].from_state == 'LX1'
        assert root_state_1.transitions[2].to_state == 'LX2'
        assert root_state_1.transitions[2].parent is root_state_1
        assert root_state_1.transitions[3].from_state == 'LX1'
        assert root_state_1.transitions[3].to_state == 'LX1'
        assert root_state_1.transitions[3].parent is root_state_1
        assert root_state_1.transitions[4].from_state == 'LX2'
        assert root_state_1.transitions[4].to_state == 'LX1'
        assert root_state_1.transitions[4].parent is root_state_1

        assert len(root_state_1.transitions_from) == 1
        transition_from = root_state_1.transitions_from[0]
        assert transition_from.from_state == 'LX'
        assert transition_from.to_state == dsl_nodes.EXIT_STATE
        assert transition_from.event is None
        assert transition_from.guard is None
        assert transition_from.effects == []
        assert transition_from.parent is None

        assert len(root_state_1.transitions_to) == 1
        transition_to = root_state_1.transitions_to[0]
        assert transition_to.from_state == dsl_nodes.INIT_STATE
        assert transition_to.to_state == 'LX'
        assert transition_to.event is None
        assert transition_to.guard is None
        assert transition_to.effects == []
        assert transition_to.parent is None

        assert len(root_state_1.transitions_entering_children) == 2
        assert root_state_1.transitions_entering_children[0].from_state == dsl_nodes.INIT_STATE
        assert root_state_1.transitions_entering_children[0].to_state == 'LX1'
        assert root_state_1.transitions_entering_children[0].event is None
        assert root_state_1.transitions_entering_children[0].guard is None
        assert root_state_1.transitions_entering_children[0].parent is root_state_1
        assert root_state_1.transitions_entering_children[1].from_state == dsl_nodes.INIT_STATE
        assert root_state_1.transitions_entering_children[1].to_state == 'LX2'
        assert root_state_1.transitions_entering_children[1].event is not None
        assert root_state_1.transitions_entering_children[1].guard is None
        assert root_state_1.transitions_entering_children[1].parent is root_state_1

        assert len(root_state_1.transitions_entering_children_simplified) == 1
        assert root_state_1.transitions_entering_children_simplified[0].from_state == dsl_nodes.INIT_STATE
        assert root_state_1.transitions_entering_children_simplified[0].to_state == 'LX1'
        assert root_state_1.transitions_entering_children_simplified[0].event is None
        assert root_state_1.transitions_entering_children_simplified[0].guard is None
        assert root_state_1.transitions_entering_children_simplified[0].parent is root_state_1

        assert root_state_1.on_enters == [
            OnStage(stage='enter', aspect=None, name=None, doc=None, operations=[
                Operation(var_name='b', expr=BinaryOp(x=Integer(value=0), op='+', y=Variable(name='b'))),
                Operation(var_name='b', expr=BinaryOp(x=Integer(value=3), op='+',
                                                      y=BinaryOp(x=Variable(name='a'), op='*',
                                                                 y=BinaryOp(x=Integer(value=2), op='+',
                                                                            y=Variable(name='b')))))])]
        assert root_state_1.on_durings == []
        assert root_state_1.on_exits == [
            OnStage(stage='exit', aspect=None, name=None, doc=None,
                    operations=[Operation(var_name='b', expr=Integer(value=0)), Operation(var_name='b', expr=BinaryOp(
                        x=Variable(name='a'), op='<<', y=Integer(value=2)))])]

        assert root_state_1.abstract_on_enters == []
        assert root_state_1.non_abstract_on_enters == root_state_1.on_enters
        assert root_state_1.abstract_on_durings == []
        assert root_state_1.non_abstract_on_durings == root_state_1.on_durings
        assert root_state_1.abstract_on_exits == []
        assert root_state_1.non_abstract_on_exits == root_state_1.on_exits

        assert root_state_1.events == {'EEE': Event(name='EEE', state_path=('LX',))}

    def test_operation_basic(self, operation_1, operation_2):
        assert operation_1.var_name == 'b'
        assert operation_1.expr == BinaryOp(x=Integer(value=0), op='+', y=Variable(name='b'))
        assert operation_1.to_ast_node() == dsl_nodes.OperationAssignment(name='b', expr=dsl_nodes.BinaryOp(
            expr1=dsl_nodes.Integer(raw='0'), op='+', expr2=dsl_nodes.Name(name='b')))
        assert operation_1.var_name_to_ast_node() == dsl_nodes.Name(name='b')

        assert operation_2.var_name == 'b'
        assert operation_2.expr == BinaryOp(x=Integer(value=3), op='+',
                                            y=BinaryOp(x=Variable(name='a'), op='*',
                                                       y=BinaryOp(x=Integer(value=2), op='+',
                                                                  y=Variable(name='b'))))
        assert operation_2.to_ast_node() == dsl_nodes.OperationAssignment(name='b', expr=dsl_nodes.BinaryOp(
            expr1=dsl_nodes.Integer(raw='3'), op='+', expr2=dsl_nodes.BinaryOp(expr1=dsl_nodes.Name(name='a'), op='*',
                                                                               expr2=dsl_nodes.Paren(
                                                                                   expr=dsl_nodes.BinaryOp(
                                                                                       expr1=dsl_nodes.Integer(raw='2'),
                                                                                       op='+', expr2=dsl_nodes.Name(
                                                                                           name='b'))))))
        assert operation_2.var_name_to_ast_node() == dsl_nodes.Name(name='b')

    def test_walk_states(self, demo_model_1, root_state_1, state_LX_LX1, state_LX_LX1_LX11):
        assert [state.path for state in demo_model_1.walk_states()] == [
            ('LX',),
            ('LX', 'LX1'),
            ('LX', 'LX1', 'LX11'),
            ('LX', 'LX1', 'LX12'),
            ('LX', 'LX1', 'LX13'),
            ('LX', 'LX1', 'LX14'),
            ('LX', 'LX2'),
            ('LX', 'LX2', 'LX21'),
            ('LX', 'LX2', 'LX21', 'LX211'),
            ('LX', 'LX2', 'LX21', 'LX212'),
        ]

        assert [state.path for state in root_state_1.walk_states()] == [
            ('LX',),
            ('LX', 'LX1'),
            ('LX', 'LX1', 'LX11'),
            ('LX', 'LX1', 'LX12'),
            ('LX', 'LX1', 'LX13'),
            ('LX', 'LX1', 'LX14'),
            ('LX', 'LX2'),
            ('LX', 'LX2', 'LX21'),
            ('LX', 'LX2', 'LX21', 'LX211'),
            ('LX', 'LX2', 'LX21', 'LX212'),
        ]

        assert [state.path for state in state_LX_LX1.walk_states()] == [
            ('LX', 'LX1'),
            ('LX', 'LX1', 'LX11'),
            ('LX', 'LX1', 'LX12'),
            ('LX', 'LX1', 'LX13'),
            ('LX', 'LX1', 'LX14'),
        ]
        assert [state.path for state in state_LX_LX1_LX11.walk_states()] == [
            ('LX', 'LX1', 'LX11'),
        ]

    def test_var_defines(self, var_define_a, var_define_b):
        assert var_define_a.name == 'a'
        assert var_define_a.type == 'int'
        assert var_define_a.init == Integer(value=0)
        assert var_define_a.init() == 0
        assert var_define_a.to_ast_node() == dsl_nodes.DefAssignment(name='a', type='int',
                                                                     expr=dsl_nodes.Integer(raw='0'))
        assert var_define_a.name_ast_node() == dsl_nodes.Name(name='a')

        assert var_define_b.name == 'b'
        assert var_define_b.type == 'int'
        assert var_define_b.init == BinaryOp(x=Integer(value=2), op='|', y=Integer(value=5))
        assert var_define_b.init() == 7
        assert var_define_b.to_ast_node() == dsl_nodes.DefAssignment(name='b', type='int', expr=dsl_nodes.BinaryOp(
            expr1=dsl_nodes.Integer(raw='2'), op='|', expr2=dsl_nodes.Integer(raw='5')))
        assert var_define_b.name_ast_node() == dsl_nodes.Name(name='b')

    def test_parent_states(self, state_LX_LX1, state_LX_LX1_LX11, root_state_1):
        assert root_state_1.parent is None
        assert state_LX_LX1.parent is root_state_1
        assert state_LX_LX1_LX11.parent is state_LX_LX1

    def test_state_LX_LX1(self, state_LX_LX1):
        assert state_LX_LX1.name == 'LX1'
        assert state_LX_LX1.path == ('LX', 'LX1')
        assert not state_LX_LX1.is_leaf_state
        assert not state_LX_LX1.is_root_state

        assert len(state_LX_LX1.substates) == 4
        assert set(state_LX_LX1.substates.keys()) == {'LX11', 'LX12', 'LX13', 'LX14'}
        assert state_LX_LX1.substate_name_to_id == {'LX11': 0, 'LX12': 1, 'LX13': 2, 'LX14': 3}

        assert len(state_LX_LX1.transitions) == 10
        assert state_LX_LX1.transitions[0].from_state == dsl_nodes.INIT_STATE
        assert state_LX_LX1.transitions[0].to_state == 'LX11'
        assert state_LX_LX1.transitions[0].event is None
        assert state_LX_LX1.transitions[0].guard is None
        assert len(state_LX_LX1.transitions[0].effects) == 0
        assert state_LX_LX1.transitions[0].parent is state_LX_LX1
        assert state_LX_LX1.transitions[1].from_state == 'LX11'
        assert state_LX_LX1.transitions[1].to_state == 'LX12'
        assert state_LX_LX1.transitions[1].event is not None
        assert state_LX_LX1.transitions[1].event.path == ('LX', 'LX1', 'LX11', 'E1')
        assert state_LX_LX1.transitions[1].guard is None
        assert len(state_LX_LX1.transitions[1].effects) == 0
        assert state_LX_LX1.transitions[1].parent is state_LX_LX1
        assert state_LX_LX1.transitions[2].from_state == 'LX12'
        assert state_LX_LX1.transitions[2].to_state == 'LX13'
        assert state_LX_LX1.transitions[2].event is not None
        assert state_LX_LX1.transitions[2].event.path == ('LX', 'LX1', 'LX12', 'E1')
        assert state_LX_LX1.transitions[2].guard is None
        assert len(state_LX_LX1.transitions[2].effects) == 0
        assert state_LX_LX1.transitions[2].parent is state_LX_LX1
        assert state_LX_LX1.transitions[3].from_state == 'LX12'
        assert state_LX_LX1.transitions[3].to_state == 'LX14'
        assert state_LX_LX1.transitions[3].event is not None
        assert state_LX_LX1.transitions[3].event.path == ('LX', 'LX1', 'LX12', 'E2')
        assert state_LX_LX1.transitions[3].guard is None
        assert len(state_LX_LX1.transitions[3].effects) == 0
        assert state_LX_LX1.transitions[3].parent is state_LX_LX1
        assert state_LX_LX1.transitions[4].from_state == 'LX13'
        assert state_LX_LX1.transitions[4].to_state == dsl_nodes.EXIT_STATE
        assert state_LX_LX1.transitions[4].event is not None
        assert state_LX_LX1.transitions[4].event.path == ('LX', 'LX1', 'LX13', 'E1')
        assert state_LX_LX1.transitions[4].guard is None
        assert len(state_LX_LX1.transitions[4].effects) == 1
        assert state_LX_LX1.transitions[4].effects[0] == Operation(var_name='a', expr=Integer(value=2))
        assert state_LX_LX1.transitions[4].parent is state_LX_LX1
        assert state_LX_LX1.transitions[5].from_state == 'LX13'
        assert state_LX_LX1.transitions[5].to_state == dsl_nodes.EXIT_STATE
        assert state_LX_LX1.transitions[5].event is not None
        assert state_LX_LX1.transitions[5].event.path == ('LX', 'LX1', 'LX13', 'E2')
        assert state_LX_LX1.transitions[5].guard is None
        assert len(state_LX_LX1.transitions[5].effects) == 1
        assert state_LX_LX1.transitions[5].effects[0] == Operation(var_name='a', expr=Integer(value=3))
        assert state_LX_LX1.transitions[5].parent is state_LX_LX1
        assert state_LX_LX1.transitions[6].from_state == 'LX13'
        assert state_LX_LX1.transitions[6].to_state == 'LX14'
        assert state_LX_LX1.transitions[6].event is not None
        assert state_LX_LX1.transitions[6].event.path == ('LX', 'LX1', 'LX13', 'E3')
        assert state_LX_LX1.transitions[6].guard is None
        assert len(state_LX_LX1.transitions[6].effects) == 0
        assert state_LX_LX1.transitions[6].parent is state_LX_LX1
        assert state_LX_LX1.transitions[7].from_state == 'LX13'
        assert state_LX_LX1.transitions[7].to_state == 'LX14'
        assert state_LX_LX1.transitions[7].event is not None
        assert state_LX_LX1.transitions[7].event.path == ('LX', 'LX1', 'LX13', 'E4')
        assert state_LX_LX1.transitions[7].guard is None
        assert len(state_LX_LX1.transitions[7].effects) == 0
        assert state_LX_LX1.transitions[7].parent is state_LX_LX1
        assert state_LX_LX1.transitions[8].from_state == 'LX14'
        assert state_LX_LX1.transitions[8].to_state == 'LX12'
        assert state_LX_LX1.transitions[8].event is not None
        assert state_LX_LX1.transitions[8].event.path == ('LX', 'LX1', 'LX14', 'E1')
        assert state_LX_LX1.transitions[8].guard is None
        assert len(state_LX_LX1.transitions[8].effects) == 0
        assert state_LX_LX1.transitions[8].parent is state_LX_LX1
        assert state_LX_LX1.transitions[9].from_state == 'LX14'
        assert state_LX_LX1.transitions[9].to_state == dsl_nodes.EXIT_STATE
        assert state_LX_LX1.transitions[9].event is not None
        assert state_LX_LX1.transitions[9].event.path == ('LX', 'LX1', 'LX14', 'E2')
        assert state_LX_LX1.transitions[9].guard is None
        assert len(state_LX_LX1.transitions[9].effects) == 1
        assert state_LX_LX1.transitions[9].effects[0] == Operation(var_name='a', expr=Integer(value=1))
        assert state_LX_LX1.transitions[9].parent is state_LX_LX1

        assert len(state_LX_LX1.transitions_from) == 2
        assert state_LX_LX1.transitions_from[0].from_state == 'LX1'
        assert state_LX_LX1.transitions_from[0].to_state == 'LX2'
        assert state_LX_LX1.transitions_from[0].event is None
        assert state_LX_LX1.transitions_from[0].guard is not None
        assert str(state_LX_LX1.transitions_from[0].guard) == 'a == 2 || a == 3'
        assert len(state_LX_LX1.transitions_from[0].effects) == 0
        assert state_LX_LX1.transitions_from[0].parent is state_LX_LX1.parent
        assert state_LX_LX1.transitions_from[1].from_state == 'LX1'
        assert state_LX_LX1.transitions_from[1].to_state == 'LX1'
        assert state_LX_LX1.transitions_from[1].event is None
        assert state_LX_LX1.transitions_from[1].guard is not None
        assert str(state_LX_LX1.transitions_from[1].guard) == 'a == 1'
        assert len(state_LX_LX1.transitions_from[1].effects) == 0
        assert state_LX_LX1.transitions_from[1].parent is state_LX_LX1.parent

        assert len(state_LX_LX1.transitions_to) == 3
        assert state_LX_LX1.transitions_to[0].from_state == dsl_nodes.INIT_STATE
        assert state_LX_LX1.transitions_to[0].to_state == 'LX1'
        assert state_LX_LX1.transitions_to[0].event is None
        assert state_LX_LX1.transitions_to[0].guard is None
        assert len(state_LX_LX1.transitions_to[0].effects) == 0
        assert state_LX_LX1.transitions_to[0].parent is state_LX_LX1.parent
        assert state_LX_LX1.transitions_to[1].from_state == 'LX1'
        assert state_LX_LX1.transitions_to[1].to_state == 'LX1'
        assert state_LX_LX1.transitions_to[1].event is None
        assert state_LX_LX1.transitions_to[1].guard is not None
        assert str(state_LX_LX1.transitions_to[1].guard) == 'a == 1'
        assert len(state_LX_LX1.transitions_to[1].effects) == 0
        assert state_LX_LX1.transitions_to[1].parent is state_LX_LX1.parent
        assert state_LX_LX1.transitions_to[2].from_state == 'LX2'
        assert state_LX_LX1.transitions_to[2].to_state == 'LX1'
        assert state_LX_LX1.transitions_to[2].event is None
        assert state_LX_LX1.transitions_to[2].guard is not None
        assert str(state_LX_LX1.transitions_to[2].guard) == 'a == 1'
        assert len(state_LX_LX1.transitions_to[2].effects) == 0
        assert state_LX_LX1.transitions_to[2].parent is state_LX_LX1.parent

        assert len(state_LX_LX1.transitions_entering_children) == 1
        assert state_LX_LX1.transitions_entering_children[0].from_state == dsl_nodes.INIT_STATE
        assert state_LX_LX1.transitions_entering_children[0].to_state == 'LX11'
        assert state_LX_LX1.transitions_entering_children[0].event is None
        assert state_LX_LX1.transitions_entering_children[0].guard is None
        assert len(state_LX_LX1.transitions_entering_children[0].effects) == 0
        assert state_LX_LX1.transitions_entering_children[0].parent is state_LX_LX1

        assert len(state_LX_LX1.transitions_entering_children_simplified) == 1
        assert state_LX_LX1.transitions_entering_children_simplified[0].from_state == dsl_nodes.INIT_STATE
        assert state_LX_LX1.transitions_entering_children_simplified[0].to_state == 'LX11'
        assert state_LX_LX1.transitions_entering_children_simplified[0].event is None
        assert state_LX_LX1.transitions_entering_children_simplified[0].guard is None
        assert len(state_LX_LX1.transitions_entering_children_simplified[0].effects) == 0
        assert state_LX_LX1.transitions_entering_children_simplified[0].parent is state_LX_LX1

    def test_state_LX_LX1_LX11(self, state_LX_LX1_LX11):
        assert state_LX_LX1_LX11.name == 'LX11'
        assert state_LX_LX1_LX11.path == ('LX', 'LX1', 'LX11')
        assert state_LX_LX1_LX11.is_leaf_state
        assert not state_LX_LX1_LX11.is_root_state

        assert len(state_LX_LX1_LX11.substates) == 0
        assert state_LX_LX1_LX11.substate_name_to_id == {}

        assert len(state_LX_LX1_LX11.transitions) == 0

        assert len(state_LX_LX1_LX11.transitions_from) == 1
        assert state_LX_LX1_LX11.transitions_from[0].from_state == 'LX11'
        assert state_LX_LX1_LX11.transitions_from[0].to_state == 'LX12'
        assert state_LX_LX1_LX11.transitions_from[0].event is not None
        assert state_LX_LX1_LX11.transitions_from[0].event.path == ('LX', 'LX1', 'LX11', 'E1')
        assert state_LX_LX1_LX11.transitions_from[0].guard is None
        assert len(state_LX_LX1_LX11.transitions_from[0].effects) == 0
        assert state_LX_LX1_LX11.transitions_from[0].parent is state_LX_LX1_LX11.parent

        assert len(state_LX_LX1_LX11.transitions_to) == 1
        assert state_LX_LX1_LX11.transitions_to[0].from_state == dsl_nodes.INIT_STATE
        assert state_LX_LX1_LX11.transitions_to[0].to_state == 'LX11'
        assert state_LX_LX1_LX11.transitions_to[0].event is None
        assert state_LX_LX1_LX11.transitions_to[0].guard is None
        assert len(state_LX_LX1_LX11.transitions_to[0].effects) == 0
        assert state_LX_LX1_LX11.transitions_to[0].parent is state_LX_LX1_LX11.parent

        assert len(state_LX_LX1_LX11.transitions_entering_children) == 0
        assert len(state_LX_LX1_LX11.transitions_entering_children_simplified) == 1
        assert state_LX_LX1_LX11.transitions_entering_children_simplified == [None]

        # print(
        #     f'assert len(state_LX_LX1_LX11.transitions_to) == {len(state_LX_LX1_LX11.transitions_to)!r}')
        # for i, transition in enumerate(state_LX_LX1_LX11.transitions_to):
        #     if transition:
        #         print(
        #             f'assert state_LX_LX1_LX11.transitions_to[{i}].from_state == {state_LX_LX1_LX11.transitions_to[i].from_state!r}')
        #         print(
        #             f'assert state_LX_LX1_LX11.transitions_to[{i}].to_state == {state_LX_LX1_LX11.transitions_to[i].to_state!r}')
        #         if state_LX_LX1_LX11.transitions_to[i].event is not None:
        #             print(f'assert state_LX_LX1_LX11.transitions_to[{i}].event is not None')
        #             print(
        #                 f'assert state_LX_LX1_LX11.transitions_to[{i}].event.path == {state_LX_LX1_LX11.transitions_to[i].event.path!r}')
        #         else:
        #             print(f'assert state_LX_LX1_LX11.transitions_to[{i}].event is None')
        #         if state_LX_LX1_LX11.transitions_to[i].guard is not None:
        #             print(f'assert state_LX_LX1_LX11.transitions_to[{i}].guard is not None')
        #             print(
        #                 f'assert str(state_LX_LX1_LX11.transitions_to[{i}].guard) == {str(state_LX_LX1_LX11.transitions_to[i].guard)!r}')
        #         else:
        #             print(f'assert state_LX_LX1_LX11.transitions_to[{i}].guard is None')
        #         print(
        #             f'assert len(state_LX_LX1_LX11.transitions_to[{i}].effects) == {len(state_LX_LX1_LX11.transitions_to[i].effects)}')
        #         for j, effect in enumerate(state_LX_LX1_LX11.transitions_to[i].effects):
        #             print(
        #                 f'assert state_LX_LX1_LX11.transitions_to[{i}].effects[{j}] == {state_LX_LX1_LX11.transitions_to[i].effects[j]!r}')
        #         print(f'assert state_LX_LX1_LX11.transitions_to[{i}].parent is state_LX_LX1')
        #     else:
        #         print(f'assert state_LX_LX1_LX11.transitions_to[{i}] is None')

    def test_transitions(self, transition_1, transition_2, transition_3, transition_4, transition_5, transition_6,
                         transition_7, root_state_1, state_LX_LX1):
        assert transition_1.from_state == dsl_nodes.INIT_STATE
        assert transition_1.to_state == 'LX'
        assert transition_1.event is None
        assert transition_1.guard is None
        assert transition_1.effects == []
        assert transition_1.parent is None
        assert (transition_1.to_ast_node() ==
                dsl_nodes.TransitionDefinition(from_state=dsl_nodes.INIT_STATE, to_state='LX', event_id=None,
                                               condition_expr=None, post_operations=[]))

        assert transition_2.from_state == 'LX'
        assert transition_2.to_state == dsl_nodes.EXIT_STATE
        assert transition_2.event is None
        assert transition_2.guard is None
        assert transition_2.effects == []
        assert transition_2.parent is None
        assert (transition_2.to_ast_node() ==
                dsl_nodes.TransitionDefinition(from_state='LX', to_state=dsl_nodes.EXIT_STATE, event_id=None,
                                               condition_expr=None, post_operations=[]))

        assert transition_3.from_state == dsl_nodes.INIT_STATE
        assert transition_3.to_state == 'LX1'
        assert transition_3.event is None
        assert transition_3.guard is None
        assert transition_3.effects == []
        assert transition_3.parent is root_state_1
        assert (transition_3.to_ast_node() ==
                dsl_nodes.TransitionDefinition(from_state=dsl_nodes.INIT_STATE, to_state='LX1', event_id=None,
                                               condition_expr=None, post_operations=[]))

        assert transition_4.from_state == dsl_nodes.INIT_STATE
        assert transition_4.to_state == 'LX2'
        assert transition_4.event == Event(name='EEE', state_path=('LX',))
        assert transition_4.guard is None
        assert transition_4.effects == []
        assert transition_4.parent is root_state_1
        assert (transition_4.to_ast_node() ==
                dsl_nodes.TransitionDefinition(from_state=dsl_nodes.INIT_STATE, to_state='LX2',
                                               event_id=dsl_nodes.ChainID(['EEE']),
                                               condition_expr=None, post_operations=[]))

        assert transition_5.from_state == 'LX12'
        assert transition_5.to_state == 'LX14'
        assert transition_5.event == Event(name='E2', state_path=('LX', 'LX1', 'LX12'))
        assert transition_5.guard is None
        assert transition_5.effects == []
        assert transition_5.parent is state_LX_LX1
        assert (transition_5.to_ast_node() ==
                dsl_nodes.TransitionDefinition(from_state='LX12', to_state='LX14',
                                               event_id=dsl_nodes.ChainID(['LX12', 'E2']),
                                               condition_expr=None, post_operations=[]))

        assert transition_6.from_state == 'LX13'
        assert transition_6.to_state == dsl_nodes.EXIT_STATE
        assert transition_6.event == Event(name='E1', state_path=('LX', 'LX1', 'LX13'))
        assert transition_6.guard is None
        assert transition_6.effects == [Operation(var_name='a', expr=Integer(value=2))]
        assert transition_6.parent is state_LX_LX1
        assert (transition_6.to_ast_node() ==
                dsl_nodes.TransitionDefinition(from_state='LX13', to_state=dsl_nodes.EXIT_STATE,
                                               event_id=dsl_nodes.ChainID(path=['LX13', 'E1']), condition_expr=None,
                                               post_operations=[dsl_nodes.OperationAssignment(name='a',
                                                                                              expr=dsl_nodes.Integer(
                                                                                                  raw='2'))]))

        assert transition_7.from_state == 'LX2'
        assert transition_7.to_state == 'LX1'
        assert transition_7.event is None
        assert transition_7.guard == BinaryOp(x=Variable(name='a'), op='==', y=Integer(value=1))
        assert transition_7.effects == []
        assert transition_7.parent is root_state_1
        assert (transition_7.to_ast_node() ==
                dsl_nodes.TransitionDefinition(from_state='LX2', to_state='LX1', event_id=None,
                                               condition_expr=dsl_nodes.BinaryOp(expr1=dsl_nodes.Name(name='a'),
                                                                                 op='==',
                                                                                 expr2=dsl_nodes.Integer(raw='1')),
                                               post_operations=[]))

    def test_parse_duplicate_defs(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        def int a=3;
        state LX;
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert 'Duplicated variable definition' in err.msg
        assert 'def int a = 3;' in err.msg

    def test_parse_duplicate_state_name(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1;
            state LX2;
            state LX1 {
                enter abstract F;
            }

            [*] -> LX1;
            LX2 -> [*];
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Duplicate state name in namespace 'LX':" in err.msg
        assert 'state LX1 {' in err.msg
        assert 'state LX1;' not in err.msg

    def test_parse_unknown_from_state(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1;
            state LX2;

            [*] -> LX1;
            LX3 -> [*];
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown from state 'LX3' of transition:" in err.msg
        assert "LX3 -> [*];" in err.msg

    def test_parse_unknown_to_state(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1;
            state LX2;

            [*] -> LX3;
            LX1 -> [*];
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown to state 'LX3' of transition:" in err.msg
        assert "[*] -> LX3;" in err.msg

    def test_parse_unknown_guard_variable(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1;
            state LX2;

            [*] -> LX2 : if [a == 0];
            LX1 -> [*] : if [a == 0 && c > 0 || a - d > 0];
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown guard variable c, d in transition:" in err.msg
        assert "LX1 -> [*] : if [a == 0 && c > 0 || a - d > 0];" in err.msg

    def test_parse_unknown_transition_effect_variable(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1;
            state LX2;

            [*] -> LX2 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = b * (c + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown transition operation variable c in transition:" in err.msg
        assert "b = b * (c + 2);" in err.msg

    def test_parse_unknown_transition_effect_set_var(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1;
            state LX2;

            [*] -> LX2 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                c = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown transition operation variable c in transition:" in err.msg
        assert "c = a * (b + 2);" in err.msg

    def test_parse_unknown_no_enter_transition(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1;
            state LX2;

            LX1 -> LX2 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "At least 1 entry transition should be assigned in non-leaf state 'LX':" in err.msg
        assert "state LX {" in err.msg

    def test_parse_unknown_non_abstract_enter_variable(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                enter {
                    a = b + a * 2;
                    b = a + c;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown enter operation variable c in transition:" in err.msg
        assert "b = a + c;" in err.msg

    def test_parse_unknown_non_abstract_enter_set_var(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                enter {
                    a = b + a * 2;
                    c = a + 2;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown enter operation variable c in transition:" in err.msg
        assert "c = a + 2;" in err.msg

    def test_parse_unknown_non_abstract_during_non_leaf_aspect(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            during {
                a = b + a * 2;
                b = a + b;
            }
            state LX1 {

            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "For composite state 'LX', during must assign aspect to either 'before' or 'after':" in err.msg
        assert "during {" in err.msg
        assert "b = a + b;" in err.msg

    def test_parse_unknown_non_abstract_during_leaf_before_aspect(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                during before {
                    a = b + a * 2;
                    b = a + b;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "For leaf state 'LX1', during cannot assign aspect 'before':" in err.msg
        assert "during before {" in err.msg
        assert "b = a + b;" in err.msg

    def test_parse_unknown_non_abstract_during_leaf_after_aspect(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                during after {
                    a = b + a * 2;
                    b = a + b;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "For leaf state 'LX1', during cannot assign aspect 'after':" in err.msg
        assert "during after {" in err.msg
        assert "b = a + b;" in err.msg

    def test_parse_unknown_non_abstract_during_variable(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                during {
                    a = b + a * 2;
                    b = a + c;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown during operation variable c in transition:" in err.msg
        assert "b = a + c;" in err.msg

    def test_parse_unknown_non_abstract_during_set_var(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                during {
                    a = b + a * 2;
                    c = a + 2;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown during operation variable c in transition:" in err.msg
        assert "c = a + 2;" in err.msg

    def test_parse_unknown_non_abstract_exit_variable(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                exit {
                    a = b + a * 2;
                    b = a + c;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown exit operation variable c in transition:" in err.msg
        assert "b = a + c;" in err.msg

    def test_parse_unknown_non_abstract_exit_set_var(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                exit {
                    a = b + a * 2;
                    c = a + 2;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown exit operation variable c in transition:" in err.msg
        assert "c = a + 2;" in err.msg

    def test_to_plantuml(self, demo_model_1, expected_plantuml_code, text_aligner):
        text_aligner.assert_equal(
            expect=expected_plantuml_code,
            actual=demo_model_1.to_plantuml(),
        )

    def test_parse_unknown_non_abstract_during_aspect_variable(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                >> during before {
                    a = b + a * 2;
                    b = a + c;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown during aspect variable c in transition:" in err.msg
        assert "b = a + c;" in err.msg

    def test_parse_unknown_non_abstract_during_aspect_variable_set(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                >> during before {
                    a = b + a * 2;
                    c = a + 2;
                }
            }
            state LX2;

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Unknown during aspect variable c in transition:" in err.msg
        assert "c = a + 2;" in err.msg
