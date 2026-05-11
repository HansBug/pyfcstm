"""Tests for :func:`pyfcstm.topology.check_inevitability`."""

from __future__ import annotations

import pytest

from pyfcstm.topology import check_inevitability


@pytest.mark.unittest
class TestInevitabilityPositive:
    def test_linear_chain_target_is_inevitable(self, linear_machine):
        # Every path must traverse A, B, C.
        for name in ('A', 'B', 'C'):
            r = check_inevitability(linear_machine, target='Root.' + name)
            assert r.inevitable is True, name

    def test_source_equals_target(self, linear_machine):
        r = check_inevitability(linear_machine, target='Root.A', source='Root.A')
        assert r.inevitable is True


@pytest.mark.unittest
class TestInevitabilityBranching:
    def test_branching_target_is_avoidable(self, branching_machine):
        r = check_inevitability(branching_machine, target='Root.Good')
        assert r.inevitable is False
        # Counterexample is alt_end via the Bad branch.
        assert r.counterexample.kind == 'alt_end'
        prefix_names = [s.name for s in r.counterexample.prefix]
        assert 'Init' in prefix_names and 'Bad' in prefix_names

    def test_branching_pre_branch_is_inevitable(self, branching_machine):
        r = check_inevitability(branching_machine, target='Root.Init')
        assert r.inevitable is True


@pytest.mark.unittest
class TestInevitabilityCycleCex:
    def test_target_avoidable_via_cycle(self, parse_dsl):
        # A -> B -> A (cycle) and A -> C -> [*]. Is C inevitable from A? No -
        # the cycle is an infinite path that never reaches C.
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
        r = check_inevitability(sm, target='Root.C')
        assert r.inevitable is False
        assert r.counterexample.kind == 'cycle'
        cycle_names = [s.name for s in r.counterexample.cycle]
        # The cycle should mention A and B.
        assert set(cycle_names) & {'A', 'B'} == {'A', 'B'}


@pytest.mark.unittest
class TestInevitabilityDeadlockCex:
    def test_real_deadlock_in_residual_blocks_inevitability(self, parse_dsl):
        # A -> {B, C}; B is a true deadlock (no out); C -> [*]. Inev(C) from A?
        # No - the path A -> B is a real deadlock that avoids C.
        sm = parse_dsl(
            """
            state Root {
                state A;
                state B;
                state C;
                [*] -> A;
                A -> B;
                A -> C;
                C -> [*];
            }
            """
        )
        r = check_inevitability(sm, target='Root.C')
        assert r.inevitable is False
        assert r.counterexample.kind == 'deadlock'
        assert r.counterexample.terminal.name == 'B'

    def test_residual_only_deadlock_is_not_a_counterexample(self, linear_machine):
        # A -> B -> C -> [*]. Inev(B)? Removing B leaves A with no out edges
        # IN RESIDUAL, but A originally had an out edge to B. That is NOT a
        # counterexample (target unavoidable), and the algorithm must
        # recognize this.
        r = check_inevitability(linear_machine, target='Root.B')
        assert r.inevitable is True


@pytest.mark.unittest
class TestInevitabilityUnreachable:
    def test_target_unreachable_is_avoidable(self, parse_dsl):
        sm = parse_dsl(
            """
            state Root {
                state A;
                state B;
                state Detached;
                [*] -> A;
                A -> B;
                B -> [*];
            }
            """
        )
        r = check_inevitability(sm, target='Root.Detached')
        assert r.inevitable is False
        assert r.counterexample.kind == 'unreachable'


@pytest.mark.unittest
class TestInevitabilitySource:
    def test_source_changes_verdict(self, branching_machine):
        # From Bad alone, Bad IS inevitable (you are already there).
        r = check_inevitability(branching_machine, target='Root.Bad', source='Root.Bad')
        assert r.inevitable is True
        # From Init, Bad is avoidable (you might go Good).
        r2 = check_inevitability(branching_machine, target='Root.Bad', source='Root.Init')
        assert r2.inevitable is False
