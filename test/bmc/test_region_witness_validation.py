"""Public constructors of the witness and call-record types reject malformed region fields."""

import pytest
import z3

from pyfcstm.bmc import BmcBuildError
from pyfcstm.bmc.relation import BmcAbstractCallRecord
from pyfcstm.bmc.witness import (
    BmcRuntimeFrame,
    BmcWitnessCallRecord,
    BmcWitnessFrame,
    BmcWitnessLocalCase,
    BmcWitnessStep,
)

pytestmark = pytest.mark.unittest

LABEL = "Root.A.P::fallback::Root.A.P::0"


@pytest.mark.parametrize(
    "scope, kind, label",
    [
        ("", "fallback", LABEL),
        (3, "fallback", LABEL),
        ("Root.A", "", LABEL),
        ("Root.A", "fallback", ""),
        ("Root.A", "fallback", "not-a-label"),
    ],
)
def test_a_local_case_with_a_malformed_field_is_refused(scope, kind, label):
    with pytest.raises(BmcBuildError):
        BmcWitnessLocalCase(scope, kind, label)


def test_a_local_case_reports_the_scope_and_the_ends_of_its_label():
    case = BmcWitnessLocalCase(None, "initial", "__init__::initial::Root.Idle::0")
    assert (case.scope, case.source, case.target) == (None, "__init__", "Root.Idle")


def snapshot_record(**extra):
    return BmcAbstractCallRecord(
        0, "A", "during", "leaf_during", "Root", "Root", None, {"x": z3.Int("x")}, **extra
    )


@pytest.mark.parametrize("scope_path", ["", 3])
def test_an_abstract_call_record_with_a_malformed_scope_is_refused(scope_path):
    with pytest.raises(BmcBuildError):
        snapshot_record(scope_path=scope_path)


def test_an_abstract_call_record_lists_its_region_fields_when_they_are_set():
    plain = snapshot_record().to_canonical()
    assert "scope_path" not in plain and "stack_states" not in plain
    scoped = snapshot_record(
        scope_path="Root.A", stack_states=["Root.A.P"]
    ).to_canonical()
    assert scoped["scope_path"] == "Root.A"
    assert scoped["stack_states"] == ["Root.A.P"]


@pytest.mark.parametrize("configuration", ["", 3])
def test_a_witness_call_record_with_a_malformed_configuration_is_refused(configuration):
    with pytest.raises(BmcBuildError):
        BmcWitnessCallRecord(
            0, "A", "during", "leaf_during", "Root", "Root", None, {}, configuration
        )


@pytest.mark.parametrize("configuration", ["", 3])
def test_a_runtime_frame_with_a_malformed_configuration_is_refused(configuration):
    with pytest.raises(BmcBuildError):
        BmcRuntimeFrame(0, "Root", False, {}, configuration)


@pytest.mark.parametrize(
    "sentinel, configuration",
    [("init", "Root{A: P}"), (None, ""), (None, 3)],
)
def test_a_witness_frame_with_a_misplaced_configuration_is_refused(
    sentinel, configuration
):
    with pytest.raises(BmcBuildError):
        BmcWitnessFrame(0, None, None, sentinel, False, {}, configuration)


def step(case_label, local_cases):
    return BmcWitnessStep(
        0, 0, 1, case_label, "transition", "progress", None, None, False, False,
        local_cases=local_cases,
    )


@pytest.mark.parametrize(
    "case_label, local_cases",
    [
        (None, None),
        ("Root::initial::Root.A::0", (BmcWitnessLocalCase(None, "initial", "a::b::c::0"),)),
        (None, ("not a case",)),
    ],
)
def test_a_witness_step_with_inconsistent_local_cases_is_refused(
    case_label, local_cases
):
    with pytest.raises(BmcBuildError):
        step(case_label, local_cases)


def test_an_action_block_lists_the_stack_of_its_unit_only_when_it_is_set():
    from pyfcstm.bmc.macro import ActionBlock

    plain = ActionBlock("state_action", "leaf_during", 1, "Root", ())
    assert "stack_states" not in plain.to_canonical()
    stacked = ActionBlock(
        "state_action", "leaf_during", 1, "Root", (), stack_states=("Root.A.P",)
    )
    assert stacked.to_canonical()["stack_states"] == ["Root.A.P"]
