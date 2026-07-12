import os
import hashlib
import pkgutil
import re

import pytest

import pyfcstm.llm as llm
from pyfcstm.llm import _resources as guide_resources
from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.model import load_state_machine_from_text


_FCSTM_BLOCK_RE = re.compile(r"```fcstm\n(.*?)\n```", re.DOTALL)
_INVALID_FCSTM_BLOCK_RE = re.compile(r"```fcstm-invalid\n(.*?)\n```", re.DOTALL)


def _resource_loader(resources):
    return lambda package, resource: resources.get(resource)


@pytest.mark.unittest
def test_grammar_guide_prompt_api_returns_packaged_text():
    guide = llm.get_grammar_guide_prompt_for_llm()

    assert guide.startswith("# FCSTM Grammar Guide for LLMs")
    assert "\r" not in guide
    assert "`=>` and `implies`" in guide
    assert ": /GlobalEvent" in guide
    assert "Combo transition triggers are ordered `+` chains" in guide
    assert "S -> T :: E + [x > 0]" in guide
    assert "Do not combine event syntax and guard syntax" not in guide
    assert "Do not use `^` for\nboolean xor" in guide
    assert "pseudo state Bypass;" in guide
    assert "enter ref /SharedInit;" in guide
    assert ">> during after abstract PublishSnapshot;" in guide


@pytest.mark.unittest
def test_grammar_guide_prompt_is_available_as_package_data():
    data = pkgutil.get_data(llm.__name__, "fcstm_grammar_guide.md")
    checksum = pkgutil.get_data(llm.__name__, "fcstm_grammar_guide.md.sha256")
    guide = llm.get_grammar_guide_prompt_for_llm()

    assert data is not None
    assert checksum is not None
    assert data.decode("utf-8").splitlines() == guide.splitlines()


@pytest.mark.unittest
def test_grammar_guide_prompt_normalizes_crlf_resource(monkeypatch):
    raw_text = "# FCSTM\r\n\r\n## Section\r\nUse `=>`.\r\n"
    expected_text = "# FCSTM\n\n## Section\nUse `=>`.\n"
    expected_digest = hashlib.sha256(expected_text.encode("utf-8")).hexdigest()

    monkeypatch.setattr(
        guide_resources.pkgutil,
        "get_data",
        _resource_loader(
            {
                "fcstm_grammar_guide.md": raw_text.encode("utf-8"),
                "fcstm_grammar_guide.md.sha256": expected_digest.encode("utf-8"),
            }
        ),
    )

    guide = llm.get_grammar_guide_prompt_for_llm()
    metadata = llm.get_grammar_guide_prompt_metadata_for_llm()

    assert guide == expected_text
    assert "\r" not in guide
    assert metadata["byte_size"] == len(expected_text.encode("utf-8"))
    assert metadata["line_count"] == len(expected_text.splitlines())
    assert metadata["chapter_count"] == 1
    assert metadata["sha256"] == expected_digest
    assert metadata["expected_sha256"] == expected_digest


@pytest.mark.unittest
def test_grammar_guide_prompt_reports_missing_packaged_resource(monkeypatch):
    monkeypatch.setattr(guide_resources.pkgutil, "get_data", _resource_loader({}))

    with pytest.raises(FileNotFoundError) as err_info:
        llm.get_grammar_guide_prompt_for_llm()

    message = str(err_info.value)
    assert "fcstm_grammar_guide.md" in message
    assert "was not found" in message


@pytest.mark.unittest
def test_grammar_guide_prompt_reports_missing_checksum_resource(monkeypatch):
    guide = "# FCSTM\n"
    monkeypatch.setattr(
        guide_resources.pkgutil,
        "get_data",
        _resource_loader({"fcstm_grammar_guide.md": guide.encode("utf-8")}),
    )

    with pytest.raises(llm.GrammarGuidePromptIntegrityError) as err_info:
        llm.get_grammar_guide_prompt_for_llm()

    message = str(err_info.value)
    assert "integrity verification failed" in message
    assert "fcstm_grammar_guide.md.sha256" in message
    assert "run `make sha256`" in message
    assert "reinstall pyfcstm" in message


@pytest.mark.unittest
def test_grammar_guide_prompt_reports_malformed_checksum_resource(monkeypatch):
    monkeypatch.setattr(
        guide_resources.pkgutil,
        "get_data",
        _resource_loader(
            {
                "fcstm_grammar_guide.md": b"# FCSTM\n",
                "fcstm_grammar_guide.md.sha256": b"not-a-sha256\n",
            }
        ),
    )

    with pytest.raises(llm.GrammarGuidePromptIntegrityError) as err_info:
        llm.get_grammar_guide_prompt_for_llm()

    message = str(err_info.value)
    assert "integrity verification failed" in message
    assert "malformed" in message
    assert "64-character SHA-256" in message


@pytest.mark.unittest
def test_grammar_guide_prompt_reports_checksum_mismatch(monkeypatch):
    monkeypatch.setattr(
        guide_resources.pkgutil,
        "get_data",
        _resource_loader(
            {
                "fcstm_grammar_guide.md": b"# FCSTM\n",
                "fcstm_grammar_guide.md.sha256": (64 * "0").encode("utf-8"),
            }
        ),
    )

    with pytest.raises(llm.GrammarGuidePromptIntegrityError) as err_info:
        llm.get_grammar_guide_prompt_for_llm()

    message = str(err_info.value)
    assert "expected SHA-256" in message
    assert "computed" in message
    assert "LF-normalized packaged prompt" in message


@pytest.mark.unittest
def test_grammar_guide_prompt_can_warn_on_checksum_mismatch(monkeypatch):
    monkeypatch.setattr(
        guide_resources.pkgutil,
        "get_data",
        _resource_loader(
            {
                "fcstm_grammar_guide.md": b"# FCSTM\n",
                "fcstm_grammar_guide.md.sha256": (64 * "0").encode("utf-8"),
            }
        ),
    )

    with pytest.warns(RuntimeWarning) as warnings:
        guide = llm.get_grammar_guide_prompt_for_llm(raise_on_integrity_error=False)

    assert guide == "# FCSTM\n"
    assert "integrity verification failed" in str(warnings[0].message)


@pytest.mark.unittest
def test_grammar_guide_metadata_can_warn_on_checksum_mismatch(monkeypatch):
    monkeypatch.setattr(
        guide_resources.pkgutil,
        "get_data",
        _resource_loader(
            {
                "fcstm_grammar_guide.md": b"# FCSTM\n",
                "fcstm_grammar_guide.md.sha256": (64 * "0").encode("utf-8"),
            }
        ),
    )

    with pytest.warns(RuntimeWarning) as warnings:
        metadata = llm.get_grammar_guide_prompt_metadata_for_llm(
            raise_on_integrity_error=False
        )

    assert metadata["sha256"] == hashlib.sha256(b"# FCSTM\n").hexdigest()
    assert metadata["expected_sha256"] == 64 * "0"
    assert "integrity verification failed" in str(warnings[0].message)


@pytest.mark.unittest
def test_grammar_guide_prompt_path_points_to_packaged_markdown():
    guide_path = llm.get_grammar_guide_prompt_path_for_llm()

    assert os.path.basename(guide_path) == "fcstm_grammar_guide.md"
    assert os.path.isfile(guide_path)


@pytest.mark.unittest
def test_grammar_guide_prompt_path_error_is_actionable(monkeypatch):
    monkeypatch.setattr(guide_resources.os.path, "isfile", lambda path: False)

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
    expected_sections = {
        "## Output Contract",
        "## Top-Level Structure",
        "## State Definitions",
        "## Transitions",
        "## Nested State Targets",
        "## Events",
        "## Forced Transitions",
        "## Lifecycle Actions",
        "## Aspect Actions",
        "## Expressions",
        "## Cycle Semantics",
        "## LLM Modeling Strategy",
        "## Worked Protocol Example",
        "## Invalid Forms To Avoid",
        "## Pre-Output Checklist",
    }
    actual_sections = {line for line in guide.splitlines() if line.startswith("## ")}

    assert metadata["resource_name"] == "fcstm_grammar_guide.md"
    assert metadata["byte_size"] == len(guide.encode("utf-8"))
    assert metadata["line_count"] == len(guide.splitlines())
    assert metadata["chapter_count"] == sum(
        1 for line in guide.splitlines() if line.startswith("## ")
    )
    assert actual_sections == expected_sections
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])


@pytest.mark.unittest
def test_grammar_guide_positive_examples_parse_and_validate():
    guide = llm.get_grammar_guide_prompt_for_llm()
    examples = _FCSTM_BLOCK_RE.findall(guide)

    assert len(examples) >= 4
    for index, example in enumerate(examples, start=1):
        model = load_state_machine_from_text(example, path=os.getcwd())
        assert model.root_state is not None, (
            f"example {index} did not build a root state"
        )


@pytest.mark.unittest
def test_grammar_guide_invalid_examples_are_rejected():
    guide = llm.get_grammar_guide_prompt_for_llm()
    examples = _INVALID_FCSTM_BLOCK_RE.findall(guide)

    assert len(examples) >= 3
    for example in examples:
        with pytest.raises((GrammarParseError, SyntaxError, ValueError)):
            load_state_machine_from_text(example, path=os.getcwd())
