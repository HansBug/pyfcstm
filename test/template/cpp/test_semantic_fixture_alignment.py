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
def test_generated_cpp_alignment_semantic_fixture(case, tmp_path):
    run_cpp_alignment_case("cpp", case, str(tmp_path))


@pytest.mark.unittest
@pytest.mark.slow
def test_generated_cpp_alignment_harness_uses_wrapper_api(tmp_path):
    case = load_semantic_case("abstract_hook_ref_context_reports_callsite_metadata")
    artifacts = run_cpp_alignment_case("cpp", case, str(tmp_path))
    harness_source = Path(artifacts.harness_dir, "harness.cpp").read_text(
        encoding="utf-8"
    )

    observations = read_observations_jsonl(artifacts.observations_path)
    assert all(item["api_return"] is None for item in observations)

    _assert_wrapper_only_harness(harness_source)
    assert "Wrapper::Vars" in harness_source
    assert "Wrapper::EventId" in harness_source
    assert "Wrapper::Hooks" in harness_source
    assert "Wrapper::ExecutionContext" in harness_source
