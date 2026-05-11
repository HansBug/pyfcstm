"""Tests for the leaf-only macro graph builder."""

from __future__ import annotations

import pytest

from pyfcstm.topology import (
    END_KEY,
    END_NODE,
    build_topology_graph,
    node_key,
    resolve_to_leaves,
)


@pytest.mark.unittest
class TestResolveToLeaves:
    def test_leaf_passthrough(self, linear_machine):
        a = linear_machine.resolve_state('Root.A')
        assert resolve_to_leaves(a) == (a,)

    def test_composite_single_init(self, linear_machine):
        leaves = resolve_to_leaves(linear_machine.root_state)
        assert tuple(s.name for s in leaves) == ('A',)

    def test_composite_branching_init(self, init_branch_machine):
        root = init_branch_machine.root_state
        leaves = resolve_to_leaves(root)
        # Root has [*] -> P; P has [*] -> X and [*] -> Y → both must appear.
        names = tuple(s.name for s in leaves)
        assert set(names) == {'X', 'Y'}
        # Declaration order preserved.
        assert names == ('X', 'Y')

    def test_composite_without_init_is_unreachable_via_parser(self, parse_dsl):
        # The DSL parser itself rejects composite states with no init
        # transition (SyntaxError at parse time), so resolve_to_leaves's
        # defensive ValueError branch is only reachable via manual
        # ``State`` construction. We document the behavior here without
        # exercising the protected path.
        with pytest.raises(SyntaxError, match="entry transition"):
            parse_dsl(
                "state Root { state P { state X; X -> [*]; } [*] -> P; }"
            )


@pytest.mark.unittest
class TestBuildTopologyGraph:
    def test_linear_initial_leaves(self, linear_machine):
        g = build_topology_graph(linear_machine)
        assert tuple(s.name for s in g.initial_leaves) == ('A',)

    def test_linear_edges(self, linear_machine):
        g = build_topology_graph(linear_machine)
        labels = sorted(e.label for e in g.edges)
        assert labels == ['Root.A -> Root.B', 'Root.B -> Root.C', 'Root.C -> [*]']

    def test_branching_edges(self, branching_machine):
        g = build_topology_graph(branching_machine)
        labels = sorted(e.label for e in g.edges)
        assert labels == [
            'Root.Bad -> [*]',
            'Root.Good -> [*]',
            'Root.Init -> Root.Bad',
            'Root.Init -> Root.Good',
        ]

    def test_trap_cycle_edges(self, trap_cycle_machine):
        g = build_topology_graph(trap_cycle_machine)
        labels = sorted(e.label for e in g.edges)
        assert labels == ['Root.A -> Root.B', 'Root.B -> Root.A']

    def test_nested_macro_edges_flatten_through_hierarchy(self, nested_machine):
        g = build_topology_graph(nested_machine)
        labels = sorted(e.label for e in g.edges)
        # Every hierarchy boundary collapses to a leaf->leaf edge.
        assert labels == [
            'Root.Done -> [*]',
            'Root.Outer.Inner.X -> Root.Outer.Inner.Y',
            'Root.Outer.Inner.Y -> Root.Outer.Sibling',
            'Root.Outer.Sibling -> Root.Done',
        ]

    def test_branching_init_produces_multiple_edges(self, init_branch_machine):
        g = build_topology_graph(init_branch_machine)
        # P -> [*] transition on the parent, after bubbling, terminates at END.
        # Initial leaves include both X and Y because P has two init transitions.
        assert tuple(s.name for s in g.initial_leaves) == ('X', 'Y')

    def test_adjacency_recovers_state_objects(self, linear_machine):
        g = build_topology_graph(linear_machine)
        a = linear_machine.resolve_state('Root.A')
        b = linear_machine.resolve_state('Root.B')
        succs = g.successors(a)
        assert succs == (b,)

    def test_end_node_has_no_successors(self, linear_machine):
        g = build_topology_graph(linear_machine)
        assert g.successors(END_NODE) == ()
        assert g.adjacency[END_KEY] == ()

    def test_warnings_empty_on_wellformed_input(self, linear_machine, branching_machine, nested_machine):
        for sm in (linear_machine, branching_machine, nested_machine):
            assert build_topology_graph(sm).warnings == ()

    def test_off_cliff_emits_warning(self, parse_dsl):
        # Inner.A -> [*] bubbles to Inner; Inner has no transitions_from
        # declared on Root and Root itself has no Inner -> X. The off-cliff
        # exit should be dropped with a warning.
        sm = parse_dsl(
            """
            state Root {
                state Inner {
                    state A;
                    [*] -> A;
                    A -> [*];
                }
                [*] -> Inner;
            }
            """
        )
        g = build_topology_graph(sm)
        # A -> [*] bubbles to Inner; Inner has no transitions_from on Root.
        assert any('Inner' in w and 'stall' in w for w in g.warnings), g.warnings


@pytest.mark.unittest
class TestNodeKey:
    def test_end_node_key(self):
        assert node_key(END_NODE) == END_KEY

    def test_state_key_is_path_tuple(self, linear_machine):
        a = linear_machine.resolve_state('Root.A')
        assert node_key(a) == ('Root', 'A')
