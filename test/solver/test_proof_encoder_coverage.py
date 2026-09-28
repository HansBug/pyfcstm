"""Proof coverage for expressions produced by the actual DSL domain encoder."""

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.solver.expr import create_z3_vars_from_models
from pyfcstm.solver.domain import translate_expr_domain
from pyfcstm.solver import UnsatQuery, UnsatConstraint, explain_unsat

pytestmark = pytest.mark.unittest

EXPRESSION_CASES = [
 ('abs_int','int','abs(x) < 0'), ('abs_real','float','abs(x) < 0'),
 ('sign_int','int','sign(x) > 1'), ('sign_real','float','sign(x) < -1'),
 ('floor_real','float','floor(x) > x'), ('ceil_real','float','ceil(x) < x'),
 ('trunc_pos','float','x >= 0 && trunc(x) > x'),
 ('trunc_neg','float','x < 0 && trunc(x) < x'),
 ('round_bound','float','round(x) > x + 0.5'),
 ('round_tie','float','x == 2.5 && round(x) != 2'),
 ('round_neg','float','x == -1.5 && round(x) != -2'),
 ('sqrt','float','sqrt(x) < 0'), ('sqrt_int','int','sqrt(x) < 0'),
 ('sqrt_square','float','sqrt(x) * sqrt(x) != x'),
 ('power_int','int','x ** 2 < 0'), ('power_real','float','x ** 4 < 0'),
 ('variable_power','int','x == 2 && y == 3 && x ** y != 8'),
 ('constant_power','int','x == 3 && 2 ** x != 8'),
 ('mod_negative','int','y < 0 && x % y < 0'),
 ('mod_upper','int','y > 0 && x % y >= y'),
 ('mod_upper_negative','int','y < 0 && x % y >= -y'),
 ('int_div_negative_divisor','int','x == 5 && y == -2 && x / y != -2'),
 ('real_div_positive','float','x > 0 && y > 0 && x / y <= 0'),
 ('real_div_negative','float','x > 0 && y < 0 && x / y >= 0'),
 ('real_div_fixed','float','x == 5.0 && y == 2.0 && x / y != 2.5'),
 ('real_div_identity','float','y != 0 && (x / y) * y != x'),
 ('conditional','int','((x >= 0) ? x : -x) < 0'),
 ('short_circuit','int','x == 0 && !(x == 0 || 1 / x > 0)'),
 ('iff','int','(x > 0 iff y > 0) && x > 0 && y <= 0'),
 ('xor','int','(x > 0 xor y > 0) && x > 0 && y > 0'),
 ('implies','int','(x > 0 => y > 0) && x > 0 && y <= 0'),
]

def _expression_report(name, kind, predicate):
    model = load_state_machine_from_text(
        'def %s x=0; def %s y=0; state Root { state A; state B; [*]->A; A->B: if [%s]; }'
        % (kind, kind, predicate))
    guard = next(transition.guard for state in model.walk_states() for transition in state.transitions
                 if transition.guard is not None)
    translated = translate_expr_domain(guard, create_z3_vars_from_models(model))
    assert translated.failure is None
    query = UnsatQuery(name, tuple(UnsatConstraint('domain%d' % index, (item.constraint,))
                                  for index, item in enumerate(translated.definedness_constraints)) +
                      (UnsatConstraint('guard', (translated.z3_expr,)),))
    return explain_unsat(query, timeout_ms=5000)


@pytest.mark.parametrize('name,kind,predicate', EXPRESSION_CASES, ids=[case[0] for case in EXPRESSION_CASES])
def test_generated_expression_has_a_complete_proof(name, kind, predicate):
    report = _expression_report(name, kind, predicate)
    assert report.solver_status == 'unsat'
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'
    assert report.reading_status == 'complete'
    assert report.gaps == ()


@pytest.mark.parametrize('name', ['round_tie', 'real_div_positive', 'sqrt_square', 'variable_power'])
@pytest.mark.parametrize('language', ['en', 'zh'])
def test_encoder_theory_proof_text_is_complete_and_portable(name, language, text_aligner):
    from pathlib import Path
    from pyfcstm.solver import UnsatReport

    case = next(case for case in EXPRESSION_CASES if case[0] == name)
    report = _expression_report(*case)
    expected = (Path(__file__).parent / 'proof_readings' / (name + '.' + language + '.txt')).read_text()
    text_aligner.assert_equal(expected, report.reading.to_text(language))
    text_aligner.assert_equal(expected, UnsatReport.from_canonical(report.to_canonical()).reading.to_text(language))


def test_constant_true_premise_does_not_justify_a_false_arithmetic_claim():
    import z3
    from dataclasses import replace
    from pyfcstm.solver.proof import ProofParameter, analyze_proof
    from .test_proof_rules import _certificate_graph

    graph = _certificate_graph((z3.RealVal(0) <= 0,), (), z3.RealVal(0) < 0)
    graph = replace(graph, nodes=graph.nodes[:-1] + (replace(graph.nodes[-1], parameters=(
        ProofParameter('symbol', 'arith'),)),))
    assert analyze_proof(graph).graph.node(graph.root_id).local_check == 'unsupported'


@pytest.mark.parametrize('operator', ['to_int', '/'])
def test_algebraic_operand_is_not_silently_replaced_by_a_rational(operator):
    from pyfcstm.solver.proof import ProofGraph, ProofNode, ProofParameter, ProofTerm, analyze_proof

    terms = (
        ProofTerm('a', 'algebraic', 'Real', 'algebraic', value='(root-obj (+ (^ x 2) (- 2)) 2)'),
        ProofTerm('d', 'constant', 'Real', 'd', value='d', operator_kind='uninterpreted'),
        ProofTerm('zero', 'literal', 'Real', 'Real', value='0'),
        ProofTerm('izero', 'literal', 'Int', 'Int', value='0'),
        ProofTerm('guard', 'application', 'Bool', '=', ('d', 'zero')),
        ProofTerm('value', 'application', 'Int' if operator == 'to_int' else 'Real', operator,
                  ('a',) if operator == 'to_int' else ('a', 'd')),
        ProofTerm('product', 'application', 'Real', '*', ('d', 'value')),
        ProofTerm('claim', 'application', 'Bool', '>=', ('value', 'izero' if operator == 'to_int' else 'zero')),
        ProofTerm('clause', 'application', 'Bool', 'or', ('guard', 'claim')),
    )
    graph = ProofGraph('algebraic', 'root', (
        ProofNode('root', 'th-lemma', (), 'clause', parameters=(ProofParameter('symbol', 'arith'),)),
    ), terms, ())
    assert analyze_proof(graph).graph.node('root').local_check == 'unsupported'


@pytest.mark.parametrize('case,mutation', [('real_div_positive', 'guard'), ('real_div_positive', 'operator'),
                                          ('floor_real', 'bound'), ('round_tie', 'constant_divisor')])
def test_theory_templates_reject_removed_conditions_and_changed_operators(case, mutation):
    from dataclasses import replace
    from pyfcstm.solver.proof import analyze_proof

    report = _expression_report(*next(item for item in EXPRESSION_CASES if item[0] == case))
    kind = 'floor_lower' if mutation == 'bound' else 'remainder_lower' if mutation == 'constant_divisor' else 'real_division'
    node = next(node for node in report.proof.nodes if node.inference_kind == kind)
    graph = replace(report.proof, nodes=(replace(node, parents=()),), root_id=node.node_id)
    clause = graph.term(node.conclusion)
    if mutation == 'guard':
        target, changes = clause.arguments[0], {'operator': 'distinct'}
    elif mutation == 'operator':
        term = next(term for term in graph.terms if term.operator == '/')
        target, changes = term.term_id, {'operator_kind': 'uninterpreted'}
    elif mutation == 'bound':
        target, changes = clause.arguments[1], {'operator': '<'}
    else:
        remainder = next(term for term in graph.terms if term.operator == 'mod')
        target, changes = remainder.arguments[1], {'value': '0'}
    graph = replace(graph, terms=tuple(replace(term, **changes) if term.term_id == target else term
                                      for term in graph.terms))
    assert analyze_proof(graph).graph.node(node.node_id).local_check == 'unsupported'


@pytest.mark.parametrize('case', ['branches', 'sequential', 'guarded_division', 'nested'])
def test_operation_encoder_results_have_complete_proofs(case):
    import z3
    from pyfcstm.solver.operation import execute_operations_domain, parse_operations

    x, y, z = z3.Ints('x y z')
    programs = {
        'branches': 'if [x < 0] { y = -x; } else if [x == 0] { y = 0; } else { y = x; }',
        'sequential': 'y = x + 1; z = y + 2;',
        'guarded_division': 'if [x == 0] { y = 0; } else { y = 1 / x; }',
        'nested': 'if [x >= 0] { if [x > 0] { y = x; } else { y = 0; } } else { y = -x; }',
    }
    context = (x >= 0,) if case == 'sequential' else (x == 0,) if case == 'guarded_division' else ()
    execution = execute_operations_domain(parse_operations(programs[case]), {'x': x, 'y': y, 'z': z},
                                          path_conditions=context)
    assert execution.failure is None
    goal = (execution.env['z'] < 3 if case == 'sequential' else
            execution.env['y'] != 0 if case == 'guarded_division' else execution.env['y'] < 0)
    report = explain_unsat(UnsatQuery(case, (
        UnsatConstraint('context', (z3.And(*context),)),
        UnsatConstraint('definedness', (z3.And(*(item.constraint for item in execution.definedness_constraints)),)),
        UnsatConstraint('expressions', (z3.And(*execution.expr_constraints),)),
        UnsatConstraint('bad_output', (goal,)),
    )))
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'
    assert report.scope_check == 'passed'
    assert report.gaps == ()
