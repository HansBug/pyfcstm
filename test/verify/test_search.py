from types import SimpleNamespace

import z3
import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine, parse_expr, Event
from pyfcstm.solver import SolveResult
from pyfcstm.verify import search as verify_search


TEST_DSL = '''
def int counter = 0;
state Root {
    state Idle;
    [*] -> Idle;
}
'''

PSEUDO_CHAIN_DSL = '''
state Root {
    pseudo state Alpha;
    pseudo state Beta;
    pseudo state Gamma;
    pseudo state Delta;
    pseudo state Omega;

    [*] -> Alpha;
    Alpha -> Beta;
    Beta -> Gamma;
    Gamma -> Delta;
    Delta -> Omega;
}
'''


def build_state_machine(dsl_code: str = TEST_DSL):
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


@pytest.mark.unittest
class TestBfsSearchErrors:
    def test_rejects_invalid_init_state_type(self):
        state_machine = build_state_machine()

        with pytest.raises(TypeError) as exc_info:
            verify_search.bfs_search(state_machine, 123)

        message = str(exc_info.value)
        assert "expected 'init_state' to be a State object or a full state path string" in message
        assert "got int: 123" in message
        assert "Root.System.Active" in message

    def test_rejects_state_from_other_machine(self):
        state_machine = build_state_machine()
        other_state_machine = build_state_machine()
        foreign_state = other_state_machine.resolve_state('Root.Idle')

        with pytest.raises(ValueError) as exc_info:
            verify_search.bfs_search(state_machine, foreign_state)

        message = str(exc_info.value)
        assert "does not belong to the provided state machine" in message
        assert "'Root.Idle'" in message
        assert "different parsed state machine instance" in message

    def test_wraps_invalid_init_state_path(self):
        state_machine = build_state_machine()

        with pytest.raises(LookupError) as exc_info:
            verify_search.bfs_search(state_machine, 'Root.Missing')

        message = str(exc_info.value)
        assert "Failed to resolve 'init_state' for bfs_search()" in message
        assert "'Root.Missing'" in message
        assert "starts from the state machine root" in message

    def test_rejects_invalid_init_constraints_type(self):
        state_machine = build_state_machine()

        with pytest.raises(TypeError) as exc_info:
            verify_search.bfs_search(state_machine, 'Root.Idle', init_constraints=['counter > 0'])

        message = str(exc_info.value)
        assert "expected 'init_constraints' to be None" in message
        assert "got list: ['counter > 0']" in message
        assert "logical condition such as 'counter > 0 && enabled'" in message

    def test_rejects_invalid_fn_on_enqueue_type(self):
        state_machine = build_state_machine()

        with pytest.raises(TypeError) as exc_info:
            verify_search.bfs_search(state_machine, 'Root.Idle', fn_on_enqueue=123)

        message = str(exc_info.value)
        assert "expected 'fn_on_enqueue' to be None or a callable" in message
        assert "got int: 123" in message

    def test_rejects_non_logical_constraint_string(self):
        state_machine = build_state_machine()

        with pytest.raises(ValueError) as exc_info:
            verify_search.bfs_search(state_machine, 'Root.Idle', init_constraints='counter + 1')

        message = str(exc_info.value)
        assert "Failed to parse 'init_constraints' for bfs_search()" in message
        assert "'counter + 1'" in message
        assert "must be a logical DSL condition" in message

    def test_rejects_non_boolean_constraint_expr(self):
        state_machine = build_state_machine()

        with pytest.raises(ValueError) as exc_info:
            verify_search.bfs_search(
                state_machine,
                'Root.Idle',
                init_constraints=parse_expr('counter + 1'),
            )

        message = str(exc_info.value)
        assert "produced a non-boolean constraint" in message
        assert "counter + 1" in message
        assert "use a comparison such as 'counter > 0'" in message

    def test_reports_unexpected_internal_frame_type(self, monkeypatch):
        state_machine = build_state_machine()

        def _broken_search_frame(**kwargs):
            frame = SimpleNamespace(**kwargs)
            frame.type = 'broken'
            return frame

        monkeypatch.setattr(verify_search, 'SearchFrame', _broken_search_frame)

        with pytest.raises(RuntimeError) as exc_info:
            verify_search.bfs_search(state_machine, 'Root.Idle')

        message = str(exc_info.value)
        assert "unsupported type 'broken'" in message
        assert "'Root.Idle'" in message
        assert "Supported frame types are 'leaf', 'composite_in', 'composite_out', and 'end'" in message


@pytest.mark.unittest
class TestBfsSearchLimits:
    def test_warns_when_max_cycle_and_max_depth_are_both_unbounded(self):
        state_machine = build_state_machine(PSEUDO_CHAIN_DSL)

        with pytest.warns(
                UserWarning,
                match=r"max_cycle=None and max_depth=None",
        ):
            ctx = verify_search.bfs_search(
                state_machine,
                'Root.Alpha',
                max_cycle=None,
                max_depth=None,
            )

        assert ('Root.Omega', 'leaf') in ctx.spaces

    def test_derives_default_max_depth_from_max_cycle(self):
        state_machine = build_state_machine(PSEUDO_CHAIN_DSL)

        ctx = verify_search.bfs_search(
            state_machine,
            'Root.Alpha',
            max_cycle=1,
            max_depth=None,
        )

        assert ('Root.Alpha', 'leaf') in ctx.spaces
        assert ('Root.Beta', 'leaf') in ctx.spaces
        assert ('Root.Gamma', 'leaf') in ctx.spaces
        assert ('Root.Delta', 'leaf') in ctx.spaces
        assert ('Root.Omega', 'leaf') not in ctx.spaces

    def test_explicit_max_depth_overrides_derived_default(self):
        state_machine = build_state_machine(PSEUDO_CHAIN_DSL)

        with pytest.warns(
                UserWarning,
                match=r"max_depth=2 and max_cycle=5",
        ):
            ctx = verify_search.bfs_search(
                state_machine,
                'Root.Alpha',
                max_cycle=5,
                max_depth=2,
            )

        assert ('Root.Alpha', 'leaf') in ctx.spaces
        assert ('Root.Beta', 'leaf') in ctx.spaces
        assert ('Root.Gamma', 'leaf') in ctx.spaces
        assert ('Root.Delta', 'leaf') not in ctx.spaces

    def test_warns_when_max_cycle_is_unbounded_but_max_depth_is_finite(self):
        state_machine = build_state_machine(PSEUDO_CHAIN_DSL)

        with pytest.warns(UserWarning) as warnings_info:
            ctx = verify_search.bfs_search(
                state_machine,
                'Root.Alpha',
                max_cycle=None,
                max_depth=2,
            )

        messages = [str(item.message) for item in warnings_info]
        assert len(messages) == 2
        assert any("max_cycle=None. Cycle expansion is unlimited" in message for message in messages)
        assert any("max_depth=2 and max_cycle=None" in message for message in messages)
        assert ('Root.Gamma', 'leaf') in ctx.spaces
        assert ('Root.Delta', 'leaf') not in ctx.spaces

    def test_fn_on_enqueue_can_stop_search_early(self):
        state_machine = build_state_machine(PSEUDO_CHAIN_DSL)
        seen_space_keys = []

        def _stop_when_beta_enqueued(ctx):
            seen_space_keys.append(sorted(ctx.spaces.keys()))
            return ('Root.Beta', 'leaf') in ctx.spaces

        ctx = verify_search.bfs_search(
            state_machine,
            'Root.Alpha',
            max_cycle=5,
            fn_on_enqueue=_stop_when_beta_enqueued,
        )

        assert len(seen_space_keys) >= 2
        assert seen_space_keys[0] == [('Root.Alpha', 'leaf')]
        assert ('Root.Beta', 'leaf') in seen_space_keys[-1]
        assert ('Root.Alpha', 'leaf') in ctx.spaces
        assert ('Root.Beta', 'leaf') in ctx.spaces
        assert ('Root.Gamma', 'leaf') not in ctx.spaces
        assert list(ctx.queue) == [ctx.spaces[('Root.Beta', 'leaf')].frames[0]]

    def test_rejects_non_bool_fn_on_enqueue_result(self):
        state_machine = build_state_machine()

        with pytest.raises(TypeError) as exc_info:
            verify_search.bfs_search(
                state_machine,
                'Root.Idle',
                fn_on_enqueue=lambda ctx: 'stop',
            )

        message = str(exc_info.value)
        assert "expected 'fn_on_enqueue' to return a bool" in message
        assert "'stop'" in message


@pytest.mark.unittest
class TestSearchFrameHelpers:
    def test_state_search_context_try_append_frame_retains_new_space_once(self):
        state_machine = build_state_machine()
        state = state_machine.resolve_state('Root.Idle')
        ctx = verify_search.StateSearchContext()

        frame0 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={},
            constraints=z3.BoolVal(True),
            event_var=None,
            depth=0,
            cycle=0,
            prev_frame=None,
        )
        frame1 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={},
            constraints=z3.BoolVal(False),
            event_var=None,
            depth=1,
            cycle=1,
            prev_frame=frame0,
        )

        assert ctx.try_append_frame(frame0) is True
        assert ctx.try_append_frame(frame1) is False
        assert list(ctx.queue) == [frame0]
        assert ctx.spaces[('Root.Idle', 'leaf')].frames == [frame0]

    def test_get_history_returns_frames_in_forward_order(self):
        state_machine = build_state_machine()
        state = state_machine.resolve_state('Root.Idle')

        frame0 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={},
            constraints=z3.BoolVal(True),
            event_var=None,
            depth=0,
            cycle=0,
            prev_frame=None,
        )
        frame1 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={},
            constraints=z3.BoolVal(True),
            event_var=None,
            depth=1,
            cycle=1,
            prev_frame=frame0,
        )
        frame2 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={},
            constraints=z3.BoolVal(True),
            event_var=None,
            depth=2,
            cycle=2,
            prev_frame=frame1,
        )

        history = frame2.get_history()

        assert history == [frame0, frame1, frame2]

    def test_solve_delegates_to_solver_and_returns_result(self):
        x = z3.Int('x')
        frame = verify_search.SearchFrame(
            state=None,
            type='end',
            var_state={'x': x},
            constraints=x == 3,
            event_var=None,
            depth=0,
            cycle=0,
            prev_frame=None,
        )

        result = frame.solve(max_solutions=1)

        assert isinstance(result, SolveResult)
        assert result.status == 'sat'
        assert result.variables == ['x']
        assert result.solutions == [{'x': 3}]

    def test_to_concrete_frames_materializes_cycle_level_events(self):
        state_machine = build_state_machine()
        state = state_machine.resolve_state('Root.Idle')
        base = z3.Int('base')

        event_start = Event(name='Start', state_path=('Root', 'Idle'))
        event_pause = Event(name='Pause', state_path=('Root', 'Idle'))
        event_resume = Event(name='Resume', state_path=('Root', 'Idle'))

        _, start_var_name = verify_search.get_z3_event_key_and_var_name(0, event_start)
        _, pause_var_name = verify_search.get_z3_event_key_and_var_name(1, event_pause)
        _, resume_var_name = verify_search.get_z3_event_key_and_var_name(2, event_resume)
        _, unrelated_var_name = verify_search.get_z3_event_key_and_var_name(1, 'Root.Idle.Unrelated')

        start_var = z3.Bool(start_var_name)
        pause_var = z3.Bool(pause_var_name)
        resume_var = z3.Bool(resume_var_name)

        frame0 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base},
            constraints=base == 10,
            event_var=None,
            depth=0,
            cycle=0,
            prev_frame=None,
        )
        frame1 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 1},
            constraints=base == 10,
            event_var=None,
            depth=1,
            cycle=0,
            prev_frame=frame0,
        )
        frame2 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 2},
            constraints=z3.And(base == 10, start_var),
            event_var=start_var,
            depth=2,
            cycle=0,
            prev_frame=frame1,
        )
        frame3 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 3},
            constraints=z3.And(base == 10, start_var),
            event_var=None,
            depth=3,
            cycle=1,
            prev_frame=frame2,
        )
        frame4 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 4},
            constraints=z3.And(base == 10, start_var, pause_var),
            event_var=pause_var,
            depth=4,
            cycle=1,
            prev_frame=frame3,
        )
        frame5 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 5},
            constraints=z3.And(base == 10, start_var, pause_var),
            event_var=None,
            depth=5,
            cycle=1,
            prev_frame=frame4,
        )
        frame6 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 6},
            constraints=z3.And(base == 10, start_var, pause_var),
            event_var=None,
            depth=6,
            cycle=2,
            prev_frame=frame5,
        )
        frame7 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 7},
            constraints=z3.And(base == 10, start_var, pause_var, resume_var),
            event_var=resume_var,
            depth=7,
            cycle=2,
            prev_frame=frame6,
        )
        frame8 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 8},
            constraints=z3.And(base == 10, start_var, pause_var, resume_var),
            event_var=None,
            depth=8,
            cycle=3,
            prev_frame=frame7,
        )

        assert frame0.event_cycle is None
        assert frame0.event_path_name is None
        assert frame2.event_cycle == 0
        assert frame2.event_path_name == event_start.path_name
        assert frame4.event_cycle == 1
        assert frame4.event_path_name == event_pause.path_name
        assert frame7.event_cycle == 2
        assert frame7.event_path_name == event_resume.path_name

        concrete_frames = frame8.to_concrete_frames({
            'base': 10,
            start_var_name: True,
            pause_var_name: True,
            resume_var_name: True,
            unrelated_var_name: True,
        })

        assert len(concrete_frames) == 9
        assert [frame.depth for frame in concrete_frames] == list(range(9))
        assert [frame.cycle for frame in concrete_frames] == [0, 0, 0, 1, 1, 1, 2, 2, 3]
        assert [frame.var_state['counter'] for frame in concrete_frames] == [10, 11, 12, 13, 14, 15, 16, 17, 18]
        assert all(frame.satisfied is True for frame in concrete_frames)
        assert concrete_frames[0].events == ['Root.Idle.Start']
        assert concrete_frames[1].events == ['Root.Idle.Start']
        assert concrete_frames[2].events == ['Root.Idle.Start']
        assert concrete_frames[3].events == ['Root.Idle.Pause']
        assert concrete_frames[4].events == ['Root.Idle.Pause']
        assert concrete_frames[5].events == ['Root.Idle.Pause']
        assert concrete_frames[6].events == ['Root.Idle.Resume']
        assert concrete_frames[7].events == ['Root.Idle.Resume']
        assert concrete_frames[8].events == []
        assert concrete_frames[8].get_history() == concrete_frames
        assert concrete_frames[8].get_history(cycle_only=True) == [
            concrete_frames[2],
            concrete_frames[5],
            concrete_frames[7],
            concrete_frames[8],
        ]
        assert concrete_frames[0].prev_cycle_frame is None
        assert concrete_frames[1].prev_cycle_frame is None
        assert concrete_frames[2].prev_cycle_frame is None
        assert concrete_frames[3].prev_cycle_frame is concrete_frames[2]
        assert concrete_frames[4].prev_cycle_frame is concrete_frames[2]
        assert concrete_frames[5].prev_cycle_frame is concrete_frames[2]
        assert concrete_frames[6].prev_cycle_frame is concrete_frames[5]
        assert concrete_frames[7].prev_cycle_frame is concrete_frames[5]
        assert concrete_frames[8].prev_cycle_frame is concrete_frames[7]
        assert concrete_frames[0].prev_frame is None
        assert concrete_frames[1].prev_frame is concrete_frames[0]
        assert concrete_frames[8].prev_frame is concrete_frames[7]

    def test_to_concrete_frames_collects_multiple_events_in_same_cycle(self):
        state_machine = build_state_machine()
        state = state_machine.resolve_state('Root.Idle')
        base = z3.Int('base')

        event_alpha = Event(name='Alpha', state_path=('Root', 'Idle'))
        event_beta = Event(name='Beta', state_path=('Root', 'Idle'))
        event_gamma = Event(name='Gamma', state_path=('Root', 'Idle'))

        _, alpha_var_name = verify_search.get_z3_event_key_and_var_name(1, event_alpha)
        _, beta_var_name = verify_search.get_z3_event_key_and_var_name(1, event_beta)
        _, gamma_var_name = verify_search.get_z3_event_key_and_var_name(1, event_gamma)

        alpha_var = z3.Bool(alpha_var_name)
        beta_var = z3.Bool(beta_var_name)
        gamma_var = z3.Bool(gamma_var_name)

        frame0 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base},
            constraints=base == 20,
            event_var=None,
            depth=0,
            cycle=0,
            prev_frame=None,
        )
        frame1 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 1},
            constraints=base == 20,
            event_var=None,
            depth=1,
            cycle=1,
            prev_frame=frame0,
        )
        frame2 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 2},
            constraints=z3.And(base == 20, alpha_var),
            event_var=alpha_var,
            depth=2,
            cycle=1,
            prev_frame=frame1,
        )
        frame3 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 3},
            constraints=z3.And(base == 20, alpha_var, beta_var),
            event_var=beta_var,
            depth=3,
            cycle=1,
            prev_frame=frame2,
        )
        frame4 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 4},
            constraints=z3.And(base == 20, alpha_var, beta_var),
            event_var=alpha_var,
            depth=4,
            cycle=1,
            prev_frame=frame3,
        )
        frame5 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 5},
            constraints=z3.And(base == 20, alpha_var, beta_var),
            event_var=gamma_var,
            depth=5,
            cycle=1,
            prev_frame=frame4,
        )
        frame6 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={'counter': base + 6},
            constraints=z3.And(base == 20, alpha_var, beta_var),
            event_var=None,
            depth=6,
            cycle=2,
            prev_frame=frame5,
        )

        concrete_frames = frame6.to_concrete_frames({
            'base': 20,
            alpha_var_name: True,
            beta_var_name: True,
            gamma_var_name: False,
        })

        assert len(concrete_frames) == 7
        assert [frame.cycle for frame in concrete_frames] == [0, 1, 1, 1, 1, 1, 2]
        assert [frame.var_state['counter'] for frame in concrete_frames] == [20, 21, 22, 23, 24, 25, 26]
        assert concrete_frames[0].events == []
        assert concrete_frames[1].events == ['Root.Idle.Alpha', 'Root.Idle.Beta']
        assert concrete_frames[2].events == ['Root.Idle.Alpha', 'Root.Idle.Beta']
        assert concrete_frames[3].events == ['Root.Idle.Alpha', 'Root.Idle.Beta']
        assert concrete_frames[4].events == ['Root.Idle.Alpha', 'Root.Idle.Beta']
        assert concrete_frames[5].events == ['Root.Idle.Alpha', 'Root.Idle.Beta']
        assert concrete_frames[6].events == []
        assert all('Root.Idle.Gamma' not in frame.events for frame in concrete_frames)


@pytest.mark.unittest
class TestZ3EventVarNameHelpers:
    def test_detects_valid_event_var_name_string(self):
        assert verify_search.is_z3_event_var_name('_E_C6__Root.System.Tick') is True

    def test_detects_valid_event_var_name_z3_variable(self):
        assert verify_search.is_z3_event_var_name(z3.Bool('_E_C7__Root.System.Tick')) is True

    def test_rejects_invalid_event_var_name_via_bool_helper(self):
        assert verify_search.is_z3_event_var_name('Root.System.Tick') is False
        assert verify_search.is_z3_event_var_name(z3.Not(z3.Bool('_E_C1__Root.System.Tick'))) is False
        assert verify_search.is_z3_event_var_name(123) is False

    def test_builds_event_key_and_var_name_from_string(self):
        key, var_name = verify_search.get_z3_event_key_and_var_name(
            cycle=2,
            event='Root.Idle.Resume',
        )

        assert key == (2, 'Root.Idle.Resume')
        assert var_name == '_E_C2__Root.Idle.Resume'

    def test_builds_event_key_and_var_name_from_event_object(self):
        key, var_name = verify_search.get_z3_event_key_and_var_name(
            cycle=3,
            event=Event(name='Resume', state_path=('Root', 'Idle')),
        )

        assert key == (3, 'Root.Idle.Resume')
        assert var_name == '_E_C3__Root.Idle.Resume'

    def test_parses_event_var_name_from_string(self):
        cycle, event_name = verify_search.parse_z3_event_var_name('_E_C4__Root.Idle.Resume')

        assert cycle == 4
        assert event_name == 'Root.Idle.Resume'

    def test_parses_event_var_name_from_z3_variable(self):
        cycle, event_name = verify_search.parse_z3_event_var_name(
            z3.Bool('_E_C5__Root.System.Tick'),
        )

        assert cycle == 5
        assert event_name == 'Root.System.Tick'

    def test_rejects_invalid_event_var_name_string(self):
        with pytest.raises(ValueError) as exc_info:
            verify_search.parse_z3_event_var_name('Root.System.Tick')

        message = str(exc_info.value)
        assert "Failed to parse a Z3 event variable name" in message
        assert "Expected format '_E_C<cycle>__<event_path>'" in message

    def test_rejects_non_variable_z3_expression(self):
        with pytest.raises(TypeError) as exc_info:
            verify_search.parse_z3_event_var_name(z3.Not(z3.Bool('_E_C1__Root.System.Tick')))

        message = str(exc_info.value)
        assert "expected a string or a Z3 symbolic variable" in message

    def test_rejects_invalid_forward_inputs(self):
        with pytest.raises(TypeError) as exc_info:
            verify_search.get_z3_event_key_and_var_name(cycle='1', event='Root.System.Tick')

        assert "expected 'cycle' to be an int" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            verify_search.get_z3_event_key_and_var_name(cycle=1, event='')

        assert "non-empty event path string" in str(exc_info.value)
