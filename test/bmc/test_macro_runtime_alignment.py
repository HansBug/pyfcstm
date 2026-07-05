"""Runtime-alignment tests for macro-step path expansion."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyfcstm.bmc import build_bmc_domain, entry_source, stable_leaf_source
from pyfcstm.bmc.expand import expand_macro_step_cases
from pyfcstm.model import IfBlock, Operation, load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

_FIXTURE = Path(__file__).with_name("fixtures") / "macro_runtime_alignment.fcstm"


def _execute_statements(statements, vars_):
    for statement in statements:
        if isinstance(statement, Operation):
            vars_[statement.var_name] = statement.expr(**vars_)
            continue
        if isinstance(statement, IfBlock):
            selected = False
            for branch in statement.branches:
                if branch.condition is None or bool(branch.condition(**vars_)):
                    _execute_statements(branch.statements, vars_)
                    selected = True
                    break
            if selected:
                continue
            continue
        raise AssertionError("unsupported test statement %r" % (statement,))


def _replay_action_prefix(case, initial_vars, block_count=None):
    vars_ = dict(initial_vars)
    blocks = (
        case.action_blocks if block_count is None else case.action_blocks[:block_count]
    )
    for block in blocks:
        if not block.is_abstract:
            _execute_statements(block.operations, vars_)
    return vars_


def _eval_condition(template, case, registry, initial_vars, events, active=None):
    if active is None:
        active = set()
    if template.kind == "true":
        return True
    if template.kind == "false":
        return False
    if template.kind == "not":
        return not _eval_condition(
            template.operands[0], case, registry, initial_vars, events, active
        )
    if template.kind == "and":
        return all(
            _eval_condition(item, case, registry, initial_vars, events, active)
            for item in template.operands
        )
    if template.kind == "or":
        return any(
            _eval_condition(item, case, registry, initial_vars, events, active)
            for item in template.operands
        )
    atom = template.name
    assert atom is not None
    if atom.startswith("event:"):
        return atom[len("event:") :] in events
    if atom.startswith("guard:"):
        requirement_id = atom[len("guard:") :]
        guards = {item.requirement_id: item for item in case.guard_requirements}
        guard = guards[requirement_id]
        anchored_vars = _replay_action_prefix(
            case, initial_vars, guard.after_action_block_index
        )
        return bool(guard.expr(**anchored_vars))
    if atom.startswith("accepted:"):
        label = atom[len("accepted:") :]
        if label in active:
            raise AssertionError("recursive accepted atom %s" % label)
        active.add(label)
        accepted_case = registry[label]
        result = _eval_condition(
            accepted_case.condition,
            accepted_case,
            registry,
            initial_vars,
            events,
            active,
        )
        active.remove(label)
        return result
    raise AssertionError("unexpected atom %s" % atom)


def _selected_case(formal, initial_vars, events):
    registry = {case.label: case for case in formal.cases}
    selected = [
        case
        for case in formal.cases
        if _eval_condition(case.condition, case, registry, initial_vars, events)
    ]
    assert len(selected) == 1, [case.label for case in selected]
    return selected[0]


def _runtime_cycle(model, state, initial_vars, events):
    runtime = SimulationRuntime(
        model, initial_state=state, initial_vars=dict(initial_vars)
    )
    runtime.cycle(list(events))
    return ".".join(runtime.current_state.path), dict(runtime.vars)


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("initial_vars", "events", "expected_target"),
    [
        ({"x": 0, "y": 0}, ("Root.System.A.Tick",), "Root.System.B"),
        ({"x": 11, "y": 0}, ("Root.System.A.Tick",), "Root.Done"),
        ({"x": 11, "y": -200}, ("Root.System.A.Tick",), "Root.System.A"),
        (
            {"x": 0, "y": 0},
            ("Root.System.A.Tick", "Root.System.Trap.Arm"),
            "Root.System.Trap.TrapLeaf",
        ),
        ({"x": 4, "y": 5}, (), "Root.System.A"),
    ],
)
def test_stable_a_cases_select_same_target_and_actions_as_runtime(
    initial_vars,
    events,
    expected_target,
):
    """Flat path cases align with runtime transition validation and fallback."""
    model = load_state_machine_from_text(_FIXTURE.read_text())
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.System.A"))

    case = _selected_case(formal, initial_vars, events)
    replayed_vars = _replay_action_prefix(case, initial_vars)
    runtime_state, runtime_vars = _runtime_cycle(
        model,
        "Root.System.A",
        initial_vars,
        events,
    )

    assert case.target_state_path == expected_target
    assert runtime_state == expected_target
    assert replayed_vars == runtime_vars


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("initial_vars", "expected_kind", "expected_target"),
    [
        ({"x": 0, "y": 0}, "initial", "Root.System.B"),
        ({"x": 13, "y": 8}, "initial", "Root.Done"),
        ({"x": 13, "y": 0}, "delta", "__diagnostic__"),
    ],
)
def test_hot_route_entry_cases_use_runtime_guard_anchors(
    initial_vars,
    expected_kind,
    expected_target,
):
    """Hot pseudo entry selects B, Done, or semantic delta by anchored guards."""
    model = load_state_machine_from_text(_FIXTURE.read_text())
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(entry_source(domain, "Root.System.Route"))

    case = _selected_case(formal, initial_vars, ())

    assert case.kind == expected_kind
    assert case.target_state_path == expected_target
    if case.kind != "delta":
        replayed_vars = _replay_action_prefix(case, initial_vars)
        runtime_state, runtime_vars = _runtime_cycle(
            model,
            "Root.System.Route",
            initial_vars,
            (),
        )
        assert runtime_state == expected_target
        assert replayed_vars == runtime_vars


@pytest.mark.unittest
def test_runtime_alignment_condition_has_no_action_if_atoms():
    """Action-local conditions stay inside operations and not case conditions."""
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
    case = formal.cases[0]

    assert case.condition.variables == ()
    assert isinstance(case.action_blocks[0].operations[0], IfBlock)
    assert _replay_action_prefix(case, {"x": 2}) == {"x": 3}
    assert _replay_action_prefix(case, {"x": 0}) == {"x": -1}


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("events", "expected_target", "expected_roles", "expected_x"),
    [
        (
            (),
            "Root.A",
            [
                "aspect_during_before",
                "aspect_during_before",
                "leaf_during",
                "leaf_during",
                "aspect_during_after",
                "aspect_during_after",
            ],
            111107,
        ),
        (
            ("Root.Go",),
            "Root.B",
            [
                "state_exit",
                "state_exit",
                "state_enter",
                "state_enter",
                "aspect_during_before",
                "aspect_during_before",
                "leaf_during",
                "leaf_during",
                "aspect_during_after",
                "aspect_during_after",
            ],
            111145,
        ),
    ],
)
def test_multiple_lifecycle_actions_preserve_runtime_order(
    events,
    expected_target,
    expected_roles,
    expected_x,
):
    """Repeated actions in the same lifecycle stage remain ordered blocks."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Go;
            >> during before { x = x + 100; }
            >> during before { x = x + 1000; }
            >> during after { x = x + 10000; }
            >> during after { x = x + 100000; }
            state A {
                enter { x = x + 1; }
                enter { x = x + 2; }
                during { x = x + 3; }
                during { x = x + 4; }
                exit { x = x + 5; }
                exit { x = x + 6; }
            }
            state B {
                enter { x = x + 7; }
                enter { x = x + 8; }
                during { x = x + 9; }
                during { x = x + 10; }
            }
            [*] -> A;
            A -> B : Go;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))

    case = _selected_case(formal, {"x": 0}, events)
    runtime_state, runtime_vars = _runtime_cycle(model, "Root.A", {"x": 0}, events)

    assert case.target_state_path == expected_target
    assert [block.runtime_role for block in case.action_blocks] == expected_roles
    assert _replay_action_prefix(case, {"x": 0}) == {"x": expected_x}
    assert runtime_state == expected_target
    assert runtime_vars == {"x": expected_x}


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("events", "expected_target", "expected_actions"),
    [
        (
            (),
            "Root.A",
            [
                ("aspect_during_before", "Root.RootBefore"),
                ("leaf_during", "Root.A.ADuring"),
                ("aspect_during_after", "Root.RootAfter"),
            ],
        ),
        (
            ("Root.Go",),
            "Root.B",
            [
                ("state_exit", "Root.A.AExit"),
                ("aspect_during_before", "Root.RootBefore"),
                ("aspect_during_after", "Root.RootAfter"),
            ],
        ),
    ],
)
def test_abstract_actions_are_recorded_as_noop_occurrence_blocks(
    events,
    expected_target,
    expected_actions,
):
    """Abstract actions remain observable blocks while preserving no-op vars."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Go;
            >> during before abstract RootBefore;
            >> during after abstract RootAfter;
            state A {
                enter abstract AEnter;
                during abstract ADuring;
                exit abstract AExit;
            }
            state B;
            [*] -> A;
            A -> B : Go;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))

    case = _selected_case(formal, {"x": 0}, events)
    runtime_state, runtime_vars = _runtime_cycle(model, "Root.A", {"x": 0}, events)

    assert case.target_state_path == expected_target
    assert [
        (block.runtime_role, block.action_name) for block in case.action_blocks
    ] == expected_actions
    assert all(
        block.is_abstract and block.operations == () for block in case.action_blocks
    )
    assert _replay_action_prefix(case, {"x": 0}) == {"x": 0}
    assert runtime_state == expected_target
    assert runtime_vars == {"x": 0}
