"""BMC witness public API and decoder tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import z3

import pyfcstm.bmc.witness as witness_module
from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
    BmcEventDecodePolicy,
    BmcReplayMismatch,
    BmcReplayResult,
    BmcRuntimeTrace,
    BmcSolveResult,
    BmcWitnessCallRecord,
    BmcWitnessEvent,
    BmcWitnessFrame,
    BmcWitnessStep,
    BmcWitnessTrace,
    build_bmc_core_formula,
    compile_bmc_property,
    decode_bmc_witness,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.bmc.binding import BoundAssumption
from pyfcstm.bmc.query import EventCardinalityAssumption
from pyfcstm.model import OnAspect, OnStage
from pyfcstm.model import load_state_machine_from_text


pytestmark = pytest.mark.unittest


def _compile(dsl_text: str, query_text: str):
    model = load_state_machine_from_text(dsl_text)
    core = build_bmc_core_formula(BmcEngine(model).prepare(query_text))
    return model, compile_bmc_property(core)


def _solve_with_extra(formula, *extra):
    solver = z3.Solver()
    solver.add(formula.solve_formula, *extra)
    assert solver.check() == z3.sat
    return solver.model()


def test_witness_api_is_lazy_exported_from_bmc_package() -> None:
    """The root package exposes the witness layer without eager solver work."""
    assert BmcEventDecodePolicy().include_debug_reads is True
    assert BmcSolveResult.__name__ == "BmcSolveResult"
    assert BmcWitnessTrace.__name__ == "BmcWitnessTrace"
    assert BmcReplayResult.__name__ == "BmcReplayResult"
    assert callable(solve_bmc_property)
    assert callable(decode_bmc_witness)
    assert callable(replay_bmc_witness)


def test_solve_result_decodes_init_sentinel_as_public_json() -> None:
    """Cold-start ``STATE_INIT`` stays out of public witness JSON."""
    model, formula = _compile(
        """
        state Root {
            state A;
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A");',
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    assert result.to_canonical()["has_model"] is True

    trace = decode_bmc_witness(formula, result.model)
    assert trace.frames[0].sentinel == "init"
    assert trace.frames[0].state is None
    assert trace.to_canonical()["frames"][0]["state_id"] is None
    assert replay_bmc_witness(model, trace).ok is True


def test_decode_rejects_non_model_inputs_loudly() -> None:
    """Public decoder validation rejects accidental non-Z3-model objects."""
    _, formula = _compile("state Root;", 'check reach <= 1: active("Root");')
    with pytest.raises(BmcBuildError, match="model must be z3.ModelRef"):
        decode_bmc_witness(formula, object())
    result = solve_bmc_property(formula)
    with pytest.raises(BmcBuildError, match="event_policy"):
        decode_bmc_witness(formula, result.model, event_policy=object())


def test_event_clean_ignores_unrelated_true_model_events() -> None:
    """Replay input events come from selected-case provenance, not all true BoolVars."""
    model, formula = _compile(
        """
        state Root {
            state A {
                event go;
                event noise;
            }
            state B;
            [*] -> A;
            A -> B :: go;
        }
        """,
        'init state("Root.A"); check reach <= 1: active("Root.B");',
    )
    noise = formula.core.symbols.event_input(0, "Root.A.noise")
    model_ref = _solve_with_extra(formula, noise)
    assert z3.is_true(model_ref.eval(noise, model_completion=True))

    trace = decode_bmc_witness(formula, model_ref)
    assert [event.path for event in trace.steps[0].input_events] == ["Root.A.go"]
    assert trace.steps[0].input_events[0].reason == "case_positive"
    assert replay_bmc_witness(model, trace).ok is True


def test_event_clean_preserves_explicit_true_assumption_inputs() -> None:
    """Explicit true event assumptions are replay inputs even when unconsumed."""
    model, formula = _compile(
        """
        state Root {
            event noise;
            state A;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        'assume event("Root.noise", 0) == true;\n'
        'check reach <= 1: active("Root.A");',
    )
    result = solve_bmc_property(formula)
    trace = decode_bmc_witness(formula, result.model)
    assert [(item.path, item.reason) for item in trace.steps[0].input_events] == [
        ("Root.noise", "explicit_true_assumption")
    ]
    replay = replay_bmc_witness(model, trace)
    assert replay.ok is True
    assert replay.runtime_trace.steps[0].unconsumed_events == ("Root.noise",)


def test_response_trigger_support_event_is_sparse_and_replayable() -> None:
    """Response trigger-only events are emitted as deterministic property support."""
    model, formula = _compile(
        """
        state Root {
            event trigger;
            state A;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        "check response <= 1:\n"
        '  trigger event("Root.trigger", current)\n'
        "  -> within 1 terminated();",
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    trace = decode_bmc_witness(formula, result.model)
    assert [(item.path, item.reason) for item in trace.steps[0].input_events] == [
        ("Root.trigger", "property_support")
    ]
    assert replay_bmc_witness(model, trace).ok is True


def test_response_trigger_support_uses_domain_order_for_disjunction() -> None:
    """When several trigger events are true, support selection is stable."""
    model, formula = _compile(
        """
        state Root {
            event alpha;
            event beta;
            state A;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        "check response <= 1:\n"
        '  trigger event("Root.beta", current) || event("Root.alpha", current)\n'
        "  -> within 1 terminated();",
    )
    alpha = formula.core.symbols.event_input(0, "Root.alpha")
    beta = formula.core.symbols.event_input(0, "Root.beta")
    model_ref = _solve_with_extra(formula, alpha, beta)
    trace = decode_bmc_witness(formula, model_ref)
    assert [(item.path, item.reason) for item in trace.steps[0].input_events] == [
        ("Root.alpha", "property_support")
    ]
    assert replay_bmc_witness(model, trace).ok is True


def test_response_trigger_event_scan_ignores_non_event_predicate_atoms() -> None:
    """Property-support event extraction walks mixed trigger ASTs precisely."""
    model, formula = _compile(
        """
        def int x = 0;
        state Root {
            event trigger;
            state A { during abstract Before; }
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        "check response <= 1:\n"
        '  trigger ((true) ? event("Root.trigger", current) : false) '
        '&& called("Root.A.Before") && active("Root.A") '
        "&& !terminated() && x == 0\n"
        "  -> within 1 terminated();",
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"

    trace = decode_bmc_witness(formula, result.model)
    assert [(item.path, item.reason) for item in trace.steps[0].input_events] == [
        ("Root.trigger", "property_support")
    ]
    assert [
        (
            item.action_name,
            item.stage,
            item.role,
            item.state,
            item.active_leaf,
            item.snapshot,
        )
        for item in trace.steps[0].abstract_calls
    ] == [
        (
            "Root.A.Before",
            "during",
            "leaf_during",
            "Root.A",
            "Root.A",
            {"x": 0},
        )
    ]
    assert replay_bmc_witness(model, trace).ok is True


def test_response_trigger_support_does_not_duplicate_explicit_true_inputs() -> None:
    """Existing true replay inputs satisfy response triggers without support noise."""
    model, formula = _compile(
        """
        state Root {
            event trigger;
            state A;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        'assume event("Root.trigger", 0) == true;\n'
        "check response <= 1:\n"
        '  trigger event("Root.trigger", current)\n'
        "  -> within 1 terminated();",
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"

    trace = decode_bmc_witness(formula, result.model)
    assert [
        (item.path, item.reason, item.model_value)
        for item in trace.steps[0].input_events
    ] == [("Root.trigger", "explicit_true_assumption", True)]
    assert replay_bmc_witness(model, trace).ok is True


def test_explicit_true_assumptions_preserve_required_case_events() -> None:
    """Assumption-driven replay inputs do not mask selected transition events."""
    model, formula = _compile(
        """
        state Root {
            event noise;
            state A { event go; }
            state B;
            [*] -> A;
            A -> B :: go;
        }
        """,
        'init state("Root.A");\n'
        'assume event("Root.noise", 0) == true;\n'
        'check reach <= 1: active("Root.B");',
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"

    trace = decode_bmc_witness(formula, result.model)
    assert [
        (item.path, item.reason, item.model_value)
        for item in trace.steps[0].input_events
    ] == [
        ("Root.noise", "explicit_true_assumption", True),
        ("Root.A.go", "case_positive", True),
    ]
    replay = replay_bmc_witness(model, trace)
    assert replay.ok is True
    assert replay.runtime_trace.steps[0].unconsumed_events == ("Root.noise",)


def test_response_trigger_support_can_be_disabled_by_policy() -> None:
    """The event policy can suppress property-support replay inputs."""
    _, formula = _compile(
        """
        state Root {
            event trigger;
            state A;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        "check response <= 1:\n"
        '  trigger event("Root.trigger", current)\n'
        "  -> within 1 terminated();",
    )
    result = solve_bmc_property(formula)
    trace = decode_bmc_witness(
        formula,
        result.model,
        event_policy=BmcEventDecodePolicy(include_property_support=False),
    )
    assert trace.steps[0].input_events == ()


def test_solve_property_reports_incomplete_response_diagnostics() -> None:
    """Response objectives expose incomplete-bound solves separately."""
    _, formula = _compile(
        """
        state Root {
            event trigger;
            state A;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        "check response <= 1:\n"
        '  trigger event("Root.trigger", current)\n'
        "  -> within 2 terminated();",
    )
    result = solve_bmc_property(formula)
    assert result.status == "unsat"
    assert result.model is None
    assert result.incomplete_status == "sat"
    assert result.incomplete_model is not None
    assert result.to_canonical()["has_incomplete_model"] is True
    assert any(item.startswith("incomplete_elapsed_ms=") for item in result.diagnostics)


@pytest.mark.parametrize("bad_timeout", [0, -1, True, 1.5])
def test_solve_property_rejects_invalid_timeout_values(bad_timeout) -> None:
    """The public solver validates timeout values before touching Z3."""
    _, formula = _compile("state Root;", 'check reach <= 1: active("Root");')
    with pytest.raises(BmcBuildError, match="timeout_ms"):
        solve_bmc_property(formula, timeout_ms=bad_timeout)


def test_solver_unknown_and_timeout_paths_are_structured(monkeypatch) -> None:
    """Solver status mapping covers timeout and non-timeout unknown results."""

    class FakeSolver:
        def __init__(self, status, reason):
            self.status = status
            self.reason = reason
            self.timeout = None

        def set(self, *, timeout):
            self.timeout = timeout

        def add(self, *exprs):
            self.exprs = exprs

        def check(self):
            return self.status

        def reason_unknown(self):
            return self.reason

    timeout_solver = FakeSolver(z3.unknown, "timeout")
    monkeypatch.setattr(witness_module.z3, "Solver", lambda: timeout_solver)
    assert witness_module._solve(z3.BoolVal(True), timeout_ms=5)[:3] == (
        "timeout",
        None,
        "timeout",
    )
    assert timeout_solver.timeout == 5

    unknown_solver = FakeSolver(z3.unknown, "canceled")
    monkeypatch.setattr(witness_module.z3, "Solver", lambda: unknown_solver)
    assert witness_module._solve(z3.BoolVal(True), timeout_ms=None)[:3] == (
        "unknown",
        None,
        "canceled",
    )


def test_internal_z3_decode_guards_are_loud() -> None:
    """Malformed Z3 values fail with internal witness bug diagnostics."""
    solver = z3.Solver()
    solver.add(z3.BoolVal(True))
    assert solver.check() == z3.sat
    model = solver.model()

    assert witness_module._z3_number_value(model, z3.RealVal("2"), "int") == 2
    for helper, expr, message in [
        (witness_module._z3_bool_value, z3.IntVal(1), "Boolean"),
        (witness_module._z3_int_value, z3.BoolVal(True), "integer"),
        (witness_module._z3_number_value, z3.BoolVal(True), "numeric"),
    ]:
        with pytest.raises(BmcBuildError, match=message) as error_info:
            helper(model, expr)
        assert "internal BMC witness consistency error" in str(error_info.value)
        assert "https://github.com/HansBug/pyfcstm/issues/new" in str(error_info.value)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda formula: BmcSolveResult(object(), "sat"), "formula must"),
        (lambda formula: BmcSolveResult(formula, "maybe"), "status must"),
        (lambda formula: BmcSolveResult(formula, "sat", model=object()), "model must"),
        (
            lambda formula: BmcSolveResult(formula, "sat", incomplete_status="maybe"),
            "incomplete_status",
        ),
        (
            lambda formula: BmcSolveResult(formula, "sat", incomplete_model=object()),
            "incomplete_model",
        ),
        (
            lambda formula: BmcSolveResult(formula, "sat", elapsed_ms="slow"),
            "elapsed_ms",
        ),
        (
            lambda formula: BmcSolveResult(formula, "sat", timeout_ms=0),
            "timeout_ms",
        ),
        (
            lambda formula: BmcSolveResult(formula, "sat", diagnostics=(1,)),
            "diagnostics",
        ),
    ],
)
def test_solve_result_rejects_invalid_public_payloads(factory, message) -> None:
    """Public solve-result construction fails loudly for malformed payloads."""
    _, formula = _compile("state Root;", 'check reach <= 1: active("Root");')
    with pytest.raises(BmcBuildError, match=message):
        factory(formula)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: BmcEventDecodePolicy(include_debug_reads="yes"),
            "include_debug_reads",
        ),
        (
            lambda: BmcEventDecodePolicy(include_property_support="yes"),
            "include_property_support",
        ),
        (lambda: BmcWitnessEvent("", "case_positive"), "event path"),
        (lambda: BmcWitnessEvent("Root.Go", "unknown"), "Unsupported witness event"),
        (lambda: BmcWitnessEvent("Root.Go", "case_positive", "true"), "model_value"),
        (
            lambda: BmcWitnessCallRecord(-1, "A", "during", "role", "S", "S"),
            "ordinal",
        ),
        (
            lambda: BmcWitnessCallRecord(0, "", "during", "role", "S", "S"),
            "action_name",
        ),
        (
            lambda: BmcWitnessCallRecord(0, "A", "during", "role", "S", "S", ""),
            "named_ref",
        ),
        (
            lambda: BmcWitnessCallRecord(
                0, "A", "during", "role", "S", "S", snapshot=()
            ),
            "snapshot",
        ),
        (lambda: BmcWitnessFrame(True, None, None, "init", False, {}), "frame index"),
        (lambda: BmcWitnessFrame(0, True, None, "init", False, {}), "state_id"),
        (lambda: BmcWitnessFrame(0, None, "", "init", False, {}), "state"),
        (lambda: BmcWitnessFrame(0, None, None, "diag", False, {}), "sentinel"),
        (lambda: BmcWitnessFrame(0, None, None, "init", "no", {}), "terminated"),
        (lambda: BmcWitnessFrame(0, None, None, "init", False, ()), "vars"),
        (
            lambda: BmcWitnessStep(
                True, 0, 1, "c", "fallback", "fallback_gamma", None, None, False, True
            ),
            "index",
        ),
        (
            lambda: BmcWitnessStep(
                0, 0, 1, "", "fallback", "fallback_gamma", None, None, False, True
            ),
            "case_label",
        ),
        (
            lambda: BmcWitnessStep(
                0, 0, 1, "c", "fallback", "fallback_gamma", "", None, False, True
            ),
            "source_state",
        ),
        (
            lambda: BmcWitnessStep(
                0, 0, 1, "c", "fallback", "fallback_gamma", None, None, "no", True
            ),
            "delta",
        ),
        (
            lambda: BmcWitnessStep(
                0,
                0,
                1,
                "c",
                "fallback",
                "fallback_gamma",
                None,
                None,
                False,
                True,
                input_events=(object(),),
            ),
            "input_events",
        ),
        (
            lambda: BmcWitnessStep(
                0,
                0,
                1,
                "c",
                "fallback",
                "fallback_gamma",
                None,
                None,
                False,
                True,
                event_reads=(object(),),
            ),
            "event_reads",
        ),
        (
            lambda: BmcWitnessStep(
                0,
                0,
                1,
                "c",
                "fallback",
                "fallback_gamma",
                None,
                None,
                False,
                True,
                abstract_calls=(object(),),
            ),
            "abstract_calls",
        ),
        (lambda: BmcWitnessTrace({}, {}, {}, (), (), schema_version="v2"), "schema"),
        (lambda: BmcWitnessTrace((), {}, {}, (), ()), "property"),
        (lambda: BmcWitnessTrace({}, (), {}, (), ()), "solver"),
        (lambda: BmcWitnessTrace({}, {}, (), (), ()), "initial"),
        (lambda: BmcWitnessTrace({}, {}, {}, (object(),), ()), "frames"),
        (lambda: BmcWitnessTrace({}, {}, {}, (), (object(),)), "steps"),
        (lambda: BmcWitnessTrace({}, {}, {}, (), (), diagnostics=(1,)), "diagnostics"),
        (lambda: BmcReplayResult(object(), BmcRuntimeTrace((), ())), "witness"),
        (
            lambda: BmcReplayResult(BmcWitnessTrace({}, {}, {}, (), ()), object()),
            "runtime_trace",
        ),
        (
            lambda: BmcReplayResult(
                BmcWitnessTrace({}, {}, {}, (), ()),
                BmcRuntimeTrace((), ()),
                (object(),),
            ),
            "mismatches",
        ),
    ],
)
def test_witness_public_dataclasses_reject_invalid_payloads(factory, message) -> None:
    """Witness JSON/replay dataclasses validate their public payload shape."""
    with pytest.raises(BmcBuildError, match=message):
        factory()


def test_abstract_call_role_internal_consistency_errors_are_loud() -> None:
    """Broken model metadata cannot silently corrupt replay call roles."""

    class FakeContext:
        named_ref = None
        abstract_target = "Root.A.Touch"
        action_name = "Root.A.Touch"
        call_stage = "during"
        action_stage = "during"

        def get_full_state_path(self):
            return "Root.A"

    resolver = witness_module._AbstractCallRoleResolver(
        {"Root.A.Touch": "leaf_during"},
        {("Root.A.Touch", "during", "Root.A"): ["leaf_during"]},
    )
    with pytest.raises(BmcBuildError, match="exceeded replay role metadata"):
        resolver.resolve(FakeContext(), occurrence_index=1)

    resolver = witness_module._AbstractCallRoleResolver({}, {})
    with pytest.raises(BmcBuildError, match="no replay role metadata"):
        resolver.resolve(FakeContext())

    bad_aspect = OnAspect(
        "during",
        "around",
        "BadAspect",
        None,
        [],
        True,
        ("Root", "BadAspect"),
    )
    with pytest.raises(BmcBuildError, match="Unsupported aspect action role"):
        witness_module._role_for_action(bad_aspect)

    bad_stage = OnStage("pause", None, "BadStage", None, [], True, ("Root", "BadStage"))
    with pytest.raises(BmcBuildError, match="Unsupported stage action role"):
        witness_module._role_for_action(bad_stage)

    orphan = OnStage("during", None, "Orphan", None, [], True, ("Root", "Orphan"))
    with pytest.raises(BmcBuildError, match="no parent state"):
        witness_module._runtime_state_paths_for_action(orphan)

    cyclic_ref = OnStage("during", None, "Loop", None, [], False, ("Root", "Loop"))
    cyclic_ref.ref = cyclic_ref
    assert witness_module._resolved_abstract_target(cyclic_ref) is None

    context_roles = {}
    witness_module._record_context_role(context_roles, cyclic_ref, None, "Root.A")
    assert context_roles == {}

    missing_stage = OnStage(None, None, "NoStage", None, [], True, ("Root", "NoStage"))
    with pytest.raises(BmcBuildError, match="no call stage"):
        witness_module._record_context_role(
            context_roles, missing_stage, "leaf_during", "Root.A"
        )

    state_machine = load_state_machine_from_text(
        """
        state Root {
            state A { during abstract Touch; }
            [*] -> A;
        }
        """
    )
    assert witness_module._abstract_action_role_map(state_machine) == {
        "Root.A.Touch": "leaf_during"
    }

    assert witness_module._role_for_action(object()) is None
    fake_state = SimpleNamespace(
        on_enters=(object(),),
        on_durings=(),
        on_exits=(),
        on_during_aspects=(),
        is_leaf_state=False,
        is_pseudo=False,
    )
    fake_machine = SimpleNamespace(walk_states=lambda: (fake_state,))
    empty_resolver = witness_module._abstract_call_role_resolver(fake_machine)
    assert empty_resolver.named_roles == {}
    assert empty_resolver.context_roles == {}

    cyclic_machine_state = SimpleNamespace(
        on_enters=(cyclic_ref,),
        on_durings=(),
        on_exits=(),
        on_during_aspects=(),
    )
    cyclic_machine = SimpleNamespace(walk_states=lambda: (cyclic_machine_state,))
    assert witness_module._iter_resolved_abstract_action_paths(cyclic_machine) == ()


def test_internal_decoder_selection_and_progress_guards_are_loud() -> None:
    """Selected-case and fallback progress helpers are pinned for corruption."""
    solver = z3.Solver()
    solver.add(z3.BoolVal(True))
    assert solver.check() == z3.sat
    model = solver.model()
    relation = SimpleNamespace(selector=z3.BoolVal(False))

    with pytest.raises(BmcBuildError, match="Expected exactly one selected case"):
        witness_module._selected_relation(model, (relation,), 0)

    custom_relation = SimpleNamespace(case=SimpleNamespace(kind="custom"))
    assert witness_module._progress_for(custom_relation, False, False) == "custom"


def test_internal_event_decode_edge_guards_are_loud() -> None:
    """Impossible bound-query and response-support edge cases are pinned."""
    solver = z3.Solver()
    solver.add(z3.BoolVal(True))
    assert solver.check() == z3.sat
    model = solver.model()

    fake_event_assumption = BoundAssumption(
        EventCardinalityAssumption("any"),
        "event",
        cycles=(0,),
        resolved_event_ids=(0,),
    )
    fake_formula = SimpleNamespace(
        core=SimpleNamespace(
            context=SimpleNamespace(
                bound_query=SimpleNamespace(assumptions=(fake_event_assumption,))
            )
        )
    )
    assert witness_module._explicit_assumption_events(fake_formula, model, 0) == (
        (),
        (),
    )

    reach_formula = SimpleNamespace(kind="reach")
    assert witness_module._response_trigger_event_paths(reach_formula) == ()
    assert (
        witness_module._response_trigger_is_true_under_events(
            reach_formula, model, 0, ()
        )
        is False
    )

    non_current_response = SimpleNamespace(
        kind="response",
        core=SimpleNamespace(
            context=SimpleNamespace(
                bound_query=SimpleNamespace(
                    property=SimpleNamespace(
                        source=SimpleNamespace(
                            trigger=witness_module.bmc_ast.Event(
                                "Root.trigger", selector=0
                            )
                        )
                    )
                )
            )
        ),
    )
    assert witness_module._response_trigger_event_paths(non_current_response) == ()

    _, no_event_formula = _compile(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        "check response <= 1:\n"
        '  trigger active("Root.B")\n'
        "  -> within 1 terminated();",
    )
    solver = z3.Solver()
    solver.add(no_event_formula.core.core)
    assert solver.check() == z3.sat
    assert (
        witness_module._property_support_events(
            no_event_formula,
            solver.model(),
            0,
            (),
            BmcEventDecodePolicy(),
        )
        == ()
    )

    _, formula = _compile(
        """
        state Root {
            event trigger;
            state A;
            state B;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        "check response <= 1:\n"
        '  trigger event("Root.trigger", current) && active("Root.B")\n'
        "  -> within 1 terminated();",
    )
    event = formula.core.symbols.event_input(0, "Root.trigger")
    solver = z3.Solver()
    solver.add(formula.core.core, event)
    assert solver.check() == z3.sat
    with pytest.raises(BmcBuildError, match="Response trigger remained false"):
        witness_module._property_support_events(
            formula,
            solver.model(),
            0,
            (),
            BmcEventDecodePolicy(),
        )


def test_replay_result_and_mismatch_canonical_shapes_are_json_stable() -> None:
    """Replay result canonicalization exposes mismatch details deterministically."""
    trace = BmcWitnessTrace(
        {"kind": "reach"}, {"status": "sat"}, {"mode": "cold"}, (), ()
    )
    mismatch = BmcReplayMismatch(
        "frames[1].vars.x", 1.0, 2.0, "float value mismatch", 1e-9
    )
    replay = BmcReplayResult(trace, BmcRuntimeTrace((), ()), (mismatch,))
    assert replay.ok is False
    assert replay.to_canonical()["mismatches"] == [mismatch.to_canonical()]


def test_event_decode_policy_can_drop_debug_reads_without_changing_replay_inputs() -> (
    None
):
    """Debug reads are optional metadata, not replay inputs."""
    assert BmcEventDecodePolicy(
        include_debug_reads=False,
        include_property_support=True,
    ).to_canonical() == {
        "node": "bmc_event_decode_policy",
        "include_debug_reads": False,
        "include_property_support": True,
    }

    _, formula = _compile(
        """
        state Root {
            state A { event go; }
            state B;
            [*] -> A;
            A -> B :: go;
        }
        """,
        'init state("Root.A");\n'
        'assume event("Root.A.go", 0) == false;\n'
        'check reach <= 1: active("Root.A");',
    )
    result = solve_bmc_property(formula)
    trace = decode_bmc_witness(formula, result.model)
    assert trace.steps[0].input_events == ()
    assert [event.reason for event in trace.steps[0].event_reads]

    quiet = decode_bmc_witness(
        formula,
        result.model,
        event_policy=BmcEventDecodePolicy(include_debug_reads=False),
    )
    assert quiet.steps[0].input_events == ()
    assert quiet.steps[0].event_reads == ()
