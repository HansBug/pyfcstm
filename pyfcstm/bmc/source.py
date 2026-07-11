"""Macro-step source profiles for FCSTM bounded model checking.

A macro-step source describes the state boundary from which one symbolic
``cycle`` starts before the later macro expander enumerates concrete
:class:`pyfcstm.bmc.macro.CycleCase` objects.  The source layer is deliberately
solver-independent: it consumes the numbered :class:`pyfcstm.bmc.domain.BmcDomain`
snapshot and records only stable ids, display paths, source kind, and origin.
Initial ``where`` predicates stay outside this module and are compiled into the
initial-frame formula by later query/binder layers.

Design contracts:

* ``init`` sources model cold entry through the internal cold-start sentinel.
* ``entry`` sources model hot non-stoppable states whose uncovered branch may
  become semantic delta.
* ``stable_leaf`` sources point at non-sentinel stoppable leaves and use the
  same macro-step semantics for initial hot starts and recurrence frames.
* ``terminated`` sources use a fixed sentinel id and reserved case-label path
  so user states with similar names cannot impersonate it.
* Constructors validate against :class:`pyfcstm.bmc.domain.BmcDomain` eagerly;
  direct dataclass construction remains possible for tests but still performs
  the same validation when a domain is supplied.

The module contains:

* :class:`MacroStepSource` - Immutable source profile consumed by macro-step
  case expansion.
* :func:`init_source`, :func:`entry_source`, :func:`stable_leaf_source`,
  and :func:`terminated_source` - Validated source constructors.
* :func:`source_from_initial_spec` - Convert query initial specifications into
  source profiles without reading the initial predicate.

Example::

    >>> from pyfcstm.bmc.domain import build_bmc_domain
    >>> from pyfcstm.bmc.query import InitialSpec
    >>> from pyfcstm.bmc.source import source_from_initial_spec
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
    >>> source = source_from_initial_spec(domain, InitialSpec())
    >>> source.kind
    'init'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from .domain import (
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BmcDomain,
    StateDomainEntry,
)
from .errors import InvalidBmcDomain, InvalidBmcEncoding, InvalidBmcQuery
from .query import InitialSpec

INIT_CASE_PATH = "__init__"
TERMINATE_CASE_PATH = "__terminate__"

_CanonicalDict = Dict[str, Any]
_StateRef = Union[int, str, StateDomainEntry]
_SOURCE_KINDS = {"init", "entry", "stable_leaf", "terminated"}
_SOURCE_ORIGINS = {"initial", "recurrence"}
_RESERVED_CASE_PATHS = {INIT_CASE_PATH, TERMINATE_CASE_PATH}


def _validate_choice(value: object, choices: set, field_name: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise InvalidBmcEncoding("Unsupported %s: %r." % (field_name, value))
    return value


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidBmcEncoding("%s must be a non-empty string." % field_name)
    return value


def _validate_state_id(value: object, field_name: str = "state id") -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBmcEncoding("%s must be an integer." % field_name)
    return value


def _resolve_state_entry(domain: BmcDomain, state: _StateRef) -> StateDomainEntry:
    if not isinstance(domain, BmcDomain):
        raise InvalidBmcEncoding("domain must be BmcDomain.")
    try:
        if isinstance(state, StateDomainEntry):
            return domain.state_by_id(state.id)
        if isinstance(state, str):
            return domain.state_by_path(state)
        if isinstance(state, bool) or not isinstance(state, int):
            raise InvalidBmcEncoding("state must be a state id, path, or entry.")
        return domain.state_by_id(state)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: BmcDomain lookup rejects unknown state ids or paths
        # supplied to a macro-step source constructor.
        raise InvalidBmcEncoding(str(err)) from err


def _root_state_entry(domain: BmcDomain) -> StateDomainEntry:
    if not isinstance(domain, BmcDomain):
        raise InvalidBmcEncoding("domain must be BmcDomain.")
    roots = [entry for entry in domain.states if entry.is_root]
    if len(roots) != 1:
        raise InvalidBmcEncoding("domain must contain exactly one model root state.")
    return roots[0]


@dataclass(frozen=True)
class MacroStepSource:
    """Source profile for one symbolic macro-step.

    :param kind: Source kind: ``"init"``, ``"entry"``,
        ``"stable_leaf"``, or ``"terminated"``.
    :type kind: str
    :param origin: ``"initial"`` for the ``F_0 -> F_1`` source, or
        ``"recurrence"`` for recurrence-frame sources.
    :type origin: str
    :param source_state_id: Domain state id for the source.  Sentinel sources
        use the fixed negative sentinel ids.
    :type source_state_id: int
    :param source_state_path: Source path used by macro-case labels.  Sentinel
        sources use reserved paths such as ``"__terminate__"``.
    :type source_state_path: str
    :param domain: Optional domain used for eager validation, defaults to
        ``None``.
    :type domain: BmcDomain, optional

    :ivar kind: Source kind.
    :vartype kind: str
    :ivar origin: Source origin.
    :vartype origin: str
    :ivar source_state_id: Domain state id.
    :vartype source_state_id: int
    :ivar source_state_path: Macro-case source path.
    :vartype source_state_path: str

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.bmc.source import entry_source
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> entry_source(domain).allows_semantic_delta
        True
    """

    kind: str
    origin: str
    source_state_id: int
    source_state_path: str
    domain: Optional[BmcDomain] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        kind = _validate_choice(self.kind, _SOURCE_KINDS, "source kind")
        origin = _validate_choice(self.origin, _SOURCE_ORIGINS, "source origin")
        state_id = _validate_state_id(self.source_state_id, "source_state_id")
        source_path = _require_non_empty_string(
            self.source_state_path,
            "source_state_path",
        )
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "source_state_id", state_id)
        object.__setattr__(self, "source_state_path", source_path)
        self._validate_intrinsic_shape()

        if self.domain is not None:
            if not isinstance(self.domain, BmcDomain):
                raise InvalidBmcEncoding("domain must be BmcDomain.")
            self._validate_against_domain(self.domain)

    def _validate_intrinsic_shape(self) -> None:
        if self.kind == "init":
            if self.source_state_id != STATE_INIT_ID:
                raise InvalidBmcEncoding("init source must use the fixed sentinel id.")
            if self.source_state_path != INIT_CASE_PATH:
                raise InvalidBmcEncoding(
                    "init source must use the reserved macro-step path."
                )
        elif self.kind == "entry":
            if self.source_state_id < 0:
                raise InvalidBmcEncoding("entry source must use a model state id.")
            if self.source_state_path in _RESERVED_CASE_PATHS:
                raise InvalidBmcEncoding(
                    "entry source must not use reserved macro-step paths."
                )
        elif self.kind == "stable_leaf":
            if self.source_state_id < 0:
                raise InvalidBmcEncoding(
                    "stable_leaf source must use a model state id."
                )
            if self.source_state_path in _RESERVED_CASE_PATHS:
                raise InvalidBmcEncoding(
                    "stable_leaf source must not use reserved macro-step paths."
                )
        elif self.kind == "terminated":
            if self.source_state_id != STATE_TERMINATE_ID:
                raise InvalidBmcEncoding(
                    "terminated source must use the fixed sentinel id."
                )
            if self.source_state_path != TERMINATE_CASE_PATH:
                raise InvalidBmcEncoding(
                    "terminated source must use the reserved macro-step path."
                )

    def _validate_against_domain(self, domain: BmcDomain) -> None:
        if self.kind == "init":
            self._validate_sentinel_source(
                domain,
                STATE_INIT_ID,
                INIT_CASE_PATH,
                "init",
            )
            return
        if self.kind == "terminated":
            self._validate_sentinel_source(
                domain,
                STATE_TERMINATE_ID,
                TERMINATE_CASE_PATH,
                "terminated",
            )
            return

        try:
            entry = domain.state_by_id(self.source_state_id)
        except InvalidBmcDomain as err:
            # InvalidBmcDomain: BmcDomain lookup rejects unknown source ids
            # supplied through direct MacroStepSource construction.
            raise InvalidBmcEncoding(str(err)) from err
        if self.source_state_path != entry.path:
            raise InvalidBmcEncoding("Source path does not match source state id.")
        if entry.path in _RESERVED_CASE_PATHS:
            raise InvalidBmcEncoding(
                "Model source path must not use reserved macro-step paths."
            )
        if self.kind == "entry":
            if entry.is_sentinel:
                raise InvalidBmcEncoding(
                    "Model source kind cannot use sentinel states."
                )
            if entry.is_stoppable and not entry.is_root:
                raise InvalidBmcEncoding(
                    "entry source must be root or non-stoppable model state."
                )
        elif self.kind == "stable_leaf":
            if self.source_state_id not in domain.stable_state_ids:
                raise InvalidBmcEncoding(
                    "stable_leaf source must use a stable domain state id."
                )
            if entry.is_sentinel or entry.kind != "leaf" or not entry.is_stoppable:
                raise InvalidBmcEncoding(
                    "stable_leaf source must be a non-sentinel stoppable leaf."
                )

    def _validate_sentinel_source(
        self,
        domain: BmcDomain,
        expected_id: int,
        expected_path: str,
        source_name: str,
    ) -> None:
        if self.source_state_id != expected_id:
            raise InvalidBmcEncoding(
                "%s source must use the fixed sentinel id." % source_name
            )
        try:
            domain.state_by_id(expected_id)
        except InvalidBmcDomain as err:
            # InvalidBmcDomain: BmcDomain lookup rejects malformed sentinel
            # metadata while validating an absorb source.
            raise InvalidBmcEncoding(str(err)) from err
        if self.source_state_path != expected_path:
            raise InvalidBmcEncoding(
                "%s source must use the reserved macro-step path." % source_name
            )

    @property
    def allows_semantic_delta(self) -> bool:
        """Return whether this source may emit semantic delta cases.

        :return: ``True`` for cold-init and entry sources.
        :rtype: bool

        Example::

            >>> MacroStepSource('entry', 'recurrence', 0, 'Root').allows_semantic_delta
            True
        """
        return self.kind in {"init", "entry"}

    @property
    def uses_stable_fallback(self) -> bool:
        """Return whether this source must use stable leaf fallback.

        :return: ``True`` for ``"stable_leaf"`` sources.
        :rtype: bool

        Example::

            >>> MacroStepSource('stable_leaf', 'recurrence', 1, 'Root.A').uses_stable_fallback
            True
        """
        return self.kind == "stable_leaf"

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable source dictionary.

        :return: Canonical source profile.
        :rtype: Dict[str, object]

        Example::

            >>> MacroStepSource('entry', 'initial', 0, 'Root').to_canonical()['kind']
            'entry'
        """
        return {
            "node": "macro_step_source",
            "kind": self.kind,
            "origin": self.origin,
            "source_state_id": self.source_state_id,
            "source_state_path": self.source_state_path,
            "allows_semantic_delta": self.allows_semantic_delta,
            "uses_stable_fallback": self.uses_stable_fallback,
        }

    def to_semantic_canonical(self, include_origin: bool = True) -> _CanonicalDict:
        """Return canonical source semantics for equivalence checks.

        :param include_origin: Whether to include the ``origin`` field,
            defaults to ``True``.
        :type include_origin: bool, optional
        :return: Canonical semantic source profile.
        :rtype: Dict[str, object]

        Example::

            >>> source = MacroStepSource('stable_leaf', 'initial', 1, 'Root.A')
            >>> source.to_semantic_canonical(include_origin=False)['kind']
            'stable_leaf'
        """
        result = self.to_canonical()
        if not include_origin:
            result = dict(result)
            result.pop("origin", None)
        return result


def init_source(
    domain: BmcDomain,
    origin: str = "initial",
) -> MacroStepSource:
    """Construct the internal cold-start source.

    :param domain: Domain snapshot containing the fixed init sentinel.
    :type domain: BmcDomain
    :param origin: Source origin, defaults to ``"initial"``.
    :type origin: str, optional
    :return: Validated init source.
    :rtype: MacroStepSource
    :raises InvalidBmcEncoding: If the domain sentinel metadata is missing.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain, STATE_INIT_ID
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> init_source(domain).source_state_id == STATE_INIT_ID
        True
    """
    return MacroStepSource(
        "init",
        origin,
        STATE_INIT_ID,
        INIT_CASE_PATH,
        domain=domain,
    )


def entry_source(
    domain: BmcDomain,
    state: Optional[_StateRef] = None,
    origin: str = "initial",
) -> MacroStepSource:
    """Construct a hot-entry source for a root or non-stoppable model state.

    ``state`` defaults to the model root for callers that need an already-entered
    root boundary, such as recurrence from a query-local non-stoppable source.
    Cold starts use :func:`init_source` instead.  Explicit non-root stoppable
    leaves should be constructed through :func:`stable_leaf_source`.

    :param domain: Domain snapshot that owns the source state.
    :type domain: BmcDomain
    :param state: Source state id, path, or entry, defaults to the root state.
    :type state: int or str or StateDomainEntry, optional
    :param origin: Source origin, defaults to ``"initial"``.
    :type origin: str, optional
    :return: Validated entry source.
    :rtype: MacroStepSource
    :raises InvalidBmcEncoding: If the source is not the root or a
        non-stoppable model state in ``domain``.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> entry_source(domain).kind
        'entry'
    """
    entry = (
        _root_state_entry(domain)
        if state is None
        else _resolve_state_entry(domain, state)
    )
    return MacroStepSource("entry", origin, entry.id, entry.path, domain=domain)


def stable_leaf_source(
    domain: BmcDomain,
    state: _StateRef,
    origin: str = "recurrence",
) -> MacroStepSource:
    """Construct a stable leaf source.

    :param domain: Domain snapshot that owns the source state.
    :type domain: BmcDomain
    :param state: Stoppable leaf state id, path, or entry.
    :type state: int or str or StateDomainEntry
    :param origin: Source origin, defaults to ``"recurrence"``.
    :type origin: str, optional
    :return: Validated stable leaf source.
    :rtype: MacroStepSource
    :raises InvalidBmcEncoding: If ``state`` is not a non-sentinel stoppable
        leaf in ``domain``.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> stable_leaf_source(domain, 'Root').uses_stable_fallback
        True
    """
    entry = _resolve_state_entry(domain, state)
    return MacroStepSource("stable_leaf", origin, entry.id, entry.path, domain=domain)


def terminated_source(
    domain: BmcDomain,
    origin: str = "recurrence",
) -> MacroStepSource:
    """Construct a terminated sentinel absorb source.

    :param domain: Domain snapshot containing the fixed terminate sentinel.
    :type domain: BmcDomain
    :param origin: Source origin, defaults to ``"recurrence"``.
    :type origin: str, optional
    :return: Validated terminated source.
    :rtype: MacroStepSource
    :raises InvalidBmcEncoding: If the domain sentinel metadata is missing.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain, STATE_TERMINATE_ID
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> terminated_source(domain).source_state_id == STATE_TERMINATE_ID
        True
    """
    return MacroStepSource(
        "terminated",
        origin,
        STATE_TERMINATE_ID,
        TERMINATE_CASE_PATH,
        domain=domain,
    )


def source_from_initial_spec(
    domain: BmcDomain,
    initial_spec: InitialSpec,
) -> MacroStepSource:
    """Build the initial macro-step source for an initial specification.

    The optional ``InitialSpec.predicate`` is intentionally ignored here.  It
    belongs to the initial-frame condition ``I_0`` and must not affect source
    kind, fallback partition, or any future :class:`pyfcstm.bmc.macro.CycleCase`
    condition.

    :param domain: Domain snapshot used to resolve initial state paths.
    :type domain: BmcDomain
    :param initial_spec: Parser-independent initial specification.
    :type initial_spec: InitialSpec
    :return: Initial macro-step source.
    :rtype: MacroStepSource
    :raises InvalidBmcQuery: If ``initial_spec`` has an unsupported mode.
    :raises InvalidBmcEncoding: If the referenced state cannot be used as a
        source profile.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.bmc.query import InitialSpec
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> source_from_initial_spec(
        ...     domain, InitialSpec(mode='state', state_path='Root')
        ... ).kind
        'stable_leaf'
    """
    if not isinstance(initial_spec, InitialSpec):
        raise InvalidBmcQuery("initial_spec must be InitialSpec.")
    if initial_spec.mode == "cold":
        return init_source(domain, origin="initial")
    if initial_spec.mode == "terminated":
        return terminated_source(domain, origin="initial")
    if initial_spec.mode == "state":
        entry = _resolve_state_entry(domain, initial_spec.state_path or "")
        if entry.is_stoppable and not entry.is_sentinel:
            return stable_leaf_source(domain, entry, origin="initial")
        return entry_source(domain, entry, origin="initial")
    raise InvalidBmcQuery("unknown initial source mode: %r." % (initial_spec.mode,))


__all__ = [
    "INIT_CASE_PATH",
    "TERMINATE_CASE_PATH",
    "MacroStepSource",
    "init_source",
    "entry_source",
    "stable_leaf_source",
    "terminated_source",
    "source_from_initial_spec",
]
