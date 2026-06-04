"""
Unit tests for ``SimulationRuntime.cycle`` event input normalization.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


def _build_runtime() -> SimulationRuntime:
    """Build a minimal runtime with one evented transition."""
    ast = parse_with_grammar_entry(
        """
def int x = 0;
state Root {
    state A { during { x = x + 1; } }
    state B { during { x = x + 10; } }
    [*] -> A;
    A -> B :: Go;
}
""",
        'state_machine_dsl',
    )
    return SimulationRuntime(parse_dsl_node_to_state_machine(ast))


@pytest.mark.unittest
def test_cycle_accepts_single_model_event_object():
    """Model event objects can be passed directly as one event input."""
    runtime = _build_runtime()
    runtime.cycle()

    event = runtime.state_machine.resolve_event('Root.A.Go')
    runtime.cycle(event)

    assert runtime.current_state.path == ('Root', 'B')
    assert runtime.vars['x'] == 11


@pytest.mark.unittest
def test_cycle_rejects_event_like_item_with_non_string_path_name():
    """Event-like collection items must expose a string ``path_name``."""
    runtime = _build_runtime()
    runtime.cycle()

    class BadEvent:
        path_name = 12

    with pytest.raises(TypeError, match='path_name must be str'):
        runtime.cycle([BadEvent()])


@pytest.mark.unittest
def test_cycle_rejects_unsupported_event_item_type():
    """Unsupported collection item types fail before execution."""
    runtime = _build_runtime()
    runtime.cycle()

    with pytest.raises(TypeError, match='Unknown event type'):
        runtime.cycle([7])


@pytest.mark.unittest
def test_cycle_rejects_non_iterable_event_container():
    """Unsupported non-iterable event containers fail before execution."""
    runtime = _build_runtime()
    runtime.cycle()

    with pytest.raises(TypeError, match='Unknown event type'):
        runtime.cycle(7)
