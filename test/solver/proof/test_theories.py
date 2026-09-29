"""Theory deductions retain concrete checked evidence for readable proofs."""

import pytest
import z3

from pyfcstm.solver import UnsatConstraint, UnsatQuery, UnsatReport, explain_unsat

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('count', [3, 8, 32])
def test_event_cardinality_conflict_has_a_checked_counting_derivation(count):
    """Two enabled events exceed the declared one-event capacity."""
    events = [z3.Bool('event_%d' % index) for index in range(count)]
    report = explain_unsat(UnsatQuery('event_limit', (
        UnsatConstraint('limit', (z3.AtMost(*events, 1),)),
        UnsatConstraint('first', (events[0],)),
        UnsatConstraint('second', (events[1],)),
    )))
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'
    assert report.scope_check == 'passed'
    assert report.gaps == ()
    certificates = [node.cardinality for node in report.proof.nodes if node.cardinality is not None]
    assert certificates
    assert all(certificate.minimum <= certificate.maximum for certificate in certificates)
    assert all(node.local_check == 'checked' for node in report.proof.nodes if node.cardinality is not None)
    loaded = UnsatReport.from_canonical(report.to_canonical())
    assert loaded.proof == report.proof


@pytest.mark.parametrize('weights,threshold', [((2, 3, 4), 4), ((-2, 3, 4), 0)])
def test_weighted_boolean_bounds_keep_signed_integer_weights(weights, threshold):
    """The counting certificate must use coefficients rather than count atoms."""
    a, b, c = z3.Bools('a b c')
    report = explain_unsat(UnsatQuery('weighted_limit', (
        UnsatConstraint('limit', (z3.PbLe(list(zip((a, b, c), weights)), threshold),)),
        UnsatConstraint('first', (a,)),
        UnsatConstraint('second', (b,)),
    )))
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'
    assert report.gaps == ()


def test_counting_lemma_keeps_the_rewritten_count_constraint_visible():
    """The final resolution must visibly supply the count used by its lemma."""
    a, b, c = z3.Bools('a b c')
    report = explain_unsat(UnsatQuery('events', (
        UnsatConstraint('limit', (z3.AtMost(a, b, c, 1),)),
        UnsatConstraint('a', (a,)),
        UnsatConstraint('b', (b,)),
    )))
    certificate = next(node.cardinality for node in report.proof.nodes if node.cardinality is not None)
    root = report.reading.get_block(report.reading.root_id)
    premise_claims = {claim for key in root.premise_block_ids
                      for claim in report.reading.get_block(key).claims}
    assert certificate.constraint_id in premise_claims


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_counting_proof_text_exposes_every_bound_and_roundtrips(language, text_aligner):
    """The complete readable proof contains actual count ranges and premises."""
    from pathlib import Path

    a, b, c = z3.Bools('a b c')
    report = explain_unsat(UnsatQuery('events', (
        UnsatConstraint('limit', (z3.AtMost(a, b, c, 1),)),
        UnsatConstraint('a', (a,)),
        UnsatConstraint('b', (b,)),
    )))
    certificate = next(node.cardinality for node in report.proof.nodes if node.cardinality is not None)
    unknown = next(item for item in certificate.contributions if item.minimum != item.maximum)
    auxiliary = report.proof.term(unknown.term_id).value
    expected = (Path(__file__).parent / 'proof_readings' / ('cardinality_%s.txt' % language)).read_text('utf-8')
    expected = expected.replace('AUX', auxiliary)
    text_aligner.assert_equal(expected, report.reading.to_text(language, detail='detailed'))
    loaded = UnsatReport.from_canonical(report.to_canonical())
    text_aligner.assert_equal(expected, loaded.reading.to_text(language, detail='detailed'))


def _counting_graph(operator, weights, threshold, required, assignments, constant=False):
    """Construct public local evidence with independently specified premises."""
    from pyfcstm.solver.proof import ProofGraph, ProofInput, ProofNode, ProofParameter, ProofTerm

    terms = [ProofTerm(name, 'constant', 'Bool', name, value=name,
                       operator_kind='uninterpreted') for name in ('a', 'b', 'c')]
    if constant:
        terms[2] = ProofTerm('c', 'literal', 'Bool', 'false', value='false')
    parameters = (threshold,) if operator in ('at-most', 'at-least') else (threshold,) + weights
    terms.extend((
        ProofTerm('pb', 'application', 'Bool', operator, ('a', 'b', 'c'),
                  parameters=tuple(ProofParameter('integer', str(value)) for value in parameters)),
        ProofTerm('not-pb', 'application', 'Bool', 'not', ('pb',)),
        ProofTerm('false', 'literal', 'Bool', 'false', value='false'),
    ))
    inputs, nodes = [], []
    literals = [('pb' if required else 'not-pb')]
    for name, value in assignments:
        if value:
            literals.append(name)
        else:
            terms.append(ProofTerm('not-'+name, 'application', 'Bool', 'not', (name,)))
            literals.append('not-'+name)
    for index, literal in enumerate(literals):
        key = 'p%d' % index
        inputs.append(ProofInput(key, key, 0, literal, False))
        nodes.append(ProofNode(key, 'asserted', (), literal, input_occurrences=(key,)))
    nodes.append(ProofNode('root', 'th-lemma', tuple(node.node_id for node in nodes), 'false',
                           parameters=(ProofParameter('symbol', 'pb'),)))
    return ProofGraph('counting', 'root', tuple(nodes), tuple(terms), tuple(inputs))


@pytest.mark.parametrize('operator,weights,threshold,required,assignments,expected', [
    ('at-most', (1, 1, 1), 1, True, (('a', True), ('b', True)), (2, 3)),
    ('at-least', (1, 1, 1), 2, True, (('a', False), ('b', False)), (0, 1)),
    ('pble', (2, 3, 4), 4, True, (('a', True), ('b', True)), (5, 9)),
    ('pble', (2, 3, 4), 9, False, (('a', True), ('b', True)), (5, 9)),
    ('pbge', (2, 3, 4), 2, False, (('a', True), ('b', False)), (2, 6)),
    ('pbge', (2, 3, 4), 4, True, (('a', False), ('b', False), ('c', False)), (0, 0)),
    ('pbeq', (1, 1, 1), 1, True, (('a', True), ('b', True)), (2, 3)),
    ('pbeq', (1, 1, 1), 2, False, (('a', True), ('b', True), ('c', False)), (2, 2)),
    ('pbeq', (1, 1, 1), 2, True, (('a', True), ('b', False)), None),
    ('pble', (1, 1, 1), 1, True, (), None),
    ('pbge', (1, 1, 1), 1, True, (), None),
    ('pbeq', (1, 1, 1), 4, True, (), (0, 3)),
    ('pble', (-2, 3, 4), 0, True, (('b', True),), (1, 7)),
])
def test_local_boolean_intervals_prove_only_an_actual_count_conflict(
        operator, weights, threshold, required, assignments, expected):
    """A range crossing the threshold is insufficient evidence of contradiction."""
    from pyfcstm.solver.proof import analyze_proof

    graph = _counting_graph(operator, weights, threshold, required, assignments)
    node = analyze_proof(graph).graph.node('root')
    if expected is None:
        assert node.local_check == 'unsupported'
        assert node.cardinality is None
    else:
        assert node.local_check == 'checked'
        assert (node.cardinality.minimum, node.cardinality.maximum) == expected
        assert node.cardinality.assumptions == ()


def test_counting_uses_the_truth_value_of_boolean_constants():
    from pyfcstm.solver.proof import analyze_proof

    graph = _counting_graph('at-least', (1, 1, 1), 3, True, (), constant=True)
    node = analyze_proof(graph).graph.node('root')
    assert node.local_check == 'checked'
    assert (node.cardinality.minimum, node.cardinality.maximum) == (0, 2)


@pytest.mark.parametrize('mutation', ['reversed', 'outside', 'duplicate', 'missing', 'arithmetic'])
def test_offline_counting_evidence_rejects_bad_ranges_and_references(mutation):
    """Malformed public snapshots cannot silently attach invalid counting data."""
    a, b, c = z3.Bools('a b c')
    report = explain_unsat(UnsatQuery('events', (
        UnsatConstraint('limit', (z3.AtMost(a, b, c, 1),)),
        UnsatConstraint('a', (a,)),
        UnsatConstraint('b', (b,)),
    )))
    data = report.to_canonical()
    certificate = next(node['cardinality'] for node in data['proof']['nodes']
                       if node['cardinality'] is not None)
    if mutation == 'reversed':
        certificate['contributions'][0]['minimum'] = 1
    elif mutation == 'outside':
        certificate['contributions'][0]['maximum'] = 2
    elif mutation == 'duplicate':
        certificate['assignments'] += certificate['assignments'][:1]
    elif mutation == 'missing':
        certificate['constraint_id'] = 'missing'
    else:
        term = next(term for term in data['proof']['terms']
                    if term['term_id'] == certificate['constraint_id'])
        term['sort'] = 'Int'
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('mutation', ['missing_weight', 'noninteger_weight', 'opposite_literal'])
def test_counting_does_not_certify_malformed_or_conflicting_local_inputs(mutation):
    from dataclasses import replace
    from pyfcstm.solver.proof import ProofInput, ProofNode, ProofParameter, ProofTerm
    from pyfcstm.solver.proof import analyze_proof

    graph = _counting_graph('pble', (2, 3, 4), 4, True, (('a', True), ('b', True)))
    if mutation == 'opposite_literal':
        term = ProofTerm('not-a', 'application', 'Bool', 'not', ('a',))
        opposite = ProofNode('opposite', 'asserted', (), 'not-a', input_occurrences=('opposite',))
        root = replace(graph.nodes[-1], parents=graph.nodes[-1].parents + ('opposite',))
        graph = replace(graph, terms=graph.terms + (term,),
                        nodes=graph.nodes[:-1] + (opposite, root),
                        inputs=graph.inputs + (ProofInput('opposite', 'opposite', 0, 'not-a', False),))
    else:
        pb = graph.term('pb')
        parameters = (pb.parameters[:-1] if mutation == 'missing_weight' else
                      (ProofParameter('symbol', '4'),) + pb.parameters[1:])
        graph = replace(graph, terms=tuple(replace(term, parameters=parameters) if term.term_id == 'pb'
                                          else term for term in graph.terms))
    result = analyze_proof(graph)
    assert result.graph.node('root').local_check == 'unsupported'
    assert result.graph.node('root').cardinality is None


def test_closed_counting_contradiction_prints_no_unintroduced_assumptions(text_aligner):
    from pyfcstm.solver.proof import analyze_proof
    from pyfcstm.solver.proof import ProofReading, ReadingBlock

    graph = analyze_proof(_counting_graph('at-most', (1, 1, 1), 1, True,
                                         (('a', True), ('b', True)))).graph
    reading = ProofReading('counting', 'unsat', 'root', 'complete', tuple(
        ReadingBlock(node.node_id, node.inference_kind, (node.conclusion,),
                     node.parents, (), (node.node_id,)) for node in graph.nodes), (), (), graph)
    text_aligner.assert_equal('''\
Query: counting
Solver result: UNSAT
Reading: complete

P1  Input
  Input origins: p0
  Therefore: at-most[1](a, b, c)

P2  Input
  Input origins: p1
  Therefore: a

P3  Input
  Input origins: p2
  Therefore: b

P4  Boolean counting contradiction
  From: P1, P2, P3
  Known: a = true
  Known: b = true
  Contribution: a; weight = 1; [1, 1]
  Contribution: b; weight = 1; [1, 1]
  Contribution: c; weight = 1; [0, 1]
  Weighted sum range: [2, 3]
  Required: at-most[1](a, b, c) = true
  These bounds force the constraint to be false; contradiction.
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
''', reading.to_text(detail='detailed'))


@pytest.mark.parametrize('term_id', ['a', 'pb', 'c'])
def test_counting_rejects_nonboolean_portable_terms(term_id):
    from dataclasses import replace
    from pyfcstm.solver.proof import analyze_proof

    graph = _counting_graph('at-most', (1, 1, 1), 1, True, (('a', True), ('b', True)))
    graph = replace(graph, terms=tuple(replace(term, sort='Int') if term.term_id == term_id else term
                                      for term in graph.terms))
    assert analyze_proof(graph).graph.node('root').local_check == 'unsupported'


def test_native_nonlinear_equality_order_lemmas_are_checked():
    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('square', (
        UnsatConstraint('square', (x * x == 2,)),
    )))
    triangles = [node for node in report.proof.nodes
                 if tuple(p.value for p in node.parameters) == ('arith', 'triangle-eq')]
    assert triangles
    assert all(node.local_check == 'checked' for node in triangles)
    assert all(node.inference_kind == 'order' for node in triangles)


def _order_graph(clauses):
    from pyfcstm.solver.proof import ProofGraph, ProofNode, ProofParameter, ProofTerm

    terms = [ProofTerm('x', 'constant', 'Real', 'x', operator_kind='uninterpreted'),
             ProofTerm('y', 'constant', 'Real', 'y', operator_kind='uninterpreted'),
             ProofTerm('z', 'constant', 'Real', 'z', operator_kind='uninterpreted')]
    literals = []
    for index, (operator, left, right, positive) in enumerate(clauses):
        key = 'c%d' % index
        terms.append(ProofTerm(key, 'application', 'Bool', operator, (left, right)))
        if not positive:
            terms.append(ProofTerm('not-' + key, 'application', 'Bool', 'not', (key,)))
            key = 'not-' + key
        literals.append(key)
    terms.append(ProofTerm('clause', 'application', 'Bool', 'or', tuple(literals)))
    return ProofGraph('order', 'root', (
        ProofNode('root', 'th-lemma', (), 'clause', parameters=(
            ProofParameter('symbol', 'arith'), ProofParameter('symbol', 'triangle-eq'))),
    ), tuple(terms), ())


@pytest.mark.parametrize('clauses,expected', [
    ((('=', 'x', 'y', False), ('<=', 'x', 'y', True)), 'checked'),
    ((('=', 'x', 'y', False), ('>=', 'x', 'y', True)), 'checked'),
    ((('=', 'x', 'y', True), ('<=', 'x', 'y', False), ('>=', 'x', 'y', False)), 'checked'),
    ((('<', 'x', 'y', True), ('=', 'y', 'x', True), ('>', 'x', 'y', True)), 'checked'),
    ((('=', 'x', 'y', False), ('<', 'x', 'y', True)), 'unsupported'),
    ((('<=', 'x', 'y', True), ('>=', 'x', 'z', True)), 'unsupported'),
    ((('=', 'x', 'x', True),), 'checked'),
    ((), 'unsupported'),
])
def test_order_check_requires_all_signs_of_the_same_difference(clauses, expected):
    from pyfcstm.solver.proof import analyze_proof

    result = analyze_proof(_order_graph(clauses))
    assert result.graph.node('root').local_check == expected


@pytest.mark.parametrize('mutation', ['missing', 'not_clause', 'authored_or', 'authored_relation',
                                     'unknown_relation', 'arity', 'sort'])
def test_order_check_rejects_uninterpreted_and_malformed_comparisons(mutation):
    from dataclasses import replace
    from pyfcstm.solver.proof import analyze_proof

    graph = _order_graph((('=', 'x', 'y', False), ('<=', 'x', 'y', True)))
    if mutation == 'missing':
        graph = replace(graph, nodes=(replace(graph.nodes[0], conclusion=None),))
    else:
        target, changes = {
            'not_clause': ('clause', {'operator': 'and'}),
            'authored_or': ('clause', {'operator_kind': 'uninterpreted'}),
            'authored_relation': ('c0', {'operator_kind': 'uninterpreted'}),
            'unknown_relation': ('c0', {'operator': 'distinct'}),
            'arity': ('c0', {'arguments': ('x',)}),
            'sort': ('x', {'sort': 'Bool'}),
        }[mutation]
        graph = replace(graph, terms=tuple(replace(term, **changes) if term.term_id == target else term
                                          for term in graph.terms))
    assert analyze_proof(graph).graph.node('root').local_check == 'unsupported'


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_nonlinear_order_and_interval_reading_is_complete(language, text_aligner):
    from pathlib import Path

    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('nonlinear', (UnsatConstraint('square', (x * x == 2,)),)))
    expected = (Path(__file__).parent / 'proof_readings' / ('nonlinear.' + language + '.txt')).read_text(encoding='utf-8')
    text_aligner.assert_equal(expected, report.reading.to_text(language, detail='detailed'))
    restored = UnsatReport.from_canonical(report.to_canonical())
    text_aligner.assert_equal(expected, restored.reading.to_text(language, detail='detailed'))


def test_native_division_order_lemmas_normalize_shared_nonlinear_atoms():
    x, d = z3.Ints('x d')
    report = explain_unsat(UnsatQuery('division', (
        UnsatConstraint('values', (x == 5, d == 2)),
        UnsatConstraint('wrong_quotient', (x / d != 2,)),
    )))
    triangles = [node for node in report.proof.nodes
                 if tuple(p.value for p in node.parameters) == ('arith', 'triangle-eq')]
    assert triangles
    assert all(node.local_check == 'checked' for node in triangles)


@pytest.mark.parametrize('positive', [True, False])
def test_nonzero_divisor_has_nonnegative_euclidean_remainder(positive):
    x, d = z3.Ints('x d')
    report = explain_unsat(UnsatQuery('remainder', (
        UnsatConstraint('divisor', (d > 0 if positive else d < 0,)),
        UnsatConstraint('negative_remainder', (x % d < 0,)),
    )))
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    assert any(node.inference_kind == 'remainder_lower' for node in report.proof.nodes)


def test_native_euclidean_division_axioms_are_checked():
    x, d = z3.Ints('x d')
    report = explain_unsat(UnsatQuery('division', (
        UnsatConstraint('values', (x == 5, d == 2)),
        UnsatConstraint('wrong_quotient', (x / d != 2,)),
    )))
    axioms = [node for node in report.proof.nodes
              if tuple(p.value for p in node.parameters) == ('arith',)]
    assert {node.inference_kind for node in axioms} == {
        'division_identity', 'remainder_lower', 'remainder_upper'}
    assert all(node.local_check == 'checked' for node in axioms)


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_remainder_reading_explains_nonzero_condition_in_full(language, text_aligner):
    from pathlib import Path

    x, d = z3.Ints('x d')
    report = explain_unsat(UnsatQuery('remainder', (
        UnsatConstraint('divisor', (d > 0,)),
        UnsatConstraint('negative_remainder', (x % d < 0,)),
    )))
    expected = (Path(__file__).parent / 'proof_readings' / ('remainder.' + language + '.txt')).read_text(encoding='utf-8')
    text_aligner.assert_equal(expected, report.reading.to_text(language, detail='detailed'))
    restored = UnsatReport.from_canonical(report.to_canonical())
    text_aligner.assert_equal(expected, restored.reading.to_text(language, detail='detailed'))


@pytest.mark.parametrize('mutation', ['missing', 'no_guard', 'wrong_guard', 'wrong_zero',
                                     'real_divisor', 'authored_mod', 'wrong_divisor', 'bad_body'])
def test_remainder_axiom_rejects_missing_preconditions_and_wrong_operators(mutation):
    from dataclasses import replace
    from pyfcstm.solver.proof import analyze_proof

    x, d = z3.Ints('x d')
    report = explain_unsat(UnsatQuery('remainder', (
        UnsatConstraint('divisor', (d > 0,)), UnsatConstraint('negative', (x % d < 0,)),
    )))
    graph = report.proof
    node = next(node for node in graph.nodes if node.inference_kind == 'remainder_lower')
    clause = graph.term(node.conclusion)
    guard = graph.term(clause.arguments[0])
    divisor, zero = guard.arguments
    rem = next(term for term in graph.terms if term.operator == 'mod')
    if mutation == 'missing':
        graph = replace(graph, nodes=tuple(replace(item, conclusion=None) if item.node_id == node.node_id else item
                                          for item in graph.nodes))
    else:
        target, changes = {
            'no_guard': (clause.term_id, {'arguments': (clause.arguments[1],)}),
            'wrong_guard': (guard.term_id, {'operator': 'distinct'}),
            'wrong_zero': (zero, {'value': '1'}),
            'real_divisor': (divisor, {'sort': 'Real'}),
            'authored_mod': (rem.term_id, {'operator_kind': 'uninterpreted'}),
            'wrong_divisor': (rem.term_id, {'arguments': (rem.arguments[0], zero)}),
            'bad_body': (clause.arguments[1], {'operator_kind': 'uninterpreted'}),
        }[mutation]
        graph = replace(graph, terms=tuple(replace(term, **changes) if term.term_id == target else term
                                          for term in graph.terms))
    assert analyze_proof(graph).graph.node(node.node_id).local_check == 'unsupported'


@pytest.mark.parametrize('kind', ['division_identity', 'remainder_upper'])
def test_division_axiom_rejects_changed_arithmetic_claim(kind):
    from dataclasses import replace
    from pyfcstm.solver.proof import analyze_proof

    x, d = z3.Ints('x d')
    report = explain_unsat(UnsatQuery('division', (
        UnsatConstraint('values', (x == 5, d == 2)),
        UnsatConstraint('wrong_quotient', (x / d != 2,)),
    )))
    graph = report.proof
    node = next(node for node in graph.nodes if node.inference_kind == kind)
    clause = graph.term(node.conclusion)
    guard = graph.term(clause.arguments[0])
    body = graph.term(clause.arguments[1])
    # Change the equality's dividend or relax the upper limit. Neither is the
    # exact Euclidean axiom represented by the original native evidence.
    replacement = guard.arguments[0 if kind == 'division_identity' else 1]
    changed = replace(body, arguments=(body.arguments[0], replacement))
    graph = replace(graph, terms=tuple(changed if term.term_id == body.term_id else term for term in graph.terms))
    assert analyze_proof(graph).graph.node(node.node_id).local_check == 'unsupported'


def test_unknown_arithmetic_hint_remains_an_explicit_gap():
    from dataclasses import replace
    from pyfcstm.solver.proof import ProofParameter, analyze_proof

    graph = _order_graph((('=', 'x', 'y', False), ('<=', 'x', 'y', True)))
    graph = replace(graph, nodes=(replace(graph.nodes[0], parameters=(
        ProofParameter('symbol', 'arith'), ProofParameter('symbol', 'unrecognized'))),))
    assert analyze_proof(graph).graph.node('root').local_check == 'unsupported'


@pytest.mark.parametrize('expression', ['power', 'sqrt'])
def test_arithmetic_capture_retries_when_legacy_profile_cannot_produce_proof(expression):
    x = z3.Int('x') if expression == 'power' else z3.Real('x')
    constraints = (x ** 2 < 0,) if expression == 'power' else (x >= 0, z3.Sqrt(x) < 0)
    report = explain_unsat(UnsatQuery(expression, (UnsatConstraint('impossible', constraints),)), timeout_ms=5000)
    assert report.solver_status == 'unsat'
    assert report.proof_status == 'captured'
    assert report.input_check == 'passed'
    assert report.scope_check == 'passed'


@pytest.mark.parametrize('spent_seconds', [0.04, 0.2])
def test_arithmetic_capture_retry_shares_deadline_and_keeps_unknown_honest(monkeypatch, spent_seconds):
    import time

    now, checks, timeouts = [0.0], [], []
    original_check, original_set = z3.Solver.check, z3.Solver.set

    def check(native, *assumptions):
        checks.append(native)
        if len(checks) == 1:
            result = original_check(native, *assumptions)
            assert result == z3.unknown
            now[0] = spent_seconds
            return result
        return z3.unknown

    def set_options(native, *args, **kwargs):
        if 'timeout' in kwargs:
            timeouts.append(kwargs['timeout'])
        return original_set(native, *args, **kwargs)

    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(z3.Solver, 'check', check)
    monkeypatch.setattr(z3.Solver, 'set', set_options)
    monkeypatch.setattr(z3.Solver, 'reason_unknown', lambda native:
                        'incomplete (theory arithmetic)' if len(checks) == 1 else 'retry incomplete')
    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('power', (UnsatConstraint('square', (x ** 2 < 0,)),)), timeout_ms=100)
    assert report.solver_status == 'unknown'
    assert report.proof_status == 'unavailable'
    assert report.proof is None
    assert timeouts[0] == 100
    if spent_seconds < 0.1:
        assert len(checks) == 2
        assert 0 < timeouts[1] <= 61
        assert report.stop_reason == 'retry incomplete'
    else:
        assert len(checks) == 1
        assert report.stop_reason == 'budget exhausted during proof capture'


@pytest.mark.parametrize('expression', ['power', 'sqrt'])
def test_power_and_principal_square_root_axioms_have_complete_readings(expression):
    x = z3.Int('x') if expression == 'power' else z3.Real('x')
    constraints = (x ** 2 < 0,) if expression == 'power' else (x >= 0, z3.Sqrt(x) < 0)
    report = explain_unsat(UnsatQuery(expression, (UnsatConstraint('impossible', constraints),)))
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    assert any(node.inference_kind in ('even_power', 'root_nonnegative') for node in report.proof.nodes)


def _power_axiom_graph(exponent='1/2', domain=True, identity=False):
    from pyfcstm.solver.proof import ProofGraph, ProofNode, ProofParameter, ProofTerm

    terms = (
        ProofTerm('x', 'constant', 'Real', 'x', value='x', operator_kind='uninterpreted'),
        ProofTerm('zero', 'literal', 'Real', 'Real', value='0'),
        ProofTerm('exponent', 'literal', 'Real', 'Real', value=exponent),
        ProofTerm('two', 'literal', 'Real', 'Real', value='2'),
        ProofTerm('root', 'application', 'Real', '^', ('x', 'exponent')),
        ProofTerm('square', 'application', 'Real', '^', ('root', 'two')),
        ProofTerm('nonnegative', 'application', 'Bool', '>=', ('x', 'zero')),
        ProofTerm('outside-domain', 'application', 'Bool', 'not', ('nonnegative',)),
        ProofTerm('claim', 'application', 'Bool', '=' if identity else '>=',
                  ('x', 'square') if identity else ('root', 'zero')),
        ProofTerm('clause', 'application', 'Bool', 'or', ('outside-domain', 'claim')),
    )
    return ProofGraph('power', 'axiom', (
        ProofNode('axiom', 'th-lemma', (), 'clause' if domain else 'claim', parameters=(
            ProofParameter('symbol', 'arith'),)),
    ), terms, ())


@pytest.mark.parametrize('exponent,domain,identity,expected', [
    ('2', False, False, 'even_power'), ('4', False, False, 'even_power'),
    ('1', False, False, 'opaque'), ('-2', False, False, 'opaque'),
    ('0', False, False, 'opaque'), ('1/2', False, False, 'opaque'),
    ('1/2', True, False, 'root_nonnegative'), ('1/2', True, True, 'root_identity'),
    ('1/2', False, True, 'opaque'), ('1/3', True, True, 'opaque'),
])
def test_power_axioms_require_correct_exponent_and_domain(exponent, domain, identity, expected):
    from pyfcstm.solver.proof import analyze_proof

    node = analyze_proof(_power_axiom_graph(exponent, domain, identity)).graph.node('axiom')
    assert node.inference_kind == expected
    assert node.local_check == ('unsupported' if expected == 'opaque' else 'checked')


@pytest.mark.parametrize('target,changes', [
    ('root', {'operator_kind': 'uninterpreted'}),
    ('root', {'sort': 'Int'}),
    ('root', {'arguments': ('x',)}),
    ('x', {'sort': 'Bool'}),
    ('exponent', {'kind': 'constant', 'operator_kind': 'uninterpreted'}),
    ('exponent', {'sort': 'Bool'}),
    ('claim', {'operator': '<='}),
    ('nonnegative', {'arguments': ('zero', 'x')}),
])
def test_root_axioms_reject_authored_operators_and_wrong_domain(target, changes):
    from dataclasses import replace
    from pyfcstm.solver.proof import analyze_proof

    graph = _power_axiom_graph()
    graph = replace(graph, terms=tuple(replace(term, **changes) if term.term_id == target else term
                                      for term in graph.terms))
    assert analyze_proof(graph).graph.node('axiom').local_check == 'unsupported'


@pytest.mark.parametrize('expression', ['power', 'sqrt'])
@pytest.mark.parametrize('language', ['en', 'zh'])
def test_power_and_root_proof_text_in_full(expression, language, text_aligner):
    from pathlib import Path

    x = z3.Int('x') if expression == 'power' else z3.Real('x')
    constraints = (x ** 2 < 0,) if expression == 'power' else (x >= 0, z3.Sqrt(x) < 0)
    report = explain_unsat(UnsatQuery(expression, (UnsatConstraint('impossible', constraints),)))
    expected = (Path(__file__).parent / 'proof_readings' / (expression + '.' + language + '.txt')).read_text(encoding='utf-8')
    text_aligner.assert_equal(expected, report.reading.to_text(language, detail='detailed'))
    text_aligner.assert_equal(expected, UnsatReport.from_canonical(report.to_canonical()).reading.to_text(language, detail='detailed'))


@pytest.mark.parametrize('value,identity,expected', [
    ('4', False, 'checked'), ('0', False, 'checked'), ('-1', False, 'unsupported'),
    ('4', True, 'checked'), ('-1', True, 'unsupported'),
])
def test_literal_radicands_are_checked_without_an_external_domain_premise(value, identity, expected):
    from dataclasses import replace
    from pyfcstm.solver.proof import analyze_proof

    graph = _power_axiom_graph(domain=False, identity=identity)
    graph = replace(graph, terms=tuple(replace(term, kind='literal', operator='Real',
                                              operator_kind='builtin', value=value)
                                      if term.term_id == 'x' else term for term in graph.terms))
    assert analyze_proof(graph).graph.node('axiom').local_check == expected


@pytest.mark.parametrize('identity', [True, False])
def test_algebraic_radicand_sign_is_not_guessed_from_its_display(identity):
    from dataclasses import replace
    from pyfcstm.solver.proof import analyze_proof

    graph = _power_axiom_graph(domain=False, identity=identity)
    terms = []
    for term in graph.terms:
        if term.term_id == 'x':
            term = replace(term, kind='algebraic', operator_kind='builtin', value='(root-obj (+ (^ x 2) (- 2)) 2)')
        elif term.term_id == 'claim' and identity:
            term = replace(term, arguments=('zero', 'square'))
        terms.append(term)
    graph = replace(graph, terms=tuple(terms))
    assert analyze_proof(graph).graph.node('axiom').local_check == 'unsupported'


@pytest.mark.parametrize('case', ['square', 'product', 'division', 'negative_division'])
def test_nonlinear_local_bounds_produce_checked_interval_refutations(case):
    x, y, d = z3.Ints('x y d')
    constraints = {
        'square': (x * x == 2,),
        'product': (x > 1, y > 1, x * y < 2),
        'division': (x == 5, d == 2, x / d != 2),
        'negative_division': (x == -5, d == 2, x / d != -3),
    }[case]
    report = explain_unsat(UnsatQuery(case, (UnsatConstraint('conditions', constraints),)))
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    intervals = [node.interval for node in report.proof.nodes if node.inference_kind == 'interval']
    assert intervals
    assert all(certificate.steps for certificate in intervals)


@pytest.mark.parametrize('base,threshold,expected', [(True, 0, False), (2, 1, True), (0, 0, False)])
def test_constant_power_domain_requires_a_numeric_strict_bound(base, threshold, expected):
    from .test_polynomial import _graph
    from pyfcstm.solver.proof.rules import _strictly_above

    graph = _graph((), base)
    assert _strictly_above(graph.node('target').conclusion, threshold, (), graph) is expected


@pytest.mark.parametrize('base,condition,expected', [
    (True, ('not', ('=', 'x', 0)), False),
    ('x', ('not', ('=', 'x', 0)), True),
    ('x', ('not', ('=', 0, 'x')), True),
    ('x', ('=', 'x', 0), False),
    ('x', ('not', ('=', 'y', 0)), False),
    ('x', ('not', ('=', True, False)), False),
])
def test_zero_power_domain_requires_the_same_nonzero_base(base, condition, expected):
    from .test_polynomial import _graph
    from pyfcstm.solver.proof.rules import _nonzero_assumption

    graph = _graph((condition,), base)
    assert _nonzero_assumption(graph.node('target').conclusion,
                               ((graph.node('fact0').conclusion, True),), graph) is expected


def test_linear_equality_reconstruction_rejects_boolean_equalities():
    from .test_polynomial import _graph
    from pyfcstm.solver.budget import SolveBudget
    from pyfcstm.solver.proof.rules import _linear_equality

    graph = _graph((), ('=', True, False))
    assert _linear_equality(graph.node('target'), graph, SolveBudget(None)) is None


@pytest.mark.parametrize('language', ['en', 'zh'])
@pytest.mark.parametrize('detail', ['brief', 'standard', 'detailed'])
def test_quartic_polynomial_reading_matches_the_complete_text(language, detail, text_aligner):
    from pathlib import Path

    x = z3.Real('x')
    report = explain_unsat(UnsatQuery('quartic', (
        UnsatConstraint('impossible', (x*x*x*x + 1 == 0,)),
    )))
    expected = (Path(__file__).parent / 'proof_readings' /
                ('quartic.%s.%s.txt' % (detail, language))).read_text(encoding='utf-8')
    text_aligner.assert_equal(expected, report.reading.to_text(language, detail=detail))
    restored = UnsatReport.from_canonical(report.to_canonical())
    text_aligner.assert_equal(expected, restored.reading.to_text(language, detail=detail))


@pytest.mark.parametrize('algebraic_symbol', ['x', 'y'])
def test_power_domain_helpers_do_not_guess_algebraic_values(algebraic_symbol):
    from dataclasses import replace
    from .test_polynomial import _graph
    from pyfcstm.solver.proof.rules import _nonzero_assumption, _strictly_above

    graph = _graph((('not', ('=', 'x', 'y')),), 'x')
    graph = replace(graph, terms=tuple(
        replace(term, kind='algebraic', value='root-obj') if term.value == algebraic_symbol else term
        for term in graph.terms))
    base = graph.node('target').conclusion
    assert not _nonzero_assumption(base, ((graph.node('fact0').conclusion, True),), graph)
    assert not _strictly_above(base, 0, (), graph)
