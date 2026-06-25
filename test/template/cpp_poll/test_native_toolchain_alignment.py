import os

import pytest

from test.testings.native_toolchain_alignment import (
    ARTIFACT_DIR_ENV_VAR,
    resolve_selected_profile,
    run_native_toolchain_case,
)
from test.testings.simulate_semantics import load_semantic_case


@pytest.mark.native_toolchain
def test_generated_cpp_poll_native_toolchain_alignment(
    native_semantic_case_id, request, tmp_path
):
    """
    Align a shared semantic fixture through the C++ poll native matrix.

    :param native_semantic_case_id: Shared semantic fixture case id selected by
        the native matrix pytest parametrization.
    :type native_semantic_case_id: str
    :param request: Pytest request object used for profile resolution.
    :type request: pytest.FixtureRequest
    :param tmp_path: Temporary artifact root for this pytest invocation.
    :type tmp_path: pathlib.Path
    :return: ``None``.
    :rtype: None

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> case.id
        'design_basic_simple_transition'
    """
    profile = resolve_selected_profile(request.config)
    artifact_root = os.environ.get(ARTIFACT_DIR_ENV_VAR) or str(tmp_path / "artifacts")
    result = run_native_toolchain_case(
        "cpp_poll",
        load_semantic_case(native_semantic_case_id),
        profile,
        artifact_root,
    )

    assert result["status"] == "passed", result["message"]
    expected_classification = (
        "analysis_report_only" if result.get("report_only") else "passed"
    )
    assert result["classification"] == expected_classification
    assert "harness" in result["artifact_paths"]
    assert "generated" in result["artifact_paths"]
