"""Public model construction refuses syntax whose semantics are unavailable."""

import pytest

from pyfcstm.dsl import parse_condition, parse_state_machine_dsl
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.model.expr import parse_expr, parse_expr_from_string, parse_expr_node_to_expr
from pyfcstm.model.imports import assemble_state_machine_imports
from pyfcstm.utils import ModelValidationError

pytestmark = pytest.mark.unittest

SOURCES = [
    ('region', 'state Root { region Motor { state A; [*] -> A; } }'),
    ('region', 'state Root { state Child { region Only {} } [*] -> Child; }'),
    ('active', 'state Root { state A; [*] -> A; A -> [*] : if [active("A")]; }'),
    ('active', 'state Root { during { if [active("Root")] {} } }'),
    ('active', 'def int x = 0; state Root { enter { x = (active("Root")) ? 1 : 0; } }'),
    ('active', 'state Root { state A; [*] -> A; A -> [*] :: go + [active("A")]; }'),
    ('active', 'state Root { >> during before { if [active("Root")] {} } }'),
]


@pytest.mark.parametrize('feature,source', SOURCES)
@pytest.mark.parametrize('collect', [False, True])
def test_model_refuses_unsupported_syntax(feature, source, collect):
    program = parse_state_machine_dsl(source)
    before = str(program)
    if collect:
        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)
        assert model is None
    else:
        with pytest.raises(ModelValidationError) as error:
            parse_dsl_node_to_state_machine(program)
        diagnostics = error.value.diagnostics
    assert diagnostics
    assert {item.code for item in diagnostics} == {'E_UNSUPPORTED_FEATURE'}
    assert {item.refs['feature'] for item in diagnostics} == {feature}
    assert all(item.span is not None for item in diagnostics)
    assert str(program) == before
    assert not hasattr(program, '_source_path')


@pytest.mark.parametrize('feature,source', SOURCES[:4])
@pytest.mark.parametrize('collect', [False, True])
def test_imported_unsupported_syntax_never_builds_partial_model(tmp_path, feature, source, collect):
    child = tmp_path / 'child.fcstm'
    child.write_text(source, encoding='utf-8')
    middle = tmp_path / 'middle.fcstm'
    middle.write_text('state Middle { import "child.fcstm" as Child; [*] -> Child; }',
                      encoding='utf-8')
    program = parse_state_machine_dsl(
        'state Host { import "middle.fcstm" as Module; [*] -> Module; }'
    )
    if collect:
        model, diagnostics = parse_dsl_node_to_state_machine(
            program, path=str(tmp_path / 'host.fcstm'), collect=True)
        assert model is None
    else:
        with pytest.raises(ModelValidationError) as error:
            parse_dsl_node_to_state_machine(program, path=str(tmp_path))
        diagnostics = error.value.diagnostics
    assert diagnostics[0].code == 'E_UNSUPPORTED_FEATURE'
    assert diagnostics[0].refs['feature'] == feature
    assert diagnostics[0].refs['source_path'] == str(child)


def test_import_assembly_also_rejects_region_syntax():
    with pytest.raises(ModelValidationError) as error:
        assemble_state_machine_imports(parse_state_machine_dsl(SOURCES[0][1]))
    assert error.value.diagnostics[0].code == 'E_UNSUPPORTED_FEATURE'


@pytest.mark.parametrize('convert', [parse_expr, parse_expr_from_string])
@pytest.mark.parametrize('text', [
    'active("Root")', '!active("Root")',
    'True && active("Root")', '(active("Root")) ? 1 : 0',
])
def test_standalone_expression_rejects_active_query(convert, text):
    with pytest.raises(ModelValidationError) as error:
        convert(text)
    assert error.value.diagnostics[0].code == 'E_UNSUPPORTED_FEATURE'
    assert error.value.diagnostics[0].refs['feature'] == 'active'


def test_programmatic_expression_rejects_active_query_without_span():
    expression = parse_condition('active("Root")').expr
    expression._span = None
    with pytest.raises(ModelValidationError) as error:
        parse_expr_node_to_expr(expression)
    assert error.value.diagnostics[0].span is None


def test_collect_reports_distinct_unsupported_sites_once():
    program = parse_state_machine_dsl('''state Root {
        state A;
        [*] -> A;
        A -> [*] : [active("A")];
        during { if [active("Root")] {} }
        region Motor {}
    }''')
    model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)
    assert model is None
    assert sorted(item.refs['feature'] for item in diagnostics) == ['active', 'active', 'region']


@pytest.mark.parametrize('collect', [False, True])
def test_contextual_identifiers_remain_executable(collect):
    program = parse_state_machine_dsl('''def int active = 0;
        state region { state active; [*] -> active;
            active -> [*] : if [active > 0];
        }''')
    result = parse_dsl_node_to_state_machine(program, collect=collect)
    if collect:
        result, diagnostics = result
        assert diagnostics == []
    assert result.root_state.name == 'region'
