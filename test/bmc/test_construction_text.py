"""Readable construction reports preserve execution scope and boundary identity."""

from pathlib import Path
import re

import pytest
import z3

from pyfcstm.bmc import BmcOptions, compile_bmc_query
from pyfcstm.bmc.construction import get_bmc_construction
from pyfcstm.model import load_state_machine_from_file, load_state_machine_from_text


pytestmark = pytest.mark.unittest
FIXTURES = Path(__file__).parent / 'fixtures' / 'construction'


def compile_report(source, query, *, groups=None, query_source_path=None, **options):
    compiled = compile_bmc_query(load_state_machine_from_text(source), query,
                                 options=BmcOptions(record_construction=True, **options),
                                 query_source_path=query_source_path)
    ids = groups if groups is not None else tuple('transition.step.%04d' % i
                                                  for i in range(len(compiled.core.steps)))
    return get_bmc_construction(compiled.core, ids)


def assert_snapshot(text_aligner, name, lines):
    text_aligner.assert_equal(expect=(FIXTURES / (name + '.txt')).read_text().rstrip(),
                              actual='\n'.join(lines))


def test_editor_frame_links_keep_conditional_control_context(text_aligner):
    compiled = compile_bmc_query(
        load_state_machine_from_file(str(FIXTURES / 'dose_editor.fcstm')),
        (FIXTURES / 'dose_editor.fbmcq').read_text(), options=BmcOptions(record_construction=True))
    # Include Trim and its next-frame continuation, not an asserted witness.
    ids = tuple('transition.case.%04d.%04d' % (step, index)
                for step in (2, 3) for index, relation in enumerate(compiled.core.steps[step].case_relations)
                if (step == 2 and 'Review::transition::DoseEditor.Editing.Adjust.Trim' in relation.case.label)
                or (step == 3 and 'Trim::transition::' in relation.case.label))
    report = get_bmc_construction(compiled.core, ids)
    assert len(report.cases) == 2
    assert report.check().status == 'verified'
    assert_snapshot(text_aligner, 'editor_frames', report.text_lines())
    assert_snapshot(text_aligner, 'editor_frames_expanded', report.text_lines(expanded=True))


def test_repeated_action_calls_keep_local_lifetimes_and_guard_anchor(text_aligner):
    report = compile_report('''
        input int request; param int gain = 1; def int x = 0;
        state Root {
            state Library { enter Shared { temporary = request * gain; x = x + temporary; } }
            state A {
                enter First ref /Library.Shared;
                enter Second ref /Library.Shared;
                state Ready;
                [*] -> Ready : if [x > 0];
            }
            [*] -> A;
        }
    ''', 'init cold havoc *; check reach <= 1: true;')
    assert report.check().status == 'verified'
    assert_snapshot(text_aligner, 'repeated_calls', report.text_lines())


def test_pure_control_events_are_not_treated_as_accepted_transitions(text_aligner):
    report = compile_report('''
        state Root {
            event Go;
            state A;
            state B { event Go; state Leaf; [*] -> Leaf; }
            [*] -> A;
            A -> B : /Go;
            B -> A : /B.Go;
        }
    ''', '''
        init state("Root.A");
        assume at 0: active("Root.B");
        check reach <= 2: true;
    ''', groups=('initial.target', 'assumption.0000.frame.0000', 'transition.step.0000',
                   'transition.step.0001'), query_source_path="control.fbmcq")
    assert report.check().status == 'verified'
    before = tuple((entry.display, entry.source) for entry in report.core.symbols.names.entries)
    assert_snapshot(text_aligner, 'control_only', report.text_lines())
    assert tuple((entry.display, entry.source) for entry in report.core.symbols.names.entries) == before


@pytest.mark.parametrize('target', ['cold', 'terminated'])
def test_pseudo_state_names_and_absorbing_step(text_aligner, target):
    report = compile_report('state Root { event Stop; }', 'init %s; check reach <= 1: true;' % target,
                            groups=('initial.target', 'transition.step.0000'))
    assert_snapshot(text_aligner, 'control_' + target, report.text_lines())


def test_nested_alternatives_keep_identity_writes_and_guarded_domains(text_aligner):
    report = compile_report('''
        def int x = 0; def int y = 0;
        state Root { enter {
            if [x > 0] {
                x = x;
                if [y > x] { y = y / x; }
            } else if [x < 0] { x = x - 1; }
            y = x + y;
        } }
    ''', 'init cold havoc *; check reach <= 1: true;')
    assert report.check().status == 'verified'
    action = next(action for case in report.cases for action in case.actions)
    assert_snapshot(text_aligner, 'nested_actions', action.text_lines(report.core.symbols.names, expanded=True))
    assert_snapshot(text_aligner, 'nested_frames', report.text_lines())


def test_slicing_keeps_authored_statement_positions(text_aligner):
    report = compile_report('''
        def int x = 0; def int unused = 0;
        state Root { enter {
            unused = unused + 1;
            if [x > 0] { x = x + 1; }
        } }
    ''', 'init cold; check reach <= 1: x > 0;', cone_slicing=True)
    assert report.core.cone_slice.dropped_variables == ('unused',)
    assert_snapshot(text_aligner, 'sliced_actions', report.text_lines())


def test_pruned_branch_keeps_observation_without_inventing_writes(text_aligner):
    report = compile_report('''
        def int x = 0;
        state Root { enter {
            x = 1;
            if [x < 0] { x = 2; } else { x = x; }
        } }
    ''', 'init cold havoc *; check reach <= 1: true;')
    assert_snapshot(text_aligner, 'pruned_action', report.text_lines())


def test_inputs_change_between_steps_parameters_do_not_and_hot_start_has_no_entry(text_aligner):
    report = compile_report('''
        input int request; param int gain = 1; def int x = 0;
        state Root {
            enter { x = 99; }
            during { temporary = request * gain; x = x + temporary; }
        }
    ''', 'init state("Root") havoc *; check reach <= 2: true;')
    assert report.check().status == 'verified'
    assert_snapshot(text_aligner, 'hot_inputs', report.text_lines())


def test_abstract_hooks_do_not_fabricate_boundary_writes(text_aligner):
    report = compile_report('def int x = 0; state Root { enter abstract Observe; }',
                            'init cold havoc *; check reach <= 1: true;')
    assert_snapshot(text_aligner, 'abstract_call', report.text_lines())


def test_guarded_priority_does_not_turn_event_read_into_event_absence(text_aligner):
    report = compile_report('''
        def int x = 0;
        state Root { event Go; state A; state B; [*] -> A;
            A -> B : /Go + [x > 0];
            A -> A : if [x <= 0];
        }
    ''', 'init state("Root.A") havoc *; check reach <= 1: true;')
    assert_snapshot(text_aligner, 'guarded_priority', report.text_lines())


def test_text_options_and_empty_selection(text_aligner):
    report = compile_report('def int x = 0; state Root { enter { x = x; } }', 'init cold; check reach <= 1: true;')
    action = next(action for case in report.cases for action in case.actions)
    with pytest.raises(TypeError, match='expanded must be Boolean'):
        report.text_lines(expanded=1)
    with pytest.raises(TypeError, match='expanded must be Boolean'):
        action.text_lines(expanded='yes')
    empty = get_bmc_construction(report.core, ())
    text_aligner.assert_equal(expect='''
Source construction (no reachability, coverage or UNSAT proof).
Cases are conditional alternatives, not a selected execution trace.
x@f is a frame value; x#n is a local definition in one frame/case, never a cross-frame reference.
event("path")@k is a step k input; active("leaf")@k is the frame k state.
Parameters are shared; @inputk values are fresh step inputs, not persistent frame variables.
Local Boolean cleanup preserves source groups; SMT-specific numeric functions keep their exact meaning.
Selected groups: (none)
For a leaf root, !cold distinguishes its entered position from fbmcq active(root), which also holds at cold.
'''.strip(), actual='\n'.join(empty.text_lines()))


def test_long_names_remain_authored_and_native_operators_are_preserved(text_aligner):
    report = compile_report('''
        def int pressure_before_calibration = 0; def int v0 = 0;
        state Root { enter {
            pressure_before_calibration = (pressure_before_calibration % 7) * v0;
            v0 = (pressure_before_calibration > 0) ? pressure_before_calibration : v0;
        } }
    ''', 'init cold havoc *; check reach <= 1: true;')
    action = next(action for case in report.cases for action in case.actions)
    assert_snapshot(text_aligner, 'long_names', action.text_lines(report.core.symbols.names, expanded=True))


@pytest.mark.parametrize('condition', [
    'true && (x > 0)', 'false || (x > 0)', '!!(x > 0)', '!true', '!false',
    '(x > 0 && y > 0) => (z > 0)',
    '((x > 0) iff (y > 0 && z > 0)) && (x < 10)',
    '(x > 0 || y > 0) xor (z > 0)',
    '((x > 0) => (y > 0)) && ((z > 0) => (x < 10))',
    '!((x > 0 && y > 0) || (z > 0 && x < 10))',
    '((x > 0) ? (y > 0) : (z > 0)) iff (x < 10)',
    '((x + y + z > 0 && x - y + z > 0) => (x > y || y > z)) '
    '&& ((x > 0 || y > 0) => (z < x && z < y))',
    '((x + y + z > 0 && x - y + z > 0) ? '
    '((x > y || y > z) => (x + y > z)) : '
    '((x < y || y < z) iff (x - y < z)))',
    '(1 < 2 && 1.0 != 2.0) => (x > 0)',
    '(2 < 1 || 2.0 == 1.0) iff (x < 0)',
    'z == ((x + y > 0 && x - y < 10 && x * y < 100 && x + y * 7 > -100) '
    '? (x + y) : (x - y))',
])
def test_displayed_boolean_relation_roundtrips_through_fbmcq(condition):
    source = 'def int x = 0; def int y = 0; def int z = 0; state Root;'
    query = 'init state("Root") havoc *; assume at 0: %s; check reach <= 1: true;'
    groups = ('assumption.0000.frame.0000',)
    report = compile_report(source, query % condition, groups=groups)
    original = report.groups[0].expressions[0]
    before = original.sexpr()
    output = '\n'.join(report.text_lines())
    displayed = output.split('  Constraint: ', 1)[1].strip()
    # Only frame labels are removed; the public grammar parses every emitted
    # Boolean operator, its precedence, and all multiline parentheses.
    rebound = compile_report(source, query % re.sub(r'\b([xyz])@0\b', r'\1', displayed), groups=groups)
    recovered = rebound.groups[0].expressions[0]
    recovered = z3.substitute(recovered, *((rebound.core.symbols.frame_var(0, name),
                                           report.core.symbols.frame_var(0, name)) for name in ('x', 'y', 'z')))
    checker = z3.Solver()
    checker.add(z3.Xor(original, recovered))
    assert checker.check() == z3.unsat
    assert original.sexpr() == before


def test_nonleaf_entry_delta_and_negative_source_condition(text_aligner):
    report = compile_report('''
        def int x = 0;
        state Root { state Parent { state Ready; [*] -> Ready : if [x > 0]; }
            [*] -> Parent; }
    ''', '''init state("Root.Parent") havoc *;
        assume at 0: !active("Root.Parent.Ready"); check reach <= 2: true;''',
        groups=('initial.target', 'assumption.0000.frame.0000', 'transition.step.0000'))
    assert report.check().status == 'verified'
    assert_snapshot(text_aligner, 'entry_control', report.text_lines(expanded=True))


def test_deep_guard_and_priority_preserve_named_groups(text_aligner):
    clause = '((x > 10 && y < 20) || (x < -10 && y > 20) || (x > y && x < 100))'
    report = compile_report('''
        def int x = 0; def int y = 0;
        state Root { event Apply; event Cancel; state Ready; state Done;
            [*] -> Ready;
            Ready -> Done : /Cancel + [x > 100];
            Ready -> Done : /Apply + [%s && (x + y > 0 || x - y < 20)] effect {
                if [%s] { x = x + y; } else { x = x - y; }
            };
        }
    ''' % (clause, clause), 'init state("Root.Ready") havoc *; check reach <= 1: true;')
    assert report.check().status == 'verified'
    assert_snapshot(text_aligner, 'deep_conditions', report.text_lines())


def test_expanded_boundaries_retain_typed_numeric_operations(text_aligner):
    report = compile_report('''
        def int x = 0; def int y = 0; def float ratio = 0.0;
        state Root { enter {
            x = (x / y) + (x % y);
            ratio = ratio / 2.0;
            ratio = ratio + x;
            y = abs(x);
        } }
    ''', 'init cold havoc *; check reach <= 1: true;')
    assert report.check().status == 'verified'
    assert_snapshot(text_aligner, 'typed_boundary', report.text_lines(expanded=True))


def test_false_guard_keeps_source_and_conditional_boundary(text_aligner):
    report = compile_report('''
        def int x = 0;
        state Root { event Go; state Ready; state Done; [*] -> Ready;
            Ready -> Done : /Go + [1 < 0] effect { x = x + 1; };
        }
    ''', 'init state("Root.Ready") havoc *; check reach <= 1: true;')
    assert_snapshot(text_aligner, 'false_guard', report.text_lines())


def test_entered_leaf_root_is_not_confused_with_cold(text_aligner):
    report = compile_report('state Root;', '''
        init state("Root"); assume at 0: active("Root"); check reach <= 1: true;
    ''', groups=('initial.target', 'assumption.0000.frame.0000'))
    assert_snapshot(text_aligner, 'leaf_root', report.text_lines())
    # This ordinary query exposes why an exact entered-root position must
    # retain !cold rather than silently borrow the frame-domain premise.
    cold = compile_report('state Root;', '''
        init cold; assume at 0: active("Root"); check reach <= 1: true;
    ''', groups=('initial.target', 'assumption.0000.frame.0000'))
    solver = z3.Solver()
    solver.add(*(expression for group in cold.groups for expression in group.expressions))
    assert solver.check() == z3.sat


def test_shared_branch_condition_stays_scoped_and_expands_completely(text_aligner):
    condition = ('((x + y * 3 > 10 && y - x * 7 < 20) '
                 '|| (x * 7 + y < -10 && y * 3 - x > 20) '
                 '|| (x + y * 3 > y - x * 7 && x * 7 + y < 100) '
                 '|| (x - y * 7 < y + x * 3 && x * 3 - y > -100))')
    report = compile_report('''
        def int x = 0; def int y = 0;
        state Root { enter {
            if [%s] { x = x + y; } else { x = x - y; }
        } }
    ''' % condition, 'init cold havoc *; check reach <= 1: true;')
    assert report.check().status == 'verified'
    assert_snapshot(text_aligner, 'shared_branch', report.text_lines())
    assert_snapshot(text_aligner, 'shared_branch_expanded', report.text_lines(expanded=True))
