# pyfcstm

[![PyPI](https://img.shields.io/pypi/v/pyfcstm)](https://pypi.org/project/pyfcstm/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyfcstm)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/pyfcstm)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pyfcstm)

![Loc](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/HansBug/7eb8c32d6549edaa09592ca2a5a47187/raw/loc.json)
![Comments](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/HansBug/7eb8c32d6549edaa09592ca2a5a47187/raw/comments.json)
[![Maintainability](https://api.codeclimate.com/v1/badges/5b6e14a915b63faeae90/maintainability)](https://codeclimate.com/github/HansBug/pyfcstm/maintainability)
[![codecov](https://codecov.io/gh/hansbug/pyfcstm/graph/badge.svg?token=NYSTMMTC2F)](https://codecov.io/gh/hansbug/pyfcstm)

[![Docs Deploy](https://github.com/hansbug/pyfcstm/workflows/Docs%20Deploy/badge.svg)](https://github.com/hansbug/pyfcstm/actions?query=workflow%3A%22Docs+Deploy%22)
[![Code Test](https://github.com/hansbug/pyfcstm/workflows/Code%20Test/badge.svg)](https://github.com/hansbug/pyfcstm/actions?query=workflow%3A%22Code+Test%22)
[![Badge Creation](https://github.com/hansbug/pyfcstm/workflows/Badge%20Creation/badge.svg)](https://github.com/hansbug/pyfcstm/actions?query=workflow%3A%22Badge+Creation%22)
[![Package Release](https://github.com/hansbug/pyfcstm/workflows/Package%20Release/badge.svg)](https://github.com/hansbug/pyfcstm/actions?query=workflow%3A%22Package+Release%22)

[![GitHub stars](https://img.shields.io/github/stars/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/network)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/hansbug/pyfcstm)
[![GitHub issues](https://img.shields.io/github/issues/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/issues)
[![GitHub pulls](https://img.shields.io/github/issues-pr/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/pulls)
[![Contributors](https://img.shields.io/github/contributors/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/graphs/contributors)
[![GitHub license](https://img.shields.io/github/license/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/blob/master/LICENSE)

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

    sc.validate()

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