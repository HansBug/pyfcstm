"""Unit tests for inspect presentation renderers."""

import json
import textwrap

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.diagnostics.inspect_render import (
    INSPECT_LLM_DRAFT_SCHEMA_VERSION,
    inspect_output_suffix_warning,
    render_inspect_human,
    render_inspect_llm_json,
    render_inspect_llm_markdown,
)
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine


SOURCE = textwrap.dedent(
    """
    def int x = 0;
    state Root {
        state Idle;
        state Running;
        [*] -> Idle;
        Idle -> Running : if [x > 0 && x < 0];
    }
    """
).strip()


def _report():
    ast = parse_with_grammar_entry(SOURCE, "state_machine_dsl")
    machine = parse_dsl_node_to_state_machine(ast)
    return inspect_model(machine)


@pytest.mark.unittest
class TestInspectRender:
    def test_human_renderer_contains_summary_location_and_guidance(self):
        text = render_inspect_human(_report(), SOURCE, input_path="case.fcstm")

        assert "FCSTM Inspect Report: case.fcstm" in text
        assert "status: warning" in text
        assert "diagnostics: 0 errors" in text
        assert "W_UNWRITTEN_READ_VAR" in text
        assert "case.fcstm:" in text
        assert "^" in text
        assert "suggested actions:" in text
        assert "do not:" in text

    def test_llm_json_renderer_is_draft_and_actionable(self):
        payload = json.loads(render_inspect_llm_json(_report(), SOURCE))

        assert payload["schema_version"] == INSPECT_LLM_DRAFT_SCHEMA_VERSION
        assert payload["schema_status"] == "draft"
        assert payload["status"] == "warning"
        assert payload["diagnostics"]
        diagnostic = payload["diagnostics"][0]
        assert {"code", "severity", "message", "refs"} <= set(diagnostic)
        assert "recommended_actions" in diagnostic
        assert "do_not" in diagnostic

    def test_llm_markdown_renderer_contains_draft_schema_and_sections(self):
        text = render_inspect_llm_markdown(_report(), SOURCE)

        assert "# FCSTM Inspect Report" in text
        assert INSPECT_LLM_DRAFT_SCHEMA_VERSION in text
        assert "## W_" in text
        assert "Recommended actions" in text

    @pytest.mark.parametrize(
        ("path", "output_format", "expected"),
        [
            ("report.json", "human", "--format json"),
            ("report.md", "json", "--format llm-md"),
            ("report.md", "llm-json", "--format llm-md"),
            ("report.json", "llm-md", "--format llm-json"),
            ("report.txt", "human", None),
            ("report.json", "json", None),
        ],
    )
    def test_suffix_warning_policy(self, path, output_format, expected):
        warning = inspect_output_suffix_warning(path, output_format)
        if expected is None:
            assert warning is None
        else:
            assert expected in warning
