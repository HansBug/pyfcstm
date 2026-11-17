"""
Read-only execution context for abstract function handlers.

This module provides the :class:`ReadOnlyExecutionContext` class that gives
abstract function handlers read-only access to the current execution state
including the active state path and variable values.

The module contains the following main components:

* :class:`ReadOnlyExecutionContext` - Immutable context passed to abstract handlers.

Example::

    >>> from pyfcstm.simulate import ReadOnlyExecutionContext
    >>> def my_handler(ctx: ReadOnlyExecutionContext):
    ...     print(f"State: {ctx.get_full_state_path()}")
    ...     print(f"Counter: {ctx.get_var('counter')}")
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional, Union, Tuple

#: Supplies the configuration snapshot of the cycle that is executing, so that
#: every context built while handlers run carries the position at the moment
#: of its construction. The runtime sets it for the duration of a committed
#: cycle; outside a cycle it is ``None``.
_configuration_provider: ContextVar[Optional[Callable[[], Any]]] = ContextVar(
    "pyfcstm_simulate_configuration_provider", default=None
)


def _current_configuration() -> Optional[Any]:
    """
    Snapshot the position of the cycle that is executing, if any.

    :return: The configuration at this moment, or ``None`` when no committed
        cycle is running, for example for a context built by hand.
    :rtype: Optional[pyfcstm.model.configuration.Configuration]
    """
    provider = _configuration_provider.get()
    return None if provider is None else provider()


@dataclass(frozen=True)
class ReadOnlyExecutionContext:
    """
    Read-only execution context for abstract function handlers.

    Provides immutable access to current state and variable values without
    allowing modifications. This context is passed to registered abstract
    handlers during execution. The existing ``state_path``,
    ``action_name``, and ``action_stage`` fields keep their public meaning, and
    the additional metadata fields expose the same callsite information in a
    fixture-friendly shape.

    :param state_path: State path that owns the executing action. It is a leaf
        for leaf lifecycle actions and for ancestor aspect actions, which
        run for a descendant leaf's cycle; entering or leaving a composite
        state, or running a plain ``during`` action declared on one, gives
        that composite state's own path. In a model with regions, an aspect
        reports the deepest state common to every active leaf it wraps: the
        leaf when it wraps a single branch, and the owner of the regions when
        it wraps several.
    :type state_path: Tuple[str, ...]
    :param vars: Snapshot of current variable values (immutable mapping copy)
    :type vars: Mapping[str, Union[int, float]]
    :param action_name: Full path name of the resolved abstract action target.
    :type action_name: str
    :param action_stage: Lifecycle stage at the current callsite
        (``'enter'``, ``'during'``, or ``'exit'``).
    :type action_stage: str
    :param active_leaf: Runtime state path where the action executes: the
        active leaf state when one is active, otherwise the action's host
        state path. Omitting it selects the host path via ``state_path``,
        which is what every callsite without an active leaf relies on.
    :type active_leaf: Tuple[str, ...], optional
    :param call_stage: Explicit callsite lifecycle stage. When omitted, it
        defaults to ``action_stage``.
    :type call_stage: str, optional
    :param abstract_target: Explicit resolved abstract target path. When
        omitted, it defaults to ``action_name``.
    :type abstract_target: str, optional
    :param named_ref: Path of the named ``ref`` action at the callsite, or
        ``None`` when the callsite is not a named ``ref``. Only the callsite
        names a call: a named action arrived at by following a ``ref`` is that
        reference's target, so a chain starting from an anonymous ``ref``
        reports ``None`` however many named actions it passes through.
    :type named_ref: Optional[str], optional
    :param configuration: Immutable snapshot of the whole position at the
        moment of the call, as a :class:`pyfcstm.model.configuration.Configuration`.
        It shows regions that already moved earlier in the same cycle in their
        new place and regions that have not yet been initialized as ``[init]``.
        Contexts that the runtime builds for handlers always carry it; a context
        built by hand, outside a running cycle, defaults to ``None``.
    :type configuration: Optional[pyfcstm.model.configuration.Configuration], optional

    Example::

        >>> ctx = ReadOnlyExecutionContext(
        ...     state_path=('System', 'Active'),
        ...     vars={'counter': 10, 'temperature': 25.5},
        ...     action_name='System.Active.Monitor',
        ...     action_stage='during'
        ... )
        >>> ctx.get_state_name()
        'Active'
        >>> ctx.get_var('counter')
        10
        >>> ctx.active_leaf
        ('System', 'Active')
        >>> ctx.abstract_target
        'System.Active.Monitor'
    """

    state_path: Tuple[str, ...]
    vars: Mapping[str, Union[int, float]]
    action_name: str
    action_stage: str
    active_leaf: Optional[Tuple[str, ...]] = None
    call_stage: Optional[str] = None
    abstract_target: Optional[str] = None
    named_ref: Optional[str] = None
    parameters: Mapping[str, Union[int, float]] = field(
        default_factory=dict, repr=False
    )
    inputs: Mapping[str, Union[int, float]] = field(default_factory=dict, repr=False)
    configuration: Optional[Any] = field(default_factory=_current_configuration, repr=False)

    def __post_init__(self) -> None:
        """
        Freeze and normalize the context snapshot.

        Variable mappings are copied into a read-only proxy. Path-like metadata
        is normalized to tuples, and optional callsite aliases are derived from
        the existing four constructor fields when omitted. This preserves the
        original direct-construction API while exposing richer metadata to
        runtime-created handler contexts.

        :return: ``None``.
        :rtype: None

        Example::

            >>> ctx = ReadOnlyExecutionContext(
            ...     state_path=('Root', 'A'),
            ...     vars={},
            ...     action_name='Root.A.Touch',
            ...     action_stage='during',
            ... )
            >>> ctx.call_stage
            'during'
            >>> ctx.named_ref is None
            True
        """
        object.__setattr__(self, "state_path", tuple(self.state_path))
        object.__setattr__(self, "vars", MappingProxyType(dict(self.vars)))
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        object.__setattr__(self, "inputs", MappingProxyType(dict(self.inputs)))
        active_leaf = self.state_path if self.active_leaf is None else self.active_leaf
        object.__setattr__(self, "active_leaf", tuple(active_leaf))
        call_stage = self.action_stage if self.call_stage is None else self.call_stage
        object.__setattr__(self, "call_stage", call_stage)
        abstract_target = (
            self.action_name if self.abstract_target is None else self.abstract_target
        )
        object.__setattr__(self, "abstract_target", abstract_target)

    def get_var(self, name: str) -> Union[int, float]:
        """
        Get variable value by name.

        :param name: Variable name
        :type name: str
        :return: Variable value
        :rtype: Union[int, float]
        :raises KeyError: If variable does not exist

        Example::

            >>> ctx = ReadOnlyExecutionContext(
            ...     state_path=('System', 'Active'),
            ...     vars={'counter': 10},
            ...     action_name='Initialize',
            ...     action_stage='enter',
            ... )
            >>> ctx.get_var('counter')
            10
        """
        return self.vars[name]

    def get_state_name(self) -> str:
        """
        Get current state name (last component of path).

        :return: State name, or empty string if no state is active
        :rtype: str

        Example::

            >>> ctx = ReadOnlyExecutionContext(
            ...     state_path=('System', 'Active'),
            ...     vars={'counter': 10},
            ...     action_name='Initialize',
            ...     action_stage='enter',
            ... )
            >>> ctx.get_state_name()
            'Active'
        """
        return self.state_path[-1] if self.state_path else ""

    def get_full_state_path(self) -> str:
        """
        Get full state path as dot-separated string.

        :return: Full state path
        :rtype: str

        Example::

            >>> ctx = ReadOnlyExecutionContext(
            ...     state_path=('System', 'Active'),
            ...     vars={'counter': 10},
            ...     action_name='Initialize',
            ...     action_stage='enter',
            ... )
            >>> ctx.get_full_state_path()
            'System.Active'
        """
        return ".".join(self.state_path)

    def has_var(self, name: str) -> bool:
        """
        Check if a variable exists.

        :param name: Variable name
        :type name: str
        :return: ``True`` if variable exists
        :rtype: bool

        Example::

            >>> ctx = ReadOnlyExecutionContext(
            ...     state_path=('System', 'Active'),
            ...     vars={'counter': 10},
            ...     action_name='Initialize',
            ...     action_stage='enter',
            ... )
            >>> ctx.has_var('counter')
            True
            >>> ctx.has_var('nonexistent')
            False
        """
        return name in self.vars
