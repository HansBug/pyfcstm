"""Tests for :func:`pyfcstm.topology.check_finiteness`."""

from __future__ import annotations

import pytest

from pyfcstm.topology import check_finiteness


@pytest.mark.unittest
class TestFinitenessPositive:
    def test_linear_chain_is_finite(self, linear_machine):
        r = check_finiteness(linear_machine)
        assert r.finite is True
        assert r.counterexample is None
        assert r.violating_node_count == 0

    def test_branching_with_terminal_branches_is_finite(self, branching_machine):
        r = check_finiteness(branching_machine)
        assert r.finite is True

    def test_nested_hierarchy_is_finite(self, nested_machine):
        r = check_finiteness(nested_machine)
        assert r.finite is True


@pytest.mark.unittest
class TestFinitenessTrapCycle:
    def test_simple_cycle_detected(self, trap_cycle_machine):
        r = check_finiteness(trap_cycle_machine)
        assert r.finite is False
        assert r.counterexample.kind == 'trap_cycle'
        cycle_names = tuple(s.name for s in r.counterexample.cycle)
        # Cycle visits A and B (start and end identical).
        assert set(cycle_names) == {'A', 'B'}
        # First and last cycle node are the same.
        assert cycle_names[0] == cycle_names[-1]

    def test_cycle_counter_lists_all_violating_leaves(self, trap_cycle_machine):
        r = check_finiteness(trap_cycle_machine)
        # Both A and B are in the trap region.
        assert r.violating_node_count == 2


@pytest.mark.unittest
class TestFinitenessDeadlock:
    def test_deadlock_reported(self, deadlock_machine):
        r = check_finiteness(deadlock_machine)
        assert r.finite is False
        assert r.counterexample.kind == 'deadlock'
        assert r.counterexample.deadlock_leaf.name == 'B'

    def test_deadlock_violation_count(self, deadlock_machine):
        r = check_finiteness(deadlock_machine)
        # Only the deadlock leaf itself counts as a direct violator.
        # Predecessor leaves are merely *reaching* a violation, not
        # violating in themselves.
        assert r.violating_node_count == 1


@pytest.mark.unittest
class TestFinitenessSource:
    def test_source_outside_cycle_yields_finite(self, parse_dsl):
        # Machine has a cycle A<->B, but C is on a clean exit path.
        sm = parse_dsl(
            """
            state Root {
                state A;
                state B;
                state C;
                [*] -> A;
                A -> B;
                B -> A;
                A -> C;
                C -> [*];
            }
            """
        )
        # From C alone, the only path is C -> [*]; finite.
        r = check_finiteness(sm, source='Root.C')
        assert r.finite is True

    def test_source_inside_cycle_yields_infinite(self, parse_dsl):
        sm = parse_dsl(
            """
            state Root {
                state A;
                state B;
                state C;
                [*] -> A;
                A -> B;
                B -> A;
                A -> C;
                C -> [*];
            }
            """
        )
        r = check_finiteness(sm, source='Root.B')
        # From B alone, B only goes to A; A goes to either B (cycle) or C (clean exit).
        # Default source = global init = A which has both options. From B: same as A.
        # The non-trivial SCC {A,B} is still reachable from B. But it's also escapable.
        # Per topo: every macro path from B → it can either escape via C (finite path)
        # or stay in cycle (infinite path). So overall not finite: ∃ infinite path.
        assert r.finite is False


@pytest.mark.unittest
class TestFinitenessFormatting:
    def test_cycle_cex_format(self, trap_cycle_machine):
        r = check_finiteness(trap_cycle_machine)
        text = r.counterexample.format()
        assert '[cycle:' in text
        assert 'Root.A' in text and 'Root.B' in text

    def test_deadlock_cex_format(self, deadlock_machine):
        r = check_finiteness(deadlock_machine)
        text = r.counterexample.format()
        assert 'deadlock(Root.B)' in text
        assert 'Root.A' in text
