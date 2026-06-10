"""Contract tests for verify diagnostics declared in ``codes.yaml``.

These tests prepare the diagnostics contract for later inspect integration.
They exercise raw verify algorithms and topology queries from real DSL
fixtures, then validate the refs payload shape against ``CODE_REGISTRY``
without calling the future inspect adapter.
"""

from __future__ import annotations

import json
import os
from textwrap import dedent

import pytest

from pyfcstm.diagnostics import CODE_REGISTRY, inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils import ModelDiagnostic
from pyfcstm.verify import (
    REGISTRY,
    composite_init_guards_incomplete,
    dead_guard,
    effect_contradicts_guard,
    effect_no_op_under_guard,
    enter_postcondition_implies_during_precondition,
    forced_guard_unsat_under_init,
    guard_tautology,
    transition_shadowed_by_predecessor,
)
from pyfcstm.verify import topology

from ._schema_check import assert_refs_match_schema


pytestmark = pytest.mark.unittest


STRUCTURAL_VERIFY_CODES = {
    "I_NONTRIVIAL_SCC",
    "W_TOPOLOGICAL_NOEXIT",
    "I_TOPOLOGICAL_NON_TERMINATING",
    "W_EVENT_UNREACHABLE_EMIT",
}

SMT_LOCAL_VERIFY_CODES = {
    "W_DEAD_GUARD",
    "W_GUARD_TAUTOLOGY",
    "W_FORCED_GUARD_UNSAT",
    "W_EFFECT_SMT_NO_OP",
    "I_EFFECT_GUARD_CONTRADICT",
    "W_TRANSITION_SHADOWED",
    "I_ENTER_DURING_CONTRADICT",
    "W_COMPOSITE_INIT_INCOMPLETE",
}

NEW_VERIFY_CODES = STRUCTURAL_VERIFY_CODES | SMT_LOCAL_VERIFY_CODES


def _parse(source: str):
    ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast)


def _variables(machine):
    return tuple(machine.defines.values())


def _guarded_transition(machine):
    return next(
        transition
        for state in machine.walk_states()
        for transition in state.transitions
        if transition.guard is not None
    )


def _forced_transition(machine):
    return next(
        transition
        for state in machine.walk_states()
        for transition in state.transitions
        if transition.is_forced
    )


def _effect_transition(machine):
    return next(
        transition
        for state in machine.walk_states()
        for transition in state.transitions
        if transition.effects
    )


def _state_path(state):
    return ".".join(state.path)


def _state_by_path(machine, path: str):
    return next(state for state in machine.walk_states() if _state_path(state) == path)


def _transition_summary(payload):
    return "{parent}:{from_state}->{to_state}".format(**payload)


def _diag(code: str, severity: str, refs: dict) -> ModelDiagnostic:
    return ModelDiagnostic(
        code=code,
        severity=severity,
        message=f"synthetic contract check for {code}",
        span=None,
        refs=refs,
    )


def _raw_smt_diag_from_example(code: str) -> dict:
    spec = CODE_REGISTRY[code]
    machine = _parse(spec.example_dsl)
    variables = _variables(machine)

    if code == "W_DEAD_GUARD":
        result = dead_guard(_guarded_transition(machine), variables)
    elif code == "W_GUARD_TAUTOLOGY":
        result = guard_tautology(_guarded_transition(machine), variables)
    elif code == "W_FORCED_GUARD_UNSAT":
        result = forced_guard_unsat_under_init(_forced_transition(machine), variables)
    elif code == "W_EFFECT_SMT_NO_OP":
        result = effect_no_op_under_guard(_effect_transition(machine), variables)
    elif code == "I_EFFECT_GUARD_CONTRADICT":
        result = effect_contradicts_guard(_effect_transition(machine), variables)
    elif code == "W_TRANSITION_SHADOWED":
        result = transition_shadowed_by_predecessor(machine, variables)
    elif code == "I_ENTER_DURING_CONTRADICT":
        result = enter_postcondition_implies_during_precondition(
            _state_by_path(machine, "System.A"),
            variables,
        )
    elif code == "W_COMPOSITE_INIT_INCOMPLETE":
        result = composite_init_guards_incomplete(machine, variables)
    else:  # pragma: no cover - parameterized test guards the code set.
        raise AssertionError(f"unexpected SMT verify code {code!r}")

    matches = [diag for diag in result.diagnostics if diag["code"] == code]
    assert matches, (code, result)
    return matches[0]


def _refs_from_raw_smt(raw: dict) -> dict:
    code = raw["code"]
    data = raw["data"]
    refs = {
        "algorithm_name": raw["algorithm_name"],
        "verification_scope": data["verification_scope"],
    }

    if "transition" in data:
        refs["transition"] = data["transition"]
        refs["transition_summary"] = _transition_summary(data["transition"])
    if code == "W_FORCED_GUARD_UNSAT":
        refs["scope"] = data["scope"]
    elif code == "W_TRANSITION_SHADOWED":
        refs.update({
            "source_state_path": data["source"],
            "reason": data["reason"],
            "shadowed_by_count": len(data["shadowed_by"]),
            "shadowed_by": [
                _transition_summary(item) for item in data["shadowed_by"]
            ],
        })
    elif code == "I_ENTER_DURING_CONTRADICT":
        refs.update({
            "state_path": data["state"],
            "condition": data["condition"],
            "condition_source": data["condition_source"],
            "branch_taken": data["branch_taken"],
        })
    elif code == "W_COMPOSITE_INIT_INCOMPLETE":
        refs.update({
            "composite_path": data["state"],
            "init_transition_count": len(data["init_transitions"]),
            "init_transitions": [
                _transition_summary(item) for item in data["init_transitions"]
            ],
            "witness": data["witness"],
        })
    return refs


def _structural_refs_from_example(code: str) -> dict:
    machine = _parse(CODE_REGISTRY[code].example_dsl)

    if code == "I_NONTRIVIAL_SCC":
        scc = topology.strongly_connected_components(machine)[0]
        return {
            "algorithm_name": "strongly_connected_components",
            "verification_scope": "topological_only",
            "representative_state_path": scc[0],
            "scc": list(scc),
        }
    if code == "W_TOPOLOGICAL_NOEXIT":
        report = topology.topological_finite(machine)
        kind, payload = report.counterexamples[0]
        representative = payload[0] if isinstance(payload, tuple) else payload
        return {
            "algorithm_name": "topological_finite",
            "verification_scope": "topological_only",
            "representative_state_path": representative,
            "counterexample_kind": kind,
            "scc": list(payload) if isinstance(payload, tuple) else [],
        }
    if code == "I_TOPOLOGICAL_NON_TERMINATING":
        report = topology.topological_inevitable_terminator(machine)
        path = list(report.counterexample_path or ())
        return {
            "algorithm_name": "topological_inevitable_terminator",
            "verification_scope": "topological_only",
            "representative_state_path": path[0],
            "counterexample_path": path,
        }
    if code == "W_EVENT_UNREACHABLE_EMIT":
        event_name = topology.event_emission_to_consumer_reachable(machine)[0]
        graph = topology.build_leaf_level_macro_graph(machine)
        reachability = topology._event_consumer_reachability(machine, graph)
        unreachable_consumers = [
            reachable for reachable in reachability[event_name] if not reachable
        ]
        return {
            "algorithm_name": "event_emission_to_consumer_reachable",
            "verification_scope": "topological_only",
            "event_name": event_name,
            "consumer_count": len(unreachable_consumers),
        }
    raise AssertionError(f"unexpected structural verify code {code!r}")


def _refs_for_code(code: str) -> dict:
    if code in STRUCTURAL_VERIFY_CODES:
        return _structural_refs_from_example(code)
    return _refs_from_raw_smt(_raw_smt_diag_from_example(code))


def test_all_implemented_verify_diagnostic_codes_are_declared():
    emitted_by_registry = {
        code
        for meta in REGISTRY.values()
        if meta.impl is not None
        for code in meta.diagnostic_codes
    }
    missing = emitted_by_registry - set(CODE_REGISTRY)
    assert not missing, (
        "implemented verify algorithms must not advertise diagnostic codes "
        f"missing from codes.yaml: {sorted(missing)}"
    )


def test_unregistered_verify_code_is_rejected_by_refs_schema_check():
    unknown = _diag(
        "W_VERIFY_CONTRACT_NOT_DECLARED",
        "warning",
        {"algorithm_name": "demo"},
    )
    with pytest.raises(AssertionError, match="unknown code"):
        assert_refs_match_schema(unknown)


@pytest.mark.parametrize("code", sorted(NEW_VERIFY_CODES))
def test_verify_codes_are_declared_as_verify_pipeline(code):
    spec = CODE_REGISTRY[code]
    assert spec.emit_tier == "verify_pipeline"
    assert spec.for_llm is not None
    assert spec.example_dsl
    assert spec.required_fields()


@pytest.mark.parametrize("code", sorted(STRUCTURAL_VERIFY_CODES))
def test_structural_verify_codes_keep_structural_contract(code):
    spec = CODE_REGISTRY[code]
    assert spec.capability == "pure_static"
    assert "algorithm_name" in spec.required_fields()
    assert spec.refs_schema["verification_scope"].enum == ("topological_only",)


@pytest.mark.parametrize("code", sorted(SMT_LOCAL_VERIFY_CODES))
def test_smt_verify_codes_keep_solver_contract(code):
    spec = CODE_REGISTRY[code]
    assert spec.capability == "requires_solver"
    assert "algorithm_name" in spec.required_fields()
    assert spec.refs_schema["verification_scope"].enum == ("smt_local",)


@pytest.mark.parametrize("code", sorted(NEW_VERIFY_CODES))
def test_verify_example_dsl_parses_and_default_inspect_does_not_emit_code(code):
    spec = CODE_REGISTRY[code]
    machine = _parse(spec.example_dsl)
    report = inspect_model(machine)
    assert code not in {diag.code for diag in report.diagnostics}


@pytest.mark.parametrize("code", sorted(NEW_VERIFY_CODES))
def test_verify_refs_contract_is_backed_by_real_dsl_evidence(code):
    spec = CODE_REGISTRY[code]
    diag = _diag(code, spec.severity, _refs_for_code(code))
    assert_refs_match_schema(diag, context=code)


def test_event_unreachable_emit_consumer_count_comes_from_topology_evidence():
    refs = _structural_refs_from_example("W_EVENT_UNREACHABLE_EMIT")
    machine = _parse(CODE_REGISTRY["W_EVENT_UNREACHABLE_EMIT"].example_dsl)
    graph = topology.build_leaf_level_macro_graph(machine)
    reachability = topology._event_consumer_reachability(machine, graph)
    event_reachability = reachability[refs["event_name"]]
    unreachable_count = sum(1 for reachable in event_reachability if not reachable)

    assert unreachable_count == 2
    assert refs["consumer_count"] == unreachable_count


def test_json_schema_keeps_verify_refs_extensible_via_codes_yaml_contract():
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "pyfcstm",
        "diagnostics",
        "schema.json",
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    refs_schema = schema["definitions"]["ModelDiagnostic"]["properties"]["refs"]
    assert refs_schema["additionalProperties"] is True
    assert "Structured payload declared in codes.yaml" in refs_schema["description"]
