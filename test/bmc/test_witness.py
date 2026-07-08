"""BMC witness public API and decoder tests."""

from __future__ import annotations

import pytest
import z3

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
