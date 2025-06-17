import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLTransition:
    @pytest.mark.parametrize(['input_text', 'expected'], [
        ('state S1;', StateDefinition(name='S1', substates=[], transitions=[])),  # Simple leaf state definition
        ('state Running;', StateDefinition(name='Running', substates=[], transitions=[])),
        # Leaf state with descriptive name
        ('state IDLE;', StateDefinition(name='IDLE', substates=[], transitions=[])),  # Leaf state with uppercase name
        ('state s_2;', StateDefinition(name='s_2', substates=[], transitions=[])),  # Leaf state with underscore in name
        ('state waiting_for_input;', StateDefinition(name='waiting_for_input', substates=[], transitions=[])),
        # Leaf state with multiple underscores
        ('state Complex { }', StateDefinition(name='Complex', substates=[], transitions=[])),
        # Composite state with empty body
        ('state Parent { }', StateDefinition(name='Parent', substates=[], transitions=[])),
        # Composite state named Parent with empty body
        ('state S1 { state S2; }',
         StateDefinition(name='S1', substates=[StateDefinition(name='S2', substates=[], transitions=[])],
                         transitions=[])),  # Composite state containing a leaf state
        ('state Parent { state Child1; state Child2; }', StateDefinition(name='Parent', substates=[
            StateDefinition(name='Child1', substates=[], transitions=[]),
            StateDefinition(name='Child2', substates=[], transitions=[])], transitions=[])),
        # Composite state with multiple leaf states
        ('state S1 { state S2 { state S3; } }', StateDefinition(name='S1', substates=[
            StateDefinition(name='S2', substates=[StateDefinition(name='S3', substates=[], transitions=[])],
                            transitions=[])], transitions=[])),  # Composite state with nested composite state
        ('state Machine { state Running { state Fast; state Slow; } }', StateDefinition(name='Machine', substates=[
            StateDefinition(name='Running', substates=[StateDefinition(name='Fast', substates=[], transitions=[]),
                                                       StateDefinition(name='Slow', substates=[], transitions=[])],
                            transitions=[])], transitions=[])),
        # Composite state with nested composite state containing multiple leaf states
        ('state S1 { [*] -> S2; }', StateDefinition(name='S1', substates=[], transitions=[
            TransitionDefinition(from_state=INIT_STATE, to_state='S2', event_id=None, condition_expr=None,
                                 post_operations=[])])),  # Composite state with entry transition
        ('state S1 { S2 -> S3; }', StateDefinition(name='S1', substates=[], transitions=[
            TransitionDefinition(from_state='S2', to_state='S3', event_id=None, condition_expr=None,
                                 post_operations=[])])),  # Composite state with normal transition
        ('state S1 { S2 -> [*]; }', StateDefinition(name='S1', substates=[], transitions=[
            TransitionDefinition(from_state='S2', to_state=EXIT_STATE, event_id=None, condition_expr=None,
                                 post_operations=[])])),  # Composite state with exit transition
        ('state S1 { S2 -> S3: chain.id; }', StateDefinition(name='S1', substates=[], transitions=[
            TransitionDefinition(from_state='S2', to_state='S3', event_id=ChainID(path=['chain', 'id']),
                                 condition_expr=None, post_operations=[])])),
        # Composite state with transition having chain ID
        ('state S1 { [*] -> S2: entry.chain; }', StateDefinition(name='S1', substates=[], transitions=[
            TransitionDefinition(from_state=INIT_STATE, to_state='S2', event_id=ChainID(path=['entry', 'chain']),
                                 condition_expr=None, post_operations=[])])),
        # Composite state with entry transition having chain ID
        ('state S1 { S2 -> S3: if [x > 5]; }', StateDefinition(name='S1', substates=[], transitions=[
            TransitionDefinition(from_state='S2', to_state='S3', event_id=None,
                                 condition_expr=BinaryOp(expr1=Name(name='x'), op='>', expr2=Integer(raw='5')),
                                 post_operations=[])])),  # Composite state with conditional transition
        ('state S1 { S2 -> S3: if [x == 10 && y < 20]; }', StateDefinition(name='S1', substates=[], transitions=[
            TransitionDefinition(from_state='S2', to_state='S3', event_id=None, condition_expr=BinaryOp(
                expr1=BinaryOp(expr1=Name(name='x'), op='==', expr2=Integer(raw='10')), op='&&',
                expr2=BinaryOp(expr1=Name(name='y'), op='<', expr2=Integer(raw='20'))), post_operations=[])])),
        # Composite state with complex conditional transition
        ('state S1 { S2 -> S3 effect { x = 10; } }', StateDefinition(name='S1', substates=[], transitions=[
            TransitionDefinition(from_state='S2', to_state='S3', event_id=None, condition_expr=None,
                                 post_operations=[OperationAssignment(name='x', expr=Integer(raw='10'))])])),
        # Composite state with effect-transition operation
        ('state S1 { S2 -> S3 effect { x = 10; y = 20; } }', StateDefinition(name='S1', substates=[], transitions=[
            TransitionDefinition(from_state='S2', to_state='S3', event_id=None, condition_expr=None,
                                 post_operations=[OperationAssignment(name='x', expr=Integer(raw='10')),
                                                  OperationAssignment(name='y', expr=Integer(raw='20'))])])),
        # Composite state with multiple effect-transition operations
        ('state S1 { state S2; S2 -> S3: if [x > 5]; S3 -> [*]; }',
         StateDefinition(name='S1', substates=[StateDefinition(name='S2', substates=[], transitions=[])], transitions=[
             TransitionDefinition(from_state='S2', to_state='S3', event_id=None,
                                  condition_expr=BinaryOp(expr1=Name(name='x'), op='>', expr2=Integer(raw='5')),
                                  post_operations=[]),
             TransitionDefinition(from_state='S3', to_state=EXIT_STATE, event_id=None, condition_expr=None,
                                  post_operations=[])])),  # Composite state with leaf state and transitions
        (
                'state Machine { state Off; state On { state Idle; state Running; } Off -> On: if [power == 1]; On -> Off: if [power == 0]; }',
                StateDefinition(name='Machine', substates=[StateDefinition(name='Off', substates=[], transitions=[]),
                                                           StateDefinition(name='On', substates=[
                                                               StateDefinition(name='Idle', substates=[],
                                                                               transitions=[]),
                                                               StateDefinition(name='Running', substates=[],
                                                                               transitions=[])],
                                                                           transitions=[])], transitions=[
                    TransitionDefinition(from_state='Off', to_state='On', event_id=None,
                                         condition_expr=BinaryOp(expr1=Name(name='power'), op='==',
                                                                 expr2=Integer(raw='1')),
                                         post_operations=[]),
                    TransitionDefinition(from_state='On', to_state='Off', event_id=None,
                                         condition_expr=BinaryOp(expr1=Name(name='power'), op='==',
                                                                 expr2=Integer(raw='0')),
                                         post_operations=[])])),
        # Complex state machine with nested states and transitions
        ('state S1 { state S2; state S3; S2 -> S3: if [x > 5] effect { x = 10; }; S3 -> [*]; }',
         StateDefinition(name='S1', substates=[StateDefinition(name='S2', substates=[], transitions=[]),
                                               StateDefinition(name='S3', substates=[], transitions=[])], transitions=[
             TransitionDefinition(from_state='S2', to_state='S3', event_id=None,
                                  condition_expr=BinaryOp(expr1=Name(name='x'), op='>', expr2=Integer(raw='5')),
                                  post_operations=[OperationAssignment(name='x', expr=Integer(raw='10'))]),
             TransitionDefinition(from_state='S3', to_state=EXIT_STATE, event_id=None, condition_expr=None,
                                  post_operations=[])])),
        # Composite state with states, conditional transition with effect operations
        ('state S1 { ; state S2; ; S2 -> S3; ; }',
         StateDefinition(name='S1', substates=[StateDefinition(name='S2', substates=[], transitions=[])], transitions=[
             TransitionDefinition(from_state='S2', to_state='S3', event_id=None, condition_expr=None,
                                  post_operations=[])])),
        # Composite state with empty statements between valid statements
    ])
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name='state_definition') == expected

    @pytest.mark.parametrize(['input_text', 'expected_str'], [
        ('state S1;', 'state S1;'),  # Simple leaf state definition
        ('state Running;', 'state Running;'),  # Leaf state with descriptive name
        ('state IDLE;', 'state IDLE;'),  # Leaf state with uppercase name
        ('state s_2;', 'state s_2;'),  # Leaf state with underscore in name
        ('state waiting_for_input;', 'state waiting_for_input;'),  # Leaf state with multiple underscores
        ('state Complex { }', 'state Complex;'),  # Composite state with empty body
        ('state Parent { }', 'state Parent;'),  # Composite state named Parent with empty body
        ('state S1 { state S2; }', 'state S1 {\n    state S2;\n}'),  # Composite state containing a leaf state
        ('state Parent { state Child1; state Child2; }', 'state Parent {\n    state Child1;\n    state Child2;\n}'),
        # Composite state with multiple leaf states
        ('state S1 { state S2 { state S3; } }', 'state S1 {\n    state S2 {\n        state S3;\n    }\n}'),
        # Composite state with nested composite state
        ('state Machine { state Running { state Fast; state Slow; } }',
         'state Machine {\n    state Running {\n        state Fast;\n        state Slow;\n    }\n}'),
        # Composite state with nested composite state containing multiple leaf states
        ('state S1 { [*] -> S2; }', 'state S1 {\n    [*] -> S2;\n}'),  # Composite state with entry transition
        ('state S1 { S2 -> S3; }', 'state S1 {\n    S2 -> S3;\n}'),  # Composite state with normal transition
        ('state S1 { S2 -> [*]; }', 'state S1 {\n    S2 -> [*];\n}'),  # Composite state with exit transition
        ('state S1 { S2 -> S3: chain.id; }', 'state S1 {\n    S2 -> S3 : chain.id;\n}'),
        # Composite state with transition having chain ID
        ('state S1 { [*] -> S2: entry.chain; }', 'state S1 {\n    [*] -> S2 : entry.chain;\n}'),
        # Composite state with entry transition having chain ID
        ('state S1 { S2 -> S3: if [x > 5]; }', 'state S1 {\n    S2 -> S3 : if [x > 5];\n}'),
        # Composite state with conditional transition
        ('state S1 { S2 -> S3: if [x == 10 && y < 20]; }', 'state S1 {\n    S2 -> S3 : if [x == 10 && y < 20];\n}'),
        # Composite state with complex conditional transition
        ('state S1 { S2 -> S3 effect { x = 10; } }', 'state S1 {\n    S2 -> S3 effect {\n        x = 10;\n    }\n}'),
        # Composite state with effect-transition operation
        ('state S1 { S2 -> S3 effect { x = 10; y = 20; } }',
         'state S1 {\n    S2 -> S3 effect {\n        x = 10;\n        y = 20;\n    }\n}'),
        # Composite state with multiple effect-transition operations
        ('state S1 { state S2; S2 -> S3: if [x > 5]; S3 -> [*]; }',
         'state S1 {\n    state S2;\n    S2 -> S3 : if [x > 5];\n    S3 -> [*];\n}'),
        # Composite state with leaf state and transitions
        (
                'state Machine { state Off; state On { state Idle; state Running; } Off -> On: if [power == 1]; On -> Off: if [power == 0]; }',
                'state Machine {\n    state Off;\n    state On {\n        state Idle;\n        state Running;\n    }\n    Off -> On : if [power == 1];\n    On -> Off : if [power == 0];\n}'),
        # Complex state machine with nested states and transitions
        ('state S1 { state S2; state S3; S2 -> S3: if [x > 5] effect { x = 10; }; S3 -> [*]; }',
         'state S1 {\n    state S2;\n    state S3;\n    S2 -> S3 : if [x > 5] effect {\n        x = 10;\n    }\n    S3 -> [*];\n}'),
        # Composite state with states, conditional transition with effect operations
        ('state S1 { ; state S2; ; S2 -> S3; ; }',
         'state S1 {\n    state S2;\n    S2 -> S3;\n}'),
        # Composite state with empty statements between valid statements
    ])
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(parse_with_grammar_entry(input_text, entry_name='state_definition')),
        )

    @pytest.mark.parametrize(['input_text'], [
        ('state;',),  # Missing state identifier
        ('state 123;',),  # Invalid state name starting with number
        ('state S1',),  # Missing semicolon after leaf state
        ('state S1 {',),  # Unclosed composite state definition
        ('state S1 }',),  # Missing opening brace for composite state
        ('State S1;',),  # Incorrect capitalization of 'state' keyword
        ('state S1 { state }',),  # Missing state identifier in inner state
        ('state S1 { S2 -> }',),  # Incomplete transition definition
        ('state S1 { -> S2; }',),  # Missing source state in transition
        ('state S1 { S2 ->; }',),  # Missing target state in transition
        ('state S1 { S2 -> S3: }',),  # Incomplete chain ID specification
        ('state S1 { S2 -> S3: if; }',),  # Missing condition expression after 'if'
        ('state S1 { S2 -> S3: if []; }',),  # Empty condition expression
        ('state S1 { S2 -> S3: if x > 5; }',),  # Missing brackets around condition
        ('state S1 { S2 -> S3 effect }',),  # Missing braces after 'effect' keyword
        ('state S1 { S2 -> S3 effect { x := 10; } }',),
        # Incorrect assignment operator in effect operation (using := instead of =)
        ('state S1 { S2 -> S3 effect { x = 10 } }',),  # Missing semicolon after assignment in effect operation
        ('state { state S2; }',),  # Missing state identifier for outer state
        ('state S1 { state S2 state S3; }',),  # Missing semicolon between inner states
        ('state S1 { [*] -> [*]; }',),  # Invalid transition from entry to exit
        ('state S1 { S2 -> S3: if [x > 5] effect x = 10; }',),  # Missing braces around effect operations
        ('state S1 { S2 -> S3: chain..id; }',),  # Invalid chain ID with consecutive dots
        ('state S1 { S2 -> S3: if [x > 5] else [y < 10]; }',),  # Unsupported 'else' clause in condition
        ('state S1 { S2 -> S3: when [x > 5]; }',),  # Using 'when' instead of 'if' for condition
    ])
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name='state_definition')

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f'Found {len(err.errors)} errors during parsing:' in err.args[0]
