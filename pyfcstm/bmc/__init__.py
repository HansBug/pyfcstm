"""Public API for FCSTM bounded model checking query models.

The BMC package is an independent root package for the FCSTM bounded model
checking workstream.  It exposes parser-independent query and expression
dataclasses while deliberately leaving grammar parsing, semantic binding,
solver lowering, witness replay, and verify-registry integration to separate
layers.

Package contracts:

* BMC query objects are parser-independent and data-only in this package.
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
from pyfcstm.bmc.query import (
    BmcAssumption,
    BmcProperty,
    BmcQuery,
    EventAssumption,
    EventCardinalityAssumption,
    FrameAssumption,
    InitialSpec,
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
]
