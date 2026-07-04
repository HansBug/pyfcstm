"""Macro-step expansion tests for FCSTM BMC."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyfcstm.bmc import (
    BmcBuildError,
    build_bmc_domain,
    entry_source,
    stable_leaf_source,
)
from pyfcstm.bmc.expand import MacroExpansionOptions, expand_macro_step_cases
from pyfcstm.model import IfBlock, load_state_machine_from_text

_FIXTURE = Path(__file__).with_name("fixtures") / "macro_runtime_alignment.fcstm"


def _case_by_kind_target(formal, kind, target_path):
    for case in formal.cases:
        if case.kind == kind and case.target_state_path == target_path:
            return case
    raise AssertionError("missing %s -> %s case" % (kind, target_path))


def _conditions(case):
    return set(case.condition.variables)


@pytest.mark.unittest
def test_stable_leaf_fallback_records_during_action_blocks_not_var_updates():
    """Fallback keeps executable model blocks and no longer exposes writeback text."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            >> during before { x = x + 10; }
            state A { during { x = x + 1; } }
            [*] -> A;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    fallback = _case_by_kind_target(formal, "fallback", "Root.A")

    assert fallback.condition.variables == ()
    assert [block.runtime_role for block in fallback.action_blocks] == [
        "leaf_during",
        "leaf_during",
    ]
    assert "var_update" not in fallback.to_canonical()


@pytest.mark.unittest
def test_transition_priority_masks_exclude_accepted_paths_not_raw_guards():
    """Later transitions are gated by accepted:<label> atoms for earlier paths."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A;
            state B;
            state C;
            [*] -> A;
            A -> B : if [x > 0];
            A -> C : if [x < 10];
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    first = _case_by_kind_target(formal, "transition", "Root.B")
    second = _case_by_kind_target(formal, "transition", "Root.C")
    fallback = _case_by_kind_target(formal, "fallback", "Root.A")

    assert _conditions(first) == {"guard:g0"}
    assert "accepted:%s" % first.label in _conditions(second)
    assert "guard:g1" in second.condition.variables
    assert {
        priority.excluded_case_labels for priority in second.priority_exclusions
    } == {(first.label,)}
    assert "accepted:%s" % first.label in _conditions(fallback)
    assert "accepted:%s" % second.label in _conditions(fallback)


@pytest.mark.unittest
def test_action_if_block_is_recorded_without_splitting_cases():
    """Action-local IfBlock stays inside ActionBlock and never becomes a condition atom."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A {
                during {
                    if [x > 0] { x = x + 1; } else { x = x - 1; }
                }
            }
            [*] -> A;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    fallback = _case_by_kind_target(formal, "fallback", "Root.A")

    assert len(formal.cases) == 1
    assert fallback.condition.variables == ()
    assert isinstance(fallback.action_blocks[0].operations[0], IfBlock)


@pytest.mark.unittest
def test_runtime_fixture_records_guard_anchors_after_prefix_actions():
    """Guards are raw expressions with action-block anchors, not pre-substituted text."""
    model = load_state_machine_from_text(_FIXTURE.read_text())
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.System.A"))

    to_b = _case_by_kind_target(formal, "transition", "Root.System.B")
    to_done = _case_by_kind_target(formal, "transition", "Root.Done")
    to_trap = _case_by_kind_target(formal, "transition", "Root.System.Trap.TrapLeaf")

    assert _conditions(to_trap) == {
        "event:Root.System.A.Tick",
        "event:Root.System.Trap.Arm",
    }
    assert "accepted:%s" % to_trap.label in _conditions(to_b)
    assert [
        (str(g.expr.to_ast_node()), g.after_action_block_index)
        for g in to_b.guard_requirements
    ] == [("x < 13", 2)]
    assert [
        (str(g.expr.to_ast_node()), g.after_action_block_index)
        for g in to_done.guard_requirements
    ] == [
        ("x >= 13", 2),
        ("y >= 30", 4),
    ]
    assert [block.runtime_role for block in to_done.action_blocks[:5]] == [
        "state_exit",
        "transition_effect",
        "transition_effect",
        "plain_during_after",
        "state_exit",
    ]


@pytest.mark.unittest
def test_hot_pseudo_entry_uses_guard_anchor_zero_for_first_route_guard():
    """Hot-started pseudo entry does not invent pre-guard action effects."""
    model = load_state_machine_from_text(_FIXTURE.read_text())
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(entry_source(domain, "Root.System.Route"))

    to_b = _case_by_kind_target(formal, "initial", "Root.System.B")
    to_done = _case_by_kind_target(formal, "initial", "Root.Done")
    delta = _case_by_kind_target(formal, "delta", "__diagnostic__")

    assert [
        (str(g.expr.to_ast_node()), g.after_action_block_index)
        for g in to_b.guard_requirements
    ] == [("x < 13", 0)]
    assert [
        (str(g.expr.to_ast_node()), g.after_action_block_index)
        for g in to_done.guard_requirements
    ] == [
        ("x >= 13", 0),
        ("y >= 30", 2),
    ]
    assert _conditions(delta) == {
        "accepted:%s" % to_b.label,
        "accepted:%s" % to_done.label,
    }


@pytest.mark.unittest
def test_rejected_pseudo_loop_allows_later_transition_and_fallback():
    """A structurally repeated pseudo candidate is failed, not accepted priority."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Go;
            state A { during { x = x + 1; } }
            pseudo state Loop;
            state Done;
            [*] -> A;
            A -> Loop :: Go;
            A -> Done :: Go;
            Loop -> Loop;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))

    selected = _case_by_kind_target(formal, "transition", "Root.Done")
    fallback = _case_by_kind_target(formal, "fallback", "Root.A")

    assert selected.condition.variables == ("event:Root.A.Go",)
    assert fallback.failed_conditions
    assert fallback.action_blocks[0].runtime_role == "leaf_during"


@pytest.mark.unittest
def test_variable_progressing_pseudo_loop_fails_closed():
    """PR-9 refuses to summarize pseudo loops whose convergence depends on effects."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A;
            pseudo state P;
            state B;
            [*] -> A;
            A -> P : if [x < 4];
            P -> P : if [x < 4] effect { x = x + 1; }
            P -> B : if [x >= 4];
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)

    with pytest.raises(BmcBuildError, match="micro-step safety limit"):
        expand_macro_step_cases(
            stable_leaf_source(domain, "Root.A"),
            MacroExpansionOptions(max_micro_steps=20),
        )
