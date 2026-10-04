"""Parent roles determine assembled interfaces without relaxing source ownership."""

import pytest

from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.model import load_state_machine_from_file, parse_dsl_node_to_state_machine
from pyfcstm.utils.validate import ModelValidationError

pytestmark = pytest.mark.unittest
ROLES = ("param", "input", "control", "output")
TARGETS = {
    "param": {"param"},
    "input": set(ROLES),
    "control": {"control", "output"},
    "output": {"control", "output"},
}


def declaration(role, name, numeric="int", value="1"):
    return f"{role} {numeric} {name}" + (";" if role == "input" else f" = {value};")


@pytest.mark.parametrize("source", ROLES)
@pytest.mark.parametrize("target", ROLES)
@pytest.mark.parametrize(
    "source_type,target_type",
    [("int", "int"), ("float", "float"), ("int", "float"), ("float", "int")],
)
def test_binding_result_role_type_partition_and_round_trip(
    tmp_path, source, target, source_type, target_type
):
    child = tmp_path / "child.fcstm"
    child.write_text(
        declaration(source, "value", source_type) + " state Child;", encoding="utf-8"
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        declaration(target, "shared", target_type, "9")
        + ' state Host { import "./child.fcstm" as Child { var value -> shared; } [*] -> Child; }',
        encoding="utf-8",
    )
    if target not in TARGETS[source] or source_type != target_type:
        with pytest.raises(ModelValidationError):
            load_state_machine_from_file(host)
        return
    model = load_state_machine_from_file(host)
    assert list(model.defines) == ["shared"]
    define = model.defines["shared"]
    assert define.role.value == target
    assert define.type == target_type
    assert define.init is None if target == "input" else define.init.value == 9
    for role, partition in zip(
        ROLES,
        [
            model.parameters,
            model.inputs,
            model.control_variables,
            model.output_variables,
        ],
    ):
        assert list(partition) == (["shared"] if role == target else [])
        if role == target:
            assert partition["shared"] is define
    sources = define._source_declarations
    assert [item["declaration"].role.value for item in sources] == [target, source]
    assert sources[1]["declaration"].name == "value"
    assert sources[1]["bindings"][0]["target_name"] == "shared"
    rebuilt = parse_dsl_node_to_state_machine(
        parse_state_machine_dsl(str(model.to_ast_node()))
    )
    assert rebuilt.defines["shared"].role == define.role
    assert rebuilt.defines["shared"].type == define.type


@pytest.mark.parametrize(
    "role,target",
    [("input", "control"), ("input", "output"), ("input", "param"), ("param", "param")],
)
@pytest.mark.parametrize(
    "body",
    [
        "enter { value = 2; }",
        "during before { value = 2; }",
        "during after { value = 2; }",
        ">> during before { value = 2; } state A; [*] -> A;",
        ">> during after { value = 2; } state A; [*] -> A;",
        "enter Set { value = 2; } exit ref Set;",
        "state A; [*] -> A effect { value = 2; };",
        "state A; [*] -> A; A -> [*] effect { value = 2; };",
        "during { if [1 == 0] { value = 2; } else { if [1 == 1] { value = 3; } } }",
        "exit { value = 2; }",
        "state A { enter { value = 2; } } [*] -> A;",
        "state A; state B; [*] -> A; A -> B effect { value = 2; }",
    ],
)
@pytest.mark.parametrize("collect", [False, True])
def test_binding_cannot_hide_source_readonly_writes(
    tmp_path, role, target, body, collect
):
    child = tmp_path / "child.fcstm"
    child.write_text(
        declaration(role, "value") + " state Child { " + body + " }", encoding="utf-8"
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        declaration(target, "shared")
        + ' state Host { import "./child.fcstm" as Child { var value -> shared; } }',
        encoding="utf-8",
    )
    if collect:
        model, diagnostics = load_state_machine_from_file(host, collect=True)
        assert not model.root_state.substates
        assert len(model.defines["shared"]._source_declarations) == 1
    else:
        with pytest.raises(ModelValidationError) as caught:
            load_state_machine_from_file(host)
        diagnostics = caught.value.diagnostics
    errors = [
        item
        for item in diagnostics
        if item.code == ("E_INPUT_WRITE" if role == "input" else "E_PARAM_WRITE")
    ]
    assert errors
    for error in errors:
        assert error.refs["var_name"] == "value"
        assert error.refs["source_path"] == str(child)
        assert error.span is not None


@pytest.mark.parametrize("first", ROLES)
@pytest.mark.parametrize("second", ROLES)
def test_implicit_target_cannot_be_retyped_by_import_order(tmp_path, first, second):
    (tmp_path / "a.fcstm").write_text(
        declaration(first, "value") + " state A;", encoding="utf-8"
    )
    (tmp_path / "b.fcstm").write_text(
        declaration(second, "value") + " state B;", encoding="utf-8"
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        'state Host { import "./a.fcstm" as A { var value -> shared; } import "./b.fcstm" as B { var value -> shared; } [*] -> A; }',
        encoding="utf-8",
    )
    if first != second or first == "input":
        with pytest.raises(ModelValidationError):
            load_state_machine_from_file(host)
    else:
        assert load_state_machine_from_file(host).defines["shared"].role.value == first


@pytest.mark.parametrize("outer", ROLES)
def test_nested_binding_checks_intermediate_contract(tmp_path, outer):
    (tmp_path / "leaf.fcstm").write_text(
        "input int sample; state Leaf;", encoding="utf-8"
    )
    (tmp_path / "child.fcstm").write_text(
        'param int configured = 3; state Child { import "./leaf.fcstm" as Leaf { var sample -> configured; } [*] -> Leaf; }',
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        declaration(outer, "shared", value="9")
        + ' state Host { import "./child.fcstm" as Child { var configured -> shared; } [*] -> Child; }',
        encoding="utf-8",
    )
    if outer != "param":
        with pytest.raises(ModelValidationError):
            load_state_machine_from_file(host)
    else:
        model = load_state_machine_from_file(host)
        assert model.parameters["shared"].init.value == 9
        sources = model.defines["shared"]._source_declarations
        assert [item["declaration"].role.value for item in sources] == [
            "param",
            "param",
            "input",
        ]
        assert [len(item["bindings"]) for item in sources] == [0, 1, 2]


@pytest.mark.parametrize(
    "target,first,second",
    [
        (target, first, second)
        for target in ROLES
        for first in ROLES
        for second in ROLES
        if target in TARGETS[first] and target in TARGETS[second]
    ],
)
def test_explicit_parent_owns_mixed_imports_in_both_orders(
    tmp_path, target, first, second
):
    for alias, role in [("A", first), ("B", second)]:
        (tmp_path / f"{alias}.fcstm").write_text(
            declaration(role, "value", value="3") + f" state {alias};", encoding="utf-8"
        )
    host = tmp_path / "host.fcstm"
    for order in [("A", "B"), ("B", "A")]:
        mappings = " ".join(
            f'import "./{alias}.fcstm" as {alias} {{ var value -> shared; }}'
            for alias in order
        )
        host.write_text(
            declaration(target, "shared", value="9")
            + f" state Host {{ {mappings} [*] -> A; }}",
            encoding="utf-8",
        )
        model = load_state_machine_from_file(host)
        assert list(model.defines) == ["shared"]
        define = model.defines["shared"]
        assert define.role.value == target
        assert define.init is None if target == "input" else define.init.value == 9
        sources = define._source_declarations
        assert {item["declaration"].role.value for item in sources} == {
            target,
            first,
            second,
        }
        assert [item["bindings"][0]["alias"] for item in sources[1:]] == list(order)


@pytest.mark.parametrize("role", ["input", "param"])
@pytest.mark.parametrize("collect", [False, True])
def test_outer_binding_cannot_hide_writes_to_implicit_nested_readonly(
    tmp_path, role, collect
):
    (tmp_path / "leaf.fcstm").write_text(
        declaration(role, "value") + " state Leaf;", encoding="utf-8"
    )
    child = tmp_path / "child.fcstm"
    child.write_text(
        'state Child { import "./leaf.fcstm" as Leaf { var value -> shared; } enter { shared = 2; } [*] -> Leaf; }',
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        declaration("control" if role == "input" else "param", "target")
        + ' state Host { import "./child.fcstm" as Child { var shared -> target; } [*] -> Child; }',
        encoding="utf-8",
    )
    if collect:
        _, diagnostics = load_state_machine_from_file(host, collect=True)
    else:
        with pytest.raises(ModelValidationError) as caught:
            load_state_machine_from_file(host)
        diagnostics = caught.value.diagnostics
    diagnostic = next(
        item
        for item in diagnostics
        if item.code == ("E_INPUT_WRITE" if role == "input" else "E_PARAM_WRITE")
    )
    assert diagnostic.refs["source_path"] == str(child)
    assert diagnostic.refs["var_name"] == "shared"
