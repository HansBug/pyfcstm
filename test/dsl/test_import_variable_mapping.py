"""Canonical and legacy import variable mapping syntax."""

import pytest

from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.dsl import node

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize("spelling", ["var", "def"])
@pytest.mark.parametrize(
    "selector,target",
    [
        ("value", "shared"),
        ("{a, b}", "Host_$0"),
        ("sensor_*", "Host_$1"),
        ("*", "Host_$0"),
    ],
)
def test_import_variable_mapping_round_trip(spelling, selector, target):
    source = 'state Root { import "./worker.fcstm" as Worker { %s %s -> %s; } }' % (
        spelling,
        selector,
        target,
    )
    tree = parse_state_machine_dsl(source)
    mapping = tree.root_state.imports[0].mappings[0]
    assert isinstance(mapping, node.ImportVariableMapping)
    assert mapping.spelling == spelling
    assert str(mapping).startswith(spelling + " ")
    assert parse_state_machine_dsl(str(tree)) == tree


def test_programmatic_mapping_defaults_to_var_and_legacy_alias_is_retained():
    selector = node.ImportDefExactSelector("value")
    target = node.ImportDefTargetTemplate("shared")
    assert str(node.ImportVariableMapping(selector, target)) == "var value -> shared;"
    assert str(node.ImportDefMapping(selector, target)) == "def value -> shared;"


def test_invalid_programmatic_mapping_spelling_is_rejected():
    with pytest.raises(ValueError, match="spelling"):
        node.ImportVariableMapping(
            node.ImportDefExactSelector("value"),
            node.ImportDefTargetTemplate("shared"),
            spelling="anything",
        )


def test_var_is_reserved_outside_import_blocks():
    from pyfcstm.dsl.error import GrammarParseError

    with pytest.raises(GrammarParseError):
        parse_state_machine_dsl("def int var = 0; state Root;")


@pytest.mark.parametrize("source_role", ["param", "input", "control", "output"])
@pytest.mark.parametrize("target_role", ["param", "input", "control", "output"])
def test_mapping_syntax_preserves_authored_roles_without_converting_them(
    source_role, target_role
):
    source_init = "" if source_role == "input" else " = 1"
    target_init = "" if target_role == "input" else " = 2"
    child = parse_state_machine_dsl(
        f"{source_role} int value{source_init}; state Child;"
    )
    host = parse_state_machine_dsl(
        f'{target_role} int shared{target_init}; state Host {{ import "./child.fcstm" as Child {{ var value -> shared; }} }}'
    )
    assert child.definitions[0].role.value == source_role
    assert host.definitions[0].role.value == target_role
    assert str(host.root_state.imports[0].mappings[0]) == "var value -> shared;"
    assert parse_state_machine_dsl(str(child)) == child
    assert parse_state_machine_dsl(str(host)) == host
