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


def test_large_unavailable_diagnostic_does_not_require_a_proof_graph(text_aligner):
    from dataclasses import replace
    from pyfcstm.solver.proof import ProofGap

    reading = explain_unsat(UnsatQuery('empty', ())).reading
    diagnostic = 'unavailable ' * 7000
    reading = replace(reading, graph=None, gaps=(ProofGap('unavailable', None, diagnostic),))
    text_aligner.assert_equal('Query: empty\nSolver result: SAT\nReading: not_requested\n'
                              'View: brief\n\nNo refutation is available.\n'
                              'Unexplained or invalid evidence:\n  unavailable: ' + diagnostic + '\n',
                              reading.to_text(detail='brief'))


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
        language, detail, text_aligner, proof_snapshot):
    report = proof_snapshot('conditional_long')
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


@pytest.mark.parametrize('operation', ['term', 'missing', 'brief', 'standard', 'detailed'])
def test_reading_does_not_expand_unused_shared_formulas(operation, text_aligner):
    """A small proof must not materialize an unrelated exponential expression."""
    import tracemalloc

    expression = z3.Int('unused')
    for _ in range(20):
        expression = expression + expression
    report = explain_unsat(UnsatQuery('unused_expression', (
        UnsatConstraint('unused', (expression > 0,)),
        UnsatConstraint('contradiction', (z3.BoolVal(False),)),
    )))
    root = report.proof.node(report.proof.root_id).conclusion
    tracemalloc.start()
    try:
        if operation == 'term':
            assert report.reading.get_term_text(root) == 'false'
        elif operation == 'missing':
            with pytest.raises(KeyError):
                report.reading.get_term_text('missing')
        else:
            simple = explain_unsat(UnsatQuery('unused_expression', (
                UnsatConstraint('contradiction', (z3.BoolVal(False),)),
            )))
            text_aligner.assert_equal(simple.reading.to_text(detail=operation),
                                      report.reading.to_text(detail=operation))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 1024 * 1024


@pytest.mark.parametrize('detail', ['brief', 'standard', 'detailed'])
def test_reading_renders_certificate_atoms_outside_native_proof_roots(detail, text_aligner):
    from pyfcstm.solver.proof import UnsatReport

    x = z3.Real('x')
    report = explain_unsat(UnsatQuery('square_alias', tuple(
        UnsatConstraint(str(index), (expression,)) for index, expression in enumerate(
            (x*x >= 1, x*x <= 0, x**2 >= 0)))))
    output = report.reading.to_text(detail=detail)
    loaded = UnsatReport.from_canonical(report.to_canonical())
    text_aligner.assert_equal(output, loaded.reading.to_text(detail=detail))


def test_mechanical_steps_inside_a_scope_fold_without_hiding_its_boundary(proof_snapshot):
    from pyfcstm.solver.proof.text import _compact_reading

    report = proof_snapshot('branches')
    before = report.to_canonical()
    compact = _compact_reading(report.reading)
    assert any(block.detail_block_ids and block.active_hypotheses for block in compact.blocks)
    boundaries = {block.block_id for block in report.reading.blocks
                  if block.kind in ('assumption', 'discharge')}
    assert boundaries <= {block.block_id for block in compact.blocks}
    assert {key for block in compact.blocks for key in block.evidence_node_ids} == {
        key for block in report.reading.blocks for key in block.evidence_node_ids}
    assert compact.get_block(compact.root_id).claims == report.reading.get_block(report.reading.root_id).claims
    assert compact.get_block(compact.root_id).active_hypotheses == ()
    assert report.to_canonical() == before


def test_automatic_compaction_builds_the_reading_index_once(monkeypatch, text_aligner):
    from pyfcstm.solver.proof.text import ProofReading

    values = z3.Ints(' '.join('x%d' % i for i in range(17)))
    formulas = [values[0] == 0] + [
        z3.Implies(values[i] >= 0, values[i+1] == values[i]+1) for i in range(16)
    ] + [values[-1] < 0]
    report = explain_unsat(UnsatQuery('indexed_chain', tuple(
        UnsatConstraint('condition_%d' % i, (formula,)) for i, formula in enumerate(formulas)
    )))
    expected = report.reading.to_text()
    original = ProofReading.__post_init__
    rebuilds = []

    def counted(reading, graph):
        rebuilds.append(len(reading.blocks))
        original(reading, graph)

    monkeypatch.setattr(ProofReading, '__post_init__', counted)
    text_aligner.assert_equal(expected, report.reading.to_text())
    assert len(rebuilds) <= 1


def test_standard_chain_reading_shares_repeated_reference_sequences(text_aligner):
    values = z3.Ints(' '.join('x%d' % i for i in range(51)))
    formulas = [values[0] == 0] + [
        z3.Implies(values[i] >= 0, values[i+1] == values[i]+1) for i in range(50)
    ] + [values[-1] < 0]
    report = explain_unsat(UnsatQuery('chain', tuple(
        UnsatConstraint('a%d' % i, (formula,)) for i, formula in enumerate(formulas)
    )))
    before = report.to_canonical()
    output = report.reading.to_text(detail='standard')
    assert len(output.encode('utf-8')) <= 96 * 1024
    restored = UnsatReport.from_canonical(before)
    text_aligner.assert_equal(output, restored.reading.to_text(detail='standard'))
    assert report.to_canonical() == before


def test_long_conditional_chain_has_bounded_guide_and_standard_views():
    values = z3.Ints(' '.join('x%d' % i for i in range(251)))
    formulas = [values[0] == 0] + [
        z3.Implies(values[i] >= 0, values[i + 1] == values[i] + 1) for i in range(250)
    ] + [values[-1] < 0]
    report = explain_unsat(UnsatQuery('long-chain', tuple(
        UnsatConstraint('a%d' % i, (formula,)) for i, formula in enumerate(formulas)
    )))
    assert report.reading_status == 'complete'
    assert report.gaps == ()
    sizes = {detail: len(report.reading.to_text(detail=detail).encode('utf-8'))
             for detail in ('brief', 'standard')}
    assert sizes['brief'] <= 64 * 1024, sizes
    assert sizes['standard'] <= 512 * 1024, sizes


@pytest.mark.parametrize('name', ['branches', 'conditional_long', 'round_tie'])
def test_standard_definitions_are_all_referenced_and_resolvable(name, proof_snapshot):
    import re
    from collections import Counter

    output = proof_snapshot(name).reading.to_text(detail='standard')
    declarations = re.findall(r'^  \[\[([^\]\n]+)\]\] =', output, re.MULTILINE)
    occurrences = Counter(re.findall(r'\[\[([^\]\n]+)\]\]', output))
    assert bool(declarations) == (name != 'branches')
    assert len(declarations) == len(set(declarations))
    assert set(occurrences) == set(declarations)
    assert all(count >= 2 for count in occurrences.values())


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_closed_step_guide_retains_original_block_references(language, proof_snapshot, text_aligner):
    from pyfcstm.solver.proof.text import _render_guide

    report = proof_snapshot('branches')
    before = report.to_canonical()
    output = _render_guide(report.reading, language)
    expected = Path(__file__).with_name('proof_readings') / ('branches.guide.%s.txt' % language)
    text_aligner.assert_equal(expected.read_text(encoding='utf-8'), output)
    for key in re.findall(r'^(p\d+)  ', output, re.MULTILINE):
        block = report.reading.get_block(key)
        assert block.active_hypotheses == ()
        assert report.reading.expand(key) == tuple(report.reading.get_block(parent)
                                                  for parent in block.premise_block_ids)
    assert report.to_canonical() == before


def test_guide_preserves_source_alternatives_and_omits_unused_sources(text_aligner):
    from pyfcstm.solver.proof import SourceDescription
    from pyfcstm.solver.proof.text import _render_guide

    report = explain_unsat(UnsatQuery('source-guide', (
        UnsatConstraint('first', (z3.BoolVal(False),),
                        SourceDescription('s1', 'First condition', 'rules.cfg', (1, 1, 1, 6), 'false')),
        UnsatConstraint('duplicate', (z3.BoolVal(False),), SourceDescription('s2', 'Second condition')),
        UnsatConstraint('unused', (z3.BoolVal(True),), SourceDescription('unused', 'Unused condition')),
    )))
    text_aligner.assert_equal('''\
Query: source-guide
Solver result: UNSAT
Reading: complete
View: brief
Guide only: key semantic steps. Internal branches and mechanical steps remain in standard/detailed.
Block IDs work with get_block(id) and expand(id); formulas expand with get_term_text(id).

p0  Input: false
  Input origin alternatives: first, duplicate
  Source links: logical:s1, logical:s2

Sources:
  s1: First condition [rules.cfg] 1:1-1:6
    false
  s2: Second condition

Conclusion: the submitted conjunction is inconsistent.
''', _render_guide(report.reading, 'en'))


def test_guide_keeps_domain_fold_identity(text_aligner, captured_branch_proof):
    from pyfcstm.solver.proof.text import _render_guide
    from .test_extensions import _branch_query

    def propose(reading):
        root = reading.get_block(reading.root_id)
        return (FoldProposal(root.block_id, tuple(block.block_id for block in reading.blocks), (),
                             root.claims, (), 'Both cases contradict the goal', '两个分支均与目标矛盾'),)

    report = explain_unsat(_branch_query(), extensions=ProofExtensions(reading_folders=(ReadingFolder(propose),)))
    text_aligner.assert_equal('''\
Query: branches
Solver result: UNSAT
Reading: complete
View: brief
Guide only: key semantic steps. Internal branches and mechanical steps remain in standard/detailed.
Block IDs work with get_block(id) and expand(id); formulas expand with get_term_text(id).

fold:p47  Both cases contradict the goal: false

Conclusion: the submitted conjunction is inconsistent.
''', _render_guide(report.reading, 'en'))
    assert report.reading.expand('fold:p47')


def test_guide_of_a_local_refutation_keeps_its_condition_and_gap(proof_snapshot, text_aligner):
    from dataclasses import replace
    from pyfcstm.solver.proof import ProofGap
    from pyfcstm.solver.proof.text import _render_guide

    reading = proof_snapshot('branches').reading
    root = reading.get_block('p43')
    assert root.active_hypotheses == ('n38',)
    index = reading.blocks.index(root)
    local = replace(reading, graph=reading._graph, root_id=root.block_id,
                    blocks=reading.blocks[:index + 1], status='partial',
                    gaps=(ProofGap('analysis_incomplete', 'n43', 'local excerpt'),))
    text_aligner.assert_equal('''\
Query: branches
Solver result: UNSAT
Reading: partial
View: brief
Guide only: key semantic steps. Internal branches and mechanical steps remain in standard/detailed.
Block IDs work with get_block(id) and expand(id); formulas expand with get_term_text(id).

p0  Input: (y < 0)
  Input origins: goal
p7  Input: (y = (if (x >= 0) then (x + 1) else 0))
  Input origins: update
p43  Exact linear combination: false
  Conditional on hypotheses (graph.node): n38
  Combine 4 bounds: 2 <= 0; contradiction.

The root conclusion still depends on local hypotheses.
Unexplained or invalid evidence:
  analysis_incomplete [n43]: local excerpt
''', _render_guide(local, 'en'))


def test_shared_collections_reserve_graph_ids_and_preserve_repeated_items(text_aligner):
    from pyfcstm.solver.proof.text import _References

    definitions = {}
    references = _References(definitions, ('share0',))
    items = tuple('a%d' % i for i in range(17)) + ('a0',)
    assert references.join(items, ' + ', True) == '[[share1]] + a16'
    text_aligner.assert_equal('''\
share1 = (a0 + a0 + a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10 + a11 + a12 + a13 + a14 + a15)
''', ''.join('%s = %s\n' % item for item in definitions.items()))
