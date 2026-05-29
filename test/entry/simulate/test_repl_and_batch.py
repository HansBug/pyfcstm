"""
Coverage for ``pyfcstm.entry.simulate.repl.SimulationREPL.run`` and
``pyfcstm.entry.simulate.batch.create_cross_platform_output_func``.

The REPL is normally interactive; we drive it by replacing ``session.prompt``
with a queue-based stub, which is the minimum monkey-patching required to
exercise the real ``run()`` loop (commands, EOFError exit, KeyboardInterrupt
continue) through the public class API.
"""
import textwrap

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.entry.simulate.batch import create_cross_platform_output_func
from pyfcstm.entry.simulate.repl import SimulationREPL
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


_TINY_DSL = textwrap.dedent("""
    def int counter = 0;

    state System {
        [*] -> Idle;
        state Idle;
    }
""").strip()


def _make_runtime():
    ast_node = parse_with_grammar_entry(_TINY_DSL, entry_name='state_machine_dsl')
    model = parse_dsl_node_to_state_machine(ast_node)
    return SimulationRuntime(model), model


class _ScriptedPrompt:
    """Queue-driven stand-in for ``prompt_toolkit.PromptSession.prompt``."""

    def __init__(self, inputs):
        # ``inputs`` is a list of strings; an ``EOFError`` instance also
        # acceptable to simulate Ctrl-D, and ``KeyboardInterrupt`` instance
        # for Ctrl-C.
        self._inputs = list(inputs)
        self.calls = 0

    def __call__(self, *args, **kwargs):
        if not self._inputs:
            raise EOFError
        self.calls += 1
        item = self._inputs.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.mark.unittest
class TestSimulationREPLRun:
    def test_run_processes_commands_then_exits_on_quit(self, capsys):
        runtime, model = _make_runtime()
        repl = SimulationREPL(runtime, state_machine=model, use_color=False)

        scripted = _ScriptedPrompt([
            '',          # empty input -> ``continue``
            '   ',       # whitespace-only -> ``continue``
            'current',   # produces output
            'quit',      # should_exit=True
        ])
        repl.session.prompt = scripted

        repl.run()

        captured = capsys.readouterr()
        # ``current`` prints the runtime state header; before cycling the
        # active state is still the composite root ``System``.
        assert 'Current State' in captured.out
        assert 'Goodbye' in captured.out  # quit produces goodbye message
        assert scripted.calls >= 3

    def test_run_eof_exits_gracefully(self, capsys):
        runtime, model = _make_runtime()
        repl = SimulationREPL(runtime, state_machine=model, use_color=False)

        scripted = _ScriptedPrompt([EOFError()])
        repl.session.prompt = scripted

        repl.run()

        captured = capsys.readouterr()
        assert 'Goodbye' in captured.out

    def test_run_keyboard_interrupt_continues(self, capsys):
        runtime, model = _make_runtime()
        repl = SimulationREPL(runtime, state_machine=model, use_color=False)

        # First call raises KeyboardInterrupt -> should print blank line +
        # continue. Next call returns 'quit' to exit cleanly.
        scripted = _ScriptedPrompt([KeyboardInterrupt(), 'quit'])
        repl.session.prompt = scripted

        repl.run()

        captured = capsys.readouterr()
        # The function calls print() with no args after Ctrl-C; combined
        # with the goodbye on quit, we should see both lines.
        assert 'Goodbye' in captured.out


@pytest.mark.unittest
class TestCrossPlatformOutput:
    def test_create_cross_platform_output_func_non_windows(self, capsys):
        # On any non-Windows platform the helper returns ``standard_output``
        # which is a thin wrapper around ``print``.
        out_func = create_cross_platform_output_func()
        out_func('hello world')
        captured = capsys.readouterr()
        assert 'hello world' in captured.out
