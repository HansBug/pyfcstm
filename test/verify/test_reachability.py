import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.verify import ReachabilityResult, SearchConcreteFrame, SearchFrame, StateSearchContext, verify_reachability


DETAILED_REACHABILITY_DSL = '''
def int counter = 0;
state Root {
    state Idle;
    state Warmup;
    state Ready;
    [*] -> Idle;
    Idle -> Warmup : if [counter >= 1];
    Warmup -> Ready : if [counter >= 2];
}
'''

SIMPLE_REACHABILITY_DSL = '''
def int counter = 0;
state Root {
    state Idle;
    state Ready;
    [*] -> Idle;
    Idle -> Ready : if [counter >= 1];
}
'''


def build_state_machine(dsl_code: str = SIMPLE_REACHABILITY_DSL):
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


@pytest.mark.unittest
class TestVerifyReachability:
    def test_returns_detailed_witness_path_for_reachable_target(self):
        state_machine = build_state_machine(DETAILED_REACHABILITY_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=('Root.Idle', 'counter >= 2'),
            target_state='Root.Ready',
            max_cycle=2,
        )

        assert isinstance(result, ReachabilityResult)
        assert result.reachable is True

        assert isinstance(result.search_context, StateSearchContext)
        assert ('Root.Idle', 'leaf') in result.search_context.spaces
        assert ('Root.Warmup', 'leaf') in result.search_context.spaces
        assert ('Root.Ready', 'leaf') in result.search_context.spaces

        assert isinstance(result.target_frame, SearchFrame)
        assert result.target_frame is result.search_context.spaces[('Root.Ready', 'leaf')].frames[0]
        assert result.target_frame.state.path == ('Root', 'Ready')
        assert result.target_frame.type == 'leaf'
        assert result.target_frame.depth == 2
        assert result.target_frame.cycle == 2
        assert result.target_frame.event_var is None
        assert result.target_frame.event_cycle is None
        assert result.target_frame.event_path_name is None

        symbolic_history = result.target_frame.get_history()
        assert [frame.state.path for frame in symbolic_history] == [
            ('Root', 'Idle'),
            ('Root', 'Warmup'),
            ('Root', 'Ready'),
        ]
        assert [frame.depth for frame in symbolic_history] == [0, 1, 2]
        assert [frame.cycle for frame in symbolic_history] == [0, 1, 2]
        assert all(frame.type == 'leaf' for frame in symbolic_history)
        assert symbolic_history[0].prev_frame is None
        assert symbolic_history[1].prev_frame is symbolic_history[0]
        assert symbolic_history[2].prev_frame is symbolic_history[1]

        assert result.solution is not None
        assert result.solution == {'counter': 2}

        assert isinstance(result.concrete_path, list)
        assert len(result.concrete_path) == 3
        assert all(isinstance(frame, SearchConcreteFrame) for frame in result.concrete_path)

        concrete_path = result.concrete_path
        assert [frame.state.path for frame in concrete_path] == [
            ('Root', 'Idle'),
            ('Root', 'Warmup'),
            ('Root', 'Ready'),
        ]
        assert [frame.type for frame in concrete_path] == ['leaf', 'leaf', 'leaf']
        assert [frame.depth for frame in concrete_path] == [0, 1, 2]
        assert [frame.cycle for frame in concrete_path] == [0, 1, 2]
        assert [frame.satisfied for frame in concrete_path] == [True, True, True]
        assert [frame.var_state for frame in concrete_path] == [
            {'counter': 2},
            {'counter': 2},
            {'counter': 2},
        ]
        assert [frame.events for frame in concrete_path] == [[], [], []]

        assert concrete_path[0].prev_frame is None
        assert concrete_path[1].prev_frame is concrete_path[0]
        assert concrete_path[2].prev_frame is concrete_path[1]

        assert concrete_path[0].prev_cycle_frame is None
        assert concrete_path[1].prev_cycle_frame is concrete_path[0]
        assert concrete_path[2].prev_cycle_frame is concrete_path[1]

        assert concrete_path[2].get_history() == concrete_path
        assert concrete_path[2].get_history(cycle_only=True) == concrete_path

    def test_reports_unreachable_target_without_witness_details(self):
        state_machine = build_state_machine(SIMPLE_REACHABILITY_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=('Root.Idle', 'counter == 0'),
            target_state='Root.Ready',
            max_cycle=1,
        )

        assert isinstance(result, ReachabilityResult)
        assert result.reachable is False
        assert result.target_frame is None
        assert result.concrete_path is None
        assert result.solution is None
        assert isinstance(result.search_context, StateSearchContext)
        assert ('Root.Idle', 'leaf') in result.search_context.spaces
        assert ('Root.Ready', 'leaf') in result.search_context.spaces
        ready_frames = result.search_context.spaces[('Root.Ready', 'leaf')].frames
        assert len(ready_frames) == 1
        assert ready_frames[0].solve(max_solutions=1).status == 'unsat'

    def test_supports_multi_init_reachability_queries(self):
        state_machine = build_state_machine(SIMPLE_REACHABILITY_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=[
                ('Root.Idle', 'counter == 0'),
                ('Root.Idle', 'counter >= 1'),
            ],
            target_state='Root.Ready',
            max_cycle=1,
        )

        assert result.reachable is True
        assert result.target_frame is not None
        assert result.concrete_path is not None
        assert result.solution is not None
        assert result.concrete_path[-1].state.path == ('Root', 'Ready')
        assert result.solution['counter'] >= 1
