"""Variable ownership, declaration round-trips, and model write boundaries."""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.dsl import node as ast
from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.model import (
    PlantUMLOptions,
    StateMachine,
    VarDefine,
    parse_dsl_node_to_state_machine,
)
from pyfcstm.model.expr import Integer, Variable
from pyfcstm.utils import ModelValidationError


pytestmark = pytest.mark.unittest

DECLARATIONS = [
    ("def", "control", " = 2"),
    ("control", "control", " = 2"),
    ("input", "input_dynamic", ""),
    ("input dynamic", "input_dynamic", ""),
    ("param", "input_static", " = 2"),
    ("input static", "input_static", " = 2"),
    ("output", "output", " = 2"),
]


def build(source, **kwargs):
    return parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(source, "state_machine_dsl"), **kwargs
    )


@pytest.mark.parametrize("keyword,role,initializer", DECLARATIONS)
@pytest.mark.parametrize("type_name", ["int", "float"])
def test_declaration_round_trip(keyword, role, initializer, type_name):
    from pyfcstm.model import VariableRole

    source = "/* sensor interface */\n%s %s value%s;\nstate Root;" % (
        keyword,
        type_name,
        initializer,
    )
    tree = parse_with_grammar_entry(source, "state_machine_dsl")
    model = parse_dsl_node_to_state_machine(tree)
    definition = model.defines["value"]
    assert definition.role is VariableRole(role)
    assert tree.definitions[0].role == role
    assert str(model.to_ast_node()) == str(tree)
    assert build(str(model.to_ast_node())).defines["value"] == definition
    assert (definition.init is None) == (role == "input_dynamic")
    assert definition.doc == "sensor interface"


def test_role_partitions_keep_global_order_and_definition_identity():
    model = build(
        "output int first = 0; input int sensor; def int count = 1; "
        "param int limit = 2; output float last = 0.0; state Root;"
    )
    expected = {
        "control_variables": ["count"],
        "dynamic_inputs": ["sensor"],
        "static_inputs": ["limit"],
        "output_variables": ["first", "last"],
        "persistent_variables": ["first", "count", "last"],
    }
    for property_name, names in expected.items():
        partition = getattr(model, property_name)
        assert list(partition) == names
        for name in names:
            assert partition[name] is model.defines[name]
        with pytest.raises(TypeError):
            partition["extra"] = model.defines["count"]
        with pytest.raises(TypeError):
            del partition[names[0]]
    assert list(build("state Root;").persistent_variables) == []


@pytest.mark.parametrize(
    "keyword", ["def", "control", "param", "input static", "output"]
)
def test_required_initializer_is_model_error(keyword):
    with pytest.raises(ModelValidationError) as error:
        build("%s int value; state Root;" % keyword)
    assert error.value.diagnostics[0].code == "E_VARIABLE_INITIALIZER_REQUIRED"


@pytest.mark.parametrize("keyword", ["input", "input dynamic"])
def test_dynamic_initializer_is_model_error(keyword):
    with pytest.raises(ModelValidationError) as error:
        build("%s int value = 1; state Root;" % keyword)
    assert error.value.diagnostics[0].code == "E_DYNAMIC_INPUT_INITIALIZER"


@pytest.mark.parametrize("keyword", ["input", "input dynamic", "param", "input static"])
@pytest.mark.parametrize(
    "body",
    [
        "state Root { enter { value = 1; } }",
        "state Root { during { value = 1; } }",
        "state Root { exit { value = 1; } }",
        "state Root { state A; [*] -> A effect { value = 1; }; }",
        "state Root { state A; state B; [*] -> A; A -> B effect { value = 1; }; }",
        "state Root { state A; [*] -> A; A -> [*] effect { value = 1; }; }",
        "state Root { >> during before { value = 1; } state A; [*] -> A; }",
        "state Root { during { if [1 == 1] { if [1 == 1] { value = 1; } } } }",
        "state Root { enter Set { value = 1; } exit ref Set; }",
        "state Root { during { if [True] {} else { value = 1; } } }",
        "state Root { during { if [True] {} else if [False] { value = 1; } } }",
        "state Root { >> during after { value = 1; } state A; [*] -> A; }",
        "state Root { state A { enter { value = 1; } } [*] -> A; }",
    ],
)
def test_input_writes_rejected_during_model_construction(keyword, body):
    initializer = " = 0" if keyword in ("param", "input static") else ""
    source = "%s int value%s; %s" % (keyword, initializer, body)
    with pytest.raises(ModelValidationError) as error:
        build(source)
    diagnostic = error.value.diagnostics[0]
    expected = "E_STATIC_INPUT_WRITE" if initializer else "E_DYNAMIC_INPUT_WRITE"
    assert diagnostic.code == expected
    assert diagnostic.refs["var_name"] == "value"
    assert diagnostic.span is not None
    _, diagnostics = build(source, collect=True)
    assert expected in [item.code for item in diagnostics]


@pytest.mark.parametrize("role", ["control", "input_static", "output"])
def test_programmatic_initializers_cannot_reference_variables(role):
    with pytest.raises(ModelValidationError) as error:
        VarDefine("derived", "int", Variable("other") + Integer(1), role=role)
    assert error.value.diagnostics[0].code == "E_INITIALIZER_VARIABLE_REFERENCE"


def test_programmatic_roles_and_legacy_positional_documentation():
    from pyfcstm.model import VariableRole

    legacy = VarDefine("x", "int", Integer(1), "legacy documentation")
    assert legacy.role is VariableRole.CONTROL
    assert legacy.doc == "legacy documentation"
    assert str(legacy.to_ast_node()).endswith("def int x = 1;")
    for role, keyword, initializer in [
        ("input_dynamic", "input", None),
        ("input_static", "param", Integer(1)),
        ("output", "output", Integer(1)),
    ]:
        definition = VarDefine("x", "int", initializer, role=role)
        assert str(definition.to_ast_node()).startswith(keyword + " int x")
        assert (
            build(str(definition.to_ast_node()) + " state Root;").defines["x"].role
            == role
        )


def test_programmatic_machine_rejects_input_write():
    state = build("def int value = 0; state Root { during { value = 1; } }").root_state
    with pytest.raises(ModelValidationError) as error:
        StateMachine(
            {"value": VarDefine("value", "int", None, role="input_dynamic")}, state
        )
    assert error.value.diagnostics[0].code == "E_DYNAMIC_INPUT_WRITE"


@pytest.mark.parametrize(
    "prefix", ["sensor", "input random", "control dynamic", "param static"]
)
def test_unknown_declaration_prefix_is_syntax_error(prefix):
    with pytest.raises(GrammarParseError):
        parse_with_grammar_entry(
            "%s int x = 0; state Root;" % prefix, "state_machine_dsl"
        )


def test_cross_role_duplicate_names_are_rejected():
    with pytest.raises(ModelValidationError) as error:
        build("input int x; output int x = 0; state Root;")
    assert error.value.diagnostics[0].code == "E_DUPLICATE_VAR"


def test_ast_initializer_variable_reference_is_rejected():
    program = ast.StateMachineDSLProgram(
        [ast.DefAssignment("value", "int", ast.Name("other"))],
        ast.StateDefinition("Root"),
    )
    with pytest.raises(ModelValidationError) as error:
        parse_dsl_node_to_state_machine(program)
    assert error.value.diagnostics[0].code == "E_INITIALIZER_VARIABLE_REFERENCE"


@pytest.mark.parametrize("mapping", ["", " { def * -> shared_$0; }"])
def test_import_preserves_role_and_missing_dynamic_initializer(tmp_path, mapping):
    from pyfcstm.model import load_state_machine_from_file

    module = tmp_path / "sensor.fcstm"
    module.write_text(
        "input int reading; param int limit = 2; output int command = 0; "
        "control int count = 0; state Sensor;",
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        'state Host { import "./sensor.fcstm" as Sensor%s %s [*] -> Sensor; }'
        % (
            mapping,
            "" if mapping else ";",
        ),
        encoding="utf-8",
    )
    model = load_state_machine_from_file(str(host))
    prefix = "shared_" if mapping else "Sensor_"
    assert [
        (name, definition.role.value) for name, definition in model.defines.items()
    ] == [
        (prefix + "reading", "input_dynamic"),
        (prefix + "limit", "input_static"),
        (prefix + "command", "output"),
        (prefix + "count", "control"),
    ]
    assert model.defines[prefix + "reading"].init is None
    assert (
        build(str(model.to_ast_node())).defines[prefix + "reading"].role
        == "input_dynamic"
    )


def test_output_writes_in_multiple_actions_are_valid_and_plantuml_preserves_roles():
    model = build(
        "input int sensor; param int limit = 2; output int command = 0; "
        "state Root { enter { command = sensor; } during { command = limit; } }"
    )
    plantuml = model.to_plantuml(PlantUMLOptions(variable_display_mode="note"))
    assert "input int sensor;" in plantuml
    assert "param int limit = 2;" in plantuml
    assert "output int command = 0;" in plantuml
    assert " = None" not in plantuml


def test_invalid_programmatic_role_is_rejected():
    with pytest.raises(ValueError):
        VarDefine("value", "int", Integer(1), role="sensor")


def test_plantuml_legend_exposes_roles_for_external_interfaces():
    model = build(
        "input int sensor; param int limit = 2; output int command = 0; "
        "def int count = 0; state Root;"
    )
    legend = model.to_plantuml()
    assert "|= Variable |= Type |= Initial Value |= Role |" in legend
    assert "| sensor | int | N/A | input_dynamic |" in legend
    assert "| limit | int | 2 | input_static |" in legend
    assert "| command | int | 0 | output |" in legend
    assert "| count | int | 0 | control |" in legend
