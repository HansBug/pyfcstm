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


def test_imported_region_preserves_abstract_during_and_exit_actions(tmp_path):
    (tmp_path / 'module.fcstm').write_text('''def int value = 0;
state Module { region Worker {
        state On { during abstract Tick; exit abstract Stop; }
        [*] -> On;
    } }''', encoding='utf-8')
    source = tmp_path / 'host.fcstm'
    source.write_text('state Host { import "module.fcstm" as Unit; [*] -> Unit; }', encoding='utf-8')
    model = load_state_machine_from_file(source)
    assert 'Unit_value' in model.defines
    leaf = model.root_state.substates['Unit'].regions['Worker'].substates['On']
    assert leaf.on_durings[0].is_abstract and leaf.on_durings[0].name == 'Tick'
    assert leaf.on_exits[0].is_abstract and leaf.on_exits[0].name == 'Stop'


def test_import_does_not_rebind_query_with_foreign_root(tmp_path):
    module = tmp_path / 'module.fcstm'
    module.write_text('state Module { during { if [active("Foreign.Leaf")] {} } }', encoding='utf-8')
    source = tmp_path / 'host.fcstm'
    source.write_text('state Host { import "module.fcstm" as Unit; [*] -> Unit; }', encoding='utf-8')
    model, diagnostics = load_state_machine_from_file(source, collect=True)
    assert model is None
    diagnostic = next(item for item in diagnostics if item.code == 'E_ACTIVE_QUERY_TARGET')
    assert diagnostic.refs == {'state_path': 'Foreign.Leaf', 'reason': 'invalid_path',
                               'source_path': str(module)}


def test_unused_import_event_mapping_to_missing_region_collects_error(tmp_path):
    (tmp_path / 'module.fcstm').write_text(
        'state Module { event Tick; state Idle; [*] -> Idle; }', encoding='utf-8')
    source = tmp_path / 'host.fcstm'
    source.write_text('''state Host {
        region Worker {
            state Container {
                import "module.fcstm" as Unit { event /Tick -> /Missing.Tick; }
                [*] -> Unit;
            }
            [*] -> Container;
        }
    }''', encoding='utf-8')
    _, diagnostics = load_state_machine_from_file(source, collect=True)
    assert any(item.code == 'E_IMPORT_MAPPING_INVALID' for item in diagnostics)


def test_unused_import_event_docs_match_the_named_region_event(tmp_path):
    (tmp_path / 'module.fcstm').write_text(
        'state Module { /* module docs */ event Tick; state Idle; [*] -> Idle; }',
        encoding='utf-8')
    source = tmp_path / 'host.fcstm'
    source.write_text('''state Host { region Worker {
        event Earlier;
        /* host docs */ event Shared;
        state Container {
            import "module.fcstm" as Unit { event /Tick -> /Worker.Shared; }
            [*] -> Unit;
        }
        [*] -> Container;
    } }''', encoding='utf-8')
    model = load_state_machine_from_file(source)
    events = model.root_state.regions['Worker'].events
    assert events['Earlier'].doc is None
    assert 'host docs' in events['Shared'].doc
    assert 'module docs' in events['Shared'].doc
