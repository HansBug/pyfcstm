"""
Unit tests for init command auto-completion functionality.

This module tests the enhanced auto-completion for the init command,
including state path completion and variable name/value completion.
"""

import pytest
from prompt_toolkit.document import Document

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.entry.simulate.completer import SimulationCompleter


def build_state_machine(dsl_code: str):
    """Helper to build state machine from DSL code."""
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


@pytest.mark.unittest
class TestInitCommandCompletion:
    """Test auto-completion for init command."""

    def test_state_path_completion(self):
        """Test state path completion for init command."""
        dsl_code = '''
def int counter = 0;
def int flag = 0;
state System {
    state Idle {
        during { counter = counter + 1; }
    }
    state Active {
        state Running;
        state Paused;
        [*] -> Running;
    }
    [*] -> Idle;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        completer = SimulationCompleter(runtime)

        # Test completing "init Sys"
        doc = Document('init Sys', len('init Sys'))
        completions = list(completer.get_completions(doc, None))

        # Should suggest System states
        completion_texts = [c.text for c in completions]
        assert 'System.Idle' in completion_texts
        assert 'System.Active' in completion_texts
        assert 'System.Active.Running' in completion_texts
        assert 'System.Active.Paused' in completion_texts

        # Check metadata
        for c in completions:
            meta_str = str(c.display_meta).lower()
            if c.text == 'System.Idle':
                assert 'leaf state' in meta_str
            elif c.text == 'System.Active':
                assert 'composite state' in meta_str

    def test_variable_name_completion(self):
        """Test variable name completion for init command."""
        dsl_code = '''
def int counter = 0;
def int flag = 0;
def float temperature = 25.0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        completer = SimulationCompleter(runtime)

        # Test completing "init Root.A cou"
        doc = Document('init Root.A cou', len('init Root.A cou'))
        completions = list(completer.get_completions(doc, None))

        # Should suggest counter=
        completion_texts = [c.text for c in completions]
        assert 'counter=' in completion_texts

        # Check metadata shows type
        for c in completions:
            if c.text == 'counter=':
                assert 'int' in str(c.display_meta).lower()

    def test_variable_value_completion(self):
        """Test variable value completion for init command."""
        dsl_code = '''
def int counter = 0;
def float temperature = 25.0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        completer = SimulationCompleter(runtime)

        # Test completing "init Root.A counter="
        doc = Document('init Root.A counter=', len('init Root.A counter='))
        completions = list(completer.get_completions(doc, None))

        # Should suggest int values (with var= prefix)
        completion_texts = [c.text for c in completions]
        assert 'counter=0' in completion_texts
        assert 'counter=1' in completion_texts
        assert 'counter=10' in completion_texts
        assert 'counter=0xFF' in completion_texts
        assert 'counter=0b1010' in completion_texts

        # Test completing "init Root.A temperature="
        doc = Document('init Root.A temperature=', len('init Root.A temperature='))
        completions = list(completer.get_completions(doc, None))

        # Should suggest float values (with var= prefix)
        completion_texts = [c.text for c in completions]
        assert 'temperature=0.0' in completion_texts
        assert 'temperature=1.0' in completion_texts
        assert 'temperature=10.5' in completion_texts
        assert 'temperature=1e-3' in completion_texts

    def test_variable_filtering_already_assigned(self):
        """Test that already assigned variables are filtered out."""
        dsl_code = '''
def int x = 0;
def int y = 0;
def int z = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        completer = SimulationCompleter(runtime)

        # Test completing "init Root.A x=10 y=20 "
        doc = Document('init Root.A x=10 y=20 ', len('init Root.A x=10 y=20 '))
        completions = list(completer.get_completions(doc, None))

        # Should only suggest z= (x and y already assigned)
        completion_texts = [c.text for c in completions]
        assert 'z=' in completion_texts
        assert 'x=' not in completion_texts
        assert 'y=' not in completion_texts

    def test_state_path_partial_match(self):
        """Test state path completion with partial matches."""
        dsl_code = '''
def int counter = 0;
state System {
    state Active;
    state Standby;
    state Shutdown;
    [*] -> Active;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        completer = SimulationCompleter(runtime)

        # Test completing "init System.S"
        doc = Document('init System.S', len('init System.S'))
        completions = list(completer.get_completions(doc, None))

        # Should suggest Standby and Shutdown, not Active
        completion_texts = [c.text for c in completions]
        assert 'System.Standby' in completion_texts
        assert 'System.Shutdown' in completion_texts
        assert 'System.Active' not in completion_texts

    def test_nested_state_completion(self):
        """Test completion for deeply nested states."""
        dsl_code = '''
def int counter = 0;
state Root {
    state Level1 {
        state Level2 {
            state Level3 {
                state Leaf;
                [*] -> Leaf;
            }
            [*] -> Level3;
        }
        [*] -> Level2;
    }
    [*] -> Level1;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        completer = SimulationCompleter(runtime)

        # Test completing "init Root.Level1.Level2."
        doc = Document('init Root.Level1.Level2.', len('init Root.Level1.Level2.'))
        completions = list(completer.get_completions(doc, None))

        # Should suggest Level3 and Level3.Leaf
        completion_texts = [c.text for c in completions]
        assert 'Root.Level1.Level2.Level3' in completion_texts
        assert 'Root.Level1.Level2.Level3.Leaf' in completion_texts
