"""
Integration tests for simulator runtime contract combinations.

These tests exercise interactions between simulator contracts that are already
covered individually elsewhere. They intentionally use only ``pyfcstm.simulate``
public runtime behavior.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import Event, parse_dsl_node_to_state_machine
from pyfcstm.simulate import (
    CycleResult,
    ReadOnlyExecutionContext,
    SimulationRuntime,
    SimulationRuntimeDfsError,
    SimulationRuntimeEventError,
    SimulationRuntimeTerminalStateError,
    abstract_handler,
)


def _build_runtime(dsl_code, **kwargs):
    """
    Build a simulation runtime from FCSTM source.

    :param dsl_code: FCSTM DSL source code.
    :type dsl_code: str
    :param kwargs: Keyword arguments forwarded to
        :class:`pyfcstm.simulate.SimulationRuntime`.
    :type kwargs: typing.Any
    :return: Runtime constructed from the parsed state-machine model.
    :rtype: pyfcstm.simulate.SimulationRuntime

    Example::

        >>> runtime = _build_runtime("state Root { state A; [*] -> A; }")
        >>> runtime.is_ended
        False
    """
    ast = parse_with_grammar_entry(dsl_code, "state_machine_dsl")
    return SimulationRuntime(parse_dsl_node_to_state_machine(ast), **kwargs)


@pytest.mark.unittest
def test_event_accounting_and_handler_context_remain_consistent_together():
    """Combine event accounting with abstract-handler context metadata."""
    runtime = _build_runtime(
        """
def int ticks = 0;
def float reading = 0.0;
state Root {
    >> during before abstract Audit;

    state Idle {
        enter abstract Init;
        during { ticks = ticks + 1; reading = reading + 1.0; }
        during abstract Monitor;
    }
    state Done { during { ticks = ticks + 100; } }

    [*] -> Idle;
    Idle -> Done :: Go;
}
"""
    )

    calls = []

    def record(ctx: ReadOnlyExecutionContext):
        calls.append(
            {
                "target": ctx.abstract_target,
                "action": ctx.action_name,
                "stage": ctx.action_stage,
                "call_stage": ctx.call_stage,
                "state": ctx.get_full_state_path(),
                "active_leaf": ctx.active_leaf,
                "vars": dict(ctx.vars),
            }
        )

    runtime.register_abstract_handler("Root.Audit", record)
    runtime.register_abstract_handler("Root.Idle.Init", record)
    runtime.register_abstract_handler("Root.Idle.Monitor", record)

    first = runtime.cycle()
    assert first == CycleResult(
        input_events=(), consumed_events=(), unconsumed_events=()
    )
    assert runtime.current_state.path == ("Root", "Idle")
    assert runtime.vars == {"ticks": 1, "reading": 1.0}
    assert type(runtime.vars["reading"]) is float
    assert calls == [
        {
            "target": "Root.Idle.Init",
            "action": "Root.Idle.Init",
            "stage": "enter",
            "call_stage": "enter",
            "state": "Root.Idle",
            "active_leaf": ("Root", "Idle"),
            "vars": {"ticks": 0, "reading": 0.0},
        },
        {
            "target": "Root.Audit",
            "action": "Root.Audit",
            "stage": "during",
            "call_stage": "during",
            "state": "Root.Idle",
            "active_leaf": ("Root", "Idle"),
            "vars": {"ticks": 0, "reading": 0.0},
        },
        {
            "target": "Root.Idle.Monitor",
            "action": "Root.Idle.Monitor",
            "stage": "during",
            "call_stage": "during",
            "state": "Root.Idle",
            "active_leaf": ("Root", "Idle"),
            "vars": {"ticks": 1, "reading": 1.0},
        },
    ]

    second = runtime.cycle(["Root.Idle.Go", "Root.Idle.Go"])
    assert second == CycleResult(
        input_events=("Root.Idle.Go", "Root.Idle.Go"),
        consumed_events=("Root.Idle.Go",),
        unconsumed_events=("Root.Idle.Go",),
    )
    assert runtime.current_state.path == ("Root", "Done")
    assert runtime.vars == {"ticks": 101, "reading": 1.0}
    assert runtime.history[-1]["events"] == ["Root.Idle.Go", "Root.Idle.Go"]


@pytest.mark.unittest
def test_failed_handler_cycle_rolls_back_warning_errors_and_event_result():
    """A raising handler rolls warning metadata back without consuming events."""
    runtime = _build_runtime(
        """
def int x = 0;
state Root {
    state A {
        enter abstract /* anonymous */;
        enter abstract Fail;
        during { x = x + 1; }
    }
    state B { during { x = x + 10; } }

    [*] -> A;
    A -> B :: Go;
}
""",
        abstract_error_mode="raise",
    )

    def fail(_ctx: ReadOnlyExecutionContext):
        raise RuntimeError("boom")

    runtime.register_abstract_handler("Root.A.Fail", fail)

    with pytest.warns(UserWarning, match="has no name"):
        with pytest.raises(RuntimeError, match="boom"):
            runtime.cycle(["Root.A.Go"])

    assert runtime.is_error_state is True
    assert runtime.error_info[0] == "Root.A.Fail"
    assert runtime.vars == {"x": 0}
    assert runtime.abstract_handler_errors == []
    assert len(runtime._warned_anonymous_abstracts) == 0
    assert runtime.cycle(["Root.A.Go"]) == CycleResult()
    assert runtime.vars == {"x": 0}

    removed = runtime.clear_abstract_handler_session()
    assert removed == 1
    assert runtime.abstract_handler_errors == []
    assert len(runtime._warned_anonymous_abstracts) == 0


@pytest.mark.unittest
def test_decorator_registry_copy_and_duplicate_cleanup_share_callable_identity():
    """Object scanner, duplicate cleanup, and session copy use one identity rule."""
    dsl_code = """
def int visits = 0;
state Root {
    state A {
        enter abstract Start;
        during abstract Tick;
        during { visits = visits + 1; }
    }
    [*] -> A;
}
"""
    source = _build_runtime(dsl_code, abstract_error_mode="log", history_size=3)
    target = _build_runtime(dsl_code)

    class Handlers:
        def __init__(self):
            self.calls = []

        @abstract_handler("Root.A.Start")
        @abstract_handler("Root.A.Tick")
        def shared(self, ctx: ReadOnlyExecutionContext):
            self.calls.append((ctx.action_name, ctx.call_stage, ctx.active_leaf))

        @staticmethod
        @abstract_handler("Root.A.Tick")
        def static_tick(ctx: ReadOnlyExecutionContext):
            Handlers.static_calls.append(ctx.action_name)

    Handlers.static_calls = []
    handlers = Handlers()
    assert source.register_handlers_from_object(handlers) == 3
    with pytest.raises(ValueError, match="already registered"):
        source.register_handlers_from_object(handlers)

    with pytest.warns(UserWarning, match="Duplicate abstract handler"):
        source.register_abstract_handler(
            "Root.A.Tick", handlers.shared, allow_duplicates=True
        )
    assert len(source.get_abstract_handlers("Root.A.Tick")) == 3
    assert (
        source.unregister_abstract_handler(
            "Root.A.Tick", handlers.shared, removal_mode="one"
        )
        == 1
    )
    assert len(source.get_abstract_handlers("Root.A.Tick")) == 2

    source.copy_session_configuration_to(target)
    assert target.history_size == 3
    assert target.abstract_error_mode == "log"
    assert len(target.get_abstract_handlers("Root.A.Start")) == 1
    assert len(target.get_abstract_handlers("Root.A.Tick")) == 2

    target.cycle()
    assert handlers.calls == [
        ("Root.A.Start", "enter", ("Root", "A")),
        ("Root.A.Tick", "during", ("Root", "A")),
    ]
    assert Handlers.static_calls == ["Root.A.Tick"]
    assert target.vars == {"visits": 1}


@pytest.mark.unittest
def test_persistent_normalization_rejects_nonfinite_values_across_entry_paths():
    """Persistent vars share finite numeric validation across all entry paths."""
    initializer_runtime = _build_runtime(
        """
def float level = 1.0 / 0.0;
def int counter = 0;
state Root { state A; [*] -> A; }
""",
        initial_vars={"level": 5, "counter": 2.0},
    )
    assert initializer_runtime.vars == {"level": 5.0, "counter": 2}
    assert type(initializer_runtime.vars["level"]) is float
    assert type(initializer_runtime.vars["counter"]) is int

    with pytest.raises(ValueError, match="level.*initializer"):
        _build_runtime(
            """
def float level = 1.0 / 0.0;
def int counter = 0;
state Root { state A; [*] -> A; }
"""
        )

    with pytest.raises(ValueError, match="counter.*finite"):
        _build_runtime(
            """
def int counter = 0;
state Root { state A; [*] -> A; }
""",
            initial_state="Root.A",
            initial_vars={"counter": float("nan")},
        )

    with pytest.raises((ValueError, ArithmeticError), match="evaluation failed"):
        _build_runtime(
            """
def float level = 0.0;
state Root {
    state A { during { level = 1.0 / 0.0; } }
    [*] -> A;
}
"""
        ).cycle()

    with pytest.raises(ValueError, match="level.*finite"):
        _build_runtime(
            """
def float level = 0.0;
state Root {
    state A { during { level = 1.0e309; } }
    [*] -> A;
}
"""
        ).cycle()


@pytest.mark.unittest
def test_hot_start_transient_and_composite_boundaries_keep_declared_order():
    """Hot start handles pseudo leaves and composite initial guards in order."""
    transient_runtime = _build_runtime(
        """
def int x = 0;
state Root {
    pseudo state Gate { during { x = x + 100; } }
    state Ready {
        enter { x = x + 10; }
        during { x = x + 1; }
    }
    [*] -> Gate;
    Gate -> Ready;
}
""",
        initial_state="Root.Gate",
        initial_vars={"x": 0},
    )

    transient_runtime.cycle()
    assert transient_runtime.current_state.path == ("Root", "Ready")
    assert transient_runtime.vars == {"x": 11}

    composite_runtime = _build_runtime(
        """
def int x = 0;
state Root {
    state Parent {
        during before { x = x + 10; }
        state A { enter { x = x + 100; } }
        state B { enter { x = x + 1000; } }
        [*] -> B : if [x >= 10];
        [*] -> A;
    }
    [*] -> Parent;
}
""",
        initial_state="Root.Parent",
        initial_vars={"x": 0},
    )

    composite_runtime.cycle()
    assert composite_runtime.current_state.path == ("Root", "Parent", "A")
    assert composite_runtime.vars == {"x": 100}


@pytest.mark.unittest
def test_invalid_event_and_state_inputs_do_not_modify_runtime_state():
    """Unsupported event and state references are rejected before mutation."""
    runtime = _build_runtime(
        """
def int x = 0;
state Root {
    state A { during { x = x + 1; } }
    state B { during { x = x + 10; } }
    [*] -> A;
    A -> B :: Go;
}
"""
    )
    runtime.cycle()
    assert runtime.current_state.path == ("Root", "A")
    assert runtime.vars == {"x": 1}

    class EventLike:
        path_name = "Root.A.Go"

    with pytest.raises(SimulationRuntimeEventError, match="Unsupported event input"):
        runtime.cycle([EventLike()])
    assert runtime.current_state.path == ("Root", "A")
    assert runtime.vars == {"x": 1}

    with pytest.raises(SimulationRuntimeEventError, match="not owned"):
        runtime.cycle(Event(name="Go", state_path=("Root", "A")))
    assert runtime.current_state.path == ("Root", "A")
    assert runtime.vars == {"x": 1}


@pytest.mark.unittest
def test_diagnostics_for_safety_expression_and_terminal_queries_remain_specific():
    """Safety, expression, and terminal diagnostics use simulator exceptions."""
    with pytest.raises(SimulationRuntimeDfsError, match="step safety limit"):
        _build_runtime(
            """
def int x = 0;
state Root {
    pseudo state Loop { during { x = x + 1; } }
    [*] -> Loop;
    Loop -> Loop;
}
"""
        ).cycle()

    expression_runtime = _build_runtime(
        """
def int x = 0;
state Root {
    state A { during { x = 1.5 << 1; } }
    [*] -> A;
}
"""
    )
    with pytest.raises((ValueError, ArithmeticError), match="evaluation failed"):
        expression_runtime.cycle()
    assert expression_runtime.vars == {"x": 0}

    terminal_runtime = _build_runtime(
        """
state Root {
    state A;
    [*] -> A;
    A -> [*];
}
"""
    )
    terminal_runtime.cycle()
    terminal_runtime.cycle()
    assert terminal_runtime.is_ended is True
    with pytest.raises(SimulationRuntimeTerminalStateError, match="is_ended"):
        terminal_runtime.current_state
