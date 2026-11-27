"""A forced declaration is syntactic sugar: the analyzers judge it exactly like its expansion.

The expansion is the model that the declaring one exports as FCSTM text. Loaded
as an ordinary model it knows nothing about forced declarations, so any special
treatment of the declaring model by an analyzer would make the two differ. The
inspect report is the exception by design: it shows the declaration as written.
"""

import json

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.diagnostics.analyzers import collect_const_fold_warnings, collect_numeric_warnings
from pyfcstm.model import collect_event_transitions, load_state_machine_from_text

pytestmark = pytest.mark.unittest

MODELS = {
    'constant_guards': '''
state Root {
    [*] -> P;
    state P { [*] -> a; state a; }
    state Q;
    !P -> Q : if [1 > 2];
    Q -> P : if [2 > 1];
}
''',
    'division_in_the_guard': '''
def int x = 0;
state Root {
    [*] -> P;
    state P { [*] -> M; state M { [*] -> a; state a { during { x = x + 1; } } } }
    state Q;
    !P -> Q : if [x / 0 > 1];
    Q -> P : if [x > 1];
}
''',
    'event_on_a_nested_source': '''
state Root {
    event Stop;
    [*] -> Run;
    state Run { [*] -> Inner; state Inner { [*] -> A; state A; pseudo state J; } state Side; }
    state Idle;
    !Run -> Idle : /Stop;
}
''',
}


def _show(items):
    # Where in the source text something was written is a property of the text,
    # and the two texts differ, so spans are left out.
    return sorted(
        json.dumps([item.code, {key: str(value) for key, value in sorted(item.refs.items())
                                if not key.endswith('span')}])
        for item in items
    )


def _pair(source):
    declared = load_state_machine_from_text(source)
    assert declared.forced_variables == ('__forced_0',)
    return declared, load_state_machine_from_text(str(declared.to_ast_node()))


@pytest.mark.parametrize('name', sorted(MODELS))
def test_constant_folding_gives_the_declaration_the_answer_of_its_expansion(name):
    declared, expansion = _pair(MODELS[name])
    assert _show(collect_const_fold_warnings(declared)) == _show(collect_const_fold_warnings(expansion))


@pytest.mark.parametrize('name', sorted(MODELS))
def test_numeric_findings_give_the_declaration_the_answer_of_its_expansion(name):
    declared, expansion = _pair(MODELS[name])
    found = _show(collect_numeric_warnings(declared))
    assert found == _show(collect_numeric_warnings(expansion))
    if name == 'division_in_the_guard':
        assert found, 'the model is built to give a finding'


@pytest.mark.parametrize('name', sorted(MODELS))
def test_the_transitions_listed_per_event_are_those_of_the_expansion(name):
    declared, expansion = _pair(MODELS[name])

    def listed(machine):
        return sorted(
            (event, sorted(('.'.join(owner.path), str(edge.from_state), str(edge.to_state))
                           for owner, edge in pairs))
            for event, pairs in collect_event_transitions(machine).items()
        )

    assert listed(declared) == listed(expansion)


def test_the_inspect_report_shows_the_declaration_as_written():
    report = inspect_model(load_state_machine_from_text(MODELS['event_on_a_nested_source']))
    assert len(report.forced_transitions) == 1
    assert '__forced' not in json.dumps(report.to_json())
    # One transition per state below the source, pseudo state included.
    assert sorted(item.from_path for item in report.transitions if item.is_forced) == [
        'Root.Run', 'Root.Run.Inner', 'Root.Run.Inner.A', 'Root.Run.Inner.J', 'Root.Run.Side']
