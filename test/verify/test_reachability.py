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

        assert result.reachable is True
        assert result.solution == {'draw_count': 0, 'water_temp': 50}
        assert result.target_frame is not None
        assert result.target_frame.state.path == ('Root', 'Heating')
        assert result.target_frame.depth == 1
        assert result.target_frame.cycle == 1
        assert result.concrete_path is not None
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Standby'),
            ('Root', 'Heating'),
        ]
        assert [frame.var_state for frame in result.concrete_path] == [
            {
                'water_temp': 50,
                'draw_count': 0,
            },
            {
                'water_temp': 54,
                'draw_count': 0,
            },
        ]
        assert [frame.events for frame in result.concrete_path] == [[], []]
        assert [frame.cycle for frame in result.concrete_path] == [0, 1]
        assert [frame.depth for frame in result.concrete_path] == [0, 1]
        assert result.concrete_path[1].prev_frame is result.concrete_path[0]
        assert result.concrete_path[1].prev_cycle_frame is result.concrete_path[0]

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

        assert result.reachable is True
        assert result.solution == {'draw_count': 1, 'water_temp': 60}
        assert result.target_frame is not None
        assert result.target_frame.state.path == ('Root', 'Standby')
        assert result.concrete_path is not None
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Heating'),
            ('Root', 'Standby'),
        ]
        assert [frame.var_state for frame in result.concrete_path] == [
            {
                'water_temp': 60,
                'draw_count': 1,
            },
            {
                'water_temp': 59,
                'draw_count': 1,
            },
        ]
        assert [frame.events for frame in result.concrete_path] == [[], []]
        assert result.concrete_path[-1].get_history() == result.concrete_path

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

        assert result.reachable is False
        assert result.target_frame is None
        assert result.concrete_path is None
        assert result.solution is None

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

        assert result.reachable is True
        assert result.solution == {'draw_count': 0, 'water_temp': 50}
        assert result.target_frame is not None
        assert result.target_frame.state.path == ('Root', 'Heating')
        assert result.concrete_path is not None
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Standby'),
            ('Root', 'Heating'),
        ]

    def test_water_heater_event_variant_can_reach_drawn_via_hot_water_draw(self):
        state_machine = build_state_machine(WATER_HEATER_EVENTFUL_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=('Root.Standby', 'water_temp == 54 && draw_count == 0'),
            target_state='Root.Drawn',
            max_cycle=2,
        )

        assert result.reachable is True
        assert result.solution is not None
        assert result.solution['draw_count'] == 0
        assert result.solution['water_temp'] == 54
        assert result.solution['_E_C0__Root.Standby.HotWaterDraw'] is True
        assert result.target_frame is not None
        assert result.target_frame.state.path == ('Root', 'Drawn')
        assert result.target_frame.depth == 1
        assert result.target_frame.cycle == 1
        assert result.target_frame.event_var is not None
        assert result.target_frame.event_cycle == 0
        assert result.target_frame.event_path_name == 'Root.Standby.HotWaterDraw'
        assert result.concrete_path is not None
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Standby'),
            ('Root', 'Drawn'),
        ]
        assert [frame.events for frame in result.concrete_path] == [
            ['Root.Standby.HotWaterDraw'],
            [],
        ]
        assert [frame.var_state for frame in result.concrete_path] == [
            {'water_temp': 54, 'draw_count': 0},
            {'water_temp': 45, 'draw_count': 1},
        ]

    def test_water_heater_event_variant_can_reach_heating_after_draw_event(self):
        state_machine = build_state_machine(WATER_HEATER_EVENTFUL_DSL)

        result = verify_reachability(
            state_machine=state_machine,
            init=('Root.Standby', 'water_temp == 54 && draw_count == 0'),
            target_state='Root.Heating',
            max_cycle=3,
        )

        assert result.reachable is True
        assert result.solution is not None
        assert result.solution['draw_count'] == 0
        assert result.solution['water_temp'] == 54
        assert result.solution['_E_C0__Root.Standby.HotWaterDraw'] is True
        assert result.target_frame is not None
        assert result.target_frame.state.path == ('Root', 'Heating')
        assert result.target_frame.depth == 2
        assert result.target_frame.cycle == 2
        assert result.concrete_path is not None
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Standby'),
            ('Root', 'Drawn'),
            ('Root', 'Heating'),
        ]
        assert [frame.cycle for frame in result.concrete_path] == [0, 1, 2]
        assert [frame.events for frame in result.concrete_path] == [
            ['Root.Standby.HotWaterDraw'],
            [],
            [],
        ]
        assert [frame.var_state for frame in result.concrete_path] == [
            {'water_temp': 54, 'draw_count': 0},
            {'water_temp': 45, 'draw_count': 1},
            {'water_temp': 49, 'draw_count': 1},
        ]
        assert result.concrete_path[1].prev_frame is result.concrete_path[0]
        assert result.concrete_path[2].prev_frame is result.concrete_path[1]
        assert result.concrete_path[2].prev_cycle_frame is result.concrete_path[1]

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

        assert result.reachable is True
        assert result.target_frame is not None
        assert result.target_frame.state.path == ('Root', 'Vault')
        assert result.target_frame.depth == 5
        assert result.target_frame.cycle == 5

        assert result.solution is not None
        assert result.solution['charge'] == 1
        assert result.solution['proof'] == 0
        assert result.solution['_E_C0__Root.Idle.Wake'] is True
        assert result.solution['_E_C2__Root.Seal'] is True
        assert result.solution['_E_C4__Root.Verify.Launch'] is True

        assert result.concrete_path is not None
        assert [frame.state.path for frame in result.concrete_path] == [
            ('Root', 'Idle'),
            ('Root', 'Warm'),
            ('Root', 'Balance'),
            ('Root', 'Arm'),
            ('Root', 'Verify'),
            ('Root', 'Vault'),
        ]
        assert [frame.cycle for frame in result.concrete_path] == [0, 1, 2, 3, 4, 5]
        assert [frame.events for frame in result.concrete_path] == [
            ['Root.Idle.Wake'],
            [],
            ['Root.Seal'],
            [],
            ['Root.Verify.Launch'],
            [],
        ]
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
        ]
        assert result.concrete_path[-1].get_history() == result.concrete_path
        assert result.concrete_path[-1].get_history(cycle_only=True) == result.concrete_path

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

        assert result.reachable is False
        assert result.target_frame is None
        assert result.concrete_path is None
        assert result.solution is None
