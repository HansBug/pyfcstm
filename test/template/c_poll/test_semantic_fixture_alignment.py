import pytest

from test.testings.native_semantic_alignment import (
    GENERATED_C_POLL_ALIGNMENT,
    run_native_alignment_case_subprocess,
)
from test.testings.simulate_semantics import iter_semantic_cases


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    # C-family backends consume the shared generated-runtime fixture subset.
    iter_semantic_cases(runners=["generated_python_alignment"]),
    ids=lambda case: case.id,
)
def test_generated_c_poll_alignment_semantic_fixture(case):
    result = run_native_alignment_case_subprocess(GENERATED_C_POLL_ALIGNMENT, case.id)

    assert result.status == "passed", result.message
    assert result.classification is None
