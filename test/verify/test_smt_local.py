"""Tests for SMT-local verification algorithms."""

from textwrap import dedent

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.verify import smt_local
from pyfcstm.verify.registry import REGISTRY
from pyfcstm.verify.smt_local import (
    AlgorithmResult,
    composite_init_guards_incomplete,
    dead_guard,
    effect_contradicts_guard,
    effect_no_op_under_guard,
    enter_postcondition_implies_during_precondition,
    forced_guard_unsat_under_init,
    guard_tautology,
    transition_shadowed_by_predecessor,
)
from pyfcstm.model.expr import BinaryOp, Integer, Variable
from pyfcstm.model.model import IfBlock, IfBlockBranch, Operation, Transition


pytestmark = pytest.mark.unittest

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


def parse_machine(code):
    """Parse DSL through grammar and model validation before using fixtures."""
    ast = parse_with_grammar_entry(dedent(code), "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast)


def variables(machine):
    """Return model variable definitions in stable source order."""
    return tuple(machine.defines.values())


def root_transition(machine, index=-1):
    """Return one root-scope transition."""
    return machine.root_state.transitions[index]


def transition_by_guard(machine, text):
    """Find a transition whose guard text contains a fragment."""
    for state in machine.walk_states():
        for transition in state.transitions:
            if transition.guard is not None and text in str(transition.guard):
                return transition
    raise AssertionError("transition not found")


def timeout_result(*args, **kwargs):
    """Deterministic timeout result for monkeypatched solver helpers."""
    return smt_local.AlgorithmResult(kind="timeout")


def sat_timeout_result(*args, **kwargs):
    """Deterministic timeout-shaped logical helper result."""
    from pyfcstm.solver.logical import SatResult

    return SatResult(kind="timeout")


def assert_single_diag(result, code):
    """Assert that an algorithm emitted exactly one expected raw diagnostic."""
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0]["code"] == code
    return result.diagnostics[0]


def test_raw_transition_payload_covers_root_transition_without_event():
    """Synthetic root transitions have no parent and are still serializable."""
    machine = parse_machine(
        """
        state System {
            state A;
            [*] -> A;
        }
        """
    )
    payload = smt_local._transition_payload(machine.root_state.transitions_from[0])

    assert payload["parent"] is None
    assert payload["from_state"] == "System"
    assert payload["to_state"] == "[*]"
    assert payload["event"] is None


def test_expected_expression_translation_failures_are_normalized():
    """Known expression-to-Z3 failures become algorithm results, not crashes."""
    x = Variable("x")
    missing_value, missing_result = smt_local._expr_to_z3_or_result(x, {})
    bad_op_value, bad_op_result = smt_local._expr_to_z3_or_result(
        BinaryOp(x, "@", Integer(1)),
        {"x": smt_local.z3.Int("x")},
    )
    real_mod_value, real_mod_result = smt_local._expr_to_z3_or_result(
        BinaryOp(x, "%", Integer(2)),
        {"x": smt_local.z3.Real("x")},
    )

    assert missing_value is None
    assert missing_result.kind == "undecidable_skip"
    assert bad_op_value is None
    assert bad_op_result.kind == "undecidable_skip"
    assert real_mod_value is None
    assert real_mod_result.kind == "undecidable_skip"


def test_expected_operation_translation_failures_are_normalized():
    """Operation symbolic execution normalizes expression translation failures."""
    value, result = smt_local._execute_operations_or_result(
        [Operation(var_name="x", expr=Variable("missing"))],
        {"x": smt_local.z3.Int("x")},
    )

    assert value is None
    assert result.kind == "undecidable_skip"


def test_expr_translation_not_implemented_is_unsafe_skip(monkeypatch):
    """Unsupported function translation is normalized as unsafe skip."""

    def raise_not_implemented(*args, **kwargs):
        raise NotImplementedError("unsupported function")

    monkeypatch.setattr(smt_local, "expr_to_z3", raise_not_implemented)

    value, result = smt_local._expr_to_z3_or_result(
        Variable("x"),
        {"x": smt_local.z3.Int("x")},
    )

    assert value is None
    assert result.kind == "unsafe_skip"


def test_operation_translation_not_implemented_is_unsafe_skip(monkeypatch):
    """Operation execution preserves unsupported-function safety skips."""

    def raise_not_implemented(*args, **kwargs):
        raise NotImplementedError("unsupported function")

    monkeypatch.setattr(smt_local, "execute_operations", raise_not_implemented)

    value, result = smt_local._execute_operations_or_result(
        [Operation(var_name="x", expr=Integer(1))],
        {"x": smt_local.z3.Int("x")},
    )

    assert value is None
    assert result.kind == "unsafe_skip"


def test_operation_translation_z3_exception_is_undecidable_skip(monkeypatch):
    """Z3 operation-domain failures are normalized as undecidable skips."""

    def raise_z3_exception(*args, **kwargs):
        raise smt_local.z3.Z3Exception("bad sort")

    monkeypatch.setattr(smt_local, "execute_operations", raise_z3_exception)

    value, result = smt_local._execute_operations_or_result(
        [Operation(var_name="x", expr=Integer(1))],
        {"x": smt_local.z3.Int("x")},
    )

    assert value is None
    assert result.kind == "undecidable_skip"


def test_init_constraint_translation_failure_is_normalized():
    """Invalid variable initializers become an algorithm result."""
    machine = parse_machine(
        """
        def int x = 0;
        state System {
            state A;
            [*] -> A;
        }
        """
    )
    var_def = next(iter(machine.defines.values()))
    var_def.init = Variable("missing")

    value, result = smt_local._build_init_constraints_or_result(
        variables(machine),
        {"x": smt_local.z3.Int("x")},
    )

    assert value is None
    assert result.kind == "undecidable_skip"


def test_guard_translation_failure_is_normalized():
    """Guard translation failure propagates through guard helper."""
    transition = Transition(
        from_state="A",
        to_state="B",
        event=None,
        guard=Variable("missing"),
        effects=[],
    )

    guard, z3_vars, result = smt_local._guard_z3_or_result(transition, ())

    assert guard is None
    assert z3_vars is None
    assert result.kind == "undecidable_skip"


def test_transition_shadowing_helper_reports_unconditional_followers():
    """Any transition after an unconditional catch-all is structurally shadowed."""
    machine = parse_machine(
        """
        state System {
            state A;
            state B;
            state C;
            [*] -> A;
            A -> B;
            A -> C;
        }
        """
    )

    result = transition_shadowed_by_predecessor(machine, variables(machine))

    assert result.kind == "unsat"
    diag = assert_single_diag(result, "W_TRANSITION_SHADOWED")
    assert diag["data"]["reason"] == "unconditional_catchall"


def test_transition_shadowing_helper_starts_unconditional_domain():
    """The first unconditional transition is the catch-all baseline."""
    transition = Transition("A", "B", event=None, guard=None, effects=[])

    assert smt_local._domain_key(transition) == "unconditional"


def test_lifecycle_action_collection_skips_abstract_actions():
    """Abstract lifecycle actions do not contribute concrete operations."""
    machine = parse_machine(
        """
        def int x = 0;
        state System {
            state A {
                enter abstract Setup;
                during { x = x + 1; }
            }
            [*] -> A;
        }
        """
    )
    state = machine.root_state.substates["A"]

    assert smt_local._action_operations(state.on_enters) == []


def test_conditional_collection_includes_if_block_conditions():
    """Operation if-block conditions are first-cycle condition candidates."""
    condition = BinaryOp(Variable("x"), ">", Integer(0))
    operations = [
        IfBlock(
            branches=[
                IfBlockBranch(
                    condition=condition,
                    statements=[Operation(var_name="x", expr=Integer(1))],
                )
            ]
        )
    ]

    assert tuple(smt_local._conditional_conditions_from_operations(operations)) == (
        condition,
    )


def test_event_bool_name_falls_back_for_anonymous_transition():
    """Internal event-bool naming has a deterministic anonymous fallback."""
    transition = Transition("A", "B", event=None, guard=None, effects=[])

    assert smt_local._event_bool_name(transition) == "__event__anonymous"


def test_group2_registry_impls_are_real_function_pointers():
    """Every PR-A4 registry entry points at its raw implementation."""
    expected_impls = {
        "dead_guard": dead_guard,
        "guard_tautology": guard_tautology,
        "forced_guard_unsat_under_init": forced_guard_unsat_under_init,
        "effect_no_op_under_guard": effect_no_op_under_guard,
        "effect_contradicts_guard": effect_contradicts_guard,
        "transition_shadowed_by_predecessor": transition_shadowed_by_predecessor,
        "enter_postcondition_implies_during_precondition": (
            enter_postcondition_implies_during_precondition
        ),
        "composite_init_guards_incomplete": composite_init_guards_incomplete,
    }

    for name in GROUP2_SMT_LOCAL:
        assert REGISTRY[name].impl is expected_impls[name]


class TestDeadGuard:
    """Test dead guard detection."""

    def test_triggers_for_unsatisfiable_guard(self):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x > 5 && x < 3];
            }
            """
        )

        result = dead_guard(root_transition(machine), variables(machine))

        assert result.kind == "unsat"
        assert_single_diag(result, "W_DEAD_GUARD")

    def test_does_not_trigger_for_satisfiable_guard(self):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x > 5];
            }
            """
        )

        result = dead_guard(root_transition(machine), variables(machine))

        assert result == AlgorithmResult(kind="sat")

    def test_timeout_propagates(self, monkeypatch):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x > 0];
            }
            """
        )
        monkeypatch.setattr(smt_local, "is_sat", sat_timeout_result)

        result = dead_guard(
            root_transition(machine), variables(machine), smt_timeout_ms=1
        )

        assert result == AlgorithmResult(kind="timeout")

    def test_unsafe_guard_skips_solver(self):
        machine = parse_machine(
            """
            def int flags = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [(flags & 1) == 1];
            }
            """
        )

        result = dead_guard(root_transition(machine), variables(machine))

        assert result.kind == "unsafe_skip"
        assert result.reason == "bitwise"


class TestGuardTautology:
    """Test tautological guard detection."""

    def test_triggers_for_tautological_guard(self):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x >= 0 || x < 0];
            }
            """
        )

        result = guard_tautology(root_transition(machine), variables(machine))

        assert result.kind == "unsat"
        assert_single_diag(result, "W_GUARD_TAUTOLOGY")

    def test_does_not_trigger_for_non_tautological_guard(self):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x > 0];
            }
            """
        )

        result = guard_tautology(root_transition(machine), variables(machine))

        assert result == AlgorithmResult(kind="sat")

    def test_timeout_propagates(self, monkeypatch):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x > 0];
            }
            """
        )
        monkeypatch.setattr(smt_local, "is_sat", sat_timeout_result)

        result = guard_tautology(
            root_transition(machine), variables(machine), smt_timeout_ms=1
        )

        assert result == AlgorithmResult(kind="timeout")

    def test_unsafe_guard_skips_solver(self):
        machine = parse_machine(
            """
            def int flags = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [(flags << 1) > 0];
            }
            """
        )

        result = guard_tautology(root_transition(machine), variables(machine))

        assert result.kind == "unsafe_skip"
        assert result.reason == "bitwise"


class TestForcedGuardUnsatUnderInit:
    """Test forced transition guard checks under initial values."""

    def test_triggers_for_forced_guard_false_at_init(self):
        machine = parse_machine(
            """
            def int counter = 0;
            def int threshold = 0;
            state System {
                state A {
                    state Sub1;
                    state Sub2;
                    [*] -> Sub1;
                    Sub1 -> Sub2;
                }
                state B;
                [*] -> A;
                !A -> B : if [counter > threshold];
            }
            """
        )
        transition = transition_by_guard(machine, "counter > threshold")

        result = forced_guard_unsat_under_init(transition, variables(machine))

        assert result.kind == "unsat"
        assert_single_diag(result, "W_FORCED_GUARD_UNSAT")

    def test_does_not_trigger_when_forced_guard_true_at_init(self):
        machine = parse_machine(
            """
            def int counter = 5;
            def int threshold = 0;
            state System {
                state A {
                    state Sub1;
                    state Sub2;
                    [*] -> Sub1;
                    Sub1 -> Sub2;
                }
                state B;
                [*] -> A;
                !A -> B : if [counter > threshold];
            }
            """
        )
        transition = transition_by_guard(machine, "counter > threshold")

        result = forced_guard_unsat_under_init(transition, variables(machine))

        assert result == AlgorithmResult(kind="sat")

    def test_timeout_propagates(self, monkeypatch):
        machine = parse_machine(
            """
            def int counter = 5;
            def int threshold = 0;
            state System {
                state A {
                    state Sub1;
                    state Sub2;
                    [*] -> Sub1;
                    Sub1 -> Sub2;
                }
                state B;
                [*] -> A;
                !A -> B : if [counter > threshold];
            }
            """
        )
        monkeypatch.setattr(smt_local, "is_sat", sat_timeout_result)

        result = forced_guard_unsat_under_init(
            transition_by_guard(machine, "counter > threshold"),
            variables(machine),
            smt_timeout_ms=1,
        )

        assert result == AlgorithmResult(kind="timeout")

    def test_unsafe_guard_skips_solver(self):
        machine = parse_machine(
            """
            def int flags = 0;
            state System {
                state A {
                    state Sub1;
                    state Sub2;
                    [*] -> Sub1;
                    Sub1 -> Sub2;
                }
                state B;
                [*] -> A;
                !A -> B : if [(flags ^ 1) == 0];
            }
            """
        )

        result = forced_guard_unsat_under_init(
            transition_by_guard(machine, "flags ^ 1"),
            variables(machine),
        )

        assert result.kind == "unsafe_skip"
        assert result.reason == "bitwise"


class TestEffectNoOpUnderGuard:
    """Test semantic no-op effect checks."""

    def test_triggers_for_semantic_no_op_effect(self):
        machine = parse_machine(
            """
            def int x = 0;
            def int y = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x > 0] effect { x = x + y - y; };
            }
            """
        )

        result = effect_no_op_under_guard(root_transition(machine), variables(machine))

        assert result.kind == "unsat"
        assert_single_diag(result, "W_EFFECT_SMT_NO_OP")

    def test_does_not_trigger_when_effect_can_change_state(self):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x > 0] effect { x = x + 1; };
            }
            """
        )

        result = effect_no_op_under_guard(root_transition(machine), variables(machine))

        assert result == AlgorithmResult(kind="sat")

    def test_timeout_propagates(self, monkeypatch):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x > 0] effect { x = x + 1; };
            }
            """
        )
        monkeypatch.setattr(smt_local, "is_sat", sat_timeout_result)

        result = effect_no_op_under_guard(root_transition(machine), variables(machine))

        assert result == AlgorithmResult(kind="timeout")

    def test_unsafe_effect_skips_solver(self):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [x > 0] effect { x = x << 1; };
            }
            """
        )

        result = effect_no_op_under_guard(root_transition(machine), variables(machine))

        assert result.kind == "unsafe_skip"
        assert result.reason == "bitwise"


class TestEffectContradictsGuard:
    """Test effect/guard contradiction checks."""

    def test_triggers_when_effect_makes_guard_false(self):
        machine = parse_machine(
            """
            def int counter = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [counter > 0] effect { counter = 0; };
            }
            """
        )

        result = effect_contradicts_guard(root_transition(machine), variables(machine))

        assert result.kind == "unsat"
        assert_single_diag(result, "I_EFFECT_GUARD_CONTRADICT")

    def test_does_not_trigger_when_guard_can_still_hold_after_effect(self):
        machine = parse_machine(
            """
            def int counter = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [counter > 0] effect { counter = counter + 1; };
            }
            """
        )

        result = effect_contradicts_guard(root_transition(machine), variables(machine))

        assert result == AlgorithmResult(kind="sat")

    def test_timeout_propagates(self, monkeypatch):
        machine = parse_machine(
            """
            def int counter = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [counter > 0] effect { counter = counter + 1; };
            }
            """
        )
        calls = []

        def feasible_then_timeout(*args, **kwargs):
            from pyfcstm.solver.logical import SatResult

            calls.append(args)
            if len(calls) == 1:
                return SatResult(kind="sat")
            return SatResult(kind="timeout")

        monkeypatch.setattr(smt_local, "is_sat", feasible_then_timeout)

        result = effect_contradicts_guard(root_transition(machine), variables(machine))

        assert result == AlgorithmResult(kind="timeout")
        assert len(calls) == 2

    def test_dead_guard_case_does_not_emit_effect_contradiction(self):
        machine = parse_machine(
            """
            def int counter = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [counter > 0 && counter < 0] effect { counter = 0; };
            }
            """
        )

        result = effect_contradicts_guard(root_transition(machine), variables(machine))

        assert result == AlgorithmResult(kind="sat")

    def test_unsafe_effect_skips_solver(self):
        machine = parse_machine(
            """
            def int counter = 0;
            state System {
                state A;
                state B;
                [*] -> A;
                A -> B : if [counter > 0] effect { counter = counter ** counter; };
            }
            """
        )

        result = effect_contradicts_guard(root_transition(machine), variables(machine))

        assert result.kind == "unsafe_skip"
        assert result.reason == "double_var_power"


class TestTransitionShadowedByPredecessor:
    """Test transition shadowing detection."""

    def test_triggers_for_guard_shadowing(self):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                state C;
                [*] -> A;
                A -> B : if [x > 0];
                A -> C : if [x > 1];
            }
            """
        )

        result = transition_shadowed_by_predecessor(machine, variables(machine))

        assert result.kind == "unsat"
        diag = assert_single_diag(result, "W_TRANSITION_SHADOWED")
        assert diag["data"]["reason"] == "guard_shadow"

    def test_does_not_trigger_for_complementary_guards(self):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                state C;
                [*] -> A;
                A -> B : if [x > 5];
                A -> C : if [x <= 5];
            }
            """
        )

        result = transition_shadowed_by_predecessor(machine, variables(machine))

        assert result == AlgorithmResult(kind="sat")

    def test_timeout_propagates_when_no_shadow_diagnostic_exists(self, monkeypatch):
        machine = parse_machine(
            """
            def int x = 0;
            state System {
                state A;
                state B;
                state C;
                [*] -> A;
                A -> B : if [x > 5];
                A -> C : if [x <= 5];
            }
            """
        )
        monkeypatch.setattr(smt_local, "is_sat", sat_timeout_result)

        result = transition_shadowed_by_predecessor(machine, variables(machine))

        assert result == AlgorithmResult(kind="timeout")

    def test_unsafe_guard_skips_solver(self):
        machine = parse_machine(
            """
            def int flags = 0;
            state System {
                state A;
                state B;
                state C;
                [*] -> A;
                A -> B : if [flags > 0];
                A -> C : if [(flags & 1) == 1];
            }
            """
        )

        result = transition_shadowed_by_predecessor(machine, variables(machine))

        assert result.kind == "unsafe_skip"
        assert result.reason == "bitwise"

    def test_event_duplicate_shadowing_is_structural(self):
        machine = parse_machine(
            """
            state System {
                event Tick;
                state A;
                state B;
                state C;
                [*] -> A;
                A -> B : Tick;
                A -> C : Tick;
            }
            """
        )

        result = transition_shadowed_by_predecessor(machine, variables(machine))

        assert result.kind == "unsat"
        diag = assert_single_diag(result, "W_TRANSITION_SHADOWED")
        assert diag["data"]["reason"] == "duplicate_event"


class TestEnterPostconditionImpliesDuringPrecondition:
    """Test first-cycle lifecycle coupling checks."""

    def test_triggers_when_enter_determines_during_ternary_true_branch(self):
        machine = parse_machine(
            """
            def int mode = 1;
            def int x = 0;
            state System {
                state Idle {
                    enter { mode = 1; }
                    during { x = (mode == 1) ? 10 : 20; }
                }
                [*] -> Idle;
            }
            """
        )
        state = machine.root_state.substates["Idle"]

        result = enter_postcondition_implies_during_precondition(
            state, variables(machine)
        )

        assert result.kind == "unsat"
        diag = assert_single_diag(result, "I_ENTER_DURING_CONTRADICT")
        assert diag["data"]["branch_taken"] == "true"

    def test_does_not_trigger_without_during_conditional(self):
        machine = parse_machine(
            """
            def int mode = 0;
            def int x = 0;
            state System {
                state Idle {
                    enter { x = 1; }
                    during { x = mode + 1; }
                }
                [*] -> Idle;
            }
            """
        )
        state = machine.root_state.substates["Idle"]

        result = enter_postcondition_implies_during_precondition(
            state, variables(machine)
        )

        assert result == AlgorithmResult(kind="sat")

    def test_timeout_propagates_when_no_diagnostic_exists(self, monkeypatch):
        machine = parse_machine(
            """
            def int mode = 0;
            def int external = 0;
            def int x = 0;
            state System {
                state Idle {
                    enter { x = 1; }
                    during { x = (external > mode) ? 10 : 20; }
                }
                [*] -> Idle;
            }
            """
        )
        state = machine.root_state.substates["Idle"]
        monkeypatch.setattr(smt_local, "is_sat", sat_timeout_result)

        result = enter_postcondition_implies_during_precondition(
            state,
            variables(machine),
        )

        assert result == AlgorithmResult(kind="timeout")

    def test_unsafe_during_condition_skips_solver(self):
        machine = parse_machine(
            """
            def int flags = 1;
            def int x = 0;
            state System {
                state Idle {
                    enter { x = 1; }
                    during { x = ((flags & 1) == 1) ? 10 : 20; }
                }
                [*] -> Idle;
            }
            """
        )
        state = machine.root_state.substates["Idle"]

        result = enter_postcondition_implies_during_precondition(
            state, variables(machine)
        )

        assert result.kind == "unsafe_skip"
        assert result.reason == "bitwise"


class TestCompositeInitGuardsIncomplete:
    """Test composite initial-transition coverage checks."""

    def test_triggers_for_guard_coverage_gap(self):
        machine = parse_machine(
            """
            def int x = 0;
            state Root {
                state A;
                state B;
                [*] -> A : if [x > 0];
                [*] -> B : if [x < 0];
            }
            """
        )

        result = composite_init_guards_incomplete(machine, variables(machine))

        assert result.kind == "sat"
        assert_single_diag(result, "W_COMPOSITE_INIT_INCOMPLETE")

    def test_does_not_trigger_for_complete_guard_coverage(self):
        machine = parse_machine(
            """
            def int x = 0;
            state Root {
                state A;
                state B;
                [*] -> A : if [x >= 0];
                [*] -> B : if [x < 0];
            }
            """
        )

        result = composite_init_guards_incomplete(machine, variables(machine))

        assert result == AlgorithmResult(kind="unsat")

    def test_timeout_propagates_when_no_diagnostic_exists(self, monkeypatch):
        machine = parse_machine(
            """
            def int x = 0;
            state Root {
                state A;
                state B;
                [*] -> A : if [x >= 0];
                [*] -> B : if [x < 0];
            }
            """
        )
        monkeypatch.setattr(smt_local, "is_sat", sat_timeout_result)

        result = composite_init_guards_incomplete(machine, variables(machine))

        assert result == AlgorithmResult(kind="timeout")

    def test_unsafe_init_guard_skips_solver(self):
        machine = parse_machine(
            """
            def int flags = 0;
            state Root {
                state A;
                state B;
                [*] -> A : if [(flags & 1) == 1];
                [*] -> B : if [flags == 0];
            }
            """
        )

        result = composite_init_guards_incomplete(machine, variables(machine))

        assert result.kind == "unsafe_skip"
        assert result.reason == "bitwise"

    def test_nested_composite_reports_nested_state(self):
        machine = parse_machine(
            """
            def int x = 0;
            state Root {
                state Outer {
                    state Inner1;
                    state Inner2;
                    [*] -> Inner1 : if [x > 0];
                    [*] -> Inner2 : if [x < 0];
                }
                [*] -> Outer;
            }
            """
        )

        result = composite_init_guards_incomplete(machine, variables(machine))

        assert result.kind == "sat"
        diag = assert_single_diag(result, "W_COMPOSITE_INIT_INCOMPLETE")
        assert diag["data"]["state"] == "Root.Outer"


def test_algorithms_complete_under_simple_performance_smoke(benchmark):
    """All eight algorithms stay fast on representative tiny fixtures."""
    guard_machine = parse_machine(
        """
        def int x = 1;
        def int y = 0;
        state System {
            state A;
            state B;
            state C;
            [*] -> A;
            A -> B : if [x > 0] effect { y = y + 1; };
            A -> C : if [x <= 0];
        }
        """
    )
    lifecycle_machine = parse_machine(
        """
        def int mode = 1;
        def int x = 0;
        state System {
            state Idle {
                enter { mode = 1; }
                during { x = (mode == 1) ? 10 : 20; }
            }
            [*] -> Idle;
        }
        """
    )
    composite_machine = parse_machine(
        """
        def int x = 0;
        state Root {
            state A;
            state B;
            [*] -> A : if [x >= 0];
            [*] -> B : if [x < 0];
        }
        """
    )
    guard_transition = guard_machine.root_state.transitions[1]
    lifecycle_state = lifecycle_machine.root_state.substates["Idle"]

    def run_all():
        dead_guard(guard_transition, variables(guard_machine))
        guard_tautology(guard_transition, variables(guard_machine))
        forced_guard_unsat_under_init(guard_transition, variables(guard_machine))
        effect_no_op_under_guard(guard_transition, variables(guard_machine))
        effect_contradicts_guard(guard_transition, variables(guard_machine))
        transition_shadowed_by_predecessor(guard_machine, variables(guard_machine))
        enter_postcondition_implies_during_precondition(
            lifecycle_state,
            variables(lifecycle_machine),
        )
        composite_init_guards_incomplete(
            composite_machine, variables(composite_machine)
        )

    benchmark(run_all)
