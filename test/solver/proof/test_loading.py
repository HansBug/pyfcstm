"""Portable proof snapshots validate identities before offline navigation."""

import json
import subprocess
import sys

import pytest
import z3

from pyfcstm.solver import UnsatConstraint, UnsatQuery, UnsatReport, explain_unsat


pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('mutation', ['contribution', 'assignment', 'required', 'assumptions'])
def test_loading_replays_counting_from_local_premises(mutation):
    p, q, s = z3.Bools('p q s')
    report = explain_unsat(UnsatQuery('count', (
        UnsatConstraint('limit', (z3.AtMost(p, q, s, 1),)),
        UnsatConstraint('p', (p,)), UnsatConstraint('q', (q,)),
    )))
    data = json.loads(json.dumps(report.to_canonical()))
    evidence = next(node['cardinality'] for node in data['proof']['nodes'] if node['cardinality'])
    if mutation == 'contribution':
        for item in evidence['contributions']:
            item['minimum'] = item['maximum'] = 1
    elif mutation == 'assignment':
        evidence['assignments'][0][1] = not evidence['assignments'][0][1]
    elif mutation == 'required':
        evidence['constraint_value'] = not evidence['constraint_value']
    else:
        evidence['assumptions'] = []
    with pytest.raises(ValueError, match='invalid cardinality derivation'):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('mutation', ['endpoint', 'bound', 'rule'])
def test_loading_replays_interval_steps_from_local_premises(mutation):
    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('square', (UnsatConstraint('condition', (x*x == 2,)),)))
    data = json.loads(json.dumps(report.to_canonical()))
    evidence = next(node['interval'] for node in data['proof']['nodes'] if node['interval'])
    if mutation == 'endpoint':
        evidence['steps'][0]['lower'] = '123456'
    elif mutation == 'bound':
        evidence['bounds'][0]['constant'] = '123456'
    else:
        evidence['steps'][0]['rule'] = 'literal'
        evidence['steps'][0]['bound_index'] = None
    with pytest.raises(ValueError, match='invalid interval derivation'):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('family', ['interval', 'cardinality'])
def test_generated_certificate_replay_failure_warns_and_keeps_the_gap(monkeypatch, family):
    from dataclasses import replace
    from pyfcstm.solver.proof import interval, rules

    p, q, s = z3.Bools('p q s')
    x = z3.Int('x')
    expressions = (x*x == 2,) if family == 'interval' else (z3.AtMost(p, q, s, 1), p, q)
    query = UnsatQuery(family, (UnsatConstraint('conditions', expressions),))
    module, name = (interval, 'interval_certificate') if family == 'interval' else (rules, '_cardinality_certificate')
    original = getattr(module, name)

    def corrupt(*args, **kwargs):
        certificate = original(*args, **kwargs)
        if certificate is None:
            return None
        if family == 'interval':
            return replace(certificate, steps=(replace(certificate.steps[0], lower='123456'),) + certificate.steps[1:])
        return replace(certificate, constraint_value=not certificate.constraint_value)

    monkeypatch.setattr(module, name, corrupt)
    with pytest.warns(RuntimeWarning, match='invalid_' + family + '_certificate'):
        report = explain_unsat(query)
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'partial'
    assert any(gap.reason == 'invalid_' + family + '_certificate' for gap in report.gaps)
    assert all(getattr(node, family) is None for node in report.proof.nodes)


def _report():
    x = z3.Real('x')
    return explain_unsat(UnsatQuery('interval', (
        UnsatConstraint('lower', (x >= 2,)), UnsatConstraint('upper', (x < 1,)),
    )), minimize=True)


def test_json_roundtrip_preserves_all_proof_and_reading_data(text_aligner):
    original = _report()
    decoded = json.loads(json.dumps(original.to_canonical()))
    restored = UnsatReport.from_canonical(decoded)
    assert restored.to_canonical() == original.to_canonical()
    for language in ('en', 'zh'):
        text_aligner.assert_equal(original.reading.to_text(language), restored.reading.to_text(language))
    decoded['proof']['nodes'].clear()
    assert restored.proof.nodes == original.proof.nodes


def test_reading_claim_must_match_its_evidence():
    report = explain_unsat(UnsatQuery('false_input', (
        UnsatConstraint('false', (z3.BoolVal(False),)),
        UnsatConstraint('true', (z3.BoolVal(True),)),
    )))
    data = report.to_canonical()
    true_id = next(term.term_id for term in report.proof.terms if term.value == 'true')
    data['reading']['blocks'][0]['claims'] = (true_id,)
    with pytest.raises(ValueError, match='reading claims disagree with evidence'):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('mutation', ['wrong_occurrence', 'missing_occurrence', 'wrong_relation'])
def test_logical_source_links_belong_to_the_displayed_evidence(mutation):
    from pyfcstm.solver.proof import SourceDescription

    report = explain_unsat(UnsatQuery('sources', (
        UnsatConstraint('false', (z3.BoolVal(False),), SourceDescription('bad', 'Impossible condition')),
        UnsatConstraint('true', (z3.BoolVal(True),), SourceDescription('unused', 'Unrelated condition')),
    )))
    data = report.to_canonical()
    link = data['reading']['blocks'][0]['source_links'][0]
    if mutation == 'wrong_occurrence':
        link['occurrence_id'] = next(item.occurrence_id for item in report.proof.inputs if item.constraint_id == 'true')
    elif mutation == 'missing_occurrence':
        link['occurrence_id'] = None
    else:
        link['relation'] = 'context'
    with pytest.raises(ValueError, match='source link disagrees with evidence'):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('mutation', ['unrelated_binding', 'wrong_description'])
def test_construction_source_links_match_an_occurrence_in_the_evidence(mutation):
    from pyfcstm.solver.proof import ProofExtensions, SourceAdapter, SourceBinding, SourceDescription

    x, y = z3.Ints('x y')
    class Sources(SourceAdapter):
        def bindings(self):
            return (SourceBinding(x, SourceDescription('x-source', 'Relevant variable')),
                    SourceBinding(y, SourceDescription('y-source', 'Unrelated variable')))

    report = explain_unsat(UnsatQuery('sources', (
        UnsatConstraint('lower', (x >= 1,)), UnsatConstraint('upper', (x <= 0,)),
        UnsatConstraint('unused', (y >= 0,)),
    )), extensions=ProofExtensions(source_adapter=Sources()))
    data = report.to_canonical()
    link = next(link for block in data['reading']['blocks'] for link in block['source_links'])
    link['source_id'] = 'y-source'
    if mutation == 'unrelated_binding':
        link['term_id'] = next(term.term_id for term in report.proof.terms if term.value == 'y')
    with pytest.raises(ValueError, match='source link disagrees with evidence'):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('folded', [False, True])
def test_multiple_expression_sources_survive_loading_and_folding(folded, text_aligner):
    from .test_extensions import _interval_fold
    from pyfcstm.solver.proof import ProofExtensions, ReadingFolder, SourceAdapter, SourceBinding, SourceDescription

    x, y = z3.Ints('x y')
    class Sources(SourceAdapter):
        def bindings(self):
            return (SourceBinding(x, SourceDescription('x-source', 'First variable')),
                    SourceBinding(y, SourceDescription('y-source', 'Second variable')))

    folders = (ReadingFolder(lambda reading: (_interval_fold(reading),)),) if folded else ()
    report = explain_unsat(UnsatQuery('combined_sources', (
        UnsatConstraint('lower', (x+y >= 1,)), UnsatConstraint('upper', (x+y <= 0,)),
    )), extensions=ProofExtensions(source_adapter=Sources(), reading_folders=folders))
    assert any(len(block.source_links) >= 2 for block in report.reading.blocks)
    loaded = UnsatReport.from_canonical(report.to_canonical())
    assert loaded.to_canonical() == report.to_canonical()
    for language in ('en', 'zh'):
        text_aligner.assert_equal(report.reading.to_text(language), loaded.reading.to_text(language))


@pytest.mark.parametrize('mutation', ['scope', 'premises', 'root'])
def test_reading_cannot_change_the_native_derivation_boundary(proof_snapshot, mutation):
    data = proof_snapshot('branches').to_canonical()
    blocks = data['reading']['blocks']
    if mutation == 'scope':
        next(block for block in blocks if block['active_hypotheses'])['active_hypotheses'] = ()
    elif mutation == 'premises':
        next(block for block in blocks if block['premise_block_ids'])['premise_block_ids'] = ()
    else:
        data['reading']['root_id'] = blocks[0]['block_id']
    with pytest.raises(ValueError, match='reading .* disagree'):
        UnsatReport.from_canonical(data)


def test_offline_loading_does_not_import_z3_or_the_bmc_stack(tmp_path, text_aligner):
    report = _report()
    snapshot = tmp_path / 'proof.json'
    snapshot.write_text(json.dumps(report.to_canonical()), encoding='utf-8')
    script = '''
import importlib.abc
import json
import sys
class BlockNative(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'z3' or fullname.startswith(('z3.', 'pyfcstm.bmc')):
            raise ImportError('offline reader must not import ' + fullname)
sys.meta_path.insert(0, BlockNative())
from pyfcstm.solver import UnsatReport
with open(sys.argv[1], encoding='utf-8') as stream:
    report = UnsatReport.from_canonical(json.load(stream))
print(report.reading.to_text(), end='')
'''
    result = subprocess.run([sys.executable, '-c', script, str(snapshot)],
                            capture_output=True, encoding='utf-8', check=True)
    text_aligner.assert_equal(report.reading.to_text(), result.stdout)
    assert result.stderr == ''


@pytest.mark.parametrize('mode', ['core', 'proof'])
def test_sat_and_unavailable_graphs_roundtrip(mode, text_aligner):
    original = explain_unsat(UnsatQuery('empty', ()), mode=mode)
    restored = UnsatReport.from_canonical(json.loads(json.dumps(original.to_canonical())))
    assert restored.to_canonical() == original.to_canonical()
    text_aligner.assert_equal(original.reading.to_text(), restored.reading.to_text())


@pytest.mark.parametrize('location,value', [
    (('solver_status',), 'definitely'),
    (('proof', 'root_id'), 'missing'),
    (('proof', 'nodes', 0, 'parents'), ['missing']),
    (('proof', 'terms', 0, 'arguments'), ['missing']),
    (('proof', 'inputs', 0, 'term_id'), 'missing'),
    (('proof', 'inputs', 0, 'expression_index'), True),
    (('proof', 'inputs', 0, 'expression_index'), -1),
    (('proof', 'nodes', 0, 'local_check'), 'maybe'),
    (('proof', 'terms', 0, 'kind'), 'unknown'),
    (('reading', 'blocks', 0, 'claims'), ['missing']),
    (('reading', 'blocks', 0, 'premise_block_ids'), ['missing']),
    (('reading', 'root_id'), 'missing'),
    (('reading', 'status'), 'perfect'),
    (('core', 'core_ids'), ['not-an-input']),
])
def test_loader_rejects_malformed_public_snapshots(location, value):
    data = json.loads(json.dumps(_report().to_canonical()))
    target = data
    for key in location[:-1]:
        target = target[key]
    target[location[-1]] = value
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('table,id_field', [('nodes', 'node_id'), ('terms', 'term_id'), ('inputs', 'occurrence_id')])
def test_loader_rejects_duplicate_identities(table, id_field):
    data = json.loads(json.dumps(_report().to_canonical()))
    data['proof'][table].append(data['proof'][table][0])
    with pytest.raises(ValueError, match='duplicate'):
        UnsatReport.from_canonical(data)


def test_loader_rejects_cycles_in_proof_and_reading():
    for reading_cycle in (False, True):
        data = json.loads(json.dumps(_report().to_canonical()))
        if reading_cycle:
            block = data['reading']['blocks'][0]
            block['premise_block_ids'] = [block['block_id']]
        else:
            node = data['proof']['nodes'][0]
            node['parents'] = [node['node_id']]
        with pytest.raises(ValueError):
            UnsatReport.from_canonical(data)


def test_loader_rejects_extra_fields_and_missing_required_fields():
    data = json.loads(json.dumps(_report().to_canonical()))
    data['schema_version'] = 'invented'
    with pytest.raises(ValueError, match='fields'):
        UnsatReport.from_canonical(data)
    data.pop('schema_version')
    data.pop('query_id')
    with pytest.raises(ValueError, match='fields'):
        UnsatReport.from_canonical(data)


def test_package_solve_remains_callable_after_importing_the_submodule():
    script = '''
from pyfcstm.solver.solve import SolveResult
from pyfcstm.solver import solve
assert callable(solve)
assert isinstance(solve([], max_solutions=1), SolveResult)
'''
    subprocess.run([sys.executable, '-c', script], check=True, capture_output=True)


@pytest.mark.parametrize('change', ['missing_graph', 'missing_scope', 'non_false_root',
                                   'reading_gaps', 'duplicate_core', 'invalid_application'])
def test_loader_rejects_self_contradictory_report_contracts(change):
    data = json.loads(json.dumps(_report().to_canonical()))
    if change == 'missing_graph':
        data['proof'] = None
        data['reading'] = None
    elif change == 'missing_scope':
        data['proof_scope'] = 'none'
    elif change == 'non_false_root':
        data['proof']['nodes'][-1]['conclusion'] = data['proof']['inputs'][0]['term_id']
    elif change == 'reading_gaps':
        data['reading']['gaps'] = [{'reason': 'unsupported_rule', 'node_id': None, 'detail': 'missing'}]
    elif change == 'duplicate_core':
        data['core']['core_ids'].append(data['core']['core_ids'][0])
    else:
        data['proof']['terms'][0].update(kind='application', operator='not', operator_kind='builtin')
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)


def test_domain_folds_and_source_relationships_survive_offline_roundtrip(text_aligner):
    from pyfcstm.solver import (FoldProposal, ProofExtensions, ReadingFolder,
                               SourceAdapter, SourceBinding, SourceDescription)

    x = z3.Int('x')
    location = SourceDescription('assignment', 'Capacity definition', 'rules.cfg', (1, 1, 1, 8), 'x := 0')

    class Sources(SourceAdapter):
        def bindings(self):
            return (SourceBinding(x, location, 'context'),)

    def propose(reading):
        root = reading.get_block(reading.root_id)
        yield FoldProposal(root.block_id, tuple(block.block_id for block in reading.blocks),
                           (), root.claims, root.active_hypotheses, 'Capacity conflict', '容量冲突')

    original = explain_unsat(UnsatQuery('capacity', (
        UnsatConstraint('lower', (x > 0,), location),
        UnsatConstraint('upper', (x <= 0,)),
    )), extensions=ProofExtensions(source_adapter=Sources(), reading_folders=(ReadingFolder(propose),)))
    restored = UnsatReport.from_canonical(json.loads(json.dumps(original.to_canonical())))
    assert restored.to_canonical() == original.to_canonical()
    assert len(restored.reading.expand(restored.reading.root_id)) == len(original.reading.blocks[0].detail_block_ids)
    for language in ('en', 'zh'):
        text_aligner.assert_equal(original.reading.to_text(language), restored.reading.to_text(language))


@pytest.mark.parametrize('location,value', [
    (('query_id',), ''),
    (('proof', 'terms'), {}),
    (('proof', 'terms', 0, 'kind'), 'quantifier'),
    (('proof', 'terms', 1, 'value'), '1/0'),
    (('proof', 'terms', 1, 'value'), 'not-a-number'),
    (('proof', 'nodes', 0, 'certificate', 'weights'), []),
    (('reading', 'root_id'), None),
    (('proof',), None),
    (('reading', 'blocks', 0, 'evidence_node_ids'), []),
    (('reading', 'blocks', 0, 'kind'), 'domain'),
    (('core', 'core_check'), 'unknown'),
    (('core',), None),
    (('scope_check',), 'partial'),
])
def test_loader_reports_invalid_shapes_and_cross_field_invariants(location, value):
    data = json.loads(json.dumps(_report().to_canonical()))
    target = data
    for key in location[:-1]:
        target = target[key]
    target[location[-1]] = value
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('mutation', ['unverified', 'missing_input', 'wrong_background'])
def test_core_proof_requires_its_verified_input_groups(mutation):
    data = json.loads(json.dumps(_report().to_canonical()))
    if mutation == 'unverified':
        data['core'].update(core_ids=None, core_check='not_checked',
                            subset_minimality='not_proven', reduction='raw')
    elif mutation == 'missing_input':
        data['core']['core_ids'] = data['core']['core_ids'][:-1]
    else:
        data['proof']['inputs'][0]['background'] = True
    with pytest.raises(ValueError, match='core'):
        UnsatReport.from_canonical(data)


def test_loader_rejects_unverified_minimality_and_proof_on_a_sat_report():
    data = json.loads(json.dumps(explain_unsat(UnsatQuery('empty', ()), mode='core').to_canonical()))
    data['core']['subset_minimality'] = 'proven'
    with pytest.raises(ValueError, match='minimality'):
        UnsatReport.from_canonical(data)
    data = json.loads(json.dumps(_report().to_canonical()))
    data['solver_status'] = data['reading']['solver_status'] = 'sat'
    with pytest.raises(ValueError, match='UNSAT'):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('span', [(1, 2), (0, 1, 1, 2), (2, 1, 1, 2)])
def test_loader_rejects_malformed_source_spans(span):
    from pyfcstm.solver import SourceDescription

    report = explain_unsat(UnsatQuery('false', (
        UnsatConstraint('false', (z3.BoolVal(False),), SourceDescription('source', 'Impossible')),
    )))
    data = json.loads(json.dumps(report.to_canonical()))
    data['reading']['sources'][0]['span'] = span
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)


def test_loader_accepts_sources_without_a_span():
    from pyfcstm.solver import SourceDescription

    report = explain_unsat(UnsatQuery('false', (
        UnsatConstraint('false', (z3.BoolVal(False),), SourceDescription('source', 'Impossible')),
    )))
    assert UnsatReport.from_canonical(report.to_canonical()).reading.get_source('source').span is None


def test_loader_rejects_empty_builtin_application():
    data = json.loads(json.dumps(_report().to_canonical()))
    data['proof']['terms'][0].update(kind='application', operator='+', operator_kind='builtin')
    with pytest.raises(ValueError, match='arguments'):
        UnsatReport.from_canonical(data)


def test_public_exports_are_visible_to_introspection_and_unknown_names_fail():
    import pyfcstm.solver as package

    assert set(package.__all__) <= set(dir(package))
    with pytest.raises(AttributeError, match='has no attribute'):
        getattr(package, 'not_a_solver_api')


def test_algebraic_literals_keep_their_exact_value_offline(text_aligner):
    x = z3.Real('x')
    algebraic = z3.simplify(z3.Sqrt(2))
    report = explain_unsat(UnsatQuery('algebraic', (
        UnsatConstraint('value', (x == algebraic,)),
        UnsatConstraint('impossible', (z3.BoolVal(False),)),
    )))
    restored = UnsatReport.from_canonical(json.loads(json.dumps(report.to_canonical())))
    assert restored.to_canonical() == report.to_canonical()
    term = next(term for term in restored.proof.terms if term.value == algebraic.sexpr())
    assert term.kind == 'algebraic'
    text_aligner.assert_equal('''Query: algebraic
Solver result: UNSAT
Reading: complete

P1  Input
  Input origins: impossible
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
''', restored.reading.to_text(detail='detailed'))


@pytest.mark.parametrize('reference', ['hidden_hypothesis', 'input_hypothesis', 'hidden_premise', 'gap'])
def test_loader_checks_the_roles_and_visibility_of_reading_references(reference):
    data = json.loads(json.dumps(_report().to_canonical()))
    blocks = data['reading']['blocks']
    if reference == 'hidden_hypothesis':
        visible = {block['evidence_node_ids'][0] for block in blocks}
        hidden = next(node['node_id'] for node in data['proof']['nodes'] if node['node_id'] not in visible)
        blocks[-1]['active_hypotheses'] = [hidden]
    elif reference == 'input_hypothesis':
        blocks[-1]['active_hypotheses'] = [blocks[0]['evidence_node_ids'][0]]
    elif reference == 'hidden_premise':
        data['reading']['detail_blocks'].append(blocks.pop(0))
    else:
        gaps = [{'reason': 'unsupported_rule', 'node_id': 'missing', 'detail': 'Missing evidence'}]
        data['gaps'] = data['reading']['gaps'] = gaps
        data['reading_status'] = data['reading']['status'] = 'partial'
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)


def test_loader_rejects_gap_references_when_no_graph_exists():
    data = explain_unsat(UnsatQuery('empty', ())).to_canonical()
    data['gaps'] = ({'reason': 'unsupported_rule', 'node_id': 'missing', 'detail': 'Missing evidence'},)
    data['reading'] = None
    with pytest.raises(ValueError):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('mutation,message', [
    ('zero_coefficient', 'monomials must be normalized'),
    ('negative_weight', 'weights must be nonnegative'),
    ('missing_literal', 'only polynomial inputs'),
    ('empty_steps', 'must contain a contradiction'),
    ('forward_reference', 'must reference earlier steps'),
    ('wrong_square', 'invalid polynomial derivation'),
])
def test_loader_rejects_changed_polynomial_certificates(mutation, message):
    x = z3.Real('x')
    report = explain_unsat(UnsatQuery('quartic', (
        UnsatConstraint('impossible', (x*x*x*x + 1 == 0,)),
    )))
    data = report.to_canonical()
    node = next(node for node in data['proof']['nodes'] if node['polynomial'] is not None)
    certificate = node['polynomial']
    steps = certificate['steps']
    if mutation == 'zero_coefficient':
        steps[0]['coefficients'] = (((), '0'),)
    elif mutation == 'negative_weight':
        steps[-1]['weights'] = ('-1',) + steps[-1]['weights'][1:]
    elif mutation == 'missing_literal':
        steps[0]['term_id'] = None
    elif mutation == 'empty_steps':
        certificate['steps'] = ()
    elif mutation == 'forward_reference':
        steps[-1]['premises'] = (len(steps),)
    else:
        square = next(step for step in steps if step['rule'] == 'square')
        square['factor'] = (((), '2'),)
    with pytest.raises(ValueError, match=message):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('mutation,message', [
    ('missing_weights', 'bounds and weights must align'),
    ('not_opposing', 'integer-free range'),
    ('wrong_sum', 'integer-free range'),
    ('real_atom', 'requires integer terms'),
    ('nonopposite_coefficients', 'opposing coefficient vectors'),
    ('wrong_conclusion', 'invalid divisibility derivation'),
    ('missing_premise', 'invalid divisibility derivation'),
    ('changed_literal', 'invalid divisibility derivation'),
])
def test_loader_rejects_changed_divisibility_certificates(mutation, message):
    from dataclasses import replace
    from .test_integer import _graph, _check

    graph = _graph()
    root = replace(graph.node('root'), divisibility=_check(graph), inference_kind='divisibility')
    graph = replace(graph, nodes=graph.nodes[:-1] + (root,))
    data = UnsatReport('divisibility', 'unsat', 'captured', graph).to_canonical()
    certificate = data['proof']['nodes'][-1]['divisibility']
    if mutation == 'missing_weights':
        certificate['weights'] = ()
    elif mutation == 'not_opposing':
        certificate['bound_pairs'][0][1]['constant'] = '100'
    elif mutation == 'wrong_sum':
        certificate['lower'] = '1/3'
    elif mutation == 'nonopposite_coefficients':
        certificate['bound_pairs'][0][0]['coefficients'] = (('x', '1'),)
    elif mutation == 'wrong_conclusion':
        data['proof']['nodes'][-1]['conclusion'] = 'upper'
    elif mutation == 'missing_premise':
        data['proof']['nodes'][-1]['parents'] = ('y_upper', 'lower', 'y_lower')
    elif mutation == 'changed_literal':
        next(term for term in data['proof']['terms'] if term['term_id'] == 'one')['value'] = '2'
    else:
        next(term for term in data['proof']['terms'] if term['term_id'] == 'x')['sort'] = 'Real'
    with pytest.raises(ValueError, match=message):
        UnsatReport.from_canonical(data)


def test_loader_rejects_linear_evidence_for_a_different_conclusion():
    from dataclasses import replace
    from .test_polynomial import _graph
    from pyfcstm.solver.budget import SolveBudget
    from pyfcstm.solver.proof.rules import _linear_equality

    graph = _graph((('<=', 'x', 'y'), ('<=', 'y', 'x')), ('=', 'x', 'y'))
    root = graph.node('target')
    certificate = _linear_equality(root, graph, SolveBudget(None))
    assert certificate is not None
    changed = replace(root, conclusion=graph.nodes[0].conclusion, linear_equality=certificate)
    graph = replace(graph, nodes=graph.nodes[:-1] + (changed,))
    data = UnsatReport('linear_equality', 'unsat', 'captured', graph).to_canonical()
    with pytest.raises(ValueError, match='must prove an arithmetic conclusion alternative'):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('direction', ['less', 'greater'])
@pytest.mark.parametrize('mutation', ['weight', 'constant', 'strict', 'opposite_direction'])
def test_loader_replays_both_directions_of_linear_equality(direction, mutation):
    from dataclasses import replace
    from .test_polynomial import _graph
    from pyfcstm.solver.budget import SolveBudget
    from pyfcstm.solver.proof.rules import _linear_equality

    graph = _graph((('<=', 'x', 'y'), ('<=', 'y', 'x')), ('=', 'x', 'y'))
    root = graph.node('target')
    certificate = _linear_equality(root, graph, SolveBudget(None))
    assert certificate is not None
    graph = replace(graph, nodes=graph.nodes[:-1] + (replace(root, linear_equality=certificate),))
    original = UnsatReport('linear_equality', 'unsat', 'captured', graph, proof_scope='full')
    assert UnsatReport.from_canonical(original.to_canonical()).to_canonical() == original.to_canonical()
    data = json.loads(json.dumps(original.to_canonical()))
    evidence = data['proof']['nodes'][-1]['linear_equality']
    combination = evidence[direction]
    if mutation == 'weight':
        combination['weights'][0] = '123456'
    elif mutation == 'constant':
        combination['constant'] = '123456'
    elif mutation == 'strict':
        combination['strict'] = not combination['strict']
    else:
        evidence[direction] = evidence['greater' if direction == 'less' else 'less']
    with pytest.raises(ValueError, match='invalid linear equality derivation'):
        UnsatReport.from_canonical(data)


def test_generated_linear_equality_replay_rejects_a_corrupted_direction(monkeypatch):
    from dataclasses import replace
    from .test_polynomial import _graph
    from pyfcstm.solver.proof import ProofParameter, analyze_proof, rules

    graph = _graph((('<=', 'x', 'y'), ('<=', 'y', 'x')), ('=', 'x', 'y'))
    root = replace(graph.nodes[-1], parameters=(ProofParameter('symbol', 'arith'),))
    graph = replace(graph, nodes=graph.nodes[:-1] + (root,))
    original = rules._linear_equality

    def corrupt(*args):
        certificate = original(*args)
        assert certificate is not None
        return replace(certificate, greater=certificate.less)

    monkeypatch.setattr(rules, '_linear_equality', corrupt)
    with pytest.warns(RuntimeWarning) as recorded:
        result = analyze_proof(graph)
    assert any('invalid_linear_equality_certificate' in str(item.message) for item in recorded)
    assert result.graph.node(root.node_id).linear_equality is None
    assert result.graph.node(root.node_id).local_check == 'unsupported'
    assert any(gap.reason == 'invalid_linear_equality_certificate' for gap in result.gaps)


@pytest.mark.parametrize('mutation', ['no_conclusion', 'nonlocal', 'not_equality', 'boolean', 'empty_sum'])
def test_linear_equality_replay_rejects_missing_or_wrongly_typed_obligations(mutation):
    from dataclasses import replace
    from .test_polynomial import _graph
    from pyfcstm.solver.budget import SolveBudget
    from pyfcstm.solver.proof.rules import _linear_equality, check_linear_equality_certificate

    graph = _graph((('<=', 'x', 'y'), ('<=', 'y', 'x')), ('=', 'x', 'y'))
    node = graph.node(graph.root_id)
    certificate = _linear_equality(node, graph, SolveBudget(None))
    assert check_linear_equality_certificate(node, graph, certificate)
    if mutation == 'no_conclusion':
        node = replace(node, conclusion=None)
    elif mutation == 'nonlocal':
        node = replace(node, conclusion=graph.nodes[0].conclusion)
    elif mutation == 'not_equality':
        graph = replace(graph, terms=tuple(replace(term, operator='<=') if term.term_id == node.conclusion
                                          else term for term in graph.terms))
    elif mutation == 'boolean':
        children = graph.term(node.conclusion).arguments
        graph = replace(graph, terms=tuple(replace(term, sort='Bool') if term.term_id in children else term
                                          for term in graph.terms))
    else:
        certificate = replace(certificate, less=replace(certificate.less, bounds=(), weights=()))
    assert not check_linear_equality_certificate(node, graph, certificate)


@pytest.mark.parametrize('mutation', ['no_conclusion', 'unavailable_constraint'])
def test_counting_replay_rejects_missing_local_obligations(mutation):
    from dataclasses import replace
    from pyfcstm.solver.proof.rules import check_cardinality_certificate

    p, q, s = z3.Bools('p q s')
    report = explain_unsat(UnsatQuery('count', (UnsatConstraint('conditions', (z3.AtMost(p, q, s, 1), p, q)),)))
    node = next(node for node in report.proof.nodes if node.cardinality is not None)
    certificate = node.cardinality
    if mutation == 'no_conclusion':
        node = replace(node, conclusion=None)
    else:
        certificate = replace(certificate, constraint_id=report.proof.node(report.proof.root_id).conclusion)
    assert not check_cardinality_certificate(node, report.proof, certificate)


def test_loader_rejects_a_cycle_in_expansion_details():
    data = _report().to_canonical()
    block = data['reading']['blocks'][0]
    block['detail_block_ids'] = (block['block_id'],)
    with pytest.raises(ValueError, match='cyclic reading references'):
        UnsatReport.from_canonical(data)


def test_fold_expansion_must_preserve_its_recorded_evidence():
    from .test_extensions import _interval_query, _interval_fold
    from pyfcstm.solver.proof import ProofExtensions, ReadingFolder

    report = explain_unsat(_interval_query(), extensions=ProofExtensions(reading_folders=(
        ReadingFolder(lambda reading: (_interval_fold(reading),)),)))
    data = report.to_canonical()
    root = next(block for block in data['reading']['blocks'] if block['block_id'] == data['reading']['root_id'])
    assert len(root['detail_block_ids']) > 1
    root['detail_block_ids'] = root['detail_block_ids'][-1:]
    with pytest.raises(ValueError, match='reading expansion disagrees with evidence'):
        UnsatReport.from_canonical(data)


def test_closed_refutation_is_validated_without_a_reading():
    data = _report().to_canonical()
    data['reading'] = None
    data['reading_status'] = 'not_requested'
    data['proof']['root_id'] = data['proof']['nodes'][0]['node_id']
    with pytest.raises(ValueError, match='closed refutation must conclude False'):
        UnsatReport.from_canonical(data)


@pytest.mark.parametrize('mutation', ['bound', 'weight', 'sum', 'strict', 'empty', 'nonlocal'])
def test_loader_rechecks_arithmetic_evidence_instead_of_trusting_stored_totals(mutation):
    x = z3.Real('x')
    report = explain_unsat(UnsatQuery('rounding', (
        UnsatConstraint('domain', (x >= 0,)),
        UnsatConstraint('goal', (z3.ToReal(z3.ToInt(x)) < 0,)),
    )))
    data = json.loads(json.dumps(report.to_canonical()))
    certificate = next(node['certificate'] for node in data['proof']['nodes']
                       if node['certificate'] is not None)
    if mutation == 'bound':
        certificate['bounds'][0]['constant'] = '1234567'
    elif mutation == 'weight':
        certificate['weights'] = ['-1' for _ in certificate['weights']]
    elif mutation == 'sum':
        certificate['constant'] = '1234567'
    elif mutation == 'empty':
        certificate['bounds'] = []
        certificate['weights'] = []
    elif mutation == 'nonlocal':
        certificate['bounds'][0]['term_id'] = data['proof']['inputs'][1]['term_id']
        certificate['bounds'][0]['negated'] = False
    else:
        certificate['strict'] = not certificate['strict']
    with pytest.raises(ValueError, match='arithmetic derivation'):
        UnsatReport.from_canonical(data)
