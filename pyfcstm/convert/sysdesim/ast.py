import warnings
from typing import List, Tuple, Optional, Set

from .model import StateMachine, Model, State, Region, SignalEvent, TimeEvent, Transition
from ...dsl import node as dsl_node
from ...utils import to_identifier

class SysMLConverter:
    """
    鲁棒性转换器。
    在保持 pyfcstm 原始 extra_name 语义约定的基础上，
    实现全局跳转扫描与递归并发拆分。
    """
    def __init__(self, model: Model):
        self.model = model
        self.extra_roots: List[dsl_node.StateDefinition] = []
        self.global_transition_pool: List[Transition] = []
        self._index_all_transitions(model.clazz.state_machine)

    def _index_all_transitions(self, container):
        if hasattr(container, 'regions'):
            for r in container.regions:
                self.global_transition_pool.extend(r.transitions)
                for s in r.states:
                    self._index_all_transitions(s)

    def _get_state_id(self, state: State) -> str:
        if state.type == 'uml:Pseudostate':
            return '[*]'
        # 机器读的 ID
        name_or_id = state.name if state.name else state.id
        return to_identifier(name_or_id)

    def _get_event_mapping(self, event_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        获取事件的机器ID和人类显示名。
        返回: (identifier_name, original_display_name)
        """
        if not event_id: return None, None
        event = self.model.events.get(event_id)
        if isinstance(event, SignalEvent):
            raw = event.signal_object.name
            return to_identifier(raw) if raw else None, raw
        elif isinstance(event, TimeEvent):
            display = f"After {event.expression}"
            return to_identifier(display), display
        return None, None

    def _extract_all_events(self):
        """提取所有事件，严格遵循 (name=标识符, extra_name=原始名) 的约定"""
        nodes = []
        for _, event in self.model.events.items():
            if isinstance(event, (SignalEvent, TimeEvent)):
                evt_id, raw_display = self._get_event_mapping(event.id)
                if evt_id:
                    nodes.append(dsl_node.EventDefinition(
                        name=evt_id, 
                        extra_name=raw_display
                    ))
        return nodes

    def convert(self, state_machine: StateMachine) -> List[dsl_node.StateDefinition]:
        self.extra_roots = []
        main_substates, main_transitions, _ = self._convert_region(state_machine.regions[0])
        main_root = dsl_node.StateDefinition(
            name='Root', extra_name='<根状态>',
            events=self._extract_all_events(),
            substates=main_substates, transitions=main_transitions,
        )
        for i in range(1, len(state_machine.regions)):
            self._push_extra_region(state_machine.regions[i], f"Root_Region_{i}", f"<根状态-并发区域{i}>")
        return [main_root] + self.extra_roots

    def _push_extra_region(self, region: Region, root_name: str, extra_name: str):
        sub_s, sub_t, _ = self._convert_region(region)
        self.extra_roots.append(dsl_node.StateDefinition(
            name=root_name, extra_name=extra_name,
            events=self._extract_all_events(),
            substates=sub_s, transitions=sub_t,
        ))

    def _convert_state(self, state: State) -> Tuple[dsl_node.StateDefinition, List[Transition]]:
        promoted = []
        if state.regions:
            sub_s, sub_t, sub_p = self._convert_region(state.regions[0])
            promoted.extend(sub_p)
            for i in range(1, len(state.regions)):
                name_id = f"{self._get_state_id(state)}_Region_{i}"
                # 语义保护：保持父级状态名在拆分模型标题中的展示
                display_label = f"{state.name} (Region {i})" if state.name else f"Region {i}"
                self._push_extra_region(state.regions[i], name_id, display_label)
            
            node = dsl_node.StateDefinition(
                name=self._get_state_id(state), 
                extra_name=state.name, 
                substates=sub_s, transitions=sub_t
            )
        else:
            node = dsl_node.StateDefinition(
                name=self._get_state_id(state), 
                extra_name=state.name
            )
        return node, promoted

    def _convert_region(self, region: Region) -> Tuple[list, list, list]:
        states, transitions, promoted_out = [], [], []
        d_states = {s.id: s for s in region.states}
        local_state_ids: Set[str] = set(d_states.keys())

        for state in region.states:
            if state.type != 'uml:Pseudostate':
                node, child_promoted = self._convert_state(state)
                states.append(node)
                for t in child_promoted:
                    if t.target in local_state_ids:
                        evt_id, _ = self._get_event_mapping(t.event_trigger)
                        transitions.append(dsl_node.TransitionDefinition(
                            from_state=self._get_state_id(state), to_state=self._get_state_id(d_states[t.target]),
                            event_id=dsl_node.ChainID([evt_id], is_absolute=True) if evt_id else None,
                            condition_expr=None, post_operations=[]))
                    else:
                        promoted_out.append(t)

        for t in self.global_transition_pool:
            if t.source in local_state_ids and t.target in local_state_ids:
                is_duplicate = any(x.from_state == self._get_state_id(d_states[t.source]) and 
                                   x.to_state == self._get_state_id(d_states[t.target]) for x in transitions)
                if not is_duplicate:
                    evt_id, _ = self._get_event_mapping(t.event_trigger)
                    transitions.append(dsl_node.TransitionDefinition(
                        from_state=self._get_state_id(d_states[t.source]),
                        to_state=self._get_state_id(d_states[t.target]),
                        event_id=dsl_node.ChainID([evt_id], is_absolute=True) if evt_id else None,
                        condition_expr=None, post_operations=[]))

        for t in region.transitions:
            if t.target not in local_state_ids:
                src = d_states.get(t.source)
                from_id = self._get_state_id(src) if src else '[*]'
                if from_id != '[*]':
                    evt_id, _ = self._get_event_mapping(t.event_trigger)
                    transitions.append(dsl_node.TransitionDefinition(
                        from_state=from_id, to_state='[*]',
                        event_id=dsl_node.ChainID([evt_id], is_absolute=True) if evt_id else None,
                        condition_expr=None, post_operations=[]))
                promoted_out.append(t)

        return states, transitions, promoted_out

def convert_state_machine_to_ast_node(state_machine: StateMachine, model: Model) -> List[dsl_node.StateDefinition]:
    return SysMLConverter(model).convert(state_machine)

def convert_model_to_ast(model: Model):
    nodes = convert_state_machine_to_ast_node(model.clazz.state_machine, model)
    return nodes[0] if nodes else None