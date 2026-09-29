"""Source metadata binds exact expressions and remains separate from premises."""

import pytest
import z3

from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat
from pyfcstm.solver.proof import ProofExtensions, SourceAdapter, SourceDescription


pytestmark = pytest.mark.unittest


def test_construction_binding_matches_an_actual_subterm_and_prints_its_role(text_aligner):
    from pyfcstm.solver.proof import SourceBinding

    x = z3.Real('encoded')
    location = SourceDescription('capacity', 'Configured capacity', 'limits.cfg', (2, 1, 2, 12))

    class Sources(SourceAdapter):
        def bindings(self):
            return (SourceBinding(x, location, 'construction'),)

    report = explain_unsat(UnsatQuery('capacity', (
        UnsatConstraint('positive', (x > 0,)), UnsatConstraint('zero', (x <= 0,)),
    )), extensions=ProofExtensions(source_adapter=Sources()))
    binding, = report.proof.source_bindings
    assert report.proof.term(binding.term_id).operator == 'encoded'
    assert binding.description == location
    assert binding.relation == 'construction'
    assert report.source_status == 'partial'
    assert report.reading.get_source('capacity') == location
    assert {link.term_id for block in report.reading.blocks for link in block.source_links} == {binding.term_id}
    text_aligner.assert_equal('''\
Query: capacity
Solver result: UNSAT
Reading: complete

P1  Input
  Input origins: positive
  Therefore: (encoded > 0)
  Construction source: Configured capacity [limits.cfg]

P2  Input
  Input origins: zero
  Therefore: (encoded <= 0)
  Construction source: Configured capacity [limits.cfg]

P3  Resolve the clauses
  From: P1, P2
  Therefore: false

Conclusion: the submitted conjunction is inconsistent.
''', report.reading.to_text(detail='detailed'))


def test_bindings_do_not_add_conditions_or_match_by_symbol_spelling():
    from pyfcstm.solver.proof import SourceBinding

    x, unused = z3.Ints('x unused')

    class Sources(SourceAdapter):
        def bindings(self):
            return (SourceBinding(unused, SourceDescription('unused', 'Not in the input')),)

    report = explain_unsat(UnsatQuery('false', (
        UnsatConstraint('contradiction', (z3.And(x > 0, x <= 0),)),
    )), extensions=ProofExtensions(source_adapter=Sources()))
    assert report.proof.source_bindings == ()
    assert len(report.proof.inputs) == 1
    assert report.source_status == 'absent'


@pytest.mark.parametrize('expression', [None, 1, 'x'])
def test_source_binding_requires_an_expression(expression):
    from pyfcstm.solver.proof import SourceBinding

    class Sources(SourceAdapter):
        def bindings(self):
            return (SourceBinding(expression, SourceDescription('bad', 'Bad binding')),)

    with pytest.raises(TypeError, match='expression'):
        explain_unsat(UnsatQuery('false', (UnsatConstraint('false', (z3.BoolVal(False),)),)),
                      extensions=ProofExtensions(source_adapter=Sources()))


def test_source_binding_from_another_context_is_rejected():
    from pyfcstm.solver.proof import SourceBinding

    other = z3.Context()

    class Sources(SourceAdapter):
        def bindings(self):
            return (SourceBinding(z3.Int('x', ctx=other), SourceDescription('bad', 'Wrong context')),)

    with pytest.raises(ValueError, match='context'):
        explain_unsat(UnsatQuery('false', (UnsatConstraint('false', (z3.BoolVal(False),)),)),
                      extensions=ProofExtensions(source_adapter=Sources()))


def test_metadata_cannot_create_a_logical_premise():
    from pyfcstm.solver.proof import SourceBinding

    with pytest.raises(ValueError, match='construction or context'):
        SourceBinding(z3.Int('x'), SourceDescription('fake', 'Fake premise'), 'logical')


def test_conflicting_source_descriptions_do_not_silently_overwrite():
    x = z3.Int('x')
    with pytest.raises(ValueError, match='conflicting source'):
        explain_unsat(UnsatQuery('conflict', (
            UnsatConstraint('lower', (x > 0,), SourceDescription('same', 'First')),
            UnsatConstraint('upper', (x <= 0,), SourceDescription('same', 'Second')),
        )))


@pytest.mark.parametrize('binding', [False, True])
def test_adapter_descriptions_must_be_portable_values(binding):
    from pyfcstm.solver.proof import SourceBinding

    x = z3.Int('x')

    class BrokenSources(SourceAdapter):
        def describe(self, handle):
            return {'source_id': 'not-a-description'}

        def bindings(self):
            return (SourceBinding(x, 'handle'),) if binding else ()

    query = UnsatQuery('bad-description', (
        UnsatConstraint('lower', (x > 0,), None if binding else 'handle'),
        UnsatConstraint('upper', (x <= 0,)),
    ))
    with pytest.raises(TypeError, match='SourceDescription'):
        explain_unsat(query, extensions=ProofExtensions(source_adapter=BrokenSources()))


def test_adapter_bindings_require_source_binding_objects():
    class BrokenSources(SourceAdapter):
        def bindings(self):
            return ('not-a-binding',)

    with pytest.raises(TypeError, match='SourceBinding'):
        explain_unsat(UnsatQuery('empty', ()), extensions=ProofExtensions(source_adapter=BrokenSources()))


def test_default_adapter_rejects_unexplained_application_handles():
    with pytest.raises(TypeError, match='SourceDescription or a SourceAdapter'):
        explain_unsat(UnsatQuery('false', (UnsatConstraint('false', (z3.BoolVal(False),), object()),)))


def test_source_spans_are_detached_from_mutable_caller_input():
    span = [1, 1, 1, 8]
    source = SourceDescription('source', 'Impossible', 'rules.cfg', span)
    report = explain_unsat(UnsatQuery('false', (UnsatConstraint('false', (z3.BoolVal(False),), source),)))
    span[0] = 99
    assert report.reading.get_source('source').span == (1, 1, 1, 8)


@pytest.mark.parametrize('arguments', [
    {'source_id': ''}, {'title': ''}, {'title': 1}, {'document_id': []}, {'excerpt': {}},
    {'span': (1, 2)}, {'span': (True, 1, 1, 3)}, {'span': (0, 1, 1, 3)}, {'span': (2, 1, 1, 3)},
])
def test_invalid_source_descriptions_fail_at_the_public_boundary(arguments):
    values = {'source_id': 'source', 'title': 'Title'}
    values.update(arguments)
    with pytest.raises(ValueError):
        SourceDescription(**values)
