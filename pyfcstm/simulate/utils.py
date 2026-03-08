"""
Naming utilities for simulation runtime logging and diagnostics.

This module provides helper functions for converting runtime objects into
human-readable string representations. These utilities are used throughout
the simulation runtime for logging execution steps, indexing events for
transition matching, and presenting lifecycle action paths in diagnostic
messages.

The module contains the following main components:

* :func:`get_event_name` - Convert an event object to its dot-separated path.
* :func:`get_func_name` - Convert a lifecycle or aspect action to its readable path.
* :func:`is_state_resolve_event_path` - Check if a path string is definitely for State.resolve_event.

These functions are essential for debugging state machine execution, as they
provide consistent naming conventions that match the DSL source structure.

Example::

    >>> from pyfcstm.model import Event, OnStage, State
    >>> from pyfcstm.simulate.utils import get_event_name, get_func_name
    >>> # Event naming
    >>> event = Event(name='Start', path=('System', 'Idle', 'Start'))
    >>> get_event_name(event)
    'System.Idle.Start'
    >>> # Action naming
    >>> state = State(name='Active', path=('System', 'Active'))
    >>> action = OnStage(name='Initialize', state_path=('System', 'Active', 'Initialize'))
    >>> get_func_name(action)
    'System.Active.Initialize'
"""


from typing import Union

from ..model import Event, OnStage, OnAspect


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


def get_event_name(event: Event) -> str:
    """
    Convert an event object to its canonical dot-separated path string.

    The returned string serves as the stable identifier used by the runtime
    for event indexing and transition matching. This format matches the
    fully-qualified event paths used in the DSL.

    Event paths follow the state hierarchy where the event is defined. For
    example, a local event ``Go`` defined in state ``System.Active`` would
    have the path ``System.Active.Go``.

    :param event: Event object to convert to string representation.
    :type event: Event
    :return: Dot-separated event path matching the DSL structure.
    :rtype: str

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.simulate.utils import get_event_name
        >>> dsl_code = '''
        ... state System {
        ...     state Idle;
        ...     state Active;
        ...     [*] -> Idle;
        ...     Idle -> Active :: Start;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        >>> sm = parse_dsl_node_to_state_machine(ast)
        >>> # Find the Start event
        >>> start_event = sm.root_state.substates['Idle'].events['Start']
        >>> get_event_name(start_event)
        'System.Idle.Start'

    .. note::
       This function is used internally by :class:`SimulationRuntime` when
       building the event dictionary for transition matching. The returned
       string must be stable and unique within the state machine.
    """
    return '.'.join(event.path)


def get_func_name(func: Union[OnStage, OnAspect]) -> str:
    """
    Convert a lifecycle or aspect action to a readable dot-separated path string.

    The returned string represents the action's location in the state hierarchy,
    making it easy to identify which state owns the action in log messages and
    diagnostic output.

    Unnamed actions (where the name component is ``None``) are rendered with
    ``<unnamed>`` in the terminal position. This ensures log messages can
    distinguish between named and anonymous actions while maintaining a
    consistent format.

    :param func: Lifecycle or aspect action to convert to string representation.
    :type func: Union[OnStage, OnAspect]
    :return: Dot-separated action path with state hierarchy.
    :rtype: str

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.simulate.utils import get_func_name
        >>> dsl_code = '''
        ... state System {
        ...     state Active {
        ...         enter Initialize {
        ...             # Named action
        ...         }
        ...         during {
        ...             # Unnamed action
        ...         }
        ...     }
        ...     [*] -> Active;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        >>> sm = parse_dsl_node_to_state_machine(ast)
        >>> active_state = sm.root_state.substates['Active']
        >>> # Named enter action
        >>> get_func_name(active_state.on_enters[0])
        'System.Active.Initialize'
        >>> # Unnamed during action
        >>> get_func_name(active_state.on_durings[0])
        'System.Active.<unnamed>'

    .. note::
       This function is used by :class:`SimulationRuntime` when logging
       action execution. The format matches the DSL structure, making it
       easy to correlate runtime logs with source code.
    """
    sp = func.state_path
    if sp[-1] is None:
        sp = tuple((*sp[:-1], '<unnamed>'))
    return '.'.join(sp)
