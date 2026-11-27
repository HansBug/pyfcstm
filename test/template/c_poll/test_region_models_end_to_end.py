"""The models with regions of the end-to-end checks, run through the generated ``c_poll`` runtime."""

import pytest

from test.end_to_end import MODEL_CASES
from test.testings.native_semantic_alignment import (
    GENERATED_C_POLL_ALIGNMENT,
    run_native_alignment_case_subprocess,
)

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize("case_id", MODEL_CASES)
def test_generated_runtime_follows_the_simulator_on_the_end_to_end_models(case_id):
    """The generated ``c_poll`` runtime agrees with the simulator after every cycle of the scenario."""
    result = run_native_alignment_case_subprocess(GENERATED_C_POLL_ALIGNMENT, case_id)
    assert result.status == "passed", result.message
