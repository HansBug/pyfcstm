"""Trace construction retains readable identities independently of SMT spelling."""

import pytest
import z3

from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint, normalized_fact_for
from pyfcstm.bmc.relation import BmcSymbolSource
from pyfcstm.solver.symbols import SymbolNames
from pyfcstm.bmc.infeasibility import build_core_item
from pyfcstm.bmc.explanation import explanation_text_lines

pytestmark = pytest.mark.unittest


def test_public_modulo_conflict_displays_formulas_without_claiming_a_derivation(text_aligner):
    name = 'generated_payload_long_identifier_abcdef'
    model = load_state_machine_from_text(
        'def int %s = 0; def int divisor = 2; state Root;' % name
    )
    query = '''
init cold havoc { %s };
assume at 0: %s %% divisor > 0;
assume at 0: %s %% divisor <= 0;
check invariant <= 1: divisor > 0;
''' % (name, name, name)
    result = solve_bmc_property(
        compile_bmc_query(model, query), infeasibility_explanation='formal'
    )
    explanation = result.feasibility.explanation
    assert explanation.core.subset_minimality == 'proven'
    assert explanation.narrative.derivation_status == 'structural_only'
    readings = [item.human_text for item in explanation.core.items]
    assert set(readings) == {'0 < v0@0%divisor@0', '0 >= v0@0%divisor@0'}
    text_aligner.assert_equal(expect="""
Explanation: PARTIAL FORMAL DOMAIN EXPLANATION
Classification: the assumptions are internally inconsistent
Variable names (@N denotes the value at frame N):
  v0 = generated_payload_long_identifier_abcdef

Why no execution exists:
  1. The listed source groups are jointly unsatisfiable in assumptions_component. A more specific value/state derivation is not available for this expression shape.
Derivation: STRUCTURAL ONLY

Conflict constraints:
  1. fbmcq assumption constraint (source location unavailable)
     0 < v0@0%divisor@0
  2. fbmcq assumption constraint (source location unavailable)
     0 >= v0@0%divisor@0

The displayed core is sufficient for UNSAT and proven subset-minimal.
Core scope: assumptions_component
Reduction: subset_minimal
Reason: subset-minimal source core published with a structural_only derivation
""".strip(), actual='\n'.join(explanation_text_lines(explanation)))
    assert result.property_satisfied is None


def test_core_formula_display_does_not_require_arithmetic_fact_recognition():
    names = SymbolNames()
    payload, limit = z3.Ints('generated_payload generated_limit')
    names.register(payload, 'v0@3', BmcSymbolSource('variable', 'payload', frame=3))
    names.register(limit, 'v1@3', BmcSymbolSource('variable', 'limit', frame=3))
    expression = z3.If(payload > limit, payload % limit, payload ** 2) > 0
    group = BmcTrackedConstraint('guard', 'assumptions', 'assumption.frame',
                                 (expression,), BmcSourceRef('generated', None, None),
                                 refs={'frame': 3})
    item = build_core_item(group, symbol_names=names)
    assert item.normalized_fact['kind'] == 'structural_constraint'
    assert item.human_text == 'If(v0@3 > v1@3, ToReal(v0@3%v1@3), v0@3**2) > 0'


@pytest.mark.parametrize('category,refs,expected', [
    ('assumption.frame', {'frame': 3}, 'variable_comparison'),
    ('initial.target', {'frame': 3}, 'state_membership'),
    ('assumption.event', {'step': 3}, 'proposition'),
    ('transition.step', {'step': 3}, 'transition_case'),
])
def test_normalization_uses_registered_identity_with_opaque_symbol_names(category, refs, expected):
    names = SymbolNames()
    value, following, state = z3.Ints('opaque_a opaque_b opaque_c')
    event = z3.Bool('opaque_d')
    names.register(value, 'v0@3', BmcSymbolSource('variable', 'payload', frame=3))
    names.register(following, 'v0@4', BmcSymbolSource('variable', 'payload', frame=4))
    names.register(state, 'state[3]', BmcSymbolSource('state', 'state', frame=3))
    names.register(event, 'event[0]@3', BmcSymbolSource('event', 'Root.tick', step=3))
    expressions = {
        'assumption.frame': value > 0,
        'initial.target': state == 1,
        'assumption.event': event,
        'transition.step': z3.Implies(z3.And(state == 1, event), following == value / 2),
    }
    stage = {'initial.target': 'initialization', 'transition.step': 'kernel'}.get(category, 'assumptions')
    group = BmcTrackedConstraint('source', stage, category,
                                 (expressions[category],),
                                 BmcSourceRef('generated', None, None), refs=refs)
    fact = normalized_fact_for(group, symbol_names=names)
    assert fact['kind'] == expected
    if expected in ('variable_comparison', 'transition_case'):
        assert fact['variable'] == 'payload'
    if expected == 'proposition':
        assert fact['identity'] == 'Root.tick@3'
    if expected == 'transition_case':
        assert fact['condition'][1]['identity'] == 'Root.tick@3'
        assert fact['target_frame'] == 4


def test_long_variable_keeps_short_identity_and_frame_from_construction():
    name = 'generated_controller_payload_1234567890_abcdef'
    model = load_state_machine_from_text('def int %s = 0; state Root;' % name)
    formula = compile_bmc_query(model, 'check invariant <= 2: %s >= 0;' % name)
    symbols = formula.core.symbols
    entry = symbols.names.lookup(symbols.frame_var(1, name))
    assert entry.display == 'v0@1'
    assert entry.source.name == name
    assert entry.source.frame == 1
    assert entry.source.kind == 'variable'
    assert symbols.names.render(symbols.frame_var(1, name) + 2) == 'v0@1 + 2'
    state = symbols.names.lookup(symbols.frame_state(2))
    assert state.source.kind == 'state'
    assert state.source.frame == 2


def test_authored_name_matching_generated_alias_keeps_distinct_identities():
    long_name = 'generated_controller_payload_1234567890_abcdef'
    model = load_state_machine_from_text(
        'def int %s = 0; def int v0 = 1; state Root;' % long_name
    )
    symbols = compile_bmc_query(model, 'check invariant <= 1: v0 >= 0;').core.symbols
    long_entry = symbols.names.lookup(symbols.frame_var(0, long_name))
    short_entry = symbols.names.lookup(symbols.frame_var(0, 'v0'))
    assert long_entry.display == 'v0@0'
    assert short_entry.display == 'v1@0'
    assert long_entry.source.name == long_name
    assert short_entry.source.name == 'v0'


def test_empty_registry_never_recovers_identity_from_encoded_spelling():
    from pyfcstm.bmc.infeasibility import _binding_symbols

    names = SymbolNames()
    event = z3.Bool('E_0_event_0_tick_opaque')
    group = BmcTrackedConstraint('event', 'assumptions', 'assumption.event',
                                 (event,), BmcSourceRef('generated', None, None))
    assert normalized_fact_for(group, symbol_names=names)['kind'] == 'structural_constraint'
    assert _binding_symbols(event, symbol_names=names) == {}


def test_legacy_binding_lookup_agrees_with_registered_compiled_variable():
    from pyfcstm.bmc.infeasibility import _binding_symbol

    model = load_state_machine_from_text('def int x = 0; state Root;')
    core = compile_bmc_query(model, 'check invariant <= 1: x >= 0;').core
    symbol = core.symbols.frame_var(0, 'x')
    fact = dict(kind='variable_equality', variable='x', frame=0, value=1)
    assert _binding_symbol(symbol == 1, fact, ('x',)).eq(symbol)
    assert _binding_symbol(symbol == 1, fact, symbol_names=core.symbols.names).eq(symbol)


def test_formula_renderer_does_not_invent_an_encoding_for_unsupported_proof_fact():
    from pyfcstm.bmc.infeasibility import _proof_formula_renderer

    model = load_state_machine_from_text('def int x = 0; state Root;')
    core = compile_bmc_query(model, 'check invariant <= 1: x >= 0;').core
    render = _proof_formula_renderer(core, {})
    fact = dict(kind='arithmetic_expression', variable='x', frame=0,
                target_frame=1, operator='mod', operand=2)
    assert render(fact, (), 'derived') is None


def test_compound_assignment_operand_stays_an_original_formula_without_reduced_fact(text_aligner):
    model = load_state_machine_from_text('''
def int x = 0; def int y = 0;
state Root { state A; [*] -> A; A -> A effect { x = x + (y + 1); }; }
''')
    core = compile_bmc_query(model, 'check invariant <= 2: x >= 0;').core
    groups = [group for group in core._tracked_groups
              if group.category == 'transition.step' and group.refs.get('step') == 1]
    item = build_core_item(groups[0], symbol_names=core.symbols.names)
    assert item.normalized_fact['kind'] == 'structural_constraint'
    text_aligner.assert_equal(expect="""
And(And(case[0]@1 == And(-3 == state[1], True),
        Implies(And(-3 == state[1], True),
                And(1 == state[2], x@2 == x@1, y@2 == y@1))),
    And(case[1]@1 ==
        And(-3 == state[1], Not(And(-3 == state[1], True))),
        Implies(And(-3 == state[1],
                    Not(And(-3 == state[1], True))),
                And(-3 == state[2], x@2 == x@1, y@2 == y@1))),
    And(case[2]@1 == And(-1 == state[1], True),
        Implies(And(-1 == state[1], True),
                And(-1 == state[2], x@2 == x@1, y@2 == y@1))),
    And(case[3]@1 ==
        And(1 == state[1], Not(And(1 == state[1], True))),
        Implies(And(1 == state[1],
                    Not(And(1 == state[1], True))),
                And(1 == state[2], x@2 == x@1, y@2 == y@1))),
    And(case[4]@1 == And(1 == state[1], True),
        Implies(And(1 == state[1], True),
                And(1 == state[2],
                    x@2 == x@1 + y@1 + 1,
                    y@2 == y@1))),
    delta[1] ==
    And(-3 == state[1], Not(And(-3 == state[1], True))),
    fallback[1] ==
    And(1 == state[1], Not(And(1 == state[1], True))),
    Not(And(delta[1], fallback[1])))
""".strip(), actual=item.human_text)


def test_proof_output_uses_registered_alias_and_retains_original_facts(text_aligner):
    name = 'generated_controller_payload_1234567890_abcdef'
    model = load_state_machine_from_text('''
def int %s = 8;
state Root { state A; state B; [*] -> A;
    A -> A effect { %s = %s / 2; }; A -> B;
}
''' % (name, name, name))
    result = solve_bmc_property(compile_bmc_query(model, '''
assume at 1: %s == 8;
assume at 2: %s == 99;
check reach <= 3: active("Root.A");
''' % (name, name)), infeasibility_explanation='proof')
    explanation = result.feasibility.explanation
    assert explanation.achieved_mode == 'proof'
    steps = '\n'.join(step.text for step in explanation.narrative.reasoning_steps)
    text_aligner.assert_equal(expect="""
8 == v0@1
Implies(And(1 == state[1], True), v0@2 == v0@1/2)
99 == v0@2
Therefore v0@2 == v0@1/2.
Therefore v0@2 == v0@1/2.
Starting from that value, the step therefore leaves v0 equal to 4 at frame 2.
Therefore one value cannot be two things at once. No execution satisfies these initialization requirements, transition requirements, and query requirements, and the property was not evaluated.
""".strip(), actual=steps)
    assert any(node.conclusion.get('variable') == name for node in explanation.proof.nodes)
    text_aligner.assert_equal(expect="""
8 == v0@1
99 == v0@2
Implies(And(1 == state[1], True), v0@2 == v0@1/2)
v0@2 == v0@1/2
v0@2 == v0@1/2
At frame 2, v0 must equal 4.
These requirements cannot all hold.
""".strip(), actual='\n'.join(node.human_text for node in explanation.proof.nodes))
    text_aligner.assert_equal(
        expect='Variable names (@N denotes the value at frame N):\n  v0 = %s' % name,
        actual='\n'.join(explanation_text_lines(explanation)[2:4]),
    )
