"""Public solver helpers for Z3-backed FCSTM analysis.

The solver package is the pure symbolic layer shared by verification
algorithms and future reachability/search work.  It translates model
expressions and operation blocks into Z3 formulas, but it does not import
``pyfcstm.verify``, diagnostics, registries, lifecycle rules, or inspect
policy.  FCSTM runtime semantics that need states, transitions, declaration
order, or lifecycle phases live in :mod:`pyfcstm.verify`.

Module map:

.. list-table::
   :header-rows: 1

   * - Module
     - Public entry
     - Purpose
   * - :mod:`pyfcstm.solver.expr`
     - :func:`expr_to_z3`, :func:`create_z3_vars_from_models`
     - Translate expressions and declared variables into Z3 values.
   * - :mod:`pyfcstm.solver.domain`
     - :func:`translate_expr_domain`,
       :func:`merge_definedness_constraints`
     - Return expression values together with runtime-definedness
       constraints such as non-zero divisors.
   * - :mod:`pyfcstm.solver.operation`
     - :func:`parse_operations`, :func:`execute_operations`,
       ``execute_operations_domain``
     - Parse and symbolically execute operation blocks, including
       path-sensitive execution through ``if`` / ``elif`` / ``else``.
   * - :mod:`pyfcstm.solver.logical`
     - ``is_sat`` and related query helpers
     - Wrap small satisfiability, validity, and overlap checks.
   * - :mod:`pyfcstm.solver.safety`
     - Optional safety classifiers
     - Provide advisory classification for downstream policy layers; raw
       verification algorithms do not use it as a default gate.
   * - :mod:`pyfcstm.solver.solve`
     - :func:`solve`, :class:`SolveResult`
     - Enumerate satisfying assignments for caller-supplied constraints.

Example::

    >>> import z3
    >>> from pyfcstm.model.expr import BinaryOp, Integer, Variable
    >>> from pyfcstm.solver import expr_to_z3, solve
    >>> # The package-level imports keep the historical simple solver API.
    >>> z3_vars = {"x": z3.Int("x")}
    >>> expr = BinaryOp(x=Variable("x"), op="+", y=Integer(5))
    >>> z3_expr = expr_to_z3(expr, z3_vars)
    >>> result = solve([z3_expr == 10], max_solutions=1)
    >>> result.status
    'sat'
    >>> result.solutions[0]["x"]
    5

    >>> from pyfcstm.solver.domain import translate_expr_domain
    >>> # Domain-aware translation also reports runtime preconditions.
    >>> div_expr = BinaryOp(x=Variable("x"), op="/", y=Integer(2))
    >>> domain = translate_expr_domain(div_expr, z3_vars)
    >>> domain.failure is None
    True
    >>> len(domain.definedness_constraints)
    1
"""

from importlib import import_module
from types import ModuleType
import sys


_EXPORTS = {
    'expr_to_z3': 'expr', 'create_z3_vars_from_models': 'expr',
    'parse_operations': 'operation', 'execute_operations': 'operation',
    'solve': 'solve', 'SolveResult': 'solve',
    'SymbolName': 'symbols', 'SymbolNames': 'symbols',
    'UnsatConstraint': 'unsat', 'UnsatQuery': 'unsat',
    'UnsatCoreResult': 'unsat', 'explain_unsat_core': 'unsat',
    'explain_unsat': 'proof', 'UnsatReport': 'proof',
    'ProofExtensions': 'proof', 'SourceAdapter': 'proof',
    'SourceDescription': 'proof', 'SourceBinding': 'proof',
    'ProofRuleHandler': 'proof_rules', 'RuleAnalysis': 'proof_rules',
    'ReadingFolder': 'proof_text', 'FoldProposal': 'proof_text',
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    """Load native dependencies only when a solver operation is requested."""
    if name not in _EXPORTS:
        raise AttributeError("module %r has no attribute %r" % (__name__, name))
    module = import_module('.' + _EXPORTS[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__():
    """Include lazily exported helpers in ordinary module introspection."""
    return sorted(set(globals()) | set(__all__))


class _SolverModule(ModuleType):
    """Preserve the solve function when Python attaches its namesake module."""

    def __getattribute__(self, name):
        value = super().__getattribute__(name)
        # A direct import of pyfcstm.solver.solve attaches the submodule after
        # loading it. The historical package API exposes the function instead.
        if name == 'solve' and isinstance(value, ModuleType):
            value = value.solve
            self.solve = value
        return value


sys.modules[__name__].__class__ = _SolverModule
