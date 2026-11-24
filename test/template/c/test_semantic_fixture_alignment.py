import pytest

from test.testings.native_semantic_alignment import (
    GENERATED_C_ALIGNMENT,
    iter_native_semantic_cases,
    run_native_alignment_case_subprocess,
)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    # The shared generated-runtime subset, plus the region corpus once the
    # template declares the ``region`` feature.
    iter_native_semantic_cases("c"),
    ids=lambda case: case.id,
)
def test_generated_c_alignment_semantic_fixture(case):
    result = run_native_alignment_case_subprocess(GENERATED_C_ALIGNMENT, case.id)

    assert result.status == "passed", result.message
    assert result.classification is None
