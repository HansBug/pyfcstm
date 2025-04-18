import random
import uuid

import pytest

from pyfcstm.model import NormalState, Event, Transition, CompositeState, Statechart, PseudoState, StateType


@pytest.fixture
def mock_uuid4(monkeypatch):
    original_uuid4 = uuid.uuid4

    def _mocked_uuid4():

        bytes_ = bytes([random.randint(0, 255) for _ in range(16)])
        return uuid.UUID(bytes=bytes_, version=4)

    monkeypatch.setattr(uuid, "uuid4", _mocked_uuid4)
    try:
        random.seed(0)
        yield
    finally:
        monkeypatch.setattr(uuid, "uuid4", original_uuid4)


@pytest.fixture
def normal_state():
    return NormalState('TestState')


@pytest.fixture
def pseudo_state():
    return PseudoState('TestState')


@pytest.fixture
def event():
    return Event('TestEvent')


@pytest.fixture
def composite_state(normal_state):
    return CompositeState('TestComposite', initial_state=normal_state, states=[normal_state])


@pytest.fixture
def statechart(composite_state):
    return Statechart('TestChart', root_state=composite_state)


@pytest.mark.unittest
class TestModelState:
    def test_simple_integrate(self, mock_uuid4):
        a = NormalState('A')
        b = NormalState('B')
        c = NormalState('C')
        d = NormalState('D')

        e1 = Event('e1')
        e2 = Event('e2')
        e3 = Event('e3')
        e4 = Event('e4')

        t1 = Transition(a, b, e1)
        t2 = Transition(a, c, e2)
        t3 = Transition(b, d, e3)
        t4 = Transition(c, d, e4)

        root = CompositeState('Root', initial_state=a, states=[a, b, c, d])

        sc = Statechart(
            'chart1',
            root_state=root,
            states=[a, b, c, d, root],
            events=[e1, e2, e3, e4],
            transitions=[t1, t2, t3, t4],
        )

        assert sc.name == 'chart1'
        assert sc.root_state == root
        assert sc.root_state_id == root.id
        assert len(sc.states) == 5
        assert len(sc.events) == 4
        assert len(sc.transitions) == 4

        assert a in sc.states
        assert b in sc.states
        assert c in sc.states
        assert d in sc.states
        assert root in sc.states

        assert e1 in sc.events
        assert e2 in sc.events
        assert e3 in sc.events
        assert e4 in sc.events

        assert t1 in sc.transitions
        assert t2 in sc.transitions
        assert t3 in sc.transitions
        assert t4 in sc.transitions

        assert root.initial_state == a
        assert root.initial_state_id == a.id
        assert len(root.states) == 4

        assert t1.src_state == a
        assert t1.dst_state == b
        assert t1.event == e1

        assert t2.src_state == a
        assert t2.dst_state == c
        assert t2.event == e2

        assert t3.src_state == b
        assert t3.dst_state == d
        assert t3.event == e3

        assert t4.src_state == c
        assert t4.dst_state == d
        assert t4.event == e4

        assert sc.states.get_by_name('A') is a
        assert sc.states.get_by_name('B') is b
        assert sc.states.get_by_name('C') is c
        assert sc.states.get_by_name('D') is d
        assert sc.states.get_by_name('A', "B", "C", 'D') == (a, b, c, d)
        assert sc.states.get_by_name('A', 'b', 'C', 'd') == (a, None, c, None)

        assert sc.events.get_by_name('e1') is e1
        assert sc.events.get_by_name('e2') is e2
        assert sc.events.get_by_name('e3') is e3
        assert sc.events.get_by_name('e4') is e4
        assert sc.events.get_by_name('e1', 'e2', 'e3', 'e4') == (e1, e2, e3, e4)
        assert sc.events.get_by_name('e1', 'E2', 'e3', 'E4') == (e1, None, e3, None)

        with pytest.raises(TypeError):
            _ = sc.transitions.get_by_name('F')

        assert sc.root_state.states.get_by_name('A') is a
        assert sc.root_state.states.get_by_name('B') is b
        assert sc.root_state.states.get_by_name('C') is c
        assert sc.root_state.states.get_by_name('D') is d
        assert sc.root_state.states.get_by_name('A', "B", "C", 'D') == (a, b, c, d)
        assert sc.root_state.states.get_by_name('A', 'b', 'C', 'd') == (a, None, c, None)

        assert str(sc) == "<Statechart #a1016d07-0132-413c-a59a-8f5d33f3cb29, name='chart1', " \
                          "root_state=<CompositeState name='Root'>, states=<ChartElements[State] 5 items>, " \
                          "transitions=<ChartElements[Transition] 4 items>, events=<ChartElements[Event] 4 items>>"
        assert repr(sc) == "<Statechart name='chart1', root_state=<CompositeState name='Root'>>"
        assert str(sc.states) == ("State[<NormalState name='A'>, <NormalState name='B'>, <NormalState name='C'>, "
                                  "<NormalState name='D'>, <CompositeState name='Root'>]")
        assert repr(sc.states) == "<ChartElements[State] 5 items>"
        assert str(sc.transitions) == ("Transition[<Transition src_state=<NormalState name='A'>, "
                                       "dst_state=<NormalState name='B'>, event=<Event name='e1'>>, "
                                       "<Transition src_state=<NormalState name='A'>, dst_state=<NormalState name='C'>, "
                                       "event=<Event name='e2'>>, <Transition src_state=<NormalState name='B'>, "
                                       "dst_state=<NormalState name='D'>, event=<Event name='e3'>>, "
                                       "<Transition src_state=<NormalState name='C'>, dst_state=<NormalState name='D'>, "
                                       "event=<Event name='e4'>>]")
        assert repr(sc.transitions) == "<ChartElements[Transition] 4 items>"
        assert str(sc.events) == "Event[<Event name='e1'>, <Event name='e2'>, <Event name='e3'>, <Event name='e4'>]"
        assert repr(sc.events) == "<ChartElements[Event] 4 items>"

        assert str(sc.root_state.states) == "State[<NormalState name='A'>, <NormalState name='B'>, " \
                                            "<NormalState name='C'>, <NormalState name='D'>]"
        assert repr(sc.root_state.states) == "<StateElements 4 items>"

        assert sc.json == {
            'events': [{'guard': None,
                        'id': '1085f323-2d42-4c13-a9c8-8d786ed68ce6',
                        'name': 'e1'},
                       {'guard': None,
                        'id': 'fcb62aa6-3bf9-4b61-bc08-8a3b70be57aa',
                        'name': 'e2'},
                       {'guard': None, 'id': 'da1f334a-7017-450d-bf60-3dc82ebd3b12',
                        'name': 'e3'},
                       {'guard': None,
                        'id': '0b635e3f-f56b-4f0b-9933-852371249ab3',
                        'name': 'e4'}],
            'id': 'a1016d07-0132-413c-a59a-8f5d33f3cb29',
            'name': 'chart1',
            'preamble': [],
            'root_state_id': 'e4f90013-fda6-4fef-99d4-602a4207cdd5',
            'states': [{'description': '',
                        'id': 'c5d71484-f8cf-4bf4-b76f-47904730804b',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'A',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'type': 'normal'},
                       {'description': '',
                        'id': '9e3225a9-f133-45de-a168-f4e2851f072f',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'B',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'type': 'normal'},
                       {'description': '',
                        'id': 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'C',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'type': 'normal'},
                       {'description': '',
                        'id': '379a953f-aa68-43e3-aec5-a27b945e605f',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'D',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'type': 'normal'},
                       {'description': '',
                        'id': 'e4f90013-fda6-4fef-99d4-602a4207cdd5',
                        'initial_state_id': 'c5d71484-f8cf-4bf4-b76f-47904730804b',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'Root',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'state_ids': ['c5d71484-f8cf-4bf4-b76f-47904730804b',
                                      '9e3225a9-f133-45de-a168-f4e2851f072f',
                                      'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa',
                                      '379a953f-aa68-43e3-aec5-a27b945e605f'],
                        'type': 'composite'}],
            'transitions': [{'dst_state_id': '9e3225a9-f133-45de-a168-f4e2851f072f',
                             'event_id': '1085f323-2d42-4c13-a9c8-8d786ed68ce6',
                             'id': 'df5c1fef-1433-4866-85b7-f056681d5152',
                             'src_state_id': 'c5d71484-f8cf-4bf4-b76f-47904730804b'},
                            {'dst_state_id': 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa',
                             'event_id': 'fcb62aa6-3bf9-4b61-bc08-8a3b70be57aa',
                             'id': 'af803ce2-5906-41d1-9fb6-c6804e06ea28',
                             'src_state_id': 'c5d71484-f8cf-4bf4-b76f-47904730804b'},
                            {'dst_state_id': '379a953f-aa68-43e3-aec5-a27b945e605f',
                             'event_id': 'da1f334a-7017-450d-bf60-3dc82ebd3b12',
                             'id': 'ab178f45-7af6-4493-b743-9ec6d4290062',
                             'src_state_id': '9e3225a9-f133-45de-a168-f4e2851f072f'},
                            {'dst_state_id': '379a953f-aa68-43e3-aec5-a27b945e605f',
                             'event_id': '0b635e3f-f56b-4f0b-9933-852371249ab3',
                             'id': 'ab517a72-e5c1-4410-8dd6-1754e4208450',
                             'src_state_id': 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa'}]
        }

    def test_normal_state(self, mock_uuid4, normal_state):
        assert normal_state.name == 'TestState'
        assert normal_state.id == 'c5d71484-f8cf-4bf4-b76f-47904730804b'
        assert normal_state.description == ''
        assert normal_state.min_time_lock is None
        assert normal_state.max_time_lock is None
        assert normal_state.on_entry is None
        assert normal_state.on_during is None
        assert normal_state.on_exit is None
        assert normal_state.chart is None
        assert str(normal_state) == "<NormalState #c5d71484-f8cf-4bf4-b76f-47904730804b, name='TestState'>"
        assert repr(normal_state) == "<NormalState name='TestState'>"
        assert normal_state.json == {
            'description': '',
            'id': 'c5d71484-f8cf-4bf4-b76f-47904730804b',
            'max_time_lock': None,
            'min_time_lock': None,
            'name': 'TestState',
            'on_during': None,
            'on_entry': None,
            'on_exit': None,
            'type': 'normal'
        }

    def test_pseudo_state(self, mock_uuid4, pseudo_state):
        assert pseudo_state.name == 'TestState'
        assert pseudo_state.id == 'c5d71484-f8cf-4bf4-b76f-47904730804b'
        assert pseudo_state.description == ''
        assert pseudo_state.min_time_lock is None
        assert pseudo_state.max_time_lock is None
        assert pseudo_state.on_entry is None
        assert pseudo_state.on_during is None
        assert pseudo_state.on_exit is None
        assert pseudo_state.chart is None
        assert str(pseudo_state) == "<PseudoState #c5d71484-f8cf-4bf4-b76f-47904730804b, name='TestState'>"
        assert repr(pseudo_state) == "<PseudoState name='TestState'>"
        assert pseudo_state.json == {
            'description': '',
            'id': 'c5d71484-f8cf-4bf4-b76f-47904730804b',
            'max_time_lock': None,
            'min_time_lock': None,
            'name': 'TestState',
            'on_during': None,
            'on_entry': None,
            'on_exit': None,
            'type': 'pseudo'
        }

    def test_event(self, mock_uuid4, event):
        assert event.name == 'TestEvent'
        assert event.id == 'c5d71484-f8cf-4bf4-b76f-47904730804b'
        assert event.guard is None
        assert event.chart is None
        assert str(event) == "<Event #c5d71484-f8cf-4bf4-b76f-47904730804b, name='TestEvent', guard=None>"
        assert repr(event) == "<Event name='TestEvent'>"
        assert event.json == {
            'guard': None,
            'id': 'c5d71484-f8cf-4bf4-b76f-47904730804b',
            'name': 'TestEvent'
        }

    def test_transition(self, mock_uuid4, normal_state, event):
        transition = Transition(normal_state, normal_state, event)
        assert transition.id == 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa'
        assert transition.src_state_id == normal_state.id
        assert transition.dst_state_id == normal_state.id
        assert transition.event_id == event.id
        assert transition.chart is None
        assert str(
            transition) == "<Transition #cc00fcaa-7ca6-4061-b17a-48e52e29a3fa, src_state='c5d71484-f8cf-4bf4-b76f-47904730804b', dst_state='c5d71484-f8cf-4bf4-b76f-47904730804b', event='9e3225a9-f133-45de-a168-f4e2851f072f'>"
        assert repr(
            transition) == "<Transition src_state='c5d71484-f8cf-4bf4-b76f-47904730804b', dst_state='c5d71484-f8cf-4bf4-b76f-47904730804b', event='9e3225a9-f133-45de-a168-f4e2851f072f'>"
        assert transition.json == {
            'dst_state_id': 'c5d71484-f8cf-4bf4-b76f-47904730804b',
            'event_id': '9e3225a9-f133-45de-a168-f4e2851f072f',
            'id': 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa',
            'src_state_id': 'c5d71484-f8cf-4bf4-b76f-47904730804b'
        }

    def test_composite_state(self, mock_uuid4, composite_state, normal_state):
        assert composite_state.name == 'TestComposite'
        assert composite_state.id == '9e3225a9-f133-45de-a168-f4e2851f072f'
        assert composite_state.initial_state_id == normal_state.id
        assert len(composite_state.states) == 1
        assert normal_state in composite_state.states
        assert str(
            composite_state) == "<CompositeState #9e3225a9-f133-45de-a168-f4e2851f072f, name='TestComposite', states=<StateElements 1 item>>"
        assert repr(composite_state) == "<CompositeState name='TestComposite'>"
        assert composite_state.json == {
            'description': '',
            'id': '9e3225a9-f133-45de-a168-f4e2851f072f',
            'initial_state_id': 'c5d71484-f8cf-4bf4-b76f-47904730804b',
            'max_time_lock': None,
            'min_time_lock': None,
            'name': 'TestComposite',
            'on_during': None,
            'on_entry': None,
            'on_exit': None,
            'state_ids': ['c5d71484-f8cf-4bf4-b76f-47904730804b'],
            'type': 'composite'
        }


@pytest.fixture
def state_type():
    return StateType


@pytest.mark.unittest
class TestStateType:
    def test_state_type_values(self, state_type):
        assert state_type.COMPOSITE.value == 'composite'
        assert state_type.NORMAL.value == 'normal'
        assert state_type.PSEUDO.value == 'pseudo'

    def test_get_cls_composite(self, state_type):
        assert state_type.COMPOSITE.get_cls() == CompositeState

    def test_get_cls_normal(self, state_type):
        assert state_type.NORMAL.get_cls() == NormalState

    def test_get_cls_pseudo(self, state_type):
        assert state_type.PSEUDO.get_cls() == PseudoState

    def test_loads_enum_value(self, state_type):
        assert state_type.loads(state_type.COMPOSITE) == state_type.COMPOSITE
        assert state_type.loads(state_type.NORMAL) == state_type.NORMAL
        assert state_type.loads(state_type.PSEUDO) == state_type.PSEUDO

    def test_loads_string_value(self, state_type):
        assert state_type.loads('composite') == state_type.COMPOSITE
        assert state_type.loads('COMPOSITE') == state_type.COMPOSITE
        assert state_type.loads('normal') == state_type.NORMAL
        assert state_type.loads('NORMAL') == state_type.NORMAL
        assert state_type.loads('pseudo') == state_type.PSEUDO
        assert state_type.loads('PSEUDO') == state_type.PSEUDO

    def test_loads_invalid_type(self, state_type):
        with pytest.raises(TypeError) as exc_info:
            state_type.loads(123)
        assert str(exc_info.value) == "Unknown state value type - 123."

    def test_loads_invalid_string(self, state_type):
        with pytest.raises(KeyError):
            state_type.loads('invalid')

    def test_statechart_from_json(self):
        sc = Statechart.from_json({
            'events': [{'guard': None,
                        'id': '1085f323-2d42-4c13-a9c8-8d786ed68ce6',
                        'name': 'e1'},
                       {'guard': None,
                        'id': 'fcb62aa6-3bf9-4b61-bc08-8a3b70be57aa',
                        'name': 'e2'},
                       {'guard': None, 'id': 'da1f334a-7017-450d-bf60-3dc82ebd3b12',
                        'name': 'e3'},
                       {'guard': None,
                        'id': '0b635e3f-f56b-4f0b-9933-852371249ab3',
                        'name': 'e4'}],
            'id': 'a1016d07-0132-413c-a59a-8f5d33f3cb29',
            'name': 'chart1',
            'preamble': [],
            'root_state_id': 'e4f90013-fda6-4fef-99d4-602a4207cdd5',
            'states': [{'description': '',
                        'id': 'c5d71484-f8cf-4bf4-b76f-47904730804b',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'A',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'type': 'normal'},
                       {'description': '',
                        'id': '9e3225a9-f133-45de-a168-f4e2851f072f',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'B',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'type': 'normal'},
                       {'description': '',
                        'id': 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'C',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'type': 'normal'},
                       {'description': '',
                        'id': '379a953f-aa68-43e3-aec5-a27b945e605f',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'D',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'type': 'normal'},
                       {'description': '',
                        'id': 'e4f90013-fda6-4fef-99d4-602a4207cdd5',
                        'initial_state_id': 'c5d71484-f8cf-4bf4-b76f-47904730804b',
                        'max_time_lock': None,
                        'min_time_lock': None,
                        'name': 'Root',
                        'on_during': None,
                        'on_entry': None,
                        'on_exit': None,
                        'state_ids': ['c5d71484-f8cf-4bf4-b76f-47904730804b',
                                      '9e3225a9-f133-45de-a168-f4e2851f072f',
                                      'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa',
                                      '379a953f-aa68-43e3-aec5-a27b945e605f'],
                        'type': 'composite'}],
            'transitions': [{'dst_state_id': '9e3225a9-f133-45de-a168-f4e2851f072f',
                             'event_id': '1085f323-2d42-4c13-a9c8-8d786ed68ce6',
                             'id': 'df5c1fef-1433-4866-85b7-f056681d5152',
                             'src_state_id': 'c5d71484-f8cf-4bf4-b76f-47904730804b'},
                            {'dst_state_id': 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa',
                             'event_id': 'fcb62aa6-3bf9-4b61-bc08-8a3b70be57aa',
                             'id': 'af803ce2-5906-41d1-9fb6-c6804e06ea28',
                             'src_state_id': 'c5d71484-f8cf-4bf4-b76f-47904730804b'},
                            {'dst_state_id': '379a953f-aa68-43e3-aec5-a27b945e605f',
                             'event_id': 'da1f334a-7017-450d-bf60-3dc82ebd3b12',
                             'id': 'ab178f45-7af6-4493-b743-9ec6d4290062',
                             'src_state_id': '9e3225a9-f133-45de-a168-f4e2851f072f'},
                            {'dst_state_id': '379a953f-aa68-43e3-aec5-a27b945e605f',
                             'event_id': '0b635e3f-f56b-4f0b-9933-852371249ab3',
                             'id': 'ab517a72-e5c1-4410-8dd6-1754e4208450',
                             'src_state_id': 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa'}]
        })

        # Check basic properties
        assert sc.id == 'a1016d07-0132-413c-a59a-8f5d33f3cb29'
        assert sc.name == 'chart1'
        assert sc.preamble == []

        # Check states
        assert len(sc.states) == 5
        state_a = sc.states.get_by_name('A')
        assert state_a.name == 'A'
        assert state_a.id == 'c5d71484-f8cf-4bf4-b76f-47904730804b'
        assert isinstance(state_a, NormalState)
        assert str(state_a) == "<NormalState #c5d71484-f8cf-4bf4-b76f-47904730804b, name='A'>"

        state_b = sc.states.get_by_name('B')
        assert state_b.name == 'B'
        assert state_b.id == '9e3225a9-f133-45de-a168-f4e2851f072f'
        assert isinstance(state_b, NormalState)
        assert str(state_b) == "<NormalState #9e3225a9-f133-45de-a168-f4e2851f072f, name='B'>"

        state_c = sc.states.get_by_name('C')
        assert state_c.name == 'C'
        assert state_c.id == 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa'
        assert isinstance(state_c, NormalState)
        assert str(state_c) == "<NormalState #cc00fcaa-7ca6-4061-b17a-48e52e29a3fa, name='C'>"

        state_d = sc.states.get_by_name('D')
        assert state_d.name == 'D'
        assert state_d.id == '379a953f-aa68-43e3-aec5-a27b945e605f'
        assert isinstance(state_d, NormalState)
        assert str(state_d) == "<NormalState #379a953f-aa68-43e3-aec5-a27b945e605f, name='D'>"

        root_state = sc.states.get_by_name('Root')
        assert root_state.name == 'Root'
        assert root_state.id == 'e4f90013-fda6-4fef-99d4-602a4207cdd5'
        assert isinstance(root_state, CompositeState)
        assert root_state.initial_state is state_a
        assert root_state.initial_state_id == 'c5d71484-f8cf-4bf4-b76f-47904730804b'
        assert str(
            root_state) == "<CompositeState #e4f90013-fda6-4fef-99d4-602a4207cdd5, name='Root', states=<StateElements 4 items>>"
        assert str(root_state.states) == "State[<NormalState name='A'>, <NormalState name='B'>, " \
                                         "<NormalState name='C'>, <NormalState name='D'>]"

        # Check events
        assert len(sc.events) == 4
        event_e1 = sc.events.get_by_name('e1')
        assert event_e1.name == 'e1'
        assert event_e1.id == '1085f323-2d42-4c13-a9c8-8d786ed68ce6'

        event_e2 = sc.events.get_by_name('e2')
        assert event_e2.name == 'e2'
        assert event_e2.id == 'fcb62aa6-3bf9-4b61-bc08-8a3b70be57aa'

        event_e3 = sc.events.get_by_name('e3')
        assert event_e3.name == 'e3'
        assert event_e3.id == 'da1f334a-7017-450d-bf60-3dc82ebd3b12'

        event_e4 = sc.events.get_by_name('e4')
        assert event_e4.name == 'e4'
        assert event_e4.id == '0b635e3f-f56b-4f0b-9933-852371249ab3'

        # Check transitions
        assert len(sc.transitions) == 4

        # A -> B transition
        transition_1 = sc.transitions['df5c1fef-1433-4866-85b7-f056681d5152']
        assert transition_1.src_state is state_a
        assert transition_1.src_state_id == state_a.id
        assert transition_1.dst_state is state_b
        assert transition_1.dst_state_id == state_b.id
        assert transition_1.event is event_e1
        assert transition_1.event_id == event_e1.id
        assert str(transition_1) == "<Transition #df5c1fef-1433-4866-85b7-f056681d5152, " \
                                    "src_state=<NormalState name='A'>, dst_state=<NormalState name='B'>, " \
                                    "event=<Event name='e1'>>"

        # A -> C transition
        transition_2 = sc.transitions['af803ce2-5906-41d1-9fb6-c6804e06ea28']
        assert transition_2.src_state is state_a
        assert transition_2.src_state_id == state_a.id
        assert transition_2.dst_state is state_c
        assert transition_2.dst_state_id == state_c.id
        assert transition_2.event is event_e2
        assert transition_2.event_id == event_e2.id
        assert str(transition_2) == "<Transition #af803ce2-5906-41d1-9fb6-c6804e06ea28, " \
                                    "src_state=<NormalState name='A'>, dst_state=<NormalState name='C'>, " \
                                    "event=<Event name='e2'>>"

        # B -> D transition
        transition_3 = sc.transitions['ab178f45-7af6-4493-b743-9ec6d4290062']
        assert transition_3.src_state is state_b
        assert transition_3.src_state_id == state_b.id
        assert transition_3.dst_state is state_d
        assert transition_3.dst_state_id == state_d.id
        assert transition_3.event is event_e3
        assert transition_3.event_id == event_e3.id
        assert str(transition_3) == "<Transition #ab178f45-7af6-4493-b743-9ec6d4290062, " \
                                    "src_state=<NormalState name='B'>, dst_state=<NormalState name='D'>, " \
                                    "event=<Event name='e3'>>"

        # C -> D transition
        transition_4 = sc.transitions['ab517a72-e5c1-4410-8dd6-1754e4208450']
        assert transition_4.src_state is state_c
        assert transition_4.src_state_id == state_c.id
        assert transition_4.dst_state is state_d
        assert transition_4.dst_state_id == state_d.id
        assert transition_4.event is event_e4
        assert transition_4.event_id == event_e4.id
        assert str(transition_4) == "<Transition #ab517a72-e5c1-4410-8dd6-1754e4208450, " \
                                    "src_state=<NormalState name='C'>, dst_state=<NormalState name='D'>, " \
                                    "event=<Event name='e4'>>"

        # Check root states
        assert len(sc.root_state.states) == 4
        state_a = sc.root_state.states.get('c5d71484-f8cf-4bf4-b76f-47904730804b')
        assert state_a.name == 'A'
        assert state_a.id == 'c5d71484-f8cf-4bf4-b76f-47904730804b'
        assert isinstance(state_a, NormalState)
        assert str(state_a) == "<NormalState #c5d71484-f8cf-4bf4-b76f-47904730804b, name='A'>"

        state_b = sc.root_state.states.get('9e3225a9-f133-45de-a168-f4e2851f072f')
        assert state_b.name == 'B'
        assert state_b.id == '9e3225a9-f133-45de-a168-f4e2851f072f'
        assert isinstance(state_b, NormalState)
        assert str(state_b) == "<NormalState #9e3225a9-f133-45de-a168-f4e2851f072f, name='B'>"

        state_c = sc.root_state.states.get('cc00fcaa-7ca6-4061-b17a-48e52e29a3fa')
        assert state_c.name == 'C'
        assert state_c.id == 'cc00fcaa-7ca6-4061-b17a-48e52e29a3fa'
        assert isinstance(state_c, NormalState)
        assert str(state_c) == "<NormalState #cc00fcaa-7ca6-4061-b17a-48e52e29a3fa, name='C'>"

        state_d = sc.root_state.states.get('379a953f-aa68-43e3-aec5-a27b945e605f')
        assert state_d.name == 'D'
        assert state_d.id == '379a953f-aa68-43e3-aec5-a27b945e605f'
        assert isinstance(state_d, NormalState)
        assert str(state_d) == "<NormalState #379a953f-aa68-43e3-aec5-a27b945e605f, name='D'>"
