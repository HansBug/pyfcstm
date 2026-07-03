"""Public API for FCSTM bounded model checking query models.

The BMC package is an independent root package for the FCSTM bounded model
checking workstream.  It exposes parser-independent query and expression
dataclasses while deliberately leaving grammar parsing, semantic binding,
solver lowering, witness replay, and verify-registry integration to separate
layers.

Package contracts:

* BMC query objects are parser-independent and data-only in this package.
* The root package must not depend on ``pyfcstm.verify`` or its registry.
* Parser entry points build parser-independent query objects and remain
  separate from model-aware binding or solver lowering.
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
       :class:`BmcBuildError`
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
from pyfcstm.bmc.errors import (
    BmcBuildError,
    BmcError,
    BmcQueryParseError,
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

__all__ = [
    "BmcError",
    "BmcQueryParseError",
    "InvalidBmcQuery",
    "UnsupportedBmcQuery",
    "InvalidBmcEncoding",
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
]
