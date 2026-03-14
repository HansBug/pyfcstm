import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime
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

WATER_HEATER_DSL = '''
def int water_temp = 55;
def int draw_count = 0;
state Root {
    state Standby {
        during {
            water_temp = water_temp - 1;
        }
    }

    state Heating {
        during {
            water_temp = water_temp + 4;
        }
    }

    [*] -> Standby;
    Standby -> Heating : if [water_temp <= 50];
    Standby -> Standby :: HotWaterDraw effect {
        water_temp = water_temp - 8;
        draw_count = draw_count + 1;
    };
    Heating -> Standby : if [water_temp >= 60];
    Heating -> Heating :: HotWaterDraw effect {
        water_temp = water_temp - 8;
        draw_count = draw_count + 1;
    };
}
'''

WATER_HEATER_EVENTFUL_DSL = '''
def int water_temp = 55;
def int draw_count = 0;
state Root {
    state Standby {
        during {
            water_temp = water_temp - 1;
        }
    }

    state Drawn {
        during {
            water_temp = water_temp - 1;
        }
    }

    state Heating {
        during {
            water_temp = water_temp + 4;
        }
    }

    [*] -> Standby;
    Standby -> Heating : if [water_temp <= 50];
    Standby -> Drawn :: HotWaterDraw effect {
        water_temp = water_temp - 8;
        draw_count = draw_count + 1;
    };
    Drawn -> Heating : if [water_temp <= 50];
    Drawn -> Standby : if [water_temp > 50];
    Heating -> Standby : if [water_temp >= 60];
    Heating -> Drawn :: HotWaterDraw effect {
        water_temp = water_temp - 8;
        draw_count = draw_count + 1;
    };
}
'''

COMPACT_COMPLEX_REACHABILITY_DSL = '''
def int charge = 0;
def int proof = 0;

state Root {
    event Seal;

    state Idle {
        enter {
            proof = 0;
        }
        exit {
            charge = charge + 1;
        }
    }

    state Warm {
        enter {
            proof = proof + 1;
        }
        during {
            charge = charge + 2;
        }
        exit {
            proof = proof + 1;
        }
    }

    state Balance {
        enter {
            charge = charge - 1;
        }
        during {
            proof = proof + 2;
        }
        exit {
            charge = charge + 1;
        }
    }

    state Arm {
        enter {
            proof = proof + 1;
        }
        during {
            charge = charge + 1;
        }
        exit {
            proof = proof + 2;
        }
    }

    state Verify {
        enter {
            charge = charge - 1;
        }
        during {
            proof = proof + 1;
        }
        exit {
            charge = charge + 1;
        }
    }

    state Vault {
        enter {
            proof = proof + 1;
        }
    }

    [*] -> Idle;

    Idle -> Warm :: Wake;

    Warm -> Idle : if [charge < 3 || proof < 1];
    Warm -> Balance : if [charge >= 3 && proof >= 1];

    Balance -> Idle : if [charge < 3 || proof < 4];
    Balance -> Arm : /Seal;

    Arm -> Warm : if [charge < 4 || proof < 5];
    Arm -> Verify : if [charge >= 4 && proof >= 5];

    Verify -> Balance : if [charge < 4 || proof < 8];
    Verify -> Vault :: Launch;
}
'''

NESTED_BOUNDARY_REACHABILITY_DSL = '''
def int token = 0;
state Root {
    state Launch;

    state Session {
        enter {
            token = token + 1;
        }
        during before {
            token = token + 10;
        }
        during after {
            token = token + 100;
        }
        exit {
            token = token + 1000;
        }

        state Gate {
            enter {
                token = token + 20;
            }
            during before {
                token = token + 200;
            }
            during after {
                token = token + 2000;
            }
            exit {
                token = token + 20000;
            }

            state Leaf {
                enter {
                    token = token + 30;
                }
            }

            [*] -> Leaf;
            Leaf -> [*];
        }

        [*] -> Gate;
        Gate -> [*];
    }

    state Done;

    [*] -> Launch;
    Launch -> Session;
    Session -> Done;
}
'''

UNCONDITIONAL_FALLBACK_REACHABILITY_DSL = '''
def int selector = 0;
state Root {
    state Idle;
    state Fast;
    state Slow;
    [*] -> Idle;
    Idle -> Fast : if [selector >= 1];
    Idle -> Slow;
}
'''


def build_state_machine(dsl_code: str = SIMPLE_REACHABILITY_DSL):
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


def assert_runtime_matches_cycle_only_concrete_path(
        state_machine,
        concrete_path,
):
    assert concrete_path is not None, 'runtime replay requires a non-empty concrete path result'
    assert len(concrete_path) >= 1, (
        f'runtime replay requires at least one concrete frame, got {len(concrete_path)!r}'
    )

    cycle_only_path = concrete_path[-1].get_history(cycle_only=True)
    initial_frame = cycle_only_path[0]
    runtime = SimulationRuntime(
        state_machine,
        initial_state=initial_frame.state.path,
        initial_vars=initial_frame.var_state,
    )

    assert runtime.current_state.path == initial_frame.state.path, (
        f'runtime replay initial hot-start state mismatch: '
        f'expected {initial_frame.state.path!r}, got {runtime.current_state.path!r}'
    )
    assert runtime.vars == initial_frame.var_state, (
        f'runtime replay initial variables mismatch: '
        f'expected {initial_frame.var_state!r}, got {runtime.vars!r}'
    )

    for current_frame, next_frame in zip(cycle_only_path, cycle_only_path[1:]):
        runtime.cycle(current_frame.events)
        assert runtime.current_state.path == next_frame.state.path, (
            f'runtime replay state mismatch after events {current_frame.events!r} '
            f'when advancing to cycle {next_frame.cycle}: '
            f'expected {next_frame.state.path!r}, got {runtime.current_state.path!r}'
        )
        assert runtime.vars == next_frame.var_state, (
            f'runtime replay variable mismatch after events {current_frame.events!r} '
            f'when advancing to cycle {next_frame.cycle}: '
            f'expected {next_frame.var_state!r}, got {runtime.vars!r}'
        )


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

        assert isinstance(result, ReachabilityResult), (
            f'reachable query should return ReachabilityResult, got {type(result)!r}'
        )
        assert result.reachable is True, f'reachable target should be reported as reachable, got {result.reachable!r}'

        assert isinstance(result.search_context, StateSearchContext), (
            f'search context should be StateSearchContext, got {type(result.search_context)!r}'
        )
        assert ('Root.Idle', 'leaf') in result.search_context.spaces, (
            f"search space should contain ('Root.Idle', 'leaf'), available={list(result.search_context.spaces)!r}"
        )
        assert ('Root.Warmup', 'leaf') in result.search_context.spaces, (
            f"search space should contain ('Root.Warmup', 'leaf'), available={list(result.search_context.spaces)!r}"
        )
        assert ('Root.Ready', 'leaf') in result.search_context.spaces, (
            f"search space should contain ('Root.Ready', 'leaf'), available={list(result.search_context.spaces)!r}"
        )

        assert isinstance(result.target_frame, SearchFrame), (
            f'reachable target should expose SearchFrame, got {type(result.target_frame)!r}'
        )
        assert result.target_frame is result.search_context.spaces[('Root.Ready', 'leaf')].frames[0], (
            'target frame should point at the retained Root.Ready search frame'
        )
        assert result.target_frame.state.path == ('Root', 'Ready'), (
            f"target frame should end at ('Root', 'Ready'), got {result.target_frame.state.path!r}"
        )
        assert result.target_frame.type == 'leaf', f"target frame type should be 'leaf', got {result.target_frame.type!r}"
        assert result.target_frame.depth == 2, f'target frame depth should be 2, got {result.target_frame.depth!r}'
        assert result.target_frame.cycle == 2, f'target frame cycle should be 2, got {result.target_frame.cycle!r}'
        assert result.target_frame.event_var is None, (
            f'guard-only witness should not attach an event variable, got {result.target_frame.event_var!r}'
        )
        assert result.target_frame.event_cycle is None, (
            f'guard-only witness should not report an event cycle, got {result.target_frame.event_cycle!r}'
        )
        assert result.target_frame.event_path_name is None, (
            f'guard-only witness should not report an event path, got {result.target_frame.event_path_name!r}'
        )

        symbolic_history = result.target_frame.get_history()
        assert [frame.state.path for frame in symbolic_history] == [
            ('Root', 'Idle'),
            ('Root', 'Warmup'),
            ('Root', 'Ready'),
        ], f'symbolic history should follow Idle -> Warmup -> Ready, got {[frame.state.path for frame in symbolic_history]!r}'
        assert [frame.depth for frame in symbolic_history] == [0, 1, 2], (
            f'symbolic history depths should be [0, 1, 2], got {[frame.depth for frame in symbolic_history]!r}'
        )
        assert [frame.cycle for frame in symbolic_history] == [0, 1, 2], (
            f'symbolic history cycles should be [0, 1, 2], got {[frame.cycle for frame in symbolic_history]!r}'
        )
        assert all(frame.type == 'leaf' for frame in symbolic_history), (
            f"all symbolic history frames should be 'leaf', got {[frame.type for frame in symbolic_history]!r}"
        )
        assert symbolic_history[0].prev_frame is None, 'first symbolic history frame should not have a predecessor'
        assert symbolic_history[1].prev_frame is symbolic_history[0], (
            'second symbolic history frame should link to the first'
        )
        assert symbolic_history[2].prev_frame is symbolic_history[1], (
            'third symbolic history frame should link to the second'
        )

        assert result.solution is not None, 'reachable query should provide a solver solution'
        assert result.solution == {'counter': 2}, (
            f"solver solution should be {{'counter': 2}}, got {result.solution!r}"
        )

        assert isinstance(result.concrete_path, list), (
            f'reachable query should provide a concrete witness list, got {type(result.concrete_path)!r}'
        )
        assert len(result.concrete_path) == 3, (
            f'concrete witness should contain exactly three frames, got {len(result.concrete_path)!r}'
        )
        assert all(isinstance(frame, SearchConcreteFrame) for frame in result.concrete_path), (
            f'all concrete witness entries should be SearchConcreteFrame, got {[type(frame).__name__ for frame in result.concrete_path]!r}'
        )

        concrete_path = result.concrete_path
        assert [frame.state.path for frame in concrete_path] == [
            ('Root', 'Idle'),
            ('Root', 'Warmup'),
            ('Root', 'Ready'),
        ], f'concrete witness should follow Idle -> Warmup -> Ready, got {[frame.state.path for frame in concrete_path]!r}'
        assert [frame.type for frame in concrete_path] == ['leaf', 'leaf', 'leaf'], (
            f"concrete witness frame types should all be 'leaf', got {[frame.type for frame in concrete_path]!r}"
        )
        assert [frame.depth for frame in concrete_path] == [0, 1, 2], (
            f'concrete witness depths should be [0, 1, 2], got {[frame.depth for frame in concrete_path]!r}'
        )
        assert [frame.cycle for frame in concrete_path] == [0, 1, 2], (
            f'concrete witness cycles should be [0, 1, 2], got {[frame.cycle for frame in concrete_path]!r}'
        )
        assert [frame.satisfied for frame in concrete_path] == [True, True, True], (
            f'concrete witness satisfaction flags should all be True, got {[frame.satisfied for frame in concrete_path]!r}'
        )
        assert [frame.var_state for frame in concrete_path] == [
            {'counter': 2},
            {'counter': 2},
            {'counter': 2},
        ], f"concrete witness variables should keep counter fixed at 2, got {[frame.var_state for frame in concrete_path]!r}"
        assert [frame.events for frame in concrete_path] == [[], [], []], (
            f'guard-only witness should not emit any events, got {[frame.events for frame in concrete_path]!r}'
        )

        assert concrete_path[0].prev_frame is None, 'first concrete frame should not have a predecessor'
        assert concrete_path[1].prev_frame is concrete_path[0], 'second concrete frame should link to the first'
        assert concrete_path[2].prev_frame is concrete_path[1], 'third concrete frame should link to the second'

        assert concrete_path[0].prev_cycle_frame is None, 'first concrete frame should not have a previous cycle frame'
        assert concrete_path[1].prev_cycle_frame is concrete_path[0], 'second concrete frame should link to the first cycle frame'
        assert concrete_path[2].prev_cycle_frame is concrete_path[1], 'third concrete frame should link to the second cycle frame'

        assert concrete_path[2].get_history() == concrete_path, 'full concrete history should reconstruct the entire path'
        assert concrete_path[2].get_history(cycle_only=True) == concrete_path, (
            'cycle-only concrete history should equal the full path for one-frame-per-cycle witnesses'
        )
        assert_runtime_matches_cycle_only_concrete_path(state_machine, concrete_path)

    def test_reports_unreachable_target_without_witness_details(self):
        state_machine = build_state_machine(SIMPLE_REACHABILITY_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=('Root.Idle', 'counter == 0'),
            target_state='Root.Ready',
            max_cycle=1,
        )

        assert isinstance(result, ReachabilityResult), (
            f'unreachable query should still return ReachabilityResult, got {type(result)!r}'
        )
        assert result.reachable is False, f'unreachable target should be reported as unreachable, got {result.reachable!r}'
        assert result.target_frame is None, f'unreachable query should not expose a target frame, got {result.target_frame!r}'
        assert result.concrete_path is None, f'unreachable query should not expose a concrete path, got {result.concrete_path!r}'
        assert result.solution is None, f'unreachable query should not expose a solver solution, got {result.solution!r}'
        assert isinstance(result.search_context, StateSearchContext), (
            f'unreachable query should still expose StateSearchContext, got {type(result.search_context)!r}'
        )
        assert ('Root.Idle', 'leaf') in result.search_context.spaces, (
            f"unreachable search should retain ('Root.Idle', 'leaf'), available={list(result.search_context.spaces)!r}"
        )
        assert ('Root.Ready', 'leaf') in result.search_context.spaces, (
            f"unreachable search should retain ('Root.Ready', 'leaf'), available={list(result.search_context.spaces)!r}"
        )
        ready_frames = result.search_context.spaces[('Root.Ready', 'leaf')].frames
        assert len(ready_frames) == 1, (
            f'unreachable target space should retain exactly one symbolic frame, got {len(ready_frames)!r}'
        )
        assert ready_frames[0].solve(max_solutions=1).status == 'unsat', (
            f"retained Root.Ready frame should be unsat, got {ready_frames[0].solve(max_solutions=1).status!r}"
        )

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

        assert result.reachable is True, f'multi-init query should find a reachable branch, got {result.reachable!r}'
        assert result.target_frame is not None, 'multi-init reachable query should expose a target frame'
        assert result.concrete_path is not None, 'multi-init reachable query should expose a concrete witness path'
        assert result.solution is not None, 'multi-init reachable query should expose a solver solution'
        assert result.concrete_path[-1].state.path == ('Root', 'Ready'), (
            f"multi-init witness should end at ('Root', 'Ready'), got {result.concrete_path[-1].state.path!r}"
        )
        assert result.solution['counter'] >= 1, (
            f"multi-init witness should choose counter >= 1, got solution {result.solution!r}"
        )
        assert_runtime_matches_cycle_only_concrete_path(state_machine, result.concrete_path)

    def test_water_heater_standby_at_threshold_can_reach_heating(self):
        state_machine = build_state_machine(WATER_HEATER_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=(
                'Root.Standby',
                'water_temp == 50 && draw_count == 0',
            ),
            target_state='Root.Heating',
            max_cycle=2,
        )

        assert result.reachable is True, f'heating threshold case should be reachable, got {result.reachable!r}'
        assert result.solution == {'draw_count': 0, 'water_temp': 50}, (
            f"heating threshold case should solve to {{'draw_count': 0, 'water_temp': 50}}, got {result.solution!r}"
        )
        assert result.target_frame is not None, 'heating threshold case should expose a target frame'
        assert result.target_frame.state.path == ('Root', 'Heating'), (
            f"heating threshold case should end at ('Root', 'Heating'), got {result.target_frame.state.path!r}"
        )
        assert result.target_frame.depth == 1, f'heating threshold witness depth should be 1, got {result.target_frame.depth!r}'
        assert result.target_frame.cycle == 1, f'heating threshold witness cycle should be 1, got {result.target_frame.cycle!r}'
        assert result.concrete_path is not None, 'heating threshold case should expose a concrete witness path'
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Standby'),
            ('Root', 'Heating'),
        ], f'heating threshold path should be Standby -> Heating, got {[frame.state.path for frame in result.concrete_path]!r}'
        assert [frame.var_state for frame in result.concrete_path] == [
            {
                'water_temp': 50,
                'draw_count': 0,
            },
            {
                'water_temp': 54,
                'draw_count': 0,
            },
        ], f'heating threshold variable trace mismatch, got {[frame.var_state for frame in result.concrete_path]!r}'
        assert [frame.events for frame in result.concrete_path] == [[], []], (
            f'heating threshold case should not require events, got {[frame.events for frame in result.concrete_path]!r}'
        )
        assert [frame.cycle for frame in result.concrete_path] == [0, 1], (
            f'heating threshold cycle trace should be [0, 1], got {[frame.cycle for frame in result.concrete_path]!r}'
        )
        assert [frame.depth for frame in result.concrete_path] == [0, 1], (
            f'heating threshold depth trace should be [0, 1], got {[frame.depth for frame in result.concrete_path]!r}'
        )
        assert result.concrete_path[1].prev_frame is result.concrete_path[0], (
            'heating threshold concrete frame 1 should link back to frame 0'
        )
        assert result.concrete_path[1].prev_cycle_frame is result.concrete_path[0], (
            'heating threshold concrete frame 1 should link back to previous cycle frame 0'
        )
        assert_runtime_matches_cycle_only_concrete_path(state_machine, result.concrete_path)

    def test_water_heater_heating_at_upper_bound_can_return_to_standby(self):
        state_machine = build_state_machine(WATER_HEATER_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=(
                'Root.Heating',
                'water_temp == 60 && draw_count == 1',
            ),
            target_state='Root.Standby',
            max_cycle=2,
        )

        assert result.reachable is True, f'heating upper-bound return case should be reachable, got {result.reachable!r}'
        assert result.solution == {'draw_count': 1, 'water_temp': 60}, (
            f"heating upper-bound return case should solve to {{'draw_count': 1, 'water_temp': 60}}, got {result.solution!r}"
        )
        assert result.target_frame is not None, 'heating upper-bound return case should expose a target frame'
        assert result.target_frame.state.path == ('Root', 'Standby'), (
            f"heating upper-bound return case should end at ('Root', 'Standby'), got {result.target_frame.state.path!r}"
        )
        assert result.concrete_path is not None, 'heating upper-bound return case should expose a concrete witness path'
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Heating'),
            ('Root', 'Standby'),
        ], f'heating upper-bound return path should be Heating -> Standby, got {[frame.state.path for frame in result.concrete_path]!r}'
        assert [frame.var_state for frame in result.concrete_path] == [
            {
                'water_temp': 60,
                'draw_count': 1,
            },
            {
                'water_temp': 59,
                'draw_count': 1,
            },
        ], f'heating upper-bound return variable trace mismatch, got {[frame.var_state for frame in result.concrete_path]!r}'
        assert [frame.events for frame in result.concrete_path] == [[], []], (
            f'heating upper-bound return case should not require events, got {[frame.events for frame in result.concrete_path]!r}'
        )
        assert result.concrete_path[-1].get_history() == result.concrete_path, (
            'heating upper-bound return full history should reconstruct the concrete path'
        )
        assert_runtime_matches_cycle_only_concrete_path(state_machine, result.concrete_path)

    def test_water_heater_standby_above_threshold_cannot_reach_heating(self):
        state_machine = build_state_machine(WATER_HEATER_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=(
                'Root.Standby',
                'water_temp == 51 && draw_count == 0',
            ),
            target_state='Root.Heating',
            max_cycle=2,
        )

        assert result.reachable is False, f'above-threshold standby case should be unreachable, got {result.reachable!r}'
        assert result.target_frame is None, f'above-threshold standby case should not expose a target frame, got {result.target_frame!r}'
        assert result.concrete_path is None, f'above-threshold standby case should not expose a concrete path, got {result.concrete_path!r}'
        assert result.solution is None, f'above-threshold standby case should not expose a solver solution, got {result.solution!r}'

    def test_water_heater_multi_init_can_find_threshold_start_for_heating(self):
        state_machine = build_state_machine(WATER_HEATER_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=[
                ('Root.Standby', 'water_temp == 51 && draw_count == 0'),
                ('Root.Standby', 'water_temp == 50 && draw_count == 0'),
            ],
            target_state='Root.Heating',
            max_cycle=2,
        )

        assert result.reachable is True, f'multi-init water heater case should be reachable, got {result.reachable!r}'
        assert result.solution == {'draw_count': 0, 'water_temp': 50}, (
            f"multi-init water heater case should solve to {{'draw_count': 0, 'water_temp': 50}}, got {result.solution!r}"
        )
        assert result.target_frame is not None, 'multi-init water heater case should expose a target frame'
        assert result.target_frame.state.path == ('Root', 'Heating'), (
            f"multi-init water heater case should end at ('Root', 'Heating'), got {result.target_frame.state.path!r}"
        )
        assert result.concrete_path is not None, 'multi-init water heater case should expose a concrete witness path'
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Standby'),
            ('Root', 'Heating'),
        ], f'multi-init water heater path should be Standby -> Heating, got {[frame.state.path for frame in result.concrete_path]!r}'
        assert_runtime_matches_cycle_only_concrete_path(state_machine, result.concrete_path)

    def test_water_heater_event_variant_can_reach_drawn_via_hot_water_draw(self):
        state_machine = build_state_machine(WATER_HEATER_EVENTFUL_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=('Root.Standby', 'water_temp == 54 && draw_count == 0'),
            target_state='Root.Drawn',
            max_cycle=2,
        )

        assert result.reachable is True, f'eventful draw case should be reachable, got {result.reachable!r}'
        assert result.solution is not None, 'eventful draw case should expose a solver solution'
        assert result.solution['draw_count'] == 0, f"eventful draw solution should keep draw_count at 0, got {result.solution!r}"
        assert result.solution['water_temp'] == 54, f"eventful draw solution should start from water_temp 54, got {result.solution!r}"
        assert result.solution['_E_C0__Root.Standby.HotWaterDraw'] is True, (
            f"eventful draw solution should trigger Root.Standby.HotWaterDraw at cycle 0, got {result.solution!r}"
        )
        assert result.target_frame is not None, 'eventful draw case should expose a target frame'
        assert result.target_frame.state.path == ('Root', 'Drawn'), (
            f"eventful draw case should end at ('Root', 'Drawn'), got {result.target_frame.state.path!r}"
        )
        assert result.target_frame.depth == 1, f'eventful draw witness depth should be 1, got {result.target_frame.depth!r}'
        assert result.target_frame.cycle == 1, f'eventful draw witness cycle should be 1, got {result.target_frame.cycle!r}'
        assert result.target_frame.event_var is not None, 'eventful draw witness should expose an event variable'
        assert result.target_frame.event_cycle == 0, f'eventful draw witness event cycle should be 0, got {result.target_frame.event_cycle!r}'
        assert result.target_frame.event_path_name == 'Root.Standby.HotWaterDraw', (
            f"eventful draw witness event path should be 'Root.Standby.HotWaterDraw', got {result.target_frame.event_path_name!r}"
        )
        assert result.concrete_path is not None, 'eventful draw case should expose a concrete witness path'
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Standby'),
            ('Root', 'Drawn'),
        ], f'eventful draw path should be Standby -> Drawn, got {[frame.state.path for frame in result.concrete_path]!r}'
        assert [frame.events for frame in result.concrete_path] == [
            ['Root.Standby.HotWaterDraw'],
            [],
        ], f'eventful draw event trace mismatch, got {[frame.events for frame in result.concrete_path]!r}'
        assert [frame.var_state for frame in result.concrete_path] == [
            {'water_temp': 54, 'draw_count': 0},
            {'water_temp': 45, 'draw_count': 1},
        ], f'eventful draw variable trace mismatch, got {[frame.var_state for frame in result.concrete_path]!r}'
        assert_runtime_matches_cycle_only_concrete_path(state_machine, result.concrete_path)

    def test_water_heater_event_variant_can_reach_heating_after_draw_event(self):
        state_machine = build_state_machine(WATER_HEATER_EVENTFUL_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=('Root.Standby', 'water_temp == 54 && draw_count == 0'),
            target_state='Root.Heating',
            max_cycle=3,
        )

        assert result.reachable is True, f'eventful draw-to-heating case should be reachable, got {result.reachable!r}'
        assert result.solution is not None, 'eventful draw-to-heating case should expose a solver solution'
        assert result.solution['draw_count'] == 0, (
            f"eventful draw-to-heating solution should keep draw_count at 0, got {result.solution!r}"
        )
        assert result.solution['water_temp'] == 54, (
            f"eventful draw-to-heating solution should start from water_temp 54, got {result.solution!r}"
        )
        assert result.solution['_E_C0__Root.Standby.HotWaterDraw'] is True, (
            f"eventful draw-to-heating solution should trigger Root.Standby.HotWaterDraw at cycle 0, got {result.solution!r}"
        )
        assert result.target_frame is not None, 'eventful draw-to-heating case should expose a target frame'
        assert result.target_frame.state.path == ('Root', 'Heating'), (
            f"eventful draw-to-heating case should end at ('Root', 'Heating'), got {result.target_frame.state.path!r}"
        )
        assert result.target_frame.depth == 2, f'eventful draw-to-heating witness depth should be 2, got {result.target_frame.depth!r}'
        assert result.target_frame.cycle == 2, f'eventful draw-to-heating witness cycle should be 2, got {result.target_frame.cycle!r}'
        assert result.concrete_path is not None, 'eventful draw-to-heating case should expose a concrete witness path'
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Standby'),
            ('Root', 'Drawn'),
            ('Root', 'Heating'),
        ], f'eventful draw-to-heating path mismatch, got {[frame.state.path for frame in result.concrete_path]!r}'
        assert [frame.cycle for frame in result.concrete_path] == [0, 1, 2], (
            f'eventful draw-to-heating cycle trace should be [0, 1, 2], got {[frame.cycle for frame in result.concrete_path]!r}'
        )
        assert [frame.events for frame in result.concrete_path] == [
            ['Root.Standby.HotWaterDraw'],
            [],
            [],
        ], f'eventful draw-to-heating event trace mismatch, got {[frame.events for frame in result.concrete_path]!r}'
        assert [frame.var_state for frame in result.concrete_path] == [
            {'water_temp': 54, 'draw_count': 0},
            {'water_temp': 45, 'draw_count': 1},
            {'water_temp': 49, 'draw_count': 1},
        ], f'eventful draw-to-heating variable trace mismatch, got {[frame.var_state for frame in result.concrete_path]!r}'
        assert result.concrete_path[1].prev_frame is result.concrete_path[0], (
            'eventful draw-to-heating frame 1 should link to frame 0'
        )
        assert result.concrete_path[2].prev_frame is result.concrete_path[1], (
            'eventful draw-to-heating frame 2 should link to frame 1'
        )
        assert result.concrete_path[2].prev_cycle_frame is result.concrete_path[1], (
            'eventful draw-to-heating frame 2 should link to previous cycle frame 1'
        )
        assert_runtime_matches_cycle_only_concrete_path(state_machine, result.concrete_path)

    def test_compact_complex_machine_can_reach_vault_from_relaxed_window(self):
        state_machine = build_state_machine(COMPACT_COMPLEX_REACHABILITY_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=(
                'Root.Idle',
                'charge >= 0 && charge <= 1 && proof == 0',
            ),
            target_state='Root.Vault',
            max_cycle=5,
        )

        assert result.reachable is True, f'compact complex case should be reachable, got {result.reachable!r}'
        assert result.target_frame is not None, 'compact complex case should expose a target frame'
        assert result.target_frame.state.path == ('Root', 'Vault'), (
            f"compact complex case should end at ('Root', 'Vault'), got {result.target_frame.state.path!r}"
        )
        assert result.target_frame.depth == 5, f'compact complex witness depth should be 5, got {result.target_frame.depth!r}'
        assert result.target_frame.cycle == 5, f'compact complex witness cycle should be 5, got {result.target_frame.cycle!r}'

        assert result.solution is not None, 'compact complex case should expose a solver solution'
        assert result.solution['charge'] == 1, f"compact complex initial charge should be 1, got {result.solution!r}"
        assert result.solution['proof'] == 0, f"compact complex initial proof should be 0, got {result.solution!r}"
        assert result.solution['_E_C0__Root.Idle.Wake'] is True, (
            f"compact complex case should trigger Root.Idle.Wake at cycle 0, got {result.solution!r}"
        )
        assert result.solution['_E_C2__Root.Seal'] is True, (
            f"compact complex case should trigger Root.Seal at cycle 2, got {result.solution!r}"
        )
        assert result.solution['_E_C4__Root.Verify.Launch'] is True, (
            f"compact complex case should trigger Root.Verify.Launch at cycle 4, got {result.solution!r}"
        )

        assert result.concrete_path is not None, 'compact complex case should expose a concrete witness path'
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Idle'),
            ('Root', 'Warm'),
            ('Root', 'Balance'),
            ('Root', 'Arm'),
            ('Root', 'Verify'),
            ('Root', 'Vault'),
        ], f'compact complex path mismatch, got {[frame.state.path for frame in result.concrete_path]!r}'
        assert [frame.cycle for frame in result.concrete_path] == [0, 1, 2, 3, 4, 5], (
            f'compact complex cycle trace should be [0, 1, 2, 3, 4, 5], got {[frame.cycle for frame in result.concrete_path]!r}'
        )
        assert [frame.events for frame in result.concrete_path] == [
            ['Root.Idle.Wake'],
            [],
            ['Root.Seal'],
            [],
            ['Root.Verify.Launch'],
            [],
        ], f'compact complex event trace mismatch, got {[frame.events for frame in result.concrete_path]!r}'
        assert [frame.var_state for frame in result.concrete_path] == [
            {
                'charge': 1,
                'proof': 0,
            },
            {
                'charge': 4,
                'proof': 1,
            },
            {
                'charge': 3,
                'proof': 4,
            },
            {
                'charge': 5,
                'proof': 5,
            },
            {
                'charge': 4,
                'proof': 8,
            },
            {
                'charge': 5,
                'proof': 9,
            },
        ], f'compact complex variable trace mismatch, got {[frame.var_state for frame in result.concrete_path]!r}'
        assert result.concrete_path[-1].get_history() == result.concrete_path, (
            'compact complex full history should reconstruct the concrete path'
        )
        assert result.concrete_path[-1].get_history(cycle_only=True) == result.concrete_path, (
            'compact complex cycle-only history should equal the concrete path'
        )
        assert_runtime_matches_cycle_only_concrete_path(state_machine, result.concrete_path)

    def test_compact_complex_machine_cannot_reach_vault_with_tight_cycle_budget(self):
        state_machine = build_state_machine(COMPACT_COMPLEX_REACHABILITY_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=(
                'Root.Idle',
                'charge >= 0 && charge <= 1 && proof == 0',
            ),
            target_state='Root.Vault',
            max_cycle=4,
        )

        assert result.reachable is False, f'compact complex tight-budget case should be unreachable, got {result.reachable!r}'
        assert result.target_frame is None, f'compact complex tight-budget case should not expose a target frame, got {result.target_frame!r}'
        assert result.concrete_path is None, f'compact complex tight-budget case should not expose a concrete path, got {result.concrete_path!r}'
        assert result.solution is None, f'compact complex tight-budget case should not expose a solver solution, got {result.solution!r}'

    def test_nested_composite_boundaries_produce_full_witness_and_runtime_replay(self):
        state_machine = build_state_machine(NESTED_BOUNDARY_REACHABILITY_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=('Root.Launch', 'token == 0'),
            target_state=state_machine.resolve_state('Root.Done'),
            max_cycle=10,
        )

        assert result.reachable is True, f'nested composite boundary case should be reachable, got {result.reachable!r}'
        assert result.solution == {'token': 0}, (
            f"nested composite boundary case should solve to {{'token': 0}}, got {result.solution!r}"
        )
        assert result.target_frame is not None, 'nested composite boundary case should expose a target frame'
        assert result.target_frame.state.path == ('Root', 'Done'), (
            f"nested composite boundary case should end at ('Root', 'Done'), got {result.target_frame.state.path!r}"
        )
        assert result.target_frame.type == 'leaf', (
            f"nested composite boundary target frame type should be 'leaf', got {result.target_frame.type!r}"
        )
        assert result.target_frame.depth == 6, (
            f'nested composite boundary target depth should be 6, got {result.target_frame.depth!r}'
        )
        assert result.target_frame.cycle == 2, (
            f'nested composite boundary target cycle should be 2, got {result.target_frame.cycle!r}'
        )
        assert result.concrete_path is not None, 'nested composite boundary case should expose a concrete witness path'
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Launch'),
            ('Root', 'Session'),
            ('Root', 'Session', 'Gate'),
            ('Root', 'Session', 'Gate', 'Leaf'),
            ('Root', 'Session', 'Gate'),
            ('Root', 'Session'),
            ('Root', 'Done'),
        ], f'nested composite boundary path mismatch, got {[frame.state.path for frame in result.concrete_path]!r}'
        assert [frame.type for frame in result.concrete_path] == [
            'leaf',
            'composite_in',
            'composite_in',
            'leaf',
            'composite_out',
            'composite_out',
            'leaf',
        ], f'nested composite boundary frame types mismatch, got {[frame.type for frame in result.concrete_path]!r}'
        assert [frame.cycle for frame in result.concrete_path] == [0, 0, 0, 1, 1, 1, 2], (
            f'nested composite boundary cycle trace mismatch, got {[frame.cycle for frame in result.concrete_path]!r}'
        )
        assert [frame.depth for frame in result.concrete_path] == [0, 1, 2, 3, 4, 5, 6], (
            f'nested composite boundary depth trace mismatch, got {[frame.depth for frame in result.concrete_path]!r}'
        )
        assert [frame.var_state for frame in result.concrete_path] == [
            {'token': 0},
            {'token': 1},
            {'token': 31},
            {'token': 261},
            {'token': 2261},
            {'token': 22361},
            {'token': 23361},
        ], f'nested composite boundary variable trace mismatch, got {[frame.var_state for frame in result.concrete_path]!r}'
        assert [frame.events for frame in result.concrete_path] == [[], [], [], [], [], [], []], (
            f'nested composite boundary case should not require events, got {[frame.events for frame in result.concrete_path]!r}'
        )
        assert result.concrete_path[-1].get_history() == result.concrete_path, (
            'nested composite boundary full history should reconstruct the concrete path'
        )
        assert ('Root.Session', 'composite_in') in result.search_context.spaces, (
            f"nested composite boundary search should retain ('Root.Session', 'composite_in'), "
            f"available={list(result.search_context.spaces)!r}"
        )
        assert ('Root.Session.Gate', 'composite_in') in result.search_context.spaces, (
            f"nested composite boundary search should retain ('Root.Session.Gate', 'composite_in'), "
            f"available={list(result.search_context.spaces)!r}"
        )
        assert ('Root.Session.Gate', 'composite_out') in result.search_context.spaces, (
            f"nested composite boundary search should retain ('Root.Session.Gate', 'composite_out'), "
            f"available={list(result.search_context.spaces)!r}"
        )
        assert ('Root.Session', 'composite_out') in result.search_context.spaces, (
            f"nested composite boundary search should retain ('Root.Session', 'composite_out'), "
            f"available={list(result.search_context.spaces)!r}"
        )

        runtime = SimulationRuntime(
            state_machine,
            initial_state='Root.Launch',
            initial_vars={'token': 0},
        )
        runtime.cycle([])
        assert runtime.current_state.path == result.concrete_path[3].state.path, (
            f'nested composite boundary runtime state mismatch after first replay cycle: '
            f'expected {result.concrete_path[3].state.path!r}, got {runtime.current_state.path!r}'
        )
        assert runtime.vars == result.concrete_path[3].var_state, (
            f'nested composite boundary runtime variables mismatch after first replay cycle: '
            f'expected {result.concrete_path[3].var_state!r}, got {runtime.vars!r}'
        )
        runtime.cycle([])
        assert runtime.current_state.path == result.concrete_path[6].state.path, (
            f'nested composite boundary runtime state mismatch after second replay cycle: '
            f'expected {result.concrete_path[6].state.path!r}, got {runtime.current_state.path!r}'
        )
        assert runtime.vars == result.concrete_path[6].var_state, (
            f'nested composite boundary runtime variables mismatch after second replay cycle: '
            f'expected {result.concrete_path[6].var_state!r}, got {runtime.vars!r}'
        )

    def test_unconditional_fallback_branch_produces_sat_second_transition_witness(self):
        state_machine = build_state_machine(UNCONDITIONAL_FALLBACK_REACHABILITY_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=('Root.Idle', 'selector == 0'),
            target_state='Root.Slow',
            max_cycle=10,
        )

        assert result.reachable is True, f'unconditional fallback case should be reachable, got {result.reachable!r}'
        assert result.solution == {'selector': 0}, (
            f"unconditional fallback case should solve to {{'selector': 0}}, got {result.solution!r}"
        )
        assert result.target_frame is not None, 'unconditional fallback case should expose a target frame'
        assert result.target_frame.state.path == ('Root', 'Slow'), (
            f"unconditional fallback case should end at ('Root', 'Slow'), got {result.target_frame.state.path!r}"
        )
        assert result.target_frame.depth == 1, (
            f'unconditional fallback target depth should be 1, got {result.target_frame.depth!r}'
        )
        assert result.target_frame.cycle == 1, (
            f'unconditional fallback target cycle should be 1, got {result.target_frame.cycle!r}'
        )
        assert result.concrete_path is not None, 'unconditional fallback case should expose a concrete witness path'
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Idle'),
            ('Root', 'Slow'),
        ], f'unconditional fallback path mismatch, got {[frame.state.path for frame in result.concrete_path]!r}'
        assert [frame.var_state for frame in result.concrete_path] == [
            {'selector': 0},
            {'selector': 0},
        ], f'unconditional fallback variable trace mismatch, got {[frame.var_state for frame in result.concrete_path]!r}'
        assert [frame.events for frame in result.concrete_path] == [[], []], (
            f'unconditional fallback case should not require events, got {[frame.events for frame in result.concrete_path]!r}'
        )
        assert ('Root.Fast', 'leaf') in result.search_context.spaces, (
            f"unconditional fallback search should retain ('Root.Fast', 'leaf'), "
            f"available={list(result.search_context.spaces)!r}"
        )
        fast_frames = result.search_context.spaces[('Root.Fast', 'leaf')].frames
        assert len(fast_frames) == 1, (
            f'unconditional fallback search should retain exactly one Root.Fast frame, got {len(fast_frames)!r}'
        )
        assert fast_frames[0].solve(max_solutions=1).status == 'unsat', (
            f"unconditional fallback Root.Fast frame should be unsat, got {fast_frames[0].solve(max_solutions=1).status!r}"
        )
        assert_runtime_matches_cycle_only_concrete_path(state_machine, result.concrete_path)
