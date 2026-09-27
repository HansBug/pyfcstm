"""Caller extensions interpret evidence and propose checked reading boundaries."""

import pytest
import z3

from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat
from pyfcstm.solver.proof import ProofExtensions


pytestmark = pytest.mark.unittest


def test_rule_handler_interprets_native_evidence_without_changing_its_claim():
    from pyfcstm.solver.proof_rules import ProofRuleHandler, RuleAnalysis

    seen = []

    def interpret(node, graph):
        seen.append(node.node_id)
        assert graph.term(node.conclusion).sort == 'Bool'
        return RuleAnalysis('logical', 'trusted')

    x = z3.Int('x')
    report = explain_unsat(UnsatQuery('nonlinear', (
        UnsatConstraint('square', (x * x == 2,)),
    )), extensions=ProofExtensions(rule_handlers=(ProofRuleHandler('th-lemma', interpret),)))
    assert seen
    assert report.rule_check == 'partial'
    assert report.reading_status == 'complete'
    assert all(report.proof.node(key).local_check == 'trusted' for key in seen)
    assert all(report.proof.node(key).inference_kind == 'logical' for key in seen)


def test_duplicate_rule_handlers_are_rejected_even_before_a_sat_check():
    from pyfcstm.solver.proof_rules import ProofRuleHandler, RuleAnalysis

    handler = ProofRuleHandler('th-lemma', lambda node, graph: RuleAnalysis('logical', 'trusted'))
    with pytest.raises(ValueError, match='duplicate rule handler'):
        explain_unsat(UnsatQuery('empty', ()),
                      extensions=ProofExtensions(rule_handlers=(handler, handler)))


@pytest.mark.parametrize('rule', ['asserted', 'hypothesis', 'lemma'])
def test_extensions_cannot_override_input_binding_or_hypothesis_discharge(rule):
    from pyfcstm.solver.proof_rules import ProofRuleHandler, RuleAnalysis

    with pytest.raises(ValueError, match='reserved rule'):
        explain_unsat(UnsatQuery('empty', ()), extensions=ProofExtensions(rule_handlers=(
            ProofRuleHandler(rule, lambda node, graph: RuleAnalysis('logical', 'checked')),
        )))


def test_handler_must_return_a_rule_analysis():
    from pyfcstm.solver.proof_rules import ProofRuleHandler

    x = z3.Real('x')
    with pytest.raises(TypeError, match='RuleAnalysis'):
        explain_unsat(UnsatQuery('bounds', (
            UnsatConstraint('lower', (x >= 2,)), UnsatConstraint('upper', (x < 1,)),
        )), extensions=ProofExtensions(rule_handlers=(ProofRuleHandler('th-lemma', lambda n, g: None),)))


@pytest.mark.parametrize('kind,check', [('nonsense', 'trusted'), ('logical', 'nonsense')])
def test_handler_result_rejects_unknown_contract_values(kind, check):
    from pyfcstm.solver.proof_rules import RuleAnalysis

    with pytest.raises(ValueError):
        RuleAnalysis(kind, check)


def _interval_query():
    x = z3.Real('x')
    return UnsatQuery('interval', (
        UnsatConstraint('lower', (x >= 2,)), UnsatConstraint('upper', (x < 1,)),
    ))


def _interval_fold(reading):
    from pyfcstm.solver.proof_text import FoldProposal

    root = reading.get_block(reading.root_id)
    selected = tuple(block.block_id for block in reading.blocks if block.kind != 'input')
    premises = tuple(block.block_id for block in reading.blocks if block.kind == 'input')
    return FoldProposal(root.block_id, selected, premises,
                        root.claims, root.active_hypotheses,
                        'Incompatible lower and upper bounds', '上下界不相容')


def test_a_domain_fold_keeps_expandable_original_evidence(text_aligner):
    from pyfcstm.solver.proof_text import ReadingFolder

    report = explain_unsat(_interval_query(), extensions=ProofExtensions(reading_folders=(
        ReadingFolder(lambda reading: (_interval_fold(reading),)),
    )))
    reading = report.reading
    root = reading.get_block(reading.root_id)
    assert root.kind == 'domain'
    details = reading.expand(root.block_id)
    assert len(details) == 2
    assert details[0].kind == 'arithmetic'
    assert details[1].claims == root.claims
    assert set(root.evidence_node_ids) == {
        key for block in details for key in block.evidence_node_ids}
    assert reading.expand(details[1].block_id) == (details[0],) + tuple(
        reading.get_block(key) for key in root.premise_block_ids)
    text_aligner.assert_equal('''\
Query: interval
Solver result: UNSAT
Reading: complete

P1  Input
  Input origins: lower
  Therefore: (x >= 2)

P2  Input
  Input origins: upper
  Therefore: (x < 1)

P3  Incompatible lower and upper bounds
  From: P1, P2
  Therefore: false
  Expandable proof steps: 2

Conclusion: the submitted conjunction is inconsistent.
''', reading.to_text())
    text_aligner.assert_equal('''\
查询：interval
求解结果：UNSAT
阅读完整度：complete

P1  输入条件
  输入来源：lower
  得到：(x >= 2)

P2  输入条件
  输入来源：upper
  得到：(x < 1)

P3  上下界不相容
  根据：P1, P2
  得到：false
  可展开的证明步骤：2

结论：提交的条件合取不可满足。
''', reading.to_text(language='zh'))


@pytest.mark.parametrize('change,message', [
    ({'premise_block_ids': ()}, 'premises'),
    ({'claims': ()}, 'claims'),
    ({'active_hypotheses': ('made-up',)}, 'hypotheses'),
    ({'block_ids': ()}, 'root'),
    ({'block_ids': ('missing',)}, 'unknown block'),
    ({'title_en': ''}, 'title'),
])
def test_unsound_domain_fold_is_rejected(change, message):
    from dataclasses import replace
    from pyfcstm.solver.proof_text import ReadingFolder

    def propose(reading):
        return (replace(_interval_fold(reading), **change),)

    with pytest.raises(ValueError, match=message):
        explain_unsat(_interval_query(), extensions=ProofExtensions(reading_folders=(ReadingFolder(propose),)))


@pytest.mark.parametrize('rule,callback,error', [('', lambda n, g: None, ValueError),
                                              ('rewrite', None, TypeError)])
def test_rule_handler_requires_a_named_callable(rule, callback, error):
    from pyfcstm.solver.proof_rules import ProofRuleHandler

    with pytest.raises(error):
        ProofRuleHandler(rule, callback)


def test_extension_collections_reject_foreign_objects():
    with pytest.raises(TypeError, match='ProofRuleHandler'):
        ProofExtensions(rule_handlers=(object(),))


def test_reading_folder_requires_a_callable():
    from pyfcstm.solver.proof_text import ReadingFolder

    with pytest.raises(TypeError, match='callable'):
        ReadingFolder(None)


def test_reading_folder_must_return_proposals():
    from pyfcstm.solver.proof_text import ReadingFolder

    with pytest.raises(TypeError, match='FoldProposal'):
        explain_unsat(_interval_query(), extensions=ProofExtensions(reading_folders=(
            ReadingFolder(lambda reading: (None,)),)))


def test_reading_folder_collection_must_contain_folders():
    with pytest.raises(TypeError, match='ReadingFolder'):
        explain_unsat(_interval_query(), extensions=ProofExtensions(reading_folders=(object(),)))


@pytest.mark.parametrize('choice,message', [('duplicate', 'duplicate'), ('disconnected', 'connected')])
def test_domain_fold_requires_a_unique_connected_slice(choice, message):
    from dataclasses import replace
    from pyfcstm.solver.proof_text import FoldProposal, ReadingFolder

    def propose(reading):
        if choice == 'duplicate':
            proposal = _interval_fold(reading)
            return (replace(proposal, block_ids=proposal.block_ids + (proposal.root_id,)),)
        inputs = tuple(block for block in reading.blocks if block.kind == 'input')
        return (FoldProposal(inputs[0].block_id, tuple(block.block_id for block in inputs),
                             (), inputs[0].claims, (), 'Invalid slice', '无效片段'),)

    with pytest.raises(ValueError, match=message):
        explain_unsat(_interval_query(), extensions=ProofExtensions(reading_folders=(ReadingFolder(propose),)))


def test_an_extension_can_report_invalid_evidence_without_an_invented_reading():
    from pyfcstm.solver.proof_rules import ProofRuleHandler, RuleAnalysis

    report = explain_unsat(_interval_query(), extensions=ProofExtensions(rule_handlers=(
        ProofRuleHandler('th-lemma', lambda node, graph: RuleAnalysis('opaque', 'invalid')),
    )))
    assert report.proof_status == 'invalid'
    assert report.rule_check == 'failed'
    assert report.reading_status == 'not_requested'
    assert report.gaps[0].reason == 'invalid_inference'


def _branch_query():
    x, y = z3.Ints('x y')
    return UnsatQuery('branches', (
        UnsatConstraint('update', (y == z3.If(x >= 0, x + 1, 0),)),
        UnsatConstraint('goal', (y < 0,)),
    ))


@pytest.mark.parametrize('choice,message', [
    ('shared', 'premise used outside'),
    ('assumption', 'hypotheses used outside'),
    ('open_root', 'hypotheses at its root'),
])
def test_domain_fold_cannot_hide_external_dependencies_or_assumptions(choice, message):
    from pyfcstm.solver.proof_text import FoldProposal, ReadingFolder

    def propose(reading):
        assumption = next(block for block in reading.blocks if block.kind == 'assumption')
        if choice == 'assumption':
            root, selected = assumption, {assumption.block_id}
        elif choice == 'open_root':
            root = next(block for block in reading.blocks if block.kind == 'arithmetic' and block.active_hypotheses)
            selected = {block.block_id for block in reading.blocks if block.active_hypotheses}
        else:
            root = next(block for block in reading.blocks if block.kind == 'discharge')
            selected, pending = set(), [root.block_id]
            while pending:
                key = pending.pop()
                if key not in selected:
                    selected.add(key)
                    pending.extend(reading.get_block(key).premise_block_ids)
        boundary = tuple(sorted({parent for key in selected for parent in reading.get_block(key).premise_block_ids
                                 if parent not in selected}))
        return (FoldProposal(root.block_id, tuple(sorted(selected)), boundary, root.claims,
                             root.active_hypotheses, 'Invalid fold', '无效合并'),)

    with pytest.raises(ValueError, match=message):
        explain_unsat(_branch_query(), extensions=ProofExtensions(reading_folders=(ReadingFolder(propose),)))


def test_closed_branch_proof_can_be_folded_without_erasing_its_derivation(text_aligner):
    from pyfcstm.solver.proof_text import FoldProposal, ReadingFolder

    def propose(reading):
        root = reading.get_block(reading.root_id)
        return (FoldProposal(root.block_id, tuple(block.block_id for block in reading.blocks), (),
                             root.claims, (), 'Both cases contradict the goal', '两个分支均与目标矛盾'),)

    report = explain_unsat(_branch_query(), extensions=ProofExtensions(reading_folders=(ReadingFolder(propose),)))
    details = report.reading.expand(report.reading.root_id)
    assert any(block.kind == 'assumption' for block in details)
    assert any(block.kind == 'discharge' for block in details)
    assert report.reading.blocks[0].active_hypotheses == ()
    text_aligner.assert_equal('''\
Query: branches
Solver result: UNSAT
Reading: complete

P1  Both cases contradict the goal
  Therefore: false
  Expandable proof steps: 18

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text())
