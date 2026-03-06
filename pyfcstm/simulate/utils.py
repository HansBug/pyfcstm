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
