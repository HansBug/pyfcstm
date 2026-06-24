import re
from pathlib import Path

import pytest

from test.template.cpp_shared import run_cpp_alignment_case
from test.testings.simulate_semantics import iter_semantic_cases, load_semantic_case


@pytest.mark.unittest
@pytest.mark.slow
@pytest.mark.parametrize(
    "case",
    iter_semantic_cases(),
    ids=lambda case: case.id,
)
def test_generated_cpp_poll_alignment_semantic_fixture(case, tmp_path):
    run_cpp_alignment_case("cpp_poll", case, str(tmp_path / case.id))


@pytest.mark.unittest
@pytest.mark.slow
def test_generated_cpp_poll_alignment_harness_uses_wrapper_api(tmp_path):
    case = load_semantic_case("design_basic_simple_transition")
    artifacts = run_cpp_alignment_case("cpp_poll", case, str(tmp_path / case.id))
    harness_source = Path(artifacts.harness_dir, "harness.cpp").read_text(
        encoding="utf-8"
    )

    assert '#include "machine.hpp"' in harness_source
    assert '#include "machine.h"' not in harness_source
    assert "native_handle" not in harness_source
    assert not re.search(
        r"\b[A-Za-z_][A-Za-z0-9_]*Machine_(init|hot_start|cycle|set_hooks|set_event_checks)\s*\(",
        harness_source,
    )
