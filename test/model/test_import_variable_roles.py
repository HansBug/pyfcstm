"""Role and numeric type invariants across module assembly."""

import pytest

from pyfcstm.model import load_state_machine_from_file

pytestmark = pytest.mark.unittest
ROLES = ("control", "input", "param", "output")


def declaration(role, name, numeric="int", value="1"):
    return "%s %s %s%s;" % (
        role,
        numeric,
        name,
        "" if role == "input" else " = " + value,
    )


def build(tmp_path, source_role, target_role, source_type="int", target_type="int"):
    (tmp_path / "child.fcstm").write_text(
        declaration(source_role, "value", source_type) + " state Child;",
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        declaration(target_role, "shared", target_type)
        + ' state Host { import "./child.fcstm" as Child { def value -> shared; } [*] -> Child; }',
        encoding="utf-8",
    )
    return load_state_machine_from_file(str(host))


@pytest.mark.parametrize("source", ROLES)
@pytest.mark.parametrize("target", ROLES)
def test_import_requires_identical_roles(tmp_path, source, target):
    if source != target:
        with pytest.raises(SyntaxError, match="role"):
            build(tmp_path, source, target)
    else:
        assert list(build(tmp_path, source, target).defines) == ["shared"]


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "source_type,target_type", [("int", "float"), ("float", "int")]
)
def test_import_requires_identical_numeric_types(
    tmp_path, role, source_type, target_type
):
    with pytest.raises(SyntaxError, match="type"):
        build(tmp_path, role, role, source_type, target_type)


def test_implicit_shared_input_is_rejected(tmp_path):
    (tmp_path / "child.fcstm").write_text(
        "input int value; state Child;", encoding="utf-8"
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        'state Host { import "./child.fcstm" as A { def value -> shared; } import "./child.fcstm" as B { def value -> shared; } [*] -> A; }',
        encoding="utf-8",
    )
    with pytest.raises(SyntaxError, match="explicit"):
        load_state_machine_from_file(str(host))


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("numeric", ["int", "float"])
def test_absent_target_preserves_declaration(tmp_path, role, numeric):
    (tmp_path / "child.fcstm").write_text(
        declaration(role, "value", numeric) + " state Child;", encoding="utf-8"
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        'state Host { import "./child.fcstm" as Child { var value -> renamed; } [*] -> Child; }',
        encoding="utf-8",
    )
    machine = load_state_machine_from_file(str(host))
    variable = machine.defines["renamed"]
    expected = {"input": "input_dynamic", "param": "input_static"}.get(role, role)
    assert variable.role.value == expected
    assert variable.type == numeric


@pytest.mark.parametrize("source", ROLES)
@pytest.mark.parametrize("target", ROLES)
def test_recursive_mapping_cannot_change_role(tmp_path, source, target):
    (tmp_path / "leaf.fcstm").write_text(
        declaration(source, "value") + " state Leaf;", encoding="utf-8"
    )
    (tmp_path / "child.fcstm").write_text(
        'state Child { import "./leaf.fcstm" as Leaf { var value -> inner; } [*] -> Leaf; }',
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        declaration(target, "shared")
        + ' state Host { import "./child.fcstm" as Child { var inner -> shared; } [*] -> Child; }',
        encoding="utf-8",
    )
    if source != target:
        with pytest.raises(SyntaxError, match="role"):
            load_state_machine_from_file(str(host))
    else:
        assert list(load_state_machine_from_file(str(host)).defines) == ["shared"]


def test_collect_conflicting_import_does_not_commit_any_declarations(tmp_path):
    from pyfcstm.dsl import parse_state_machine_dsl
    from pyfcstm.diagnostics.sink import DiagnosticSink
    from pyfcstm.model.imports import assemble_state_machine_imports

    (tmp_path / "child.fcstm").write_text(
        "output int fresh = 1; input int value; state Child;", encoding="utf-8"
    )
    source = 'param int shared = 1; state Host { import "./child.fcstm" as Child { var value -> shared; var fresh -> fresh; } }'
    sink = DiagnosticSink(collect=True)
    tree = assemble_state_machine_imports(
        parse_state_machine_dsl(source), path=str(tmp_path), collect_into=sink
    )
    assert [item.name for item in tree.definitions] == ["shared"]
    assert not tree.root_state.substates
    assert len(sink.diagnostics) == 1
    assert "role" in sink.diagnostics[0].message


@pytest.mark.parametrize("invalid_mapping", [False, True])
def test_collect_rejects_invalid_nested_import_and_keeps_valid_sibling(
    tmp_path, invalid_mapping
):
    from pyfcstm.dsl import parse_state_machine_dsl
    from pyfcstm.diagnostics.sink import DiagnosticSink
    from pyfcstm.model.imports import assemble_state_machine_imports

    (tmp_path / "leaf.fcstm").write_text(
        "input int value; state Leaf;", encoding="utf-8"
    )
    nested = 'param int shared = 1; state Child { import "./leaf.fcstm" as Leaf { var value -> shared; } }'
    if invalid_mapping:
        nested = (
            'state Child { import "./leaf.fcstm" as Leaf { var missing -> shared; } }'
        )
    (tmp_path / "child.fcstm").write_text(nested, encoding="utf-8")
    (tmp_path / "valid.fcstm").write_text(
        "output int result = 1; state Valid;", encoding="utf-8"
    )
    source = 'state Host { import "./child.fcstm" as Child; import "./valid.fcstm" as Valid; }'
    sink = DiagnosticSink(collect=True)
    tree = assemble_state_machine_imports(
        parse_state_machine_dsl(source), path=str(tmp_path), collect_into=sink
    )
    assert [item.name for item in tree.definitions] == ["Valid_result"]
    assert [item.name for item in tree.root_state.substates] == ["Valid"]
    assert sink.has_errors()


def test_shared_input_retains_each_recursive_declaration_source(tmp_path):
    (tmp_path / "leaf.fcstm").write_text(
        "input int value; state Leaf;", encoding="utf-8"
    )
    (tmp_path / "child.fcstm").write_text(
        'input int inner; state Child { import "./leaf.fcstm" as Leaf { var value -> inner; } [*] -> Leaf; }',
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        'input int shared; state Host { import "./child.fcstm" as A { var inner -> shared; } import "./child.fcstm" as B { var inner -> shared; } [*] -> A; }',
        encoding="utf-8",
    )
    machine = load_state_machine_from_file(host)
    sources = machine.defines["shared"]._source_declarations
    assert [item["declaration"].name for item in sources] == [
        "shared",
        "inner",
        "value",
        "inner",
        "value",
    ]
    assert [len(item["bindings"]) for item in sources] == [0, 1, 2, 1, 2]
    assert sources[2]["declaration"]._source_path == str(tmp_path / "leaf.fcstm")
    assert [item["alias"] for item in sources[2]["bindings"]] == ["Leaf", "A"]
    assert [item["alias"] for item in sources[4]["bindings"]] == ["Leaf", "B"]
    assert all(item["declaration"].role.value == "input_dynamic" for item in sources)
    assert sources[2]["bindings"][-1]["target_name"] == "shared"


def test_reassembling_expanded_ast_preserves_declaration_provenance(tmp_path):
    from pyfcstm.dsl import parse_state_machine_dsl
    from pyfcstm.model import parse_dsl_node_to_state_machine
    from pyfcstm.model.imports import assemble_state_machine_imports

    (tmp_path / "child.fcstm").write_text(
        "param int limit = 2; state Child;", encoding="utf-8"
    )
    source = 'state Host { import "./child.fcstm" as Child { var limit -> configured; } [*] -> Child; }'
    expanded = assemble_state_machine_imports(
        parse_state_machine_dsl(source), path=str(tmp_path)
    )
    machine = parse_dsl_node_to_state_machine(expanded, path=str(tmp_path))
    sources = machine.defines["configured"]._source_declarations
    assert len(sources) == 1
    assert sources[0]["declaration"].name == "limit"
    assert sources[0]["declaration"]._source_path == str(tmp_path / "child.fcstm")
    assert len(sources[0]["bindings"]) == 1
    assert expanded.definitions[0]._source_declarations == sources


@pytest.mark.parametrize(
    "source,host,code",
    [
        ("input int value = 1;", "input int shared;", "E_DYNAMIC_INPUT_INITIALIZER"),
        (
            "param int value;",
            "param int shared = 1;",
            "E_VARIABLE_INITIALIZER_REQUIRED",
        ),
    ],
)
@pytest.mark.parametrize("collect", [False, True])
def test_host_default_cannot_hide_invalid_imported_initializer(
    tmp_path, source, host, code, collect
):
    from pyfcstm.utils.validate import ModelValidationError

    (tmp_path / "child.fcstm").write_text(source + " state Child;", encoding="utf-8")
    host_file = tmp_path / "host.fcstm"
    host_file.write_text(
        host
        + ' state Host { import "./child.fcstm" as Child { var value -> shared; } [*] -> Child; }',
        encoding="utf-8",
    )
    if collect:
        machine, diagnostics = load_state_machine_from_file(host_file, collect=True)
        assert code in {item.code for item in diagnostics}
        assert not machine.root_state.substates
    else:
        with pytest.raises(ModelValidationError) as caught:
            load_state_machine_from_file(host_file)
        assert code in {item.code for item in caught.value.diagnostics}


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "selector,target,expected",
    [
        ("value", "chosen", "chosen"),
        ("{value}", "Host_$0", "Host_value"),
        ("v*", "Host_$1", "Host_alue"),
        ("*", "Host_$0", "Host_value"),
    ],
)
def test_canonical_mapping_selectors_preserve_roles(
    tmp_path, role, selector, target, expected
):
    (tmp_path / "child.fcstm").write_text(
        declaration(role, "value") + " state Child;", encoding="utf-8"
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        'state Host { import "./child.fcstm" as Child { var %s -> %s; } [*] -> Child; }'
        % (selector, target),
        encoding="utf-8",
    )
    machine = load_state_machine_from_file(host)
    assert list(machine.defines) == [expected]
    expected_role = {"input": "input_dynamic", "param": "input_static"}.get(role, role)
    assert machine.defines[expected].role.value == expected_role


@pytest.mark.parametrize("role", ["control", "param", "output"])
@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("same_default", [False, True])
def test_shared_defaults_follow_explicit_host_ownership(
    tmp_path, role, explicit, same_default
):
    (tmp_path / "a.fcstm").write_text(
        declaration(role, "a", value="1") + " state A;", encoding="utf-8"
    )
    (tmp_path / "b.fcstm").write_text(
        declaration(role, "b", value="1" if same_default else "2") + " state B;",
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    prefix = declaration(role, "shared", value="9") if explicit else ""
    host.write_text(
        prefix
        + ' state Host { import "./a.fcstm" as A { var a -> shared; } import "./b.fcstm" as B { var b -> shared; } [*] -> A; }',
        encoding="utf-8",
    )
    if not explicit and not same_default:
        with pytest.raises(SyntaxError, match="initial values"):
            load_state_machine_from_file(host)
    else:
        machine = load_state_machine_from_file(host)
        assert machine.defines["shared"].init.value == (9 if explicit else 1)


@pytest.mark.parametrize("first", ROLES)
@pytest.mark.parametrize("second", ROLES)
def test_duplicate_source_declarations_cannot_bypass_binding_checks(
    tmp_path, first, second
):
    from pyfcstm.utils.validate import ModelValidationError

    (tmp_path / "child.fcstm").write_text(
        declaration(first, "value") + declaration(second, "value") + " state Child;",
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        'state Host { import "./child.fcstm" as Child { var value -> shared; } [*] -> Child; }',
        encoding="utf-8",
    )
    with pytest.raises(ModelValidationError) as caught:
        load_state_machine_from_file(host)
    assert "E_DUPLICATE_VAR" in {item.code for item in caught.value.diagnostics}


@pytest.mark.parametrize(
    "source_name,selector,target",
    [
        ("value", "value", "var"),
        ("value", "value", "param"),
        ("prefix_input", "prefix_*", "$1"),
        ("prefix_1", "prefix_*", "$1"),
        ("value", "value*", "$1"),
    ],
)
def test_rendered_mapping_target_must_be_a_dsl_identifier(
    tmp_path, source_name, selector, target
):
    (tmp_path / "child.fcstm").write_text(
        declaration("control", source_name) + " state Child;", encoding="utf-8"
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        'state Host { import "./child.fcstm" as Child { var %s -> %s; } [*] -> Child; }'
        % (selector, target),
        encoding="utf-8",
    )
    with pytest.raises(SyntaxError, match="identifier"):
        load_state_machine_from_file(host)
    from pyfcstm.diagnostics.sink import DiagnosticSink
    from pyfcstm.dsl import parse_state_machine_dsl
    from pyfcstm.model.imports import assemble_state_machine_imports

    sink = DiagnosticSink(collect=True)
    tree = assemble_state_machine_imports(
        parse_state_machine_dsl(host.read_text(encoding="utf-8")),
        path=str(tmp_path),
        collect_into=sink,
    )
    assert tree.definitions == []
    assert tree.root_state.substates == []
    assert len(sink.diagnostics) == 1
    assert sink.diagnostics[0].code == "E_IMPORT_MAPPING_INVALID"
    assert sink.diagnostics[0].refs["reason"] == "target_invalid"
