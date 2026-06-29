"""
Inspect analyzer package map.

This package groups the small, composable analyzers used by
:func:`pyfcstm.diagnostics.inspect.inspect_model`. Each analyzer owns one
well-bounded diagnostic concern and returns structured
:class:`pyfcstm.utils.validate.ModelDiagnostic` objects for the design-health
pipeline.

.. list-table:: Analyzer modules
   :header-rows: 1

   * - Module
     - Responsibility
   * - :mod:`pyfcstm.diagnostics.analyzers.combo`
     - Combo-trigger provenance diagnostics.
   * - :mod:`pyfcstm.diagnostics.analyzers.const_fold`
     - Literal-only constant-folding diagnostics.
   * - :mod:`pyfcstm.diagnostics.analyzers.numeric`
     - C/C++ deployment-profile numeric diagnostics.
   * - :mod:`pyfcstm.diagnostics.analyzers.design_health`
     - Aggregates analyzer outputs into the default inspect warning set.
   * - :mod:`pyfcstm.diagnostics.analyzers.data_flow`
     - Variable read/write and guard-affect data-flow diagnostics.
   * - :mod:`pyfcstm.diagnostics.analyzers.structural`
     - State and transition topology diagnostics.

Example::

    >>> from pyfcstm.diagnostics.analyzers import collect_numeric_warnings
    >>> collect_numeric_warnings(None)
    []
"""

from .combo import collect_combo_warnings
from .const_fold import (
    collect_const_fold_warnings,
    fold_condition_expression,
    fold_numeric_expression,
)
from .design_health import collect_design_health_warnings
from .naming import collect_naming_warnings
from .numeric import collect_numeric_warnings
from .thresholds import collect_threshold_warnings
from .transition_info import collect_transition_infos
from .type_shape import collect_type_warnings
from .use_def import UseDefGraph, build_use_def_graph, collect_expr_variables

__all__ = [
    'collect_combo_warnings',
    'collect_const_fold_warnings',
    'collect_design_health_warnings',
    'fold_condition_expression',
    'fold_numeric_expression',
    'collect_naming_warnings',
    'collect_numeric_warnings',
    'collect_threshold_warnings',
    'collect_transition_infos',
    'collect_type_warnings',
    'UseDefGraph',
    'build_use_def_graph',
    'collect_expr_variables',
]
