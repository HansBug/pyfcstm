"""Public execution trace ordering, identity, and commit boundaries."""

import json
from dataclasses import FrozenInstanceError

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import (
    CycleResult,
    ExecutionTraceEntry,
    SimulationRuntime,
    SimulationRuntimeEventError,
    SimulationRuntimeExpressionError,
)


pytestmark = pytest.mark.unittest


def _runtime(source, **kwargs):
    return SimulationRuntime(
        parse_dsl_node_to_state_machine(
            parse_with_grammar_entry(source, "state_machine_dsl")
        ),
        **kwargs,
    )


def test_trace_records_lifecycle_effect_order_and_detached_snapshots():
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            enter { x = 1; }
            exit { x = 40; }
            state A { during { x = 10; } exit { x = 20; } }
            state B { enter { x = 30; } }
            [*] -> A;
            A -> B : if [x > 0] effect { x = 25; };
            B -> [*];
        }
    """,
        history_size=0,
    )
    first = runtime.cycle(trace=True)
    second = runtime.cycle(trace=True)
    assert [entry.kind for entry in first.trace] == [
        "state_enter",
        "action",
        "transition",
        "state_enter",
        "action",
    ]
    assert [entry.vars["x"] for entry in first.trace] == [0, 1, 1, 1, 10]
    assert [(entry.kind, entry.vars["x"]) for entry in second.trace] == [
        ("action", 20),
        ("state_exit", 20),
        ("transition", 25),
        ("state_enter", 25),
        ("action", 30),
    ]
    assert second.trace[2].transition_label == "Root.A::0::A->B"
    assert second.trace[3].state_path == ("Root", "B")
    with pytest.raises(TypeError):
        second.trace[0].vars["x"] = 999
    payload = second.trace[0].to_dict()
    payload["vars"]["x"] = 999
    payload["state_path"].append("Elsewhere")
    assert second.trace[0].vars == {"x": 20}
    assert second.trace[0].state_path == ("Root", "A")
    assert json.loads(json.dumps([e.to_dict() for e in first.trace]))[0]["vars"] == {
        "x": 0
    }
    ended = runtime.cycle(trace=True)
    assert runtime.is_ended
    assert [(e.kind, e.state_path, e.vars["x"]) for e in ended.trace] == [
        ("state_exit", ("Root", "B"), 30),
        ("transition", ("Root", "B"), 30),
        ("action", ("Root",), 40),
        ("state_exit", ("Root",), 40),
    ]
    assert runtime.cycle(trace=True) == CycleResult()
    assert runtime.history == []


def test_trace_is_opt_in_and_does_not_change_history_or_event_accounting():
    source = """
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
    """
    plain, traced = _runtime(source), _runtime(source)
    for events in (None, ["Root.A.Go", "Root.A.Go"]):
        ordinary = plain.cycle(events)
        observed = traced.cycle(events, trace=True)
        assert ordinary.trace == ()
        assert observed.trace
        assert observed.input_events == ordinary.input_events
        assert observed.consumed_events == ordinary.consumed_events
        assert observed.unconsumed_events == ordinary.unconsumed_events
        assert traced.history == plain.history
        assert traced.brief_stack == plain.brief_stack
        assert traced.vars == plain.vars
    assert traced.cycle().trace == ()


def test_trace_excludes_rejected_higher_priority_transition_and_its_actions():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            state A;
            state Blocked {
                enter { x = 100; }
                state Inner;
                [*] -> Inner : if [x < 0];
            }
            state B { enter { x = 1; } }
            [*] -> A;
            A -> Blocked :: Go;
            A -> B :: Go;
        }
    """)
    runtime.cycle()
    result = runtime.cycle("Root.A.Go", trace=True)
    assert [e.transition_label for e in result.trace if e.kind == "transition"] == [
        "Root.A::1::A->B",
    ]
    assert all("Blocked" not in e.state_path for e in result.trace)
    assert [e.vars["x"] for e in result.trace] == [0, 0, 0, 1]
    assert result.consumed_events == ("Root.A.Go",)


def test_delta_and_invalid_events_do_not_leak_speculative_entries():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            enter { x = x + 1; }
            state A;
            [*] -> A :: Start;
        }
    """)
    delta = runtime.cycle(trace=True)
    assert delta.delta and delta.trace == ()
    assert runtime.vars == {"x": 0}
    with pytest.raises(SimulationRuntimeEventError):
        runtime.cycle("Root.Unknown", trace=True)
    result = runtime.cycle("Root.Start", trace=True)
    assert [e.kind for e in result.trace] == [
        "state_enter",
        "action",
        "transition",
        "state_enter",
    ]
    assert runtime.vars == {"x": 1}


def test_expression_error_leaves_previous_trace_valid_and_next_trace_clean():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } }
            state B { enter { x = 1 / 0; } }
            [*] -> A;
            A -> B :: Go;
        }
    """)
    first = runtime.cycle(trace=True)
    with pytest.raises(SimulationRuntimeExpressionError):
        runtime.cycle("Root.A.Go", trace=True)
    assert runtime.cycle_count == 1
    next_result = runtime.cycle(trace=True)
    assert len(next_result.trace) == 1
    assert next_result.trace[0].vars == {"x": 2}
    assert first.trace[-1].vars == {"x": 1}


def test_ref_and_aspect_trace_identifies_callsite_and_execution_location():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            >> during before { x = x + 1; }
            >> during after { x = x + 100; }
            state A {
                during Add { x = x + 10; }
                during ref Add;
                during { x = x + 1000; }
            }
            [*] -> A;
        }
    """)
    result = runtime.cycle(trace=True)
    actions = [e for e in result.trace if e.kind == "action"]
    assert [e.action_path for e in actions] == [
        "Root::on_during_aspects::0",
        "Root.A::on_durings::0",
        "Root.A::on_durings::1",
        "Root.A::on_durings::2",
        "Root::on_during_aspects::1",
    ]
    assert all(e.state_path == ("Root", "A") for e in actions)
    assert actions[2].resolved_action_path == "Root.A::on_durings::0"
    assert [e.vars["x"] for e in actions] == [1, 11, 21, 1021, 1121]


@pytest.mark.parametrize("mode", ["raise", "log"])
def test_abstract_handler_errors_preserve_trace_commit_boundary(mode):
    runtime = _runtime(
        """
        state Root {
            state A { enter abstract Notify; }
            [*] -> A;
        }
    """,
        abstract_error_mode=mode,
    )
    calls = []

    def fail(context):
        calls.append(context)
        raise ValueError("handler failed")

    runtime.register_abstract_handler("Root.A.Notify", fail)
    if mode == "raise":
        with pytest.raises(ValueError, match="handler failed"):
            runtime.cycle(trace=True)
        assert runtime.cycle_count == 0
        assert runtime.history == []
        assert runtime.cycle(trace=True).trace == ()
    else:
        result = runtime.cycle(trace=True)
        assert result.trace[-1].action_path == "Root.A::on_enters::0"
        assert len(runtime.abstract_handler_errors) == 1
    assert len(calls) == 1


def test_hot_start_has_no_fabricated_entry_and_root_exit_is_addressable():
    runtime = _runtime(
        """
        def int x = 0;
        state Root { enter { x = 100; } exit { x = x + 1; } }
    """,
        initial_state="Root",
        initial_vars={"x": 5},
    )
    result = runtime.cycle(trace=True)
    assert runtime.is_ended
    assert [e.kind for e in result.trace] == ["action", "state_exit", "transition"]
    assert result.trace[-1].transition_label == "Root::0::Root->[*]"
    assert runtime.vars == {"x": 6}


def test_pseudo_chain_records_every_committed_iteration_once():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            pseudo state P { during { x = x + 1; } }
            state A;
            [*] -> P;
            P -> A : if [x >= 2];
            P -> P;
        }
    """)
    result = runtime.cycle(trace=True)
    assert [e.vars["x"] for e in result.trace if e.kind == "action"] == [1, 2]
    assert [e.transition_label for e in result.trace if e.kind == "transition"] == [
        "Root::0::INIT_STATE->P",
        "Root.P::1::P->P",
        "Root.P::0::P->A",
    ]


def test_composite_entry_and_child_exit_preserve_boundary_action_order():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            state Group {
                during before { x = x * 10 + 1; }
                during after { x = x * 10 + 5; }
                exit { x = x * 10 + 6; }
                state A {
                    enter { x = x * 10 + 2; }
                    during { x = x * 10 + 3; }
                    exit { x = x * 10 + 4; }
                }
                [*] -> A;
                A -> [*] :: Go;
            }
            state Done { enter { x = x * 10 + 7; } }
            [*] -> Group;
            Group -> Done;
        }
    """)
    entered = runtime.cycle(trace=True)
    assert [e.vars["x"] for e in entered.trace if e.kind == "action"] == [1, 12, 123]
    exited = runtime.cycle("Root.Group.A.Go", trace=True)
    assert [e.vars["x"] for e in exited.trace if e.kind == "action"] == [
        1234,
        12345,
        123456,
        1234567,
    ]
    assert [e.state_path for e in exited.trace if e.kind == "state_exit"] == [
        ("Root", "Group", "A"),
        ("Root", "Group"),
    ]
    assert [e.transition_label for e in exited.trace if e.kind == "transition"] == [
        "Root.Group.A::0::A->[*]",
        "Root.Group::0::Group->Done",
    ]


def test_abstract_dispatch_without_handlers_is_still_an_observed_action():
    runtime = _runtime("""
        state Root {
            state A { enter abstract Notify; during abstract /* Observe */; }
            [*] -> A;
        }
    """)
    with pytest.warns(UserWarning, match="has no name"):
        result = runtime.cycle(trace=True)
    assert [e.action_path for e in result.trace if e.kind == "action"] == [
        "Root.A::on_enters::0",
        "Root.A::on_durings::0",
    ]
    assert runtime.abstract_handler_errors == []


@pytest.mark.parametrize("initial", [False, True], ids=["outgoing", "initial"])
@pytest.mark.parametrize("choice", [0, 1, 2])
def test_parallel_edges_to_the_same_target_keep_their_source_local_index(
    initial, choice
):
    source = "[*]" if initial else "A"
    edges = "\n".join(
        "%s -> B : if [choice == %d] effect { x = %d; };" % (source, i, i + 10)
        for i in range(3)
    )
    runtime = _runtime(
        """
        def int choice = %d;
        def int x = 0;
        state Root { state A; state B; %s %s }
        """
        % (choice, "" if initial else "[*] -> A;", edges)
    )
    if not initial:
        runtime.cycle()
    result = runtime.cycle(trace=True)
    transitions = [entry for entry in result.trace if entry.kind == "transition"]
    assert len(transitions) == 1
    assert (
        transitions[0].transition_label
        == ("Root::%d::INIT_STATE->B" if initial else "Root.A::%d::A->B") % choice
    )
    assert transitions[0].vars["x"] == choice + 10


def test_self_transition_records_exit_effect_reentry_and_during_snapshots():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            state A {
                enter { x = x * 10 + 1; }
                during { x = x * 10 + 2; }
                exit { x = x * 10 + 3; }
            }
            [*] -> A;
            A -> A :: Again effect { x = x * 10 + 4; };
        }
    """)
    runtime.cycle()
    result = runtime.cycle("Root.A.Again", trace=True)
    assert [(e.kind, e.vars["x"]) for e in result.trace] == [
        ("action", 123),
        ("state_exit", 123),
        ("transition", 1234),
        ("state_enter", 1234),
        ("action", 12341),
        ("action", 123412),
    ]
    assert result.trace[2].transition_label == "Root.A::0::A->A"


def test_initial_candidate_rejection_discards_effects_and_abstract_dispatches():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            enter { x = 1; }
            state Bad {
                enter abstract Notify;
                enter { x = 99; }
                state Dead;
                [*] -> Dead : if [false];
            }
            state Good { enter { x = x + 1; } }
            [*] -> Bad effect { x = 100; };
            [*] -> Good effect { x = 10; };
        }
    """)
    calls = []
    runtime.register_abstract_handler("Root.Bad.Notify", calls.append)
    result = runtime.cycle(trace=True)
    assert calls == []
    assert [(e.kind, e.vars["x"]) for e in result.trace] == [
        ("state_enter", 0),
        ("action", 1),
        ("transition", 10),
        ("state_enter", 10),
        ("action", 11),
    ]
    assert result.trace[2].transition_label == "Root::1::INIT_STATE->Good"
    assert all("Bad" not in e.state_path for e in result.trace)


def test_forced_pseudo_transition_records_only_the_stable_expanded_edge():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            pseudo state P { enter { x = 1; } exit { x = 2; } }
            state Bad {
                enter { x = 100; }
                state Dead;
                [*] -> Dead : if [false];
            }
            state Good { enter { x = x + 10; } }
            [*] -> P;
            !P -> Bad;
            !P -> Good;
        }
    """)
    result = runtime.cycle(trace=True)
    assert [e.transition_label for e in result.trace if e.kind == "transition"] == [
        "Root::0::INIT_STATE->P",
        "Root.P::1::P->Good",
    ]
    assert [e.vars["x"] for e in result.trace if e.kind == "action"] == [1, 2, 12]
    assert all("Bad" not in e.state_path for e in result.trace)


@pytest.mark.parametrize(
    "events, enabled, target, consumed",
    [
        (["Root.A.First", "Root.A.Second"], 1, "B", ("Root.A.First", "Root.A.Second")),
        (["Root.A.First"], 1, "Fallback", ("Root.A.First",)),
        (["Root.A.First", "Root.A.Second"], 0, "Fallback", ("Root.A.First",)),
    ],
    ids=["complete", "missing-second-event", "false-middle-guard"],
)
def test_combo_trace_records_committed_relays_or_only_the_fallback(
    events, enabled, target, consumed
):
    runtime = _runtime(
        """
        def int enabled = 0;
        def int x = 0;
        state Root {
            state A { exit { x = 1; } }
            state B { enter { x = x + 10; } }
            state Fallback { enter { x = x + 100; } }
            [*] -> A;
            A -> B :: First + [enabled > 0] + Second effect { x = 2; };
            A -> Fallback :: First effect { x = 3; };
        }
    """,
        initial_vars={"enabled": enabled},
    )
    runtime.cycle()
    result = runtime.cycle(events, trace=True)
    entered = [e.state_path[-1] for e in result.trace if e.kind == "state_enter"]
    transitions = [e for e in result.trace if e.kind == "transition"]
    assert result.consumed_events == consumed
    assert entered[-1] == target
    if target == "B":
        assert len(transitions) == 3
        assert len(entered) == 3
        assert all(
            runtime.state_machine.root_state.substates[name].is_pseudo
            for name in entered[:-1]
        )
        assert [e.vars["x"] for e in transitions] == [1, 1, 2]
        assert result.trace[-1].vars["x"] == 12
    else:
        assert entered == ["Fallback"]
        assert len(transitions) == 1
        assert transitions[0].transition_label == "Root.A::1::A->Fallback"
        assert transitions[0].vars["x"] == 3
        assert result.trace[-1].vars["x"] == 103


def test_temporary_variables_and_conditional_writes_stay_inside_action_blocks():
    runtime = _runtime("""
        def int x = 0;
        def float y = 0.5;
        state Root {
            state A {
                during {
                    tmp = x + 2;
                    if [tmp > 0] { x = tmp; } else { x = 99; }
                }
                exit { tmp = x + 3; x = tmp; }
            }
            state B { enter { tmp = x + 7; x = tmp; } }
            [*] -> A;
            A -> B :: Go effect { tmp = x + 5; x = tmp; y = y + 0.25; };
        }
    """)
    first = runtime.cycle(trace=True)
    second = runtime.cycle("Root.A.Go", trace=True)
    assert first.trace[-1].vars == {"x": 2, "y": 0.5}
    assert [e.vars["x"] for e in second.trace] == [5, 5, 10, 10, 17]
    assert second.trace[2].vars["y"] == 0.75
    assert all(set(e.vars) == {"x", "y"} for e in first.trace + second.trace)


@pytest.mark.parametrize("stage", ["enter", "during", "exit"])
def test_cross_state_reference_chain_keeps_callsite_and_final_target(stage):
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            state Library {
                enter Last { x = x + 1; }
                during Middle ref Last;
                exit First ref Middle;
            }
            state A { %s Call ref /Library.First; }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
    """
        % stage
    )
    result = runtime.cycle(trace=True)
    if stage == "exit":
        result = runtime.cycle("Root.A.Go", trace=True)
    actions = [e for e in result.trace if e.kind == "action"]
    assert len(actions) == 1
    assert actions[0].state_path == ("Root", "A")
    collection = {"enter": "on_enters", "during": "on_durings", "exit": "on_exits"}[
        stage
    ]
    assert actions[0].action_path == "Root.A::%s::0" % collection
    assert actions[0].resolved_action_path == "Root.Library::on_enters::0"
    assert actions[0].vars == {"x": 1}
    assert not any(e.state_path == ("Root", "Library") for e in result.trace)


@pytest.mark.parametrize("boundary", ["exit", "effect", "enter", "during"])
def test_expression_failure_at_each_transition_boundary_leaves_no_trace_residue(
    boundary,
):
    failing = "x = 1 / 0;"
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } exit { %s } }
            state B { enter { %s } during { %s } }
            [*] -> A;
            A -> B :: Go effect { %s };
        }
    """
        % tuple(
            failing if boundary == slot else "x = x + 10;"
            for slot in ("exit", "enter", "during", "effect")
        )
    )
    previous = runtime.cycle(trace=True)
    with pytest.raises(SimulationRuntimeExpressionError):
        runtime.cycle("Root.A.Go", trace=True)
    assert runtime.cycle_count == 1
    assert runtime.vars == {"x": 1}
    recovered = runtime.cycle(trace=True)
    assert [(e.kind, e.vars["x"]) for e in recovered.trace] == [("action", 2)]
    assert previous.trace[-1].vars == {"x": 1}


@pytest.mark.parametrize("stage", ["enter", "during", "exit"])
@pytest.mark.parametrize("interrupt", [KeyboardInterrupt, SystemExit])
def test_interrupted_abstract_dispatch_can_retry_with_a_clean_trace(stage, interrupt):
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            state A {
                enter { x = x + 1; }
                %s abstract Notify;
                during { x = x + 10; }
            }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
    """
        % stage
    )
    calls = []

    def interrupt_once(context):
        calls.append(context)
        if len(calls) == 1:
            raise interrupt("interrupted dispatch")

    runtime.register_abstract_handler("Root.A.Notify", interrupt_once)
    events = None
    if stage == "exit":
        runtime.cycle()
        events = "Root.A.Go"
    previous_vars = dict(runtime.vars)
    previous_count = runtime.cycle_count
    with pytest.raises(interrupt, match="interrupted dispatch"):
        runtime.cycle(events, trace=True)
    assert runtime.cycle_count == previous_count
    assert runtime.vars == previous_vars
    recovered = runtime.cycle(events, trace=True)
    collection = {"enter": "on_enters", "during": "on_durings", "exit": "on_exits"}[
        stage
    ]
    action_index = 1 if stage == "enter" else 0
    assert (
        sum(
            e.action_path == "Root.A::%s::%d" % (collection, action_index)
            for e in recovered.trace
        )
        == 1
    )
    assert len(calls) == 2
    assert recovered.trace
    assert runtime.abstract_handler_errors == []


def test_direct_trace_entry_freezes_caller_data_and_serializes_all_fields():
    path = ["Root", "A"]
    variables = {"wide": 2**100, "fraction": -0.25}
    entry = ExecutionTraceEntry("state_enter", path, variables)
    path.append("B")
    variables["wide"] = 0
    with pytest.raises(FrozenInstanceError):
        entry.kind = "state_exit"
    assert json.loads(json.dumps(entry.to_dict())) == {
        "kind": "state_enter",
        "state_path": ["Root", "A"],
        "vars": {"wide": 2**100, "fraction": -0.25},
        "transition_label": None,
        "action_path": None,
        "resolved_action_path": None,
    }


@pytest.mark.parametrize("history_size", [0, 1, None])
def test_trace_switch_is_per_call_and_independent_of_history_retention(history_size):
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } }
            [*] -> A;
        }
    """,
        history_size=history_size,
    )
    results = [
        runtime.cycle(trace=enabled) for enabled in (True, False, True, False, True)
    ]
    assert [bool(result.trace) for result in results] == [
        True,
        False,
        True,
        False,
        True,
    ]
    assert [result.trace[-1].vars["x"] for result in results if result.trace] == [
        1,
        3,
        5,
    ]
    assert len(runtime.history) == (5 if history_size is None else history_size)
    assert all(
        set(item) == {"cycle", "state", "vars", "events", "delta"}
        for item in runtime.history
    )


@pytest.mark.parametrize("iterations", [1, 4, 25])
def test_repeated_pseudo_self_edges_keep_all_occurrences(iterations):
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            pseudo state P { during { x = x + 1; } }
            state Done;
            [*] -> P;
            P -> Done : if [x >= %d];
            P -> P;
        }
    """
        % iterations
    )
    result = runtime.cycle(trace=True)
    assert [e.transition_label for e in result.trace if e.kind == "transition"] == (
        ["Root::0::INIT_STATE->P"]
        + ["Root.P::1::P->P"] * (iterations - 1)
        + ["Root.P::0::P->Done"]
    )
    assert [e.vars["x"] for e in result.trace if e.kind == "action"] == list(
        range(1, iterations + 1)
    )
    assert len([e for e in result.trace if e.kind == "state_exit"]) == iterations


def test_nested_aspects_distinguish_multiple_actions_in_the_same_collection():
    runtime = _runtime("""
        def int x = 0;
        state Root {
            >> during before { x = x * 10 + 1; }
            >> during after { x = x * 10 + 8; }
            state Group {
                >> during before { x = x * 10 + 2; }
                >> during before { x = x * 10 + 3; }
                >> during after { x = x * 10 + 6; }
                >> during after { x = x * 10 + 7; }
                state A {
                    during { x = x * 10 + 4; }
                    during { x = x * 10 + 5; }
                }
                [*] -> A;
            }
            [*] -> Group;
        }
    """)
    result = runtime.cycle(trace=True)
    actions = [e for e in result.trace if e.kind == "action"]
    assert [e.action_path for e in actions] == [
        "Root::on_during_aspects::0",
        "Root.Group::on_during_aspects::0",
        "Root.Group::on_during_aspects::1",
        "Root.Group.A::on_durings::0",
        "Root.Group.A::on_durings::1",
        "Root.Group::on_during_aspects::2",
        "Root.Group::on_during_aspects::3",
        "Root::on_during_aspects::1",
    ]
    assert [e.vars["x"] for e in actions] == [
        1,
        12,
        123,
        1234,
        12345,
        123456,
        1234567,
        12345678,
    ]
    assert all(e.state_path == ("Root", "Group", "A") for e in actions)


@pytest.mark.parametrize("stage", ["enter", "during", "exit"])
@pytest.mark.parametrize("mode", ["raise", "log"])
def test_multiple_handlers_record_one_dispatch_and_observable_failure(stage, mode):
    runtime = _runtime(
        """
        state Root {
            state A { %s abstract Notify; }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
    """
        % stage,
        abstract_error_mode=mode,
    )
    calls = []

    def first(context):
        calls.append(("first", context.action_stage))

    def fail(context):
        calls.append(("fail", context.action_stage))
        raise ValueError("second handler failed")

    def last(context):
        calls.append(("last", context.action_stage))

    for handler in (first, fail, last):
        runtime.register_abstract_handler("Root.A.Notify", handler)
    events = None
    if stage == "exit":
        runtime.cycle()
        events = "Root.A.Go"
    if mode == "raise":
        count = runtime.cycle_count
        with pytest.raises(ValueError, match="second handler failed"):
            runtime.cycle(events, trace=True)
        assert calls == [("first", stage), ("fail", stage)]
        assert runtime.cycle_count == count
        assert runtime.cycle(trace=True) == CycleResult()
    else:
        result = runtime.cycle(events, trace=True)
        assert calls == [("first", stage), ("fail", stage), ("last", stage)]
        assert len([e for e in result.trace if e.kind == "action"]) == 1
        assert len(runtime.abstract_handler_errors) == 1
        name, error = runtime.abstract_handler_errors[0]
        assert name == "Root.A.Notify"
        assert str(error) == "second handler failed"


def test_handler_can_trace_an_independent_runtime_without_mixing_entries():
    inner = _runtime("""
        def int y = 0;
        state Inner { state Idle { during { y = y + 1; } } [*] -> Idle; }
    """)
    outer = _runtime("""
        def int x = 0;
        state Outer {
            state Active { during abstract Tick; during { x = x + 1; } }
            [*] -> Active;
        }
    """)
    inner_results = []
    outer.register_abstract_handler(
        "Outer.Active.Tick",
        lambda context: inner_results.append(inner.cycle(trace=True)),
    )
    first = outer.cycle(trace=True)
    second = outer.cycle(trace=True)
    assert inner.vars == {"y": 2}
    assert outer.vars == {"x": 2}
    assert all(
        e.state_path[0] == "Outer" and set(e.vars) == {"x"}
        for e in first.trace + second.trace
    )
    assert all(
        e.state_path[0] == "Inner" and set(e.vars) == {"y"}
        for result in inner_results
        for e in result.trace
    )
    assert first.trace[-1].vars == {"x": 1}
    assert inner_results[0].trace[-1].vars == {"y": 1}


def test_idle_cycle_can_have_an_empty_trace_without_being_delta():
    runtime = _runtime("state Root { state Idle; [*] -> Idle; }")
    assert runtime.cycle(trace=True).trace
    for _ in range(3):
        result = runtime.cycle(trace=True)
        assert result.trace == ()
        assert not result.delta
        assert not runtime.is_ended
    assert runtime.cycle_count == 4
