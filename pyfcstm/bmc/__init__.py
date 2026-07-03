"""Public API for FCSTM bounded model checking data contracts.

The BMC package is an independent root package for the FCSTM bounded model
checking workstream.  It exposes parser-independent query and expression
dataclasses, domain numbering snapshots, and macro-step source/case contracts
while deliberately leaving grammar parsing, semantic binding, solver lowering,
witness replay, and verify-registry integration to separate layers.

Package contracts:

* BMC query objects are parser-independent and data-only in this package.
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
     - :class:`BmcError`, :class:`InvalidBmcQuery`,
       :class:`UnsupportedBmcQuery`, :class:`InvalidBmcEncoding`,
       :class:`InvalidBmcDomain`, :class:`BmcBuildError`
     - Provide stable BMC-specific exception types without importing
       ``pyfcstm.verify``.
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
     - Number model states, events, persistent variables, frames, steps,
       sentinel states, and event-input slots before solver lowering.
   * - Macro-step sources
     - :class:`MacroStepSource`, :func:`source_from_initial_spec`,
       :func:`entry_source`, :func:`stable_leaf_source`,
       :func:`terminated_source`, :func:`diagnostic_source`
     - Describe initial and recurrence source profiles without reading
       initial ``where`` predicates or building solver relations.
   * - Macro-step cases
     - :class:`BoolTemplate`, :class:`EventUse`, :class:`VarUpdate`,
       :class:`CycleCase`, :class:`MacroStepFormal`,
       :func:`build_fallback_case`, :func:`build_semantic_delta_case`,
       :func:`verify_source_partition`
     - Freeze case labels, bare conditions, explicit variable writeback,
       absorb/fallback/delta helpers, and build-time partition self-checks.
   * - Query root model
     - :class:`InitialSpec`, :class:`FrameAssumption`,
       :class:`EventAssumption`, :class:`EventCardinalityAssumption`,
       :class:`BmcProperty`, :class:`BmcQuery`
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
from pyfcstm.bmc.domain import (
    STATE_DIAGNOSTIC_ID,
    STATE_TERMINATE_ID,
    BmcDomain,
    EventDomainEntry,
    EventInputRef,
    FrameRef,
    StateDomainEntry,
    StepRef,
    VarDomainEntry,
    build_bmc_domain,
)
from pyfcstm.bmc.errors import (
    BmcBuildError,
    BmcError,
    InvalidBmcDomain,
    InvalidBmcEncoding,
    InvalidBmcQuery,
    UnsupportedBmcQuery,
)
from pyfcstm.bmc.macro import (
    BoolTemplate,
    CycleCase,
    EventUse,
    MacroStepFormal,
    PartitionCheckResult,
    VarUpdate,
    build_fallback_case,
    build_semantic_delta_case,
    build_var_updates,
    carry_var_updates,
    case_antecedent_condition,
    diagnostic_absorb_case,
    terminated_absorb_case,
    var_update_for,
    verify_boolean_partition,
    verify_source_partition,
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
from pyfcstm.bmc.source import (
    DIAGNOSTIC_CASE_PATH,
    TERMINATE_CASE_PATH,
    MacroStepSource,
    diagnostic_source,
    entry_source,
    source_from_initial_spec,
    stable_leaf_source,
    terminated_source,
)

__all__ = [
    "BmcError",
    "InvalidBmcQuery",
    "UnsupportedBmcQuery",
    "InvalidBmcEncoding",
    "InvalidBmcDomain",
    "BmcBuildError",
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
