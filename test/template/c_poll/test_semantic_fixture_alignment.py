import pytest

from test.testings.native_semantic_alignment import (
    GENERATED_C_POLL_ALIGNMENT,
    run_native_alignment_case,
    run_native_alignment_case_subprocess,
)
from test.testings.simulate_semantics import load_semantic_case


@pytest.mark.unittest
def test_generated_c_poll_alignment_shared_fixture_smoke():
    case = load_semantic_case("design_basic_simple_transition")

    result = run_native_alignment_case(GENERATED_C_POLL_ALIGNMENT, case)

    assert result.status == "passed"
    assert result.classification is None


@pytest.mark.unittest
def test_generated_c_poll_alignment_subprocess_reports_known_native_failure():
    result = run_native_alignment_case_subprocess(
        GENERATED_C_POLL_ALIGNMENT, "aspect_context_reports_active_leaf"
    )

    assert result.status == "expected_failure"
    assert result.classification == "handler_mismatch"
    assert result.expected_classification == "handler_mismatch"
    assert result.support == "expected_failure"
    assert result.tracking == "https://github.com/HansBug/pyfcstm/issues/218"
