"""Inspect contracts for role-preserving import bindings."""

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.model import load_state_machine_from_file

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize(
    "source,target",
    [
        ("param", "param"),
        ("input", "param"),
        ("input", "input"),
        ("input", "control"),
        ("input", "output"),
        ("control", "control"),
        ("control", "output"),
        ("output", "control"),
        ("output", "output"),
    ],
)
def test_inspect_reports_final_parent_role_and_supply(tmp_path, source, target):
    from ._schema_check import assert_all_diags_match_schema

    source_init = "" if source == "input" else " = 1"
    target_init = "" if target == "input" else " = 9"
    write = "value = value + 1;" if source in ("control", "output") else ""
    (tmp_path / "child.fcstm").write_text(
        f"{source} int value{source_init}; output int observed = 0; state Child {{ enter {{ {write} observed = value; }} }}",
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        f'{target} int shared{target_init}; state Host {{ import "./child.fcstm" as Child {{ var value -> shared; var observed -> observed; }} [*] -> Child; }}',
        encoding="utf-8",
    )
    model = load_state_machine_from_file(host)
    report = inspect_model(model)
    variable = next(item for item in report.variables if item.name == "shared")
    assert variable.role == target
    assert variable.external_supply == {"input": "cycle", "param": "construction"}.get(
        target, "none"
    )
    assert set(variable.diagnostic_policy.values()) == {target == "control"}
    assert variable.read_sites
    assert bool(variable.write_sites) == (source in ("control", "output"))
    assert all(not item.is_error() for item in report.diagnostics)
    assert_all_diags_match_schema(report.diagnostics)


@pytest.mark.parametrize(
    "source,target",
    [
        ("control", "param"),
        ("output", "input"),
        ("param", "input"),
        ("param", "output"),
    ],
)
def test_import_role_conflict_survives_inspection(tmp_path, source, target):
    source_init = "" if source == "input" else " = 1"
    target_init = "" if target == "input" else " = 1"
    (tmp_path / "child.fcstm").write_text(
        f"{source} int value{source_init}; state Child;", encoding="utf-8"
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        f'{target} int shared{target_init}; state Host {{ import "./child.fcstm" as Child {{ var value -> shared; }} }}',
        encoding="utf-8",
    )
    machine, diagnostics = load_state_machine_from_file(host, collect=True)
    assert machine is not None
    report = inspect_model(machine, model_diagnostics=diagnostics)
    conflicts = [
        d for d in report.diagnostics if d.code == "E_IMPORT_DUPLICATE_MAPPING"
    ]
    assert len(conflicts) == 1
    assert "role" in conflicts[0].message
    assert conflicts[0].refs["duplicated_name"] == "shared"
    assert conflicts[0].refs["alias"] == "Child"
    assert conflicts[0].refs["binding_reason"] == "role_mismatch"
    assert conflicts[0].refs["source_path"] == str(host)
    binding = conflicts[0].refs["binding"]
    assert binding["source"][0]["name"] == "value"
    assert binding["source"][0]["source_path"] == str(tmp_path / "child.fcstm")
    assert binding["target"][0]["name"] == "shared"
    assert binding["target"][0]["source_path"] == str(host)
    span = conflicts[0].span
    assert span is not None
    authored = host.read_text(encoding="utf-8")
    assert (
        authored[span.column - 1 : span.end_column - 1]
        == 'import "./child.fcstm" as Child { var value -> shared; }'
    )
    assert not machine.root_state.substates


@pytest.mark.parametrize("role", ["control", "output"])
def test_shared_writable_variable_keeps_each_imported_writer(tmp_path, role):
    (tmp_path / "child.fcstm").write_text(
        f"{role} int value = 0; state Child {{ enter {{ value = 1; }} }}",
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        f'{role} int shared = 0; state Host {{ import "./child.fcstm" as A {{ var value -> shared; }} import "./child.fcstm" as B {{ var value -> shared; }} [*] -> A; A -> B; }}',
        encoding="utf-8",
    )
    machine = load_state_machine_from_file(host)
    report = inspect_model(machine)
    variable = next(item for item in report.variables if item.name == "shared")
    assert set(variable.written_in_states) == {"Host.A", "Host.B"}
    assert len(machine.defines["shared"]._source_declarations) == 3
    assert all(not item.is_error() for item in report.diagnostics)
    for state in machine.root_state.substates.values():
        operation = state.on_enters[0].operations[0]
        assert operation._source_path == str(tmp_path / "child.fcstm")


def test_invalid_import_initializer_retains_its_authored_file(tmp_path):
    child = tmp_path / "child.fcstm"
    child.write_text("input int value = 1; state Child;", encoding="utf-8")
    host = tmp_path / "host.fcstm"
    host.write_text(
        'input int shared; state Host { import "./child.fcstm" as Child { var value -> shared; } }',
        encoding="utf-8",
    )
    machine, diagnostics = load_state_machine_from_file(host, collect=True)
    report = inspect_model(machine, model_diagnostics=diagnostics)
    diagnostic = next(
        item for item in report.diagnostics if item.code == "E_INPUT_INITIALIZER"
    )
    assert diagnostic.refs["source_path"] == str(child)
    assert diagnostic.refs["var_name"] == "value"
    assert diagnostic.span.column == 1
    assert diagnostic.span.end_column == len("input int value = 1;") + 1
