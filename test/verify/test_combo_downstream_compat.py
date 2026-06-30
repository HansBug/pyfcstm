"""SMT-local verification smoke tests for combo-generated guard transitions."""

import pytest

from pyfcstm.verify import dead_guard, guard_tautology
from test.testings.combo_runtime import parse_machine


pytestmark = pytest.mark.unittest


def _variables(machine):
    return tuple(machine.defines.values())


def _combo_guard_transition(machine):
    return next(
        transition
        for state in machine.walk_states()
        for transition in state.transitions
        if transition.combo_origin_refs and transition.guard is not None
    )


def test_dead_guard_consumes_combo_generated_guard_transition():
    """The solver stack can prove an unsatisfiable combo guard transition."""
    machine = parse_machine(
        """
        def int x = 0;
        state Root {
            state S;
            state T;
            [*] -> S;
            S -> T :: E1 + [x > 0 && x < 0] + E2;
        }
        """
    )
    transition = _combo_guard_transition(machine)

    result = dead_guard(transition, _variables(machine), smt_timeout_ms=200)

    assert result.kind == "unsat"
    assert result.diagnostics[0]["code"] == "W_DEAD_GUARD"
    assert result.diagnostics[0]["data"]["transition"]["from_state"].startswith(
        "__combo_"
    )


def test_guard_tautology_consumes_combo_generated_guard_transition():
    """The solver stack can prove a tautological combo guard transition."""
    machine = parse_machine(
        """
        def int x = 0;
        state Root {
            state S;
            state T;
            [*] -> S;
            S -> T :: E1 + [x >= 0 || x < 0] + E2;
        }
        """
    )
    transition = _combo_guard_transition(machine)

    result = guard_tautology(transition, _variables(machine), smt_timeout_ms=200)

    assert result.kind == "unsat"
    assert result.diagnostics[0]["code"] == "W_GUARD_TAUTOLOGY"
    assert result.diagnostics[0]["data"]["transition"]["guard"] == ("x >= 0 || x < 0")
