import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLTransition:
    @pytest.mark.parametrize(['input_text', 'expected'], [
        (
                """
                def int counter = 0;
                state Main;
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='counter', type='int', expr=Integer(raw='0'))],
                                       root_state=StateDefinition(name='Main', substates=[], transitions=[], enters=[],
                                                                  durings=[], exits=[]))
        ),  # Simple state machine with a single leaf state and an integer definition
        (
                """
                def float x = 3.14;
                def int count = 10;
                state Initial;
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='x', type='float', expr=Float(raw='3.14')),
                                                    DefAssignment(name='count', type='int', expr=Integer(raw='10'))],
                                       root_state=StateDefinition(name='Initial', substates=[], transitions=[],
                                                                  enters=[], durings=[], exits=[]))
        ),  # State machine with multiple variable definitions and a single leaf state
        (
                """
                state Main {
                    state SubState1;
                    state SubState2;
                }
                """,
                StateMachineDSLProgram(definitions=[], root_state=StateDefinition(name='Main', substates=[
                    StateDefinition(name='SubState1', substates=[], transitions=[], enters=[], durings=[], exits=[]),
                    StateDefinition(name='SubState2', substates=[], transitions=[], enters=[], durings=[], exits=[])],
                                                                                  transitions=[], enters=[], durings=[],
                                                                                  exits=[]))
        ),  # Composite state containing two leaf states
        (
                """
                def int timer = 0;
                state Main {
                    [*] -> Ready;
                    Ready -> Processing: if [timer > 10];
                    Processing -> Done;
                    Done -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='timer', type='int', expr=Integer(raw='0'))],
                                       root_state=StateDefinition(name='Main', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Ready', event_id=None,
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Ready', to_state='Processing',
                                                                event_id=None,
                                                                condition_expr=BinaryOp(expr1=Name(name='timer'),
                                                                                        op='>',
                                                                                        expr2=Integer(raw='10')),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='Processing', to_state='Done', event_id=None,
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Done', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # Complete state machine with entry, normal, and exit transitions with a condition
        (
                """
                state Process {
                    [*] -> Idle;
                    Idle -> Active: if [true];
                    Active -> Complete;
                    Complete -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[], root_state=StateDefinition(name='Process', substates=[],
                                                                                  transitions=[TransitionDefinition(
                                                                                      from_state=INIT_STATE,
                                                                                      to_state='Idle', event_id=None,
                                                                                      condition_expr=None,
                                                                                      post_operations=[]),
                                                                                      TransitionDefinition(
                                                                                          from_state='Idle',
                                                                                          to_state='Active',
                                                                                          event_id=None,
                                                                                          condition_expr=Boolean(
                                                                                              raw='true'),
                                                                                          post_operations=[]),
                                                                                      TransitionDefinition(
                                                                                          from_state='Active',
                                                                                          to_state='Complete',
                                                                                          event_id=None,
                                                                                          condition_expr=None,
                                                                                          post_operations=[]),
                                                                                      TransitionDefinition(
                                                                                          from_state='Complete',
                                                                                          to_state=EXIT_STATE,
                                                                                          event_id=None,
                                                                                          condition_expr=None,
                                                                                          post_operations=[])],
                                                                                  enters=[], durings=[], exits=[]))
        ),  # State machine with entry, normal transitions with boolean condition, and exit transition
        (
                """
                def int count = 0;
                state Counter {
                    [*] -> Counting effect {
                        count = count + 1;
                    }
                    Counting -> Done: if [count > 10];
                    Done -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='count', type='int', expr=Integer(raw='0'))],
                                       root_state=StateDefinition(name='Counter', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Counting',
                                                                event_id=None, condition_expr=None, post_operations=[
                                                   OperationAssignment(name='count',
                                                                       expr=BinaryOp(expr1=Name(name='count'),
                                                                                     op='+',
                                                                                     expr2=Integer(raw='1')))]),
                                           TransitionDefinition(from_state='Counting', to_state='Done', event_id=None,
                                                                condition_expr=BinaryOp(expr1=Name(name='count'),
                                                                                        op='>',
                                                                                        expr2=Integer(raw='10')),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='Done', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # State machine with effect operation in entry transition
        (
                """
                def float temperature = 25.0;
                state ThermostatControl {
                    state Heating;
                    state Cooling;
                    state Idle;
        
                    [*] -> Idle;
                    Idle -> Heating: if [temperature < 20.0];
                    Idle -> Cooling: if [temperature > 26.0];
                    Heating -> Idle: if [temperature >= 22.0];
                    Cooling -> Idle: if [temperature <= 24.0];
                }
                """,
                StateMachineDSLProgram(
                    definitions=[DefAssignment(name='temperature', type='float', expr=Float(raw='25.0'))],
                    root_state=StateDefinition(name='ThermostatControl',
                                               substates=[StateDefinition(name='Heating', substates=[], transitions=[],
                                                                          enters=[], durings=[], exits=[]),
                                                          StateDefinition(name='Cooling', substates=[], transitions=[],
                                                                          enters=[], durings=[], exits=[]),
                                                          StateDefinition(name='Idle', substates=[], transitions=[],
                                                                          enters=[], durings=[], exits=[])],
                                               transitions=[TransitionDefinition(from_state=INIT_STATE, to_state='Idle',
                                                                                 event_id=None, condition_expr=None,
                                                                                 post_operations=[]),
                                                            TransitionDefinition(from_state='Idle', to_state='Heating',
                                                                                 event_id=None, condition_expr=BinaryOp(
                                                                    expr1=Name(name='temperature'), op='<',
                                                                    expr2=Float(raw='20.0')), post_operations=[]),
                                                            TransitionDefinition(from_state='Idle', to_state='Cooling',
                                                                                 event_id=None, condition_expr=BinaryOp(
                                                                    expr1=Name(name='temperature'), op='>',
                                                                    expr2=Float(raw='26.0')), post_operations=[]),
                                                            TransitionDefinition(from_state='Heating', to_state='Idle',
                                                                                 event_id=None, condition_expr=BinaryOp(
                                                                    expr1=Name(name='temperature'), op='>=',
                                                                    expr2=Float(raw='22.0')), post_operations=[]),
                                                            TransitionDefinition(from_state='Cooling', to_state='Idle',
                                                                                 event_id=None, condition_expr=BinaryOp(
                                                                    expr1=Name(name='temperature'), op='<=',
                                                                    expr2=Float(raw='24.0')), post_operations=[])],
                                               enters=[], durings=[], exits=[]))
        ),  # Complex state machine with multiple states and conditional transitions
        (
                """
                def int x = 0;
                state Main {
                    state A {
                        state A1;
                        state A2;
                        A1 -> A2: if [x > 5];
                    }
                    state B;
                    A -> B: if [x > 10];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='x', type='int', expr=Integer(raw='0'))],
                                       root_state=StateDefinition(name='Main', substates=[StateDefinition(name='A',
                                                                                                          substates=[
                                                                                                              StateDefinition(
                                                                                                                  name='A1',
                                                                                                                  substates=[],
                                                                                                                  transitions=[],
                                                                                                                  enters=[],
                                                                                                                  durings=[],
                                                                                                                  exits=[]),
                                                                                                              StateDefinition(
                                                                                                                  name='A2',
                                                                                                                  substates=[],
                                                                                                                  transitions=[],
                                                                                                                  enters=[],
                                                                                                                  durings=[],
                                                                                                                  exits=[])],
                                                                                                          transitions=[
                                                                                                              TransitionDefinition(
                                                                                                                  from_state='A1',
                                                                                                                  to_state='A2',
                                                                                                                  event_id=None,
                                                                                                                  condition_expr=BinaryOp(
                                                                                                                      expr1=Name(
                                                                                                                          name='x'),
                                                                                                                      op='>',
                                                                                                                      expr2=Integer(
                                                                                                                          raw='5')),
                                                                                                                  post_operations=[])],
                                                                                                          enters=[],
                                                                                                          durings=[],
                                                                                                          exits=[]),
                                                                                          StateDefinition(name='B',
                                                                                                          substates=[],
                                                                                                          transitions=[],
                                                                                                          enters=[],
                                                                                                          durings=[],
                                                                                                          exits=[])],
                                                                  transitions=[
                                                                      TransitionDefinition(from_state='A', to_state='B',
                                                                                           event_id=None,
                                                                                           condition_expr=BinaryOp(
                                                                                               expr1=Name(name='x'),
                                                                                               op='>',
                                                                                               expr2=Integer(raw='10')),
                                                                                           post_operations=[])],
                                                                  enters=[], durings=[], exits=[]))
        ),  # Nested composite states with transitions at different levels
        (
                """
                def int counter = 0;
                state Process {
                    [*] -> Start effect {
                        counter = counter + 1;
                    }
                    Start -> Middle: chain_id;
                    Middle -> End: if [counter > 5] effect {
                        counter = counter * 2;
                    }
                    End -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='counter', type='int', expr=Integer(raw='0'))],
                                       root_state=StateDefinition(name='Process', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Start', event_id=None,
                                                                condition_expr=None, post_operations=[
                                                   OperationAssignment(name='counter',
                                                                       expr=BinaryOp(expr1=Name(name='counter'),
                                                                                     op='+',
                                                                                     expr2=Integer(raw='1')))]),
                                           TransitionDefinition(from_state='Start', to_state='Middle',
                                                                event_id=ChainID(path=['chain_id']),
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Middle', to_state='End', event_id=None,
                                                                condition_expr=BinaryOp(expr1=Name(name='counter'),
                                                                                        op='>', expr2=Integer(raw='5')),
                                                                post_operations=[
                                                                    OperationAssignment(name='counter',
                                                                                        expr=BinaryOp(expr1=Name(
                                                                                            name='counter'),
                                                                                            op='*',
                                                                                            expr2=Integer(
                                                                                                raw='2')))]),
                                           TransitionDefinition(from_state='End', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # State machine with chain_id transition and effect operations
        (
                """
                def float x = 1.0;
                def float y = 2.0;
                state Calculator {
                    state Add {
                        [*] -> Computing;
                        Computing -> Done;
                        Done -> [*];
                    }
                    state Multiply {
                        [*] -> Computing;
                        Computing -> Done;
                        Done -> [*];
                    }
                    [*] -> Add: if [x < y];
                    [*] -> Multiply: if [x >= y];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='x', type='float', expr=Float(raw='1.0')),
                                                    DefAssignment(name='y', type='float', expr=Float(raw='2.0'))],
                                       root_state=StateDefinition(name='Calculator', substates=[
                                           StateDefinition(name='Add', substates=[], transitions=[
                                               TransitionDefinition(from_state=INIT_STATE, to_state='Computing',
                                                                    event_id=None, condition_expr=None,
                                                                    post_operations=[]),
                                               TransitionDefinition(from_state='Computing', to_state='Done',
                                                                    event_id=None, condition_expr=None,
                                                                    post_operations=[]),
                                               TransitionDefinition(from_state='Done', to_state=EXIT_STATE,
                                                                    event_id=None, condition_expr=None,
                                                                    post_operations=[])], enters=[], durings=[],
                                                           exits=[]),
                                           StateDefinition(name='Multiply', substates=[], transitions=[
                                               TransitionDefinition(from_state=INIT_STATE, to_state='Computing',
                                                                    event_id=None, condition_expr=None,
                                                                    post_operations=[]),
                                               TransitionDefinition(from_state='Computing', to_state='Done',
                                                                    event_id=None, condition_expr=None,
                                                                    post_operations=[]),
                                               TransitionDefinition(from_state='Done', to_state=EXIT_STATE,
                                                                    event_id=None, condition_expr=None,
                                                                    post_operations=[])], enters=[], durings=[],
                                                           exits=[])], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Add', event_id=None,
                                                                condition_expr=BinaryOp(expr1=Name(name='x'), op='<',
                                                                                        expr2=Name(name='y')),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Multiply',
                                                                event_id=None,
                                                                condition_expr=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                        expr2=Name(name='y')),
                                                                post_operations=[])], enters=[], durings=[], exits=[]))
        ),  # State machine with multiple composite states and conditional entry transitions
        (
                """
                def int status = 0;
                state StatusHandler {
                    [*] -> Checking effect {
                        status = status + 1;
                    }
                    Checking -> Success: if [status > 0] effect {
                        status = 100;
                    }
                    Checking -> Failure: if [status <= 0] effect {
                        status = -1;
                    }
                    Success -> [*];
                    Failure -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='status', type='int', expr=Integer(raw='0'))],
                                       root_state=StateDefinition(name='StatusHandler', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Checking',
                                                                event_id=None, condition_expr=None, post_operations=[
                                                   OperationAssignment(name='status',
                                                                       expr=BinaryOp(expr1=Name(name='status'),
                                                                                     op='+',
                                                                                     expr2=Integer(raw='1')))]),
                                           TransitionDefinition(from_state='Checking', to_state='Success',
                                                                event_id=None,
                                                                condition_expr=BinaryOp(expr1=Name(name='status'),
                                                                                        op='>', expr2=Integer(raw='0')),
                                                                post_operations=[
                                                                    OperationAssignment(name='status',
                                                                                        expr=Integer(
                                                                                            raw='100'))]),
                                           TransitionDefinition(from_state='Checking', to_state='Failure',
                                                                event_id=None,
                                                                condition_expr=BinaryOp(expr1=Name(name='status'),
                                                                                        op='<=',
                                                                                        expr2=Integer(raw='0')),
                                                                post_operations=[
                                                                    OperationAssignment(name='status',
                                                                                        expr=UnaryOp(op='-',
                                                                                                     expr=Integer(
                                                                                                         raw='1')))]),
                                           TransitionDefinition(from_state='Success', to_state=EXIT_STATE,
                                                                event_id=None, condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Failure', to_state=EXIT_STATE,
                                                                event_id=None, condition_expr=None,
                                                                post_operations=[])], enters=[], durings=[], exits=[]))
        ),  # State machine with multiple effect operations in different transitions
        (
                """
                def int value = 0x1A;
                state HexTest {
                    [*] -> Start;
                    Start -> End: if [value == 0x1A];
                    End -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='value', type='int', expr=HexInt(raw='0x1A'))],
                                       root_state=StateDefinition(name='HexTest', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Start', event_id=None,
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Start', to_state='End', event_id=None,
                                                                condition_expr=BinaryOp(expr1=Name(name='value'),
                                                                                        op='==',
                                                                                        expr2=HexInt(raw='0x1A')),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='End', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # State machine using hexadecimal integer in definition and condition
        (
                """
                def float pi_val = pi;
                def float e_val = E;
                state MathConstants {
                    [*] -> Processing: if [pi_val > e_val];
                    Processing -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='pi_val', type='float', expr=Constant(raw='pi')),
                                                    DefAssignment(name='e_val', type='float', expr=Constant(raw='E'))],
                                       root_state=StateDefinition(name='MathConstants', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Processing',
                                                                event_id=None,
                                                                condition_expr=BinaryOp(expr1=Name(name='pi_val'),
                                                                                        op='>',
                                                                                        expr2=Name(name='e_val')),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='Processing', to_state=EXIT_STATE,
                                                                event_id=None, condition_expr=None,
                                                                post_operations=[])], enters=[], durings=[], exits=[]))
        ),  # State machine using mathematical constants in definitions and conditions
        (
                """
                def int a = 5;
                def int b = 10;
                state ConditionalTest {
                    [*] -> Evaluate;
                    Evaluate -> TrueState: if [(a < b) ? true : false];
                    Evaluate -> FalseState: if [(a > b) ? true : false];
                    TrueState -> [*];
                    FalseState -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='a', type='int', expr=Integer(raw='5')),
                                                    DefAssignment(name='b', type='int', expr=Integer(raw='10'))],
                                       root_state=StateDefinition(name='ConditionalTest', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Evaluate',
                                                                event_id=None, condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Evaluate', to_state='TrueState',
                                                                event_id=None, condition_expr=ConditionalOp(
                                                   cond=BinaryOp(expr1=Name(name='a'), op='<', expr2=Name(name='b')),
                                                   value_true=Boolean(raw='true'), value_false=Boolean(raw='false')),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='Evaluate', to_state='FalseState',
                                                                event_id=None, condition_expr=ConditionalOp(
                                                   cond=BinaryOp(expr1=Name(name='a'), op='>', expr2=Name(name='b')),
                                                   value_true=Boolean(raw='true'), value_false=Boolean(raw='false')),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='TrueState', to_state=EXIT_STATE,
                                                                event_id=None, condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='FalseState', to_state=EXIT_STATE,
                                                                event_id=None, condition_expr=None,
                                                                post_operations=[])], enters=[], durings=[], exits=[]))
        ),  # State machine using conditional C-style expressions in transition conditions
        (
                """
                def float angle = 0.0;
                state Trigonometry {
                    [*] -> Calculate;
                    Calculate -> Result: if [sin(angle) < 0.5];
                    Result -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='angle', type='float', expr=Float(raw='0.0'))],
                                       root_state=StateDefinition(name='Trigonometry', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Calculate',
                                                                event_id=None, condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Calculate', to_state='Result',
                                                                event_id=None, condition_expr=BinaryOp(
                                                   expr1=UFunc(func='sin', expr=Name(name='angle')), op='<',
                                                   expr2=Float(raw='0.5')), post_operations=[]),
                                           TransitionDefinition(from_state='Result', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # State machine using mathematical functions in transition conditions
        (
                """
                def int flag = 1;
                state BitOperations {
                    [*] -> Process;
                    Process -> Done: if [(flag & 1) == 1];
                    Done -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='flag', type='int', expr=Integer(raw='1'))],
                                       root_state=StateDefinition(name='BitOperations', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Process',
                                                                event_id=None, condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Process', to_state='Done', event_id=None,
                                                                condition_expr=BinaryOp(expr1=Paren(
                                                                    expr=BinaryOp(expr1=Name(name='flag'), op='&',
                                                                                  expr2=Integer(raw='1'))), op='==',
                                                                    expr2=Integer(raw='1')),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='Done', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # State machine using bitwise operations in transition conditions
        (
                """
                def int x = 10;
                def int y = 20;
                state LogicalTest {
                    [*] -> Check;
                    Check -> Success: if [x < y && x > 0];
                    Check -> Failure: if [x >= y || x <= 0];
                    Success -> [*];
                    Failure -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='x', type='int', expr=Integer(raw='10')),
                                                    DefAssignment(name='y', type='int', expr=Integer(raw='20'))],
                                       root_state=StateDefinition(name='LogicalTest', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Check', event_id=None,
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Check', to_state='Success', event_id=None,
                                                                condition_expr=BinaryOp(
                                                                    expr1=BinaryOp(expr1=Name(name='x'), op='<',
                                                                                   expr2=Name(name='y')), op='&&',
                                                                    expr2=BinaryOp(expr1=Name(name='x'), op='>',
                                                                                   expr2=Integer(raw='0'))),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='Check', to_state='Failure', event_id=None,
                                                                condition_expr=BinaryOp(
                                                                    expr1=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                   expr2=Name(name='y')), op='||',
                                                                    expr2=BinaryOp(expr1=Name(name='x'), op='<=',
                                                                                   expr2=Integer(raw='0'))),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='Success', to_state=EXIT_STATE,
                                                                event_id=None, condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Failure', to_state=EXIT_STATE,
                                                                event_id=None, condition_expr=None,
                                                                post_operations=[])], enters=[], durings=[], exits=[]))
        ),  # State machine using logical AND/OR operations in transition conditions
        (
                """
                def int counter = 0;
                state EmptyTransition {
                    [*] -> Start;
                    Start -> Middle;
                    Middle -> End;
                    End -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='counter', type='int', expr=Integer(raw='0'))],
                                       root_state=StateDefinition(name='EmptyTransition', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Start', event_id=None,
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Start', to_state='Middle', event_id=None,
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Middle', to_state='End', event_id=None,
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='End', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # State machine with transitions without conditions or effect operations
        (
                """
                def int x = 5;
                state SemicolonTest {
                    ;
                    state Inner;
                    ;
                    Inner -> [*];
                    ;
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='x', type='int', expr=Integer(raw='5'))],
                                       root_state=StateDefinition(name='SemicolonTest', substates=[
                                           StateDefinition(name='Inner', substates=[], transitions=[], enters=[],
                                                           durings=[], exits=[])], transitions=[
                                           TransitionDefinition(from_state='Inner', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # State machine with empty statements (lone semicolons)
        (
                """
                def float temp = 22.5;
                state NestedConditions {
                    [*] -> Check;
                    Check -> Hot: if [temp > 25.0 && (temp < 30.0 || temp == 35.0)];
                    Check -> Cold: if [temp < 20.0 && (temp > 15.0 || temp == 10.0)];
                    Hot -> [*];
                    Cold -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='temp', type='float', expr=Float(raw='22.5'))],
                                       root_state=StateDefinition(name='NestedConditions', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Check', event_id=None,
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Check', to_state='Hot', event_id=None,
                                                                condition_expr=BinaryOp(
                                                                    expr1=BinaryOp(expr1=Name(name='temp'), op='>',
                                                                                   expr2=Float(raw='25.0')), op='&&',
                                                                    expr2=Paren(expr=BinaryOp(
                                                                        expr1=BinaryOp(expr1=Name(name='temp'), op='<',
                                                                                       expr2=Float(raw='30.0')),
                                                                        op='||',
                                                                        expr2=BinaryOp(expr1=Name(name='temp'), op='==',
                                                                                       expr2=Float(raw='35.0'))))),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='Check', to_state='Cold', event_id=None,
                                                                condition_expr=BinaryOp(
                                                                    expr1=BinaryOp(expr1=Name(name='temp'), op='<',
                                                                                   expr2=Float(raw='20.0')), op='&&',
                                                                    expr2=Paren(expr=BinaryOp(
                                                                        expr1=BinaryOp(expr1=Name(name='temp'), op='>',
                                                                                       expr2=Float(raw='15.0')),
                                                                        op='||',
                                                                        expr2=BinaryOp(expr1=Name(name='temp'), op='==',
                                                                                       expr2=Float(raw='10.0'))))),
                                                                post_operations=[]),
                                           TransitionDefinition(from_state='Hot', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Cold', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # State machine with complex nested conditional expressions
        (
                """
                def int a = 1 + 2 * 3;
                def float b = 2.5 ** 2;
                state ExpressionTest {
                    [*] -> Calculate;
                    Calculate -> Result: if [a * b > 20.0];
                    Result -> [*];
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='a', type='int',
                                                                  expr=BinaryOp(expr1=Integer(raw='1'), op='+',
                                                                                expr2=BinaryOp(expr1=Integer(raw='2'),
                                                                                               op='*', expr2=Integer(
                                                                                        raw='3')))),
                                                    DefAssignment(name='b', type='float',
                                                                  expr=BinaryOp(expr1=Float(raw='2.5'), op='**',
                                                                                expr2=Integer(raw='2')))],
                                       root_state=StateDefinition(name='ExpressionTest', substates=[], transitions=[
                                           TransitionDefinition(from_state=INIT_STATE, to_state='Calculate',
                                                                event_id=None, condition_expr=None, post_operations=[]),
                                           TransitionDefinition(from_state='Calculate', to_state='Result',
                                                                event_id=None, condition_expr=BinaryOp(
                                                   expr1=BinaryOp(expr1=Name(name='a'), op='*', expr2=Name(name='b')),
                                                   op='>', expr2=Float(raw='20.0')), post_operations=[]),
                                           TransitionDefinition(from_state='Result', to_state=EXIT_STATE, event_id=None,
                                                                condition_expr=None, post_operations=[])], enters=[],
                                                                  durings=[], exits=[]))
        ),  # State machine with complex arithmetic expressions in definitions and conditions

        (
                """
                def int x = 0;
                state A {
        
                    enter {
                        x = 1;
                    }
        
                    B -> C :: E1;
                    C -> C : if [x == 1] effect {
                        x = 0;
                    }
        
                    state B;
                    state C {
                        enter abstract F1;
                        enter abstract F2 /*
                            this is the comment of F2
                        */
        
                        during before abstract /*
                            this is another during
                        */
        
                        state D {
                            during {
                                x = x + 1;
                            }
                            state EX;
                            [*] -> EX : E1;
                        }
                        [*] -> D :: E2;
                        D -> [*] : if [x > 0] effect {
                            x = ((x + ((-1))));
                            x = x / 2;
                        }
        
                        exit {
                            x = 21;
                        }
                    }
        
                    [*] -> B;
                    C -> [*] effect {};
        
                    C -> B :: E2;
                    C -> B : C.D.E1;
        
                    during after abstract Af;
        
                    ;;;
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='x', type='int', expr=Integer(raw='0'))],
                                       root_state=StateDefinition(name='A', substates=[
                                           StateDefinition(name='B', substates=[], transitions=[], enters=[],
                                                           durings=[], exits=[]), StateDefinition(name='C', substates=[
                                               StateDefinition(name='D', substates=[
                                                   StateDefinition(name='EX', substates=[], transitions=[], enters=[],
                                                                   durings=[], exits=[])], transitions=[
                                                   TransitionDefinition(from_state=INIT_STATE, to_state='EX',
                                                                        event_id=ChainID(path=['E1']),
                                                                        condition_expr=None, post_operations=[])],
                                                               enters=[], durings=[DuringOperations(aspect=None,
                                                                                                    operations=[
                                                                                                        OperationAssignment(
                                                                                                            name='x',
                                                                                                            expr=BinaryOp(
                                                                                                                expr1=Name(
                                                                                                                    name='x'),
                                                                                                                op='+',
                                                                                                                expr2=Integer(
                                                                                                                    raw='1')))])],
                                                               exits=[])], transitions=[
                                               TransitionDefinition(from_state=INIT_STATE, to_state='D',
                                                                    event_id=ChainID(path=['E2']), condition_expr=None,
                                                                    post_operations=[]),
                                               TransitionDefinition(from_state='D', to_state=EXIT_STATE, event_id=None,
                                                                    condition_expr=BinaryOp(expr1=Name(name='x'),
                                                                                            op='>',
                                                                                            expr2=Integer(raw='0')),
                                                                    post_operations=[OperationAssignment(name='x',
                                                                                                         expr=Paren(
                                                                                                             expr=Paren(
                                                                                                                 expr=BinaryOp(
                                                                                                                     expr1=Name(
                                                                                                                         name='x'),
                                                                                                                     op='+',
                                                                                                                     expr2=Paren(
                                                                                                                         expr=Paren(
                                                                                                                             expr=UnaryOp(
                                                                                                                                 op='-',
                                                                                                                                 expr=Integer(
                                                                                                                                     raw='1')))))))),
                                                                                     OperationAssignment(name='x',
                                                                                                         expr=BinaryOp(
                                                                                                             expr1=Name(
                                                                                                                 name='x'),
                                                                                                             op='/',
                                                                                                             expr2=Integer(
                                                                                                                 raw='2')))])],
                                                                                                  enters=[
                                                                                                      EnterAbstractFunction(
                                                                                                          name='F1',
                                                                                                          doc=None),
                                                                                                      EnterAbstractFunction(
                                                                                                          name='F2',
                                                                                                          doc='this is the comment of F2')],
                                                                                                  durings=[
                                                                                                      DuringAbstractFunction(
                                                                                                          name=None,
                                                                                                          aspect='before',
                                                                                                          doc='this is another during')],
                                                                                                  exits=[ExitOperations(
                                                                                                      operations=[
                                                                                                          OperationAssignment(
                                                                                                              name='x',
                                                                                                              expr=Integer(
                                                                                                                  raw='21'))])])],
                                                                  transitions=[
                                                                      TransitionDefinition(from_state='B', to_state='C',
                                                                                           event_id=ChainID(
                                                                                               path=['B', 'E1']),
                                                                                           condition_expr=None,
                                                                                           post_operations=[]),
                                                                      TransitionDefinition(from_state='C', to_state='C',
                                                                                           event_id=None,
                                                                                           condition_expr=BinaryOp(
                                                                                               expr1=Name(name='x'),
                                                                                               op='==',
                                                                                               expr2=Integer(raw='1')),
                                                                                           post_operations=[
                                                                                               OperationAssignment(
                                                                                                   name='x',
                                                                                                   expr=Integer(
                                                                                                       raw='0'))]),
                                                                      TransitionDefinition(from_state=INIT_STATE,
                                                                                           to_state='B', event_id=None,
                                                                                           condition_expr=None,
                                                                                           post_operations=[]),
                                                                      TransitionDefinition(from_state='C',
                                                                                           to_state=EXIT_STATE,
                                                                                           event_id=None,
                                                                                           condition_expr=None,
                                                                                           post_operations=[]),
                                                                      TransitionDefinition(from_state='C', to_state='B',
                                                                                           event_id=ChainID(
                                                                                               path=['C', 'E2']),
                                                                                           condition_expr=None,
                                                                                           post_operations=[]),
                                                                      TransitionDefinition(from_state='C', to_state='B',
                                                                                           event_id=ChainID(
                                                                                               path=['C', 'D', 'E1']),
                                                                                           condition_expr=None,
                                                                                           post_operations=[])],
                                                                  enters=[EnterOperations(operations=[
                                                                      OperationAssignment(name='x',
                                                                                          expr=Integer(raw='1'))])],
                                                                  durings=[
                                                                      DuringAbstractFunction(name='Af', aspect='after',
                                                                                             doc=None)], exits=[]))
        ),  # A simpler full demo
        (
                """
                def int a = 0;
                def int b = 0x0;
        
                state LX {
                    [*] -> LX1;
        
                    enter {
                        b = 0;
                    }
        
                    exit {
                        b = 0;
                    }
        
                    state LX1 {
                        during before abstract BeforeLX1Enter;
                        during after abstract AfterLX1Enter /*
                            this is the comment line
                        */
        
                        state LX11 {
                            enter abstract LX11Enter;
                            exit abstract LX11Exit;
                            during abstract LX11During; 
                        }
                        state LX12;
                        state LX13;
                        state LX14 {
                            during {
                                b = 0x10;
                            }
                        }
        
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
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='a', type='int', expr=Integer(raw='0')),
                                                    DefAssignment(name='b', type='int', expr=HexInt(raw='0x0'))],
                                       root_state=StateDefinition(name='LX', substates=[StateDefinition(name='LX1',
                                                                                                        substates=[
                                                                                                            StateDefinition(
                                                                                                                name='LX11',
                                                                                                                substates=[],
                                                                                                                transitions=[],
                                                                                                                enters=[
                                                                                                                    EnterAbstractFunction(
                                                                                                                        name='LX11Enter',
                                                                                                                        doc=None)],
                                                                                                                durings=[
                                                                                                                    DuringAbstractFunction(
                                                                                                                        name='LX11During',
                                                                                                                        aspect=None,
                                                                                                                        doc=None)],
                                                                                                                exits=[
                                                                                                                    ExitAbstractFunction(
                                                                                                                        name='LX11Exit',
                                                                                                                        doc=None)]),
                                                                                                            StateDefinition(
                                                                                                                name='LX12',
                                                                                                                substates=[],
                                                                                                                transitions=[],
                                                                                                                enters=[],
                                                                                                                durings=[],
                                                                                                                exits=[]),
                                                                                                            StateDefinition(
                                                                                                                name='LX13',
                                                                                                                substates=[],
                                                                                                                transitions=[],
                                                                                                                enters=[],
                                                                                                                durings=[],
                                                                                                                exits=[]),
                                                                                                            StateDefinition(
                                                                                                                name='LX14',
                                                                                                                substates=[],
                                                                                                                transitions=[],
                                                                                                                enters=[],
                                                                                                                durings=[
                                                                                                                    DuringOperations(
                                                                                                                        aspect=None,
                                                                                                                        operations=[
                                                                                                                            OperationAssignment(
                                                                                                                                name='b',
                                                                                                                                expr=HexInt(
                                                                                                                                    raw='0x10'))])],
                                                                                                                exits=[])],
                                                                                                        transitions=[
                                                                                                            TransitionDefinition(
                                                                                                                from_state=INIT_STATE,
                                                                                                                to_state='LX11',
                                                                                                                event_id=None,
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX11',
                                                                                                                to_state='LX12',
                                                                                                                event_id=ChainID(
                                                                                                                    path=[
                                                                                                                        'LX11',
                                                                                                                        'E1']),
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX12',
                                                                                                                to_state='LX13',
                                                                                                                event_id=ChainID(
                                                                                                                    path=[
                                                                                                                        'LX12',
                                                                                                                        'E1']),
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX12',
                                                                                                                to_state='LX14',
                                                                                                                event_id=ChainID(
                                                                                                                    path=[
                                                                                                                        'LX12',
                                                                                                                        'E2']),
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX13',
                                                                                                                to_state=EXIT_STATE,
                                                                                                                event_id=ChainID(
                                                                                                                    path=[
                                                                                                                        'LX13',
                                                                                                                        'E1']),
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[
                                                                                                                    OperationAssignment(
                                                                                                                        name='a',
                                                                                                                        expr=HexInt(
                                                                                                                            raw='0x2'))]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX13',
                                                                                                                to_state=EXIT_STATE,
                                                                                                                event_id=ChainID(
                                                                                                                    path=[
                                                                                                                        'LX13',
                                                                                                                        'E2']),
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[
                                                                                                                    OperationAssignment(
                                                                                                                        name='a',
                                                                                                                        expr=HexInt(
                                                                                                                            raw='0x3'))]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX13',
                                                                                                                to_state='LX14',
                                                                                                                event_id=ChainID(
                                                                                                                    path=[
                                                                                                                        'LX13',
                                                                                                                        'E3']),
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX13',
                                                                                                                to_state='LX14',
                                                                                                                event_id=ChainID(
                                                                                                                    path=[
                                                                                                                        'LX13',
                                                                                                                        'E4']),
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX14',
                                                                                                                to_state='LX12',
                                                                                                                event_id=ChainID(
                                                                                                                    path=[
                                                                                                                        'LX14',
                                                                                                                        'E1']),
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX14',
                                                                                                                to_state=EXIT_STATE,
                                                                                                                event_id=ChainID(
                                                                                                                    path=[
                                                                                                                        'LX14',
                                                                                                                        'E2']),
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[
                                                                                                                    OperationAssignment(
                                                                                                                        name='a',
                                                                                                                        expr=HexInt(
                                                                                                                            raw='0x1'))])],
                                                                                                        enters=[],
                                                                                                        durings=[
                                                                                                            DuringAbstractFunction(
                                                                                                                name='BeforeLX1Enter',
                                                                                                                aspect='before',
                                                                                                                doc=None),
                                                                                                            DuringAbstractFunction(
                                                                                                                name='AfterLX1Enter',
                                                                                                                aspect='after',
                                                                                                                doc='this is the comment line')],
                                                                                                        exits=[]),
                                                                                        StateDefinition(name='LX2',
                                                                                                        substates=[
                                                                                                            StateDefinition(
                                                                                                                name='LX21',
                                                                                                                substates=[
                                                                                                                    StateDefinition(
                                                                                                                        name='LX211',
                                                                                                                        substates=[],
                                                                                                                        transitions=[],
                                                                                                                        enters=[],
                                                                                                                        durings=[],
                                                                                                                        exits=[]),
                                                                                                                    StateDefinition(
                                                                                                                        name='LX212',
                                                                                                                        substates=[],
                                                                                                                        transitions=[],
                                                                                                                        enters=[],
                                                                                                                        durings=[],
                                                                                                                        exits=[])],
                                                                                                                transitions=[
                                                                                                                    TransitionDefinition(
                                                                                                                        from_state=INIT_STATE,
                                                                                                                        to_state='LX211',
                                                                                                                        event_id=None,
                                                                                                                        condition_expr=BinaryOp(
                                                                                                                            expr1=Name(
                                                                                                                                name='a'),
                                                                                                                            op='==',
                                                                                                                            expr2=HexInt(
                                                                                                                                raw='0x2')),
                                                                                                                        post_operations=[]),
                                                                                                                    TransitionDefinition(
                                                                                                                        from_state=INIT_STATE,
                                                                                                                        to_state='LX212',
                                                                                                                        event_id=None,
                                                                                                                        condition_expr=BinaryOp(
                                                                                                                            expr1=Name(
                                                                                                                                name='a'),
                                                                                                                            op='==',
                                                                                                                            expr2=HexInt(
                                                                                                                                raw='0x3')),
                                                                                                                        post_operations=[]),
                                                                                                                    TransitionDefinition(
                                                                                                                        from_state='LX211',
                                                                                                                        to_state=EXIT_STATE,
                                                                                                                        event_id=ChainID(
                                                                                                                            path=[
                                                                                                                                'LX211',
                                                                                                                                'E1']),
                                                                                                                        condition_expr=None,
                                                                                                                        post_operations=[
                                                                                                                            OperationAssignment(
                                                                                                                                name='a',
                                                                                                                                expr=HexInt(
                                                                                                                                    raw='0x1'))]),
                                                                                                                    TransitionDefinition(
                                                                                                                        from_state='LX211',
                                                                                                                        to_state='LX212',
                                                                                                                        event_id=ChainID(
                                                                                                                            path=[
                                                                                                                                'LX211',
                                                                                                                                'E2']),
                                                                                                                        condition_expr=None,
                                                                                                                        post_operations=[]),
                                                                                                                    TransitionDefinition(
                                                                                                                        from_state='LX212',
                                                                                                                        to_state=EXIT_STATE,
                                                                                                                        event_id=ChainID(
                                                                                                                            path=[
                                                                                                                                'LX212',
                                                                                                                                'E1']),
                                                                                                                        condition_expr=None,
                                                                                                                        post_operations=[
                                                                                                                            OperationAssignment(
                                                                                                                                name='a',
                                                                                                                                expr=HexInt(
                                                                                                                                    raw='0x1'))]),
                                                                                                                    TransitionDefinition(
                                                                                                                        from_state='LX212',
                                                                                                                        to_state='LX211',
                                                                                                                        event_id=ChainID(
                                                                                                                            path=[
                                                                                                                                'E2']),
                                                                                                                        condition_expr=None,
                                                                                                                        post_operations=[])],
                                                                                                                enters=[],
                                                                                                                durings=[],
                                                                                                                exits=[])],
                                                                                                        transitions=[
                                                                                                            TransitionDefinition(
                                                                                                                from_state=INIT_STATE,
                                                                                                                to_state='LX21',
                                                                                                                event_id=None,
                                                                                                                condition_expr=None,
                                                                                                                post_operations=[]),
                                                                                                            TransitionDefinition(
                                                                                                                from_state='LX21',
                                                                                                                to_state=EXIT_STATE,
                                                                                                                event_id=None,
                                                                                                                condition_expr=BinaryOp(
                                                                                                                    expr1=Name(
                                                                                                                        name='a'),
                                                                                                                    op='==',
                                                                                                                    expr2=HexInt(
                                                                                                                        raw='0x1')),
                                                                                                                post_operations=[])],
                                                                                                        enters=[],
                                                                                                        durings=[],
                                                                                                        exits=[])],
                                                                  transitions=[
                                                                      TransitionDefinition(from_state=INIT_STATE,
                                                                                           to_state='LX1',
                                                                                           event_id=None,
                                                                                           condition_expr=None,
                                                                                           post_operations=[]),
                                                                      TransitionDefinition(from_state='LX1',
                                                                                           to_state='LX2',
                                                                                           event_id=None,
                                                                                           condition_expr=BinaryOp(
                                                                                               expr1=BinaryOp(
                                                                                                   expr1=Name(name='a'),
                                                                                                   op='==',
                                                                                                   expr2=HexInt(
                                                                                                       raw='0x2')),
                                                                                               op='||', expr2=BinaryOp(
                                                                                                   expr1=Name(name='a'),
                                                                                                   op='==',
                                                                                                   expr2=HexInt(
                                                                                                       raw='0x3'))),
                                                                                           post_operations=[]),
                                                                      TransitionDefinition(from_state='LX1',
                                                                                           to_state='LX1',
                                                                                           event_id=None,
                                                                                           condition_expr=BinaryOp(
                                                                                               expr1=Name(name='a'),
                                                                                               op='==',
                                                                                               expr2=HexInt(raw='0x1')),
                                                                                           post_operations=[]),
                                                                      TransitionDefinition(from_state='LX2',
                                                                                           to_state='LX1',
                                                                                           event_id=None,
                                                                                           condition_expr=BinaryOp(
                                                                                               expr1=Name(name='a'),
                                                                                               op='==',
                                                                                               expr2=HexInt(raw='0x1')),
                                                                                           post_operations=[])],
                                                                  enters=[EnterOperations(operations=[
                                                                      OperationAssignment(name='b',
                                                                                          expr=Integer(raw='0'))])],
                                                                  durings=[], exits=[ExitOperations(
                                               operations=[OperationAssignment(name='b', expr=Integer(raw='0'))])]))
        ),  # A full demo

        (
                """
                def int x = 0;
                state A {
                    enter abstract F;
                    enter abstract F /* this is F */
                    enter abstract /* this if another F */
                    enter {
                        x = 0;
                    }
        
                    during abstract F;
                    during abstract F /* this is F */
                    during abstract /* this if another F */
                    during {
                        x = 0;
                    }
        
                    during before abstract F;
                    during before abstract F /* this is F */
                    during before abstract /* this if another F */
                    during before {
                        x = 0;
                    }
        
                    during after abstract F;
                    during after abstract F /* this is F */
                    during after abstract /* this if another F */
                    during after {
                        x = 0;
                    }
        
                    exit abstract F;
                    exit abstract F /* this is F */
                    exit abstract /* this if another F */
                    exit {
                        x = 0;
                    }
                }
                """,
                StateMachineDSLProgram(definitions=[DefAssignment(name='x', type='int', expr=Integer(raw='0'))],
                                       root_state=StateDefinition(name='A', substates=[], transitions=[],
                                                                  enters=[EnterAbstractFunction(name='F', doc=None),
                                                                          EnterAbstractFunction(name='F',
                                                                                                doc='this is F'),
                                                                          EnterAbstractFunction(name=None,
                                                                                                doc='this if another F'),
                                                                          EnterOperations(operations=[
                                                                              OperationAssignment(name='x',
                                                                                                  expr=Integer(
                                                                                                      raw='0'))])],
                                                                  durings=[DuringAbstractFunction(name='F', aspect=None,
                                                                                                  doc=None),
                                                                           DuringAbstractFunction(name='F', aspect=None,
                                                                                                  doc='this is F'),
                                                                           DuringAbstractFunction(name=None,
                                                                                                  aspect=None,
                                                                                                  doc='this if another F'),
                                                                           DuringOperations(aspect=None, operations=[
                                                                               OperationAssignment(name='x',
                                                                                                   expr=Integer(
                                                                                                       raw='0'))]),
                                                                           DuringAbstractFunction(name='F',
                                                                                                  aspect='before',
                                                                                                  doc=None),
                                                                           DuringAbstractFunction(name='F',
                                                                                                  aspect='before',
                                                                                                  doc='this is F'),
                                                                           DuringAbstractFunction(name=None,
                                                                                                  aspect='before',
                                                                                                  doc='this if another F'),
                                                                           DuringOperations(aspect='before',
                                                                                            operations=[
                                                                                                OperationAssignment(
                                                                                                    name='x',
                                                                                                    expr=Integer(
                                                                                                        raw='0'))]),
                                                                           DuringAbstractFunction(name='F',
                                                                                                  aspect='after',
                                                                                                  doc=None),
                                                                           DuringAbstractFunction(name='F',
                                                                                                  aspect='after',
                                                                                                  doc='this is F'),
                                                                           DuringAbstractFunction(name=None,
                                                                                                  aspect='after',
                                                                                                  doc='this if another F'),
                                                                           DuringOperations(aspect='after', operations=[
                                                                               OperationAssignment(name='x',
                                                                                                   expr=Integer(
                                                                                                       raw='0'))])],
                                                                  exits=[ExitAbstractFunction(name='F', doc=None),
                                                                         ExitAbstractFunction(name='F',
                                                                                              doc='this is F'),
                                                                         ExitAbstractFunction(name=None,
                                                                                              doc='this if another F'),
                                                                         ExitOperations(operations=[
                                                                             OperationAssignment(name='x', expr=Integer(
                                                                                 raw='0'))])]))
        ),  # A full example of enter/during/exit

    ])
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name='state_machine_dsl') == expected

    @pytest.mark.parametrize(['input_text', 'expected_str'], [
        (
                """
                def int counter = 0;
                state Main;
                """,
                'def int counter = 0;\nstate Main;'
        ),  # Simple state machine with a single leaf state and an integer definition
        (
                """
                def float x = 3.14;
                def int count = 10;
                state Initial;
                """,
                'def float x = 3.14;\ndef int count = 10;\nstate Initial;'
        ),  # State machine with multiple variable definitions and a single leaf state
        (
                """
                state Main {
                    state SubState1;
                    state SubState2;
                }
                """,
                'state Main {\n    state SubState1;\n    state SubState2;\n}'
        ),  # Composite state containing two leaf states
        (
                """
                def int timer = 0;
                state Main {
                    [*] -> Ready;
                    Ready -> Processing: if [timer > 10];
                    Processing -> Done;
                    Done -> [*];
                }
                """,
                'def int timer = 0;\nstate Main {\n    [*] -> Ready;\n    Ready -> Processing : if [timer > 10];\n    Processing -> Done;\n    Done -> [*];\n}'
        ),  # Complete state machine with entry, normal, and exit transitions with a condition
        (
                """
                state Process {
                    [*] -> Idle;
                    Idle -> Active: if [true];
                    Active -> Complete;
                    Complete -> [*];
                }
                """,
                'state Process {\n    [*] -> Idle;\n    Idle -> Active : if [True];\n    Active -> Complete;\n    Complete -> [*];\n}'
        ),  # State machine with entry, normal transitions with boolean condition, and exit transition
        (
                """
                def int count = 0;
                state Counter {
                    [*] -> Counting effect {
                        count = count + 1;
                    }
                    Counting -> Done: if [count > 10];
                    Done -> [*];
                }
                """,
                'def int count = 0;\nstate Counter {\n    [*] -> Counting effect {\n        count = count + 1;\n    }\n    Counting -> Done : if [count > 10];\n    Done -> [*];\n}'
        ),  # State machine with effect operation in entry transition
        (
                """
                def float temperature = 25.0;
                state ThermostatControl {
                    state Heating;
                    state Cooling;
                    state Idle;
        
                    [*] -> Idle;
                    Idle -> Heating: if [temperature < 20.0];
                    Idle -> Cooling: if [temperature > 26.0];
                    Heating -> Idle: if [temperature >= 22.0];
                    Cooling -> Idle: if [temperature <= 24.0];
                }
                """,
                'def float temperature = 25.0;\nstate ThermostatControl {\n    state Heating;\n    state Cooling;\n    state Idle;\n    [*] -> Idle;\n    Idle -> Heating : if [temperature < 20.0];\n    Idle -> Cooling : if [temperature > 26.0];\n    Heating -> Idle : if [temperature >= 22.0];\n    Cooling -> Idle : if [temperature <= 24.0];\n}'
        ),  # Complex state machine with multiple states and conditional transitions
        (
                """
                def int x = 0;
                state Main {
                    state A {
                        state A1;
                        state A2;
                        A1 -> A2: if [x > 5];
                    }
                    state B;
                    A -> B: if [x > 10];
                }
                """,
                'def int x = 0;\nstate Main {\n    state A {\n        state A1;\n        state A2;\n        A1 -> A2 : if [x > 5];\n    }\n    state B;\n    A -> B : if [x > 10];\n}'
        ),  # Nested composite states with transitions at different levels
        (
                """
                def int counter = 0;
                state Process {
                    [*] -> Start effect {
                        counter = counter + 1;
                    }
                    Start -> Middle: chain_id;
                    Middle -> End: if [counter > 5] effect {
                        counter = counter * 2;
                    }
                    End -> [*];
                }
                """,
                'def int counter = 0;\nstate Process {\n    [*] -> Start effect {\n        counter = counter + 1;\n    }\n    Start -> Middle : chain_id;\n    Middle -> End : if [counter > 5] effect {\n        counter = counter * 2;\n    }\n    End -> [*];\n}'
        ),  # State machine with chain_id transition and effect operations
        (
                """
                def float x = 1.0;
                def float y = 2.0;
                state Calculator {
                    state Add {
                        [*] -> Computing;
                        Computing -> Done;
                        Done -> [*];
                    }
                    state Multiply {
                        [*] -> Computing;
                        Computing -> Done;
                        Done -> [*];
                    }
                    [*] -> Add: if [x < y];
                    [*] -> Multiply: if [x >= y];
                }
                """,
                'def float x = 1.0;\ndef float y = 2.0;\nstate Calculator {\n    state Add {\n        [*] -> Computing;\n        Computing -> Done;\n        Done -> [*];\n    }\n    state Multiply {\n        [*] -> Computing;\n        Computing -> Done;\n        Done -> [*];\n    }\n    [*] -> Add : if [x < y];\n    [*] -> Multiply : if [x >= y];\n}'
        ),  # State machine with multiple composite states and conditional entry transitions
        (
                """
                def int status = 0;
                state StatusHandler {
                    [*] -> Checking effect {
                        status = status + 1;
                    }
                    Checking -> Success: if [status > 0] effect {
                        status = 100;
                    }
                    Checking -> Failure: if [status <= 0] effect {
                        status = -1;
                    }
                    Success -> [*];
                    Failure -> [*];
                }
                """,
                'def int status = 0;\nstate StatusHandler {\n    [*] -> Checking effect {\n        status = status + 1;\n    }\n    Checking -> Success : if [status > 0] effect {\n        status = 100;\n    }\n    Checking -> Failure : if [status <= 0] effect {\n        status = -1;\n    }\n    Success -> [*];\n    Failure -> [*];\n}'
        ),  # State machine with multiple effect operations in different transitions
        (
                """
                def int value = 0x1A;
                state HexTest {
                    [*] -> Start;
                    Start -> End: if [value == 0x1A];
                    End -> [*];
                }
                """,
                'def int value = 0x1a;\nstate HexTest {\n    [*] -> Start;\n    Start -> End : if [value == 0x1a];\n    End -> [*];\n}'
        ),  # State machine using hexadecimal integer in definition and condition
        (
                """
                def float pi_val = pi;
                def float e_val = E;
                state MathConstants {
                    [*] -> Processing: if [pi_val > e_val];
                    Processing -> [*];
                }
                """,
                'def float pi_val = pi;\ndef float e_val = E;\nstate MathConstants {\n    [*] -> Processing : if [pi_val > e_val];\n    Processing -> [*];\n}'
        ),  # State machine using mathematical constants in definitions and conditions
        (
                """
                def int a = 5;
                def int b = 10;
                state ConditionalTest {
                    [*] -> Evaluate;
                    Evaluate -> TrueState: if [(a < b) ? true : false];
                    Evaluate -> FalseState: if [(a > b) ? true : false];
                    TrueState -> [*];
                    FalseState -> [*];
                }
                """,
                'def int a = 5;\ndef int b = 10;\nstate ConditionalTest {\n    [*] -> Evaluate;\n    Evaluate -> TrueState : if [(a < b) ? True : False];\n    Evaluate -> FalseState : if [(a > b) ? True : False];\n    TrueState -> [*];\n    FalseState -> [*];\n}'
        ),  # State machine using conditional C-style expressions in transition conditions
        (
                """
                def float angle = 0.0;
                state Trigonometry {
                    [*] -> Calculate;
                    Calculate -> Result: if [sin(angle) < 0.5];
                    Result -> [*];
                }
                """,
                'def float angle = 0.0;\nstate Trigonometry {\n    [*] -> Calculate;\n    Calculate -> Result : if [sin(angle) < 0.5];\n    Result -> [*];\n}'
        ),  # State machine using mathematical functions in transition conditions
        (
                """
                def int flag = 1;
                state BitOperations {
                    [*] -> Process;
                    Process -> Done: if [(flag & 1) == 1];
                    Done -> [*];
                }
                """,
                'def int flag = 1;\nstate BitOperations {\n    [*] -> Process;\n    Process -> Done : if [(flag & 1) == 1];\n    Done -> [*];\n}'
        ),  # State machine using bitwise operations in transition conditions
        (
                """
                def int x = 10;
                def int y = 20;
                state LogicalTest {
                    [*] -> Check;
                    Check -> Success: if [x < y && x > 0];
                    Check -> Failure: if [x >= y || x <= 0];
                    Success -> [*];
                    Failure -> [*];
                }
                """,
                'def int x = 10;\ndef int y = 20;\nstate LogicalTest {\n    [*] -> Check;\n    Check -> Success : if [x < y && x > 0];\n    Check -> Failure : if [x >= y || x <= 0];\n    Success -> [*];\n    Failure -> [*];\n}'
        ),  # State machine using logical AND/OR operations in transition conditions
        (
                """
                def int counter = 0;
                state EmptyTransition {
                    [*] -> Start;
                    Start -> Middle;
                    Middle -> End;
                    End -> [*];
                }
                """,
                'def int counter = 0;\nstate EmptyTransition {\n    [*] -> Start;\n    Start -> Middle;\n    Middle -> End;\n    End -> [*];\n}'
        ),  # State machine with transitions without conditions or effect operations
        (
                """
                def int x = 5;
                state SemicolonTest {
                    ;
                    state Inner;
                    ;
                    Inner -> [*];
                    ;
                }
                """,
                'def int x = 5;\nstate SemicolonTest {\n    state Inner;\n    Inner -> [*];\n}'
        ),  # State machine with empty statements (lone semicolons)
        (
                """
                def float temp = 22.5;
                state NestedConditions {
                    [*] -> Check;
                    Check -> Hot: if [temp > 25.0 && (temp < 30.0 || temp == 35.0)];
                    Check -> Cold: if [temp < 20.0 && (temp > 15.0 || temp == 10.0)];
                    Hot -> [*];
                    Cold -> [*];
                }
                """,
                'def float temp = 22.5;\nstate NestedConditions {\n    [*] -> Check;\n    Check -> Hot : if [temp > 25.0 && (temp < 30.0 || temp == 35.0)];\n    Check -> Cold : if [temp < 20.0 && (temp > 15.0 || temp == 10.0)];\n    Hot -> [*];\n    Cold -> [*];\n}'
        ),  # State machine with complex nested conditional expressions
        (
                """
                def int a = 1 + 2 * 3;
                def float b = 2.5 ** 2;
                state ExpressionTest {
                    [*] -> Calculate;
                    Calculate -> Result: if [a * b > 20.0];
                    Result -> [*];
                }
                """,
                'def int a = 1 + 2 * 3;\ndef float b = 2.5 ** 2;\nstate ExpressionTest {\n    [*] -> Calculate;\n    Calculate -> Result : if [a * b > 20.0];\n    Result -> [*];\n}'
        ),  # State machine with complex arithmetic expressions in definitions and conditions

        (
                """
                def int x = 0;
                state A {
        
                    enter {
                        x = 1;
                    }
        
                    B -> C :: E1;
                    C -> C : if [x == 1] effect {
                        x = 0;
                    }
        
                    state B;
                    state C {
                        enter abstract F1;
                        enter abstract F2 /*
                            this is the comment of F2
                        */
        
                        during before abstract /*
                            this is another during
                        */
        
                        state D {
                            during {
                                x = x + 1;
                            }
                            state EX;
                            [*] -> EX : E1;
                        }
                        [*] -> D :: E2;
                        D -> [*] : if [x > 0] effect {
                            x = ((x + ((-1))));
                            x = x / 2;
                        }
        
                        exit {
                            x = 21;
                        }
                    }
        
                    [*] -> B;
                    C -> [*] effect {};
        
                    C -> B :: E2;
                    C -> B : C.D.E1;
        
                    during after abstract Af;
        
                    ;;;
                }
                """,
                'def int x = 0;\nstate A {\n    enter {\n        x = 1;\n    }\n    during after abstract Af;\n    state B;\n    state C {\n        enter abstract F1;\n        enter abstract F2 /*\n            this is the comment of F2\n        */\n        during before abstract /*\n            this is another during\n        */\n        exit {\n            x = 21;\n        }\n        state D {\n            during {\n                x = x + 1;\n            }\n            state EX;\n            [*] -> EX :: E1;\n        }\n        [*] -> D :: E2;\n        D -> [*] : if [x > 0] effect {\n            x = ((x + ((-1))));\n            x = x / 2;\n        }\n    }\n    B -> C :: E1;\n    C -> C : if [x == 1] effect {\n        x = 0;\n    }\n    [*] -> B;\n    C -> [*];\n    C -> B :: E2;\n    C -> B : C.D.E1;\n}'
        ),  # A simpler full demo
        (
                """
                def int a = 0;
                def int b = 0x0;
        
                state LX {
                    [*] -> LX1;
        
                    enter {
                        b = 0;
                    }
        
                    exit {
                        b = 0;
                    }
        
                    state LX1 {
                        during before abstract BeforeLX1Enter;
                        during after abstract AfterLX1Enter /*
                            this is the comment line
                        */
        
                        state LX11 {
                            enter abstract LX11Enter;
                            exit abstract LX11Exit;
                            during abstract LX11During; 
                        }
                        state LX12;
                        state LX13;
                        state LX14 {
                            during {
                                b = 0x10;
                            }
                        }
        
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
                """,
                'def int a = 0;\ndef int b = 0x0;\nstate LX {\n    enter {\n        b = 0;\n    }\n    exit {\n        b = 0;\n    }\n    state LX1 {\n        during before abstract BeforeLX1Enter;\n        during after abstract AfterLX1Enter /*\n            this is the comment line\n        */\n        state LX11 {\n            enter abstract LX11Enter;\n            during abstract LX11During;\n            exit abstract LX11Exit;\n        }\n        state LX12;\n        state LX13;\n        state LX14 {\n            during {\n                b = 0x10;\n            }\n        }\n        [*] -> LX11;\n        LX11 -> LX12 :: E1;\n        LX12 -> LX13 :: E1;\n        LX12 -> LX14 :: E2;\n        LX13 -> [*] :: E1 effect {\n            a = 0x2;\n        }\n        LX13 -> [*] :: E2 effect {\n            a = 0x3;\n        }\n        LX13 -> LX14 :: E3;\n        LX13 -> LX14 :: E4;\n        LX14 -> LX12 :: E1;\n        LX14 -> [*] :: E2 effect {\n            a = 0x1;\n        }\n    }\n    state LX2 {\n        state LX21 {\n            state LX211;\n            state LX212;\n            [*] -> LX211 : if [a == 0x2];\n            [*] -> LX212 : if [a == 0x3];\n            LX211 -> [*] :: E1 effect {\n                a = 0x1;\n            }\n            LX211 -> LX212 :: E2;\n            LX212 -> [*] :: E1 effect {\n                a = 0x1;\n            }\n            LX212 -> LX211 : E2;\n        }\n        [*] -> LX21;\n        LX21 -> [*] : if [a == 0x1];\n    }\n    [*] -> LX1;\n    LX1 -> LX2 : if [a == 0x2 || a == 0x3];\n    LX1 -> LX1 : if [a == 0x1];\n    LX2 -> LX1 : if [a == 0x1];\n}'
        ),  # A full demo

        (
                """
                def int x = 0;
                state A {
                    enter abstract F;
                    enter abstract F /* this is F */
                    enter abstract /* this if another F */
                    enter {
                        x = 0;
                    }
        
                    during abstract F;
                    during abstract F /* this is F */
                    during abstract /* this if another F */
                    during {
                        x = 0;
                    }
        
                    during before abstract F;
                    during before abstract F /* this is F */
                    during before abstract /* this if another F */
                    during before {
                        x = 0;
                    }
        
                    during after abstract F;
                    during after abstract F /* this is F */
                    during after abstract /* this if another F */
                    during after {
                        x = 0;
                    }
        
                    exit abstract F;
                    exit abstract F /* this is F */
                    exit abstract /* this if another F */
                    exit {
                        x = 0;
                    }
                }
                """,
                'def int x = 0;\nstate A {\n    enter abstract F;\n    enter abstract F /*\n        this is F\n    */\n    enter abstract /*\n        this if another F\n    */\n    enter {\n        x = 0;\n    }\n    during abstract F;\n    during abstract F /*\n        this is F\n    */\n    during abstract /*\n        this if another F\n    */\n    during {\n        x = 0;\n    }\n    during before abstract F;\n    during before abstract F /*\n        this is F\n    */\n    during before abstract /*\n        this if another F\n    */\n    during before {\n        x = 0;\n    }\n    during after abstract F;\n    during after abstract F /*\n        this is F\n    */\n    during after abstract /*\n        this if another F\n    */\n    during after {\n        x = 0;\n    }\n    exit abstract F;\n    exit abstract F /*\n        this is F\n    */\n    exit abstract /*\n        this if another F\n    */\n    exit {\n        x = 0;\n    }\n}'
        ),  # A full example of enter/during/exit

    ])
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(parse_with_grammar_entry(input_text, entry_name='state_machine_dsl')),
        )

    @pytest.mark.parametrize(['input_text'], [
        (
                """
                def string name = "Test";
                state Main;
                """,
        ),  # Invalid type in def assignment - 'string' is not a supported type (only int/float allowed)
        (
                """
                def int x = 5
                state Main;
                """,
        ),  # Missing semicolon after def assignment
        (
                """
                def int x = ;
                state Main;
                """,
        ),  # Missing initialization expression in def assignment
        (
                """
                def int 5x = 10;
                state Main;
                """,
        ),  # Invalid identifier name in def assignment (starts with a number)
        (
                """
                def int x = 5.5.5;
                state Main;
                """,
        ),  # Invalid float literal in initialization expression
        (
                """
                state;
                """,
        ),  # Missing state identifier in state definition
        (
                """
                state Main {
                    -> SubState;
                }
                """,
        ),  # Missing source state in transition definition
        (
                """
                state Main {
                    SubState ->;
                }
                """,
        ),  # Missing target state in transition definition
        (
                """
                state Main {
                    [*] -> SubState: if [];
                }
                """,
        ),  # Empty condition expression in transition
        (
                """
                state Main {
                    [*] -> SubState effect {
                        x = 5
                    }
                }
                """,
        ),  # Missing semicolon in effect operation assignment
        (
                """
                state Main {
                    [*] -> SubState: if [x > 5] effect
                }
                """,
        ),  # Incomplete effect block in transition definition
        (
                """
                state Main {
                    state SubState {
                        [*] -> NextState;
                    }
                    SubState -> [*] effect {
                        := 5;
                    }
                }
                """,
        ),  # Missing identifier in effect operation assignment
        (
                """
                def int x = "string";
                state Main;
                """,
        ),  # Type mismatch in def assignment - string literal assigned to int
        (
                """
                state Main {
                    [*] -> if [x > 5];
                }
                """,
        ),  # Missing target state in entry transition
        (
                """
                state Main {
                    state {
                        [*] -> Inner;
                    }
                }
                """,
        ),  # Missing state identifier in nested state definition
        (
                """
                state Main {
                    [*] -> SubState: if [x > y] effect {
                        x := ;
                    }
                }
                """,
        ),  # Missing expression in effect operation assignment
        (
                """
                def int x = 5;
                state Main {
                    [*] -> SubState: if (x > 5);
                }
                """,
        ),  # Missing square brackets around condition expression
        (
                """
                def int x = 5;
                state Main {
                    [*] -> SubState: if [x > 5] {
                        x := 10;
                    }
                }
                """,
        ),  # Missing 'effect' keyword before effect operation block
        (
                """
                state Main {
                    [*] -> SubState: chain.with.invalid..dots;
                }
                """,
        ),  # Invalid chain_id with consecutive dots
        (
                """
                def int x = 0xZZ;
                state Main;
                """,
        ),  # Invalid hexadecimal literal in def assignment
        (
                """
                def int x = 5;
                state Main {
                    [*] -> SubState: if [x == "string"];
                }
                """,
        ),  # Type mismatch in condition - comparing int with string
        (
                """
                def int x = 5;
                state Main {
                    [*] -> SubState: if [x > 5] effect {
                        x := y + 1;
                    }
                }
                """,
        ),  # Using assignment operator ':=' instead of '=' in effect operation
        # (
        #         """
        #         state Main {
        #             [*] -> SubState: if [undefined_var > 5];
        #         }
        #         """,
        # ),  # Reference to undefined variable in condition
        (
                """
                def int x = 5;
                state Main {
                    [*] -> SubState effect {
                        x := unknown_function(x);
                    }
                }
                """,
        ),  # Using undefined function in effect operation
    ])
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name='state_machine_dsl')

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f'Found {len(err.errors)} errors during parsing:' in err.args[0]
