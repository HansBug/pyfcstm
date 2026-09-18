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
