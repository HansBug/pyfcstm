"""
Event candidate helpers for simulate CLI commands and completion.

This module keeps the ``events`` command and REPL completer aligned when they
summarize the current runtime state.  The helpers intentionally remain a thin
presentation layer: final event applicability is still decided by
``SimulationRuntime.cycle()``.
"""

from typing import List, Optional, Tuple

from ...dsl import EXIT_STATE
from ...model.configuration import Configuration
from ...model.region import Region


POST_EXIT_CONTINUATION_LABEL = "post-exit continuation"


def _event_path(event) -> str:
    """Return the dot-separated path for a model event."""
    return event.path_name


def _add_event_display_item(events, seen_events, event, label):
    """
    Add an event display row unless the event path was already emitted.

    :param events: Accumulated ``(event_path, label)`` rows.
    :type events: List[Tuple[str, Optional[str]]]
    :param seen_events: Event paths that are already present in ``events``.
    :type seen_events: set
    :param event: Model event to append.
    :type event: Event
    :param label: Display label for the event.
    :type label: str, optional
    :return: ``None``.
    :rtype: None
    """
    event_path = _event_path(event)
    if event_path in seen_events:
        return
    seen_events.add(event_path)
    events.append((event_path, label))


def _has_exit_transition(state) -> bool:
    """
    Return whether a state has a transition to its parent's ``[*]`` boundary.

    :param state: State to inspect.
    :type state: State
    :return: ``True`` if any outgoing transition targets ``[*]``.
    :rtype: bool
    """
    return any(transition.to_state == EXIT_STATE for transition in state.transitions_from)


def _iter_post_exit_continuation_states(state):
    """
    Yield ancestor states that can consume events after a child exit chain.

    Starting from the current active state, each ``state -> [*]`` transition puts
    the parent in ``post_child_exit`` mode.  If that parent can also exit to
    ``[*]``, runtime execution may continue upward in the same cycle before a
    named ancestor transition consumes another supplied event.  This generator
    mirrors that parent-chain shape for presentation only; guards and final
    reachability remain runtime responsibilities.

    :param state: Current active state.
    :type state: State
    :return: Ancestor states reached after one or more possible ``[*]`` exits.
    :rtype: Iterator[State]
    """
    current = state
    while _has_exit_transition(current):
        parent = current.parent
        if isinstance(parent, Region):
            # A region is not a state of its own: the continuation belongs to
            # the state that owns the regions.
            parent = parent.parent
        if parent is None or parent.is_root_state:
            return
        yield parent
        current = parent


def _active_states(runtime) -> list:
    """
    Return the states the runtime currently rests in.

    :param runtime: Simulation runtime to inspect.
    :type runtime: SimulationRuntime
    :return: One state for a model without regions; for a model with regions
        every active leaf in writing order, or the root state before the first
        cycle.
    :rtype: list
    :raises IndexError: If the runtime has no active stack, for example after
        termination.
    """
    current = runtime.current_state
    if isinstance(current, Configuration):
        return list(current.leaves) or [runtime.state_machine.root_state]
    return [current] if current else []


def get_current_event_display_items(runtime) -> List[Tuple[str, Optional[str]]]:
    """
    Return event display rows for the runtime's current position.

    The result preserves the legacy ``(full_path, short_name)`` shape used by
    :class:`pyfcstm.entry.simulate.display.StateDisplay`. Direct leaf events use
    the event's short name as before. Parent-level continuation candidates use
    ``post-exit continuation`` as the display label and keep the full event path
    in the second column.

    A model with regions rests in several leaves. The rows of every leaf are
    listed once per event, in the order of the leaves. A short name is only shown
    for an event when it leads to that event from every leaf that offers the
    name, so a name that two leaves use for different events is shown for
    neither: it would be refused as ambiguous, and only the full path works.

    :param runtime: Simulation runtime to inspect.
    :type runtime: SimulationRuntime
    :return: Event display rows.
    :rtype: List[Tuple[str, Optional[str]]]

    Example::

        >>> from pyfcstm.entry.simulate.events import get_current_event_display_items
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.simulate import SimulationRuntime
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> P;
        ...     state P {
        ...         region L { [*] -> X; state X { event Go; event Ping; }
        ...                    X -> X :: Go; X -> X :: Ping; }
        ...         region R { [*] -> Y; state Y { event Ping; } Y -> Y :: Ping; }
        ...     }
        ... }
        ... ''')
        >>> runtime = SimulationRuntime(model)
        >>> _ = runtime.cycle()
        >>> get_current_event_display_items(runtime)
        [('Root.P.L.X.Go', 'Go'), ('Root.P.L.X.Ping', None), ('Root.P.R.Y.Ping', None)]
    """
    if runtime.is_ended:
        return []
    try:
        active_states = _active_states(runtime)
    except IndexError:
        # IndexError: SimulationRuntime.current_state raises when the runtime
        # has no active stack, for example after termination.
        return []
    events: List[Tuple[str, Optional[str]]] = []
    seen_events = set()
    short_names = {}
    for current_state in active_states:
        for transition in current_state.transitions_from:
            if not transition.event:
                continue
            event_path = _event_path(transition.event)
            if event_path in seen_events:
                continue
            seen_events.add(event_path)
            short_name = transition.event.name
            short_names.setdefault(short_name, []).append(event_path)
            events.append((event_path, short_name if short_name != event_path else None))
        for state in _iter_post_exit_continuation_states(current_state):
            for transition in state.transitions_from:
                if not transition.event:
                    continue
                _add_event_display_item(
                    events,
                    seen_events,
                    transition.event,
                    POST_EXIT_CONTINUATION_LABEL,
                )
    ambiguous = {name for name, paths in short_names.items() if len(paths) > 1}
    return [
        (path, None if label in ambiguous else label) for path, label in events
    ]


def get_current_event_completion_items(runtime) -> List[Tuple[str, str]]:
    """
    Return ``(event_text, display_meta)`` pairs for REPL event completion.

    Direct events expose both full-path and short-name completions. Continuation
    candidates expose only their full path so users can pass the unambiguous
    parent-scoped event to ``cycle``.

    :param runtime: Simulation runtime to inspect.
    :type runtime: SimulationRuntime
    :return: Completion text and metadata pairs.
    :rtype: List[Tuple[str, str]]
    """
    completion_items: List[Tuple[str, str]] = []
    seen_items = set()

    for full_path, label in get_current_event_display_items(runtime):
        if label == POST_EXIT_CONTINUATION_LABEL:
            if full_path not in seen_items:
                seen_items.add(full_path)
                completion_items.append((full_path, POST_EXIT_CONTINUATION_LABEL))
            continue

        if full_path not in seen_items:
            seen_items.add(full_path)
            completion_items.append((full_path, "event name"))
        if label and label not in seen_items:
            seen_items.add(label)
            completion_items.append((label, "event name"))

    return sorted(completion_items, key=lambda item: item[0])
