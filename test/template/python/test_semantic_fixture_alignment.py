import pytest

from test.testings import simulate_semantics
from test.testings.simulate_semantics import (
    iter_semantic_cases,
    load_semantic_case,
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


@pytest.mark.unittest
def test_generated_python_alignment_uses_packaged_builtin_template(monkeypatch):
    calls = []
    real_extract_template = simulate_semantics.extract_template

    def wrapped_extract_template(name, output_dir):
        calls.append(name)
        return real_extract_template(name, output_dir)

    monkeypatch.setattr(
        simulate_semantics, "extract_template", wrapped_extract_template
    )

    run_generated_python_alignment_case(
        load_semantic_case("design_basic_simple_transition")
    )

    assert calls == ["python"]
