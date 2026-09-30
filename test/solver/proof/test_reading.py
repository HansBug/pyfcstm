"""Human and machine readers consume the same actual proof evidence."""

from pathlib import Path

import pytest
import z3

import pyfcstm.solver as solver


pytestmark = pytest.mark.unittest


def test_linear_reading_shows_inputs_the_combination_and_contradiction(text_aligner):
    from pyfcstm.solver.proof import SourceDescription

    x, y = z3.Ints('encoded_x encoded_y')
    names = solver.SymbolNames()
    names.register(x, 'x@0')
    names.register(y, 'x@1')
    report = solver.explain_unsat(solver.UnsatQuery('increment', (
        solver.UnsatConstraint('initial', (x >= 0,),
                               SourceDescription('initial-source', 'Initial value is nonnegative')),
        solver.UnsatConstraint('update', (y == x + 1,)),
        solver.UnsatConstraint('goal', (y < 0,)),
    )), names=names)
    assert report.reading_status == 'complete'
    for language in ('en', 'zh'):
        expected = Path(__file__).with_name('proof_readings') / ('increment.%s.txt' % language)
        text_aligner.assert_equal(expected.read_text(encoding='utf-8'),
                                  report.reading.to_text(language=language, detail='detailed'))
    assert len(report.reading.blocks) < len(report.proof.nodes)


def test_branch_reading_states_local_assumptions_and_their_discharge(text_aligner, proof_snapshot):
    report = proof_snapshot('branches')
    reading = report.reading
    assert reading.status == 'complete'
    expected = Path(__file__).with_name('proof_readings') / 'branches.en.txt'
    # Z3's fresh-name counter is process-wide, including other test cases.
    # Bind only that generated identity; compare every line of the derivation.
    introduced, = (term.value for term in report.proof.terms
                   if term.kind == 'constant' and term.operator not in ('x', 'y'))
    text_aligner.assert_equal(expected.read_text(encoding='utf-8').replace('z3name!0', introduced),
                              reading.to_text(detail='detailed'))
    root = reading.get_block(reading.root_id)
    assert root.active_hypotheses == ()
    assert reading.expand(root.block_id)
    assert any(block.active_hypotheses for block in reading.blocks)


def test_every_reading_claim_retains_evidence_and_expandable_premises():
    x = z3.Real('x')
    report = solver.explain_unsat(solver.UnsatQuery('interval', (
        solver.UnsatConstraint('lower', (x >= 2,)),
        solver.UnsatConstraint('upper', (x < 1,)),
    )))
    reading = report.reading
    for block in reading.blocks:
        assert block.evidence_node_ids
        assert all(report.proof.node(node_id) for node_id in block.evidence_node_ids)
        assert all(report.proof.term(term_id) for term_id in block.claims)
        assert tuple(child.block_id for child in reading.expand(block.block_id)) == block.premise_block_ids
    assert reading.to_canonical()['root_id'] == reading.root_id
    with pytest.raises(KeyError):
        reading.get_block('missing')
    with pytest.raises(KeyError):
        reading.expand('missing')
    with pytest.raises(KeyError):
        reading.get_source('missing')
    with pytest.raises(ValueError):
        reading.to_text(language='unknown')


def test_a_business_source_adapter_needs_no_bmc_types(text_aligner):
    from pyfcstm.solver.proof import ProofExtensions, SourceAdapter, SourceDescription

    class ConfigSources(SourceAdapter):
        def describe(self, handle):
            key, title = handle
            return SourceDescription(key, title, document_id='limits.cfg',
                                     span=(1, 1, 1, 10), excerpt='limit = 0')

    x = z3.Int('x')
    report = solver.explain_unsat(solver.UnsatQuery('config', (
        solver.UnsatConstraint('minimum', (x > 0,), ('min', 'Minimum allocation')),
        solver.UnsatConstraint('maximum', (x <= 0,), ('max', 'Capacity limit')),
    )), extensions=ProofExtensions(source_adapter=ConfigSources()))
    assert report.source_status == 'complete'
    assert report.reading.get_source('min').document_id == 'limits.cfg'
    assert report.reading.get_source('max').excerpt == 'limit = 0'
    expected = Path(__file__).with_name('proof_readings') / 'config.en.txt'
    text_aligner.assert_equal(expected.read_text(encoding='utf-8'), report.reading.to_text(detail='detailed'))
    assert {link.relation for block in report.reading.blocks for link in block.source_links} == {'logical'}


def test_nonlinear_reading_exposes_every_interval_deduction(text_aligner):
    x = z3.Int('x')
    report = solver.explain_unsat(solver.UnsatQuery('nonlinear', (
        solver.UnsatConstraint('square', (x * x == 2,)),
    )))
    assert report.reading_status == 'complete'
    assert report.source_status == 'absent'
    expected = Path(__file__).with_name('proof_readings') / 'nonlinear.en.txt'
    text_aligner.assert_equal(expected.read_text(encoding='utf-8'), report.reading.to_text(detail='detailed'))
    assert report.reading.gaps == ()


def test_sat_reading_explains_why_there_is_no_refutation(text_aligner):
    report = solver.explain_unsat(solver.UnsatQuery('empty', ()))
    assert report.reading.root_id is None
    text_aligner.assert_equal("""\
Query: empty
Solver result: SAT
Reading: not_requested

No refutation is available.
""", report.reading.to_text(detail='detailed'))
    assert report.reading.blocks == ()


def test_clause_certificate_marks_its_temporary_negated_conclusion(text_aligner):
    x = z3.Real('x')
    report = solver.explain_unsat(solver.UnsatQuery('interval', (
        solver.UnsatConstraint('lower', (x >= 2,)),
        solver.UnsatConstraint('upper', (x < 1,)),
    )))
    text_aligner.assert_equal('''\
Query: interval
Solver result: UNSAT
Reading: complete

P1  Exact linear combination
  To refute the negated conclusion, temporarily assume:
    not ((x >= 1))
    (x >= 2)
  1 * [x + -1 < 0]
  1 * [-1 * x + 2 <= 0]
  Sum: 1 < 0; contradiction.
  Discharge these temporary assumptions.
  Therefore: ((x >= 1) or not ((x >= 2)))

P2  Input
  Input origins: lower
  Therefore: (x >= 2)

P3  Input
  Input origins: upper
  Therefore: (x < 1)

P4  Resolve the clauses
  From: P1, P2, P3
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text(detail='detailed'))


def test_uninterpreted_operator_name_is_not_rendered_as_a_builtin(text_aligner):
    x = z3.Real('x')
    negate_named_function = z3.Function('not', z3.RealSort(), z3.RealSort())
    term = negate_named_function(x)
    report = solver.explain_unsat(solver.UnsatQuery('named-function', (
        solver.UnsatConstraint('positive', (term > 0,)),
        solver.UnsatConstraint('zero', (term <= 0,)),
    )))
    application, = (item for item in report.proof.terms if item.operator == 'not' and item.sort == 'Real')
    assert application.operator_kind == 'uninterpreted'
    text_aligner.assert_equal('''\
Query: named-function
Solver result: UNSAT
Reading: complete

P1  Input
  Input origins: positive
  Therefore: (not(x) > 0)

P2  Input
  Input origins: zero
  Therefore: (not(x) <= 0)

P3  Resolve the clauses
  From: P1, P2
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text(detail='detailed'))


def test_each_arithmetic_bound_names_a_displayed_premise_or_a_temporary_assumption():
    x, y = z3.Ints('x y')
    report = solver.explain_unsat(solver.UnsatQuery('branches', (
        solver.UnsatConstraint('update', (y == z3.If(x >= 0, x + 1, 0),)),
        solver.UnsatConstraint('goal', (y < 0,)),
    )))
    for block in report.reading.blocks:
        node = report.proof.node(block.evidence_node_ids[0])
        if node.certificate is not None:
            premises = {claim for parent in block.premise_block_ids
                        for claim in report.reading.get_block(parent).claims}
            assert all(bound.negated or bound.term_id in premises for bound in node.certificate.bounds)


def test_compound_input_preserves_binder_and_arithmetic_syntax(text_aligner):
    x, i = z3.Real('x'), z3.Int('i')
    formula = z3.And(z3.ForAll(i, i >= 0), z3.Exists(i, i < 0),
                     -x <= 0, x - 2 <= 0, z3.ToReal(i) >= 0, z3.BoolVal(False))
    report = solver.explain_unsat(solver.UnsatQuery('syntax', (
        solver.UnsatConstraint('compound', (formula,)),
    )))
    text_aligner.assert_equal('''\
Query: syntax
Solver result: UNSAT
Reading: complete

P1  Input
  Input origins: compound
  Therefore: ((forall i: Int. (#0 >= 0)) and (exists i: Int. (#0 < 0)) and ((-x) <= 0) and ((x - 2) <= 0) and (to_real(i) >= 0) and false)

P2  Logical consequence
  From: P1
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text(detail='detailed'))


def test_duplicate_input_occurrences_are_candidates_not_two_necessary_causes(text_aligner):
    report = solver.explain_unsat(solver.UnsatQuery('duplicates', (
        solver.UnsatConstraint('first', (z3.BoolVal(False),)),
        solver.UnsatConstraint('second', (z3.BoolVal(False),)),
    )))
    text_aligner.assert_equal('''\
Query: duplicates
Solver result: UNSAT
Reading: complete

P1  Input
  Input origins: first, second
  These are alternative occurrences of the same formula.
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text(detail='detailed'))


def test_array_lambda_is_not_mislabeled_as_an_existential_quantifier(text_aligner):
    i = z3.Int('i')
    array = z3.Lambda(i, i + 1)
    formula = z3.And(z3.Select(array, 0) < 0, z3.BoolVal(False))
    report = solver.explain_unsat(solver.UnsatQuery('lambda', (
        solver.UnsatConstraint('array', (formula,)),
    )))
    binder, = (term for term in report.proof.terms if term.kind == 'quantifier')
    assert binder.operator == 'lambda'
    text_aligner.assert_equal('''\
Query: lambda
Solver result: UNSAT
Reading: complete

P1  Input
  Input origins: array
  Therefore: ((select((lambda i: Int. (#0 + 1)), 0) < 0) and false)

P2  Logical consequence
  From: P1
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text(detail='detailed'))


def test_indexed_operators_and_nonarithmetic_literals_keep_their_exact_values(text_aligner):
    bits = z3.BitVec('bits', 8)
    text = z3.String('text')
    formula = z3.And(bits == z3.BitVecVal(17, 8), z3.Extract(7, 4, bits) == 0,
                     text == z3.StringVal('abc'), z3.BoolVal(False))
    report = solver.explain_unsat(solver.UnsatQuery('indexed', (
        solver.UnsatConstraint('input', (formula,)),
    )))
    extraction, = (term for term in report.proof.terms if term.operator == 'extract')
    assert tuple((parameter.kind, parameter.value) for parameter in extraction.parameters) == (
        ('integer', '7'), ('integer', '4'))
    restored = solver.UnsatReport.from_canonical(report.to_canonical())
    assert restored.to_canonical() == report.to_canonical()
    text_aligner.assert_equal('''\
Query: indexed
Solver result: UNSAT
Reading: complete

P1  Input
  Input origins: input
  Therefore: ((#x11 = bits) and (extract[7, 4](bits) = #x0) and (text = "abc") and false)

P2  Logical consequence
  From: P1
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text(detail='detailed'))
