import os
import pkgutil
import re

import pytest

import pyfcstm.llm as llm
from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.model import load_state_machine_from_text


_FCSTM_BLOCK_RE = re.compile(r"```fcstm\n(.*?)\n```", re.DOTALL)
_INVALID_FCSTM_BLOCK_RE = re.compile(r"```fcstm-invalid\n(.*?)\n```", re.DOTALL)


@pytest.mark.unittest
def test_grammar_guide_prompt_api_returns_packaged_text():
    guide = llm.get_grammar_guide_prompt_for_llm()

    assert guide.startswith("# FCSTM Grammar Guide for LLMs")
    assert "`=>` and `implies`" in guide
    assert ": /GlobalEvent" in guide
    assert "Do not use `^` for\nboolean xor" in guide


@pytest.mark.unittest
def test_grammar_guide_prompt_is_available_as_package_data():
    data = pkgutil.get_data(llm.__name__, "fcstm_grammar_guide.md")

    assert data is not None
    assert data.decode("utf-8") == llm.get_grammar_guide_prompt_for_llm()


@pytest.mark.unittest
def test_grammar_guide_prompt_path_points_to_packaged_markdown():
    guide_path = llm.get_grammar_guide_prompt_path_for_llm()

    assert os.path.basename(guide_path) == "fcstm_grammar_guide.md"
    assert os.path.isfile(guide_path)


@pytest.mark.unittest
def test_grammar_guide_prompt_path_error_is_actionable(monkeypatch):
    monkeypatch.setattr(llm, "__file__", os.path.join(os.sep, "missing", "__init__.py"))

    with pytest.raises(llm.GrammarGuidePromptPathUnavailableError) as err_info:
        llm.get_grammar_guide_prompt_path_for_llm()

    message = str(err_info.value)
    assert "fcstm_grammar_guide.md" in message
    assert "filesystem path" in message
    assert "get_grammar_guide_prompt_for_llm()" in message


@pytest.mark.unittest
def test_grammar_guide_prompt_metadata_is_deterministic():
    guide = llm.get_grammar_guide_prompt_for_llm()
    metadata = llm.get_grammar_guide_prompt_metadata_for_llm()

    assert metadata["resource_name"] == "fcstm_grammar_guide.md"
    assert metadata["byte_size"] == len(guide.encode("utf-8"))
    assert metadata["line_count"] == len(guide.splitlines())
    assert metadata["chapter_count"] == sum(
        1 for line in guide.splitlines() if line.startswith("## ")
    )
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])


@pytest.mark.unittest
def test_grammar_guide_positive_examples_parse_and_validate():
    guide = llm.get_grammar_guide_prompt_for_llm()
    examples = _FCSTM_BLOCK_RE.findall(guide)

    assert len(examples) >= 4
    for index, example in enumerate(examples, start=1):
        model = load_state_machine_from_text(example, path=os.getcwd())
        assert model.root_state is not None, f"example {index} did not build a root state"


@pytest.mark.unittest
def test_grammar_guide_invalid_examples_are_rejected():
    guide = llm.get_grammar_guide_prompt_for_llm()
    examples = _INVALID_FCSTM_BLOCK_RE.findall(guide)

    assert len(examples) >= 3
    for example in examples:
        with pytest.raises((GrammarParseError, SyntaxError, ValueError)):
            load_state_machine_from_text(example, path=os.getcwd())
