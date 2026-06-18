import pytest

from test.testings.native_semantic_alignment import (
    GENERATED_C_ALIGNMENT,
    run_native_alignment_case_subprocess,
)
from test.testings.simulate_semantics import iter_semantic_cases


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    iter_semantic_cases(),
    ids=lambda case: case.id,
)
def test_generated_c_alignment_semantic_fixture(case):
    result = run_native_alignment_case_subprocess(GENERATED_C_ALIGNMENT, case.id)

    assert result.status == "passed", result.message
    assert result.classification is None
    assert result.expected_classification is None
    assert result.support is None
    assert result.tracking is None
