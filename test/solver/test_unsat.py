"""UNSAT evidence is reusable without a BMC query or property adapter."""

import pytest
import z3
import subprocess
import sys

pytestmark = pytest.mark.unittest


def test_shared_public_api_runs_without_importing_bmc():
    completed = subprocess.run(
        [sys.executable, '-c', '''
import sys
import z3
from pyfcstm.solver import UnsatConstraint, UnsatQuery, SymbolNames, explain_unsat_core
x, y = z3.Ints('x y')
result = explain_unsat_core(UnsatQuery('ordering', (
    UnsatConstraint('before', (x < y,)),
    UnsatConstraint('after', (x >= y,)),
)))
assert result.core_check == 'verified'
assert not any(name == 'pyfcstm.bmc' or name.startswith('pyfcstm.bmc.') for name in sys.modules)
print(result.solver_status)
'''],
        check=True, capture_output=True, text=True,
    )
    assert completed.stdout.strip() == 'unsat'


def test_formula_core_has_no_property_specific_contract():
    from pyfcstm.solver.unsat import UnsatConstraint, UnsatQuery, explain_unsat_core

    x, y = z3.Ints('x y')
    query = UnsatQuery('ordering', (
        UnsatConstraint('guard', (x < y,)),
        UnsatConstraint('post', (x >= y,)),
    ))
    result = explain_unsat_core(query)
    assert result.core_ids == ('guard', 'post')
    assert result.core_check == 'verified'
    assert not hasattr(result, 'property_satisfied')


def test_generic_budget_rejects_invalid_timeout_without_bmc_errors():
    from pyfcstm.solver.unsat import UnsatQuery, explain_unsat_core

    with pytest.raises(ValueError, match='positive integer'):
        explain_unsat_core(UnsatQuery('empty', ()), timeout_ms=0)


@pytest.mark.parametrize('minimize', [False, True])
def test_selected_duplicate_occurrences_are_not_replaced_by_another_source(minimize):
    from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat_core

    x, y = z3.Ints('x y')
    first = UnsatConstraint('first_guard', (x < y,), {'line': 10})
    second = UnsatConstraint('selected_guard', (x < y,), {'line': 20})
    post = UnsatConstraint('post', (x >= y,))
    query = UnsatQuery('chosen_occurrences', (first, second, post))
    result = explain_unsat_core(
        query, selected_ids=('selected_guard', 'post'), minimize=minimize,
    )
    assert result.query is query
    assert result.core_ids == ('post', 'selected_guard')
    assert result.core_check == 'verified'
    assert result.query.constraints[1] is second
    assert result.subset_minimality == ('proven' if minimize else 'not_proven')
    assert (result.derivation_status, result.proof_status) == (
        'not_attempted', 'not_attempted',
    )


def test_source_handle_can_retain_multiple_occurrences_without_becoming_a_premise():
    from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat_core

    x, y, z = z3.Ints('x y z')
    shared_origin = {'file': 'controller.fcstm', 'line': 10}
    occurrences = (shared_origin, {'file': 'controller.fcstm', 'line': 20})
    chain = UnsatConstraint('chain', (x < y, y < z), occurrences)
    copy = UnsatConstraint('copy', (x < y,), shared_origin)
    # A caller may retain an earlier formula or proof result as metadata.
    # Neither this False formula nor the label can become a solver premise.
    post_origin = {'earlier_formula': z3.BoolVal(False), 'proof_status': 'verified'}
    post = UnsatConstraint('post', (z <= x,), post_origin)
    query = UnsatQuery('source_dependencies', (chain, copy, post))
    selected = explain_unsat_core(
        query, selected_ids=('post', 'chain'), minimize=False,
    )
    assert selected.core_ids == ('chain', 'post')
    assert selected.query.constraints[0].source is occurrences
    assert selected.query.constraints[0].source[0] is shared_origin
    assert selected.query.constraints[1].source is shared_origin
    assert selected.query.constraints[2].source is post_origin
    insufficient = explain_unsat_core(query, selected_ids=('post',), minimize=False)
    assert insufficient.solver_status == 'unsat'
    assert insufficient.core_check == 'sat'
    assert insufficient.core_ids is None
    assert (insufficient.derivation_status, insufficient.proof_status) == (
        'not_attempted', 'not_attempted',
    )


def test_source_metadata_does_not_change_an_empty_background_sat_query():
    from pyfcstm.solver import UnsatConstraint, UnsatQuery, explain_unsat_core

    x, y = z3.Ints('x y')
    query = UnsatQuery('metadata', (
        UnsatConstraint('ordering', (x < y,), {'formula': x >= y}),
    ))
    result = explain_unsat_core(query)
    assert result.solver_status == 'sat'
    assert result.core_ids is None
    assert result.core_check == 'not_checked'
    assert result.derivation_status == result.proof_status == 'not_attempted'
