import os

import pytest

from test.testings.native_toolchain_alignment import (
    ARTIFACT_DIR_ENV_VAR,
    resolve_selected_profile,
    run_native_toolchain_case,
)
from test.testings.simulate_semantics import load_semantic_case


@pytest.mark.native_toolchain
def test_generated_c_poll_native_toolchain_alignment(
    native_semantic_case_id, request, tmp_path
):
    profile = resolve_selected_profile(request.config)
    artifact_root = os.environ.get(ARTIFACT_DIR_ENV_VAR) or str(tmp_path / "artifacts")
    result = run_native_toolchain_case(
        "c_poll",
        load_semantic_case(native_semantic_case_id),
        profile,
        artifact_root,
    )

    assert result["status"] == "passed", result["message"]
    expected_classification = (
        "analysis_report_only" if result.get("report_only") else "passed"
    )
    assert result["classification"] == expected_classification
