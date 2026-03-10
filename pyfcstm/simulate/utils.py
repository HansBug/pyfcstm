"""
Naming utilities for simulation runtime logging and diagnostics.

This module provides helper functions for converting runtime objects into
human-readable string representations. These utilities are used throughout
the simulation runtime for logging execution steps and presenting lifecycle
action paths in diagnostic messages.

The module contains the following main components:

* :func:`is_state_resolve_event_path` - Check if a path string is definitely for State.resolve_event.

These functions are essential for debugging state machine execution, as they
provide consistent naming conventions that match the DSL source structure.

Example::

    >>> from pyfcstm.simulate.utils import is_state_resolve_event_path
    >>> # Check event path syntax
    >>> is_state_resolve_event_path('/global.shutdown')
    True
    >>> is_state_resolve_event_path('.error')
    True

.. note::
   For action naming, use the :attr:`OnStage.func_name` or :attr:`OnAspect.func_name`
   property directly. For event naming, use the :attr:`Event.path_name` property.
"""


def is_state_resolve_event_path(path: str) -> bool:
    """
    Check if an event path string is definitely for State.resolve_event.

    This function determines whether a path string uses State.resolve_event
    syntax (relative, parent-relative, or absolute notation) based on its
    grammatical features. It returns True only when the path is definitively
    a State.resolve_event path, and False when uncertain.

    **Return Values**:

    - ``True``: The path is definitely for State.resolve_event (uses special notation)
    - ``False``: Uncertain - could be either State or StateMachine resolve_event

    **Detection Rules**:

    1. **Absolute paths** (starting with ``/``): Definitely State.resolve_event
    2. **Parent-relative paths** (starting with ``.``): Definitely State.resolve_event
    3. **Plain paths** (no special prefix): Uncertain (could be either)

    :param path: Event path string to check
    :type path: str
    :return: True if definitely State.resolve_event syntax, False if uncertain
    :rtype: bool

    Example::

        >>> from pyfcstm.simulate.utils import is_state_resolve_event_path
        >>> # Absolute paths - definitely State.resolve_event
        >>> is_state_resolve_event_path('/global.shutdown')
        True
        >>> # Parent-relative paths - definitely State.resolve_event
        >>> is_state_resolve_event_path('.error')
        True
        >>> is_state_resolve_event_path('..system.error')
        True
        >>> # Plain paths - uncertain (could be either)
        >>> is_state_resolve_event_path('Root.System.error')
        False
        >>> is_state_resolve_event_path('error.critical')
        False

    .. note::
       This function only detects paths that are **definitely** State.resolve_event
       based on syntax. Plain paths without special notation are considered uncertain
       because they could be valid for either State or StateMachine resolve_event.
    """
    if not path:
        return False

    # Absolute paths (starting with '/') are definitely State.resolve_event
    if path.startswith('/'):
        return True

    # Parent-relative paths (starting with '.') are definitely State.resolve_event
    if path.startswith('.'):
        return True

    # Plain paths without special notation are uncertain
    return False
