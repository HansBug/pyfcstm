"""Portable proof snapshots validate identities before offline navigation."""

import json
import subprocess
import sys

import pytest
import z3

from pyfcstm.solver import UnsatConstraint, UnsatQuery, UnsatReport, explain_unsat


pytestmark = pytest.mark.unittest


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
    (('full_proof',), None),
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
