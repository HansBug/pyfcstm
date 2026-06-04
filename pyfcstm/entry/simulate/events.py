"""
Event candidate helpers for simulate CLI commands and completion.

This module keeps the ``events`` command and REPL completer aligned when they
summarize the current runtime state.  The helpers intentionally remain a thin
presentation layer: final event applicability is still decided by
``SimulationRuntime.cycle()``.
"""

from typing import List, Optional, Tuple

from ...dsl import EXIT_STATE


POST_EXIT_CONTINUATION_LABEL = "post-exit continuation"


def _event_path(event) -> str:
    """Return the dot-separated path for a model event."""
    return getattr(event, "path_name", ".".join(event.state_path) + "." + event.name)


def get_current_event_display_items(runtime) -> List[Tuple[str, Optional[str]]]:
    """
    Return event display rows for the runtime's current state.

    The result preserves the legacy ``(full_path, short_name)`` shape used by
    :class:`pyfcstm.entry.simulate.display.StateDisplay`. Direct leaf events use
    the event's short name as before. Parent-level continuation candidates use
    ``post-exit continuation`` as the display label and keep the full event path
    in the second column.

    :param runtime: Simulation runtime to inspect.
    :type runtime: SimulationRuntime
    :return: Event display rows.
    :rtype: List[Tuple[str, Optional[str]]]
    """
    if runtime.is_ended:
        return []

    try:
        current_state = runtime.current_state
    except IndexError:
        # IndexError: SimulationRuntime.current_state raises when the runtime
        # has no active stack, for example after termination.
        return []

    if not current_state:
        return []

    events: List[Tuple[str, Optional[str]]] = []
    seen_events = set()

    for transition in current_state.transitions_from:
        if not transition.event:
            continue
        event_path = _event_path(transition.event)
        if event_path in seen_events:
            continue
        seen_events.add(event_path)
        short_name = transition.event.name
        events.append((event_path, short_name if short_name != event_path else None))

    if current_state.parent and not current_state.parent.is_root_state:
        has_parent_exit = any(
            transition.to_state == EXIT_STATE
            for transition in current_state.transitions_from
        )
        if has_parent_exit:
            for transition in current_state.parent.transitions_from:
                if not transition.event:
                    continue
                event_path = _event_path(transition.event)
                if event_path in seen_events:
                    continue
                seen_events.add(event_path)
                events.append((event_path, POST_EXIT_CONTINUATION_LABEL))

    return events


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
