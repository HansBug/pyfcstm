"""Reproduce the numeric limits and the checked gaps listed in the limits table."""
import logging
import subprocess
import sys

from pyfcstm.bmc import BmcOptions, build_bmc_core_formula, prepare_bmc_query
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcQuery
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.render.c_kernel import render_c_storage_macros
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeDfsError
from pyfcstm.utils.validate import ModelValidationError

logging.disable(logging.CRITICAL)  # the Delta log lines are not part of the transcript


def section(title):
    print('== %s' % title)


section('simulator: owners entered inside one another in one cycle')
for depth in (64, 65):
    text = 'state Leaf;'
    name = 'Leaf'
    for index in range(depth):
        text = 'state S%d { region R { [*] -> %s; %s } }' % (index, name, text)
        name = 'S%d' % index
    model = load_state_machine_from_text('state Root { [*] -> %s; %s }' % (name, text))
    try:
        SimulationRuntime(model).cycle()
        print('%d nested owners: the first cycle runs' % depth)
    except SimulationRuntimeDfsError as error:
        # SimulationRuntimeDfsError: the nesting passed the structural safety limit.
        print('%d nested owners: SimulationRuntimeDfsError: %s' % (depth, str(error).split(';')[0]))

section('simulator: steps in one cycle')
chain = ('def int n = 0; state Root { [*] -> p; pseudo state p; state Done; '
         'p -> p : if [n < 500] effect { n = n + 1; }; p -> Done; }')
try:
    SimulationRuntime(load_state_machine_from_text(chain)).cycle()
except SimulationRuntimeDfsError as error:
    # SimulationRuntimeDfsError: 500 turns of the pseudo state need more than 1000 steps.
    print('SimulationRuntimeDfsError: %s' % str(error).split(';')[0])

section('BMC: how often one owner may re-enter itself in one cycle')


def reentering(limit):
    return ('def int n = 0; state Root { [*] -> O; '
            'state O { region A { [*] -> p; pseudo state p; p -> [*]; } } state Done; '
            'O -> O : if [n < %d] effect { n = n + 1; }; O -> Done; }' % limit)


query = 'check reach <= 1: active("Root.Done");'
for limit, options in [(3, BmcOptions()), (20, BmcOptions()), (3, BmcOptions(max_group_reentries=2))]:
    context = prepare_bmc_query(load_state_machine_from_text(reentering(limit)), query, options)
    try:
        build_bmc_core_formula(context)
        print('n < %d, max_group_reentries=%d: built' % (limit, options.max_group_reentries))
    except BmcBuildError as error:
        # BmcBuildError: the group re-enters itself more often than the option allows.
        print('n < %d, max_group_reentries=%d: BmcBuildError: %s' % (limit, options.max_group_reentries, error))

section('BMC: depth of one expression')
flat = load_state_machine_from_text('def int x = 0; state Root { [*] -> A; state A; }')
for count in (98, 99):
    try:
        prepare_bmc_query(flat, 'check reach <= 1: ' + '!' * count + '(x == 0);')
        print('%d prefix negations: accepted' % count)
    except InvalidBmcQuery as error:
        # InvalidBmcQuery: the expression nests deeper than 100 levels.
        print('%d prefix negations: InvalidBmcQuery: %s' % (count, error))

section('model: a history owner whose subtree has a region')
try:
    load_state_machine_from_text(
        'state Root { [*] -> P; state P { [*] -> Q; [H] -> Q; '
        'state Q { region A { state L; [*] -> L; } } } }')
except ModelValidationError as error:
    # ModelValidationError: the history owner P has a region below it.
    print(', '.join('%s (%s)' % (item.code, item.refs['reason']) for item in error.diagnostics))

section('simulator: a composite candidate that only loops (a model without regions)')
with open('limits_composite_loop.fcstm') as stream:
    runtime = SimulationRuntime(load_state_machine_from_text(stream.read()))
for events in ([], ['Root.Go'], ['Root.Go'], []):
    result = runtime.cycle(events)
    print('events=%-12s delta=%-5s %-8s x=%s' % (
        events, result.delta, '.'.join(runtime.current_state.path), runtime.vars['x']))

section('export: the text of to_ast_node() runs like the machine it came from (forced declaration over regions)')
exit_order = '''def int seq = 0;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1 { exit { seq = seq * 10 + 1; } } }
        region B { [*] -> B1; state B1 { exit { seq = seq * 10 + 2; } } }
    }
    state Idle;
    !Run -> Idle : /Stop;
}'''


def run(machine):
    runtime = SimulationRuntime(machine)
    rows = []
    for events in ([], ['Root.Stop']):
        runtime.cycle(events)
        rows.append((str(runtime.configuration), runtime.vars['seq']))
    return rows


original = load_state_machine_from_text(exit_order)
reloaded = load_state_machine_from_text(str(original.to_ast_node()))
print('original  %s' % run(original))
print('reloaded  %s' % run(reloaded))

section('inspect: a state entered only as a history default is never reported unreachable')
with open('limits_history_default.fcstm') as stream:
    source = stream.read()
report = subprocess.run(
    [sys.executable, '-m', 'pyfcstm', 'inspect', '-i', 'limits_history_default.fcstm', '--color', 'never'],
    stdout=subprocess.PIPE, universal_newlines=True, check=True).stdout
print([line.strip() for line in report.splitlines() if line.strip().startswith('unreachable:')][0])
runtime = SimulationRuntime(load_state_machine_from_text(source))
runtime.cycle()
runtime.cycle('/Go')
print('after /Go the machine is in %s' % runtime.configuration)

section('generated C: default capacities')
controller = load_state_machine_from_text(open('../../tutorials/regions/controller.fcstm').read())
flat_machine = load_state_machine_from_text('state Root { [*] -> A; state A; state B; A -> B :: Go; }')
for label, machine in (('controller (6 states, 2 regions)', controller), ('flat machine (3 states)', flat_machine)):
    lines = [line for line in render_c_storage_macros(machine, 'M').splitlines() if line.startswith('#define M_')]
    print('%s: %s' % (label, '; '.join(line.replace('#define M_', '') for line in lines[:2])))
