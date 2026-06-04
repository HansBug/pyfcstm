import pytest

from test.testings.simulate_semantics import (
    iter_semantic_cases,
    run_generated_python_alignment_case,
)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    [case for case in iter_semantic_cases(runners=["generated_python_alignment"])],
    ids=lambda case: case.id,
)
def test_generated_python_alignment_semantic_fixture(case, caplog):
    run_generated_python_alignment_case(case, caplog=caplog)
