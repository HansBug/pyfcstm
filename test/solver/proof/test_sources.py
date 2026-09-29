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


def test_display_collisions_across_groups_warn_and_keep_symbols_distinct():
    from pyfcstm.solver import SymbolNames, UnsatReport

    x, middle, other = z3.Ints('encoded middle display')
    names = SymbolNames()
    names.register(x, 'display')
    query = UnsatQuery('collision', tuple(UnsatConstraint(str(index), (expression,))
                       for index, expression in enumerate((x > 0, x < middle, middle < other, other <= 0))))
    with pytest.warns(UserWarning, match='Proof symbol display collision'):
        report = explain_unsat(query, names=names)
    symbols = [term for term in report.proof.terms
               if term.kind == 'constant' and term.operator in ('encoded', 'display')]
    assert len(symbols) == 2
    assert len({term.value for term in symbols}) == 2
    loaded = UnsatReport.from_canonical(report.to_canonical())
    for term in symbols:
        assert loaded.reading.get_term_text(term.term_id) == term.value
        assert term.value.startswith('display [')


def test_deep_query_does_not_render_expressions_to_validate_names():
    from pyfcstm.solver import SymbolNames

    expression = z3.Int('deep')
    for _ in range(1200):
        expression = expression + 1
    query = UnsatQuery('deep', (
        UnsatConstraint('long', (expression > 0,)),
        UnsatConstraint('false', (z3.BoolVal(False),)),
    ))
    report = explain_unsat(query, names=SymbolNames())
    assert report.solver_status == 'unsat'
    assert report.reading_status == 'complete'


def test_same_spelling_different_sorts_are_disambiguated_without_a_registry():
    integer, real = z3.Int('x'), z3.Real('x')
    query = UnsatQuery('sorts', (
        UnsatConstraint('input', (integer > 0, real < 0, z3.ToReal(integer) == real)),
    ))
    with pytest.warns(UserWarning, match='Proof symbol display collision'):
        report = explain_unsat(query)
    symbols = [term for term in report.proof.terms if term.kind == 'constant']
    assert len({term.value for term in symbols}) == 2


def test_disambiguation_does_not_reuse_an_authored_suffix():
    from pyfcstm.solver import SymbolNames

    x, other, reserved = z3.Ints('encoded display display_suffix')
    names = SymbolNames()
    names.register(x, 'display')
    names.register(reserved, 'display [t0]')
    query = UnsatQuery('suffix', (
        UnsatConstraint('input', (x > 0, other < 0, reserved == 0, x == other)),
    ))
    with pytest.warns(UserWarning):
        report = explain_unsat(query, names=names)
    values = {term.operator: term.value for term in report.proof.terms if term.kind == 'constant'}
    assert values['encoded'] == 'display [t0]_'
    assert values['display_suffix'] == 'display [t0]'
    assert len(set(values.values())) == 3


def test_registered_display_conflicting_with_a_binder_warns():
    from pyfcstm.solver import SymbolNames

    x, bound = z3.Ints('encoded bound')
    names = SymbolNames()
    names.register(x, 'bound')
    with pytest.warns(UserWarning, match='Proof symbol display collision'):
        report = explain_unsat(UnsatQuery('binder', (
            UnsatConstraint('input', (x > 0, z3.ForAll(bound, bound >= 0))),
        )), names=names)
    value = next(term.value for term in report.proof.terms if term.operator == 'encoded')
    assert value == 'bound [t0]'
