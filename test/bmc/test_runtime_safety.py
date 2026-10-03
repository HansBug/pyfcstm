"""Runtime-safety obligation of bounded model checking.

Each case is decided twice: by the BMC runtime-safety check and by the
simulator, which is the reference for when an operation is evaluated.  A
reported error must replay to the same kind of error at the same step.
"""

import itertools
from dataclasses import replace

import pytest
import z3

from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
    BmcOptions,
    BoolTemplate,
    EvaluationPoint,
    GuardRequirement,
    InvalidBmcEncoding,
    MacroStepFormal,
    build_bmc_core_formula,
    build_bmc_domain,
    compile_bmc_query,
    decode_bmc_result_trace,
    expand_macro_step_cases,
    replay_bmc_witness,
    solve_bmc_property,
    stable_leaf_source,
)
from pyfcstm.bmc.safety import BmcRuntimeSafetyResult, check_runtime_safety, runtime_error_formula
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.model.expr import parse_expr
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.simulate.runtime import SimulationRuntimeExpressionError

QUERY = 'check reach <= 3: active("Root.B");'
#: Two macro steps leave step 1 as the only step an error can happen at, so
#: the solver has no other error prefix to choose.
SHORT_QUERY = 'check reach <= 2: active("Root.B");'


def _machine(body, declarations="input int d;\ndef float x = 1.0;"):
    return declarations + "\nstate Root {\n" + body + "\n}"


def _first_runtime_error(model, values=(-1, 0, 2), steps=3):
    """Return ``(step, kind)`` of the earliest error over all input sequences."""
    found = None
    for sequence in itertools.product(values, repeat=steps):
        runtime = SimulationRuntime(model, input_source={"d": 0})
        for step, value in enumerate(sequence):
            try:
                runtime.cycle(inputs={"d": value})
            except SimulationRuntimeExpressionError as err:
                if found is None or step < found[0]:
                    found = (step, err.kind)
                break
    return found


GUARD_ORDER_PROTECTS = """
    [*] -> A;
    state A; state B; state C;
    A -> B : if [d == 0];
    A -> C : if [10 / d > 1];
"""
GUARD_ORDER_EXPOSES = GUARD_ORDER_PROTECTS.replace("d == 0", "d == 1")
SPECULATIVE_ENTER = """
    [*] -> A;
    state A; state B;
    state C {
        enter { x = 10 / d; }
        [*] -> C1 : if [false];
        state C1;
    }
    A -> C;
"""
EAGER_NESTED_PROBE = """
    [*] -> A;
    state A; state B;
    state C {
        [*] -> C1 : if [x > 0];
        [*] -> C2 : if [x / d > 0];
        state C1; state C2;
    }
    A -> C;
"""
LAZY_SOURCE_CHOICE = """
    [*] -> A;
    state A; state B; state C;
    A -> B;
    A -> C : if [10 / d > 0];
"""
LAZY_INITIAL_CHOICE = """
    [*] -> A;
    [*] -> B : if [10 / d > 0];
    state A; state B;
"""
SHORT_CIRCUIT_GUARD = """
    [*] -> A;
    state A; state B;
    A -> B : if [d != 0 && 10 / d > 1];
"""


@pytest.mark.unittest
@pytest.mark.parametrize(
    "body",
    [GUARD_ORDER_PROTECTS, LAZY_SOURCE_CHOICE, LAZY_INITIAL_CHOICE, SHORT_CIRCUIT_GUARD],
    ids=["earlier-guard-protects", "lazy-source-choice", "lazy-initial-choice", "short-circuit"],
)
def test_operations_the_runtime_never_evaluates_are_safe(body):
    model = load_state_machine_from_text(_machine(body))
    result = solve_bmc_property(compile_bmc_query(model, QUERY))

    assert result.runtime_safety.status == "safe"
    assert result.outcome not in ("runtime_error", "runtime_safety_unknown", "runtime_safety_timeout")
    assert _first_runtime_error(model) is None


@pytest.mark.unittest
@pytest.mark.parametrize(
    "body, kind, location, step",
    [
        (GUARD_ORDER_EXPOSES, "division_by_zero", "guard g1 in transition Root.A::1::A->C", 1),
        (SPECULATIVE_ENTER, "division_by_zero", "action block state_enter in state Root.C", 1),
        (EAGER_NESTED_PROBE, "division_by_zero", "guard g1 in transition Root.C::1::INIT_STATE->C2", 1),
    ],
    ids=["unprotected-later-guard", "failed-speculative-path", "eager-nested-probe"],
)
def test_reachable_errors_replay_at_the_reported_step(body, kind, location, step):
    model = load_state_machine_from_text(_machine(body))
    result = solve_bmc_property(compile_bmc_query(model, SHORT_QUERY))

    assert result.outcome == "runtime_error"
    assert result.status == "unknown"
    assert result.reason == "property not evaluated: runtime safety violated"
    error = result.runtime_safety.error
    assert (error.kind, error.location, error.step) == (kind, location, step)
    replay = replay_bmc_witness(model, decode_bmc_result_trace(result, source="runtime_error"))
    assert replay.ok
    assert replay.runtime_error is not None
    assert _first_runtime_error(model) == (step, kind)


@pytest.mark.unittest
def test_an_irrational_writeback_into_an_int_is_located():
    # The assumption forces r to the square root of five.  The solver model
    # keeps it as an algebraic number, whose integrality Z3 cannot evaluate
    # on its own, and the witness carries it as the nearest float.
    model = load_state_machine_from_text(
        "input float r;\ndef int y = 0;\n"
        "state Root { [*] -> A; state A { during { y = r; } } state B; }"
    )
    query = "assume always: r * r == 5 && r > 0;\n" + QUERY
    result = solve_bmc_property(compile_bmc_query(model, query))

    assert result.runtime_safety.error.kind == "writeback_non_integral"
    witness = decode_bmc_result_trace(result, source="runtime_error")
    assert witness.to_canonical()["verdict"]["runtime_error"]["inputs"] == {"r": 5 ** 0.5}
    assert replay_bmc_witness(model, witness).ok


@pytest.mark.unittest
def test_an_initializer_error_needs_no_step():
    model = load_state_machine_from_text("def float x = sqrt(0 - 1);\nstate Root;")
    result = solve_bmc_property(compile_bmc_query(model, 'check reach <= 1: active("Root");'))

    error = result.runtime_safety.error
    assert (error.step, error.kind, error.location) == (None, "math_domain", "initializer for x")
    replay = replay_bmc_witness(model, decode_bmc_result_trace(result, source="runtime_error"))
    assert replay.ok
    with pytest.raises(ValueError):
        SimulationRuntime(model)


@pytest.mark.unittest
def test_switching_the_check_off_evaluates_the_property():
    model = load_state_machine_from_text(_machine(GUARD_ORDER_EXPOSES))
    result = solve_bmc_property(compile_bmc_query(model, QUERY), runtime_safety=False)

    assert result.runtime_safety is None
    assert result.outcome != "runtime_error"


@pytest.mark.unittest
def test_a_model_without_risky_operations_is_not_applicable():
    model = load_state_machine_from_text(_machine("[*] -> A; state A; state B; A -> B;"))
    core = build_bmc_core_formula(BmcEngine(model).prepare(QUERY))

    assert runtime_error_formula(core) == (z3.BoolVal(False), ())
    assert check_runtime_safety(core).to_canonical() == {
        "elapsed_ms": 0.0,
        "error": None,
        "reason": None,
        "sites": 0,
        "status": "not_applicable",
    }


@pytest.mark.unittest
def test_the_check_runs_on_the_unsliced_core():
    # The query never reads telemetry, so cone slicing drops it, and a sliced
    # core lists no error sites; the check rebuilds the core without slicing.
    model = load_state_machine_from_text(
        "def int total = 5;\ndef int count = 0;\ndef int mean = 0;\ndef int telemetry = 0;\n"
        "state Root { [*] -> A; state A; "
        "state B { enter { mean = total / count; telemetry = 17; } } A -> B; }"
    )
    core = compile_bmc_query(
        model, "check invariant <= 2: mean == 0;", options=BmcOptions(cone_slicing=True)
    ).core
    assert core.cone_slice.dropped_variables == ("telemetry",)
    assert runtime_error_formula(core)[1] == ()

    result = check_runtime_safety(core)

    assert (result.status, result.error.kind, result.error.step) == ("violated", "division_by_zero", 1)
    assert result.core is not core


@pytest.mark.unittest
@pytest.mark.parametrize(
    "reason, status, outcome",
    [("timeout", "timeout", "runtime_safety_timeout"), ("incomplete", "unknown", "runtime_safety_unknown")],
)
def test_an_undecided_check_leaves_the_property_unevaluated(monkeypatch, reason, status, outcome):
    model = load_state_machine_from_text(_machine(GUARD_ORDER_EXPOSES))
    formula = compile_bmc_query(model, QUERY)
    # The solver gives up the way Z3 does on a hard or interrupted query.
    monkeypatch.setattr(z3.Solver, "check", lambda self, *args: z3.unknown)
    monkeypatch.setattr(z3.Solver, "reason_unknown", lambda self: reason)

    result = solve_bmc_property(formula)

    assert result.runtime_safety.status == status
    assert result.runtime_safety.reason == reason
    assert result.outcome == outcome
    assert result.reason == "property not evaluated: runtime safety %s" % status


@pytest.mark.unittest
def test_check_runtime_safety_rejects_a_non_core():
    with pytest.raises(BmcBuildError, match="core must be BmcCoreFormula"):
        check_runtime_safety("core")


@pytest.mark.unittest
@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"status": "broken"}, "Unsupported runtime safety status"),
        ({"status": "violated"}, "Only a violated runtime safety check carries an error"),
        ({"status": "timeout"}, "Only an undecided runtime safety check carries a reason"),
        ({"status": "safe", "reason": "late"}, "Only an undecided runtime safety check carries a reason"),
    ],
)
def test_runtime_safety_result_rejects_inconsistent_fields(kwargs, message):
    with pytest.raises(BmcBuildError, match=message):
        BmcRuntimeSafetyResult(sites=1, elapsed_ms=0.0, **kwargs)


def _probe_order(body):
    model = load_state_machine_from_text(_machine(body))
    formal = expand_macro_step_cases(stable_leaf_source(build_bmc_domain(model, 1), "Root.A"))
    return [
        point.guard.transition_label if point.guard is not None else point.block.runtime_role
        for point in formal.evaluation_points
    ]


@pytest.mark.unittest
def test_evaluation_points_follow_the_runtime_order():
    # The choice at the source is lazy; the nested initial choice is probed
    # in reverse declaration order before the declared order is explored.
    assert _probe_order(EAGER_NESTED_PROBE) == [
        "Root.C::1::INIT_STATE->C2",
        "Root.C::0::INIT_STATE->C1",
        "Root.C::0::INIT_STATE->C1",
        "Root.C::1::INIT_STATE->C2",
    ]
    assert _probe_order(GUARD_ORDER_PROTECTS) == ["Root.A::0::A->B", "Root.A::1::A->C"]


def _guard():
    return GuardRequirement("g0", 0, "Root", "Root -> A", parse_expr("x > 0"), "positive", "transition_guard", 0)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"parent": "point"}, "parent must be EvaluationPoint"),
        ({"condition": True}, "condition must be BoolTemplate"),
        ({"guard": None}, "either a guard or a block"),
        ({"guard": "g0"}, "guard must be GuardRequirement"),
        ({"guard": None, "block": "block"}, "block must be ActionBlock"),
    ],
)
def test_evaluation_point_rejects_inconsistent_fields(kwargs, message):
    fields = dict({"parent": None, "condition": BoolTemplate.true(), "guard": _guard()}, **kwargs)
    with pytest.raises(InvalidBmcEncoding, match=message):
        EvaluationPoint(**fields)


@pytest.mark.unittest
def test_formal_requires_points_after_their_parents():
    model = load_state_machine_from_text(_machine(GUARD_ORDER_PROTECTS))
    formal = expand_macro_step_cases(stable_leaf_source(build_bmc_domain(model, 1), "Root.A"))
    first = EvaluationPoint(None, BoolTemplate.true(), guard=_guard())
    second = EvaluationPoint(first, BoolTemplate.true(), guard=_guard())

    with pytest.raises(InvalidBmcEncoding, match="must follow its parent"):
        MacroStepFormal(formal.source, formal.success_cases, evaluation_points=(second, first))
    with pytest.raises(InvalidBmcEncoding, match="must contain EvaluationPoint"):
        MacroStepFormal(formal.source, formal.success_cases, evaluation_points=("point",))
    assert MacroStepFormal(
        formal.source, formal.success_cases, evaluation_points=(first, second)
    ).evaluation_points == (first, second)


def _error_witness(body, query=SHORT_QUERY):
    model = load_state_machine_from_text(_machine(body))
    result = solve_bmc_property(compile_bmc_query(model, query))
    return model, decode_bmc_result_trace(result, source="runtime_error")


def _with_error(witness, **changes):
    verdict = dict(witness.verdict)
    verdict["runtime_error"] = dict(verdict["runtime_error"], **changes)
    return replace(witness, verdict=verdict)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "changes, path",
    [
        ({"kind": "modulo_by_zero"}, "verdict.runtime_error.kind"),
        ({"location": "action block leaf_during in state Root.A"}, "verdict.runtime_error.location"),
        ({"inputs": {"d": 2}}, "verdict.runtime_error"),
    ],
    ids=["kind", "location", "not-raised"],
)
def test_replay_rejects_a_claim_the_runtime_does_not_reproduce(changes, path):
    model, witness = _error_witness(GUARD_ORDER_EXPOSES)
    assert replay_bmc_witness(model, witness).ok

    replay = replay_bmc_witness(model, _with_error(witness, **changes))

    assert not replay.ok
    assert [item.path for item in replay.mismatches] == [path]


@pytest.mark.unittest
def test_replay_checks_an_initializer_error_against_the_model():
    model = load_state_machine_from_text("def float x = sqrt(0 - 1);\nstate Root;")
    result = solve_bmc_property(compile_bmc_query(model, 'check reach <= 1: active("Root");'))
    witness = decode_bmc_result_trace(result, source="runtime_error")

    assert replay_bmc_witness(model, witness).runtime_error["kind"] == "math_domain"
    mismatched = replay_bmc_witness(model, _with_error(witness, kind="division_by_zero"))
    assert [item.path for item in mismatched.mismatches] == ["verdict.runtime_error.kind"]
    # The same claim replayed against a model whose initializer is defined.
    repaired = load_state_machine_from_text("def float x = sqrt(1);\nstate Root;")
    replay = replay_bmc_witness(repaired, witness)
    assert replay.runtime_error is None
    assert [item.path for item in replay.mismatches] == ["verdict.runtime_error"]


def _violated_result():
    model = load_state_machine_from_text(_machine(GUARD_ORDER_EXPOSES))
    return model, solve_bmc_property(compile_bmc_query(model, SHORT_QUERY))


@pytest.mark.unittest
def test_solve_rejects_a_non_boolean_switch():
    _, result = _violated_result()
    with pytest.raises(BmcBuildError, match="runtime_safety must be a bool"):
        solve_bmc_property(result.formula, runtime_safety="yes")


@pytest.mark.unittest
def test_a_result_keeps_an_unsafe_check_and_its_unevaluated_property_together():
    _, result = _violated_result()
    with pytest.raises(BmcBuildError, match="runtime_safety must be BmcRuntimeSafetyResult"):
        replace(result, runtime_safety="violated")
    with pytest.raises(BmcBuildError, match="leaves the property unevaluated"):
        replace(result, status="sat")


@pytest.mark.unittest
def test_the_error_prefix_channel_needs_a_violated_check():
    model, result = _violated_result()
    safe = solve_bmc_property(compile_bmc_query(model, SHORT_QUERY), runtime_safety=False)
    with pytest.raises(BmcBuildError, match="requires a violated runtime safety check"):
        decode_bmc_result_trace(safe, source="runtime_error")
    with pytest.raises(BmcBuildError, match="event_policy must be BmcEventDecodePolicy"):
        decode_bmc_result_trace(result, source="runtime_error", event_policy="sparse")


@pytest.mark.unittest
def test_an_error_prefix_witness_must_state_its_error_and_an_unevaluated_check():
    _, result = _violated_result()
    witness = decode_bmc_result_trace(result, source="runtime_error")
    verdict = {key: value for key, value in witness.verdict.items() if key != "runtime_error"}
    with pytest.raises(BmcBuildError, match="requires runtime_error with step"):
        replace(witness, verdict=verdict)
    with pytest.raises(BmcBuildError, match="requires an unevaluated primary check"):
        replace(witness, solver=dict(witness.solver, primary_status="unsat", primary_reason=None))


@pytest.mark.unittest
def test_an_undecided_check_explains_why_no_verdict_exists(monkeypatch):
    model = load_state_machine_from_text(_machine(GUARD_ORDER_EXPOSES))
    formula = compile_bmc_query(model, SHORT_QUERY)
    monkeypatch.setattr(z3.Solver, "check", lambda self, *args: z3.unknown)
    monkeypatch.setattr(z3.Solver, "reason_unknown", lambda self: "timeout")

    text = str(solve_bmc_property(formula))

    assert "RUNTIME SAFETY CHECK TIMED OUT; PROPERTY NOT EVALUATED" in text
    assert "The runtime-safety check timed out; no property verdict is available." in text


TWO_STAGES = _machine(GUARD_ORDER_EXPOSES, "input int d;\ndef float x = 1.0;\ndef float y = 10 / 2;")


@pytest.mark.unittest
def test_an_undecided_stage_does_not_hide_a_later_error(monkeypatch):
    # The initializer stage cannot fail; the solver gives up on it the way
    # Z3 does on a hard query, and the step it can decide still reports.
    model = load_state_machine_from_text(TWO_STAGES)
    formula = compile_bmc_query(model, SHORT_QUERY)
    assert formula.core._initial_error_sites
    original = z3.Solver.check
    calls = []

    def check(self, *args):
        calls.append(None)
        return z3.unknown if len(calls) == 1 else original(self, *args)

    monkeypatch.setattr(z3.Solver, "check", check)
    monkeypatch.setattr(z3.Solver, "reason_unknown", lambda self: "incomplete")

    result = solve_bmc_property(formula)

    assert result.outcome == "runtime_error"
    assert (result.runtime_safety.error.step, result.runtime_safety.error.kind) == (1, "division_by_zero")


@pytest.mark.unittest
def test_every_undecided_stage_reports_the_first_reason(monkeypatch):
    model = load_state_machine_from_text(TWO_STAGES)
    formula = compile_bmc_query(model, SHORT_QUERY)
    reasons = iter(["incomplete", "timeout"])
    monkeypatch.setattr(z3.Solver, "check", lambda self, *args: z3.unknown)
    monkeypatch.setattr(z3.Solver, "reason_unknown", lambda self: next(reasons))

    result = solve_bmc_property(formula)

    assert (result.runtime_safety.status, result.runtime_safety.reason) == ("unknown", "incomplete")


@pytest.mark.unittest
def test_a_dead_end_pseudo_state_runs_no_action():
    # The runtime enters a pseudo state without outgoing transitions without
    # running its lifecycle actions, so its division is never evaluated.
    model = load_state_machine_from_text(
        _machine("[*] -> A; state A; state B; pseudo state P { enter { x = 10 / d; } } A -> P :: Go;")
    )
    result = solve_bmc_property(compile_bmc_query(model, 'check reach <= 3: terminated();'))

    assert result.runtime_safety.status == "not_applicable"
    assert result.outcome == "no_witness"
    runtime = SimulationRuntime(model, input_source={"d": 0})
    runtime.cycle()
    runtime.cycle(["Root.A.Go"], inputs={"d": 0})
    assert runtime.current_state.path == ("Root", "A")


@pytest.mark.unittest
def test_the_error_formula_is_the_disjunction_of_its_stages():
    model = load_state_machine_from_text(_machine(GUARD_ORDER_EXPOSES, "input int d;\ndef float y = 10 / 2;"))
    core = build_bmc_core_formula(BmcEngine(model).prepare(QUERY))

    formula, sites = runtime_error_formula(core)

    assert z3.is_or(formula) and sites
    assert [site.step for site in sites][0] is None
    solver = z3.Solver()
    solver.add(formula)
    assert solver.check() == z3.sat
