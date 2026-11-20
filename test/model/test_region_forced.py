"""Forced transitions that reach regions, as the model exposes them."""

import pytest

from pyfcstm.diagnostics.inspect import inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import (
    PlantUMLOptions,
    load_state_machine_from_text,
    parse_dsl_node_to_state_machine,
)
from pyfcstm.model.forced import authored_guard, forced_flag_names, is_forced_carrier
from pyfcstm.simulate import SimulationRuntime
from test.testings.simulate_semantics import build_state_machine_from_case, iter_semantic_cases

pytestmark = pytest.mark.unittest

OWNER = '''state Root {
    event Stop;
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1; pseudo state Gate; state A2; A1 -> A2; }
        region B { [*] -> B1; state B1; }
    }
    state Idle;
    !Run -> Idle : /Stop;
}'''


def _guards(namespace, source):
    return [str(edge.guard) for edge in namespace.transitions if edge.from_state == source]


def test_a_declaration_that_reaches_regions_installs_one_hidden_variable():
    model = load_state_machine_from_text(OWNER)
    assert list(model.defines) == ['__forced_0']
    assert model.defines['__forced_0'].type == 'int'
    assert str(model.defines['__forced_0'].init) == '0'


def test_a_state_resting_in_a_region_raises_the_variable_and_pseudo_states_get_nothing():
    run = load_state_machine_from_text(OWNER).root_state.substates['Run']
    region = run.regions['A']
    exits = [edge for edge in region.transitions if edge.exit_group_levels]
    assert [(edge.from_state, edge.exit_group_levels) for edge in exits] == [('A1', 1), ('A2', 1)]
    for edge in exits:
        assert edge.is_forced and edge.event.path_name == 'Root.Stop'
        assert [(op.var_name, str(op.expr)) for op in edge.effects] == [('__forced_0', '1')]
    assert not [edge for edge in region.transitions if edge.from_state == 'Gate']


def test_the_declaring_level_decides_in_two_steps_and_keeps_the_declared_transition():
    root = load_state_machine_from_text(OWNER).root_state
    first, declared = [edge for edge in root.transitions if edge.from_state == 'Run']
    assert (first.event, str(first.guard)) == (None, '__forced_0 == 1')
    assert [(op.var_name, str(op.expr)) for op in first.effects] == [('__forced_0', '0')]
    # The declared transition keeps its event for the case that control comes
    # back without the variable raised, and gives way while it is raised.
    assert declared.event.path_name == 'Root.Stop'
    assert str(declared.guard) == '__forced_0 == 0'
    assert authored_guard(declared) is None
    assert declared.effects == []
    assert [is_forced_carrier(edge) for edge in (first, declared)] == [True, False]


def test_other_outgoing_transitions_give_way_while_the_variable_is_raised():
    model = load_state_machine_from_text('''def int x = 1;
state Root {
    event Alpha;
    event Beta;
    event Other;
    [*] -> P;
    state P {
        region A { [*] -> A1; state A1; }
        region B { [*] -> B1; state B1; }
    }
    state ToAlpha;
    state ToBeta;
    state Plain;
    state Evented;
    !P -> ToAlpha : /Alpha;
    !P -> ToBeta : /Beta;
    P -> Plain : if [x > 0];
    P -> Evented : /Other;
}''')
    assert sorted(model.defines) == ['__forced_0', '__forced_1', 'x']
    root = model.root_state
    plain = next(edge for edge in root.transitions if edge.to_state == 'Plain')
    evented = next(edge for edge in root.transitions if edge.to_state == 'Evented')
    # Both declarations ask the variable to be lowered, the first one outermost.
    assert str(plain.guard) == 'x > 0 && __forced_0 == 0 && __forced_1 == 0'
    assert evented.event.path_name == 'Root.Other'
    assert str(evented.guard) == '__forced_0 == 0 && __forced_1 == 0'
    # The transitions of one declaration give way to the other one as well, so
    # whichever declaration started the exit is the only one that goes on.
    alpha = [edge for edge in root.transitions if edge.to_state == 'ToAlpha']
    assert [str(edge.guard) for edge in alpha] == [
        '__forced_0 == 1 && __forced_1 == 0', '__forced_0 == 0 && __forced_1 == 0']
    beta = [edge for edge in root.transitions if edge.to_state == 'ToBeta']
    assert str(beta[0].guard).startswith('__forced_1 == 1')
    assert str(beta[1].guard) == '__forced_0 == 0 && __forced_1 == 0'
    assert sorted(forced_flag_names(root)) == ['__forced_0', '__forced_1']


def test_a_declaration_that_does_not_reach_regions_keeps_its_plain_expansion():
    model = load_state_machine_from_text('''state Root {
    event Stop;
    [*] -> Plain;
    state Plain {
        [*] -> A;
        state A;
        pseudo state Gate;
        state B;
        A -> B;
    }
    state Work {
        region R { [*] -> R1; state R1; }
    }
    state Idle;
    !Plain -> Idle : /Stop;
}''')
    assert not model.defines
    plain = model.root_state.substates['Plain']
    # The expansion lands on every state below, pseudo states included, and
    # repeats the event; nothing was added to the regions of Work.
    assert sorted(edge.from_state for edge in plain.transitions if edge.is_forced) == ['A', 'B', 'Gate']
    assert all(edge.event.path_name == 'Root.Stop' for edge in plain.transitions if edge.is_forced)
    work = model.root_state.substates['Work']
    assert not any(edge.is_forced for edge in work.regions['R'].transitions)


def test_a_declaration_below_regions_without_regions_in_its_scope_is_not_lowered():
    model = load_state_machine_from_text('''state Root {
    event Stop;
    [*] -> P;
    state P {
        region A {
            [*] -> Q;
            state Q { [*] -> Q1; state Q1; state Q2; Q1 -> Q2; }
            state Done;
            !Q -> Done : /Stop;
        }
        region B { [*] -> B1; state B1; }
    }
}''')
    assert not model.defines
    region = model.root_state.substates['P'].regions['A']
    q = region.substates['Q']
    assert sorted(edge.from_state for edge in q.transitions if edge.is_forced) == ['Q1', 'Q2']
    assert not any(edge.exit_group_levels for edge in q.transitions)


@pytest.mark.parametrize('taken', ['__forced_0', '_forced_0', '___forced_0'])
def test_a_variable_the_user_wrote_is_never_taken_for_the_hidden_one(taken):
    model = load_state_machine_from_text('def int %s = 5;\n%s' % (taken, OWNER))
    assert sorted(model.defines) == sorted([taken, '__forced_1'])
    assert str(model.root_state.substates['Run'].regions['A'].transitions[0].effects[0].var_name) == '__forced_1'


def test_forced_declarations_reach_each_owner_below_the_declared_state():
    model = load_state_machine_from_text('''state Root {
    event Halt;
    [*] -> Outer;
    state Outer {
        region R1 {
            [*] -> Inner;
            state Inner {
                region X { [*] -> X1; state X1; }
                region Y { [*] -> Y1; state Y1; }
            }
        }
        region R2 { [*] -> Z1; state Z1; }
    }
    state Off;
    !Outer -> Off : /Halt;
}''')
    outer = model.root_state.substates['Outer']
    inner = outer.regions['R1'].substates['Inner']
    # Every leaf of the outer owner names the outermost owner, whatever lies between.
    assert [(edge.from_state, edge.exit_group_levels) for edge in outer.regions['R2'].transitions
            if edge.exit_group_levels] == [('Z1', 1)]
    assert [(edge.from_state, edge.exit_group_levels) for region in inner.regions.values()
            for edge in region.transitions if edge.exit_group_levels] == [('X1', 2), ('Y1', 2)]
    # The composite-like owner Inner holds no transition of its own for the declaration.
    assert not [edge for edge in outer.regions['R1'].transitions if edge.is_forced]


def test_inspect_judges_the_model_as_written():
    report = inspect_model(load_state_machine_from_text(OWNER))
    assert '__forced' not in report.to_json()
    # The forced declaration is reported once, as written.
    assert len(report.forced_transitions) == 1
    # Only the transition written on the level of the declaration is expanded;
    # nothing is put into the regions.
    assert sum(item.is_forced for item in report.transitions) == 1


def test_plantuml_draws_the_declaration_once_and_hides_how_it_is_carried_out():
    model = load_state_machine_from_text('''def int x = 1;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1; }
        region B { [*] -> B1; state B1; }
    }
    state Idle;
    state Next;
    !Run -> Idle : /Stop;
    Run -> Next : if [x > 0];
}''')
    text = model.to_plantuml('full')
    assert '__forced' not in text
    assert text.count('root__run --> root__idle') == 1
    assert 'root__run --> root__next : x > 0' in text


def test_a_wildcard_declaration_keeps_the_transition_of_a_pseudo_sibling_on_its_own_level():
    model = load_state_machine_from_text('''state Root {
    event Stop;
    [*] -> Gate;
    pseudo state Gate;
    state Quiet;
    state Run {
        region A { [*] -> A1; state A1; pseudo state Pick; }
        region B { [*] -> B1; state B1; }
    }
    state Idle;
    Gate -> Run;
    !* -> Idle : /Stop;
}''')
    by_source = {}
    for edge in model.root_state.transitions:
        if edge.is_forced:
            by_source.setdefault(edge.from_state, []).append(edge)
    # On its own level every state, a pseudo one included, holds the declared
    # transition; only the state that owns regions needs the copy that decides.
    assert sorted(by_source) == ['Gate', 'Idle', 'Quiet', 'Run']
    assert [len(by_source[name]) for name in ('Gate', 'Idle', 'Quiet', 'Run')] == [1, 1, 1, 2]
    # Below the declaration a pseudo state is passed through, not left.
    region = model.root_state.substates['Run'].regions['A']
    assert [edge.from_state for edge in region.transitions if edge.is_forced] == ['A1']


def test_diagram_snapshot_shows_the_declaration_once_and_hides_how_it_is_carried_out():
    model = load_state_machine_from_text('''def int x = 1;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1; }
        region B { [*] -> B1; state B1; }
    }
    state Idle;
    state Next;
    !Run -> Idle : /Stop;
    Run -> Next : if [x > 0];
}''')
    snapshot = model.diagram().to_dict()

    def labels(node):
        found = [(item['label'], item['forced']) for item in node['transitions']]
        for child in node['children']:
            found.extend(labels(child))
        return found

    assert labels(snapshot['rootState']) == [
        ('Run -> Idle /Stop', True),
        ('[*] -> Run', False),
        ('Run -> Next if [x > 0]', False),
        ('[*] -> A1', False),
        ('[*] -> B1', False),
    ]
    assert [item['name'] for item in snapshot['variables']] == ['x']
    assert snapshot['summary']['transitions'] == 5
    assert snapshot['summary']['variables'] == 1
    # Stop is drawn on one transition, so it gets no legend entry and no colour.
    assert snapshot['eventLegend'] == []
    assert [item['eventColor'] for item in snapshot['rootState']['transitions']] == [None, None, None]
    assert '__forced' not in model.diagram().to_json()


EVENTED_NEIGHBOURS = '''state Root {
    [*] -> Run;
    state Run { region A { [*] -> A1; state A1; } }
    state Idle;
    state Off;
    state Next;
    !Run -> Idle :: Stop;
    !Run -> Off :: Kill;
    Run -> Next :: Go;
}'''


def test_transitions_that_give_way_export_with_the_guard_they_had():
    """An event transition that gives way has an event and a guard; the language cannot write both."""
    model = load_state_machine_from_text(EVENTED_NEIGHBOURS)
    go = next(edge for edge in model.root_state.transitions if edge.to_state == 'Next')
    assert go.event is not None and go.guard is not None
    assert str(go.to_ast_node()) == 'Run -> Next :: Go;'
    exported = str(model.to_ast_node())
    assert 'Run -> Idle :: Stop;' in exported and 'Run -> Off :: Kill;' in exported
    # Exporting what was exported gives the same text again.
    assert str(load_state_machine_from_text(exported).to_ast_node()) == exported
    drawing = model.to_plantuml('full')
    assert '__forced' not in drawing
    assert drawing.count('root__run --> root__next') == 1


def test_event_legend_counts_only_what_is_drawn():
    text = load_state_machine_from_text(OWNER).to_plantuml(
        PlantUMLOptions(event_visualization_mode='both'))
    assert '**Stop** (1 transitions)' in text
    # A single-use event stays uncoloured.
    assert not [line for line in text.splitlines() if '-[#' in line]


@pytest.mark.parametrize('block', [
    'enter { __forced_0 = 1; seen = __forced_0; }',
    'enter { if [seen == 0] { __forced_0 = 1; seen = __forced_0; } }',
])
def test_a_block_temporary_is_never_taken_for_the_hidden_variable(block):
    model = load_state_machine_from_text('''def int seen = 0;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        %s
        region A { [*] -> A1; state A1; A1 -> [*] :: Done; }
    }
    state Idle;
    state Next;
    !Run -> Idle : /Stop;
    Run -> Next;
}''' % block)
    assert sorted(forced_flag_names(model.root_state)) == ['__forced_1']
    runtime = SimulationRuntime(model)
    runtime.cycle()
    assert runtime.vars == {'seen': 1, '__forced_1': 0}
    # Stop was never given, so the ordinary transition of the owner is taken.
    runtime.cycle('Root.Run.A.A1.Done')
    assert str(runtime.configuration) == 'Root.Next'


@pytest.mark.parametrize('declaration,code', [
    ('!Run -> Idle : if [missing > 1];', 'E_UNDEFINED_VAR'),
    ('!Run -> Idle : /Nowhere.Stop;', 'E_MISSING_STATE'),
])
def test_a_faulty_declaration_is_reported_once_however_far_it_is_carried(declaration, code):
    program = parse_with_grammar_entry('''state Root {
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1; state A2; }
        region B { [*] -> B1; state B1; }
    }
    state Idle;
    %s
}''' % declaration, 'state_machine_dsl')
    _, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)
    assert [item.code for item in diagnostics] == [code]
    # The message quotes the declaration as written, not a carried copy of it.
    assert '! Run -> Idle' in diagnostics[0].message


def _region_cases():
    return [case for case in iter_semantic_cases() if 'regions' in case.data['categories']]


@pytest.mark.parametrize('case', _region_cases(), ids=lambda case: case.id)
def test_every_region_model_of_the_shared_corpus_exports(case):
    """Whatever the lowering puts into a model, the text exports must still work."""
    model = build_state_machine_from_case(case)
    drawing = model.to_plantuml('full')
    assert '__forced' not in drawing
    exported = str(model.to_ast_node())
    assert str(load_state_machine_from_text(exported).to_ast_node()) == exported
