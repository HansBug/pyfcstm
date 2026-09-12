"""Inspect contracts for variable roles and collecting model diagnostics."""

import json

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from ._schema_check import assert_all_diags_match_schema

pytestmark = pytest.mark.unittest


def inspect_source(source):
    model = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(source, "state_machine_dsl")
    )
    return inspect_model(model)


def test_roles_survive_inspect_json_without_dead_variable_false_positives():
    report = inspect_source(
        "input int sensor; param int limit = 2; output int command = 0; "
        "def int counter = 0; state Root { state A; state B; [*] -> A; "
        "A -> B : if [sensor > limit] effect { command = 1; } }"
    )
    payload = json.loads(json.dumps(report.to_json()))
    variables = {item["name"]: item for item in payload["variables"]}
    assert {name: item["role"] for name, item in variables.items()} == {
        "sensor": "input_dynamic",
        "limit": "input_static",
        "command": "output",
        "counter": "control",
    }
    assert variables["sensor"]["init_value"] == ""
    assert variables["limit"]["init_value"] == "2"
    codes = [(d.code, d.refs.get("var_name")) for d in report.diagnostics]
    assert ("W_UNREFERENCED_VAR", "counter") in codes
    assert not any(
        name in ("sensor", "limit", "command")
        and code
        in (
            "W_UNREFERENCED_VAR",
            "W_UNWRITTEN_READ_VAR",
            "W_WRITE_ONLY_VAR",
        )
        for code, name in codes
    )
    assert "W_GUARD_VARS_NEVER_CHANGE" not in [d.code for d in report.diagnostics]
    assert_all_diags_match_schema(report.diagnostics)
    assert "schema_version" not in payload


@pytest.mark.parametrize(
    "declaration,body,code",
    [
        ("input int value = 1;", "state Root;", "E_DYNAMIC_INPUT_INITIALIZER"),
        ("param int value;", "state Root;", "E_VARIABLE_INITIALIZER_REQUIRED"),
        (
            "input int value;",
            "state Root { during { value = 1; } }",
            "E_DYNAMIC_INPUT_WRITE",
        ),
        (
            "param int value = 1;",
            "state Root { during { value = 2; } }",
            "E_STATIC_INPUT_WRITE",
        ),
    ],
)
def test_collecting_build_reports_role_errors(declaration, body, code):
    _, diagnostics = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(declaration + body, "state_machine_dsl"),
        collect=True,
    )
    matching = [d for d in diagnostics if d.code == code]
    assert len(matching) == 1
    assert matching[0].span is not None
    assert matching[0].refs["var_name"] == "value"
    assert_all_diags_match_schema(diagnostics)


def test_role_schema_and_cli_collect_errors(tmp_path):
    import os
    import jsonschema
    from click.testing import CliRunner
    import pyfcstm.diagnostics
    from pyfcstm.entry.cli import cli

    source = tmp_path / "roles.fcstm"
    source.write_text(
        "input int sensor; param int limit = 2; output int command = 0; state Root;",
        encoding="utf-8",
    )
    result = CliRunner().invoke(cli, ["inspect", "-i", str(source), "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    schema_path = os.path.join(
        os.path.dirname(pyfcstm.diagnostics.__file__), "schema.json"
    )
    with open(schema_path, encoding="utf-8") as file:
        schema = json.load(file)
    jsonschema.Draft7Validator(schema).validate(payload)
    assert [v["role"] for v in payload["variables"]] == [
        "input_dynamic",
        "input_static",
        "output",
    ]
    for invalid_role in [None, "input", "param", "unknown"]:
        invalid = json.loads(json.dumps(payload))
        if invalid_role is None:
            del invalid["variables"][0]["role"]
        else:
            invalid["variables"][0]["role"] = invalid_role
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft7Validator(schema).validate(invalid)
    source.write_text(
        "input int sensor; state Root { during { sensor = 1; } }", encoding="utf-8"
    )
    result = CliRunner().invoke(
        cli, ["inspect", "-i", str(source), "--format", "json", "--collect-errors"]
    )
    payload = json.loads(result.output)
    assert any(d["code"] == "E_DYNAMIC_INPUT_WRITE" for d in payload["diagnostics"])


@pytest.mark.parametrize(
    "declaration,expected",
    [
        ("input int setting;", False),
        ("param int setting = 1;", False),
        ("output int setting = 1;", False),
        ("def int setting = 1;", True),
    ],
)
def test_guard_change_advice_is_scoped_to_control_state(declaration, expected):
    report = inspect_source(
        declaration
        + "state Root {state A;state B;[*] -> A; A -> B : if [setting > 0];}"
    )
    assert (
        "W_GUARD_VARS_NEVER_CHANGE" in [d.code for d in report.diagnostics]
    ) == expected
