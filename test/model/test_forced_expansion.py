"""Forced transitions of models without regions, as the model exposes them."""

import gc
import json

import pytest

from pyfcstm.diagnostics.inspect import inspect_model
from pyfcstm.dsl import EXIT_STATE, parse_with_grammar_entry
from pyfcstm.model import load_state_machine_from_text, parse_dsl_node_to_state_machine
from pyfcstm.model.region import walk_namespaces
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest

NESTED = '''def int n = 0;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        [*] -> Inner;
        state Inner {
            [*] -> A;
            state A { during { n = n + 1; } }
            pseudo state Junction;
            state B;
            A -> B : if [n >= 3];
        }
        state Side;
    }
    state Idle;
    !Run -> Idle : /Stop;
}'''


def _forced(namespace):
    return [edge for edge in namespace.transitions if edge.is_forced]


def _writes(edge):
    return [(op.var_name, str(op.expr)) for op in edge.effects]


def test_a_declaration_on_a_composite_is_decided_where_the_machine_rests():
    model = load_state_machine_from_text(NESTED)
    assert model.forced_variables == ('__forced_0',)
    assert model.defines['__forced_0'].type == 'int'
    assert str(model.defines['__forced_0'].init) == '0'
    run = model.root_state.substates['Run']
    inner = run.substates['Inner']
    # The states that can be rested in keep the event and raise the variable.
    assert [edge.from_state for edge in _forced(inner)] == ['A', 'B']
    for edge in _forced(inner):
        assert edge.to_state is EXIT_STATE
        assert edge.event.path_name == 'Root.Stop' and edge.guard is None
        assert _writes(edge) == [('__forced_0', '1')]
    # A pseudo state is never rested in and holds nothing.
    assert not [edge for edge in inner.transitions if edge.from_state == 'Junction']
    # The composite on the way up only waits for the variable; the leaf beside
    # it starts the exit itself.
    relay, side = _forced(run)
    assert (relay.from_state, relay.event, str(relay.guard)) == ('Inner', None, '__forced_0 == 1')
    assert relay.to_state is EXIT_STATE and relay.effects == []
    assert (side.from_state, side.event.path_name, side.guard) == ('Side', 'Root.Stop', None)
    assert _writes(side) == [('__forced_0', '1')]
    # The level of the declaration takes the raised case first and lowers the
    # variable; the declared transition stays for an entry that has not settled.
    first, declared = [edge for edge in model.root_state.transitions if edge.from_state == 'Run']
    assert (first.to_state, first.event, str(first.guard)) == ('Idle', None, '__forced_0 == 1')
    assert _writes(first) == [('__forced_0', '0')]
    assert declared.event.path_name == 'Root.Stop' and declared.guard is None
    gate = model.root_state.substates[declared.to_state]
    assert gate.is_pseudo and gate.is_forced_gate
    hop, = [edge for edge in model.root_state.transitions if edge.from_state == gate.name]
    assert (hop.to_state, hop.event, str(hop.guard)) == ('Idle', None, '__forced_0 == 0')


def test_other_transitions_of_a_state_on_the_way_give_way_while_the_variable_is_raised():
    model = load_state_machine_from_text('''def int x = 1;
state Root {
    event Stop;
    event Go;
    [*] -> Run;
    state Run {
        [*] -> Inner;
        state Inner { [*] -> A; state A; }
        state Side;
        Inner -> Side : if [x > 5];
        Inner -> Side :: Go;
    }
    state Idle;
    !Run -> Idle : /Stop;
}''')
    run = model.root_state.substates['Run']
    relay, plain, evented = [edge for edge in run.transitions if edge.from_state == 'Inner']
    assert str(relay.guard) == '__forced_0 == 1'
    assert str(plain.guard) == 'x > 5 && __forced_0 == 0'
    gate = run.substates[evented.to_state]
    assert evented.guard is None and gate.is_forced_gate
    hop, = [edge for edge in run.transitions if edge.from_state == gate.name]
    assert (hop.to_state, str(hop.guard)) == ('Side', '__forced_0 == 0')
    # No transition ends up with an event and a guard together.
    for namespace in walk_namespaces(model.root_state):
        for edge in namespace.transitions:
            assert edge.event is None or edge.guard is None


@pytest.mark.parametrize('declaration', [
    '!A -> B :: Go;',
    '!* -> B :: Go;',
    '!Junction -> B : if [x > 0];',
])
def test_a_declaration_whose_sources_have_nothing_inside_stays_as_written(declaration):
    model = load_state_machine_from_text('''def int x = 0;
state Root {
    [*] -> A;
    state A;
    state B;
    pseudo state Junction;
    %s
}''' % declaration)
    # There is nothing below the source to leave first, so one transition per
    # source is the whole declaration: no variable, no relay, no gate.
    assert model.forced_variables == ()
    assert list(model.defines) == ['x']
    assert not [state for state in model.root_state.substates.values() if state.is_forced_gate]
    assert all(edge.effects == [] for edge in _forced(model.root_state))
    exported = str(model.to_ast_node())
    assert '__forced' not in exported
    assert str(load_state_machine_from_text(exported).to_ast_node()) == exported


def test_a_wildcard_declaration_only_lowers_the_sources_that_have_states_inside():
    model = load_state_machine_from_text('''state Root {
    event Reset;
    [*] -> Run;
    state Run { [*] -> A; state A; }
    state Leaf;
    state Home;
    Run -> Leaf :: Next;
    !* -> Home : /Reset;
}''')
    assert model.forced_variables == ('__forced_0',)
    root = model.root_state
    from_leaf, = [edge for edge in _forced(root) if edge.from_state == 'Leaf']
    # The leaf source keeps the declared transition untouched.
    assert (from_leaf.to_state, from_leaf.event.path_name, from_leaf.guard, from_leaf.effects) == (
        'Home', 'Root.Reset', None, [])
    from_home, = [edge for edge in _forced(root) if edge.from_state == 'Home']
    assert (from_home.to_state, from_home.guard, from_home.effects) == ('Home', None, [])
    # The composite source gets the two steps.
    first, declared = [edge for edge in _forced(root) if edge.from_state == 'Run']
    assert str(first.guard) == '__forced_0 == 1' and root.substates[declared.to_state].is_forced_gate


def test_hidden_variables_are_numbered_in_the_order_they_are_handed_out():
    model = load_state_machine_from_text('''state Root {
    event Go;
    [*] -> Leaf;
    state Leaf;
    state First { [*] -> A; state A; }
    state Second { [*] -> B; state B; }
    !Leaf -> First :: Go;
    !First -> Second :: Go;
    !Second -> Leaf :: Go;
}''')
    # The declaration on Leaf needs no variable and does not use up a number.
    assert model.forced_variables == ('__forced_0', '__forced_1')
    first = model.root_state.substates['First']
    second = model.root_state.substates['Second']
    assert [_writes(edge) for edge in _forced(first)] == [[('__forced_0', '1')]]
    assert [_writes(edge) for edge in _forced(second)] == [[('__forced_1', '1')]]
    assert [item['from_path'] for item in model.forced_transitions] == [
        'Root.Leaf', 'Root.First', 'Root.Second']


@pytest.mark.parametrize('taken', ['__forced_0', '_forced_0', '___forced_0'])
def test_a_name_the_user_wrote_is_skipped(taken):
    model = load_state_machine_from_text('''def int %s = 7;
state Root {
    [*] -> Run;
    state Run { [*] -> A; state A; }
    state Idle;
    !Run -> Idle : if [%s > 0];
}''' % (taken, taken))
    assert model.forced_variables == ('__forced_1',)
    assert str(model.defines[taken].init) == '7'


def test_the_machine_that_runs_is_exported_and_reloads_to_the_same_behaviour():
    model = load_state_machine_from_text(NESTED)
    exported = str(model.to_ast_node())
    assert 'def int __forced_0 = 0;' in exported
    assert 'pseudo state __forced_gate_0;' in exported
    # The exported text has no forced declaration left: it is the lowered machine.
    assert '!' not in exported
    reloaded = load_state_machine_from_text(exported)
    assert not reloaded.forced_transitions
    assert str(reloaded.to_ast_node()) == exported

    def trajectory(machine):
        runtime = SimulationRuntime(machine)
        seen = []
        for events in ([], [], ['Root.Stop'], [], ['Root.Stop']):
            result = runtime.cycle(events)
            seen.append((runtime.current_state.path, dict(runtime.vars), result.delta))
        return seen

    assert trajectory(model) == trajectory(reloaded)
    assert trajectory(model)[2][0] == ('Root', 'Idle')


def test_hidden_variables_are_lowered_again_wherever_the_machine_rests():
    model = load_state_machine_from_text('''def int n = 0;
state Root {
    event Stop;
    event Back;
    [*] -> Run;
    state Run {
        [*] -> Inner;
        state Inner { [*] -> A; state A { during { n = n + 1; } } }
    }
    state Idle;
    !Run -> Idle : /Stop;
    !* -> Run : /Back;
    !Run -> Idle : if [n >= 6];
}''')
    assert model.forced_variables == ('__forced_0', '__forced_1', '__forced_2')
    runtime = SimulationRuntime(model)
    visited = []
    for events in ([], ['Root.Stop'], ['Root.Back'], ['Root.Back'], [], [], [], [], ['Root.Back'], []):
        runtime.cycle(events)
        visited.append(runtime.current_state.path[-1])
        assert [runtime.vars[name] for name in model.forced_variables] == [0, 0, 0]
    # The third declaration reads what earlier cycles counted: n reaches 6 in
    # the seventh cycle and takes Run away in the eighth.
    assert visited == ['A', 'Idle', 'A', 'A', 'A', 'A', 'A', 'Idle', 'A', 'Idle']


@pytest.mark.parametrize('declaration,code,quoted', [
    ('!Run -> Idle : if [missing > 1];', 'E_UNDEFINED_VAR', '! Run -> Idle'),
    ('!Run -> Idle : /Nowhere.Stop;', 'E_MISSING_STATE', '! Run -> Idle'),
    ('!* -> Idle : if [missing > 1];', 'E_UNDEFINED_VAR', '! * -> Idle'),
])
def test_a_faulty_declaration_is_reported_once_where_it_is_written(declaration, code, quoted):
    program = parse_with_grammar_entry('''state Root {
    [*] -> Run;
    state Run {
        [*] -> Inner;
        state Inner { [*] -> A; state A; }
        state Side;
    }
    state Idle;
    %s
}''' % declaration, 'state_machine_dsl')
    _, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)
    # One mistake, one diagnostic: the copies carried down the tree stay quiet.
    assert [item.code for item in diagnostics] == [code]
    assert quoted in diagnostics[0].message


def test_drawings_and_inspect_show_the_declaration_on_every_state_below_its_source():
    model = load_state_machine_from_text(NESTED)
    drawing = model.to_plantuml('full')
    assert '__forced' not in drawing
    # One arrow per state the declaration applies to, the pseudo state included.
    stops = [line.strip() for line in drawing.splitlines() if line.strip().endswith(': /Stop')]
    assert sorted(line.split(' --> ')[0].rsplit('__', 1)[-1] for line in stops) == [
        'a', 'b', 'inner', 'junction', 'side']
    assert drawing.count('root__run --> root__idle') == 1
    snapshot = model.diagram().to_json()
    assert '__forced' not in snapshot
    report = inspect_model(model)
    assert '__forced' not in json.dumps(report.to_json())
    assert len(report.forced_transitions) == 1
    # One forced transition per state below Run, the pseudo state included,
    # and the declared one; the machine that runs has none on the pseudo state.
    assert sorted(item.from_path for item in report.transitions if item.is_forced) == [
        'Root.Run', 'Root.Run.Inner', 'Root.Run.Inner.A', 'Root.Run.Inner.B',
        'Root.Run.Inner.Junction', 'Root.Run.Side']


def test_a_state_is_shown_the_same_after_its_machine_is_no_longer_kept():
    kept = load_state_machine_from_text(NESTED)
    # Only the root state is kept here; the machine it came from is dropped.
    root = load_state_machine_from_text(NESTED).root_state
    gc.collect()
    for detail in ('minimal', 'normal', 'full'):
        drawing = root.to_plantuml(detail)
        assert drawing == kept.root_state.to_plantuml(detail)
        assert '__forced' not in drawing
    run = root.substates['Run']
    assert run.to_plantuml('full') == kept.root_state.substates['Run'].to_plantuml('full')
    assert '__forced' not in run.to_plantuml('full')
    assert str(root.to_ast_node()) == str(kept.root_state.to_ast_node())


def test_a_state_of_the_machine_is_exported_the_way_the_machine_is():
    model = load_state_machine_from_text(NESTED)
    run = model.root_state.substates['Run']
    assert '__forced_0 = 1;' in str(run.to_ast_node())
    assert '__forced' not in run.to_plantuml('full')
