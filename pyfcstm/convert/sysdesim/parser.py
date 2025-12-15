import json
import warnings
from typing import Optional

from lxml.etree import _Element, _ElementTree
from lxml.etree import parse as lxml_parse

from .model import Signal, SignalEvent, TimeEvent, Clazz, StateMachine, Region, Transition, State, Model


class SysDesimParser:
    def __init__(self, tree: _ElementTree, root: _Element):
        self.tree: _ElementTree = tree
        self.root: _Element = root

    @property
    def namespaces(self):
        return self.root.nsmap

    @classmethod
    def parse_file(cls, file_path: str):
        tree = lxml_parse(file_path)
        root: _Element = tree.getroot()
        return cls(tree=tree, root=root)

    def get_model_elements(self):
        return self.root.xpath('uml:Model', namespaces=self.namespaces)

    def get_packaged_elements(self, model: _Element):
        return model.xpath('packagedElement', namespaces=self.namespaces)

    def _get_key(self, key: str, namespace: Optional[str] = None):
        if not namespace:
            return key
        else:
            return f'{{{self.namespaces[namespace]}}}{key}'

    def parse_signal(self, element: _Element):
        return Signal(
            id=element.get(self._get_key('id', 'xmi')),
            type=element.get(self._get_key('type', 'xmi')),
            name=element.get(self._get_key('name')),
        )

    def parse_signal_event(self, element: _Element):
        return SignalEvent(
            id=element.get(self._get_key('id', 'xmi')),
            type=element.get(self._get_key('type', 'xmi')),
            name=element.get(self._get_key('name')),
            signal=element.get(self._get_key('signal')),
        )

    def parse_time_expression(self, element: _Element):
        return self.parse_literal_string(
            element.xpath('expr[@xmi:type="uml:LiteralString"]', namespaces=self.namespaces)[0],
        )

    def parse_literal_string(self, element: _Element):
        return element.get(self._get_key('value'))

    def parse_time_event(self, element: _Element):
        return TimeEvent(
            id=element.get(self._get_key('id', 'xmi')),
            type=element.get(self._get_key('type', 'xmi')),
            name=element.get(self._get_key('name')),
            is_relative=json.loads(element.get(self._get_key('isRelative'))),
            expression=self.parse_time_expression(
                element.xpath('when', namespaces=self.namespaces)[0],
            ),
        )

    def parse_clazz(self, element: _Element):
        return Clazz(
            id=element.get(self._get_key('id', 'xmi')),
            type=element.get(self._get_key('type', 'xmi')),
            name=element.get(self._get_key('name')),
            classifier_behavior=element.get(self._get_key('classifierBehavior')),
            state_machine=self.parse_state_machine(
                element.xpath('ownedBehavior[@xmi:type="uml:StateMachine"]', namespaces=self.namespaces)[0],
            )
        )

    def parse_state_machine(self, element: _Element):
        return StateMachine(
            id=element.get(self._get_key('id', 'xmi')),
            type=element.get(self._get_key('type', 'xmi')),
            name=element.get(self._get_key('name')),
            regions=[self.parse_region(e) for e in element.xpath('region', namespaces=self.namespaces)],
        )

    def parse_region(self, element: _Element):
        return Region(
            id=element.get(self._get_key('id', 'xmi')),
            type=element.get(self._get_key('type', 'xmi')),
            name=element.get(self._get_key('name')),
            transitions=[self.parse_transition(e) for e in element.xpath('transition', namespaces=self.namespaces)],
            states=[self.parse_state(e) for e in element.xpath('subvertex', namespaces=self.namespaces)],
        )

    def parse_transition(self, element: _Element):
        triggers = element.xpath('trigger', namespaces=self.namespaces)
        return Transition(
            id=element.get(self._get_key('id', 'xmi')),
            type=element.get(self._get_key('type', 'xmi')),
            name=element.get(self._get_key('name')),
            source=element.get(self._get_key('source')),
            target=element.get(self._get_key('target')),
            event_trigger=self.parse_event_trigger(triggers[0]) if triggers else None,
        )

    def parse_event_trigger(self, element: _Element):
        return element.get(self._get_key('event'))

    def parse_state(self, element: _Element):
        return State(
            id=element.get(self._get_key('id', 'xmi')),
            type=element.get(self._get_key('type', 'xmi')),
            name=element.get(self._get_key('name')),
            regions=[self.parse_region(e) for e in element.xpath('region', namespaces=self.namespaces)],
        )

    def parse_packaged_element(self, element: _Element):
        type_ = element.attrib[self._get_key('type', 'xmi')]
        if type_ == 'uml:Signal':
            return self.parse_signal(element)
        elif type_ == 'uml:SignalEvent':
            return self.parse_signal_event(element)
        elif type_ == 'uml:TimeEvent':
            return self.parse_time_event(element)
        elif type_ == 'uml:Class':
            return self.parse_clazz(element)
        else:
            warnings.warn(f'Cannot parse element with type {type_!r}, skipped.')
            return None

    def parse_model(self, element: _Element):
        signals = {}
        events = {}
        clazz = None
        for e in self.get_packaged_elements(element):
            item = self.parse_packaged_element(e)
            if item is None:
                continue

            if isinstance(item, Clazz):
                clazz = item
            elif isinstance(item, (TimeEvent, SignalEvent)):
                events[item.id] = item
            elif isinstance(item, Signal):
                signals[item.id] = item
            else:
                raise TypeError(f'Unknown item type - {item!r}')

        for _, event in events.items():
            if isinstance(event, SignalEvent):
                event.signal_object = signals[event.signal]

        return Model(
            clazz=clazz,
            events=events,
        )


if __name__ == '__main__':
    pass
