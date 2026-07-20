"""Preparation engine for FCSTM bounded model checking queries.

The engine layer is the first BMC handoff point that combines a
:class:`pyfcstm.model.StateMachine` with a parser-independent
:class:`pyfcstm.bmc.query.BmcQuery`.  It parses query text when necessary,
performs structure-only binding before any domain construction, builds the
bounded domain, resolves query references against that domain, and returns a
JSON-stable preparation context.

This module is intentionally a preparation layer only.  It does not expand
macro-step cases, lower formulas to Z3, compile property objectives, decode
witnesses, expose CLI commands, or register anything under
:mod:`pyfcstm.verify`.

The module contains:

* :class:`BmcOptions` - Prepare-time policy options.
* :class:`BmcPreparedContext` - Prepared query/domain handoff data.
* :class:`BmcEngine` - Reusable model-bound preparation entry point.
* :func:`prepare_bmc_query` - Function-style convenience API.

Example::

    >>> from pyfcstm.bmc.engine import BmcEngine
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('state Root;')
    >>> context = BmcEngine(model).prepare('check reach <= 1: active("Root");')
    >>> context.bound
    1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Union

from .binding import (
    BoundBmcQuery,
    BoundReference,
    bind_bmc_query,
    bind_bmc_query_structure,
)
from .domain import BmcDomain, build_bmc_domain
from .errors import BmcBuildError
from .parse import parse_bmc_query
from .provenance import SourceDocumentRegistry
from .query import BmcQuery
from pyfcstm.model import StateMachine

_CanonicalDict = Dict[str, Any]
_QueryInput = Union[str, BmcQuery]


@dataclass(frozen=True)
class BmcOptions:
    """Prepare-time policy options for BMC query preparation.

    The first engine prototype keeps options deliberately small.  ``max_bound``
    is a policy guard for expensive accidental queries; solver tactics,
    timeouts, witness formatting, and CLI concerns belong to later layers.

    :param max_bound: Maximum allowed query bound, or ``None`` for no limit,
        defaults to ``None``.
    :type max_bound: Optional[int], optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``max_bound`` is not ``None``
        and not a positive integer.

    Example::

        >>> BmcOptions(max_bound=3).to_canonical()["max_bound"]
        3
    """

    max_bound: Optional[int] = None

    def __post_init__(self) -> None:
        if self.max_bound is None:
            return
        if isinstance(self.max_bound, bool) or not isinstance(self.max_bound, int):
            raise BmcBuildError("max_bound must be None or a positive integer.")
        if self.max_bound <= 0:
            raise BmcBuildError("max_bound must be None or a positive integer.")

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable options dictionary.

        :return: Canonical options dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> BmcOptions().to_canonical()
            {'node': 'bmc_options', 'max_bound': None}
        """
        return {"node": "bmc_options", "max_bound": self.max_bound}


def _require_field(value: object, field_name: str, field_type: type) -> None:
    if not isinstance(value, field_type):
        raise BmcBuildError("%s must be %s." % (field_name, field_type.__name__))


@dataclass(frozen=True)
class BmcPreparedContext:
    """Prepared model, query, domain, and binding snapshot.

    Prepared contexts are solver-independent handoff objects.  The raw model is
    retained for future engine stages, while :meth:`to_canonical` deliberately
    emits only JSON-stable query, bound-query, domain, option, and source-text
    data.

    :param model: State machine used for domain numbering.
    :type model: pyfcstm.model.StateMachine
    :param query: Parser-independent BMC query object.
    :type query: pyfcstm.bmc.query.BmcQuery
    :param bound_query: Model/domain-aware bound query snapshot.
    :type bound_query: pyfcstm.bmc.binding.BoundBmcQuery
    :param domain: Bounded model domain.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param options: Effective preparation options.
    :type options: BmcOptions
    :param source_text: Original ``.fbmcq`` text for string inputs, defaults to
        ``None`` for AST inputs.
    :type source_text: Optional[str], optional
    :param query_source_path: Display/source path for the query text, defaults
        to ``None`` when no reliable path is available.
    :type query_source_path: Optional[str], optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If fields are malformed or
        inconsistent.

    Example::

        >>> from pyfcstm.bmc.engine import BmcEngine
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> BmcEngine(model).prepare('check reach <= 1: active("Root");').bound
        1
    """

    model: StateMachine
    query: BmcQuery
    bound_query: BoundBmcQuery
    domain: BmcDomain
    options: BmcOptions
    source_text: Optional[str] = None
    query_source_path: Optional[str] = field(default=None, repr=False, compare=False)
    _source_registry: Optional[SourceDocumentRegistry] = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _require_field(self.model, "model", StateMachine)
        _require_field(self.query, "query", BmcQuery)
        _require_field(self.bound_query, "bound_query", BoundBmcQuery)
        _require_field(self.domain, "domain", BmcDomain)
        _require_field(self.options, "options", BmcOptions)
        if self.source_text is not None and not isinstance(self.source_text, str):
            raise BmcBuildError("source_text must be None or str.")
        if self.query_source_path is not None and (
            not isinstance(self.query_source_path, str) or not self.query_source_path
        ):
            raise BmcBuildError("query_source_path must be None or a non-empty string.")
        effective_query_path = self.query_source_path or getattr(
            self.query, "_source_path", None
        )
        if self._source_registry is None:
            documents = dict(getattr(self.model, "_source_documents", {}))
            if effective_query_path is not None and self.source_text is not None:
                documents[effective_query_path] = self.source_text
            display_root = getattr(self.model, "_source_root", None)
            registry = SourceDocumentRegistry(documents, display_root=display_root)
            object.__setattr__(self, "_source_registry", registry)
        if self.query_source_path is None and effective_query_path is not None:
            object.__setattr__(self, "query_source_path", effective_query_path)
        if self.domain.bound != self.query.property.bound:
            raise BmcBuildError(
                "domain bound %d does not match query bound %d."
                % (self.domain.bound, self.query.property.bound)
            )
        if self.bound_query.property.bound != self.domain.bound:
            raise BmcBuildError(
                "bound query bound %d does not match domain bound %d."
                % (self.bound_query.property.bound, self.domain.bound)
            )
        if self.bound_query.query.to_canonical() != self.query.to_canonical():
            raise BmcBuildError("bound query source does not match query.")

    @property
    def bound(self) -> int:
        """Return the prepared query/domain bound.

        :return: Positive BMC bound.
        :rtype: int

        Example::

            >>> from pyfcstm.bmc.engine import BmcEngine
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> BmcEngine(model).prepare('check reach <= 1: active("Root");').bound
            1
        """
        return self.domain.bound

    @property
    def references(self) -> Tuple[BoundReference, ...]:
        """Return references discovered during domain-aware query binding.

        :return: Bound query references.
        :rtype: Tuple[pyfcstm.bmc.binding.BoundReference, ...]

        Example::

            >>> from pyfcstm.bmc.engine import BmcEngine
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> BmcEngine(model).prepare('check reach <= 1: active("Root");').references[0].kind
            'state'
        """
        return self.bound_query.references

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable prepared-context dictionary.

        The state-machine object is intentionally omitted because it is not a
        JSON primitive and the domain snapshot contains the stable numbering
        data needed by later BMC stages.

        :return: Canonical prepared context.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.engine import BmcEngine
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> BmcEngine(model).prepare('check reach <= 1: active("Root");').to_canonical()["node"]
            'prepared_context'
        """
        return {
            "node": "prepared_context",
            "options": self.options.to_canonical(),
            "source_text": self.source_text,
            "query": self.query.to_canonical(),
            "bound_query": self.bound_query.to_canonical(),
            "domain": self.domain.to_canonical(),
        }


def _require_options(options: Optional[BmcOptions]) -> BmcOptions:
    if options is None:
        return BmcOptions()
    if not isinstance(options, BmcOptions):
        raise BmcBuildError("options must be BmcOptions.")
    return options


def _coerce_query(
    query: object, query_source_path: Optional[str]
) -> Tuple[BmcQuery, Optional[str], Optional[str]]:
    if isinstance(query, str):
        parsed = parse_bmc_query(query, source_path=query_source_path)
        return parsed, query, query_source_path
    if isinstance(query, BmcQuery):
        return query, None, query_source_path or getattr(query, "_source_path", None)
    raise BmcBuildError("query must be a str or BmcQuery.")


def _enforce_max_bound(options: BmcOptions, query_bound: int) -> None:
    if options.max_bound is not None and query_bound > options.max_bound:
        raise BmcBuildError(
            "max_bound policy rejected query_bound=%d with max_bound=%d."
            % (query_bound, options.max_bound)
        )


class BmcEngine:
    """Model-bound entry point for BMC query preparation.

    :param model: State machine to prepare queries against.
    :type model: pyfcstm.model.StateMachine
    :param options: Default preparation options, defaults to ``BmcOptions()``.
    :type options: BmcOptions, optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``model`` or ``options`` is
        invalid.

    Example::

        >>> from pyfcstm.bmc.engine import BmcEngine
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> engine = BmcEngine(model)
        >>> engine.prepare('check reach <= 1: active("Root");').bound
        1
    """

    def __init__(
        self, model: StateMachine, options: Optional[BmcOptions] = None
    ) -> None:
        """Initialize a BMC preparation engine.

        :param model: State machine to prepare queries against.
        :type model: pyfcstm.model.StateMachine
        :param options: Default preparation options, defaults to
            ``BmcOptions()``.
        :type options: BmcOptions, optional
        :return: ``None``.
        :rtype: None
        :raises pyfcstm.bmc.errors.BmcBuildError: If ``model`` or ``options``
            is invalid.

        Example::

            >>> from pyfcstm.bmc.engine import BmcEngine
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> isinstance(BmcEngine(load_state_machine_from_text('state Root;')), BmcEngine)
            True
        """
        if not isinstance(model, StateMachine):
            raise BmcBuildError("model must be StateMachine.")
        self._model = model
        self._options = _require_options(options)

    @property
    def model(self) -> StateMachine:
        """Return the state machine held by this engine.

        :return: State machine used for preparation.
        :rtype: pyfcstm.model.StateMachine

        Example::

            >>> from pyfcstm.bmc.engine import BmcEngine
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> BmcEngine(model).model is model
            True
        """
        return self._model

    @property
    def options(self) -> BmcOptions:
        """Return the engine default preparation options.

        :return: Default options.
        :rtype: BmcOptions

        Example::

            >>> from pyfcstm.bmc.engine import BmcEngine, BmcOptions
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> BmcEngine(load_state_machine_from_text('state Root;'), BmcOptions(max_bound=1)).options.max_bound
            1
        """
        return self._options

    def prepare(
        self,
        query: _QueryInput,
        options: Optional[BmcOptions] = None,
        *,
        query_source_path: Optional[str] = None,
    ) -> BmcPreparedContext:
        """Prepare a BMC query text or AST against this engine's model.

        Per-call ``options`` completely replace the engine default options.
        When ``options`` is omitted, the engine default options are used.

        :param query: Query text or parser-independent query object.
        :type query: Union[str, pyfcstm.bmc.query.BmcQuery]
        :param options: Per-call options, defaults to ``None``.
        :type options: BmcOptions, optional
        :param query_source_path: Optional source path for query text, defaults
            to ``None``.
        :type query_source_path: Optional[str], optional
        :return: Prepared BMC context.
        :rtype: BmcPreparedContext
        :raises pyfcstm.bmc.errors.BmcQueryParseError: If query text cannot be
            parsed.
        :raises pyfcstm.bmc.errors.InvalidBmcQuery: If query binding fails.
        :raises pyfcstm.bmc.errors.InvalidBmcDomain: If domain construction
            fails.
        :raises pyfcstm.bmc.errors.BmcBuildError: If inputs or option policy
            are invalid.

        Example::

            >>> from pyfcstm.bmc.engine import BmcEngine
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> BmcEngine(model).prepare('check reach <= 1: active("Root");').domain.bound
            1
        """
        effective_options = (
            self.options if options is None else _require_options(options)
        )
        parsed_query, source_text, effective_query_path = _coerce_query(
            query, query_source_path
        )
        structural_bound_query = bind_bmc_query_structure(parsed_query)
        query_bound = structural_bound_query.property.bound
        _enforce_max_bound(effective_options, query_bound)
        domain = build_bmc_domain(self.model, query_bound)
        bound_query = bind_bmc_query(parsed_query, domain=domain)
        return BmcPreparedContext(
            model=self.model,
            query=parsed_query,
            bound_query=bound_query,
            domain=domain,
            options=effective_options,
            source_text=source_text,
            query_source_path=effective_query_path,
        )


def prepare_bmc_query(
    model: StateMachine,
    query: _QueryInput,
    options: Optional[BmcOptions] = None,
    *,
    query_source_path: Optional[str] = None,
) -> BmcPreparedContext:
    """Prepare a BMC query with a one-shot engine.

    This function is an engine-level convenience wrapper.  It performs the
    full prepare pipeline and returns a :class:`BmcPreparedContext`, unlike
    :func:`pyfcstm.bmc.binding.bind_bmc_query`, which only returns a bound
    query snapshot.

    :param model: State machine to prepare against.
    :type model: pyfcstm.model.StateMachine
    :param query: Query text or parser-independent query object.
    :type query: Union[str, pyfcstm.bmc.query.BmcQuery]
    :param options: Preparation options, defaults to ``None``.
    :type options: BmcOptions, optional
    :param query_source_path: Optional source path for query text, defaults to
        ``None``.
    :type query_source_path: Optional[str], optional
    :return: Prepared BMC context.
    :rtype: BmcPreparedContext
    :raises pyfcstm.bmc.errors.BmcError: If parsing, binding, domain
        construction, or option policy fails.

    Example::

        >>> from pyfcstm.bmc.engine import prepare_bmc_query
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> prepare_bmc_query(model, 'check reach <= 1: active("Root");').bound
        1
    """
    return BmcEngine(model, options).prepare(query, query_source_path=query_source_path)


__all__ = [
    "BmcOptions",
    "BmcPreparedContext",
    "BmcEngine",
    "prepare_bmc_query",
]
