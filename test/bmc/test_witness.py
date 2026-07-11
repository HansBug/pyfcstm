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
    BmcRuntimeFrame,
    BmcRuntimeStep,
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


def _empty_sat_model():
    solver = z3.Solver()
    solver.add(z3.BoolVal(True))
    assert solver.check() == z3.sat
    return solver.model()


_VERDICT_DSL = """
state Root {
    event Go;
    state A;
    state B;
    [*] -> A;
    A -> B : Go;
}
"""


def _first_case_label(dsl_text: str, query_text: str, kind: str) -> str:
    model = load_state_machine_from_text(dsl_text)
    core = build_bmc_core_formula(BmcEngine(model).prepare(query_text))
    return next(
        relation.case.label
        for step in core.steps
        for relation in step.case_relations
        if relation.case.kind == kind
    )


def _verdict_formula(kind: str):
    if kind == "cover":
        label = _first_case_label(
            _VERDICT_DSL,
            'init state("Root.A"); check reach <= 1: active("Root.B");',
            "transition",
        )
        return _compile(
            _VERDICT_DSL,
            'init state("Root.A"); check cover <= 1: case("%s");' % label,
        )[1]
    queries = {
        "reach": 'init state("Root.A"); check reach <= 1: active("Root.B");',
        "exists_always": 'init state("Root.A"); check exists_always <= 1: active("Root");',
        "forbid": 'init state("Root.A"); check forbid <= 1: active("Root.A");',
        "invariant": 'init state("Root.A"); check invariant <= 1: active("Root");',
        "must_reach": 'init state("Root.A"); check must_reach <= 1: active("Root.B");',
        "response": (
            'init state("Root.A"); '
            'check response <= 1: trigger event("Root.Go", current) '
            '-> within 1 active("Root.B");'
        ),
    }
    return _compile(_VERDICT_DSL, queries[kind])[1]


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

    trace = decode_bmc_witness(
        formula,
        result.model,
        event_policy=BmcEventDecodePolicy(include_property_support=False),
    )
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


def test_response_trigger_support_cannot_be_disabled_when_replay_requires_it() -> None:
    """The decoder rejects a policy that would erase a response trigger."""
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
    with pytest.raises(BmcBuildError, match="property-support events"):
        decode_bmc_witness(
            formula,
            result.model,
            event_policy=BmcEventDecodePolicy(include_property_support=False),
        )


def test_response_non_trigger_step_ignores_true_event_without_rejecting_model() -> None:
    """A true event on a non-trigger step is not mistaken for trigger support."""
    model, formula = _compile(
        """
        state Root {
            event trigger;
            event advance;
            state A;
            state B;
            [*] -> A;
            A -> B : /advance;
        }
        """,
        'init state("Root.A");\n'
        'assume event("Root.advance", 0) == true;\n'
        "check response <= 2:\n"
        '  trigger event("Root.trigger", current) && active("Root.B")\n'
        "  -> within 1 terminated();",
    )
    trigger_0 = formula.core.symbols.event_input(0, "Root.trigger")
    trigger_1 = formula.core.symbols.event_input(1, "Root.trigger")
    model_ref = _solve_with_extra(formula, trigger_0, trigger_1)

    trace = decode_bmc_witness(formula, model_ref)

    assert trace.steps[0].input_event_paths == ("Root.advance",)
    assert trace.steps[1].input_event_paths == ("Root.trigger",)
    assert trace.steps[1].input_events == (
        BmcWitnessEvent("Root.trigger", "property_support", True),
    )
    assert replay_bmc_witness(model, trace).ok is True


def test_duplicate_event_assumptions_decode_to_one_runtime_occurrence() -> None:
    """Overlapping logical assumptions preserve Boolean event presence semantics."""
    model, formula = _compile(
        """
        state Root {
            event noise;
            state A;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        'assume event("Root.noise", *) == true;\n'
        'assume event("Root.noise", 0) == true;\n'
        'check reach <= 1: active("Root.A");',
    )
    result = solve_bmc_property(formula)

    trace = decode_bmc_witness(formula, result.model)
    replay = replay_bmc_witness(model, trace)

    assert trace.steps[0].input_event_paths == ("Root.noise",)
    assert trace.steps[0].input_events == (
        BmcWitnessEvent("Root.noise", "explicit_true_assumption", True),
    )
    assert replay.ok is True
    assert replay.runtime_trace.steps[0].input_events == ("Root.noise",)
    assert replay.runtime_trace.steps[0].unconsumed_events == ("Root.noise",)


def test_event_reason_merge_keeps_one_path_with_strongest_provenance() -> None:
    """Canonical event merging is order-stable and provenance-aware."""
    assert witness_module._merge_event_reasons(
        (
            BmcWitnessEvent("Root.noise", "model_debug", True),
            BmcWitnessEvent("Root.keep", "case_positive", True),
            BmcWitnessEvent("Root.noise", "case_positive", True),
            BmcWitnessEvent("Root.noise", "explicit_true_assumption", True),
        )
    ) == (
        BmcWitnessEvent("Root.noise", "explicit_true_assumption", True),
        BmcWitnessEvent("Root.keep", "case_positive", True),
    )


def test_witness_event_accounting_matches_replayed_multi_hop_consumption() -> None:
    """Witness accounting preserves repeated consumption within one macro step."""
    model, formula = _compile(
        """
        state Root {
            event go;
            state Parent {
                state A;
                [*] -> A;
                A -> [*] : /go;
            }
            state C;
            [*] -> Parent;
            Parent -> C : /go;
        }
        """,
        'init state("Root.Parent.A");\n'
        'assume event("Root.go", 0) == true;\n'
        'check reach <= 1: active("Root.C");',
    )
    result = solve_bmc_property(formula)

    trace = decode_bmc_witness(formula, result.model)
    replay = replay_bmc_witness(model, trace)

    assert trace.steps[0].input_event_paths == ("Root.go",)
    assert trace.steps[0].consumed_events == ("Root.go", "Root.go")
    assert trace.steps[0].unconsumed_events == ()
    assert replay.ok is True
    assert replay.runtime_trace.steps[0].consumed_events == ("Root.go", "Root.go")
    assert replay.runtime_trace.steps[0].unconsumed_events == ()


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
    assert result.property_satisfied is None
    assert result.witness_found is False
    assert result.counterexample_found is False
    assert result.incomplete is True
    assert result.outcome == "incomplete"
    assert result.to_canonical()["has_incomplete_model"] is True
    assert any(item.startswith("incomplete_elapsed_ms=") for item in result.diagnostics)


def test_solve_property_keeps_unchecked_response_suffix_incomplete() -> None:
    """Disabling suffix diagnostics must not report response UNSAT as satisfied."""
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
    result = solve_bmc_property(formula, check_incomplete=False)

    assert result.status == "unsat"
    assert result.model is None
    assert result.incomplete_status is None
    assert result.incomplete_model is None
    assert result.incomplete_reason == "incomplete check disabled"
    assert result.property_satisfied is None
    assert result.witness_found is False
    assert result.counterexample_found is False
    assert result.incomplete is True
    assert result.outcome == "incomplete"
    assert result.to_canonical()["property_satisfied"] is None
    assert "incomplete_check=disabled" in result.diagnostics


def test_response_violation_verdict_stays_decisive_with_suffix() -> None:
    """A response SAT counterexample remains decisive even with suffix metadata."""
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
    result = BmcSolveResult(
        formula,
        "sat",
        model=_empty_sat_model(),
        incomplete_status="sat",
        incomplete_model=_empty_sat_model(),
    )

    assert result.property_satisfied is False
    assert result.witness_found is False
    assert result.counterexample_found is True
    assert result.incomplete is False
    assert result.outcome == "property_violated"


@pytest.mark.parametrize(
    ("kind", "polarity"),
    [
        ("reach", "witness"),
        ("exists_always", "witness"),
        ("cover", "witness"),
        ("forbid", "counterexample"),
        ("invariant", "counterexample"),
        ("must_reach", "counterexample"),
        ("response", "counterexample"),
    ],
)
def test_solve_result_public_verdict_truth_table(kind, polarity) -> None:
    """Public verdict fields translate objective SAT/UNSAT into property results."""
    formula = _verdict_formula(kind)
    sat_result = BmcSolveResult(formula, "sat", model=_empty_sat_model())
    unsat_result = BmcSolveResult(formula, "unsat")

    assert sat_result.polarity == polarity
    assert unsat_result.polarity == polarity

    if polarity == "witness":
        assert sat_result.property_satisfied is True
        assert sat_result.witness_found is True
        assert sat_result.counterexample_found is False
        assert sat_result.incomplete is False
        assert sat_result.outcome == "witness_found"
        assert sat_result.to_canonical()["property_satisfied"] is True

        assert unsat_result.property_satisfied is False
        assert unsat_result.witness_found is False
        assert unsat_result.counterexample_found is False
        assert unsat_result.incomplete is False
        assert unsat_result.outcome == "no_witness"
        assert unsat_result.to_canonical()["outcome"] == "no_witness"
    else:
        assert sat_result.property_satisfied is False
        assert sat_result.witness_found is False
        assert sat_result.counterexample_found is True
        assert sat_result.incomplete is False
        assert sat_result.outcome == "property_violated"
        assert sat_result.to_canonical()["counterexample_found"] is True

        assert unsat_result.property_satisfied is True
        assert unsat_result.witness_found is False
        assert unsat_result.counterexample_found is False
        assert unsat_result.incomplete is False
        assert unsat_result.outcome == "property_satisfied"
        assert unsat_result.to_canonical()["property_satisfied"] is True


@pytest.mark.parametrize(
    ("status", "reason", "outcome"),
    [
        ("unknown", "canceled", "unknown"),
        ("timeout", "timeout", "timeout"),
    ],
)
def test_solve_result_unknown_and_timeout_verdicts_are_incomplete(
    status, reason, outcome
) -> None:
    """Unknown and timeout solver statuses do not claim a property verdict."""
    result = BmcSolveResult(_verdict_formula("reach"), status, reason=reason)

    assert result.property_satisfied is None
    assert result.witness_found is False
    assert result.counterexample_found is False
    assert result.incomplete is True
    assert result.outcome == outcome
    assert result.to_canonical()["incomplete"] is True


@pytest.mark.parametrize("bad_timeout", [0, -1, True, 1.5])
def test_solve_property_rejects_invalid_timeout_values(bad_timeout) -> None:
    """The public solver validates timeout values before touching Z3."""
    _, formula = _compile("state Root;", 'check reach <= 1: active("Root");')
    with pytest.raises(BmcBuildError, match="timeout_ms"):
        solve_bmc_property(formula, timeout_ms=bad_timeout)


@pytest.mark.parametrize("bad_check_incomplete", [0, 1, "yes", object()])
def test_solve_property_rejects_invalid_check_incomplete_values(
    bad_check_incomplete,
) -> None:
    """The public solver validates the incomplete-check switch loudly."""
    _, formula = _compile("state Root;", 'check reach <= 1: active("Root");')
    with pytest.raises(BmcBuildError, match="check_incomplete"):
        solve_bmc_property(formula, check_incomplete=bad_check_incomplete)


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

    _, formula = _compile("state Root;", 'check reach <= 1: active("Root");')
    with pytest.raises(BmcBuildError, match="no frames") as error_info:
        witness_module._initial_metadata(formula, ())
    assert "internal BMC witness consistency error" in str(error_info.value)
    assert "https://github.com/HansBug/pyfcstm/issues/new" in str(error_info.value)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda formula: BmcSolveResult(object(), "sat"), "formula must"),
        (lambda formula: BmcSolveResult(formula, "maybe"), "status must"),
        (lambda formula: BmcSolveResult(formula, "sat"), "model is required"),
        (lambda formula: BmcSolveResult(formula, "sat", model=object()), "model must"),
        (
            lambda formula: BmcSolveResult(
                formula, "sat", model=_empty_sat_model(), reason="timeout"
            ),
            "reason must be None",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", model=_empty_sat_model()),
            "model must be None",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", reason="because"),
            "reason must be None",
        ),
        (
            lambda formula: BmcSolveResult(
                formula, "unknown", model=_empty_sat_model(), reason="unknown"
            ),
            "model must be None",
        ),
        (
            lambda formula: BmcSolveResult(
                formula, "timeout", model=_empty_sat_model(), reason="timeout"
            ),
            "model must be None",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", incomplete_status="maybe"),
            "incomplete_status",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", incomplete_status="sat"),
            "incomplete_model is required",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", incomplete_model=object()),
            "incomplete_model",
        ),
        (
            lambda formula: BmcSolveResult(
                formula, "unsat", incomplete_model=_empty_sat_model()
            ),
            "incomplete_model must be None",
        ),
        (
            lambda formula: BmcSolveResult(
                formula,
                "unsat",
                incomplete_status="unsat",
                incomplete_model=_empty_sat_model(),
            ),
            "incomplete_model must be None",
        ),
        (
            lambda formula: BmcSolveResult(
                formula,
                "unsat",
                incomplete_status="unsat",
                incomplete_reason="because",
            ),
            "incomplete_reason must be None",
        ),
        (
            lambda formula: BmcSolveResult(
                formula,
                "unsat",
                incomplete_status="sat",
                incomplete_model=_empty_sat_model(),
                incomplete_reason="because",
            ),
            "incomplete_reason must be None",
        ),
        (
            lambda formula: BmcSolveResult(
                formula,
                "unsat",
                incomplete_status="unknown",
                incomplete_model=_empty_sat_model(),
                incomplete_reason="unknown",
            ),
            "incomplete_model must be None",
        ),
        (
            lambda formula: BmcSolveResult(
                formula,
                "unsat",
                incomplete_status="timeout",
                incomplete_model=_empty_sat_model(),
                incomplete_reason="timeout",
            ),
            "incomplete_model must be None",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", elapsed_ms="slow"),
            "elapsed_ms",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", elapsed_ms=True),
            "elapsed_ms",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", elapsed_ms=float("nan")),
            "elapsed_ms",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", elapsed_ms=float("inf")),
            "elapsed_ms",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", elapsed_ms=-1),
            "elapsed_ms",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", reason=123),
            "reason",
        ),
        (
            lambda formula: BmcSolveResult(
                formula, "unsat", incomplete_reason=object()
            ),
            "incomplete_reason",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", timeout_ms=0),
            "timeout_ms",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", diagnostics=(1,)),
            "diagnostics",
        ),
        (
            lambda formula: BmcSolveResult(formula, "unsat", diagnostics="bad"),
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
        (
            lambda: BmcWitnessCallRecord(
                0, "A", "during", "role", "S", "S", snapshot={1: 1}
            ),
            "snapshot keys",
        ),
        (
            lambda: BmcWitnessCallRecord(
                0, "A", "during", "role", "S", "S", snapshot={"x": None}
            ),
            "snapshot.x",
        ),
        (
            lambda: BmcWitnessCallRecord(
                0, "A", "during", "role", "S", "S", snapshot={"x": True}
            ),
            "snapshot.x",
        ),
        (
            lambda: BmcWitnessCallRecord(
                0, "A", "during", "role", "S", "S", snapshot={"x": "1"}
            ),
            "snapshot.x",
        ),
        (
            lambda: BmcWitnessCallRecord(
                0, "A", "during", "role", "S", "S", snapshot={"x": float("nan")}
            ),
            "snapshot.x",
        ),
        (
            lambda: BmcWitnessCallRecord(
                0, "A", "during", "role", "S", "S", snapshot={"x": float("inf")}
            ),
            "snapshot.x",
        ),
        (lambda: BmcWitnessFrame(True, None, None, "init", False, {}), "frame index"),
        (lambda: BmcWitnessFrame(0, True, None, "init", False, {}), "state_id"),
        (lambda: BmcWitnessFrame(0, None, "", "init", False, {}), "state"),
        (lambda: BmcWitnessFrame(0, None, None, "diag", False, {}), "sentinel"),
        (
            lambda: BmcWitnessFrame(0, 1, None, "init", False, {}),
            "sentinel frames",
        ),
        (
            lambda: BmcWitnessFrame(0, None, "Root", "init", False, {}),
            "sentinel frames",
        ),
        (
            lambda: BmcWitnessFrame(0, None, None, "terminated", False, {}),
            "terminated sentinel",
        ),
        (lambda: BmcWitnessFrame(0, None, None, "init", "no", {}), "terminated"),
        (lambda: BmcWitnessFrame(0, None, None, "init", False, ()), "vars"),
        (lambda: BmcWitnessFrame(0, None, None, "init", False, {1: 1}), "vars keys"),
        (
            lambda: BmcWitnessFrame(0, None, None, "init", False, {"x": None}),
            "vars.x",
        ),
        (
            lambda: BmcWitnessFrame(0, None, None, "init", False, {"x": True}),
            "vars.x",
        ),
        (
            lambda: BmcWitnessFrame(0, None, None, "init", False, {"x": "1"}),
            "vars.x",
        ),
        (
            lambda: BmcWitnessFrame(0, None, None, "init", False, {"x": float("nan")}),
            "vars.x",
        ),
        (
            lambda: BmcWitnessFrame(0, None, None, "init", False, {"x": float("inf")}),
            "vars.x",
        ),
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
                input_events=(
                    BmcWitnessEvent("Root.Noise", "negative_case_read", False),
                ),
            ),
            "replay input event reasons",
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
                input_events=(BmcWitnessEvent("Root.Go", "case_positive", False),),
            ),
            "model_value true",
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
                input_events="Root.Go",
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
                event_reads=(BmcWitnessEvent("Root.Go", "case_positive"),),
            ),
            "debug event reasons",
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
                event_reads="Root.Go",
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
                abstract_calls=None,
            ),
            "abstract_calls",
        ),
        (lambda: BmcWitnessTrace({}, {}, {}, (), (), schema_version="v2"), "schema"),
        (lambda: BmcWitnessTrace((), {}, {}, (), ()), "property"),
        (lambda: BmcWitnessTrace({}, (), {}, (), ()), "solver"),
        (lambda: BmcWitnessTrace({}, {}, (), (), ()), "initial"),
        (
            lambda: BmcWitnessTrace({"bad": object()}, {}, {}, (), ()),
            "property.bad",
        ),
        (
            lambda: BmcWitnessTrace({1: "bad"}, {}, {}, (), ()),
            "property keys",
        ),
        (
            lambda: BmcWitnessTrace(
                {}, {"status": "sat", "elapsed_ms": float("nan")}, {}, (), ()
            ),
            "solver.elapsed_ms",
        ),
        (
            lambda: BmcWitnessTrace(
                {}, {"status": "sat", "reason": object()}, {}, (), ()
            ),
            "solver.reason",
        ),
        (
            lambda: BmcWitnessTrace(
                {}, {"status": "sat", "reason": "timeout"}, {}, (), ()
            ),
            "solver.reason must be None",
        ),
        (
            lambda: BmcWitnessTrace(
                {}, {"status": "unsat", "reason": "because"}, {}, (), ()
            ),
            "solver.reason must be None",
        ),
        (
            lambda: BmcWitnessTrace({}, {"status": "maybe"}, {}, (), ()),
            "solver.status",
        ),
        (
            lambda: BmcWitnessTrace({}, {"incomplete_status": "maybe"}, {}, (), ()),
            "solver.incomplete_status",
        ),
        (
            lambda: BmcWitnessTrace(
                {},
                {
                    "incomplete_status": "sat",
                    "incomplete_reason": "because",
                },
                {},
                (),
                (),
            ),
            "solver.incomplete_reason must be None",
        ),
        (
            lambda: BmcWitnessTrace(
                {},
                {
                    "incomplete_status": "unsat",
                    "incomplete_reason": "because",
                },
                {},
                (),
                (),
            ),
            "solver.incomplete_reason must be None",
        ),
        (
            lambda: BmcWitnessTrace({}, {"elapsed_ms": True}, {}, (), ()),
            "elapsed_ms",
        ),
        (
            lambda: BmcWitnessTrace({}, {"incomplete_elapsed_ms": -1}, {}, (), ()),
            "elapsed_ms",
        ),
        (
            lambda: BmcWitnessTrace({}, {"reason": False}, {}, (), ()),
            "solver.reason",
        ),
        (
            lambda: BmcWitnessTrace({}, {"incomplete_reason": 1}, {}, (), ()),
            "solver.incomplete_reason",
        ),
        (lambda: BmcWitnessTrace({}, {}, {}, (object(),), ()), "frames"),
        (lambda: BmcWitnessTrace({}, {}, {}, None, ()), "frames"),
        (lambda: BmcWitnessTrace({}, {}, {}, (), (object(),)), "steps"),
        (lambda: BmcWitnessTrace({}, {}, {}, (), None), "steps"),
        (lambda: BmcWitnessTrace({}, {}, {}, (), (), diagnostics=(1,)), "diagnostics"),
        (lambda: BmcWitnessTrace({}, {}, {}, (), (), diagnostics="bad"), "diagnostics"),
        (lambda: BmcRuntimeFrame(True, None, True, {}), "runtime frame index"),
        (lambda: BmcRuntimeFrame(0, "", True, {}), "runtime frame state"),
        (lambda: BmcRuntimeFrame(0, None, "yes", {}), "runtime frame terminated"),
        (lambda: BmcRuntimeFrame(0, None, True, ()), "runtime frame vars"),
        (lambda: BmcRuntimeFrame(0, None, True, {1: 1}), "runtime frame vars keys"),
        (
            lambda: BmcRuntimeFrame(0, None, True, {"x": None}),
            "runtime frame vars.x",
        ),
        (
            lambda: BmcRuntimeFrame(0, None, True, {"x": True}),
            "runtime frame vars.x",
        ),
        (
            lambda: BmcRuntimeFrame(0, None, True, {"x": "1"}),
            "runtime frame vars.x",
        ),
        (
            lambda: BmcRuntimeFrame(0, None, True, {"x": float("nan")}),
            "runtime frame vars.x",
        ),
        (
            lambda: BmcRuntimeFrame(0, None, True, {"x": float("inf")}),
            "runtime frame vars.x",
        ),
        (lambda: BmcRuntimeStep(True, (), (), (), ()), "runtime step index"),
        (lambda: BmcRuntimeStep(0, (object(),), (), (), ()), "input_events"),
        (lambda: BmcRuntimeStep(0, "Root.Go", (), (), ()), "input_events"),
        (lambda: BmcRuntimeStep(0, (), (object(),), (), ()), "consumed_events"),
        (lambda: BmcRuntimeStep(0, (), "Root.Go", (), ()), "consumed_events"),
        (lambda: BmcRuntimeStep(0, (), (), (object(),), ()), "unconsumed_events"),
        (lambda: BmcRuntimeStep(0, (), (), "Root.Go", ()), "unconsumed_events"),
        (lambda: BmcRuntimeStep(0, (), (), (), (object(),)), "abstract_calls"),
        (lambda: BmcRuntimeStep(0, (), (), (), None), "abstract_calls"),
        (
            lambda: BmcRuntimeTrace((object(),), ()),
            "runtime trace frames",
        ),
        (
            lambda: BmcRuntimeTrace(None, ()),
            "runtime trace frames",
        ),
        (
            lambda: BmcRuntimeTrace((), (object(),)),
            "runtime trace steps",
        ),
        (
            lambda: BmcRuntimeTrace((), None),
            "runtime trace steps",
        ),
        (lambda: BmcReplayMismatch("", 1, 2, "bad"), "mismatch path"),
        (lambda: BmcReplayMismatch("x", 1, 2, ""), "mismatch message"),
        (lambda: BmcReplayMismatch("x", 1, 2, "bad", "wide"), "mismatch tolerance"),
        (
            lambda: BmcReplayMismatch("x", 1, 2, "bad", float("nan")),
            "mismatch tolerance",
        ),
        (
            lambda: BmcReplayMismatch("x", 1, 2, "bad", float("inf")),
            "mismatch tolerance",
        ),
        (
            lambda: BmcReplayMismatch("x", float("nan"), 2, "bad"),
            "mismatch expected",
        ),
        (
            lambda: BmcReplayMismatch("x", 1, float("inf"), "bad"),
            "mismatch actual",
        ),
        (
            lambda: BmcReplayMismatch("x", 1, object(), "bad"),
            "mismatch actual",
        ),
        (
            lambda: BmcReplayMismatch("x", 1, set(), "bad"),
            "mismatch actual",
        ),
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
        (
            lambda: BmcReplayResult(
                BmcWitnessTrace({}, {}, {}, (), ()),
                BmcRuntimeTrace((), ()),
                "bad",
            ),
            "mismatches",
        ),
    ],
)
def test_witness_public_dataclasses_reject_invalid_payloads(factory, message) -> None:
    """Witness JSON/replay dataclasses validate their public payload shape."""
    with pytest.raises(BmcBuildError, match=message):
        factory()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "input_events": (
                    BmcWitnessEvent("Root.Go", "case_positive"),
                    BmcWitnessEvent("Root.Go", "explicit_true_assumption"),
                )
            },
            "at most one event per path",
        ),
        (
            {"consumed_events": ("Root.Go",)},
            "must reference replay input event paths",
        ),
        (
            {
                "input_events": (BmcWitnessEvent("Root.Go", "case_positive"),),
                "unconsumed_events": (),
            },
            "must equal input events minus consumed events",
        ),
    ],
)
def test_witness_step_rejects_inconsistent_event_accounting(kwargs, message) -> None:
    """Public witness steps enforce canonical event-accounting invariants."""
    with pytest.raises(BmcBuildError, match=message):
        BmcWitnessStep(
            0,
            0,
            1,
            "Root::fallback::Root::0",
            "fallback",
            "fallback_gamma",
            "Root",
            "Root",
            False,
            True,
            **kwargs,
        )


def test_witness_trace_metadata_accepts_nested_json_payloads() -> None:
    """Public witness metadata preserves deterministic JSON-stable values."""
    trace = BmcWitnessTrace(
        {"kind": "reach", "tags": ["fast", {"nested": True}, None, 2]},
        {
            "status": "unknown",
            "elapsed_ms": 1.25,
            "reason": "ok",
            "incomplete_status": "unknown",
            "incomplete_elapsed_ms": 2,
            "incomplete_reason": None,
        },
        {"mode": "cold", "argv": ["--flag", 1]},
        (),
        (),
    )

    canonical = trace.to_canonical()
    assert canonical["property"] == {
        "kind": "reach",
        "tags": ["fast", {"nested": True}, None, 2],
    }
    assert canonical["solver"] == {
        "elapsed_ms": 1.25,
        "incomplete_elapsed_ms": 2,
        "incomplete_reason": None,
        "incomplete_status": "unknown",
        "reason": "ok",
        "status": "unknown",
    }
    assert canonical["initial"] == {"argv": ["--flag", 1], "mode": "cold"}


def test_witness_v1_step_schema_includes_complete_event_accounting() -> None:
    """The first public witness schema pins full cycle event accounting."""
    trace = BmcWitnessTrace(
        {"kind": "reach"},
        {"status": "sat"},
        {"mode": "hot"},
        (
            BmcWitnessFrame(0, 0, "Root.A", None, False, {}),
            BmcWitnessFrame(1, 1, "Root.B", None, False, {}),
        ),
        (
            BmcWitnessStep(
                0,
                0,
                1,
                "Root.A::transition::Root.B::0",
                "transition",
                "transition",
                "Root.A",
                "Root.B",
                False,
                False,
                input_events=(
                    BmcWitnessEvent("Root.Go", "explicit_true_assumption", True),
                    BmcWitnessEvent("Root.Noise", "explicit_true_assumption", True),
                ),
                consumed_events=("Root.Go", "Root.Go"),
            ),
        ),
    )

    payload = trace.to_canonical()

    assert payload["schema_version"] == "bmc-witness/v1"
    assert payload["steps"] == [
        {
            "index": 0,
            "source_frame": 0,
            "target_frame": 1,
            "case_label": "Root.A::transition::Root.B::0",
            "case_kind": "transition",
            "progress": "transition",
            "source_state": "Root.A",
            "target_state": "Root.B",
            "delta": False,
            "gamma": False,
            "input_events": [
                {
                    "path": "Root.Go",
                    "reason": "explicit_true_assumption",
                    "model_value": True,
                },
                {
                    "path": "Root.Noise",
                    "reason": "explicit_true_assumption",
                    "model_value": True,
                },
            ],
            "event_reads": [],
            "abstract_calls": [],
            "consumed_events": ["Root.Go", "Root.Go"],
            "unconsumed_events": ["Root.Noise"],
        }
    ]


def test_witness_trace_metadata_rejects_cycles_and_excessive_depth(monkeypatch) -> None:
    """JSON-stable metadata validation fails loudly instead of recursing."""
    cyclic_mapping = {}
    cyclic_mapping["self"] = cyclic_mapping
    with pytest.raises(BmcBuildError, match="cyclic metadata"):
        BmcWitnessTrace({"payload": cyclic_mapping}, {}, {}, (), ())

    cyclic_list = []
    cyclic_list.append(cyclic_list)
    with pytest.raises(BmcBuildError, match="cyclic metadata"):
        BmcWitnessTrace({"payload": cyclic_list}, {}, {}, (), ())

    class BadKey:
        def __str__(self) -> str:
            raise RuntimeError("metadata keys must be validated before sorting")

    with pytest.raises(BmcBuildError, match="property keys"):
        BmcWitnessTrace({BadKey(): 1}, {}, {}, (), ())

    monkeypatch.setattr(witness_module, "_PUBLIC_JSON_MAX_DEPTH", 2)
    with pytest.raises(BmcBuildError, match="nesting exceeds"):
        BmcWitnessTrace({"a": {"b": {"c": 1}}}, {}, {}, (), ())

    cyclic_mismatch = []
    cyclic_mismatch.append(cyclic_mismatch)
    with pytest.raises(BmcBuildError, match="cyclic metadata"):
        BmcReplayMismatch("x", cyclic_mismatch, 1, "bad")
    with pytest.raises(BmcBuildError, match="nesting exceeds"):
        BmcReplayMismatch("x", {"a": {"b": {"c": 1}}}, 1, "bad")


def test_public_canonicalization_revalidates_mutated_nested_payloads() -> None:
    """Canonical output rejects post-construction public payload mutation."""
    trace = BmcWitnessTrace(
        {"items": [1, 2]},
        {"status": "sat"},
        {"mode": "cold"},
        (BmcWitnessFrame(0, None, None, "init", False, {"x": 1}),),
        (),
    )
    trace.property["items"].append(float("nan"))
    with pytest.raises(BmcBuildError, match="property.items"):
        trace.to_canonical()

    trace = BmcWitnessTrace({"kind": "reach"}, {"status": "sat"}, {}, (), ())
    trace.solver["elapsed_ms"] = float("inf")
    with pytest.raises(BmcBuildError, match="solver.elapsed_ms"):
        trace.to_canonical()

    trace = BmcWitnessTrace({"kind": "reach"}, {"status": "sat"}, {}, (), ())
    trace.initial["bad"] = object()
    with pytest.raises(BmcBuildError, match="initial.bad"):
        trace.to_canonical()

    frame = BmcWitnessFrame(0, None, None, "init", False, {"x": 1})
    frame.vars["x"] = float("inf")
    with pytest.raises(BmcBuildError, match="vars.x"):
        frame.to_canonical()

    call = BmcWitnessCallRecord(
        0,
        "Root.A.Touch",
        "during",
        "leaf_during",
        "Root.A",
        "Root.A",
        snapshot={"x": 1},
    )
    call.snapshot["x"] = float("nan")
    with pytest.raises(BmcBuildError, match="snapshot.x"):
        call.to_canonical()

    runtime_frame = BmcRuntimeFrame(0, "Root.A", False, {"x": 1})
    runtime_frame.vars["x"] = float("nan")
    with pytest.raises(BmcBuildError, match="runtime frame vars.x"):
        runtime_frame.to_canonical()

    mismatch = BmcReplayMismatch("frames[1].vars", [], {}, "bad")
    mismatch.expected.append(float("nan"))
    with pytest.raises(BmcBuildError, match="mismatch expected"):
        mismatch.to_canonical()


def test_internal_json_metadata_mapping_guard_is_loud() -> None:
    """The recursive JSON metadata helper rejects non-mapping callers."""
    with pytest.raises(BmcBuildError, match="metadata must be a mapping"):
        witness_module._coerce_public_json_mapping("metadata", ())
    assert witness_module._coerce_public_json_value(
        "metadata", [1, {"enabled": True}]
    ) == [1, {"enabled": True}]
    with pytest.raises(BmcBuildError, match="nesting exceeds"):
        witness_module._coerce_public_json_mapping("metadata", {"x": 1}, _depth=999)


def test_value_comparison_fails_closed_for_non_finite_and_bool_numbers() -> None:
    """Replay value comparison cannot treat invalid numerics as equal."""
    mismatches = []

    witness_module._compare_values(mismatches, "frames[1].vars.x", float("nan"), 0)
    witness_module._compare_values(mismatches, "frames[1].vars.y", 1, float("inf"))
    witness_module._compare_values(mismatches, "frames[1].vars.z", True, 1)
    witness_module._compare_values(mismatches, "frames[1].vars.flag", True, False)
    witness_module._compare_values(mismatches, "frames[1].state", "Root.A", None)
    witness_module._compare_values(mismatches, "frames[1].mode", "active", "idle")

    assert len(mismatches) == 6
    assert mismatches[0].path == "frames[1].vars.x"
    assert mismatches[0].expected == "nan"
    assert mismatches[0].actual == 0
    assert mismatches[0].message == "numeric value mismatch"
    assert mismatches[1].to_canonical() == {
        "path": "frames[1].vars.y",
        "expected": 1,
        "actual": "inf",
        "message": "numeric value mismatch",
        "tolerance": None,
    }
    assert mismatches[2].to_canonical() == {
        "path": "frames[1].vars.z",
        "expected": True,
        "actual": 1,
        "message": "value type mismatch",
        "tolerance": None,
    }
    assert mismatches[3].to_canonical() == {
        "path": "frames[1].vars.flag",
        "expected": True,
        "actual": False,
        "message": "value mismatch",
        "tolerance": None,
    }
    assert mismatches[4].to_canonical() == {
        "path": "frames[1].state",
        "expected": "Root.A",
        "actual": None,
        "message": "value type mismatch",
        "tolerance": None,
    }
    assert mismatches[5].to_canonical() == {
        "path": "frames[1].mode",
        "expected": "active",
        "actual": "idle",
        "message": "value mismatch",
        "tolerance": None,
    }


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

    _, true_no_event_formula = _compile(
        """
        state Root {
            state A;
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        "check response <= 1:\n"
        '  trigger active("Root.A")\n'
        "  -> within 1 terminated();",
    )
    solver = z3.Solver()
    solver.add(true_no_event_formula.core.core)
    assert solver.check() == z3.sat
    assert (
        witness_module._property_support_events(
            true_no_event_formula,
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
    assert (
        witness_module._property_support_events(
            formula,
            solver.model(),
            0,
            (),
            BmcEventDecodePolicy(),
        )
        == ()
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
