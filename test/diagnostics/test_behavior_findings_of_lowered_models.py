"""The findings of the verify pipeline are those of the machine that runs.

History, ``active()`` and forced declarations are lowered into plain FCSTM, and
the text a model exports is that plain FCSTM. A finding that says how a machine
behaves must not depend on whether the model or its text is inspected, so the
verify pipeline judges the machine that runs; everything else is judged on the
model as written (see ``BEHAVIOR_DIAGNOSTIC_CODES``).
"""

import json

import pytest

from pyfcstm.diagnostics.inspect import BEHAVIOR_DIAGNOSTIC_CODES, inspect_model
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

STRUCTURAL = {'enable_verify': True}
SMT = {
    'enable_verify': True,
    'max_complexity_tier': 'smt_nonlinear_decidable',
    'smt_timeout_ms': 5000,
}

MODELS = {
    'forced_over_a_composite': '''def int n = 0;
state Root {
    event Stop;
    [*] -> P;
    state P {
        [*] -> A;
        state A { during { n = n + 1; } }
        state B;
        A -> B : if [n >= 2];
    }
    state Off;
    !P -> Off : /Stop;
}''',
    'forced_with_a_guard_that_is_never_true': '''def int x = 0;
state Root {
    [*] -> P;
    state P { [*] -> A; state A; state B; A -> B; }
    state Off;
    !P -> Off : if [x > 0 && x < 0];
}''',
    'active_condition': '''def int n = 0;
state Root {
    [*] -> A;
    state A { during { n = n + 1; } }
    state B;
    state C;
    A -> B : if [n >= 2];
    B -> C : if [active("Root.B")];
}''',
    'history_and_forced': '''state Root {
    event Pause;
    event Resume;
    event Next;
    [*] -> Work;
    state Work {
        [*] -> A;
        [H] -> A;
        state A;
        state B;
        A -> B : /Next;
        A -> [*] : /Pause;
        B -> [*] : /Pause;
    }
    state Paused;
    Work -> Paused;
    Paused -> Work.[H] : /Resume;
}''',
    'active_condition_inside_its_own_state': '''def int n = 0;
state Root {
    [*] -> A;
    state A { during { if [active("Root.A")] { n = n + 1; } } }
}''',
    'forced_loop_through_a_gate': '''state Root {
    event e;
    [*] -> a;
    state a { [*] -> x; state x; }
    state b;
    !a -> b :: e;
    b -> a;
}''',
    'forced_inside_an_owner_of_regions': '''def int seq = 0;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1 { exit { seq = seq * 10 + 1; } } }
        region B { [*] -> B1; state B1 { exit { seq = seq * 10 + 2; } } }
    }
    state Idle;
    !Run -> Idle : /Stop;
}''',
}


def _behavior(report):
    """The findings of the verify pipeline, without where they sit in the text."""
    found = []
    for item in report.diagnostics:
        if item.code not in BEHAVIOR_DIAGNOSTIC_CODES:
            continue
        refs = {
            key: value for key, value in item.refs.items()
            if key != 'source_path' and 'span' not in key
        }
        found.append((item.code, item.message, json.dumps(refs, sort_keys=True, default=str)))
    return sorted(found)


@pytest.mark.parametrize('options', [STRUCTURAL, SMT], ids=['structural', 'smt'])
@pytest.mark.parametrize('name', sorted(MODELS))
def test_a_model_and_the_text_it_exports_have_the_same_behavior_findings(name, options):
    model = load_state_machine_from_text(MODELS[name])
    exported = load_state_machine_from_text(str(model.to_ast_node()))
    assert _behavior(inspect_model(model, **options)) == _behavior(inspect_model(exported, **options))


@pytest.mark.parametrize('name', sorted(MODELS))
def test_without_the_verify_run_nothing_is_judged_on_the_lowered_machine(name):
    model = load_state_machine_from_text(MODELS[name])
    report = inspect_model(model)
    assert not [item for item in report.diagnostics if item.code in BEHAVIOR_DIAGNOSTIC_CODES]
    assert '__forced' not in json.dumps(report.to_json())
    assert '__active' not in json.dumps(report.to_json())


def test_the_findings_do_come_from_the_machine_that_runs():
    """A forced declaration over a composite is lowered into a relay whose effect
    lowers the hidden variable its own guard reads, which the verify pipeline
    reports; a model written without the declaration has no such finding."""
    model = load_state_machine_from_text(MODELS['forced_over_a_composite'])
    report = inspect_model(model, **SMT)
    behaviors = [item for item in report.diagnostics if item.code == 'I_EFFECT_GUARD_CONTRADICT']
    assert behaviors and any('__forced_0' in json.dumps(item.refs) for item in behaviors)
    plain = inspect_model(
        load_state_machine_from_text(
            MODELS['forced_over_a_composite'].replace('    !P -> Off : /Stop;\n', '')
        ),
        **SMT,
    )
    assert not [item for item in plain.diagnostics if item.code == 'I_EFFECT_GUARD_CONTRADICT']


def test_a_declaration_is_judged_on_the_model_as_written():
    """``W_FORCED_GUARD_UNSAT`` judges the declaration, which the machine that
    runs no longer carries, so it comes from the model as written."""
    model = load_state_machine_from_text('''def int x = 0;
state Root {
    [*] -> A;
    state A;
    state B;
    !A -> B : if [x > 0];
}''')
    report = inspect_model(model, **SMT)
    assert 'W_FORCED_GUARD_UNSAT' not in BEHAVIOR_DIAGNOSTIC_CODES
    assert 'W_FORCED_GUARD_UNSAT' in {item.code for item in report.diagnostics}
    # The verification report says the same: the algorithm ran on the model as
    # written, where the declaration still is a declaration.
    algorithms = {item.algorithm_name: item for item in report.verification.algorithms}
    assert algorithms['forced_guard_unsat_under_init'].result_kind == 'unsat'
