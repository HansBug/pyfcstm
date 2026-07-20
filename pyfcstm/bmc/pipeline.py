"""High-level compile-only pipeline for FCSTM BMC queries.

This module provides the convenient public handoff from a state machine and
query text or query model to a solve-ready
:class:`pyfcstm.bmc.properties.BmcPropertyFormula`.  It composes the existing
preparation, core-relation, and property-compilation stages without starting a
solver or decoding a witness.

Use :func:`compile_bmc_query` when the caller owns a model and query.  Use the
lower-level :func:`pyfcstm.bmc.properties.compile_bmc_property` when the caller
already owns a :class:`pyfcstm.bmc.relation.BmcCoreFormula` and needs to compile
only its property objective.

The module contains:

* :func:`compile_bmc_query` - Compile a model and query into a solve-ready
  property formula without solving it.

Example::

    >>> from pyfcstm.bmc.pipeline import compile_bmc_query
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('state Root;')
    >>> formula = compile_bmc_query(model, 'check reach <= 1: active("Root");')
    >>> formula.kind, formula.polarity
    ('reach', 'witness')
"""

from __future__ import annotations

from typing import Optional, Union

from pyfcstm.model import StateMachine

from .engine import BmcOptions, prepare_bmc_query
from .properties import BmcPropertyFormula, compile_bmc_property
from .query import BmcQuery
from .relation import build_bmc_core_formula

__all__ = ["compile_bmc_query"]


def compile_bmc_query(
    model: StateMachine,
    query: Union[str, BmcQuery],
    *,
    options: Optional[BmcOptions] = None,
    query_source_path: Optional[str] = None,
) -> BmcPropertyFormula:
    """Compile a model and BMC query into a solve-ready formula without solving.

    The function preserves the existing three-stage BMC truth source:
    :func:`pyfcstm.bmc.engine.prepare_bmc_query`,
    :func:`pyfcstm.bmc.relation.build_bmc_core_formula`, and
    :func:`pyfcstm.bmc.properties.compile_bmc_property`.  It does not construct
    a property solver, call :func:`pyfcstm.bmc.witness.solve_bmc_property`, or
    decode a witness.

    :param model: State machine to compile against.
    :type model: pyfcstm.model.StateMachine
    :param query: ``.fbmcq`` query text or a parsed query model.
    :type query: Union[str, pyfcstm.bmc.query.BmcQuery]
    :param options: Optional preparation policy, defaults to ``None``.
    :type options: pyfcstm.bmc.engine.BmcOptions, optional
    :param query_source_path: Optional source path for query text, defaults to
        ``None``.
    :type query_source_path: Optional[str], optional
    :return: Compiled property formula ready for an explicit solver call.
    :rtype: pyfcstm.bmc.properties.BmcPropertyFormula
    :raises pyfcstm.bmc.errors.BmcBuildError: If the model, query input, options,
        or generated BMC structures are invalid.
    :raises pyfcstm.bmc.errors.BmcQueryParseError: If query text cannot be
        parsed.
    :raises pyfcstm.bmc.errors.InvalidBmcQuery: If the query is structurally or
        semantically invalid for the model.
    :raises pyfcstm.bmc.errors.InvalidBmcDomain: If the bounded model domain is
        invalid.
    :raises pyfcstm.bmc.errors.UnsupportedBmcQuery: If a valid query construct
        cannot be lowered by the current BMC implementation.

    Example::

        >>> from pyfcstm.bmc.pipeline import compile_bmc_query
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> formula = compile_bmc_query(model, 'check reach <= 1: active("Root");')
        >>> formula.kind, formula.polarity
        ('reach', 'witness')
    """
    context = prepare_bmc_query(
        model,
        query,
        options=options,
        query_source_path=query_source_path,
    )
    core = build_bmc_core_formula(context)
    return compile_bmc_property(core)
