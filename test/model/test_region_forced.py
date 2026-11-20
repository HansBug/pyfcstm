"""Forced transitions that reach regions, as the model exposes them."""

import dataclasses

import pytest

from pyfcstm.diagnostics.inspect import inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import (
    PlantUMLOptions,
    load_state_machine_from_text,
    parse_dsl_node_to_state_machine,
)
from pyfcstm.model.region import walk_namespaces
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
    # back without the variable raised. While the variable is raised it gives
    # way: its event leads to a gate that only opens once the variable is lowered.
    assert declared.event.path_name == 'Root.Stop' and declared.guard is None
    assert declared.effects == []
    gate = root.substates[declared.to_state]
    assert gate.is_pseudo and gate.is_forced_gate and gate.name == '__forced_gate_0'
    hop, = [edge for edge in root.transitions if edge.from_state == gate.name]
    assert (hop.to_state, hop.event, str(hop.guard)) == ('Idle', None, '__forced_0 == 0')


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

    def into(target):
        return [edge for edge in root.transitions if edge.to_state == target]

    def through_gate(event_path):
        first = next(edge for edge in root.transitions
                     if edge.event is not None and edge.event.path_name == event_path)
        assert first.guard is None and root.substates[first.to_state].is_forced_gate
        return next(edge for edge in root.transitions if edge.from_state == first.to_state)

    # A transition without an event simply gets the extra conditions, the
    # first declaration outermost.
    plain, = into('Plain')
    assert str(plain.guard) == 'x > 0 && __forced_0 == 0 && __forced_1 == 0'
    # A transition with an event keeps the event and reaches its target through
    # a gate that asks every variable to be lowered.
    assert str(through_gate('Root.Other').guard) == '__forced_0 == 0 && __forced_1 == 0'
    assert through_gate('Root.Other').to_state == 'Evented'
    # The two declarations give way to each other in the same way, so whichever
    # one started the exit is the only one that goes on.
    relay_alpha, hop_alpha = into('ToAlpha')
    relay_beta, hop_beta = into('ToBeta')
    assert str(relay_alpha.guard) == '__forced_0 == 1 && __forced_1 == 0'
    assert str(relay_beta.guard) == '__forced_1 == 1 && __forced_0 == 0'
    assert str(hop_alpha.guard) == str(hop_beta.guard) == '__forced_0 == 0 && __forced_1 == 0'
    assert hop_alpha is through_gate('Root.Alpha') and hop_beta is through_gate('Root.Beta')


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
    # repeats the event.
    assert sorted(edge.from_state for edge in plain.transitions if edge.is_forced) == ['A', 'B', 'Gate']
    assert all(edge.event.path_name == 'Root.Stop' for edge in plain.transitions if edge.is_forced)
    # A declaration that does not reach regions is not lowered, so the model
    # carries no hidden variable.
    assert not model.defines


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


def test_an_event_transition_gives_way_through_a_gate_and_the_machine_exports_the_plain_expansion():
    model = load_state_machine_from_text(EVENTED_NEIGHBOURS)
    root = model.root_state
    go = next(edge for edge in root.transitions
              if edge.event is not None and edge.event.name == 'Go')
    gate = root.substates[go.to_state]
    assert go.guard is None and gate.is_forced_gate
    # Each of the three transitions of the model is something the language can write.
    assert str(go.to_ast_node()) == 'Run -> %s :: Go;' % gate.name
    exported = str(model.to_ast_node())
    assert 'Run -> Idle :: Stop;' in exported and 'Run -> Off :: Kill;' in exported
    # Exporting what was exported gives the same text again.
    assert str(load_state_machine_from_text(exported).to_ast_node()) == exported
    drawing = model.to_plantuml('full')
    assert '__forced' not in drawing
    assert drawing.count('root__run --> root__next') == 1


def _region_cases():
    return [case for case in iter_semantic_cases() if 'regions' in case.data['categories']]


def _transitions(model):
    for namespace in walk_namespaces(model.root_state):
        for edge in namespace.transitions:
            yield namespace, edge


@pytest.mark.parametrize('case', _region_cases(), ids=lambda case: case.id)
def test_no_transition_carries_an_event_and_a_guard(case):
    """The model keeps the rule of the language whatever a forced declaration lowers into."""
    model = build_state_machine_from_case(case)
    for _, edge in _transitions(model):
        assert edge.event is None or edge.guard is None
        # A transition that follows the rule can be copied like any dataclass.
        assert dataclasses.replace(edge).to_state == edge.to_state


def test_a_transition_through_a_gate_behaves_like_the_transition_as_written():
    model = load_state_machine_from_text('''def int x = 0;
def int seen = 0;
state Root {
    [*] -> Run;
    state Run {
        exit { seen = seen * 10 + 1; }
        region A { [*] -> A1; state A1; A1 -> [*] :: Done; }
    }
    state Idle;
    state Next { enter { seen = seen * 10 + 3; } }
    !Run -> Idle :: Stop;
    Run -> Next :: Go effect { x = x + 1; seen = seen * 10 + 2; }
}''')
    runtime = SimulationRuntime(model)
    runtime.cycle()
    # Go alone does nothing while the region works.
    runtime.cycle('Root.Run.Go')
    assert str(runtime.configuration) == 'Root.Run{A: A1}'
    # Once the region is done the transition is taken: exit, effect, enter,
    # the effect exactly once.
    result = runtime.cycle(['Root.Run.Go', 'Root.Run.A.A1.Done'], trace=True)
    assert str(runtime.configuration) == 'Root.Next'
    assert (runtime.vars['x'], runtime.vars['seen']) == (1, 123)
    assert result.consumed_events == ('Root.Run.A.A1.Done', 'Root.Run.Go')
    entered = [entry.state_path[-1] for entry in result.trace if entry.kind == 'state_enter']
    # The trace shows the gate as one more state passed through.
    go = next(edge for edge in model.root_state.transitions
              if edge.event is not None and edge.event.name == 'Go')
    assert model.root_state.substates[go.to_state].is_forced_gate
    assert entered == [go.to_state, 'Next']


def test_a_gate_shows_itself():
    """A gate exists only in the machine that runs, so it has nothing to stand in for it."""
    model = load_state_machine_from_text(EVENTED_NEIGHBOURS)
    gate = next(state for state in model.root_state.substates.values() if state.is_forced_gate)
    assert str(gate.to_ast_node()) == 'pseudo state %s;' % gate.name
    assert gate.name in gate.to_plantuml('full')
    # The machine itself is shown without it.
    assert '__forced' not in model.to_plantuml('full')
    assert '__forced' not in str(model.to_ast_node())


def test_a_state_the_user_named_like_a_gate_is_left_alone():
    model = load_state_machine_from_text('''state Root {
    [*] -> Run;
    state Run { region A { [*] -> A1; state A1; A1 -> [*] :: Done; } }
    state Idle;
    pseudo state __forced_gate_0;
    __forced_gate_0 -> Idle;
    !Run -> Idle :: Stop;
    Run -> __forced_gate_0 :: Go;
}''')
    root = model.root_state
    gates = sorted(state.name for state in root.substates.values() if state.is_forced_gate)
    assert gates == ['__forced_gate_1', '__forced_gate_2']
    assert not root.substates['__forced_gate_0'].is_forced_gate
    runtime = SimulationRuntime(model)
    runtime.cycle()
    runtime.cycle(['Root.Run.Go', 'Root.Run.A.A1.Done'])
    assert str(runtime.configuration) == 'Root.Idle'


COMPOSITE_OVER_OWNER = '''state Root {
    event Stop;
    [*] -> S;
    state S {
        [*] -> L;
        state L;
        state O { region A { [*] -> A1; state A1; } }
        L -> O :: Go;
    }
    state Idle;
    !S -> Idle : /Stop;
}'''

TWO_DECLARATIONS = '''state Root {
    event Stop;
    event Halt;
    [*] -> S;
    state S {
        [*] -> O;
        state O { region A { [*] -> A1; state A1; A1 -> [*] :: Done; } }
    }
    state Idle;
    state Other;
    !S -> Idle : /Stop;
    !S -> Idle : /Halt;
    S -> Other;
}'''


def test_a_declaration_on_a_composite_above_an_owner_is_drawn_like_any_other_expansion():
    """The states outside regions keep the copies the plain expansion puts on them."""
    model = load_state_machine_from_text(COMPOSITE_OVER_OWNER)
    drawing = model.to_plantuml('full')
    assert '__forced' not in drawing
    for source in ('root__s__l', 'root__s__o'):
        assert '%s --> [*] : /Stop' % source in drawing
    assert 'root__s --> root__idle : Stop' in drawing
    snapshot = model.diagram().to_dict()
    # The same count as the structural analysis, which judges the model as written.
    assert snapshot['summary']['transitions'] == len(inspect_model(model).transitions) == 7
    assert [(item['label'], item['transitionCount']) for item in snapshot['eventLegend']] == [('Stop', 3)]
    assert '__forced' not in model.diagram().to_json()


def test_two_declarations_on_one_state_export_without_hidden_names_and_without_unguarded_relays():
    model = load_state_machine_from_text(TWO_DECLARATIONS)
    exported = str(model.to_ast_node())
    assert '__forced' not in exported
    assert 'O -> [*] : /Stop;' in exported and 'O -> [*] : /Halt;' in exported
    # The relays of the lowered machine are never exported, and the text
    # exports the same way again.
    assert 'O -> [*];' not in exported
    assert str(load_state_machine_from_text(exported).to_ast_node()) == exported
    assert '__forced' not in model.to_plantuml('full')


def test_states_and_regions_export_like_the_machine_they_belong_to():
    model = load_state_machine_from_text(TWO_DECLARATIONS)
    root = model.root_state
    owner = root.substates['S'].substates['O']
    region = owner.regions['A']
    leaf = region.substates['A1']
    for namespace in (root, root.substates['S'], owner, region, leaf):
        assert '__forced' not in str(namespace.to_ast_node())
        assert '__forced' not in namespace.to_plantuml('full')
    assert str(model.to_ast_node()).count('region A {') == str(owner.to_ast_node()).count('region A {') == 1
    # Each level is the matching part of the machine export, line for line.
    machine_lines = [line.strip() for line in str(model.to_ast_node()).splitlines()]
    for namespace in (owner, region, leaf):
        assert {line.strip() for line in str(namespace.to_ast_node()).splitlines()} <= set(machine_lines)
    # The machine itself keeps what the simulator runs on.
    assert sorted(model.defines) == ['__forced_0', '__forced_1']
    assert any(edge.guard is not None for edge in root.substates['S'].transitions)


def test_what_is_shown_is_built_once_and_a_machine_without_lowered_declarations_shows_itself():
    model = load_state_machine_from_text(OWNER)
    assert model.to_plantuml('full') == model.to_plantuml('full')
    assert str(model.to_ast_node()) == str(model.to_ast_node())
    plain = load_state_machine_from_text('state Root { [*] -> A; state A; state B; A -> B; }')
    assert 'A -> B;' in str(plain.to_ast_node())
    assert 'root__a --> root__b' in plain.to_plantuml('full')


def test_event_legend_counts_only_what_is_drawn():
    text = load_state_machine_from_text(OWNER).to_plantuml(
        PlantUMLOptions(event_visualization_mode='both'))
    assert '**Stop** (1 transitions)' in text
    # A single-use event stays uncoloured.
    assert not [line for line in text.splitlines() if '-[#' in line]


@pytest.mark.parametrize('entry,block', [
    ('[*] -> Run;', 'enter { __forced_0 = 1; seen = __forced_0; }'),
    ('[*] -> Run;', 'enter { if [seen == 0] { __forced_0 = 1; seen = __forced_0; } }'),
    ('[*] -> Run effect { __forced_0 = 1; seen = __forced_0; }', ''),
])
def test_a_block_temporary_is_never_taken_for_the_hidden_variable(entry, block):
    model = load_state_machine_from_text('''def int seen = 0;
state Root {
    event Stop;
    %s
    state Run {
        %s
        region A { [*] -> A1; state A1; A1 -> [*] :: Done; }
    }
    state Idle;
    state Next;
    !Run -> Idle : /Stop;
    Run -> Next;
}''' % (entry, block))
    assert sorted(model.defines) == ['__forced_1', 'seen']
    runtime = SimulationRuntime(model)
    runtime.cycle()
    assert runtime.vars == {'seen': 1, '__forced_1': 0}
    # Stop was never given, so the ordinary transition of the owner is taken.
    runtime.cycle('Root.Run.A.A1.Done')
    assert str(runtime.configuration) == 'Root.Next'


def test_two_declarations_never_share_a_hidden_variable():
    model = load_state_machine_from_text('''def int __forced_0 = 5;
state Root {
    event Alpha;
    event Beta;
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1; }
        region B { [*] -> B1; state B1; }
    }
    state ToAlpha;
    state ToBeta;
    !Run -> ToAlpha : /Alpha;
    !Run -> ToBeta : /Beta;
}''')
    # The name of the first declaration is taken by a variable of the user, so
    # it moves on to the next one; the second declaration must not land there.
    assert sorted(model.defines) == ['__forced_0', '__forced_1', '__forced_2']
    runtime = SimulationRuntime(model)
    runtime.cycle()
    runtime.cycle('Root.Beta')
    assert str(runtime.configuration) == 'Root.ToBeta'
    assert runtime.vars == {'__forced_0': 5, '__forced_1': 0, '__forced_2': 0}


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


@pytest.mark.parametrize('case', _region_cases(), ids=lambda case: case.id)
def test_every_region_model_of_the_shared_corpus_exports(case):
    """Whatever the lowering puts into a model, the text exports must still work."""
    model = build_state_machine_from_case(case)
    drawing = model.to_plantuml('full')
    assert '__forced' not in drawing
    exported = str(model.to_ast_node())
    assert str(load_state_machine_from_text(exported).to_ast_node()) == exported
