"""Unsupported public consumers refuse models before producing partial output."""

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.utils import ModelValidationError

pytestmark = pytest.mark.unittest

SOURCE = 'state Root { region Worker { state Idle; [*] -> Idle; } }'


@pytest.mark.parametrize('single_file', [False, True])
def test_renderer_refusal_preserves_existing_output(tmp_path, single_file):
    model = load_state_machine_from_text(SOURCE)
    templates = tmp_path / 'templates'
    templates.mkdir()
    (templates / 'config.yaml').write_text('{}', encoding='utf-8')
    template = templates / 'machine.txt.j2'
    template.write_text('{{ model.root_state.name }}', encoding='utf-8')
    output = tmp_path / 'output'
    output.mkdir()
    preserved = output / 'machine.txt'
    preserved.write_text('existing output', encoding='utf-8')
    renderer = StateMachineCodeRenderer(str(templates))
    with pytest.raises(ModelValidationError) as caught:
        if single_file:
            renderer.render_one_file(model, str(preserved), str(template))
        else:
            renderer.render(model, str(output), clear_previous_directory=True)
    assert caught.value.diagnostics[0].code == 'E_UNSUPPORTED_FEATURE'
    assert preserved.read_text(encoding='utf-8') == 'existing output'
    assert [item.name for item in output.iterdir()] == ['machine.txt']


@pytest.mark.parametrize('name', [
    'build_leaf_level_macro_graph', 'topological_reachable_set', 'unreachable_states',
    'strongly_connected_components', 'topological_finite',
    'topological_inevitable_terminator', 'event_emission_to_consumer_reachable',
])
def test_topology_algorithms_accept_a_model_with_regions(name):
    from pyfcstm.verify import topology

    model = load_state_machine_from_text(SOURCE)
    getattr(topology, name)(model)


@pytest.mark.parametrize('kind', ['H', 'H*'])
def test_history_cannot_record_a_parallel_configuration(kind):
    source = '''state Root {
        state Group {
            [%s] -> Parallel;
            [*] -> Parallel;
            state Parallel { region Worker { state Idle; [*] -> Idle; } }
        }
        [*] -> Group;
    }''' % kind
    with pytest.raises(ModelValidationError) as caught:
        load_state_machine_from_text(source)
    assert caught.value.diagnostics[0].code == 'E_REGION_STRUCTURE'
    assert caught.value.diagnostics[0].refs['reason'] == 'history_boundary'


def test_ordinary_history_within_region_remains_available_in_model():
    source = '''state Root {
        region Worker {
            state Group { [H] -> Idle; [*] -> Idle; state Idle; }
            [*] -> Group.[H];
        }
    }'''
    model = load_state_machine_from_text(source)
    assert [item.owner_path for item in model.history_owners] == [('Root', 'Worker', 'Group')]
    region = model.root_state.regions['Worker']
    assert region.init_transitions[0].effects[-1].var_name == model.history_owners[0].goto_variable


@pytest.mark.parametrize('collect', [False, True])
@pytest.mark.parametrize('edge', [
    '[*] -> Group.[H];', 'Group -> Group.[H*];', '!Group -> Group.[H];',
])
def test_region_history_targets_require_declared_history(edge, collect):
    source = '''state Root { region Worker {
        state Group { state A; [*] -> A; }
        [*] -> Group;
        %s
    } }''' % edge
    if collect:
        _, diagnostics = load_state_machine_from_text(source, collect=True)
    else:
        with pytest.raises(ModelValidationError) as error:
            load_state_machine_from_text(source)
        diagnostics = error.value.diagnostics
    assert [item.code for item in diagnostics] == ['E_HISTORY_TARGET_UNDECLARED']
    assert diagnostics[0].refs['owner_path'] == 'Root.Worker.Group'


def test_inspect_reports_collected_errors_and_strict_build_warnings_for_region_models():
    from pyfcstm.diagnostics import inspect_model

    model, diagnostics = load_state_machine_from_text(
        'state Root { region Worker { state A; } }', collect=True)
    report = inspect_model(model, model_diagnostics=diagnostics)
    assert [item.code for item in report.diagnostics[:len(diagnostics)]] == [
        item.code for item in diagnostics]
    assert [item.path for item in report.regions] == ['Root.Worker']

    model = load_state_machine_from_text('''state Root { region Worker {
        state Group { state A; [*] -> A; [H] -> A; }
        [*] -> Group;
    } }''')
    assert 'W_HISTORY_UNUSED' in [item.code for item in inspect_model(model).diagnostics]


@pytest.mark.parametrize('uses_history', [False, True])
@pytest.mark.parametrize('operation', [
    '>> during before { if [1 == 1] { __hist_goto = 0; } }',
    'Group -> [*] effect { __hist_goto = 0; }',
])
def test_region_temporaries_follow_history_reserved_name_policy(uses_history, operation):
    source = '''state Root { region Worker {
        state Group { state A; [*] -> A; %s }
        [*] -> Group%s;
        %s
    } }''' % ('[H] -> A;' if uses_history else '',
             '.[H]' if uses_history else '', operation)
    _, diagnostics = load_state_machine_from_text(source, collect=True)
    assert [item.code for item in diagnostics] == [
        'E_HISTORY_RESERVED_PREFIX' if uses_history else 'W_HISTORY_RESERVED_PREFIX',
    ]
    assert diagnostics[0].refs['identifier_kind'] == 'temporary'
