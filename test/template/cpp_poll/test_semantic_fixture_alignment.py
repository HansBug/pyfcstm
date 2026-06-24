from pathlib import Path

import pytest

from test.template.cpp_shared import _assert_wrapper_only_harness
from test.template.cpp_shared import run_cpp_alignment_case
from test.testings.native_toolchain_alignment.report import read_observations_jsonl
from test.testings.simulate_semantics import iter_semantic_cases, load_semantic_case


@pytest.mark.unittest
@pytest.mark.slow
@pytest.mark.parametrize(
    "case",
    iter_semantic_cases(),
    ids=lambda case: case.id,
)
def test_generated_cpp_poll_alignment_semantic_fixture(case, tmp_path):
    """
    Align one shared semantic fixture through the generated C++ poll wrapper.

    :param case: Shared semantic fixture case to render, compile, execute, and
        compare.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param tmp_path: Temporary artifact directory provided by pytest.
    :type tmp_path: pathlib.Path
    :return: ``None``.
    :rtype: None

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> case.id
        'design_basic_simple_transition'
    """
    run_cpp_alignment_case("cpp_poll", case, str(tmp_path))


@pytest.mark.unittest
@pytest.mark.slow
def test_generated_cpp_poll_alignment_harness_uses_wrapper_api(tmp_path):
    """
    Verify the C++ poll fixture harness uses only the wrapper public API.

    :param tmp_path: Temporary artifact directory provided by pytest.
    :type tmp_path: pathlib.Path
    :return: ``None``.
    :rtype: None

    Example::

        >>> _assert_wrapper_only_harness('#include "machine.hpp"\\n')
    """
    case = load_semantic_case("abstract_hook_ref_context_reports_callsite_metadata")
    artifacts = run_cpp_alignment_case("cpp_poll", case, str(tmp_path))
    harness_source = Path(artifacts.harness_dir, "harness.cpp").read_text(
        encoding="utf-8"
    )

    observations = read_observations_jsonl(artifacts.observations_path)
    assert all(item["api_return"] is None for item in observations)

    _assert_wrapper_only_harness(harness_source)
    assert "Wrapper::Vars" in harness_source
    assert "Wrapper::EventId" in harness_source
    assert "Wrapper::Hooks" in harness_source
    assert "Wrapper::EventChecks" in harness_source
    assert "Wrapper::ExecutionContext" in harness_source
    assert "Wrapper::EventContext" in harness_source
