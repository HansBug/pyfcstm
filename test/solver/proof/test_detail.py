"""Reading detail changes presentation without changing captured evidence."""

import re
from pathlib import Path

import pytest
import z3

from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat
from pyfcstm.solver.proof import (
    FoldProposal, ProofExtensions, ProofRuleHandler, ReadingFolder, RuleAnalysis, UnsatReport,
)


pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('detail', ['brief', 'standard', 'detailed'])
def test_no_refutation_has_an_explicit_reading_level(detail, text_aligner):
    reading = explain_unsat(UnsatQuery('empty', ())).reading
    header = '' if detail == 'detailed' else 'View: %s\n' % detail
    text_aligner.assert_equal(
        'Query: empty\nSolver result: SAT\nReading: not_requested\n' + header +
        '\nNo refutation is available.\n', reading.to_text(detail=detail))


def test_default_detail_is_standard(text_aligner):
    reading = explain_unsat(UnsatQuery('empty', ())).reading
    text_aligner.assert_equal(
        'Query: empty\nSolver result: SAT\nReading: not_requested\n'
        'View: standard\n\nNo refutation is available.\n', reading.to_text())


@pytest.mark.parametrize('detail', ['unknown', '', None, 1])
def test_unknown_detail_is_rejected(detail):
    reading = explain_unsat(UnsatQuery('empty', ())).reading
    with pytest.raises(ValueError, match='detail must be brief, standard or detailed'):
        reading.to_text(detail=detail)


@pytest.mark.parametrize('detail', ['brief', 'standard'])
def test_increment_combines_normalization_with_the_arithmetic_step(detail, text_aligner):
    x, y = z3.Ints('x y')
    report = explain_unsat(UnsatQuery('increment', (
        UnsatConstraint('initial', (x >= 0,)),
        UnsatConstraint('update', (y == x + 1,)),
        UnsatConstraint('goal', (y < 0,)),
    )))
    before = report.to_canonical()
    arithmetic = ('  Combination: 3 inequalities; sum 2 <= 0; contradiction.\n'
                  if detail == 'brief' else
                  '  1 * [-1 * x <= 0]\n  1 * [y + 1 <= 0]\n'
                  '  1 * [x + -1 * y + 1 <= 0]\n  Sum: 2 <= 0; contradiction.\n')
    note = ('Guide only; use standard or detailed for the derivation.\n'
            if detail == 'brief' else '')
    expected = '''\
Query: increment
Solver result: UNSAT
Reading: complete
View: %s
%s
P1  Input
  Input origins: initial
  Therefore: (x >= 0)

P2  Input
  Input origins: goal
  Therefore: (y < 0)

P3  Input
  Input origins: update
  Therefore: (y = (x + 1))

P4  Propagate premises; Exact linear combination
  From: P1, P2, P3
%s  Therefore: false
  Expandable proof steps: 3

Conclusion: the submitted conjunction is inconsistent.
''' % (detail, note, arithmetic)
    text_aligner.assert_equal(expected, report.reading.to_text(detail=detail))
    assert report.to_canonical() == before
    restored = UnsatReport.from_canonical(before)
    text_aligner.assert_equal(expected, restored.reading.to_text(detail=detail))


def test_standard_names_shared_long_formulas_and_keeps_their_exact_definition(text_aligner):
    predicate = z3.Or(*z3.Bools(' '.join('condition_%02d' % i for i in range(12))))
    report = explain_unsat(UnsatQuery('long', (
        UnsatConstraint('positive', (predicate,)),
        UnsatConstraint('negative', (z3.Not(predicate),)),
    )))
    text_aligner.assert_equal('''\
Query: long
Solver result: UNSAT
Reading: complete
View: standard

P1  Input
  Input origins: positive
  Therefore: [[t12]]

P2  Input
  Input origins: negative
  Therefore: not ([[t12]])

P3  Propagate premises; Resolve the clauses
  From: P1, P2
  Therefore: false
  Expandable proof steps: 13

Formula definitions:
  [[t12]] = (condition_00 or condition_01 or condition_02 or condition_03 or
    condition_04 or condition_05 or condition_06 or condition_07 or condition_08
    or condition_09 or condition_10 or condition_11)

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text())
    text_aligner.assert_equal(
        '(condition_00 or condition_01 or condition_02 or condition_03 or condition_04 or '
        'condition_05 or condition_06 or condition_07 or condition_08 or condition_09 or '
        'condition_10 or condition_11)', report.reading.get_term_text('t12'))
    with pytest.raises(KeyError):
        report.reading.get_term_text('missing')


def test_term_text_without_a_graph_is_unavailable():
    reading = explain_unsat(UnsatQuery('empty', ())).reading
    with pytest.raises(ValueError, match='no proof graph'):
        reading.get_term_text('missing')


def test_brief_defers_long_formulas_but_keeps_an_offline_lookup(text_aligner):
    predicate = z3.Or(*z3.Bools(' '.join('condition_%02d' % i for i in range(12))))
    report = explain_unsat(UnsatQuery('long', (
        UnsatConstraint('positive', (predicate,)),
        UnsatConstraint('negative', (z3.Not(predicate),)),
    )))
    text_aligner.assert_equal('''\
Query: long
Solver result: UNSAT
Reading: complete
View: brief
Guide only; use standard or detailed for the derivation.

P1  Input
  Input origins: positive
  Therefore: [[t12]]

P2  Input
  Input origins: negative
  Therefore: not ([[t12]])

P3  Propagate premises; Resolve the clauses
  From: P1, P2
  Therefore: false
  Expandable proof steps: 13

Formula references (expand with get_term_text):
  [[t12]]

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text(detail='brief'))


def test_detailed_expands_nested_domain_folds_offline(text_aligner):
    before = []

    def fold(reading):
        before.append(reading.to_text(detail='detailed'))
        root = reading.get_block(reading.root_id)
        yield FoldProposal(root.block_id, tuple(b.block_id for b in reading.blocks), (),
                           root.claims, (), 'Conflicting conditions', '条件冲突')

    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('folded', (
        UnsatConstraint('lower', (x >= 1,)), UnsatConstraint('upper', (x <= 0,)),
    )), extensions=ProofExtensions(reading_folders=(ReadingFolder(fold), ReadingFolder(fold))))
    assert report.reading.blocks[0].kind == 'domain'
    loaded = UnsatReport.from_canonical(report.to_canonical())
    text_aligner.assert_equal(before[0], loaded.reading.to_text(detail='detailed'))
    assert len(loaded.reading.blocks) == 1


def test_formula_appendix_omits_unreferenced_internal_rewrites(text_aligner):
    predicates = z3.Bools(' '.join('condition_%02d' % i for i in range(12)))
    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('simplified', (
        UnsatConstraint('conditions', (z3.And(*predicates, x > 0, x < 0),)),
    )))
    text_aligner.assert_equal('''\
Query: simplified
Solver result: UNSAT
Reading: complete
View: standard

P1  Exact linear combination
  To refute the negated conclusion, temporarily assume:
    not ((x >= 0))
    not ((x <= 0))
  1 * [x + 1 <= 0]
  1 * [-1 * x + 1 <= 0]
  Sum: 2 <= 0; contradiction.
  Discharge these temporary assumptions.
  Therefore: ((x >= 0) or (x <= 0))

P2  Input
  Input origins: conditions
  Therefore: [[t16]]

P3  Propagate premises; Resolve the clauses
  From: P1, P2
  Therefore: false
  Expandable proof steps: 3

Formula definitions:
  [[t16]] = (condition_00 and condition_01 and condition_02 and condition_03 and
    condition_04 and condition_05 and condition_06 and condition_07 and
    condition_08 and condition_09 and condition_10 and condition_11 and (x > 0)
    and (x < 0))

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text())


@pytest.mark.parametrize('language', ['en', 'zh'])
@pytest.mark.parametrize('detail', ['brief', 'standard', 'detailed'])
def test_conditional_with_a_large_guard_keeps_scopes_and_only_referenced_formulas(
        language, detail, text_aligner):
    predicates = z3.Bools(' '.join('condition_%02d' % i for i in range(12)))
    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('conditional', (
        UnsatConstraint('update', (z3.If(z3.Or(*predicates), x + 1, x + 2) == 0,)),
        UnsatConstraint('initial', (x >= 0,)),
    )))
    assert report.reading_status == 'complete'
    snapshot = Path(__file__).with_name('proof_readings') / ('conditional_long.%s.%s.txt' % (detail, language))
    # Z3's auxiliary-name counters are process-wide. Normalize only those two
    # identities; compare the entire proof, including formulas and scopes.
    output = re.sub(r'z3name!\d+', 'VALUE', report.reading.to_text(language, detail))
    output = re.sub(r'k!\d+', 'CHOICE', output)
    text_aligner.assert_equal(snapshot.read_text(encoding='utf-8'), output)


@pytest.mark.parametrize('detail', ['brief', 'standard'])
def test_unchecked_extension_steps_are_never_hidden_by_automatic_folding(detail, text_aligner):
    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('unsupported', (
        UnsatConstraint('lower', (x >= 1,)), UnsatConstraint('upper', (x <= 0,)),
    )), extensions=ProofExtensions(rule_handlers=(
        ProofRuleHandler('th-lemma', lambda node, graph: RuleAnalysis('logical', 'unsupported')),
    )))
    note = ('Guide only; use standard or detailed for the derivation.\n'
            if detail == 'brief' else '')
    text_aligner.assert_equal('''\
Query: unsupported
Solver result: UNSAT
Reading: partial
View: %s
%s
P1  Logical consequence
  Therefore: (not ((x <= 0)) or not ((x >= 1)))

P2  Input
  Input origins: lower
  Therefore: (x >= 1)

P3  Input
  Input origins: upper
  Therefore: (x <= 0)

P4  Resolve the clauses
  From: P1, P2, P3
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
Unexplained or invalid evidence:
  unsupported_rule: th-lemma
''' % (detail, note), report.reading.to_text(detail=detail))
