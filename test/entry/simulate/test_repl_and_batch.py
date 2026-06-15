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
from prompt_toolkit.document import Document

from pyfcstm.dsl import EXIT_STATE, parse_with_grammar_entry
from pyfcstm.entry.simulate.batch import BatchProcessor, create_cross_platform_output_func
from pyfcstm.entry.simulate.commands import CommandProcessor
from pyfcstm.entry.simulate.events import get_current_event_display_items
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

_ENDED_MULTIPLE_CYCLE_DSL = textwrap.dedent("""
    state System {
        state A;
        [*] -> A;
        A -> [*];
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


class _DummySession:
    """
    Lightweight stand-in for ``prompt_toolkit.PromptSession``.

    PromptSession's constructor opens a real terminal output handle. On
    Windows CI (xterm under the GitHub Actions runner) that crashes with
    ``NoConsoleScreenBufferError`` because there's no Windows console.
    We bypass the real constructor and only expose ``prompt`` (which the
    test then replaces with a scripted callable).
    """

    def __init__(self, *args, **kwargs):
        self.history = kwargs.get('history')
        self.auto_suggest = kwargs.get('auto_suggest')
        self.completer = kwargs.get('completer')
        self.enable_history_search = kwargs.get('enable_history_search')
        self.style = kwargs.get('style')

    def prompt(self, *args, **kwargs):  # pragma: no cover - replaced per test
        raise EOFError


@pytest.fixture
def patch_prompt_session(monkeypatch):
    """Patch PromptSession before SimulationREPL constructs it."""
    from pyfcstm.entry.simulate import repl as repl_module
    monkeypatch.setattr(repl_module, 'PromptSession', _DummySession)
    return _DummySession


@pytest.mark.unittest
class TestSimulationREPLRun:
    def test_run_processes_commands_then_exits_on_quit(self, capsys, patch_prompt_session):
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

    def test_run_eof_exits_gracefully(self, capsys, patch_prompt_session):
        runtime, model = _make_runtime()
        repl = SimulationREPL(runtime, state_machine=model, use_color=False)

        scripted = _ScriptedPrompt([EOFError()])
        repl.session.prompt = scripted

        repl.run()

        captured = capsys.readouterr()
        assert 'Goodbye' in captured.out

    def test_run_keyboard_interrupt_continues(self, capsys, patch_prompt_session):
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


_SESSION_STATE_DSL = textwrap.dedent("""
    def int counter = 0;

    state System {
        [*] -> Idle;
        state Idle {
            during abstract Touch;
            during { counter = counter + 1; }
        }
        state Active {
            during { counter = counter + 10; }
        }
    }
""").strip()

_CONTINUATION_DSL = textwrap.dedent("""
    state Root {
        state System1 {
            state A;
            [*] -> A;
            A -> [*] :: Exit;
        }
        state System2 {
            state B;
            [*] -> B;
            B -> [*];
        }
        [*] -> System1;
        System1 -> System2 :: Switch;
        System2 -> [*];
    }
""").strip()

_AUTO_EXIT_CONTINUATION_DSL = textwrap.dedent("""
    state Root {
        state System1 {
            state A;
            [*] -> A;
            A -> [*];
        }
        state System2 {
            state B;
            [*] -> B;
        }
        [*] -> System1;
        System1 -> System2 :: Switch;
    }
""").strip()

_CASCADED_CONTINUATION_DSL = textwrap.dedent("""
    state Root {
        state System1 {
            state Sub {
                state A;
                [*] -> A;
                A -> [*] :: Exit;
            }
            [*] -> Sub;
            Sub -> [*];
        }
        state System2 {
            state B;
            [*] -> B;
        }
        [*] -> System1;
        System1 -> System2 :: Switch;
    }
""").strip()


def _build_runtime(dsl_code):
    ast_node = parse_with_grammar_entry(dsl_code, entry_name='state_machine_dsl')
    model = parse_dsl_node_to_state_machine(ast_node)
    return SimulationRuntime(model), model


def _run_to_idle_processor():
    runtime, model = _build_runtime(_SESSION_STATE_DSL)
    processor = CommandProcessor(runtime, state_machine=model, use_color=False)
    processor.process('cycle')
    return processor


@pytest.mark.unittest
class TestCommandProcessorSessionState:
    def test_default_history_size_setting_matches_runtime_retention(self):
        processor = _run_to_idle_processor()

        assert 'history_size = 100' in processor.process('setting history_size').output
        assert processor.runtime.history_size == 100

        processor.process('cycle 105')
        assert len(processor.runtime.history) == 100

        processor.process('clear')
        assert 'history_size = 100' in processor.process('setting history_size').output
        assert processor.runtime.history_size == 100

        processor.process('cycle 105')
        assert len(processor.runtime.history) == 100

    def test_constructor_history_size_becomes_displayed_session_setting(self):
        runtime, model = _build_runtime(_SESSION_STATE_DSL)

        processor = CommandProcessor(
            SimulationRuntime(model, history_size=2),
            state_machine=model,
            use_color=False,
        )

        assert 'history_size = 2' in processor.process('setting history_size').output
        processor.process('cycle 4')
        assert len(processor.runtime.history) == 2

    def test_clear_preserves_history_size_setting(self):
        processor = _run_to_idle_processor()
        processor.process('setting history_size 1')
        processor.process('cycle')
        processor.process('cycle')

        assert processor.runtime.history_size == 1
        assert len(processor.runtime.history) == 1

        processor.process('clear')
        assert processor.settings.history_size == 1
        assert processor.runtime.history_size == 1

        processor.process('cycle')
        processor.process('cycle')
        assert len(processor.runtime.history) == 1
        assert processor.runtime.history[-1]['cycle'] == processor.runtime.cycle_count

    def test_init_preserves_registered_abstract_handlers(self):
        processor = _run_to_idle_processor()
        calls = []

        def record_touch(ctx):
            calls.append(ctx.get_full_state_path())

        processor.runtime.register_abstract_handler('System.Idle.Touch', record_touch)
        result = processor.process('init System.Idle counter=10')

        assert 'Initialized from state: System.Idle' in result.output
        assert processor.runtime.has_abstract_handlers('System.Idle.Touch')

        processor.process('cycle')
        assert calls == ['System.Idle']
        assert processor.runtime.vars['counter'] == 11

    def test_clear_preserves_abstract_handlers_and_error_mode(self):
        processor = _run_to_idle_processor()

        def raise_touch(ctx):
            raise ValueError('touch failed')

        processor.runtime.register_abstract_handler('System.Idle.Touch', raise_touch)
        processor.runtime._abstract_error_mode = 'log'

        processor.process('clear')
        assert processor.runtime.has_abstract_handlers('System.Idle.Touch')
        assert processor.runtime._abstract_error_mode == 'log'

        processor.process('cycle')
        assert not processor.runtime.is_error_state
        assert len(processor.runtime.abstract_handler_errors) == 1
        action_path, error = processor.runtime.abstract_handler_errors[0]
        assert action_path == 'System.Idle.Touch'
        assert isinstance(error, ValueError)
        assert str(error) == 'touch failed'

    def test_events_lists_parent_continuation_candidates(self):
        runtime, model = _build_runtime(_CONTINUATION_DSL)
        processor = CommandProcessor(runtime, state_machine=model, use_color=False)
        processor.process('cycle')

        result = processor.process('events')

        assert 'Exit' in result.output
        assert 'Root.System1.A.Exit' in result.output
        assert 'Root.System1.Switch' in result.output
        assert 'post-exit continuation' in result.output

        cycle_result = processor.process('cycle Exit Root.System1.Switch')
        assert 'Root.System2.B' in cycle_result.output

    def test_events_lists_cascaded_parent_continuation_candidates(self):
        runtime, model = _build_runtime(_CASCADED_CONTINUATION_DSL)
        processor = CommandProcessor(runtime, state_machine=model, use_color=False)
        processor.process('cycle')

        result = processor.process('events')

        assert 'Exit' in result.output
        assert 'Root.System1.Sub.A.Exit' in result.output
        assert 'Root.System1.Switch' in result.output
        assert 'post-exit continuation' in result.output

        cycle_result = processor.process('cycle Exit Root.System1.Switch')
        assert 'Root.System2.B' in cycle_result.output

    def test_events_lists_continuation_candidate_after_automatic_exit(self):
        runtime, model = _build_runtime(_AUTO_EXIT_CONTINUATION_DSL)
        processor = CommandProcessor(runtime, state_machine=model, use_color=False)
        processor.process('cycle')

        result = processor.process('events')

        assert 'Root.System1.Switch' in result.output
        assert 'post-exit continuation' in result.output

    def test_events_omits_continuation_candidates_after_end(self):
        runtime, model = _build_runtime(_CONTINUATION_DSL)
        processor = CommandProcessor(runtime, state_machine=model, use_color=False)
        processor.process('cycle')
        processor.process('cycle Exit Root.System1.Switch')
        assert processor.runtime.current_state.path == ('Root', 'System2', 'B')
        processor.process('cycle')
        assert processor.runtime.is_ended

        result = processor.process('events')

        assert 'Root.System1.Switch' not in result.output
        assert 'No events available' in result.output

    def test_ended_multiple_cycle_table_uses_actual_cycle_count(self):
        runtime, model = _build_runtime(_ENDED_MULTIPLE_CYCLE_DSL)
        processor = CommandProcessor(runtime, state_machine=model, use_color=False)

        first_result = processor.process('cycle')

        assert not first_result.should_exit
        assert processor.runtime.current_state.path == ('System', 'A')
        assert not processor.runtime.is_ended
        assert processor.runtime.cycle_count == 1

        result = processor.process('cycle 5')

        assert not result.should_exit
        assert '(terminated)' in result.output
        assert ' 2 ' in result.output
        for fabricated_cycle in (' 3 ', ' 4 ', ' 5 ', ' 6 '):
            assert fabricated_cycle not in result.output
        assert processor.runtime.is_ended
        assert processor.runtime.cycle_count == 2


@pytest.mark.unittest
class TestRuntimeReferenceSynchronization:
    def test_repl_init_refreshes_runtime_and_completer_reference(self, patch_prompt_session):
        runtime, model = _build_runtime(_SESSION_STATE_DSL)
        repl = SimulationREPL(runtime, state_machine=model, use_color=False)

        repl.command_processor.process('init System.Active counter=7')

        assert repl.runtime is repl.command_processor.runtime
        assert repl.completer.runtime is repl.command_processor.runtime
        assert repl.session.auto_suggest.completer.runtime is repl.command_processor.runtime
        assert repl.runtime.current_state.path == ('System', 'Active')

    def test_batch_init_refreshes_runtime_reference(self):
        runtime, model = _build_runtime(_SESSION_STATE_DSL)
        batch = BatchProcessor(runtime, state_machine=model, use_color=False, output_func=lambda text: None)

        batch.execute_commands('init System.Active counter=7')

        assert batch.runtime is batch.command_processor.runtime
        assert batch.runtime.current_state.path == ('System', 'Active')

    def test_batch_clear_refreshes_runtime_reference(self):
        runtime, model = _build_runtime(_SESSION_STATE_DSL)
        batch = BatchProcessor(runtime, state_machine=model, use_color=False, output_func=lambda text: None)
        batch.execute_commands('cycle; clear')

        assert batch.runtime is batch.command_processor.runtime
        assert batch.runtime.current_state.path == ('System',)


@pytest.mark.unittest
class TestSimulationCompleterRuntimeEvents:
    def test_cycle_completion_includes_parent_continuation_event_path(self):
        runtime, model = _build_runtime(_CONTINUATION_DSL)
        processor = CommandProcessor(runtime, state_machine=model, use_color=False)
        processor.process('cycle')
        completer = processor.create_completer()

        completions = list(completer.get_completions(Document('cycle Root.System1.S'), None))
        completion_texts = {completion.text for completion in completions}
        completion_meta = {
            completion.text: str(completion.display_meta_text)
            for completion in completions
        }

        assert 'Root.System1.Switch' in completion_texts
        assert 'post-exit continuation' in completion_meta['Root.System1.Switch']

    def test_cycle_completion_includes_cascaded_parent_continuation_event_path(self):
        runtime, model = _build_runtime(_CASCADED_CONTINUATION_DSL)
        processor = CommandProcessor(runtime, state_machine=model, use_color=False)
        processor.process('cycle')
        completer = processor.create_completer()

        completions = list(completer.get_completions(Document('cycle Root.System1.S'), None))
        completion_texts = {completion.text for completion in completions}
        completion_meta = {
            completion.text: str(completion.display_meta_text)
            for completion in completions
        }

        assert 'Root.System1.Switch' in completion_texts
        assert 'post-exit continuation' in completion_meta['Root.System1.Switch']


class _NoCurrentStateRuntime:
    is_ended = False

    @property
    def current_state(self):
        raise IndexError('no active state')


class _NoneCurrentStateRuntime:
    is_ended = False
    current_state = None


class _FakeEvent:
    def __init__(self, path_name, name):
        self.path_name = path_name
        self.name = name


class _FakeTransition:
    def __init__(self, event, to_state='Other'):
        self.event = event
        self.to_state = to_state


class _FakeState:
    def __init__(self, transitions, parent=None, is_root_state=False):
        self.is_root_state = is_root_state
        self.parent = parent
        self.transitions_from = transitions


class _FakeRuntime:
    is_ended = False

    def __init__(self, current_state):
        self.current_state = current_state


@pytest.mark.unittest
class TestEventDisplayItems:
    def test_display_items_return_empty_without_active_state(self):
        assert get_current_event_display_items(_NoCurrentStateRuntime()) == []
        assert get_current_event_display_items(_NoneCurrentStateRuntime()) == []

    def test_display_items_deduplicate_event_paths(self):
        event = _FakeEvent('System.A.Go', 'Go')
        state = _FakeState([
            _FakeTransition(event),
            _FakeTransition(event),
        ])

        assert get_current_event_display_items(_FakeRuntime(state)) == [('System.A.Go', 'Go')]

    def test_display_items_omits_root_boundary_continuation(self):
        root = _FakeState([], is_root_state=True)
        state = _FakeState([_FakeTransition(None, to_state=EXIT_STATE)], parent=root)

        assert get_current_event_display_items(_FakeRuntime(state)) == []

    def test_display_items_deduplicate_continuation_event_paths(self):
        event = _FakeEvent('Root.Parent.Switch', 'Switch')
        parent = _FakeState([
            _FakeTransition(event),
            _FakeTransition(event),
        ])
        state = _FakeState([_FakeTransition(None, to_state=EXIT_STATE)], parent=parent)

        assert get_current_event_display_items(_FakeRuntime(state)) == [
            ('Root.Parent.Switch', 'post-exit continuation'),
        ]
