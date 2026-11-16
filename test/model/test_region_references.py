"""Region segments are resolved explicitly in public event and action paths."""

import pytest

from pyfcstm.diagnostics.sink import DiagnosticSink
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.utils import ModelValidationError

pytestmark = pytest.mark.unittest

SOURCE = '''state Root {
    event Shared;
    region Left {
        event Tick;
        >> during before abstract Before;
        state On { enter abstract Start; event Tick; }
        state Off { enter ref /Left.On.Start; }
        [*] -> On;
        On -> Off : /Right.Tick;
        Off -> On :: Tick;
    }
    region Right {
        event Tick;
        >> during before ref /Left.Before;
        state On { enter ref /Left.On.Start; }
        [*] -> On;
        On -> [*] : /Shared;
    }
}'''


def test_event_and_action_references_cross_named_region_segments():
    model = load_state_machine_from_text(SOURCE)
    left, right = model.root_state.regions.values()
    assert left.transitions[1].event is right.events['Tick']
    assert left.transitions[2].event.path_name == 'Root.Left.Off.Tick'
    assert right.transitions[1].event is model.root_state.events['Shared']
    assert left.substates['Off'].on_enters[0].ref is left.substates['On'].on_enters[0]
    assert right.substates['On'].on_enters[0].ref is left.substates['On'].on_enters[0]
    assert right.on_during_aspects[0].ref is left.on_during_aspects[0]
    assert model.resolve_event('Root.Left.Tick') is left.events['Tick']
    assert model.root_state.resolve_event('Left.On.Tick') is left.substates['On'].events['Tick']
    assert left.resolve_event('Tick') is left.events['Tick']
    assert left.resolve_event('.Shared') is model.root_state.events['Shared']
    assert left.substates['On'].resolve_event('.Tick') is left.events['Tick']
    assert left.substates['On'].resolve_event('/Right.Tick') is right.events['Tick']
    assert str(load_state_machine_from_text(str(model.to_ast_node())).to_ast_node()) == str(model.to_ast_node())


@pytest.mark.parametrize('reference', ['Shared', 'Missing.Tick', '/Missing.Tick'])
def test_region_event_lookup_never_searches_ancestors(reference):
    model = load_state_machine_from_text('''state Root { event Shared;
        region Worker { state On; [*] -> On; }
    }''')
    region = model.root_state.regions['Worker']
    with pytest.raises(ModelValidationError):
        region.resolve_event(reference)
    sink = DiagnosticSink(collect=True)
    assert region.resolve_event(reference, collect_into=sink) is None
    assert [item.code for item in sink.diagnostics] == ['E_EVENT_NOT_FOUND']


def test_forced_event_and_relative_action_paths_include_regions():
    model = load_state_machine_from_text('''state Root {
        region Worker {
            event Abort;
            state Group {
                state On { enter abstract Init; }
                enter ref On.Init;
                [*] -> On;
            }
            state Off;
            [*] -> Group;
            !Group -> Off : /Worker.Abort;
        }
    }''')
    region = model.root_state.regions['Worker']
    group = region.substates['Group']
    assert group.on_enters[0].ref is group.substates['On'].on_enters[0]
    assert all(edge.event is region.events['Abort'] for edge in region.transitions if edge.is_forced)

