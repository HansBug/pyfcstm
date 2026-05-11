"""Tests for :func:`pyfcstm.topology.check_reachability`."""

from __future__ import annotations

import pytest

from pyfcstm.topology import build_topology_graph, check_reachability


@pytest.mark.unittest
class TestReachabilityHappyPath:
    def test_terminal_reachable_from_default_source(self, linear_machine):
        r = check_reachability(linear_machine, target='Root.C')
        assert r.reachable is True
        assert r.format_witness() == 'Root.A -> Root.B -> Root.C'
        assert r.unreach_leaves == ()

    def test_intermediate_reachable(self, linear_machine):
        r = check_reachability(linear_machine, target='Root.B')
        assert r.reachable is True
        assert r.format_witness() == 'Root.A -> Root.B'

    def test_source_equals_target_is_trivially_reachable(self, linear_machine):
        r = check_reachability(linear_machine, target='Root.A', source='Root.A')
        assert r.reachable is True
        assert r.format_witness() == 'Root.A'


@pytest.mark.unittest
class TestReachabilityNegative:
    def test_target_unreachable_from_alternative_source(self, linear_machine):
        # Start at the terminal-most stoppable state; cannot go back.
        r = check_reachability(linear_machine, target='Root.A', source='Root.C')
        assert r.reachable is False
        # Both A and B are unreachable from C.
        unreach_names = {l.name for l in r.unreach_leaves}
        assert unreach_names == {'A', 'B'}

    def test_witness_is_none_when_unreachable(self, linear_machine):
        r = check_reachability(linear_machine, target='Root.A', source='Root.C')
        assert r.witness_path is None
        assert r.format_witness() == ''


@pytest.mark.unittest
class TestReachabilityHierarchical:
    def test_descend_into_composite_target(self, nested_machine):
        # Target a composite — resolved into its init leaf (X).
        r = check_reachability(nested_machine, target='Root.Outer')
        assert r.reachable is True

    def test_descend_into_composite_source(self, nested_machine):
        r = check_reachability(
            nested_machine,
            target='Root.Outer.Sibling',
            source='Root.Outer',
        )
        assert r.reachable is True

    def test_cross_hierarchy_reach(self, nested_machine):
        r = check_reachability(
            nested_machine,
            target='Root.Done',
            source='Root.Outer.Inner.X',
        )
        assert r.reachable is True
        assert 'Root.Outer.Inner.X' in r.format_witness()
        assert 'Root.Done' in r.format_witness()


@pytest.mark.unittest
class TestReachabilityErrors:
    def test_unknown_target_raises(self, linear_machine):
        with pytest.raises(LookupError):
            check_reachability(linear_machine, target='Root.DoesNotExist')

    def test_unknown_source_raises(self, linear_machine):
        with pytest.raises(LookupError):
            check_reachability(linear_machine, target='Root.A', source='Root.Nope')

    def test_invalid_target_type_raises(self, linear_machine):
        with pytest.raises(TypeError):
            check_reachability(linear_machine, target=42)


@pytest.mark.unittest
class TestReachabilityGraphReuse:
    def test_prebuilt_graph_reused(self, linear_machine):
        graph = build_topology_graph(linear_machine)
        r1 = check_reachability(linear_machine, target='Root.B', graph=graph)
        r2 = check_reachability(linear_machine, target='Root.C', graph=graph)
        assert r1.reachable and r2.reachable
