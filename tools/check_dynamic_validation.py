"""
Dynamically validate the simulation acceptance contract.

This maintenance command runs four fixed acceptance fixtures through the
repository simulation harness. The ``--check`` mode also proves that the
harness is live by copying one fixture into a temporary directory, changing
one explicit expected state, asserting that the copied case fails, and then
re-running the original fixtures unchanged.

Example::

    $ python tools/check_dynamic_validation.py --check
"""

import argparse
import copy
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple
from unittest.mock import patch

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from test.testings import simulate_semantics as semantic_harness  # noqa: E402

DEFAULT_CASES_ROOT = (
    REPOSITORY_ROOT / "test" / "fixtures" / "simulate_semantics" / "cases"
)
REQUIRED_CASE_IDS = (
    "design_validation_failure_multilevel_transition",
    "design_evented_pseudo_chain_invalid_then_valid",
    "expression_failure_transition_guard_raises_expression_error",
    "pseudo_self_loop_step_limit_raises_dfs_error",
)
MUTATION_CASE_ID = "design_validation_failure_multilevel_transition"
MUTATION_ORIGINAL_STATE = "Root.A"
MUTATED_STATE = "Root.Mutated"
PRODUCTION_HARNESS = "test.testings.simulate_semantics.run_simulation_case"
CASE_PROBLEMS = {
    "design_validation_failure_multilevel_transition": (
        "Reject a non-stoppable multilevel transition during speculative "
        "validation while preserving the active state and committed variables."
    ),
    "design_evented_pseudo_chain_invalid_then_valid": (
        "Reject an event-incomplete pseudo chain, then accept the path when both "
        "required events are supplied in one cycle."
    ),
    "expression_failure_transition_guard_raises_expression_error": (
        "Wrap transition-guard division by zero in "
        "SimulationRuntimeExpressionError with ZeroDivisionError as its cause "
        "while preserving the runtime snapshot."
    ),
    "pseudo_self_loop_step_limit_raises_dfs_error": (
        "Stop an unbounded pseudo-state self-loop at the speculative step limit "
        "with SimulationRuntimeDfsError and roll back the runtime snapshot."
    ),
}
EXPECTED_FIXTURE_SHA256 = {
    "design_validation_failure_multilevel_transition.yaml": (
        "cd40ed8699a9d80f0381a6738f2b28439832cb8b52fde144826f1c230af9b0a6"
    ),
    "design_validation_failure_multilevel_transition.fcstm": (
        "4ce8ae776d7efa0a9f00fa26097ac0eacd353501dbc03898114534fdf019353a"
    ),
    "design_evented_pseudo_chain_invalid_then_valid.yaml": (
        "7d87cd9115b5c1e968485e60c330bf6f3be16c044f550d0cdb6cafd7d5ae0c67"
    ),
    "design_evented_pseudo_chain_invalid_then_valid.fcstm": (
        "b1c533e360ae87558ef7cd56dca46b1b22df169784494f2d2f37384cdc839492"
    ),
    "expression_failure_transition_guard_raises_expression_error.yaml": (
        "e3715a5e3582c529405c74a0539dbb026173ad4ee650a3e75b322396ad2df2a4"
    ),
    "expression_failure_transition_guard_raises_expression_error.fcstm": (
        "6d332728477db215774b8d1fdaf3196d6e52a165f030eba407569841c3d3d263"
    ),
    "pseudo_self_loop_step_limit_raises_dfs_error.yaml": (
        "439d3b42c28a7d97dfaf2825d86dd8e80cf6a11895997124980769f585349fa7"
    ),
    "pseudo_self_loop_step_limit_raises_dfs_error.fcstm": (
        "3a0f79e2e12f4ff32ae11dabc5c48748931f9e5acf0e4947cc392a82cb5a0648"
    ),
}
REQUIRED_CASE_MATCHES = {
    "design_validation_failure_multilevel_transition": {
        "steps[3].expect.state": "Root.A",
        "steps[3].expect.vars.counter": 4,
        "steps[3].expect.vars.flag": 0,
    },
    "design_evented_pseudo_chain_invalid_then_valid": {
        "steps[2].expect.state": "Root.B.B1",
        "steps[2].expect.vars.counter": 112,
    },
    "expression_failure_transition_guard_raises_expression_error": {
        "steps[1].expect.state": "Root.A",
        "steps[1].expect.raises.type": "SimulationRuntimeExpressionError",
        "steps[1].expect.raises.cause_type": "ZeroDivisionError",
    },
    "pseudo_self_loop_step_limit_raises_dfs_error": {
        "steps[1].expect.state": "Root.A",
        "steps[1].expect.raises.type": "SimulationRuntimeDfsError",
    },
}


@dataclass(frozen=True)
class CaseResult:
    """
    Result for one dynamic semantic-fixture harness invocation.

    :param case_id: Semantic fixture id.
    :type case_id: str
    :param yaml_path: YAML fixture path passed to the harness.
    :type yaml_path: str
    :param status: Result status, either ``"passed"`` or ``"failed"``.
    :type status: str
    :param detected_problem: Problem exercised by the fixture, defaults to
        ``None``.
    :type detected_problem: typing.Optional[str], optional
    :param key_expected: Key expectations loaded from the fixture, defaults to
        ``None``.
    :type key_expected: typing.Optional[typing.Mapping[str, typing.Any]], optional
    :param actual: Values observed while the production harness ran, defaults
        to ``None``.
    :type actual: typing.Optional[typing.Mapping[str, typing.Any]], optional
    :param matched: Whether every key expectation matched, defaults to
        ``None``.
    :type matched: typing.Optional[bool], optional
    :param matched_evidence: Field-level expected/actual comparisons, defaults
        to an empty sequence.
    :type matched_evidence: typing.Sequence[typing.Mapping[str, typing.Any]], optional
    :param error_type: Optional failure exception class name, defaults to
        ``None``.
    :type error_type: typing.Optional[str], optional
    :param message: Optional failure message, defaults to ``None``.
    :type message: typing.Optional[str], optional
    :param raw_message: Optional unmodified harness failure message, defaults
        to ``None``.
    :type raw_message: typing.Optional[str], optional

    Example::

        >>> result = CaseResult("sample", "/tmp/sample.yaml", "passed")
        >>> result.to_json()["status"]
        'passed'
    """

    case_id: str
    yaml_path: str
    status: str
    detected_problem: Optional[str] = None
    key_expected: Optional[Mapping[str, Any]] = None
    actual: Optional[Mapping[str, Any]] = None
    matched: Optional[bool] = None
    matched_evidence: Sequence[Mapping[str, Any]] = ()
    error_type: Optional[str] = None
    message: Optional[str] = None
    raw_message: Optional[str] = None

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the result into a JSON-serializable mapping.

        :return: JSON-ready result data.
        :rtype: typing.Dict[str, typing.Any]

        Example::

            >>> CaseResult("sample", "/tmp/sample.yaml", "passed").to_json()["case_id"]
            'sample'
        """
        return {
            "case_id": self.case_id,
            "yaml_path": self.yaml_path,
            "status": self.status,
            "detected_problem": self.detected_problem,
            "key_expected": self.key_expected,
            "actual": self.actual,
            "matched": self.matched,
            "matched_evidence": [dict(item) for item in self.matched_evidence],
            "error_type": self.error_type,
            "message": self.message,
            "raw_message": self.raw_message,
        }


@dataclass(frozen=True)
class PhaseResult:
    """
    Result for one checker phase.

    :param name: Phase name.
    :type name: str
    :param status: Phase status, either ``"passed"`` or ``"failed"``.
    :type status: str
    :param cases: Case-level results collected during the phase.
    :type cases: typing.Sequence[CaseResult]
    :param message: Optional phase message, defaults to ``None``.
    :type message: typing.Optional[str], optional
    :param evidence: Optional phase-level evidence, defaults to ``None``.
    :type evidence: typing.Optional[typing.Mapping[str, typing.Any]], optional

    Example::

        >>> phase = PhaseResult("positive", "passed", ())
        >>> phase.to_json()["name"]
        'positive'
    """

    name: str
    status: str
    cases: Sequence[CaseResult]
    message: Optional[str] = None
    evidence: Optional[Mapping[str, Any]] = None

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the phase into a JSON-serializable mapping.

        :return: JSON-ready phase data.
        :rtype: typing.Dict[str, typing.Any]

        Example::

            >>> PhaseResult("positive", "passed", ()).to_json()["status"]
            'passed'
        """
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "cases": [case.to_json() for case in self.cases],
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class CheckerResult:
    """
    Complete dynamic-validation acceptance result.

    :param status: Overall status, either ``"passed"`` or ``"failed"``.
    :type status: str
    :param cases_root: Root directory containing semantic fixture cases.
    :type cases_root: str
    :param required_cases: Fixed case ids executed by the checker.
    :type required_cases: typing.Sequence[str]
    :param cases: Four fixed case results from the initial positive run.
    :type cases: typing.Sequence[CaseResult]
    :param phases: Phase results produced by the checker.
    :type phases: typing.Sequence[PhaseResult]
    :param source_fixture_integrity: Before/after SHA-256 evidence for every
        source YAML and FCSTM fixture.
    :type source_fixture_integrity: typing.Mapping[str, typing.Any]

    Example::

        >>> result = CheckerResult("passed", "/tmp/cases", ("sample",), (), (), {})
        >>> result.to_json()["required_cases"]
        ['sample']
    """

    status: str
    cases_root: str
    required_cases: Sequence[str]
    cases: Sequence[CaseResult]
    phases: Sequence[PhaseResult]
    source_fixture_integrity: Mapping[str, Any]

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the checker result into a JSON-serializable mapping.

        :return: JSON-ready checker result data.
        :rtype: typing.Dict[str, typing.Any]

        Example::

            >>> CheckerResult("passed", "/tmp/cases", (), (), (), {}).to_json()["status"]
            'passed'
        """
        return {
            "status": self.status,
            "cases_root": self.cases_root,
            "required_cases": list(self.required_cases),
            "production_harness": PRODUCTION_HARNESS,
            "cases": [case.to_json() for case in self.cases],
            "phases": [phase.to_json() for phase in self.phases],
            "source_fixture_integrity": self.source_fixture_integrity,
        }


def _case_yaml_path(cases_root: Path, case_id: str) -> Path:
    """
    Build the YAML path for a required semantic fixture id.

    :param cases_root: Directory containing ``*.yaml`` semantic cases.
    :type cases_root: pathlib.Path
    :param case_id: Fixture id without suffix.
    :type case_id: str
    :return: Path to the fixture YAML file.
    :rtype: pathlib.Path

    Example::

        >>> _case_yaml_path(Path('/tmp/cases'), 'sample')
        PosixPath('/tmp/cases/sample.yaml')
    """
    return cases_root / (case_id + ".yaml")


def _source_fixture_paths(cases_root: Path) -> Tuple[Path, ...]:
    """
    Return all source files used by the four fixed semantic cases.

    :param cases_root: Directory containing semantic case files.
    :type cases_root: pathlib.Path
    :return: YAML and paired FCSTM paths in fixed case order.
    :rtype: typing.Tuple[pathlib.Path, ...]

    Example::

        >>> paths = _source_fixture_paths(DEFAULT_CASES_ROOT)
        >>> len(paths)
        8
    """
    paths = []
    for case_id in REQUIRED_CASE_IDS:
        paths.append(cases_root / (case_id + ".yaml"))
        paths.append(cases_root / (case_id + ".fcstm"))
    return tuple(paths)


def _sha256_file(path: Path) -> str:
    """
    Compute the SHA-256 digest of one file without modifying it.

    :param path: File to hash.
    :type path: pathlib.Path
    :return: Lowercase hexadecimal SHA-256 digest.
    :rtype: str
    :raises OSError: If the file cannot be read.

    Example::

        >>> len(_sha256_file(DEFAULT_CASES_ROOT / (MUTATION_CASE_ID + '.yaml')))
        64
    """
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_source_hashes(cases_root: Path) -> Mapping[str, str]:
    """
    Capture SHA-256 digests for every fixed source fixture file.

    :param cases_root: Directory containing semantic case files.
    :type cases_root: pathlib.Path
    :return: Absolute file paths mapped to SHA-256 digests.
    :rtype: typing.Mapping[str, str]
    :raises OSError: If a source fixture cannot be read.

    Example::

        >>> hashes = _snapshot_source_hashes(DEFAULT_CASES_ROOT)
        >>> len(hashes)
        8
    """
    return {
        str(path.resolve()): _sha256_file(path)
        for path in _source_fixture_paths(cases_root)
    }


def _fixture_identity_evidence(cases_root: Path) -> Mapping[str, Any]:
    """
    Compare the fixed fixture files with their reviewed SHA-256 identities.

    :param cases_root: Directory containing semantic case files.
    :type cases_root: pathlib.Path
    :return: Per-file expected and actual SHA-256 evidence.
    :rtype: typing.Mapping[str, typing.Any]
    :raises OSError: If a required fixture cannot be read.

    Example::

        >>> _fixture_identity_evidence(DEFAULT_CASES_ROOT)["status"]
        'passed'
    """
    files = []
    for filename, expected in EXPECTED_FIXTURE_SHA256.items():
        path = cases_root / filename
        actual = _sha256_file(path)
        files.append(
            {
                "file": filename,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "matched": actual == expected,
            }
        )
    matched = all(item["matched"] for item in files)
    return {
        "status": "passed" if matched else "failed",
        "algorithm": "sha256",
        "files": files,
    }


def _source_integrity_evidence(
    before: Mapping[str, str], after: Mapping[str, str]
) -> Mapping[str, Any]:
    """
    Build before/after SHA-256 evidence for source fixtures.

    :param before: Digests captured before dynamic validation.
    :type before: typing.Mapping[str, str]
    :param after: Digests captured after dynamic validation.
    :type after: typing.Mapping[str, str]
    :return: JSON-ready source-integrity evidence.
    :rtype: typing.Mapping[str, typing.Any]
    :raises ValueError: If the before and after file sets differ.

    Example::

        >>> evidence = _source_integrity_evidence({'a': '1'}, {'a': '1'})
        >>> evidence['status']
        'passed'
    """
    if set(before) != set(after):
        raise ValueError("source fixture file set changed during validation")
    files = []
    for path in before:
        unchanged = before[path] == after[path]
        files.append(
            {
                "path": path,
                "before_sha256": before[path],
                "after_sha256": after[path],
                "unchanged": unchanged,
            }
        )
    all_unchanged = all(item["unchanged"] for item in files)
    return {
        "status": "passed" if all_unchanged else "failed",
        "algorithm": "sha256",
        "read_only": all_unchanged,
        "all_unchanged": all_unchanged,
        "files": files,
    }


def _exception_actual(error: BaseException) -> Mapping[str, Any]:
    """
    Serialize one exception and its explicit cause as harness evidence.

    :param error: Exception observed by the production harness.
    :type error: BaseException
    :return: Exception type, message, and optional cause details.
    :rtype: typing.Mapping[str, typing.Any]

    Example::

        >>> error = RuntimeError('outer')
        >>> _exception_actual(error)['type']
        'RuntimeError'
    """
    cause = error.__cause__
    cause_data = None
    if cause is not None:
        cause_data = {"type": type(cause).__name__, "message": str(cause)}
    return {
        "type": type(error).__name__,
        "message": str(error),
        "cause": cause_data,
    }


def _runtime_actual(
    runtime: Any,
    expect: Mapping[str, Any],
    handler_calls: Optional[Sequence[Mapping[str, Any]]],
) -> Mapping[str, Any]:
    """
    Capture the public runtime values checked by one harness expectation.

    :param runtime: Production :class:`pyfcstm.simulate.SimulationRuntime`.
    :type runtime: typing.Any
    :param expect: Fixture expectation being asserted by the harness.
    :type expect: typing.Mapping[str, typing.Any]
    :param handler_calls: Optional handler records passed to the harness.
    :type handler_calls: typing.Optional[typing.Sequence[typing.Mapping[str, typing.Any]]]
    :return: JSON-ready observed values for fields present in ``expect``.
    :rtype: typing.Mapping[str, typing.Any]

    Example::

        >>> _runtime_actual(type('R', (), {'is_ended': True, 'vars': {}})(), {'ended': True}, None)
        {'ended': True}
    """
    actual = {}
    if "ended" in expect:
        actual["ended"] = bool(runtime.is_ended)
    if "state" in expect:
        if runtime.is_ended or runtime.current_state is None:
            actual["state"] = None
        else:
            actual["state"] = ".".join(runtime.current_state.path)

    runtime_vars = dict(runtime.vars)
    if "vars" in expect:
        actual["vars"] = {name: runtime_vars.get(name) for name in dict(expect["vars"])}
    if "vars_exact" in expect:
        actual["vars_exact"] = runtime_vars
    if "vars_keys" in expect:
        actual["vars_keys"] = sorted(runtime_vars)
    if "vars_absent" in expect:
        actual["vars_absent"] = [
            name for name in expect["vars_absent"] if name not in runtime_vars
        ]
    if "handler_calls" in expect:
        actual["handler_calls"] = semantic_harness._normalize_handler_call_records(
            handler_calls or ()
        )
    return actual


def _run_production_harness(
    case: semantic_harness.SemanticCase,
    observations: Dict[str, Dict[str, Any]],
) -> None:
    """
    Run the production harness while observing its assertion inputs.

    The wrappers call the original assertion helpers unchanged. They only
    serialize the actual runtime and exception objects supplied by those
    helpers, so pass/fail remains owned by
    :func:`test.testings.simulate_semantics.run_simulation_case`.

    :param case: Loaded semantic fixture.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param observations: Mutable field-path map populated during the run.
    :type observations: typing.Dict[str, typing.Dict[str, typing.Any]]
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If the production harness detects a mismatch.
    :raises test.testings.simulate_semantics.SemanticCaseError: If runtime-only
        expectations lack required fixture setup.

    Example::

        >>> case = semantic_harness.load_semantic_case(MUTATION_CASE_ID)
        >>> observed = {}
        >>> _run_production_harness(case, observed)
        >>> 'steps[0].expect' in observed
        True
    """
    original_exception_assertion = semantic_harness._assert_exception
    original_runtime_assertion = semantic_harness._assert_runtime_expectation

    def observe_exception(error, expect, fixture, field_path):
        expectation_path = field_path[: -len(".raises")]
        observations.setdefault(expectation_path, {})["raises"] = _exception_actual(
            error
        )
        original_exception_assertion(error, expect, fixture, field_path)

    def observe_runtime(runtime, expect, fixture, field_path, handler_calls=None):
        observations.setdefault(field_path, {}).update(
            _runtime_actual(runtime, expect, handler_calls)
        )
        original_runtime_assertion(
            runtime,
            expect,
            fixture,
            field_path,
            handler_calls=handler_calls,
        )

    with patch.object(semantic_harness, "_assert_exception", observe_exception):
        with patch.object(
            semantic_harness, "_assert_runtime_expectation", observe_runtime
        ):
            semantic_harness.run_simulation_case(case)


def _key_expected(case: semantic_harness.SemanticCase) -> Mapping[str, Any]:
    """
    Extract the key step expectations from a loaded fixture.

    :param case: Loaded semantic fixture.
    :type case: test.testings.simulate_semantics.SemanticCase
    :return: JSON-ready expected values in fixture step order.
    :rtype: typing.Mapping[str, typing.Any]

    Example::

        >>> case = semantic_harness.load_semantic_case(MUTATION_CASE_ID)
        >>> _key_expected(case)['steps'][0]['expect']['state']
        'Root.A'
    """
    steps = []
    for index, step in enumerate(case.data.get("steps") or []):
        steps.append(
            {
                "step": index,
                "field_path": "steps[%d].expect" % index,
                "cycle": copy.deepcopy(step.get("cycle", [])),
                "expect": copy.deepcopy(dict(step.get("expect") or {})),
            }
        )
    return {"source": str(Path(case.yaml_path).resolve()), "steps": steps}


def _actual_report(
    case: semantic_harness.SemanticCase,
    observations: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    """
    Arrange production-harness observations in fixture step order.

    :param case: Loaded semantic fixture.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param observations: Actual values captured by expectation field path.
    :type observations: typing.Mapping[str, typing.Mapping[str, typing.Any]]
    :return: JSON-ready actual values and their production source.
    :rtype: typing.Mapping[str, typing.Any]

    Example::

        >>> case = semantic_harness.load_semantic_case(MUTATION_CASE_ID)
        >>> _actual_report(case, {})['source'] == PRODUCTION_HARNESS
        True
    """
    steps = []
    for index, step in enumerate(case.data.get("steps") or []):
        field_path = "steps[%d].expect" % index
        steps.append(
            {
                "step": index,
                "field_path": field_path,
                "cycle": copy.deepcopy(step.get("cycle", [])),
                "observed": copy.deepcopy(dict(observations.get(field_path, {}))),
            }
        )
    return {"source": PRODUCTION_HARNESS, "steps": steps}


def _text_matches(actual: str, expected: str, match_kind: str) -> bool:
    """
    Apply the production fixture contract's text-match semantics.

    :param actual: Actual exception or cause message.
    :type actual: str
    :param expected: Expected substring or regular expression.
    :type expected: str
    :param match_kind: Either ``"substring"`` or ``"regex"``.
    :type match_kind: str
    :return: Whether the actual text satisfies the expectation.
    :rtype: bool
    :raises ValueError: If ``match_kind`` is unsupported.
    :raises re.error: If a regex expectation is invalid.

    Example::

        >>> _text_matches('division by zero', 'division', 'substring')
        True
    """
    if match_kind == "substring":
        return expected in actual
    if match_kind == "regex":
        return re.search(expected, actual) is not None
    raise ValueError("unsupported match kind: %r" % match_kind)


def _match_item(
    field_path: str, expected: Any, actual: Any, matched: bool
) -> Mapping[str, Any]:
    """
    Build one JSON-ready expected/actual match record.

    :param field_path: Fixture field represented by the comparison.
    :type field_path: str
    :param expected: Expected value or match expression.
    :type expected: typing.Any
    :param actual: Actual value supplied by the production harness.
    :type actual: typing.Any
    :param matched: Whether the comparison succeeded.
    :type matched: bool
    :return: Field-level matched evidence.
    :rtype: typing.Mapping[str, typing.Any]

    Example::

        >>> _match_item('state', 'Root.A', 'Root.A', True)['matched']
        True
    """
    return {
        "field": field_path,
        "expected": expected,
        "actual": actual,
        "matched": matched,
    }


def _exception_match_evidence(
    field_path: str,
    expected: Mapping[str, Any],
    actual: Any,
) -> Sequence[Mapping[str, Any]]:
    """
    Compare one fixture ``raises`` contract with an observed exception.

    :param field_path: Path to the fixture ``raises`` mapping.
    :type field_path: str
    :param expected: Expected exception type, message, and optional cause.
    :type expected: typing.Mapping[str, typing.Any]
    :param actual: Serialized observed exception or ``None``.
    :type actual: typing.Any
    :return: Field-level exception match evidence.
    :rtype: typing.Sequence[typing.Mapping[str, typing.Any]]

    Example::

        >>> evidence = _exception_match_evidence('raises', {'type': 'ValueError'}, {'type': 'ValueError', 'message': '', 'cause': None})
        >>> evidence[0]['matched']
        True
    """
    actual_exception = actual if isinstance(actual, Mapping) else {}
    actual_type = actual_exception.get("type")
    actual_message = str(actual_exception.get("message", ""))
    evidence = [
        _match_item(
            field_path + ".type",
            expected["type"],
            actual_type,
            actual_type == expected["type"],
        )
    ]
    if "match" in expected:
        match_kind = str(expected.get("match_kind", "substring"))
        match_text = str(expected["match"])
        evidence.append(
            _match_item(
                field_path + ".match",
                {"kind": match_kind, "text": match_text},
                actual_message,
                _text_matches(actual_message, match_text, match_kind),
            )
        )

    cause = actual_exception.get("cause")
    actual_cause = cause if isinstance(cause, Mapping) else {}
    if "cause_type" in expected:
        actual_cause_type = actual_cause.get("type")
        evidence.append(
            _match_item(
                field_path + ".cause_type",
                expected["cause_type"],
                actual_cause_type,
                actual_cause_type == expected["cause_type"],
            )
        )
    if "cause_match" in expected:
        cause_match_kind = str(expected.get("cause_match_kind", "substring"))
        cause_match_text = str(expected["cause_match"])
        actual_cause_message = str(actual_cause.get("message", ""))
        evidence.append(
            _match_item(
                field_path + ".cause_match",
                {"kind": cause_match_kind, "text": cause_match_text},
                actual_cause_message,
                _text_matches(
                    actual_cause_message,
                    cause_match_text,
                    cause_match_kind,
                ),
            )
        )
    return tuple(evidence)


def _matched_evidence(
    case: semantic_harness.SemanticCase,
    observations: Mapping[str, Mapping[str, Any]],
) -> Sequence[Mapping[str, Any]]:
    """
    Compare all key fixture expectations with harness observations.

    :param case: Loaded semantic fixture.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param observations: Actual values captured by expectation field path.
    :type observations: typing.Mapping[str, typing.Mapping[str, typing.Any]]
    :return: Field-level expected/actual match evidence.
    :rtype: typing.Sequence[typing.Mapping[str, typing.Any]]

    Example::

        >>> case = semantic_harness.load_semantic_case(MUTATION_CASE_ID)
        >>> _matched_evidence(case, {})[0]['matched']
        False
    """
    evidence = []
    for index, step in enumerate(case.data.get("steps") or []):
        base_path = "steps[%d].expect" % index
        expect = dict(step.get("expect") or {})
        actual = dict(observations.get(base_path, {}))
        for field_name in ("state", "ended", "vars_exact", "vars_keys", "vars_absent"):
            if field_name in expect:
                actual_value = actual.get(field_name)
                evidence.append(
                    _match_item(
                        base_path + "." + field_name,
                        expect[field_name],
                        actual_value,
                        actual_value == expect[field_name],
                    )
                )
        if "vars" in expect:
            actual_vars = actual.get("vars")
            actual_vars = actual_vars if isinstance(actual_vars, Mapping) else {}
            for name, expected_value in dict(expect["vars"]).items():
                actual_value = actual_vars.get(name)
                evidence.append(
                    _match_item(
                        base_path + ".vars." + name,
                        expected_value,
                        actual_value,
                        actual_value == expected_value,
                    )
                )
        if "handler_calls" in expect:
            actual_calls = actual.get("handler_calls")
            evidence.append(
                _match_item(
                    base_path + ".handler_calls",
                    expect["handler_calls"],
                    actual_calls,
                    actual_calls == expect["handler_calls"],
                )
            )
        if "raises" in expect:
            evidence.extend(
                _exception_match_evidence(
                    base_path + ".raises",
                    expect["raises"],
                    actual.get("raises"),
                )
            )
    return tuple(evidence)


def _run_case(yaml_path: Path, record_contract: bool = True) -> CaseResult:
    """
    Run one semantic fixture through the production simulation harness.

    :param yaml_path: Path to a semantic fixture YAML file.
    :type yaml_path: pathlib.Path
    :param record_contract: Whether to capture expected, actual, and matched
        evidence, defaults to ``True``.
    :type record_contract: bool, optional
    :return: Case execution result.
    :rtype: CaseResult
    :raises pyfcstm.dsl.error.GrammarParseError: If fixture DSL parsing fails
        unexpectedly outside the semantic harness contract.
    :raises pyfcstm.utils.validate.ModelValidationError: If model validation
        fails unexpectedly outside the semantic harness contract.

    Example::

        >>> path = DEFAULT_CASES_ROOT / 'design_evented_pseudo_chain_invalid_then_valid.yaml'
        >>> _run_case(path).status
        'passed'
    """
    case_id = yaml_path.stem
    case = None
    observations = {}
    error_type = None
    message = None
    try:
        case = semantic_harness.load_semantic_case(str(yaml_path))
        if record_contract:
            _run_production_harness(case, observations)
        else:
            semantic_harness.run_simulation_case(case)
    except AssertionError as err:
        # AssertionError is the production harness signal for expectation mismatches.
        error_type = "AssertionError"
        message = str(err)
    except semantic_harness.SemanticCaseError as err:
        # SemanticCaseError is the production loader signal for malformed fixtures.
        error_type = "SemanticCaseError"
        message = str(err)
    except OSError as err:
        # OSError covers explicit YAML and FCSTM reads performed by the loader.
        error_type = type(err).__name__
        message = str(err)

    status = "failed" if error_type is not None else "passed"
    if case is None or not record_contract:
        return CaseResult(
            case_id=case_id,
            yaml_path=str(yaml_path),
            status=status,
            error_type=error_type,
            message=message,
            raw_message=message,
        )

    evidence = _matched_evidence(case, observations)
    matched = bool(evidence) and all(item["matched"] for item in evidence)
    if status == "passed" and not matched:
        status = "failed"
        error_type = "CheckerEvidenceError"
        message = "production harness passed but captured evidence did not match"
    return CaseResult(
        case_id=case_id,
        yaml_path=str(yaml_path),
        status=status,
        detected_problem=CASE_PROBLEMS.get(case_id),
        key_expected=_key_expected(case),
        actual=_actual_report(case, observations),
        matched=matched,
        matched_evidence=evidence,
        error_type=error_type,
        message=message,
        raw_message=message,
    )


def _run_required_cases(cases_root: Path) -> Tuple[CaseResult, ...]:
    """
    Run all fixed dynamic-validation acceptance fixtures.

    :param cases_root: Directory containing the required cases.
    :type cases_root: pathlib.Path
    :return: Case results in fixed contract order.
    :rtype: typing.Tuple[CaseResult, ...]

    Example::

        >>> results = _run_required_cases(DEFAULT_CASES_ROOT)
        >>> len(results) == len(REQUIRED_CASE_IDS)
        True
    """
    results = []
    for case_id in REQUIRED_CASE_IDS:
        result = _run_case(_case_yaml_path(cases_root, case_id))
        evidence = {item["field"]: item for item in result.matched_evidence}
        missing_or_mismatched = []
        for field, expected in REQUIRED_CASE_MATCHES[case_id].items():
            item = evidence.get(field)
            if (
                item is None
                or item.get("actual") != expected
                or item.get("matched") is not True
            ):
                missing_or_mismatched.append(field)
        if result.status == "passed" and missing_or_mismatched:
            result = replace(
                result,
                status="failed",
                matched=False,
                error_type="CheckerContractError",
                message=(
                    "required case evidence missing or mismatched: {0}".format(
                        ", ".join(missing_or_mismatched)
                    )
                ),
            )
        results.append(result)
    return tuple(results)


def _phase_from_cases(name: str, cases: Sequence[CaseResult]) -> PhaseResult:
    """
    Summarize a phase from its case results.

    :param name: Phase name.
    :type name: str
    :param cases: Case-level results collected during the phase.
    :type cases: typing.Sequence[CaseResult]
    :return: Phase result with aggregate pass/fail status.
    :rtype: PhaseResult

    Example::

        >>> phase = _phase_from_cases('sample', (CaseResult('c', '/tmp/c.yaml', 'passed'),))
        >>> phase.status
        'passed'
    """
    failed = [case for case in cases if case.status != "passed"]
    if failed:
        return PhaseResult(name, "failed", cases, "%d case(s) failed" % len(failed))
    return PhaseResult(name, "passed", cases)


def _read_yaml_mapping(path: Path) -> Mapping[str, Any]:
    """
    Read one YAML file as a mapping.

    :param path: YAML file path.
    :type path: pathlib.Path
    :return: Parsed YAML mapping.
    :rtype: typing.Mapping[str, typing.Any]
    :raises ValueError: If the YAML document is not a mapping.
    :raises yaml.YAMLError: If PyYAML cannot parse the document.
    :raises OSError: If the file cannot be read.

    Example::

        >>> data = _read_yaml_mapping(DEFAULT_CASES_ROOT / 'design_validation_failure_multilevel_transition.yaml')
        >>> isinstance(data, dict)
        True
    """
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, Mapping):
        raise ValueError("%s must contain a YAML mapping" % path)
    return data


def _write_yaml_mapping(path: Path, data: Mapping[str, Any]) -> None:
    """
    Write one YAML mapping to disk.

    :param path: Destination YAML path.
    :type path: pathlib.Path
    :param data: YAML mapping to serialize.
    :type data: typing.Mapping[str, typing.Any]
    :return: ``None``.
    :rtype: None
    :raises yaml.YAMLError: If PyYAML cannot serialize the mapping.
    :raises OSError: If the file cannot be written.

    Example::

        >>> with TemporaryDirectory() as tmp:
        ...     target = Path(tmp) / 'sample.yaml'
        ...     _write_yaml_mapping(target, {'title': 'sample'})
        ...     target.is_file()
        True
    """
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(dict(data), file, allow_unicode=True, sort_keys=False)


def _copy_case_to_temp(cases_root: Path, case_id: str, temp_root: Path) -> Path:
    """
    Copy one semantic fixture YAML and paired FCSTM source to a temp root.

    :param cases_root: Source case directory.
    :type cases_root: pathlib.Path
    :param case_id: Fixture id to copy.
    :type case_id: str
    :param temp_root: Temporary destination directory.
    :type temp_root: pathlib.Path
    :return: Path to the copied YAML fixture.
    :rtype: pathlib.Path
    :raises OSError: If either fixture file cannot be copied.

    Example::

        >>> with TemporaryDirectory() as tmp:
        ...     copied = _copy_case_to_temp(DEFAULT_CASES_ROOT, MUTATION_CASE_ID, Path(tmp))
        ...     copied.name
        'design_validation_failure_multilevel_transition.yaml'
    """
    source_yaml = _case_yaml_path(cases_root, case_id)
    source_fcstm = cases_root / (case_id + ".fcstm")
    target_yaml = temp_root / source_yaml.name
    target_fcstm = temp_root / source_fcstm.name
    shutil.copy2(str(source_yaml), str(target_yaml))
    shutil.copy2(str(source_fcstm), str(target_fcstm))
    return target_yaml


def _mutate_expected_state(yaml_path: Path) -> str:
    """
    Change the first explicit expected state in a copied fixture.

    :param yaml_path: Copied YAML fixture path to mutate.
    :type yaml_path: pathlib.Path
    :return: Original expected state value.
    :rtype: str
    :raises ValueError: If the copied fixture does not contain an explicit state
        expectation to mutate.
    :raises yaml.YAMLError: If PyYAML cannot parse or serialize the fixture.
    :raises OSError: If the copied fixture cannot be read or written.

    Example::

        >>> with TemporaryDirectory() as tmp:
        ...     copied = _copy_case_to_temp(DEFAULT_CASES_ROOT, MUTATION_CASE_ID, Path(tmp))
        ...     _mutate_expected_state(copied)
        'Root.A'
    """
    data = copy.deepcopy(dict(_read_yaml_mapping(yaml_path)))
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise ValueError("%s has no steps list to mutate" % yaml_path)
    for step in steps:
        if not isinstance(step, dict):
            continue
        expect = step.get("expect")
        if isinstance(expect, dict) and isinstance(expect.get("state"), str):
            original = expect["state"]
            expect["state"] = MUTATED_STATE
            _write_yaml_mapping(yaml_path, data)
            return original
    raise ValueError("%s has no explicit expected state to mutate" % yaml_path)


def _run_mutation_check(cases_root: Path) -> PhaseResult:
    """
    Prove that a copied and deliberately corrupted fixture fails the harness.

    :param cases_root: Directory containing the original semantic cases.
    :type cases_root: pathlib.Path
    :return: Mutation phase result.
    :rtype: PhaseResult
    :raises ValueError: If the mutation target has no state expectation.
    :raises yaml.YAMLError: If PyYAML cannot read or write the copied fixture.
    :raises OSError: If temporary fixture copying or file IO fails.

    Example::

        >>> phase = _run_mutation_check(DEFAULT_CASES_ROOT)
        >>> phase.status
        'passed'
    """
    with TemporaryDirectory(prefix="dynamic-validation-") as temp_directory:
        temp_root = Path(temp_directory)
        copied_yaml = _copy_case_to_temp(cases_root, MUTATION_CASE_ID, temp_root)
        original_state = _mutate_expected_state(copied_yaml)
        copied_yaml_path = str(copied_yaml)
        result = _run_case(copied_yaml, record_contract=False)

    raw_message = result.raw_message or ""
    diagnostic_message = "%s; original=%s; mutated=%s" % (
        raw_message,
        original_state,
        MUTATED_STATE,
    )
    expected_original_tuple = repr(tuple(MUTATION_ORIGINAL_STATE.split(".")))
    expected_mutated_tuple = repr(tuple(MUTATED_STATE.split(".")))
    evidence = (
        _match_item(
            "error_type",
            "AssertionError",
            result.error_type,
            result.error_type == "AssertionError",
        ),
        _match_item(
            "original_expected_state",
            MUTATION_ORIGINAL_STATE,
            original_state,
            original_state == MUTATION_ORIGINAL_STATE,
        ),
        _match_item(
            "message.case_id",
            MUTATION_CASE_ID,
            diagnostic_message,
            MUTATION_CASE_ID in diagnostic_message,
        ),
        _match_item(
            "message.expectation_path",
            "steps[0].expect state mismatch",
            diagnostic_message,
            "steps[0].expect state mismatch" in diagnostic_message,
        ),
        _match_item(
            "message.original_state",
            MUTATION_ORIGINAL_STATE,
            diagnostic_message,
            MUTATION_ORIGINAL_STATE in diagnostic_message,
        ),
        _match_item(
            "message.mutated_state",
            MUTATED_STATE,
            diagnostic_message,
            MUTATED_STATE in diagnostic_message,
        ),
        _match_item(
            "raw_message.actual_state",
            expected_original_tuple,
            raw_message,
            expected_original_tuple in raw_message,
        ),
        _match_item(
            "raw_message.expected_state",
            expected_mutated_tuple,
            raw_message,
            expected_mutated_tuple in raw_message,
        ),
    )
    accepted = all(item["matched"] for item in evidence)
    result = replace(
        result,
        detected_problem=(
            "Prove that the production harness rejects a copied fixture whose "
            "first explicit state expectation is deliberately corrupted."
        ),
        key_expected={
            "error_type": "AssertionError",
            "message_contains": [
                MUTATION_CASE_ID,
                "steps[0].expect state mismatch",
                MUTATION_ORIGINAL_STATE,
                MUTATED_STATE,
            ],
        },
        actual={
            "source": PRODUCTION_HARNESS,
            "error_type": result.error_type,
            "message": diagnostic_message,
            "raw_message": raw_message,
        },
        matched=accepted,
        matched_evidence=evidence,
        message=diagnostic_message,
        raw_message=raw_message,
    )
    phase_evidence = {
        "source_fixture": str(_case_yaml_path(cases_root, MUTATION_CASE_ID)),
        "temporary_copy": copied_yaml_path,
        "source_fixture_modified": False,
        "original_expected_state": original_state,
        "mutated_expected_state": MUTATED_STATE,
        "accepted_failure": accepted,
    }
    if accepted:
        return PhaseResult(
            "negative_mutation",
            "passed",
            (result,),
            "temporary mutation produced the exact required assertion mismatch",
            phase_evidence,
        )
    failed_checks = [item["field"] for item in evidence if not item["matched"]]
    return PhaseResult(
        "negative_mutation",
        "failed",
        (result,),
        "mutation rejection did not satisfy strict checks: %s"
        % ", ".join(failed_checks),
        phase_evidence,
    )


def run_checker(cases_root: Path, check: bool) -> CheckerResult:
    """
    Run the dynamic-validation acceptance checker.

    :param cases_root: Directory containing semantic fixture cases.
    :type cases_root: pathlib.Path
    :param check: Whether to run the positive, negative mutation, and final
        positive self-check phases.
    :type check: bool
    :return: Complete checker result.
    :rtype: CheckerResult
    :raises ValueError: If the mutation check cannot find a state expectation.
    :raises yaml.YAMLError: If PyYAML cannot read or write a fixture during the
        mutation check.
    :raises OSError: If fixture or report file IO fails during the check.

    Example::

        >>> result = run_checker(DEFAULT_CASES_ROOT, False)
        >>> result.status
        'passed'
    """
    before_hashes = _snapshot_source_hashes(cases_root)
    identity = _fixture_identity_evidence(cases_root)
    phases = [
        PhaseResult(
            "fixture_identity",
            identity["status"],
            (),
            "all fixed fixture SHA-256 identities match"
            if identity["status"] == "passed"
            else "one or more fixed fixture SHA-256 identities differ",
            identity,
        )
    ]
    initial_cases = ()
    if phases[-1].status == "passed":
        initial_cases = _run_required_cases(cases_root)
        phases.append(_phase_from_cases("positive", initial_cases))
        if phases[-1].status == "passed" and check:
            phases.append(_run_mutation_check(cases_root))
            final_cases = _run_required_cases(cases_root)
            phases.append(_phase_from_cases("positive_after_mutation", final_cases))

    after_hashes = _snapshot_source_hashes(cases_root)
    integrity = _source_integrity_evidence(before_hashes, after_hashes)
    phases.append(
        PhaseResult(
            "source_fixture_integrity",
            integrity["status"],
            (),
            "all source YAML and FCSTM SHA-256 digests are unchanged"
            if integrity["status"] == "passed"
            else "one or more source fixture SHA-256 digests changed",
            integrity,
        )
    )
    overall = (
        "passed"
        if phases and all(phase.status == "passed" for phase in phases)
        else "failed"
    )
    return CheckerResult(
        status=overall,
        cases_root=str(cases_root),
        required_cases=REQUIRED_CASE_IDS,
        cases=initial_cases,
        phases=tuple(phases),
        source_fixture_integrity=integrity,
    )


def _build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser

    Example::

        >>> parser = _build_parser()
        >>> parser.parse_args([]).check
        False
    """
    parser = argparse.ArgumentParser(
        description="Dynamically validate the simulation acceptance contract."
    )
    parser.add_argument(
        "--cases-root",
        default=str(DEFAULT_CASES_ROOT),
        help="semantic cases directory, defaults to test/fixtures/simulate_semantics/cases",
    )
    parser.add_argument(
        "--report",
        help="optional path where the JSON report should be written",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="run positive, mutation-negative, and final positive self-check phases",
    )
    return parser


def _validate_report_destination(report_path: Optional[str], cases_root: Path) -> None:
    """
    Prevent JSON report writes inside the source fixture directory.

    :param report_path: Optional report destination supplied by the caller.
    :type report_path: typing.Optional[str]
    :param cases_root: Source semantic fixture directory.
    :type cases_root: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises ValueError: If the report destination is inside ``cases_root``.

    Example::

        >>> _validate_report_destination(None, DEFAULT_CASES_ROOT)
    """
    if report_path is None:
        return
    destination = Path(report_path).resolve()
    try:
        destination.relative_to(cases_root.resolve())
    except ValueError:
        # Path.relative_to raises ValueError when destination is outside cases_root.
        return
    raise ValueError(
        "report path must be outside the read-only source fixture directory: %s"
        % destination
    )


def _emit_report(result: CheckerResult, report_path: Optional[str]) -> None:
    """
    Print and optionally write the checker JSON report.

    :param result: Checker result to serialize.
    :type result: CheckerResult
    :param report_path: Optional destination path for the JSON report.
    :type report_path: typing.Optional[str]
    :return: ``None``.
    :rtype: None
    :raises OSError: If the optional report file cannot be written.

    Example::

        >>> result = CheckerResult('passed', '/tmp/cases', (), (), (), {})
        >>> _emit_report(result, None)  # doctest: +ELLIPSIS
        {...
    """
    report = result.to_json()
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if report_path:
        with open(report_path, "w", encoding="utf-8") as file:
            file.write(text)
            file.write("\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the command-line interface.

    :param argv: Optional command-line argument sequence, defaults to
        ``None`` so :mod:`argparse` reads :data:`sys.argv`.
    :type argv: typing.Optional[typing.Sequence[str]], optional
    :return: Process exit code, ``0`` on success and ``1`` on checker failure.
    :rtype: int
    :raises ValueError: If the mutation check cannot find a state expectation.
    :raises yaml.YAMLError: If PyYAML cannot parse or serialize a fixture.
    :raises OSError: If fixture or report file IO fails.

    Example::

        >>> main([])  # doctest: +SKIP
        0
    """
    args = _build_parser().parse_args(argv)
    cases_root = Path(args.cases_root).resolve()
    _validate_report_destination(args.report, cases_root)
    result = run_checker(cases_root, args.check)
    _emit_report(result, args.report)
    if result.status == "passed":
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
