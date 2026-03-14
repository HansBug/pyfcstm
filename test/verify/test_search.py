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


@pytest.mark.unittest
class TestSearchFrameHelpers:
    def test_get_history_returns_frames_in_forward_order(self):
        state_machine = build_state_machine()
        state = state_machine.resolve_state('Root.Idle')

        frame0 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={},
            constraints=z3.BoolVal(True),
            event=None,
            depth=0,
            cycle=0,
            prev_frame=None,
        )
        frame1 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={},
            constraints=z3.BoolVal(True),
            event=None,
            depth=1,
            cycle=1,
            prev_frame=frame0,
        )
        frame2 = verify_search.SearchFrame(
            state=state,
            type='leaf',
            var_state={},
            constraints=z3.BoolVal(True),
            event=None,
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
            event=None,
            depth=0,
            cycle=0,
            prev_frame=None,
        )

        result = frame.solve(max_solutions=1)

        assert isinstance(result, SolveResult)
        assert result.status == 'sat'
        assert result.variables == ['x']
        assert result.solutions == [{'x': 3}]


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
