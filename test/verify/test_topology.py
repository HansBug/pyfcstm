import inspect
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import StateMachine, parse_dsl_node_to_state_machine
from pyfcstm.verify.registry import REGISTRY


pytestmark = pytest.mark.unittest


GROUP1_TOPOLOGY = (
    "topological_reachable_set",
    "unreachable_states",
    "strongly_connected_components",
    "topological_finite",
    "topological_inevitable_terminator",
    "event_emission_to_consumer_reachable",
)

GROUP2_SMT_LOCAL = (
    "dead_guard",
    "guard_tautology",
    "forced_guard_unsat_under_init",
    "effect_no_op_under_guard",
    "effect_contradicts_guard",
    "transition_shadowed_by_predecessor",
    "enter_postcondition_implies_during_precondition",
    "composite_init_guards_incomplete",
)

def _parse(src: str) -> StateMachine:
    ast = parse_with_grammar_entry(src, "state_machine_dsl")
    return cast(StateMachine, parse_dsl_node_to_state_machine(ast))


def _import_topology():
    from pyfcstm.verify import topology

    return topology


def test_build_leaf_level_macro_graph_flat_edges():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state Idle;
            state Active;
            [*] -> Idle;
            Idle -> Active;
            Active -> [*];
        }
        """
    )

    graph = topology.build_leaf_level_macro_graph(machine)

    assert graph.nodes == ("Root.Active", "Root.Idle")
    assert graph.edges["Root.Idle"] == ("Root.Active",)
    assert graph.edges["Root.Active"] == (topology.EXIT_ROOT_SINK,)


def test_leaf_level_graph_is_immutable_value_object():
    topology = _import_topology()

    graph = topology.LeafLevelGraph(
        nodes=("Root.A",),
        edges={"Root.A": (topology.EXIT_ROOT_SINK,)},
    )

    with pytest.raises(FrozenInstanceError):
        graph.nodes = ("Root.B",)  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(TypeError):
        graph.edges["Root.A"] = ("Root.B",)  # pyright: ignore[reportIndexIssue]


def test_build_leaf_level_macro_graph_init_cascade_and_leaf_bubble():
    topology = _import_topology()
    machine = _parse(
        """
        state System {
            state Working {
                state Active;
                state Idle;
                [*] -> Active;
                Active -> Idle;
                Idle -> [*];
            }
            state Done;
            state Orphan;
            [*] -> Working;
            Working -> Done;
            Done -> [*];
        }
        """
    )

    graph = topology.build_leaf_level_macro_graph(machine)

    assert graph.edges["System.Working.Active"] == ("System.Working.Idle",)
    assert graph.edges["System.Working.Idle"] == ("System.Done",)
    assert graph.edges["System.Done"] == (topology.EXIT_ROOT_SINK,)
    assert graph.edges["System.Orphan"] == tuple()


def test_build_leaf_level_macro_graph_uses_forced_expansion_and_parent_bubble():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A {
                state A1;
                state A2;
                [*] -> A1;
            }
            state Error;
            [*] -> A;
            !A -> Error :: Crash;
        }
        """
    )

    graph = topology.build_leaf_level_macro_graph(machine)

    assert graph.edges["Root.A.A1"] == ("Root.Error",)
    assert graph.edges["Root.A.A2"] == ("Root.Error",)


def test_topological_reachable_set_handles_nested_hierarchy_and_bubble():
    topology = _import_topology()
    machine = _parse(
        """
        state System {
            state Working {
                state Active;
                state Idle;
                [*] -> Active;
                Active -> Idle;
                Idle -> [*];
            }
            state Done;
            state Orphan;
            [*] -> Working;
            Working -> Done;
            Done -> [*];
        }
        """
    )

    reachable = topology.topological_reachable_set(machine)

    assert reachable["System"] == (
        "System.Done",
        "System.Working.Active",
        "System.Working.Idle",
    )
    assert reachable["System.Working"] == (
        "System.Done",
        "System.Working.Active",
        "System.Working.Idle",
    )
    assert reachable["System.Working.Active"] == (
        "System.Done",
        "System.Working.Idle",
    )
    assert reachable["System.Working.Idle"] == ("System.Done",)
    assert reachable["System.Done"] == tuple()
    assert reachable["System.Orphan"] == tuple()


def test_topological_reachable_set_matches_inspect_on_flat_model():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state Idle;
            state Active;
            [*] -> Idle;
            Idle -> Active;
            Active -> Idle;
        }
        """
    )

    actual = topology.topological_reachable_set(machine)
    expected = inspect_model(machine).reachability_graph

    assert {name: set(value) for name, value in actual.items()} == {
        name: set(value) for name, value in expected.items()
    }


def test_build_leaf_level_macro_graph_handles_root_exit_sink_once():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            [*] -> A;
            A -> [*];
        }
        """
    )

    graph = topology.build_leaf_level_macro_graph(machine)

    assert graph.edges["Root.A"] == (topology.EXIT_ROOT_SINK,)
    assert graph.edges[topology.EXIT_ROOT_SINK] == tuple()


def test_build_leaf_level_macro_graph_treats_root_leaf_as_exit_capable():
    topology = _import_topology()
    machine = _parse("state Root;")

    graph = topology.build_leaf_level_macro_graph(machine)

    assert graph.nodes == ("Root",)
    assert graph.edges["Root"] == (topology.EXIT_ROOT_SINK,)
    assert topology.topological_finite(machine).finite is True
    assert topology.topological_inevitable_terminator(machine).inevitable is True


def test_build_leaf_level_macro_graph_bubbles_parent_exit_to_root_sink():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state Outer {
                state A;
                [*] -> A;
                A -> [*];
            }
            [*] -> Outer;
            Outer -> [*];
        }
        """
    )

    graph = topology.build_leaf_level_macro_graph(machine)

    assert graph.edges["Root.Outer.A"] == (topology.EXIT_ROOT_SINK,)


def test_build_leaf_level_macro_graph_requires_leaf_exit_before_parent_transition():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state Running {
                state Active;
                state Idle;
                [*] -> Active;
                Active -> Idle;
            }
            state Error;
            [*] -> Running;
            Running -> Error;
            Error -> [*];
        }
        """
    )

    graph = topology.build_leaf_level_macro_graph(machine)
    reachable = topology.topological_reachable_set(machine)

    assert graph.edges["Root.Running.Active"] == ("Root.Running.Idle",)
    assert graph.edges["Root.Running.Idle"] == tuple()
    assert reachable["Root"] == ("Root.Running.Active", "Root.Running.Idle")
    assert reachable["Root.Running"] == (
        "Root.Running.Active",
        "Root.Running.Idle",
    )
    assert topology.unreachable_states(machine) == ("Root.Error",)
    assert topology.topological_finite(machine).counterexamples == (
        ("deadlock", "Root.Running.Idle"),
    )
    assert topology.topological_inevitable_terminator(
        machine
    ).counterexample_path == ("Root.Running.Idle",)


def test_build_leaf_level_macro_graph_bubbles_multi_level_exit_to_nested_target():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state Outer {
                state Inner {
                    state Active;
                    [*] -> Active;
                    Active -> [*];
                }
                state Cleanup {
                    state Flush;
                    [*] -> Flush;
                    Flush -> [*];
                }
                [*] -> Inner;
                Inner -> Cleanup;
                Cleanup -> [*];
            }
            state Done;
            [*] -> Outer;
            Outer -> Done;
            Done -> [*];
        }
        """
    )

    graph = topology.build_leaf_level_macro_graph(machine)
    reachable = topology.topological_reachable_set(machine)

    assert graph.edges["Root.Outer.Inner.Active"] == (
        "Root.Outer.Cleanup.Flush",
    )
    assert graph.edges["Root.Outer.Cleanup.Flush"] == ("Root.Done",)
    assert graph.edges["Root.Done"] == (topology.EXIT_ROOT_SINK,)
    assert reachable["Root"] == (
        "Root.Done",
        "Root.Outer.Cleanup.Flush",
        "Root.Outer.Inner.Active",
    )
    assert topology.topological_finite(machine).finite is True
    assert topology.topological_inevitable_terminator(machine).inevitable is True


def test_event_consumer_reachability_handles_nested_composite_sources():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            event Stop;
            event Lost;
            state System {
                state Running {
                    state Active;
                    [*] -> Active;
                    Active -> [*];
                }
                [*] -> Running;
                Running -> [*] : Stop;
            }
            state Orphan {
                state LostLeaf;
                [*] -> LostLeaf;
                LostLeaf -> LostLeaf : Lost;
            }
            [*] -> System;
            System -> [*];
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == (
        "Root.Orphan.Lost",
    )


def test_event_consumer_reachability_requires_bubble_for_composite_sources():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state System {
                event Stop;
                state Running {
                    state Active;
                    [*] -> Active;
                }
                [*] -> Running;
                Running -> [*] : Stop;
            }
            [*] -> System;
            System -> [*];
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == (
        "Root.System.Stop",
    )


def test_event_consumer_reachability_follows_chained_composite_boundary_exits():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            event RootStop;
            event InnerStop;
            state Outer {
                state Inner {
                    state Active;
                    [*] -> Active;
                    Active -> [*];
                }
                [*] -> Inner;
                Inner -> [*] : InnerStop;
            }
            [*] -> Outer;
            Outer -> [*] : RootStop;
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == tuple()


def test_event_consumer_reachability_deduplicates_boundary_exits():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            event Stop;
            state Outer {
                state Inner {
                    state A;
                    state B;
                    [*] -> A;
                    A -> B;
                    A -> [*];
                    B -> [*];
                }
                [*] -> Inner;
                Inner -> [*] : Stop;
            }
            [*] -> Outer;
            Outer -> [*];
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == tuple()


def test_event_consumer_reachability_ignores_non_exit_boundary_transition():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            event Stop;
            state Outer {
                state Inner {
                    state Active;
                    [*] -> Active;
                    Active -> [*];
                }
                state Done;
                [*] -> Inner;
                Inner -> Done;
            }
            [*] -> Outer;
            Outer -> [*] : Stop;
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == (
        "Root.Stop",
    )


def test_event_consumer_reachability_reports_unexposed_outer_boundary_event():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            event RootStop;
            state Outer {
                state Inner {
                    state Active;
                    [*] -> Active;
                    Active -> [*];
                }
                [*] -> Inner;
            }
            [*] -> Outer;
            Outer -> [*] : RootStop;
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == (
        "Root.RootStop",
    )


def test_topological_reachable_set_handles_diamond_closure_without_duplicates():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            state B;
            state C;
            state D;
            [*] -> A;
            A -> B;
            A -> C;
            B -> D;
            C -> D;
            D -> [*];
        }
        """
    )

    reachable = topology.topological_reachable_set(machine)

    assert reachable["Root.A"] == ("Root.B", "Root.C", "Root.D")


def test_topological_finite_ignores_unreachable_trap_cycle():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            state Lost1;
            state Lost2;
            [*] -> A;
            A -> [*];
            Lost1 -> Lost2;
            Lost2 -> Lost1;
        }
        """
    )

    report = topology.topological_finite(machine)

    assert report.finite is True
    assert report.counterexamples == tuple()


def test_unreachable_states_reports_unreachable_leaves_only():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            state OrphanComposite {
                state Lost;
                [*] -> Lost;
            }
            state OrphanLeaf;
            [*] -> A;
        }
        """
    )

    assert topology.unreachable_states(machine) == (
        "Root.OrphanComposite.Lost",
        "Root.OrphanLeaf",
    )


def test_unreachable_states_ignores_unreachable_pseudo_states():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            pseudo state Crash;
            [*] -> A;
        }
        """
    )

    assert topology.unreachable_states(machine) == tuple()


def test_strongly_connected_components_reports_two_node_cycle():
    topology = _import_topology()
    machine = _parse(
        """
        state Controller {
            state Idle;
            state Running;
            state Stopped;
            [*] -> Idle;
            Idle -> Running;
            Running -> Idle;
            Running -> Stopped;
            Stopped -> [*];
        }
        """
    )

    assert topology.strongly_connected_components(machine) == (
        ("Controller.Idle", "Controller.Running"),
    )


def test_strongly_connected_components_reports_self_loop():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state Loop;
            [*] -> Loop;
            Loop -> Loop;
            Loop -> [*];
        }
        """
    )

    assert topology.strongly_connected_components(machine) == (("Root.Loop",),)


def test_strongly_connected_components_ignores_acyclic_graph():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B;
            B -> [*];
        }
        """
    )

    assert topology.strongly_connected_components(machine) == tuple()


def test_strongly_connected_components_handles_deep_chain_without_recursion():
    topology = _import_topology()
    n_states = 1050
    lines = ["state Root {"]
    for index in range(n_states):
        lines.append("    state S%d;" % index)
    lines.append("    [*] -> S0;")
    for index in range(n_states - 1):
        lines.append("    S%d -> S%d;" % (index, index + 1))
    lines.append("    S%d -> [*];" % (n_states - 1))
    lines.append("}")
    machine = _parse("\n".join(lines))

    assert topology.strongly_connected_components(machine) == tuple()
    assert topology.topological_finite(machine).finite is True


def test_strongly_connected_components_keeps_diamond_join_acyclic():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            state B;
            state C;
            [*] -> A;
            A -> B;
            A -> C;
            B -> C;
            C -> [*];
        }
        """
    )

    assert topology.strongly_connected_components(machine) == tuple()


def test_topological_finite_accepts_every_reachable_leaf_with_exit_path():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B;
            B -> [*];
        }
        """
    )

    report = topology.topological_finite(machine)

    assert report.finite is True
    assert report.counterexamples == tuple()


def test_topological_finite_reports_trap_cycle():
    topology = _import_topology()
    machine = _parse(
        """
        state System {
            state A;
            state B;
            [*] -> A;
            A -> B;
            B -> A;
        }
        """
    )

    report = topology.topological_finite(machine)

    assert report.finite is False
    assert report.counterexamples == (("trap_cycle", ("System.A", "System.B")),)


def test_topological_finite_reports_deadlock():
    topology = _import_topology()
    machine = _parse(
        """
        state System {
            state A;
            state B;
            [*] -> A;
            A -> B;
        }
        """
    )

    report = topology.topological_finite(machine)

    assert report.finite is False
    assert report.counterexamples == (("deadlock", "System.B"),)


def test_topological_finite_treats_parent_off_cliff_exit_as_deadlock():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state Outer {
                state A;
                [*] -> A;
                A -> [*];
            }
            [*] -> Outer;
        }
        """
    )

    report = topology.topological_finite(machine)

    assert report.finite is False
    assert report.counterexamples == (("deadlock", "Root.Outer.A"),)


def test_topological_inevitable_terminator_accepts_straight_exit():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            state Done;
            [*] -> A;
            A -> Done;
            Done -> [*];
        }
        """
    )

    report = topology.topological_inevitable_terminator(machine)

    assert report.inevitable is True
    assert report.counterexample_path is None


def test_topological_inevitable_terminator_reports_branch_to_cycle():
    topology = _import_topology()
    machine = _parse(
        """
        state System {
            state Init;
            state Cycle;
            state Done;
            [*] -> Init;
            Init -> Cycle;
            Init -> Done;
            Done -> [*];
            Cycle -> Cycle;
        }
        """
    )

    report = topology.topological_inevitable_terminator(machine)

    assert report.inevitable is False
    assert report.counterexample_path == ("System.Cycle",)


def test_topological_inevitable_terminator_reports_self_loop_even_with_exit():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            state Done;
            [*] -> A;
            A -> A;
            A -> Done;
            Done -> [*];
        }
        """
    )

    report = topology.topological_inevitable_terminator(machine)

    assert report.inevitable is False
    assert report.counterexample_path == ("Root.A",)


def test_topological_inevitable_terminator_reports_deadlock_leaf():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B;
        }
        """
    )

    report = topology.topological_inevitable_terminator(machine)

    assert report.inevitable is False
    assert report.counterexample_path == ("Root.B",)


def test_event_emission_to_consumer_reachable_reports_fully_unreachable_event():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            event PanicEvt;
            state A;
            state Unreachable1;
            state Unreachable2;
            [*] -> A;
            A -> A;
            Unreachable1 -> Unreachable2 : PanicEvt;
            Unreachable2 -> A : PanicEvt;
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == ("Root.PanicEvt",)


def test_event_emission_to_consumer_reachable_allows_partially_reachable_event():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            event NormalEvt;
            state A;
            state B;
            state Unreachable;
            [*] -> A;
            A -> B : NormalEvt;
            Unreachable -> A : NormalEvt;
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == tuple()


def test_event_emission_to_consumer_reachable_ignores_unused_declared_event():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            event Unused;
            state A;
            [*] -> A;
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == tuple()


def test_event_emission_to_consumer_reachable_handles_init_event_source_as_reachable():
    topology = _import_topology()
    machine = _parse(
        """
        state Root {
            event Boot;
            state A;
            [*] -> A : Boot;
        }
        """
    )

    assert topology.event_emission_to_consumer_reachable(machine) == tuple()


def test_registry_wires_group1_topology_implementations():
    topology = _import_topology()

    expected_impls = {
        "topological_reachable_set": topology.topological_reachable_set,
        "unreachable_states": topology.unreachable_states,
        "strongly_connected_components": topology.strongly_connected_components,
        "topological_finite": topology.topological_finite,
        "topological_inevitable_terminator": (
            topology.topological_inevitable_terminator
        ),
        "event_emission_to_consumer_reachable": (
            topology.event_emission_to_consumer_reachable
        ),
    }
    for name in GROUP1_TOPOLOGY:
        assert REGISTRY[name].impl is expected_impls[name]
def test_topology_module_stays_independent_from_diagnostics_package():
    topology = _import_topology()

    source = inspect.getsource(topology)

    assert "pyfcstm.diagnostics" not in source
    assert "from ..diagnostics" not in source
