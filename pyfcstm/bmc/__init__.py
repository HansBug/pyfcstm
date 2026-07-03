"""Public API for FCSTM bounded model checking data contracts.

The BMC package is an independent root package for the FCSTM bounded model
checking workstream. It exposes parser-independent query and expression
dataclasses, parser entry points, domain numbering snapshots, and macro-step
source/case contracts while deliberately leaving semantic binding, solver
lowering, witness replay, and verify-registry integration to separate layers.

Package contracts:

* BMC query objects are parser-independent and data-only in this package.
* Parser entry points build parser-independent query objects and remain
  separate from model-aware binding or solver lowering.
* Domain-numbering and macro-step exports are resolved lazily so parser-only
  imports do not load ``pyfcstm.model``.
* Macro-step contracts are solver-independent and do not import ``z3`` from the
  root package.
* The root package must not depend on ``pyfcstm.verify`` or its registry.
* :func:`str` on exported query and expression dataclasses is reserved for the
  canonical ``.fbmcq`` query DSL spelling.
* :func:`repr` remains the dataclass debugging representation; callers that need
  stable machine comparison should use ``to_canonical()``.

Public module structure:

.. list-table::
   :header-rows: 1

   * - Area
     - Public entry
     - Purpose
   * - Error hierarchy
     - :class:`BmcError`, :class:`BmcQueryParseError`,
       :class:`InvalidBmcQuery`,
       :class:`UnsupportedBmcQuery`, :class:`InvalidBmcEncoding`,
       :class:`InvalidBmcDomain`, :class:`BmcBuildError`
     - Provide stable BMC-specific exception types without importing
       ``pyfcstm.verify``.
   * - Query parser
     - :func:`parse_bmc_query`, :func:`parse_bmc_num_expression`,
       :func:`parse_bmc_cond_expression`,
       :func:`parse_with_bmc_grammar_entry`,
       :func:`build_bmc_ast_from_parse_tree`
     - Convert ``.fbmcq`` text or existing ANTLR parse trees into
       parser-independent AST/query nodes.
   * - Typed expression bases
     - :class:`BmcExpr`, :class:`BmcNumExpr`, :class:`BmcCondExpr`
     - Keep FCSTM numeric and condition expression categories explicit.
   * - FCSTM-compatible numeric expressions
     - :class:`IntLiteral`, :class:`FloatLiteral`, :class:`NameRef`,
       :class:`MathConst`, :class:`NumUnaryOp`, :class:`NumBinaryOp`,
       :class:`NumConditionalOp`, :class:`UFuncCall`
     - Represent the current FCSTM ``num_expression`` shape.
   * - FCSTM-compatible condition expressions
     - :class:`BoolLiteral`, :class:`CondUnaryOp`,
       :class:`NumericComparison`, :class:`CondBinaryOp`,
       :class:`CondConditionalOp`
     - Represent the current FCSTM ``cond_expression`` shape.
   * - BMC-only query atoms
     - :class:`FrameVar`, :class:`Cycle`, :class:`Active`,
       :class:`Terminated`, :class:`Event`, :class:`Case`, :class:`Called`
     - Represent frame variables, cycle counters, active state, selected event,
       selected macro-step case, termination, and future abstract-call atoms.
   * - BMC domain model
     - :class:`StateDomainEntry`, :class:`EventDomainEntry`,
       :class:`VarDomainEntry`, :class:`FrameRef`, :class:`StepRef`,
       :class:`EventInputRef`, :class:`BmcDomain`,
       :func:`build_bmc_domain`
     - Lazily number model states, events, persistent variables, frames, steps,
       sentinel states, and event-input slots before solver lowering.
   * - Macro-step sources
     - :class:`MacroStepSource`, :func:`source_from_initial_spec`,
       :func:`entry_source`, :func:`stable_leaf_source`,
       :func:`terminated_source`, :func:`diagnostic_source`
     - Describe initial and recurrence source profiles without reading
       initial ``where`` predicates or building solver relations.
   * - Macro-step case data
     - :class:`BoolTemplate`, :class:`EventUse`, :class:`VarUpdate`,
       :class:`CycleCase`, :class:`MacroStepFormal`,
       :class:`PartitionCheckResult`
     - Freeze case labels, bare conditions, explicit variable writeback,
       source-local buckets, and build-time partition summaries.
   * - Macro-step case helpers
     - :func:`carry_var_updates`, :func:`var_update_for`,
       :func:`build_var_updates`, :func:`case_antecedent_condition`,
       :func:`terminated_absorb_case`, :func:`diagnostic_absorb_case`,
       :func:`build_fallback_case`, :func:`build_semantic_delta_case`,
       :func:`verify_boolean_partition`, :func:`verify_source_partition`
     - Construct carry, absorb, fallback, and semantic-delta cases while keeping
       partition self-checks outside formal trace formulas.
   * - Query root model
     - :class:`InitialSpec`, :class:`BmcAssumption`,
       :class:`FrameAssumption`, :class:`EventAssumption`,
       :class:`EventCardinalityAssumption`, :class:`BmcProperty`,
       :class:`BmcQuery`
     - Capture top-level ``*.fbmcq`` query structure before parser, binder, or
       solver-specific phases.

Example::

    >>> from pyfcstm.bmc import Active, BmcProperty, BmcQuery
    >>> query = BmcQuery(property=BmcProperty("reach", 2, predicate=Active("Root.Done")))
    >>> query.to_canonical()["property"]["kind"]
    'reach'
"""

from pyfcstm.bmc.ast import (
    Active,
    BmcCondExpr,
    BmcExpr,
    BmcNumExpr,
    BoolLiteral,
    Called,
    Case,
    CondBinaryOp,
    CondConditionalOp,
    CondUnaryOp,
    Cycle,
    Event,
    FloatLiteral,
    FrameVar,
    IntLiteral,
    MathConst,
    NameRef,
    NumBinaryOp,
    NumConditionalOp,
    NumUnaryOp,
    NumericComparison,
    Terminated,
    UFuncCall,
)
from pyfcstm.bmc.errors import (
    BmcBuildError,
    BmcError,
    BmcQueryParseError,
    InvalidBmcDomain,
    InvalidBmcEncoding,
    InvalidBmcQuery,
    UnsupportedBmcQuery,
)
from pyfcstm.bmc.parse import (
    build_bmc_ast_from_parse_tree,
    parse_bmc_cond_expression,
    parse_bmc_num_expression,
    parse_bmc_query,
    parse_with_bmc_grammar_entry,
)
from pyfcstm.bmc.query import (
    BmcAssumption,
    BmcProperty,
    BmcQuery,
    EventAssumption,
    EventCardinalityAssumption,
    FrameAssumption,
    InitialSpec,
)

_DOMAIN_EXPORTS = {
    "STATE_TERMINATE_ID",
    "STATE_DIAGNOSTIC_ID",
    "StateDomainEntry",
    "EventDomainEntry",
    "VarDomainEntry",
    "FrameRef",
    "StepRef",
    "EventInputRef",
    "BmcDomain",
    "build_bmc_domain",
}

_SOURCE_EXPORTS = {
    "TERMINATE_CASE_PATH",
    "DIAGNOSTIC_CASE_PATH",
    "MacroStepSource",
    "entry_source",
    "stable_leaf_source",
    "terminated_source",
    "diagnostic_source",
    "source_from_initial_spec",
}

_MACRO_EXPORTS = {
    "BoolTemplate",
    "EventUse",
    "VarUpdate",
    "CycleCase",
    "PartitionCheckResult",
    "MacroStepFormal",
    "carry_var_updates",
    "var_update_for",
    "build_var_updates",
    "case_antecedent_condition",
    "terminated_absorb_case",
    "diagnostic_absorb_case",
    "build_fallback_case",
    "build_semantic_delta_case",
    "verify_boolean_partition",
    "verify_source_partition",
}

_LAZY_EXPORT_MODULES = {
    "pyfcstm.bmc.domain": _DOMAIN_EXPORTS,
    "pyfcstm.bmc.source": _SOURCE_EXPORTS,
    "pyfcstm.bmc.macro": _MACRO_EXPORTS,
}


def __getattr__(name: str):
    """Lazily resolve model-aware and macro-step exports.

    Domain numbering and macro-step helpers import :mod:`pyfcstm.model`, while
    the query parser must remain importable without loading model, verify, or
    solver layers. Keeping these top-level exports lazy preserves the public
    convenience API without coupling parser-only callers to later BMC layers.

    :param name: Attribute name requested from :mod:`pyfcstm.bmc`.
    :type name: str
    :return: The requested domain export.
    :rtype: object
    :raises AttributeError: If ``name`` is not a public lazy domain export.

    Example::

        >>> import pyfcstm.bmc as bmc
        >>> bmc.STATE_TERMINATE_ID
        -1
    """
    import importlib

    for module_name, exports in _LAZY_EXPORT_MODULES.items():
        if name in exports:
            value = getattr(importlib.import_module(module_name), name)
            globals()[name] = value
            return value
    raise AttributeError("module 'pyfcstm.bmc' has no attribute %r" % name)


def __dir__():
    """Return the public module attributes including lazy domain exports.

    :return: Sorted attribute names for interactive discovery.
    :rtype: list

    Example::

        >>> import pyfcstm.bmc as bmc
        >>> 'BmcDomain' in dir(bmc)
        True
    """
    return sorted(set(globals()) | _DOMAIN_EXPORTS | _SOURCE_EXPORTS | _MACRO_EXPORTS)


__all__ = [
    "BmcError",
    "BmcQueryParseError",
    "InvalidBmcQuery",
    "UnsupportedBmcQuery",
    "InvalidBmcEncoding",
    "InvalidBmcDomain",
    "BmcBuildError",
    "parse_bmc_query",
    "parse_bmc_num_expression",
    "parse_bmc_cond_expression",
    "parse_with_bmc_grammar_entry",
    "build_bmc_ast_from_parse_tree",
    "BmcExpr",
    "BmcNumExpr",
    "BmcCondExpr",
    "IntLiteral",
    "FloatLiteral",
    "BoolLiteral",
    "NameRef",
    "MathConst",
    "NumUnaryOp",
    "NumBinaryOp",
    "NumConditionalOp",
    "UFuncCall",
    "CondUnaryOp",
    "NumericComparison",
    "CondBinaryOp",
    "CondConditionalOp",
    "FrameVar",
    "Cycle",
    "Active",
    "Terminated",
    "Event",
    "Case",
    "Called",
    "InitialSpec",
    "BmcAssumption",
    "FrameAssumption",
    "EventAssumption",
    "EventCardinalityAssumption",
    "BmcProperty",
    "BmcQuery",
    "STATE_TERMINATE_ID",
    "STATE_DIAGNOSTIC_ID",
    "StateDomainEntry",
    "EventDomainEntry",
    "VarDomainEntry",
    "FrameRef",
    "StepRef",
    "EventInputRef",
    "BmcDomain",
    "build_bmc_domain",
    "TERMINATE_CASE_PATH",
    "DIAGNOSTIC_CASE_PATH",
    "MacroStepSource",
    "entry_source",
    "stable_leaf_source",
    "terminated_source",
    "diagnostic_source",
    "source_from_initial_spec",
    "BoolTemplate",
    "EventUse",
    "VarUpdate",
    "CycleCase",
    "PartitionCheckResult",
    "MacroStepFormal",
    "carry_var_updates",
    "var_update_for",
    "build_var_updates",
    "case_antecedent_condition",
    "terminated_absorb_case",
    "diagnostic_absorb_case",
    "build_fallback_case",
    "build_semantic_delta_case",
    "verify_boolean_partition",
    "verify_source_partition",
]
