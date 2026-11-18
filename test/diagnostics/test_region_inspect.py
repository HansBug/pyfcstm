"""Inspect reports describe regions and judge their ordering through the public API."""

import json
from pathlib import Path

import pytest
from hbutils.testing import simulate_entry

import pyfcstm.diagnostics
from pyfcstm.diagnostics import CODE_REGISTRY, inspect_model
from pyfcstm.entry import pyfcstmcli
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

PLANT = '''
def int temp = 0;
def int duty = 0;
def int alarm = 0;

state Plant {
    [*] -> Run;
    state Run {
        region Sense {
            [*] -> Idle;
            state Idle { during { duty = 1; } }
            state Hot { during { alarm = 1; } }
            Idle -> Hot : if [duty > 50];
            Hot -> Idle : if [active("Plant.Run.Ctrl.Cool")];
            Hot -> [*] :: Stop;
        }
        region Ctrl {
            [*] -> Heat;
            state Heat { during { duty = temp + 2; } }
            state Cool { during { duty = duty - 1; } }
            Heat -> Cool : if [temp > 80];
            Cool -> [*] :: Stop;
        }
    }
    state Off;
    Run -> Off;
    !Run -> Off :: Trip;
}
'''


ORDER_DEMO = '''
def int level = 0;
def int seen = 0;
def int out = 0;
def int y = 0;
state Root {
    region Reader {
        state Idle { during { seen = level; out = 1; } }
        [*] -> Idle;
    }
    region Writer {
        state Busy { during { level = level + 1; out = y + 2; } }
        [*] -> Busy;
    }
}
'''


def inspect_text(source, **kwargs):
    return inspect_model(load_state_machine_from_text(source), **kwargs)


def codes(report, *prefixes):
    return [item.code for item in report.diagnostics if item.code.startswith(prefixes or ('',))]


def validate_against_shipped_schema(report):
    import jsonschema

    schema = json.loads(Path(pyfcstm.diagnostics.__file__).with_name('schema.json').read_text())
    payload = json.loads(json.dumps(report.to_json()))
    jsonschema.Draft7Validator(schema).validate(payload)
    return payload


# ---------------------------------------------------------------- structure

def test_regions_are_described_in_declaration_order():
    report = inspect_text(PLANT)
    assert [(item.path, item.name, item.owner_path, item.index) for item in report.regions] == [
        ('Plant.Run.Sense', 'Sense', 'Plant.Run', 0),
        ('Plant.Run.Ctrl', 'Ctrl', 'Plant.Run', 1),
    ]
    sense, ctrl = report.regions
    assert sense.substates == ('Plant.Run.Sense.Idle', 'Plant.Run.Sense.Hot')
    assert [item['target'] for item in sense.initial_targets] == ['Plant.Run.Sense.Idle']
    assert ctrl.substates == ('Plant.Run.Ctrl.Heat', 'Plant.Run.Ctrl.Cool')


def test_states_and_transitions_inside_regions_are_reported():
    report = inspect_text(PLANT)
    states = {item.path: item for item in report.states}
    assert states['Plant.Run.Sense.Idle'].parent_path == 'Plant.Run.Sense'
    assert states['Plant.Run'].is_composite and not states['Plant.Run'].is_leaf
    assert states['Plant.Run'].substates == ()
    edges = [(item.from_path, item.to_path) for item in report.transitions]
    assert ('Plant.Run.Sense.Idle', 'Plant.Run.Sense.Hot') in edges
    assert ('Plant.Run.Ctrl.Cool', '[*]') in edges
    assert len(report.transitions) == 10
    assert report.structure_statistics.state_count == 7
    assert report.structure_statistics.composite_state_count == 2


def test_region_aspects_events_and_variable_sites_are_reported():
    report = inspect_text('''
    def int count = 0;
    state Root {
        region Worker {
            >> during before { count = count + 1; }
            state Busy;
            [*] -> Busy;
            Busy -> [*] :: Finish;
        }
    }
    ''')
    assert len(report.regions[0].aspect_before) == 1
    assert [(item.state_path, item.aspect) for item in report.actions] == [('Root.Worker', 'before')]
    assert {item.qualified_name for item in report.events} == {'Root.Worker.Busy.Finish'}
    count = next(item for item in report.variables if item.name == 'count')
    assert count.written_in_states and count.read_in_states


def test_reports_without_regions_have_no_regions_key():
    report = inspect_text('state Root { state A; [*] -> A; }')
    assert report.regions == ()
    assert 'regions' not in report.to_json()
    assert 'regions' in inspect_text(PLANT).to_json()


@pytest.mark.parametrize('enable_verify', [False, True])
def test_region_reports_validate_against_the_shipped_schema(enable_verify):
    report = inspect_text(
        PLANT, enable_verify=enable_verify, max_complexity_tier='smt_undecidable_heuristic',
        max_call_count_scaling='quadratic_in_states',
    )
    payload = validate_against_shipped_schema(report)
    assert [item['index'] for item in payload['regions']] == [0, 1]
    assert 'schema_version' not in payload


# ------------------------------------------------------------- reachability

def test_owner_reaches_the_states_of_every_region():
    report = inspect_text(PLANT)
    assert set(report.reachability_graph['Plant.Run']) >= {
        'Plant.Run.Sense.Idle', 'Plant.Run.Sense.Hot', 'Plant.Run.Ctrl.Heat',
        'Plant.Run.Ctrl.Cool', 'Plant.Off',
    }
    assert 'W_UNREACHABLE_STATE' not in codes(report)
    assert 'W_UNREACHABLE_TRANSITION' not in codes(report)


NEVER_COMPLETES = '''
state Plant {
    [*] -> Run;
    state Run {
        region Sense {
            [*] -> Idle;
            state Idle;
            state Hot;
            Idle -> Hot :: Heat;
            Hot -> Idle :: Cool;
        }
        region Ctrl {
            [*] -> A;
            state A;
            A -> [*] :: Done;
        }
    }
    state Off;
    Run -> Off;
}
'''


def test_owner_exit_is_unreachable_when_a_region_can_never_finish():
    report = inspect_text(NEVER_COMPLETES)
    assert 'Plant.Off' not in report.reachability_graph['Plant']
    unreachable = [item for item in report.diagnostics if item.code == 'W_UNREACHABLE_TRANSITION']
    assert [(item.refs['from_path'], item.refs['to_path'], item.refs['reasons'])
            for item in unreachable] == [('Plant.Run', 'Plant.Off', ['owner_never_completes'])]
    assert [item.refs['state_path'] for item in report.diagnostics
            if item.code == 'W_UNREACHABLE_STATE'] == ['Plant.Off']
    assert report.structure_statistics.unreachable_transition_reasons == {'owner_never_completes': 1}


def test_forced_owner_transition_keeps_the_target_reachable():
    report = inspect_text(NEVER_COMPLETES.replace(
        'Run -> Off;', '!Run -> Off :: Trip;'))
    assert 'Plant.Off' in report.reachability_graph['Plant']
    assert 'W_UNREACHABLE_STATE' not in codes(report)


def test_an_inner_owner_that_completes_lets_the_outer_region_finish():
    report = inspect_text('''
    state Root {
        [*] -> Outer;
        state Outer {
            region Left {
                [*] -> Inner;
                state Inner {
                    region Deep { [*] -> X; state X; X -> [*] :: Go; }
                }
                Inner -> [*];
            }
        }
        state After;
        Outer -> After;
    }
    ''')
    assert 'Root.After' in report.reachability_graph['Root']
    assert 'W_UNREACHABLE_STATE' not in codes(report)


# ------------------------------------------------- ordering: the rule table

ORDER_PROLOGUE = '''
def int x = 0;
def int y = 0;
def int z = 0;
'''


def two_regions(second, first='state A { during { x = 1; } } [*] -> A;', before='', between=''):
    return ORDER_PROLOGUE + '''
    state Root {
    %s
        region First { %s }
    %s
        region Second { %s }
    }
    ''' % (before, first, between, second)


ONE_STATE = 'state B { during { %s } } [*] -> B;'
TWO_STATES = '''
    state B { during { %s } }
    state C { during { %s } }
    [*] -> B;
    B -> C :: Go;
    C -> B :: Back;
'''

# (name, second region, first region, expected count)
# The first region is expected to lose its write in every case that counts.
ROW_CASES = [
    # --- the later region overwrites in every cycle without looking: reported
    ('plain_overwrite', ONE_STATE % 'x = y + 2;', None, 1),
    ('write_after_unrelated_statement', ONE_STATE % 'z = y; x = y + 2;', None, 1),
    ('read_after_write_in_block', ONE_STATE % 'x = 0; z = x;', None, 1),
    ('second_straight_line_write', ONE_STATE % 'x = 5; x = 7;', None, 1),
    ('every_state_overwrites', TWO_STATES % ('x = y + 2;', 'x = y + 3;'), None, 1),
    ('earlier_write_in_enter_is_lost_too', ONE_STATE % 'x = y + 2;', 'state A { enter { x = 1; } } [*] -> A;', 1),
    # --- the later region uses the old value somewhere: not reported
    ('uses_old_value', ONE_STATE % 'x = x + y + 2;', None, 0),
    ('branch_condition_reads_old', ONE_STATE % 'if [x > 0] { x = y + 2; }', None, 0),
    ('earlier_else_branch_condition', ONE_STATE % 'if [x > 0] { z = 1; } else { x = y; }', None, 0),
    ('read_before_write_in_block', ONE_STATE % 'z = x; x = 0;', None, 0),
    ('guard_reads_old_in_effect', 'state B; state C; [*] -> B; B -> C : if [x > 0] effect { x = 0; };', None, 0),
    ('outgoing_guard_reads_old', 'state B { during { x = 0; } } state C; [*] -> B; B -> C : if [x > 3];', None, 0),
    ('enter_reads_old', 'state B { enter { z = x; } during { x = y; } } [*] -> B;', None, 0),
    ('own_before_aspect_reads_old', '>> during before { z = x; } ' + ONE_STATE % 'x = y + 2;', None, 0),
    # --- the later region does not overwrite in every cycle: not reported
    ('write_is_conditional', ONE_STATE % 'if [y > 0] { x = y + 2; }', None, 0),
    ('only_one_state_writes', TWO_STATES % ('x = y + 2;', 'z = 1;'), None, 0),
    ('other_state_reads', TWO_STATES % ('x = 0;', 'z = x;'), None, 0),
    ('state_without_during_does_not_write', 'state B { during { x = y; } } state C; [*] -> B; B -> C :: Go;', None, 0),
    ('region_can_finish', 'state B { during { x = y; } } state C; [*] -> B; B -> C :: Go; C -> [*];', None, 0),
    ('abstract_action_may_read', 'state B { during abstract Peek; during { x = y; } } [*] -> B;', None, 0),
    ('independent_variable', ONE_STATE % 'y = 3;', None, 0),
    ('abstract_enter_may_read', 'state B { enter abstract Setup; during { x = y; } } [*] -> B;', None, 0),
    ('nested_owner_is_not_judged', 'state C { region In { state D { during { x = y; } } [*] -> D; } } [*] -> C;', None, 0),
    ('nested_owner_with_its_own_aspect', 'state C { region In { >> during before { z = x; } state D { during { x = y; } } [*] -> D; } } [*] -> C;', None, 0),
    ('composite_during_before_reads_old', 'state C { during before { z = x; } state D { during { x = y; } } [*] -> D; } [*] -> C;', None, 0),
    ('composite_during_after_abstract', 'state C { during after abstract Peek; state D { during { x = y; } } [*] -> D; } [*] -> C;', None, 0),
    ('if_else_writes_in_every_branch', ONE_STATE % 'if [y > 0] { x = 2; } else { x = 3; }', None, 1),
    ('if_without_else_does_not_cover', ONE_STATE % 'if [y > 0] { x = 2; }', None, 0),
    ('nested_if_else_covers_only_inside_its_branch',
     ONE_STATE % 'if [y > 0] { if [z > 0] { x = 2; } else { x = 3; } } else { z = 1; }', None, 0),
    ('transition_effect_with_a_branch_does_not_matter',
     'state B { during { x = y; } } state C { during { x = y; } } [*] -> B; '
     'B -> C :: Go effect { if [y > 0] { z = 1; } else { z = 2; } };', None, 1),
    # --- aspects and pseudo states inside the later region
    ('own_after_aspect_reads_the_new_value', '>> during after { z = x; } ' + ONE_STATE % 'x = y + 2;', None, 1),
    ('pseudo_leaf_needs_no_write', 'pseudo state P; state B { during { x = y; } } [*] -> P; P -> B;', None, 1),
    ('composite_before_aspect_covers_every_leaf',
     'state C { >> during before { x = y; } state D1; state D2; [*] -> D1; D1 -> D2 :: Go; D2 -> D1 :: Back; } [*] -> C;',
     None, 1),
    ('composite_before_aspect_reads_old',
     'state C { >> during before { z = x; } state D { during { x = y; } } [*] -> D; } [*] -> C;', None, 0),
    # --- the earlier write is used in its own cycle: nothing is lost
    ('earlier_region_uses_its_own_value', ONE_STATE % 'x = y + 2;', 'state A { during { x = 1; z = x; } } [*] -> A;', 0),
    ('earlier_region_after_aspect_reads', ONE_STATE % 'x = y + 2;', '>> during after { z = x; } state A { during { x = 1; } } [*] -> A;', 0),
    ('earlier_region_reads_in_composite_during', ONE_STATE % 'x = y + 2;', 'state A { during { x = 1; } } [*] -> A;', 1),
    ('earlier_region_abstract_action', ONE_STATE % 'x = y + 2;', 'state A { during { x = 1; } during abstract Peek; } [*] -> A;', 0),
]


def run_case(second, first, before='', between=''):
    first = first or 'state A { during { x = 1; } } [*] -> A;'
    return inspect_text(two_regions(second, first, before, between))


@pytest.mark.parametrize('name, second, first, expected', ROW_CASES, ids=[case[0] for case in ROW_CASES])
def test_blind_overwrite_follows_the_rule_table(name, second, first, expected):
    report = run_case(second, first)
    found = [item for item in report.diagnostics if item.code == 'W_REGION_BLIND_OVERWRITE']
    assert len(found) == expected
    for item in found:
        assert item.severity == 'warning'
        assert item.span is not None and item.refs['previous_write_span'] is not None
        assert {key: value for key, value in item.refs.items() if key != 'previous_write_span'} == {
            'owner_path': 'Root', 'region': 'Root.Second', 'previous_region': 'Root.First',
            'variable': 'x',
        }


def test_aspects_of_the_owner_run_around_the_whole_group_and_shield_nothing():
    # They read the value left by the previous cycle, before and after the group,
    # so they neither use the first region's value nor protect it.
    for aspect in ('before', 'after'):
        report = inspect_text(two_regions(
            ONE_STATE % 'x = y + 2;', before='>> during %s { z = x; }' % aspect))
        assert codes(report, 'W_REGION', 'I_REGION') == ['W_REGION_BLIND_OVERWRITE']


def test_a_region_in_between_that_has_an_abstract_action_may_read_the_old_value():
    report = run_case(
        ONE_STATE % 'x = y + 2;', None,
        between='region Middle { state M { during abstract Peek; } [*] -> M; }')
    assert 'W_REGION_BLIND_OVERWRITE' not in codes(report)


def test_the_warning_points_at_the_overwrite_and_names_the_lost_write():
    source = two_regions(ONE_STATE % 'x = y + 2;')
    report = inspect_text(source)
    item = next(d for d in report.diagnostics if d.code == 'W_REGION_BLIND_OVERWRITE')
    lines = source.splitlines()
    span, lost = item.span, item.refs['previous_write_span']
    assert lines[span.line - 1][span.column - 1:].startswith('x = y + 2;')
    assert lines[lost.line - 1][lost.column - 1:].startswith('x = 1;')


def test_only_the_write_that_nothing_reads_is_named_as_lost():
    first = 'state A { during { x = 1; z = x; x = 2; } } [*] -> A;'
    source = two_regions(ONE_STATE % 'x = y + 2;', first)
    item = next(d for d in inspect_text(source).diagnostics if d.code == 'W_REGION_BLIND_OVERWRITE')
    lost = item.refs['previous_write_span']
    assert source.splitlines()[lost.line - 1][lost.column - 1:].startswith('x = 2;')


def test_reading_the_regions_own_fresh_value_is_not_a_backward_read():
    report = run_case(ONE_STATE % 'x = 3;', 'state A { during { x = 1; z = x; } } [*] -> A;')
    assert 'I_REGION_BACKWARD_READ' not in codes(report)


def test_overwrite_is_not_blind_when_a_region_in_between_reads_the_old_value():
    source = ORDER_PROLOGUE + '''
    state Root {
        region First { state A { during { x = 1; } } [*] -> A; }
        region Middle { state M { during { z = x; } } [*] -> M; }
        region Last { state L { during { x = 0; } } [*] -> L; }
    }
    '''
    assert 'W_REGION_BLIND_OVERWRITE' not in codes(inspect_text(source))


def test_overwrite_names_the_nearest_earlier_writer():
    source = ORDER_PROLOGUE + '''
    state Root {
        region First { state A { during { x = 1; } } [*] -> A; }
        region Middle { state M { during { z = 2; } } [*] -> M; }
        region Last { state L { during { x = 0; } } [*] -> L; }
    }
    '''
    item = next(d for d in inspect_text(source).diagnostics if d.code == 'W_REGION_BLIND_OVERWRITE')
    assert item.refs['previous_region'] == 'Root.First'
    assert item.refs['region'] == 'Root.Last'


def test_nested_regions_are_judged_inside_their_own_owner():
    source = ORDER_PROLOGUE + '''
    state Root {
        region Outer {
            state Mid {
                region In1 { state A { during { x = 1; } } [*] -> A; }
                region In2 { state B { during { x = y; } } [*] -> B; }
            }
            [*] -> Mid;
        }
    }
    '''
    item = next(d for d in inspect_text(source).diagnostics if d.code == 'W_REGION_BLIND_OVERWRITE')
    assert item.refs['owner_path'] == 'Root.Outer.Mid'
    assert item.refs['region'] == 'Root.Outer.Mid.In2'


# ------------------------------------------------ ordering: backward reads

def test_backward_variable_read_is_informational():
    source = ORDER_PROLOGUE + '''
    state Root {
        region Reader { state Idle { during { z = x; } } [*] -> Idle; }
        region Writer { state Busy { during { x = x + 1; } } [*] -> Busy; }
    }
    '''
    found = [d for d in inspect_text(source).diagnostics if d.code == 'I_REGION_BACKWARD_READ']
    assert len(found) == 1
    assert found[0].severity == 'info'
    assert found[0].refs == {
        'owner_path': 'Root', 'reader_region': 'Root.Reader', 'target_kind': 'variable',
        'target': 'x', 'writer_regions': ['Root.Writer'],
    }
    assert found[0].span is not None


def test_backward_active_query_is_informational():
    source = '''
    def int seen = 0;
    state Root {
        region Reader {
            state Idle { during { if [active("Root.Writer.Busy")] { seen = 1; } } }
            [*] -> Idle;
        }
        region Writer { state Busy; [*] -> Busy; }
    }
    '''
    found = [d for d in inspect_text(source).diagnostics if d.code == 'I_REGION_BACKWARD_READ']
    assert [(d.refs['target_kind'], d.refs['target'], d.refs['writer_regions']) for d in found] == [
        ('active', 'Root.Writer.Busy', ['Root.Writer']),
    ]


def test_forward_reads_are_silent():
    source = ORDER_PROLOGUE + '''
    state Root {
        region Writer { state Busy { during { x = x + 1; } } [*] -> Busy; }
        region Reader { state Idle { during { z = x; } } [*] -> Idle; }
    }
    '''
    assert 'I_REGION_BACKWARD_READ' not in codes(inspect_text(source))


def test_active_queries_do_not_leak_hidden_flag_variables():
    report = inspect_text(PLANT)
    assert not any(item.name.startswith('__active') for item in report.variables)
    for item in report.diagnostics:
        assert '__active' not in json.dumps(item.refs, default=str)
        assert '__active' not in item.message
    assert [item.refs['target'] for item in report.diagnostics
            if item.code == 'I_REGION_BACKWARD_READ'] == ['duty', 'Plant.Run.Ctrl.Cool']
    # ``Cool`` reads ``duty`` before writing it, so ``Ctrl`` does not overwrite
    # ``duty`` blindly in every cycle.
    assert 'W_REGION_BLIND_OVERWRITE' not in codes(report)


def test_single_region_gets_no_ordering_diagnostics():
    source = ORDER_PROLOGUE + '''
    state Root { region Only { state A { during { x = y; z = x; } } [*] -> A; } }
    '''
    assert not codes(inspect_text(source), 'I_REGION', 'W_REGION')


def test_ordering_codes_are_cataloged_for_both_severities():
    assert CODE_REGISTRY['I_REGION_BACKWARD_READ'].severity == 'info'
    assert CODE_REGISTRY['W_REGION_BLIND_OVERWRITE'].severity == 'warning'
    for code in ('I_REGION_BACKWARD_READ', 'W_REGION_BLIND_OVERWRITE'):
        spec = CODE_REGISTRY[code]
        report = inspect_text(spec.example_dsl)
        assert code in codes(report)


# ---------------------------------------- existing checks follow into regions

def test_expression_checks_reach_transitions_inside_regions():
    report = inspect_text('''
    def int n = 0;
    state Root {
        region Work {
            state A; state B;
            [*] -> A;
            A -> B : if [1 > 2];
        }
    }
    ''')
    assert 'W_GUARD_CONST_FALSE' in codes(report)


def test_region_without_unconditional_initial_transition_is_reported():
    report = inspect_text('''
    def int n = 0;
    state Root {
        region Work { state A; [*] -> A : if [n > 0]; }
        region Other { state B; [*] -> B; }
    }
    ''')
    found = [d for d in report.diagnostics if d.code == 'W_INITIAL_UNCONDITIONAL_MISSING']
    assert [d.refs['composite_path'] for d in found] == ['Root.Work']


def test_owner_with_regions_is_not_asked_for_its_own_initial_transition():
    report = inspect_text(PLANT)
    assert 'W_INITIAL_UNCONDITIONAL_MISSING' not in codes(report)


def test_large_region_is_counted_like_a_large_composite():
    states = ''.join('state S%d;' % index for index in range(3))
    report = inspect_text('state Root { region Work { %s [*] -> S0; } }' % states,
                          large_composite_threshold=2)
    assert [d.refs['composite_path'] for d in report.diagnostics
            if d.code == 'W_LARGE_COMPOSITE'] == ['Root.Work']


def test_initial_livelock_inside_a_region_is_found_and_region_exit_is_an_escape():
    looping = inspect_text('''
    state Root { region Work { pseudo state P; [*] -> P; P -> P; } }
    ''')
    assert 'W_INITIAL_LIVELOCK' in codes(looping)
    finishing = inspect_text('''
    state Root { region Work { pseudo state P; [*] -> P; P -> [*]; } }
    ''')
    assert 'W_INITIAL_LIVELOCK' not in codes(finishing)


def test_unreachable_state_inside_a_region_is_found():
    report = inspect_text('''
    state Root { region Work { state A; state Orphan; [*] -> A; } }
    ''')
    assert [d.refs['state_path'] for d in report.diagnostics
            if d.code == 'W_UNREACHABLE_STATE'] == ['Root.Work.Orphan']


def test_data_flow_checks_see_variables_used_only_inside_regions():
    report = inspect_text('''
    def int a = 0;
    def int b = 0;
    state Root {
        region Work {
            state A { during { a = a + 1; } }
            state B;
            [*] -> A;
            A -> B : if [a > 3];
        }
    }
    ''')
    assert 'W_UNREFERENCED_VAR' in [d.code for d in report.diagnostics
                                    if d.refs.get('variable') == 'b' or 'b' in d.message]
    assert not any(d.code == 'W_UNREFERENCED_VAR' and "'a'" in d.message for d in report.diagnostics)


# ------------------------------------------------------------ verify bridge

def test_verify_excludes_single_path_algorithms_with_an_explicit_reason():
    report = inspect_text(
        PLANT, enable_verify=True, max_complexity_tier='smt_undecidable_heuristic',
        max_call_count_scaling='quadratic_in_states', smt_timeout_ms=5000,
    )
    by_name = {item.algorithm_name: item for item in report.verification.algorithms}
    for name in ('topological_reachable_set', 'unreachable_states', 'strongly_connected_components',
                 'topological_finite', 'topological_inevitable_terminator',
                 'event_emission_to_consumer_reachable'):
        assert by_name[name].result_kind == 'not_run'
        assert by_name[name].reason_code == 'requires_single_active_path'
    assert by_name['dead_guard'].result_kind != 'not_run'
    assert by_name['enter_postcondition_implies_during_precondition'].result_kind == 'undecidable_skip'
    assert 'region' in by_name['enter_postcondition_implies_during_precondition'].reason


def test_active_guards_are_skipped_by_solver_checks_instead_of_misjudged():
    report = inspect_text(
        PLANT, enable_verify=True, max_complexity_tier='smt_undecidable_heuristic',
        max_call_count_scaling='quadratic_in_states', smt_timeout_ms=5000,
    )
    by_name = {item.algorithm_name: item for item in report.verification.algorithms}
    assert by_name['dead_guard'].result_kind == 'undecidable_skip'
    assert 'ActiveStateQuery' in by_name['dead_guard'].reason


def test_solver_checks_run_inside_regions():
    report = inspect_text('''
    def int n = 0;
    state Root {
        region Work {
            state A; state B;
            [*] -> A;
            A -> B : if [n > 5 && n < 3];
        }
    }
    ''', enable_verify=True, max_complexity_tier='smt_linear', smt_timeout_ms=5000)
    assert 'W_DEAD_GUARD' in codes(report)


def test_initial_guard_gap_inside_a_region_is_found_by_the_solver():
    report = inspect_text('''
    def int n = 0;
    state Root {
        region Work {
            state A; state B;
            [*] -> A : if [n > 0];
            [*] -> B : if [n < 0];
        }
    }
    ''', enable_verify=True, max_complexity_tier='smt_linear', smt_timeout_ms=5000)
    assert 'W_COMPOSITE_INIT_INCOMPLETE' in codes(report)


def test_models_without_regions_keep_their_verification_report():
    report = inspect_text('state Root { state A; [*] -> A; A -> [*]; }', enable_verify=True)
    assert all(item.reason_code != 'requires_single_active_path'
               for item in report.verification.algorithms)


# ---------------------------------------------------------------------- CLI

def run_cli(tmp_path, source, *arguments):
    path = tmp_path / 'machine.fcstm'
    path.write_text(source, encoding='utf-8')
    return simulate_entry(pyfcstmcli, ['pyfcstm', 'inspect', '-i', str(path), *arguments])


def test_cli_json_report_lists_regions_and_ordering_diagnostics(tmp_path):
    result = run_cli(tmp_path, ORDER_DEMO, '--format', 'json')
    assert result.exitcode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [item['path'] for item in payload['regions']] == ['Root.Reader', 'Root.Writer']
    assert {'I_REGION_BACKWARD_READ', 'W_REGION_BLIND_OVERWRITE'} <= {
        item['code'] for item in payload['diagnostics']}
    blind = next(item for item in payload['diagnostics'] if item['code'] == 'W_REGION_BLIND_OVERWRITE')
    assert blind['refs']['previous_write_span'] == {
        'line': 8, 'column': 45, 'end_line': 8, 'end_column': 53}


def test_cli_human_report_lists_regions_and_ordering_diagnostics(tmp_path):
    result = run_cli(tmp_path, ORDER_DEMO)
    assert result.exitcode == 0, result.stderr
    assert 'regions: 2' in result.stdout
    assert 'Root.Reader' in result.stdout and 'Root.Writer' in result.stdout
    assert 'W_REGION_BLIND_OVERWRITE' in result.stdout
    assert 'I_REGION_BACKWARD_READ' in result.stdout
    assert 'Traceback' not in result.stdout + result.stderr


def test_cli_collect_errors_keeps_build_errors_for_region_models(tmp_path):
    result = run_cli(tmp_path, 'state Root { region Worker { state A; } }', '--collect-errors',
                     '--format', 'json')
    payload = json.loads(result.stdout)
    assert 'E_INITIAL_TRANSITION_INVALID' in [item['code'] for item in payload['diagnostics']]
    assert [item['path'] for item in payload['regions']] == ['Root.Worker']


def test_cli_active_only_model_is_inspected(tmp_path):
    result = run_cli(tmp_path, 'state Root { state A; [*] -> A; A -> [*] : if [active("Root.A")]; }',
                     '--format', 'json')
    assert result.exitcode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert 'regions' not in payload
    assert [item['guard'] for item in payload['transitions'] if item['guard']] == ['active("Root.A")']


# ------------------------------------------------- tests added for coverage

@pytest.mark.parametrize('edge', ['A -> B : [x > 0] + [x > -1];', '[*] -> A : [x > 0] + [x > -1];'])
def test_combo_guard_checks_apply_inside_regions(edge):
    report = inspect_text('''
    def int x = 1;
    state Root {
        region Work { state A; state B; [*] -> A; %s }
    }
    ''' % edge)
    assert 'W_COMBO_GUARD_PREFIX_IMPLIED' in codes(report)


def test_combo_guard_check_sees_source_state_exit_writes_inside_regions():
    report = inspect_text('''
    def int x = 1;
    state Root {
        region Work {
            state A { exit { x = 5; } }
            state B;
            [*] -> A;
            A -> B : [x > 0] + [x > -1];
        }
    }
    ''')
    assert 'W_COMBO_GUARD_PREFIX_IMPLIED' not in codes(report)


def test_querying_an_earlier_or_own_region_is_silent():
    source = '''
    def int seen = 0;
    state Root {
        region First {
            state A { during { if [active("Root.First.A")] { seen = 1; } } }
            [*] -> A;
        }
        region Second {
            state B { during { if [active("Root.First.A")] { seen = 2; } } }
            [*] -> B;
        }
    }
    '''
    assert 'I_REGION_BACKWARD_READ' not in codes(inspect_text(source))


def test_block_temporaries_are_not_model_variables_for_ordering():
    source = ORDER_PROLOGUE + '''
    state Root {
        region First { state A { during { x = 1; } } [*] -> A; }
        region Second { state B { during { tmp = x; z = tmp; } } [*] -> B; }
    }
    '''
    report = inspect_text(source)
    assert 'W_REGION_BLIND_OVERWRITE' not in codes(report)
    assert 'I_REGION_BACKWARD_READ' not in codes(report)


def test_distinct_reads_of_one_variable_report_once_per_reading_region():
    source = ORDER_PROLOGUE + '''
    state Root {
        region Reader { state R { during { z = x + x; y = x; } } [*] -> R; }
        region Writer { state W { during { x = y + 1; } } [*] -> W; }
    }
    '''
    found = [d for d in inspect_text(source).diagnostics if d.code == 'I_REGION_BACKWARD_READ']
    assert [(d.refs['target'], d.refs['reader_region']) for d in found] == [('x', 'Root.Reader')]


def test_region_whose_only_exit_state_is_unreachable_never_completes():
    report = inspect_text('''
    state Plant {
        [*] -> Run;
        state Run {
            region Work {
                [*] -> A;
                state A; state B; state Orphan;
                A -> B; B -> A;
                Orphan -> [*];
            }
        }
        state Off;
        Run -> Off;
    }
    ''')
    assert 'Plant.Off' not in report.reachability_graph['Plant']
    assert [item.refs['reasons'] for item in report.diagnostics
            if item.code == 'W_UNREACHABLE_TRANSITION'
            and item.refs['from_path'] == 'Plant.Run'] == [['owner_never_completes']]


def test_a_region_cannot_finish_through_an_inner_owner_that_never_completes():
    report = inspect_text('''
    state Root {
        [*] -> Outer;
        state Outer {
            region Left {
                [*] -> Inner;
                state Inner {
                    region Deep { [*] -> X; state X; state Y; X -> Y; Y -> X; }
                }
                Inner -> [*];
            }
        }
        state After;
        Outer -> After;
    }
    ''')
    assert 'Root.After' not in report.reachability_graph['Root']
    owners = sorted(item.refs['from_path'] for item in report.diagnostics
                    if item.code == 'W_UNREACHABLE_TRANSITION'
                    and 'owner_never_completes' in item.refs['reasons'])
    assert owners == ['Root.Outer', 'Root.Outer.Left.Inner']


def test_history_entry_inside_a_region_reaches_the_default_path():
    report = inspect_text('''
    state Root {
        region Worker {
            state Group { [H] -> Idle; [*] -> Idle; state Idle; }
            [*] -> Group.[H];
        }
    }
    ''')
    assert {'Root.Worker.Group', 'Root.Worker.Group.Idle'} <= set(report.reachability_graph['Root'])
    assert 'W_UNREACHABLE_STATE' not in codes(report)


@pytest.mark.parametrize('output_format', ['llm-md', 'llm-json'])
def test_cli_llm_reports_carry_the_region_diagnostics(tmp_path, output_format):
    result = run_cli(tmp_path, ORDER_DEMO, '--format', output_format)
    assert result.exitcode == 0, result.stderr
    assert 'W_REGION_BLIND_OVERWRITE' in result.stdout
    assert 'I_REGION_BACKWARD_READ' in result.stdout


def test_hierarchy_depth_counts_states_not_region_segments():
    source = '''
    state Root {
        region R {
            state S {
                region R2 { state T; [*] -> T; }
            }
            [*] -> S;
        }
    }
    '''
    report = inspect_text(source, deep_hierarchy_threshold=1)
    assert report.metrics.max_hierarchy_depth == 2
    deep = [d for d in report.diagnostics if d.code == 'W_DEEP_HIERARCHY']
    assert [(d.refs['max_depth'], d.refs['deepest_path']) for d in deep] == [(2, 'Root.R.S.R2.T')]
    assert 'W_DEEP_HIERARCHY' not in codes(inspect_text(source, deep_hierarchy_threshold=2))


def test_region_aspects_report_the_leaves_they_reach():
    report = inspect_text('''
    def int n = 0;
    state Root {
        region Work {
            >> during before { n = n + 1; }
            state A { during { n = 0; } }
            [*] -> A;
        }
        region Idle { state B; [*] -> B; }
    }
    ''')
    assert report.aspect_impact_map == {'Root.Work': ('Root.Work.A',)}


def test_region_aspect_without_a_reachable_leaf_is_reported_for_the_region():
    report = inspect_text('''
    def int n = 0;
    state Root {
        region Work {
            >> during before { n = n + 1; }
            pseudo state P;
            [*] -> P;
        }
    }
    ''')
    found = [d for d in report.diagnostics if d.code == 'W_ASPECT_NO_DESCENDANT_LEAF']
    assert [(d.refs['composite_path'], d.refs['aspect']) for d in found] == [('Root.Work', 'before')]
    assert "Region 'Root.Work'" in found[0].message


def test_forced_transitions_and_declared_events_inside_regions_are_reported():
    report = inspect_text('''
    state Root {
        region Work {
            event Spare;
            state A; state B; state C;
            [*] -> A;
            A -> B :: Go;
            !* -> C :: Abort;
        }
    }
    ''')
    assert [(item.state_path, item.expansion_count) for item in report.forced_transitions] == [
        ('Root.Work', 3)]
    assert len([item for item in report.transitions if item.is_forced]) == 3
    assert [d.refs['event_qualified_name'] for d in report.diagnostics if d.code == 'W_UNUSED_EVENT'] == [
        'Root.Work.Spare']


def test_inspect_with_verify_accepts_models_that_only_use_active_queries():
    source = 'state Root { [*] -> A; state A; state B; state C; A -> B : if [active("Root.C")]; B -> A; }'
    for options in ({}, {'max_complexity_tier': 'smt_undecidable_heuristic',
                         'max_call_count_scaling': 'quadratic_in_states'}):
        report = inspect_text(source, enable_verify=True, **options)
        by_name = {item.algorithm_name: item for item in report.verification.algorithms}
        assert by_name['topological_reachable_set'].result_kind == 'not_run'
        assert by_name['topological_reachable_set'].reason_code == 'active_query_unsupported'
        validate_against_shipped_schema(report)
    assert report.verification.algorithms[0].reason_code == 'active_query_unsupported'
    result = run_cli_text_verify(source)
    assert result.exitcode == 0, result.stderr


def run_cli_text_verify(source):
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'active.fcstm'
        path.write_text(source, encoding='utf-8')
        return simulate_entry(pyfcstmcli, ['pyfcstm', 'inspect', '-i', str(path), '--enable-verify'])


@pytest.mark.parametrize('exits', ['s -> [*]; s -> [*];', 's -> [*]; s -> [*] :: Ev;'])
def test_verify_handles_repeated_region_exits(exits):
    source = 'state T { [*] -> A; state A { region r { [*] -> s; state s; %s } } }' % exits
    report = inspect_text(source, enable_verify=True, max_complexity_tier='smt_linear',
                          smt_timeout_ms=5000)
    by_name = {item.algorithm_name: item for item in report.verification.algorithms}
    assert by_name['transition_shadowed_by_predecessor'].result_kind != 'not_run'
    validate_against_shipped_schema(report)


def test_aspects_of_the_owner_are_not_reads_of_the_regions_inside():
    source = '''
    def int z = 0;
    state R {
        >> during before { if [active("R.B.Q")] { z = 1; } }
        region A { state P; [*] -> P; }
        region B { state Q; [*] -> Q; }
    }
    '''
    assert 'I_REGION_BACKWARD_READ' not in codes(inspect_text(source))


def test_ordering_analyzer_accepts_a_missing_model():
    from pyfcstm.diagnostics.analyzers.region_order import collect_region_order_diagnostics

    assert collect_region_order_diagnostics(None) == []


def test_a_region_in_between_that_reads_in_a_composite_during_uses_the_old_value():
    report = run_case(
        ONE_STATE % 'x = y + 2;', None,
        between='region Middle { state C { during before { z = x; } state Q; [*] -> Q; } [*] -> C; }')
    assert 'W_REGION_BLIND_OVERWRITE' not in codes(report)


def test_the_earlier_write_is_used_by_the_composite_during_that_follows_its_effect():
    first = (
        'state P; state C { during before { z = x; } state S { during { y = y + 1; } } [*] -> S; } '
        '[*] -> P; P -> C :: Go effect { x = 1; }'
    )
    report = run_case(ONE_STATE % 'x = y + 2;', first)
    assert 'W_REGION_BLIND_OVERWRITE' not in codes(report)


@pytest.mark.parametrize('first, expected', [
    ('state A { during { if [y > 0] { x = 1; z = x; } } } [*] -> A;', 0),
    ('state A { during { if [y > 0] { x = 1; } else { x = 2; } z = x; } } [*] -> A;', 0),
    ('state A { during { if [y > 0] { x = 1; } z = x; } } [*] -> A;', 1),
    ('state C { during before { z = x; } state A; [*] -> A; } [*] -> C;', 1),
    ('state C { during after { z = x; } state A; [*] -> A; } [*] -> C;', 1),
])
def test_backward_read_follows_what_the_region_wrote_before_reading(first, expected):
    source = two_regions('state B { during { x = x + 1; } } [*] -> B;', first)
    found = [d for d in inspect_text(source).diagnostics if d.code == 'I_REGION_BACKWARD_READ']
    assert len(found) == expected
