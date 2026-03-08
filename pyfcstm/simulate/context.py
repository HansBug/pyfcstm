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

from dataclasses import dataclass
from typing import Dict, Union, Tuple


@dataclass(frozen=True)
class ReadOnlyExecutionContext:
    """
    Read-only execution context for abstract function handlers.

    Provides immutable access to current state and variable values without
    allowing modifications. This context is passed to registered abstract
    handlers during execution.

    :param state_path: Current active state path from root to leaf
    :type state_path: Tuple[str, ...]
    :param vars: Snapshot of current variable values (immutable copy)
    :type vars: Dict[str, Union[int, float]]
    :param action_name: Full path name of the abstract action being executed
    :type action_name: str
    :param action_stage: Lifecycle stage ('enter', 'during', 'exit')
    :type action_stage: str

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
    """

    state_path: Tuple[str, ...]
    vars: Dict[str, Union[int, float]]
    action_name: str
    action_stage: str

    def get_var(self, name: str) -> Union[int, float]:
        """
        Get variable value by name.

        :param name: Variable name
        :type name: str
        :return: Variable value
        :rtype: Union[int, float]
        :raises KeyError: If variable does not exist

        Example::

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

            >>> ctx.has_var('counter')
            True
            >>> ctx.has_var('nonexistent')
            False
        """
        return name in self.vars
