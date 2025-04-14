# pyfcstm

Some bullshit, still WIP.

```python
from pprint import pprint

from pyfcstm.model import Statechart, CompositeState, NormalState, Event, Transition

if __name__ == '__main__':
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

    # print(a)
    # print(a.chart)
    # print(sc.states)
    # print(sc.transitions)
    # print(sc.events)
    # print(sc.root_state)
    #
    # print(t1)

    # pprint(root.json)
    # pprint(a.json)
    # pprint(e1.json)
    # pprint(t1.json)

    pprint(sc.json)

    print(Statechart.from_json(sc.json))

    sc.to_yaml('test_export.yaml')
    Statechart.read_yaml('test_export.yaml')

```