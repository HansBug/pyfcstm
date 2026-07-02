"""Unit tests for inspect presentation renderers."""

import json
import os
import re
import textwrap
from typing import Any, List, Mapping

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.diagnostics.inspect_render import (
    HumanRenderOptions,
    INSPECT_LLM_SCHEMA_VERSION,
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
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
BOX_DRAWING_RE = re.compile(r"[\u2500-\u257f]")
SOURCE_EXCERPT_RE = re.compile(r"\s+\d+ \|")


def _report():
    ast = parse_with_grammar_entry(SOURCE, "state_machine_dsl")
    machine = parse_dsl_node_to_state_machine(ast)
    return inspect_model(machine)


def _assert_excerpt_gutters_align(text):
    lines = text.splitlines()
    excerpt_count = 0
    for index, line in enumerate(lines):
        if SOURCE_EXCERPT_RE.match(line):
            excerpt_count += 1
            pipe_column = line.index("|")
            assert index > 0
            assert index + 1 < len(lines)
            assert lines[index - 1].index("|") == pipe_column
            assert lines[index + 1].index("|") == pipe_column
    assert excerpt_count > 0


def _assert_markdown_excerpt_gutters_align(text):
    lines = text.splitlines()
    caret_count = 0
    for index, line in enumerate(lines[:-1]):
        if SOURCE_EXCERPT_RE.match(line) and "^" in lines[index + 1]:
            caret_count += 1
            assert line.index("|") == lines[index + 1].index("|")
    assert caret_count > 0


def _schema_node_by_ref(schema, ref):
    assert ref.startswith("#/")
    node = schema
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _schema_type_matches(value, expected):
    expected_types = expected if isinstance(expected, list) else [expected]
    for expected_type in expected_types:
        if expected_type == "null" and value is None:
            return True
        if expected_type == "string" and isinstance(value, str):
            return True
        if expected_type == "boolean" and isinstance(value, bool):
            return True
        if (
            expected_type == "integer"
            and isinstance(value, int)
            and not isinstance(value, bool)
        ):
            return True
        if expected_type == "array" and isinstance(value, list):
            return True
        if (
            expected_type == "object"
            and isinstance(value, dict)
            and not isinstance(value, list)
        ):
            return True
    return False


def _schema_errors(
    schema_root: Mapping[str, Any],
    schema_node: Mapping[str, Any],
    value: Any,
    path: str = "$",
) -> List[str]:
    if "$ref" in schema_node:
        return _schema_errors(
            schema_root,
            _schema_node_by_ref(schema_root, schema_node["$ref"]),
            value,
            path,
        )

    if "oneOf" in schema_node:
        branch_errors = [
            _schema_errors(schema_root, branch, value, path)
            for branch in schema_node["oneOf"]
        ]
        matches = [errors for errors in branch_errors if not errors]
        if len(matches) != 1:
            return [f"{path}: expected exactly one oneOf branch to match"]
        return []

    errors = []
    if "type" in schema_node and not _schema_type_matches(value, schema_node["type"]):
        return [f"{path}: expected type {schema_node['type']!r}"]
    if "const" in schema_node and value != schema_node["const"]:
        errors.append(f"{path}: expected const {schema_node['const']!r}")
    if "enum" in schema_node and value not in schema_node["enum"]:
        errors.append(f"{path}: expected one of {schema_node['enum']!r}")
    if "minimum" in schema_node and value < schema_node["minimum"]:
        errors.append(f"{path}: expected minimum {schema_node['minimum']!r}")

    if isinstance(value, dict):
        required = set(schema_node.get("required", []))
        missing = sorted(required - set(value))
        for key in missing:
            errors.append(f"{path}: missing required property {key!r}")
        properties = schema_node.get("properties", {})
        if schema_node.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            for key in extras:
                errors.append(f"{path}: unexpected property {key!r}")
        for key, child_schema in properties.items():
            if key in value:
                errors.extend(
                    _schema_errors(
                        schema_root,
                        child_schema,
                        value[key],
                        f"{path}.{key}",
                    )
                )

    if isinstance(value, list) and "items" in schema_node:
        for index, item in enumerate(value):
            errors.extend(
                _schema_errors(
                    schema_root, schema_node["items"], item, f"{path}[{index}]"
                )
            )
    return errors


@pytest.mark.unittest
class TestInspectRender:
    def test_human_renderer_contains_checker_style_location_and_guidance(self):
        text = render_inspect_human(_report(), SOURCE, input_path="case.fcstm")

        assert "[WARN] FCSTM Inspect Report: case.fcstm" in text
        assert "status: warning" in text
        assert "diagnostics: 0 errors" in text
        assert "W_UNWRITTEN_READ_VAR" in text
        assert "--> case.fcstm:" in text
        assert "|" in text
        assert "^" in text
        assert "= source: inspect-static" in text
        assert "= why:" in text
        assert "= fix:" in text
        assert "= do-not:" in text
        assert ANSI_ESCAPE_RE.search(text) is None
        assert BOX_DRAWING_RE.search(text) is None
        _assert_excerpt_gutters_align(text)
        assert " 3 |     state Idle;" in text
        assert " 4 |     state Running;" in text
        assert " 5 |     [*] -> Idle;" in text

    def test_human_renderer_color_enabled_adds_ansi_without_losing_text(self):
        text = render_inspect_human(
            _report(),
            SOURCE,
            input_path="case.fcstm",
            options=HumanRenderOptions(color_enabled=True),
        )

        assert ANSI_ESCAPE_RE.search(text) is not None
        plain = ANSI_ESCAPE_RE.sub("", text)
        assert "[WARN] FCSTM Inspect Report: case.fcstm" in plain
        assert "W_UNWRITTEN_READ_VAR" in plain
        assert "= source: inspect-static" in plain

    def test_human_renderer_without_span_still_renders_guidance(self):
        from pyfcstm.utils.validate import ModelDiagnostic

        report = _report()
        diagnostic = ModelDiagnostic(
            code="W_DEADLOCK_LEAF",
            severity="warning",
            message="Synthetic diagnostic without span.",
            span=None,
            refs={},
        )
        report = type(report)(
            root_state_path=report.root_state_path,
            variables=report.variables,
            states=report.states,
            transitions=report.transitions,
            events=report.events,
            actions=report.actions,
            metrics=report.metrics,
            reachability_graph=report.reachability_graph,
            event_emission_map=report.event_emission_map,
            var_dataflow=report.var_dataflow,
            aspect_impact_map=report.aspect_impact_map,
            action_ref_graph=report.action_ref_graph,
            combo_transitions=report.combo_transitions,
            combo_origins=report.combo_origins,
            forced_transitions=report.forced_transitions,
            diagnostics=(diagnostic,),
        )

        text = render_inspect_human(report, SOURCE, input_path="case.fcstm")

        assert "[WARN] W_DEADLOCK_LEAF" in text
        assert "-->" not in text
        assert "= source: inspect-static" in text
        assert "= why:" in text

    def test_human_renderer_empty_diagnostics_reports_ok_state(self):
        report = _report()
        report = type(report)(
            root_state_path=report.root_state_path,
            variables=report.variables,
            states=report.states,
            transitions=report.transitions,
            events=report.events,
            actions=report.actions,
            metrics=report.metrics,
            reachability_graph=report.reachability_graph,
            event_emission_map=report.event_emission_map,
            var_dataflow=report.var_dataflow,
            aspect_impact_map=report.aspect_impact_map,
            action_ref_graph=report.action_ref_graph,
            combo_transitions=report.combo_transitions,
            combo_origins=report.combo_origins,
            forced_transitions=report.forced_transitions,
            diagnostics=(),
        )

        text = render_inspect_human(report, SOURCE, input_path="case.fcstm")

        assert "[OK] FCSTM Inspect Report: case.fcstm" in text
        assert "status: ok" in text
        assert "No diagnostics." in text
        assert ANSI_ESCAPE_RE.search(text) is None

    def test_llm_json_renderer_is_stable_and_actionable(self):
        payload = json.loads(render_inspect_llm_json(_report(), SOURCE))

        assert payload["schema_version"] == INSPECT_LLM_SCHEMA_VERSION
        assert payload["schema_status"] == "stable"
        assert payload["status"] == "warning"
        assert payload["diagnostics"]
        diagnostic = payload["diagnostics"][0]
        assert {"code", "severity", "message", "refs"} <= set(diagnostic)
        assert payload["repair_protocol"]["rules"]
        assert "recommended_actions" in diagnostic
        assert "do_not" in diagnostic
        assert "provenance" in diagnostic
        assert diagnostic["provenance"]["kind"] == diagnostic["source"]
        assert "repair_guidance" in diagnostic
        deadlock = next(
            item for item in payload["diagnostics"] if item["code"] == "W_DEADLOCK_LEAF"
        )
        context = deadlock["source_excerpt"]["context"]
        assert [line["line"] for line in context] == [3, 4, 5]
        assert context[0]["caret"] is None
        assert context[1]["is_anchor"] is True
        assert context[1]["caret"].strip("^") == "    "
        assert context[2]["text"] == "    [*] -> Idle;"

    def test_llm_json_schema_contract_matches_payload_shape(self):
        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "pyfcstm",
            "diagnostics",
            "inspect_llm_report_schema.json",
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        payload = json.loads(render_inspect_llm_json(_report(), SOURCE))

        assert schema["title"] == "FCSTM Inspect LLM Report"
        assert (
            schema["properties"]["schema_version"]["const"]
            == INSPECT_LLM_SCHEMA_VERSION
        )
        assert schema["properties"]["schema_status"]["const"] == "stable"
        assert set(schema["required"]).issubset(set(payload.keys()))
        diagnostic_required = set(schema["definitions"]["Diagnostic"]["required"])
        for diagnostic in payload["diagnostics"]:
            assert diagnostic_required.issubset(set(diagnostic.keys()))
            assert diagnostic["provenance"]["kind"] == diagnostic["source"]

        schema_errors = _schema_errors(schema, schema, payload)
        assert schema_errors == []

    def test_llm_markdown_renderer_contains_stable_schema_and_sections(self):
        text = render_inspect_llm_markdown(_report(), SOURCE)

        assert "# FCSTM Inspect Report" in text
        assert INSPECT_LLM_SCHEMA_VERSION in text
        assert "Schema status: `stable`" in text
        assert "## Repair protocol" in text
        assert "## W_" in text
        assert "Recommended actions" in text
        assert "Repair notes" in text
        assert "3 |     state Idle;" in text
        assert "4 |     state Running;" in text
        assert "|     ^^^^^^^^^^^^^^" in text
        assert "5 |     [*] -> Idle;" in text
        _assert_markdown_excerpt_gutters_align(text)

    def test_source_excerpt_renderers_do_not_emit_trailing_whitespace(self):
        source = textwrap.dedent(
            """
            state Root {
                [*] -> Idle;

                state Idle;
            }
            """
        ).strip()
        ast = parse_with_grammar_entry(source, "state_machine_dsl")
        machine = parse_dsl_node_to_state_machine(ast)
        report = inspect_model(machine)

        human = render_inspect_human(report, source)
        markdown = render_inspect_llm_markdown(report, source)

        assert " 3 |" in human
        assert "  3 |" in markdown
        for text in (human, markdown):
            for line in text.splitlines():
                assert line == line.rstrip(" \t")

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
