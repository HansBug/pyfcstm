"""Shared fixtures for topology verification tests."""

from __future__ import annotations

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import StateMachine, parse_dsl_node_to_state_machine


def _parse(dsl: str) -> StateMachine:
    return parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(dsl, 'state_machine_dsl')
    )


@pytest.fixture
def parse_dsl():
    """Return a function that parses an inline DSL snippet into a StateMachine."""
    return _parse


@pytest.fixture
def linear_machine():
    """Three leaves in a row, terminating cleanly via root [*]."""
    return _parse(
        """
        state Root {
            state A;
            state B;
            state C;
            [*] -> A;
            A -> B;
            B -> C;
            C -> [*];
        }
        """
    )


@pytest.fixture
def branching_machine():
    """One source with two terminating branches."""
    return _parse(
        """
        state Root {
            state Init;
            state Good;
            state Bad;
            [*] -> Init;
            Init -> Good;
            Init -> Bad;
            Good -> [*];
            Bad -> [*];
        }
        """
    )


@pytest.fixture
def trap_cycle_machine():
    """A <-> B never reach [*]."""
    return _parse(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B;
            B -> A;
        }
        """
    )


@pytest.fixture
def deadlock_machine():
    """B has no outgoing transition; B is a topological deadlock."""
    return _parse(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B;
        }
        """
    )


@pytest.fixture
def nested_machine():
    """Composite Outer contains Inner contains X/Y; one outer step then Done."""
    return _parse(
        """
        state Root {
            state Outer {
                state Inner {
                    state X;
                    state Y;
                    [*] -> X;
                    X -> Y;
                    Y -> [*];
                }
                state Sibling;
                [*] -> Inner;
                Inner -> Sibling;
                Sibling -> [*];
            }
            state Done;
            [*] -> Outer;
            Outer -> Done;
            Done -> [*];
        }
        """
    )


@pytest.fixture
def init_branch_machine():
    """Composite has two init transitions — both branches must appear in the
    initial leaves set (topological over-approximation of guard-driven inits).
    """
    return _parse(
        """
        state Root {
            state P {
                state X;
                state Y;
                [*] -> X;
                [*] -> Y;
                X -> [*];
                Y -> [*];
            }
            [*] -> P;
            P -> [*];
        }
        """
    )
