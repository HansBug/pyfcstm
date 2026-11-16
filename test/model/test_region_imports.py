"""Repeated imports keep region-local variables, paths and source ownership."""

import pytest

from pyfcstm.model import load_state_machine_from_file
from pyfcstm.utils import ModelValidationError

pytestmark = pytest.mark.unittest

MODULE = '''def int value = 0;
state Module {
    region Worker {
        event Tick;
        >> during before Observe { value = value + 1; }
        state On { enter Init { value = value + 2; } }
        state Off { enter ref /Worker.On.Init; }
        [*] -> On;
        On -> Off : /Worker.Tick effect { value = value + 3; }
        Off -> On : Tick;
    }
    region Observer {
        >> during before ref /Worker.Observe;
        state On;
        [*] -> On;
        On -> [*] : /Worker.Tick;
    }
}'''


def test_repeated_parallel_imports_rebase_all_owned_references(tmp_path):
    module = tmp_path / 'module.fcstm'
    module.write_text(MODULE, encoding='utf-8')
    source = tmp_path / 'host.fcstm'
    source.write_text('''state Host {
        import "./module.fcstm" as First;
        import "./module.fcstm" as Second;
        [*] -> First;
        First -> Second;
    }''', encoding='utf-8')
    model = load_state_machine_from_file(source)
    assert list(model.defines) == ['First_value', 'Second_value']
    for alias in ['First', 'Second']:
        owner = model.root_state.substates[alias]
        worker, observer = owner.regions.values()
        assert worker.events['Tick'].path_name == 'Host.%s.Worker.Tick' % alias
        assert worker.transitions[1].event is worker.events['Tick']
        assert observer.transitions[1].event is worker.events['Tick']
        assert worker.substates['Off'].on_enters[0].ref is worker.substates['On'].on_enters[0]
        assert observer.on_during_aspects[0].ref is worker.on_during_aspects[0]
        assert str(worker.transitions[1].effects[0].to_ast_node()) == '%s_value = %s_value + 3;' % (alias, alias)
        assert worker._source_path == str(module)
        assert worker.substates['On']._source_path == str(module)
        assert worker.transitions[1]._source_path == str(module)
        assert worker._span.line == 3


def test_nested_import_below_region_state_maps_events_into_host_region(tmp_path):
    (tmp_path / 'module.fcstm').write_text(MODULE, encoding='utf-8')
    source = tmp_path / 'host.fcstm'
    source.write_text('''def int shared = 10;
state Host {
    region Bus {
        event Tick;
        state Container {
            import "./module.fcstm" as Unit {
                def value -> shared;
                event /Worker.Tick -> /Bus.Tick;
            }
            [*] -> Unit;
        }
        [*] -> Container;
    }
}''', encoding='utf-8')
    model = load_state_machine_from_file(source)
    bus = model.root_state.regions['Bus']
    unit = bus.substates['Container'].substates['Unit']
    worker = unit.regions['Worker']
    assert list(model.defines) == ['shared']
    assert not worker.events
    assert worker.transitions[1].event is bus.events['Tick']
    assert worker.transitions[2].event is bus.events['Tick']
    assert unit.regions['Observer'].transitions[1].event is bus.events['Tick']
    assert str(worker.on_during_aspects[0].operations[0].to_ast_node()) == 'shared = shared + 1;'


@pytest.mark.parametrize('collect', [False, True])
def test_invalid_imported_region_preserves_diagnostic_source(tmp_path, collect):
    module = tmp_path / 'module.fcstm'
    module.write_text('state Module {\n region Empty {}\n}', encoding='utf-8')
    source = tmp_path / 'host.fcstm'
    source.write_text('state Host { import "module.fcstm" as Unit; [*] -> Unit; }', encoding='utf-8')
    if collect:
        model, diagnostics = load_state_machine_from_file(source, collect=True)
        assert model is None
    else:
        with pytest.raises(ModelValidationError) as error:
            load_state_machine_from_file(source)
        diagnostics = error.value.diagnostics
    diagnostic = next(item for item in diagnostics if item.code == 'E_REGION_STRUCTURE')
    assert diagnostic.refs['source_path'] == str(module)
    assert diagnostic.span.line == 2


@pytest.mark.parametrize('transition', [
    'On -> Off : /Worker.Tick + [value == 0];',
    '!On -> Off : /Worker.Tick;',
])
def test_imported_combo_and_forced_root_paths_are_rebased_once(tmp_path, transition):
    (tmp_path / 'module.fcstm').write_text('''def int value = 0;
state Module { region Worker {
    event Tick; state On; state Off; [*] -> On;
    %s
} }''' % transition, encoding='utf-8')
    source = tmp_path / 'host.fcstm'
    source.write_text('state Host { import "module.fcstm" as Unit; [*] -> Unit; }', encoding='utf-8')
    model = load_state_machine_from_file(source)
    region = model.root_state.substates['Unit'].regions['Worker']
    events = [edge.event for edge in region.transitions if edge.event is not None]
    assert events and all(event is region.events['Tick'] for event in events)
