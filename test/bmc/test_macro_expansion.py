"""Macro-step expansion tests for FCSTM BMC."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from pyfcstm.bmc import (
    BmcBuildError,
    BmcDomain,
    MacroExpansionOptions,
    diagnostic_source,
    build_bmc_domain,
    entry_source,
    terminated_source,
    InvalidBmcEncoding,
    MacroStepSource,
    stable_leaf_source,
)
from pyfcstm.bmc.expand import (
    _FormalStackFrame,
    _MacroExpander,
    _MacroFrontier,
    expand_macro_step_cases,
)
from pyfcstm.bmc.macro import BoolTemplate
from pyfcstm.model import IfBlock, load_state_machine_from_text


def _bad_object() -> Any:
    """Return an intentionally bad value without tripping static type checks."""
    return cast(Any, object())


_FIXTURE = Path(__file__).with_name("fixtures") / "macro_runtime_alignment.fcstm"


def _case_by_kind_target(formal, kind, target_path):
    for case in formal.cases:
        if case.kind == kind and case.target_state_path == target_path:
            return case
    raise AssertionError("missing %s -> %s case" % (kind, target_path))


def _conditions(case):
    return set(case.condition.variables)


@pytest.mark.unittest
def test_expand_public_api_rejects_bad_source_and_options():
    """Public expansion entry validates only its public boundary arguments."""
    model = load_state_machine_from_text("state Root;")
    domain = build_bmc_domain(model, bound=1)

    with pytest.raises(InvalidBmcEncoding, match="source must be MacroStepSource"):
        expand_macro_step_cases(_bad_object())
    with pytest.raises(
        InvalidBmcEncoding, match="options must be MacroExpansionOptions"
    ):
        expand_macro_step_cases(
            stable_leaf_source(domain, "Root"), options=_bad_object()
        )
    with pytest.raises(InvalidBmcEncoding, match="max_micro_steps"):
        MacroExpansionOptions(max_micro_steps=0)
    with pytest.raises(InvalidBmcEncoding, match="max_stack_depth"):
        MacroExpansionOptions(max_stack_depth=True)
    with pytest.raises(InvalidBmcEncoding, match="partition_max_assignments"):
        MacroExpansionOptions(partition_max_assignments=0)
    with pytest.raises(InvalidBmcEncoding, match="verify_partition"):
        MacroExpansionOptions(verify_partition="yes")


@pytest.mark.unittest
def test_expand_rejects_domainless_and_modeless_sources():
    """Expansion requires a source carrying a domain with a model back-reference."""
    model = load_state_machine_from_text("state Root;")
    domain = build_bmc_domain(model, bound=1)
    source = stable_leaf_source(domain, "Root")
    modeless = BmcDomain(
        domain.bound,
        domain.states,
        domain.events,
        domain.variables,
        domain.frames,
        domain.steps,
        domain.event_inputs,
        domain.initial_state_ids,
        domain.stable_state_ids,
    )

    with pytest.raises(InvalidBmcEncoding, match="domain-backed source"):
        expand_macro_step_cases(MacroStepSource("stable_leaf", "recurrence", 0, "Root"))
    with pytest.raises(InvalidBmcEncoding, match="model back-reference"):
        expand_macro_step_cases(
            MacroStepSource(
                source.kind,
                source.origin,
                source.source_state_id,
                source.source_state_path,
                domain=modeless,
            )
        )


@pytest.mark.unittest
def test_expand_rejects_inconsistent_domain_model_snapshots():
    """Expansion fails loudly when a domain back-reference no longer matches ids."""
    source_model = load_state_machine_from_text(
        """
        state Root {
            state A;
            [*] -> A;
        }
        """
    )
    source_domain = build_bmc_domain(source_model, bound=1)
    missing_source_domain = BmcDomain(
        source_domain.bound,
        source_domain.states,
        source_domain.events,
        source_domain.variables,
        source_domain.frames,
        source_domain.steps,
        source_domain.event_inputs,
        source_domain.initial_state_ids,
        source_domain.stable_state_ids,
        model=load_state_machine_from_text("state Root;"),
    )
    source = MacroStepSource(
        "stable_leaf",
        "recurrence",
        source_domain.state_path_to_id("Root.A"),
        "Root.A",
        domain=missing_source_domain,
    )

    with pytest.raises(InvalidBmcEncoding, match="source state is not present"):
        expand_macro_step_cases(source)

    target_model = load_state_machine_from_text(
        """
        state Root {
            state A;
            [*] -> A;
        }
        """
    )
    target_domain = build_bmc_domain(load_state_machine_from_text("state Root;"), 1)
    missing_target_domain = BmcDomain(
        target_domain.bound,
        target_domain.states,
        target_domain.events,
        target_domain.variables,
        target_domain.frames,
        target_domain.steps,
        target_domain.event_inputs,
        target_domain.initial_state_ids,
        target_domain.stable_state_ids,
        model=target_model,
    )

    with pytest.raises(InvalidBmcEncoding, match="Unknown state path"):
        expand_macro_step_cases(entry_source(missing_target_domain))


@pytest.mark.unittest
def test_expand_rejects_event_paths_missing_from_domain_snapshot():
    """Event atoms discovered in model transitions must be present in the domain."""
    model = load_state_machine_from_text(
        """
        state Root {
            state A { event Go; }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    eventless_domain = BmcDomain(
        domain.bound,
        domain.states,
        (),
        domain.variables,
        domain.frames,
        domain.steps,
        (),
        domain.initial_state_ids,
        domain.stable_state_ids,
        model=model,
    )
    source = MacroStepSource(
        "stable_leaf",
        "recurrence",
        domain.state_path_to_id("Root.A"),
        "Root.A",
        domain=eventless_domain,
    )

    with pytest.raises(InvalidBmcEncoding, match="Unknown event path"):
        expand_macro_step_cases(source)


@pytest.mark.unittest
def test_internal_frontier_helpers_prune_false_and_clear_pending_pseudo_exit():
    """Internal frontier helpers keep false paths empty and clear pseudo-exit state."""
    model = load_state_machine_from_text(
        """
        state Root {
            state Parent {
                pseudo state Route;
                [*] -> Route;
                Route -> [*];
            }
            [*] -> Parent;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    expander = _MacroExpander(entry_source(domain), MacroExpansionOptions())
    root = model.root_state
    parent = root.substates["Parent"]
    route = parent.substates["Route"]

    false_frontier = _MacroFrontier(
        (_FormalStackFrame(root, "active"),),
        BoolTemplate.false(),
        (),
        (),
        (),
        (),
        "initial",
    )
    false_expansion = expander._expand_frontier(false_frontier)
    assert false_expansion.outcomes == ()
    assert false_expansion.failed == ()
    assert false_expansion.diagnostics == ()

    pending_frontier = _MacroFrontier(
        (_FormalStackFrame(parent, "init_wait", plain_before_pending=True),),
        BoolTemplate.true(),
        (),
        (),
        (),
        (),
        "initial",
    )
    cleared = expander._clear_parent_plain_before_pending_after_pseudo_exit(
        pending_frontier,
        route,
    )
    assert cleared.stack[-1].state is parent
    assert not cleared.stack[-1].plain_before_pending


@pytest.mark.unittest
def test_expansion_safety_limits_fail_closed():
    """Micro-step and stack-depth caps are loud build-time failures."""
    model = load_state_machine_from_text(
        """
        state Root {
            state Parent {
                state Child;
                [*] -> Child;
            }
            [*] -> Parent;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)

    with pytest.raises(BmcBuildError, match="micro-step"):
        expand_macro_step_cases(
            entry_source(domain),
            MacroExpansionOptions(max_micro_steps=1),
        )
    with pytest.raises(BmcBuildError, match="stack-depth"):
        expand_macro_step_cases(
            stable_leaf_source(domain, "Root.Parent.Child"),
            MacroExpansionOptions(max_stack_depth=1),
        )


@pytest.mark.unittest
def test_sentinel_sources_expand_to_absorb_cases():
    """Terminated and diagnostic macro sources are explicit absorb formals."""
    model = load_state_machine_from_text("state Root;")
    domain = build_bmc_domain(model, bound=1)

    terminated = expand_macro_step_cases(terminated_source(domain))
    diagnostic = expand_macro_step_cases(diagnostic_source(domain))

    assert [
        (case.kind, case.source_state_path, case.target_state_path)
        for case in terminated.cases
    ] == [("absorb", "__terminate__", "__terminate__")]
    assert [
        (case.kind, case.source_state_path, case.target_state_path)
        for case in diagnostic.cases
    ] == [("absorb", "__diagnostic__", "__diagnostic__")]
    assert terminated.cases[0].condition.evaluate({}) is True
    assert diagnostic.cases[0].condition.evaluate({}) is True


@pytest.mark.unittest
def test_root_entry_expands_initial_descent_actions():
    """Root entry starts from an empty stack and records cold-entry actions."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            enter { x = x + 1; }
            state A { during { x = x + 2; } }
            [*] -> A effect { x = x + 4; }
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(entry_source(domain))
    initial = _case_by_kind_target(formal, "initial", "Root.A")

    assert initial.condition.evaluate({}) is True
    assert [
        (block.runtime_role, block.owner_state_path, block.transition_label)
        for block in initial.action_blocks
    ] == [
        ("state_enter", "Root", None),
        ("transition_effect", "Root", "Root::0::INIT_STATE->A"),
        ("leaf_during", "Root.A", None),
    ]


@pytest.mark.unittest
def test_nested_composite_entry_continues_through_initial_child():
    """Hot entry into a composite target expands its own initial transition."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state Parent {
                enter { x = x + 1; }
                state Child { during { x = x + 2; } }
                [*] -> Child effect { x = x + 3; }
            }
            [*] -> Parent;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(entry_source(domain, "Root.Parent"))
    initial = _case_by_kind_target(formal, "initial", "Root.Parent.Child")

    assert [
        (block.runtime_role, block.owner_state_path, block.transition_label)
        for block in initial.action_blocks
    ] == [
        ("transition_effect", "Root.Parent", "Root.Parent::0::INIT_STATE->Child"),
        ("leaf_during", "Root.Parent.Child", None),
    ]


@pytest.mark.unittest
def test_non_pseudo_initial_transition_consumes_plain_before_actions():
    """Composite plain during-before runs before non-pseudo initial children."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state Parent {
                during before { x = x + 10; }
                state Child { during { x = x + 1; } }
                [*] -> Child;
            }
            [*] -> Parent;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(entry_source(domain))
    initial = _case_by_kind_target(formal, "initial", "Root.Parent.Child")

    assert [block.runtime_role for block in initial.action_blocks] == [
        "plain_during_before",
        "leaf_during",
    ]


@pytest.mark.unittest
def test_literal_boolean_guards_are_folded_before_case_expansion():
    """Literal true guards add no atom; literal false guards are pruned."""
    model = load_state_machine_from_text(
        """
        state Root {
            state A;
            state B;
            state C;
            [*] -> A;
            A -> B : if [false];
            A -> C : if [true];
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))

    to_c = _case_by_kind_target(formal, "transition", "Root.C")
    fallback = _case_by_kind_target(formal, "fallback", "Root.A")
    assert to_c.condition.evaluate({}) is True
    assert _conditions(to_c) == set()
    assert all(case.target_state_path != "Root.B" for case in formal.cases)
    assert _conditions(fallback) == {"accepted:%s" % to_c.label}


@pytest.mark.unittest
def test_failed_initial_candidate_becomes_entry_delta_with_initial_guard_metadata():
    """Unstable guarded initial descent is reported as entry semantic delta."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state Parent {
                pseudo state Route;
                state Child;
                [*] -> Route : if [x > 0];
                Route -> Route;
            }
            [*] -> Parent;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(entry_source(domain, "Root.Parent"))
    delta = _case_by_kind_target(formal, "delta", "__diagnostic__")

    assert delta.condition.evaluate({}) is True
    assert {item.name for item in delta.failed_conditions if item.kind == "atom"} == {
        "guard:g0"
    }
    assert [
        (guard.requirement_id, str(guard.expr.to_ast_node()), guard.reason)
        for guard in delta.guard_requirements
    ] == [("g0", "x > 0", "initial_guard")]


@pytest.mark.unittest
def test_failed_parent_continuation_falls_back_with_parent_guard_metadata():
    """Rejected parent continuation is carried into stable fallback diagnostics."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state Parent {
                state Child;
                [*] -> Child;
                Child -> [*];
            }
            pseudo state Route;
            [*] -> Parent;
            Parent -> Route : if [x > 0];
            Route -> Route;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.Parent.Child"))
    fallback = _case_by_kind_target(formal, "fallback", "Root.Parent.Child")

    assert fallback.condition.evaluate({}) is True
    assert {
        item.name for item in fallback.failed_conditions if item.kind == "atom"
    } == {"guard:g0"}
    assert [
        (guard.requirement_id, str(guard.expr.to_ast_node()), guard.reason)
        for guard in fallback.guard_requirements
    ] == [("g0", "x > 0", "parent_continuation_guard")]


@pytest.mark.unittest
def test_exit_to_root_records_root_exit_and_targets_terminate():
    """Exit transitions unwind to the terminate sentinel with exit actions."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            exit { x = x + 10; }
            state A { exit { x = x + 1; } }
            [*] -> A;
            A -> [*];
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    transition = _case_by_kind_target(formal, "transition", "__terminate__")

    assert transition.condition.evaluate({}) is True
    assert [
        (block.runtime_role, block.owner_state_path)
        for block in transition.action_blocks
    ] == [
        ("state_exit", "Root.A"),
        ("state_exit", "Root"),
    ]


@pytest.mark.unittest
def test_pseudo_exit_clears_pending_plain_before_without_running_it():
    """Pseudo exit from a just-entered composite clears pending plain-before work."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state Parent {
                during before { x = x + 100; }
                pseudo state Route;
                [*] -> Route;
                Route -> [*];
            }
            state Done;
            [*] -> Parent;
            Parent -> Done;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(entry_source(domain, "Root.Parent"))
    selected = _case_by_kind_target(formal, "initial", "Root.Done")

    assert [block.runtime_role for block in selected.action_blocks] == []


@pytest.mark.unittest
def test_lifecycle_ref_actions_record_referenced_action_owner_and_name():
    """Lifecycle refs are resolved to the referenced action block."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            enter Shared { x = x + 1; }
            state A {
                enter ref /Shared;
                during { }
            }
            [*] -> A;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(entry_source(domain))
    selected = _case_by_kind_target(formal, "initial", "Root.A")

    assert [
        (block.runtime_role, block.owner_state_path, block.action_name)
        for block in selected.action_blocks
    ] == [
        ("state_enter", "Root", "Root.Shared"),
        ("state_enter", "Root", "Root.Shared"),
    ]


@pytest.mark.unittest
def test_empty_concrete_actions_do_not_create_action_blocks():
    """Empty concrete lifecycle actions are no-ops in the action-block plan."""
    model = load_state_machine_from_text(
        """
        state Root {
            state A {
                enter { }
                during { }
            }
            [*] -> A;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(entry_source(domain))
    selected = _case_by_kind_target(formal, "initial", "Root.A")

    assert selected.action_blocks == ()


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
        "aspect_during_before",
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
    assert [
        (block.block_kind, block.runtime_role) for block in to_done.action_blocks[:5]
    ] == [
        ("state_action", "state_exit"),
        ("transition_effect", "transition_effect"),
        ("transition_effect", "transition_effect"),
        ("state_action", "plain_during_after"),
        ("state_action", "state_exit"),
    ]
    assert [guard.reason for guard in to_b.guard_requirements] == ["pseudo_guard"]
    assert [guard.reason for guard in to_done.guard_requirements] == [
        "pseudo_guard",
        "parent_continuation_guard",
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
        (str(g.expr.to_ast_node()), g.after_action_block_index, g.reason)
        for g in to_b.guard_requirements
    ] == [("x < 13", 0, "pseudo_guard")]
    assert [
        (str(g.expr.to_ast_node()), g.after_action_block_index, g.reason)
        for g in to_done.guard_requirements
    ] == [
        ("x >= 13", 0, "pseudo_guard"),
        ("y >= 30", 2, "parent_continuation_guard"),
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
    """Macro expansion refuses to summarize pseudo loops that depend on effects."""
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

    with pytest.raises(BmcBuildError, match="action-dependent pseudo loop"):
        expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))


@pytest.mark.unittest
def test_failed_guarded_pseudo_candidate_keeps_failed_guard_metadata():
    """Fallback failed conditions keep matching guard requirements."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A;
            pseudo state Route;
            state B;
            A -> Route : if [x > 5];
            Route -> Route;
            Route -> B;
            [*] -> A;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)

    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    fallback = _case_by_kind_target(formal, "fallback", "Root.A")

    assert fallback.failed_conditions
    assert {atom for item in fallback.failed_conditions for atom in item.variables} == {
        "guard:g0"
    }
    assert [
        (guard.requirement_id, guard.reason) for guard in fallback.guard_requirements
    ] == [("g0", "transition_guard")]
