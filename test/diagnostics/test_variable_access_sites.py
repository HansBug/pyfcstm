"""Public variable access sites retain role, ownership and instance identity."""

import os

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.model import load_state_machine_from_text, load_state_machine_from_file

pytestmark = pytest.mark.unittest

SOURCE = '''input int sensor;
param int limit = 2;
output int result = 0;
control int counter = 0;
state Root {
    enter { counter = sensor; }
    state A {
        during { if [sensor > limit] { result = counter; } else { result = 0; } }
    }
    state B;
    [*] -> A;
    A -> B : if [sensor > limit] effect { counter = counter + 1; }
}
'''


def test_role_supply_and_policy_are_public_report_contracts():
    model = load_state_machine_from_text(SOURCE, 'machine.fcstm')
    report = inspect_model(model)
    variables = {v.name: v for v in report.variables}
    assert {name: v.external_supply for name, v in variables.items()} == {
        'sensor': 'cycle', 'limit': 'construction', 'result': 'none', 'counter': 'none',
    }
    for name, variable in variables.items():
        assert variable.diagnostic_policy == {
            'unused': name == 'counter', 'unwritten': name == 'counter',
            'write_only': name == 'counter', 'constant_guard': name == 'counter',
        }
    payload = report.to_json()
    assert payload['variables'][0]['external_supply'] == 'cycle'
    assert payload['variables'][0]['write_sites'] == []


def test_sites_locate_actions_guards_effects_and_nested_statements():
    model = load_state_machine_from_text(SOURCE, 'machine.fcstm')
    report = inspect_model(model)
    variables = {v.name: v for v in report.variables}
    sensor = variables['sensor']
    assert [(s.kind, s.state_path, s.statement_path) for s in sensor.read_sites] == [
        ('action', 'Root', (0,)),
        ('guard', 'Root', ()),
        ('action', 'Root.A', (0, 0)),
    ]
    assert all(s.source_path == os.path.abspath(model.source_path) for s in sensor.read_sites)
    assert all(s.span is not None for s in sensor.read_sites)
    result = variables['result']
    assert [s.statement_path for s in result.write_sites] == [(0, 0, 0), (0, 1, 0)]
    assert all(s.action == report.actions[1].signature for s in result.write_sites)
    assert all(s.action_index == 1 for s in result.write_sites)
    counter = variables['counter']
    assert [(s.kind, s.statement_path) for s in counter.write_sites] == [
        ('action', (0,)), ('effect', (0,)),
    ]
    effect = counter.write_sites[1]
    assert report.transitions[effect.transition_index].from_path == 'Root.A'
    assert report.transitions[effect.transition_index].to_path == 'Root.B'
    assert counter.written_in_states == ('Root',)
    assert counter.written_in_effects == (('Root.A', 'Root.B'),)


def test_imported_shared_input_retains_distinct_instances_and_authored_file(tmp_path):
    leaf = tmp_path / 'leaf.fcstm'
    leaf.write_text('input int value; output int result = 0; state Leaf { enter { result = value; } }', encoding='utf-8')
    child = tmp_path / 'child.fcstm'
    child.write_text('state Child { import "./leaf.fcstm" as Leaf { var value -> inner; var result -> result; } [*] -> Leaf; }', encoding='utf-8')
    host = tmp_path / 'host.fcstm'
    host.write_text('input int shared; state Host { import "./child.fcstm" as A { var inner -> shared; var result -> a_result; } import "./child.fcstm" as B { var inner -> shared; var result -> b_result; } [*] -> A; A -> B; }', encoding='utf-8')
    report = inspect_model(load_state_machine_from_file(host))
    shared = next(v for v in report.variables if v.name == 'shared')
    assert [s.state_path for s in shared.read_sites] == ['Host.A.Leaf', 'Host.B.Leaf']
    assert [s.source_path for s in shared.read_sites] == [str(leaf), str(leaf)]
    assert shared.read_sites[0].span == shared.read_sites[1].span
    assert shared.write_sites == ()


def test_site_json_contains_source_span_and_validates_against_shipped_schema():
    import json
    import jsonschema
    import pyfcstm.diagnostics
    from pathlib import Path

    payload = inspect_model(load_state_machine_from_text(SOURCE, 'machine.fcstm')).to_json()
    site = payload['variables'][0]['read_sites'][0]
    assert site['span'] == {'line': 6, 'column': 13, 'end_line': 6, 'end_column': 30}
    schema = json.loads(Path(pyfcstm.diagnostics.__file__).with_name('schema.json').read_text())
    jsonschema.Draft7Validator(schema).validate(payload)
    assert 'schema_version' not in payload


@pytest.mark.parametrize('stage', ['enter', 'during', 'exit', 'during before', 'during after', '>> during before', '>> during after'])
def test_accesses_cover_lifecycle_stages_and_duplicate_inline_names(stage):
    # Before/after and aspect actions belong to composites.
    source = ('input int sensor; output int result = 0; state Root { '
              + stage + ' { result = sensor + sensor; } '
              + stage + ' { result = sensor; } ' + ('}' if stage == 'during' else 'state A; [*] -> A; }'))
    report = inspect_model(load_state_machine_from_text(source))
    sensor, result = report.variables
    assert len(sensor.read_sites) == len(result.write_sites) == 2
    assert [site.action_index for site in sensor.read_sites] == [0, 1]
    assert [site.statement_path for site in sensor.read_sites] == [(0,), (0,)]
    assert sensor.read_sites[0].action == sensor.read_sites[1].action
    assert all(report.actions[s.action_index].stage == stage.replace('>> ', '').split()[0]
               for s in sensor.read_sites)


def test_nested_branches_and_unreachable_writes_are_static_accesses():
    source = '''input int sensor; output int result = 0;
state Root { during {
    if [sensor > 0] {
        if [sensor < 2] { result = sensor; } else { result = 2; }
    } else if [sensor < 0] { result = 3; } else { result = 4; }
    if [0 > 1] { result = 5; }
} }'''
    report = inspect_model(load_state_machine_from_text(source))
    sensor, result = report.variables
    assert [s.statement_path for s in sensor.read_sites] == [
        (0, 0), (0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 1),
    ]
    assert [s.statement_path for s in result.write_sites] == [
        (0, 0, 0, 0, 0), (0, 0, 0, 1, 0), (0, 1, 0), (0, 2, 0), (1, 0, 0),
    ]


def test_action_references_keep_definition_sites_and_reference_graph(tmp_path):
    child = tmp_path / 'child.fcstm'
    child.write_text('input int sensor; output int result = 0; state Child { enter Setup { result = sensor; } }', encoding='utf-8')
    host = tmp_path / 'host.fcstm'
    host.write_text('state Root { import "./child.fcstm" as Child; state A { enter ref /Child.Setup; } [*] -> A; }', encoding='utf-8')
    report = inspect_model(load_state_machine_from_file(host))
    sensor = next(v for v in report.variables if v.role == 'input_dynamic')
    assert len(sensor.read_sites) == 1
    site = sensor.read_sites[0]
    assert site.state_path == 'Root.Child'
    assert site.source_path == str(child)
    assert report.actions[site.action_index].is_ref is False
    assert any(a.is_ref and a.state_path == 'Root.A' for a in report.actions)
    assert any(report.action_ref_graph.values())


def test_programmatic_model_does_not_fabricate_access_source():
    from pyfcstm.model import StateMachine, State, VarDefine, OnStage, Operation
    from pyfcstm.model.expr import Integer, Variable

    action = OnStage(stage='during', aspect=None, name=None, doc=None,
                     operations=[Operation('value', Variable('value'))],
                     is_abstract=False, state_path=('Root', None))
    model = StateMachine(defines={'value': VarDefine('value', 'int', Integer(0))},
                         root_state=State(name='Root', path=('Root',), substates={}, on_durings=[action]))
    report = inspect_model(model)
    site = report.variables[0].read_sites[0]
    assert site.source_path is None
    assert site.span is None
    assert report.to_json()['variables'][0]['read_sites'][0]['span'] is None


@pytest.mark.parametrize('field,value', [
    ('external_supply', 'random'), ('external_supply', None),
    ('diagnostic_policy', {}), ('diagnostic_policy', {'unused': 'false'}),
    ('read_sites', [{}]), ('write_sites', None),
])
def test_schema_rejects_invalid_variable_access_contract(field, value):
    import json
    import jsonschema
    import pyfcstm.diagnostics
    from pathlib import Path

    schema = json.loads(Path(pyfcstm.diagnostics.__file__).with_name('schema.json').read_text())
    payload = inspect_model(load_state_machine_from_text(SOURCE)).to_json()
    payload['variables'][0][field] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(schema).validate(payload)


def test_human_and_llm_reports_explain_variable_ownership():
    import json
    from pyfcstm.diagnostics.inspect_render import render_inspect_human, render_inspect_llm_json, render_inspect_llm_markdown

    report = inspect_model(load_state_machine_from_text(SOURCE))
    human = render_inspect_human(report, SOURCE)
    assert 'sensor: input_dynamic; external supply: cycle' in human
    assert 'limit: input_static; external supply: construction' in human
    assert 'result: output; external supply: none' in human
    llm = json.loads(render_inspect_llm_json(report, SOURCE))
    assert any('input/param' in rule and 'output' in rule for rule in llm['repair_protocol']['rules'])
    assert 'input/param' in render_inspect_llm_markdown(report, SOURCE)


def test_combo_access_indices_resolve_to_expanded_transitions():
    source = '''input int sensor; output int result = 0;
state Root { state A; state B; [*] -> A;
A -> B :: Begin + [sensor > 0] + End effect { result = sensor; }
}'''
    report = inspect_model(load_state_machine_from_text(source))
    sensor, result = report.variables
    assert sensor.read_sites
    assert result.write_sites
    for site in sensor.read_sites + result.write_sites:
        transition = report.transitions[site.transition_index]
        assert transition.combo_origin_refs
        assert site.state_path == 'Root'
        assert site.span is not None
    assert any(s.kind == 'guard' for s in sensor.read_sites)
    assert any(s.kind == 'effect' for s in sensor.read_sites)


def test_abstract_actions_and_initializers_do_not_invent_accesses():
    report = inspect_model(load_state_machine_from_text(
        'param int limit = 1; output int result = 0; state Root { enter abstract Compute; }'))
    assert all(v.read_sites == v.write_sites == () for v in report.variables)
    assert all(v.abstract_actions_in_scope for v in report.variables)


def test_forced_guard_inside_import_keeps_host_authored_location(tmp_path):
    leaf = tmp_path / 'leaf.fcstm'
    leaf.write_text('state Leaf { state X; state Y; [*] -> X; X -> Y; }', encoding='utf-8')
    host = tmp_path / 'host.fcstm'
    host.write_text('input int sensor; state Root { import "./leaf.fcstm" as A; state B; [*] -> A; !* -> B : if [sensor > 0]; }', encoding='utf-8')
    report = inspect_model(load_state_machine_from_file(host))
    sites = report.variables[0].read_sites
    assert sites
    assert any(site.state_path.startswith('Root.A') for site in sites)
    for site in sites:
        assert site.source_path == str(host)
        assert site.span is not None
        assert report.transitions[site.transition_index].is_forced
        assert report.transitions[site.transition_index].source_path == str(host)


@pytest.mark.parametrize('format_name', ['json', 'human', 'llm-json', 'llm-md'])
def test_cli_emits_role_access_contract_in_public_formats(tmp_path, format_name):
    import json
    from click.testing import CliRunner
    from pyfcstm.entry.cli import cli

    path = tmp_path / 'roles.fcstm'
    path.write_text(SOURCE, encoding='utf-8')
    result = CliRunner().invoke(cli, ['inspect', '-i', str(path), '--format', format_name])
    assert result.exit_code == 0, result.output
    if format_name == 'json':
        payload = json.loads(result.output)
        site = payload['variables'][0]['read_sites'][0]
        assert site['source_path'] == str(path)
        assert site['span']['line'] == 6
        assert payload['variables'][0]['external_supply'] == 'cycle'
    elif format_name == 'human':
        assert 'sensor: input_dynamic; external supply: cycle' in result.output
    else:
        assert 'input/param' in result.output


@pytest.mark.parametrize('field,value', [
    ('kind', 'initializer'), ('state_path', None), ('action', 1),
    ('action_index', -1), ('transition_index', '0'),
    ('statement_path', [-1]), ('statement_path', [0.5]),
    ('source_path', 1), ('span', {}),
    ('span', {'line': 0, 'column': 1, 'end_line': 1, 'end_column': 2}),
])
def test_schema_rejects_invalid_access_location(field, value):
    import json
    import jsonschema
    import pyfcstm.diagnostics
    from pathlib import Path

    schema = json.loads(Path(pyfcstm.diagnostics.__file__).with_name('schema.json').read_text())
    payload = inspect_model(load_state_machine_from_text(SOURCE)).to_json()
    payload['variables'][0]['read_sites'][0][field] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(schema).validate(payload)
