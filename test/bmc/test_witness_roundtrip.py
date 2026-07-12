"""Adversarial BMC witness to SimulationRuntime roundtrip tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import pytest
import z3

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
from pyfcstm.bmc.witness import decode_bmc_witness, replay_bmc_witness
from pyfcstm.model import load_state_machine_from_text


pytestmark = pytest.mark.unittest


TraceCheck = Callable[[object, object], None]
ExtraConstraints = Callable[[object], Tuple[z3.BoolRef, ...]]


@dataclass(frozen=True)
class RoundtripCase:
    """One hand-authored SAT witness roundtrip scenario."""

    name: str
    dsl: str
    query: str
    check: Optional[TraceCheck] = None
    extra_constraints: Optional[ExtraConstraints] = None


def _selected_events(trace, step_index: int) -> Tuple[str, ...]:
    return tuple(event.path for event in trace.steps[step_index].input_events)


def _final_state(trace) -> Optional[str]:
    return trace.frames[-1].state


def _final_vars(trace):
    return dict(trace.frames[-1].vars)


def _roundtrip(case: RoundtripCase):
    model = load_state_machine_from_text(case.dsl)
    formula = compile_bmc_property(
        build_bmc_core_formula(BmcEngine(model).prepare(case.query))
    )
    solver = z3.Solver()
    solver.add(formula.solve_formula)
    if case.extra_constraints is not None:
        solver.add(*case.extra_constraints(formula))
    assert solver.check() == z3.sat, case.name
    trace = decode_bmc_witness(formula, solver.model())
    replay = replay_bmc_witness(model, trace)
    assert replay.ok, [item.to_canonical() for item in replay.mismatches]
    if case.check is not None:
        case.check(trace, replay)
    return trace, replay


def _assert_final(state: str, **vars_):
    def check(trace, replay) -> None:
        assert _final_state(trace) == state
        for name, value in vars_.items():
            assert _final_vars(trace)[name] == value
        assert replay.runtime_trace.frames[-1].state == state

    return check


def _assert_progress(step_index: int, progress: str):
    def check(trace, replay) -> None:
        assert trace.steps[step_index].progress == progress

    return check


def _and(*checks: TraceCheck) -> TraceCheck:
    def check(trace, replay) -> None:
        for item in checks:
            item(trace, replay)

    return check


def _assert_events(step_index: int, *events: str) -> TraceCheck:
    def check(trace, replay) -> None:
        assert _selected_events(trace, step_index) == events
        assert replay.runtime_trace.steps[step_index].input_events == events

    return check


def _assert_call_count(step_index: int, count: int) -> TraceCheck:
    def check(trace, replay) -> None:
        assert len(trace.steps[step_index].abstract_calls) == count
        assert len(replay.runtime_trace.steps[step_index].abstract_calls) == count

    return check


ROUNDTRIP_CASES = [
    RoundtripCase(
        "cold-init-stable-leaf",
        """
        state Root {
            state A;
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A");',
        _and(_assert_final("Root.A"), _assert_progress(0, "initial")),
    ),
    RoundtripCase(
        "hot-leaf-during-fallback",
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } }
            [*] -> A;
        }
        """,
        'init state("Root.A") havoc * where x == 5;\n'
        'check reach <= 1: active("Root.A") && x == 6;',
        _and(_assert_final("Root.A", x=6), _assert_progress(0, "fallback_gamma")),
    ),
    RoundtripCase(
        "hot-composite-evented-initial",
        """
        state Root {
            state Parent {
                state A;
                [*] -> A :: unlock;
            }
            [*] -> Parent;
        }
        """,
        'init state("Root.Parent");\n'
        'assume event("Root.Parent.unlock", 0) == true;\n'
        'check reach <= 1: active("Root.Parent.A");',
        _and(_assert_final("Root.Parent.A"), _assert_events(0, "Root.Parent.unlock")),
    ),
    RoundtripCase(
        "event-transition",
        """
        state Root {
            state A { event go; }
            state B;
            [*] -> A;
            A -> B :: go;
        }
        """,
        'init state("Root.A"); check reach <= 1: active("Root.B");',
        _and(_assert_final("Root.B"), _assert_events(0, "Root.A.go")),
    ),
    RoundtripCase(
        "transition-priority-first-wins",
        """
        state Root {
            state A { event go; }
            state B;
            state C;
            [*] -> A;
            A -> B :: go;
            A -> C :: go;
        }
        """,
        'init state("Root.A"); check reach <= 1: active("Root.B");',
        _and(_assert_final("Root.B"), _assert_events(0, "Root.A.go")),
    ),
    RoundtripCase(
        "fallback-event-absent",
        """
        state Root {
            state A { event go; }
            state B;
            [*] -> A;
            A -> B :: go;
        }
        """,
        'init state("Root.A");\n'
        'assume event("Root.A.go", 0) == false;\n'
        'check reach <= 1: active("Root.A");',
        _and(_assert_final("Root.A"), _assert_progress(0, "fallback_gamma")),
    ),
    RoundtripCase(
        "fallback-guard-false",
        """
        def int x = 0;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B : if [x > 0];
        }
        """,
        'init state("Root.A") havoc * where x == 0;\n'
        'check reach <= 1: active("Root.A") && x == 0;',
        _and(_assert_final("Root.A", x=0), _assert_progress(0, "fallback_gamma")),
    ),
    RoundtripCase(
        "transition-effect-writes-vars",
        """
        def int x = 0;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B effect { x = x + 2; };
        }
        """,
        'init state("Root.A") havoc * where x == 1;\n'
        'check reach <= 1: active("Root.B") && x == 3;',
        _assert_final("Root.B", x=3),
    ),
    RoundtripCase(
        "exit-action-order",
        """
        def int x = 0;
        state Root {
            state A { exit { x = x + 10; } }
            state B;
            [*] -> A;
            A -> B;
        }
        """,
        'init state("Root.A") havoc * where x == 1;\n'
        'check reach <= 1: active("Root.B") && x == 11;',
        _assert_final("Root.B", x=11),
    ),
    RoundtripCase(
        "enter-action-order",
        """
        def int x = 0;
        state Root {
            state A;
            state B { enter { x = x + 100; } }
            [*] -> A;
            A -> B;
        }
        """,
        'init state("Root.A") havoc * where x == 1;\n'
        'check reach <= 1: active("Root.B") && x == 101;',
        _assert_final("Root.B", x=101),
    ),
    RoundtripCase(
        "aspect-before-after-during",
        """
        def int x = 0;
        state Root {
            >> during before { x = x + 1; }
            >> during after { x = x + 100; }
            state A { during { x = x + 10; } }
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A") && x == 111;',
        _assert_final("Root.A", x=111),
    ),
    RoundtripCase(
        "parent-continuation",
        """
        def int x = 0;
        state Root {
            state Parent {
                state A;
                [*] -> A;
                A -> [*] :: done effect { x = x + 1; };
            }
            state B { enter { x = x + 10; } }
            [*] -> Parent;
            Parent -> B :: switch;
        }
        """,
        'init state("Root.Parent.A") havoc * where x == 0;\n'
        'assume event("Root.Parent.A.done", 0) == true;\n'
        'assume event("Root.Parent.switch", 0) == true;\n'
        'check reach <= 1: active("Root.B") && x == 11;',
        _and(
            _assert_final("Root.B", x=11),
            _assert_events(0, "Root.Parent.A.done", "Root.Parent.switch"),
        ),
    ),
    RoundtripCase(
        "pseudo-initial-multi-hop",
        """
        state Root {
            pseudo state P1;
            pseudo state P2;
            state A;
            [*] -> P1;
            P1 -> P2;
            P2 -> A;
        }
        """,
        'check reach <= 1: active("Root.A");',
        _assert_final("Root.A"),
    ),
    RoundtripCase(
        "validation-rollback-keeps-vars",
        """
        def int x = 0;
        state Root {
            state A;
            state Bad { [*] -> Dead : if [false]; state Dead; }
            [*] -> A;
            A -> Bad effect { x = 99; };
        }
        """,
        'init state("Root.A") havoc * where x == 1;\n'
        'check reach <= 1: active("Root.A") && x == 1;',
        _and(_assert_final("Root.A", x=1), _assert_progress(0, "fallback_gamma")),
    ),
    RoundtripCase(
        "terminal-transition",
        """
        state Root {
            state A;
            [*] -> A;
            A -> [*];
        }
        """,
        'init state("Root.A"); check reach <= 1: terminated();',
        lambda trace, replay: assert_terminated(trace, replay),
    ),
    RoundtripCase(
        "combo-trigger-two-events",
        """
        def int x = 0;
        state Root {
            state A { event a; event b; }
            state B;
            [*] -> A;
            A -> B :: a + b effect { x = x + 5; };
        }
        """,
        'init state("Root.A") havoc * where x == 0;\n'
        'check reach <= 1: active("Root.B") && x == 5;',
        _and(_assert_final("Root.B", x=5), _assert_events(0, "Root.A.a", "Root.A.b")),
    ),
    RoundtripCase(
        "multiple-events-without-cardinality",
        """
        state Root {
            state A { event a; event b; }
            state B;
            [*] -> A;
            A -> B :: a;
        }
        """,
        'init state("Root.A");\n'
        'assume event("Root.A.a", 0) == true;\n'
        'assume event("Root.A.b", 0) == true;\n'
        'check reach <= 1: active("Root.B");',
        _and(_assert_final("Root.B"), _assert_events(0, "Root.A.a", "Root.A.b")),
    ),
    RoundtripCase(
        "at-most-one-cardinality",
        """
        state Root {
            state A { event a; event b; }
            state B;
            state C;
            [*] -> A;
            A -> B :: a;
            A -> C :: b;
        }
        """,
        'init state("Root.A");\n'
        'assume events cardinality at_most_one {"Root.A.a", "Root.A.b"};\n'
        'check reach <= 1: active("Root.B");',
        _and(_assert_final("Root.B"), _assert_events(0, "Root.A.a")),
    ),
    RoundtripCase(
        "abstract-during-call",
        """
        def int x = 0;
        state Root {
            state A {
                during abstract Touch;
                during { x = x + 1; }
            }
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A") && '
        'call_count("Root.A.Touch", step=0) == 1 && x == 1;',
        _and(_assert_final("Root.A", x=1), _assert_call_count(0, 1)),
    ),
    RoundtripCase(
        "abstract-call-snapshot-before-after-mutation",
        """
        def int x = 0;
        state Root {
            state A {
                during abstract Before;
                during { x = x + 1; }
                during abstract After;
            }
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A") && '
        "call_count(step=0) == 2 && "
        'call_count("Root.A.Before", step=0, where x == 0) == 1 && '
        'call_count("Root.A.After", step=0, where x == 1) == 1 && x == 1;',
        _and(_assert_final("Root.A", x=1), _assert_call_count(0, 2)),
    ),
    RoundtripCase(
        "named-ref-abstract-call",
        """
        state Root {
            state Library { enter abstract Shared; }
            state A { enter FirstRef ref /Library.Shared; }
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A") && '
        'called("Root.Library.Shared", step=0, named_ref="Root.A.FirstRef");',
        _and(_assert_final("Root.A"), _assert_call_count(0, 1)),
    ),
    RoundtripCase(
        "response-property-support-event",
        """
        state Root {
            event trigger;
            state A;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        "check response <= 1:\n"
        '  trigger event("Root.trigger", current)\n'
        "  -> within 1 terminated();",
        _and(_assert_final("Root.A"), _assert_events(0, "Root.trigger")),
    ),
    RoundtripCase(
        "event-clean-noise-extra-constraint",
        """
        state Root {
            state A { event go; event noise; }
            state B;
            [*] -> A;
            A -> B :: go;
        }
        """,
        'init state("Root.A"); check reach <= 1: active("Root.B");',
        _and(_assert_final("Root.B"), _assert_events(0, "Root.A.go")),
        lambda formula: (formula.core.symbols.event_input(0, "Root.A.noise"),),
    ),
    RoundtripCase(
        "semantic-delta-no-progress",
        """
        state Root {
            state Parent {
                state A;
                [*] -> A :: unlock;
            }
            [*] -> Parent;
        }
        """,
        'init state("Root.Parent");\n'
        'assume event("Root.Parent.unlock", 0) == false;\n'
        'check reach <= 1: active("Root.Parent");',
        _and(_assert_final("Root.Parent"), _assert_progress(0, "semantic_delta")),
    ),
    RoundtripCase(
        "havoc-where-replay-start",
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 2; } }
            [*] -> A;
        }
        """,
        "init cold havoc * where x == 9;\n"
        'check reach <= 1: active("Root.A") && x == 11;',
        _assert_final("Root.A", x=11),
    ),
    RoundtripCase(
        "initial-terminated-absorb",
        """
        def int x = 0;
        state Root;
        """,
        "init terminated havoc * where x == 4;\n"
        "check reach <= 1: terminated() && x == 4;",
        lambda trace, replay: assert_terminated(trace, replay, x=4),
    ),
]


def assert_terminated(trace, replay, **vars_) -> None:
    """Assert that both witness and replay end in the terminated sentinel."""
    assert trace.frames[-1].terminated is True
    assert replay.runtime_trace.frames[-1].terminated is True
    for name, value in vars_.items():
        assert trace.frames[-1].vars[name] == value
        assert replay.runtime_trace.frames[-1].vars[name] == value


@pytest.mark.parametrize("case", ROUNDTRIP_CASES, ids=lambda item: item.name)
def test_bmc_witness_roundtrip_matches_simulation_runtime(case: RoundtripCase) -> None:
    """Every hand-authored SAT witness must replay through SimulationRuntime."""
    assert len(ROUNDTRIP_CASES) >= 20
    _roundtrip(case)


def test_at_most_one_cardinality_rejects_two_simultaneous_events() -> None:
    """The event-cardinality assumption is still enforced by the core relation."""
    case = next(
        item for item in ROUNDTRIP_CASES if item.name == "at-most-one-cardinality"
    )
    model = load_state_machine_from_text(case.dsl)
    formula = compile_bmc_property(
        build_bmc_core_formula(BmcEngine(model).prepare(case.query))
    )
    solver = z3.Solver()
    solver.add(
        formula.solve_formula,
        formula.core.symbols.event_input(0, "Root.A.a"),
        formula.core.symbols.event_input(0, "Root.A.b"),
    )
    assert solver.check() == z3.unsat
