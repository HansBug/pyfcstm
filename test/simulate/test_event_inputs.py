"""
Unit tests for ``SimulationRuntime.cycle`` event input normalization.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import Event, parse_dsl_node_to_state_machine
from pyfcstm.simulate import CycleResult, SimulationRuntime, SimulationRuntimeEventError


class IterableEventLike:
    """Synthetic event-like object that also implements the iterable protocol."""

    path_name = "Root.A.Go"

    def __iter__(self):
        yield self.path_name


class DynamicIterableEventLike:
    """Synthetic event-like object with dynamic path-name lookup."""

    def __getattr__(self, name):
        if name == "path_name":
            return "Root.A.Go"
        raise AttributeError(name)

    def __iter__(self):
        yield self.path_name


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
        "state_machine_dsl",
    )
    return SimulationRuntime(parse_dsl_node_to_state_machine(ast))


@pytest.mark.unittest
def test_cycle_accepts_single_model_event_object():
    """Model event objects can be passed directly as one event input."""
    runtime = _build_runtime()
    runtime.cycle()

    event = runtime.state_machine.resolve_event("Root.A.Go")
    result = runtime.cycle(event)

    assert result == CycleResult(
        input_events=("Root.A.Go",),
        consumed_events=("Root.A.Go",),
        unconsumed_events=(),
    )
    assert runtime.current_state.path == ("Root", "B")
    assert runtime.vars["x"] == 11


@pytest.mark.unittest
def test_cycle_reports_unconsumed_duplicate_events_in_input_order():
    """Cycle results expose consumed and remaining input event paths."""
    runtime = _build_runtime()
    runtime.cycle()

    result = runtime.cycle(["Root.A.Go", "Root.A.Go"])

    assert result.value is None
    assert result.input_events == ("Root.A.Go", "Root.A.Go")
    assert result.consumed_events == ("Root.A.Go",)
    assert result.unconsumed_events == ("Root.A.Go",)
    assert runtime.current_state.path == ("Root", "B")


@pytest.mark.unittest
def test_cycle_return_metadata_covers_stable_and_ended_cycles():
    """Cycle result metadata remains simulator-only ordinary pytest coverage."""
    runtime = _build_runtime()

    first = runtime.cycle()

    assert first == CycleResult(
        input_events=(), consumed_events=(), unconsumed_events=()
    )
    assert runtime.current_state.path == ("Root", "A")
    assert runtime.vars["x"] == 1

    runtime.cycle("Root.A.Go")
    assert runtime.current_state.path == ("Root", "B")

    ast = parse_with_grammar_entry(
        """
state Root {
    state A;
    [*] -> A;
    A -> [*] :: Stop;
}
""",
        "state_machine_dsl",
    )
    ended_runtime = SimulationRuntime(parse_dsl_node_to_state_machine(ast))
    ended_runtime.cycle()

    ended = ended_runtime.cycle(["Root.A.Stop"])

    assert ended == CycleResult(
        input_events=("Root.A.Stop",),
        consumed_events=("Root.A.Stop",),
        unconsumed_events=(),
    )
    assert ended_runtime.is_ended is True

    ignored = ended_runtime.cycle("Root.A.Stop")

    assert ignored == CycleResult()
    assert ended_runtime.is_ended is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("events_factory", "expected_input_events"),
    [
        (tuple, ("Root.A.Go",)),
        (set, ("Root.A.Go",)),
        (lambda items: (item for item in items), ("Root.A.Go",)),
    ],
    ids=["tuple", "set", "generator"],
)
def test_cycle_accepts_supported_event_iterable_containers(
    events_factory, expected_input_events
):
    """Supported iterable containers use the same item parsing contract."""
    runtime = _build_runtime()
    runtime.cycle()

    result = runtime.cycle(events_factory(["Root.A.Go"]))

    assert result.input_events == expected_input_events
    assert result.consumed_events == ("Root.A.Go",)
    assert result.unconsumed_events == ()
    assert runtime.current_state.path == ("Root", "B")


@pytest.mark.unittest
def test_cycle_rejects_bare_event_like_object():
    """Event-like objects are rejected as unsupported public inputs."""
    runtime = _build_runtime()
    runtime.cycle()

    class EventLike:
        path_name = "Root.A.Go"

    with pytest.raises(SimulationRuntimeEventError, match="Unsupported event input"):
        runtime.cycle(EventLike())

    assert runtime.current_state.path == ("Root", "A")
    assert runtime.vars["x"] == 1


@pytest.mark.unittest
@pytest.mark.parametrize(
    "event_like_cls",
    [
        pytest.param(IterableEventLike, id="class-attribute"),
        pytest.param(DynamicIterableEventLike, id="dynamic-attribute"),
    ],
)
def test_cycle_rejects_iterable_bare_event_like_object(event_like_cls):
    """Event-like bare values cannot masquerade as event containers."""
    runtime = _build_runtime()
    runtime.cycle()

    with pytest.raises(SimulationRuntimeEventError, match="Unsupported event input"):
        runtime.cycle(event_like_cls())

    assert runtime.current_state.path == ("Root", "A")
    assert runtime.vars["x"] == 1


@pytest.mark.unittest
def test_cycle_rejects_event_like_collection_item():
    """Container items use the same event input boundary as bare values."""
    runtime = _build_runtime()
    runtime.cycle()

    class EventLike:
        path_name = "Root.A.Go"

    with pytest.raises(SimulationRuntimeEventError, match="Unsupported event input"):
        runtime.cycle([EventLike()])

    assert runtime.current_state.path == ("Root", "A")
    assert runtime.vars["x"] == 1


@pytest.mark.unittest
def test_cycle_rejects_unsupported_event_item_type():
    """Unsupported collection item types fail before execution."""
    runtime = _build_runtime()
    runtime.cycle()

    with pytest.raises(SimulationRuntimeEventError, match="Unsupported event input"):
        runtime.cycle([7])


@pytest.mark.unittest
def test_cycle_rejects_non_iterable_event_container():
    """Unsupported non-iterable event containers fail before execution."""
    runtime = _build_runtime()
    runtime.cycle()

    with pytest.raises(SimulationRuntimeEventError, match="Unsupported event input"):
        runtime.cycle(7)


@pytest.mark.unittest
def test_cycle_rejects_unknown_event_path_and_preserves_public_snapshot():
    """Unknown event paths surface as simulator event errors without rollback drift."""
    ast = parse_with_grammar_entry(
        """
state Root {
    state A;
    [*] -> A;
}
""",
        "state_machine_dsl",
    )
    runtime = SimulationRuntime(parse_dsl_node_to_state_machine(ast))

    with pytest.raises(
        SimulationRuntimeEventError, match="Cannot resolve event path 'Missing'"
    ):
        runtime.cycle(["Missing"])

    assert runtime.current_state.path == ("Root",)
    assert runtime.vars == {}
    assert runtime.is_ended is False


@pytest.mark.unittest
def test_cycle_rejects_foreign_model_event_object():
    """Event objects must belong to the runtime's own state machine."""
    runtime = _build_runtime()
    runtime.cycle()

    foreign_event = Event(name="Go", state_path=("Root", "A"))

    with pytest.raises(SimulationRuntimeEventError, match="not owned"):
        runtime.cycle(foreign_event)

    with pytest.raises(SimulationRuntimeEventError, match="not owned"):
        runtime.cycle([foreign_event])
