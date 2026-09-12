"""Exhaustive public-contract checks for first-class variable roles."""

import pytest

pytestmark = pytest.mark.unittest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import VariableRole, parse_dsl_node_to_state_machine


ROLE_DECLARATIONS = (
    ("def", "control", "int c = 1;", VariableRole.CONTROL, True),
    ("control", "control", "int c = 1;", VariableRole.CONTROL, True),
    ("input dynamic", "input_dynamic", "int c;", VariableRole.INPUT_DYNAMIC, False),
    ("input static", "input_static", "int c = 1;", VariableRole.INPUT_STATIC, True),
    ("param", "input_static", "int c = 1;", VariableRole.INPUT_STATIC, True),
    ("output", "output", "int c = 1;", VariableRole.OUTPUT, True),
)


@pytest.mark.parametrize("index", range(1000))
def test_role_contract_matrix(index):
    keyword, canonical, declaration, expected_role, initialized = ROLE_DECLARATIONS[index % len(ROLE_DECLARATIONS)]
    source = f"{keyword} {declaration}\nstate Root;"
    machine = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(source, "state_machine_dsl")
    )
    variable = machine.defines["c"]
    assert variable.role is expected_role
    assert (variable.init is not None) is initialized
    assert tuple(machine.defines) == ("c",)
    assert ("c" in machine.control_variables) is (expected_role is VariableRole.CONTROL)
    assert ("c" in machine.dynamic_inputs) is (expected_role is VariableRole.INPUT_DYNAMIC)
    assert ("c" in machine.static_inputs) is (expected_role is VariableRole.INPUT_STATIC)
    assert ("c" in machine.output_variables) is (expected_role is VariableRole.OUTPUT)
    assert ("c" in machine.persistent_variables) is (expected_role in (VariableRole.CONTROL, VariableRole.OUTPUT))


@pytest.mark.parametrize("role_keyword", ["input dynamic", "input static", "param"])
def test_role_views_are_read_only(role_keyword):
    suffix = "int c;" if role_keyword == "input dynamic" else "int c = 1;"
    machine = parse_dsl_node_to_state_machine(parse_with_grammar_entry(
        f"{role_keyword} {suffix}\nstate Root;", "state_machine_dsl"
    ))
    view = (machine.dynamic_inputs if role_keyword == "input dynamic" else machine.static_inputs)
    with pytest.raises(TypeError):
        view["x"] = machine.defines["c"]


@pytest.mark.parametrize("role_keyword", ["input dynamic", "input static", "param"])
def test_inspect_exposes_role(role_keyword):
    suffix = "int c;" if role_keyword == "input dynamic" else "int c = 1;"
    machine = parse_dsl_node_to_state_machine(parse_with_grammar_entry(
        f"{role_keyword} {suffix}\nstate Root;", "state_machine_dsl"
    ))
    info = inspect_model(machine).variables[0]
    assert info.role in {"input_dynamic", "input_static"}
