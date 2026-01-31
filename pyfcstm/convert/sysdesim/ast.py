import warnings
from typing import List, Tuple, Optional

from .model import StateMachine, Model, State, Region, SignalEvent, TimeEvent, Transition
from ...dsl import node as dsl_node
from ...utils import to_identifier

class SysMLConverter:
    """
    SysML 到 pyfcstm AST 转换器
    通过类封装实现了递归 Region 拆分和 Transition 冒泡提升，消除了全局变量。
    """
    def __init__(self, model: Model):
        self.model = model
        self.extra_roots: List[dsl_node.StateDefinition] = []

    def _get_state_id(self, state: State) -> str:
        if state.type == 'uml:Pseudostate':
            return '[*]'
        name_or_id = state.name if state.name else state.id
        return to_identifier(name_or_id)

    def _get_event_name(self, event_id: str) -> Optional[str]:
        if not event_id: return None
        event = self.model.events.get(event_id)
        if isinstance(event, SignalEvent):
            return to_identifier(event.signal_object.name) if event.signal_object.name else None
        elif isinstance(event, TimeEvent):
            return to_identifier(f"After {event.expression}")
        return None

    def _extract_all_events(self) -> List[dsl_node.EventDefinition]:
        event_nodes = []
        for _, event in self.model.events.items():
            if isinstance(event, SignalEvent):
                event_nodes.append(dsl_node.EventDefinition(
                    name=to_identifier(event.signal_object.name),
                    extra_name=event.signal_object.name or None,
                ))
            elif isinstance(event, TimeEvent):
                trigger_name = f"After {event.expression}"
                event_nodes.append(dsl_node.EventDefinition(
                    name=to_identifier(trigger_name),
                    extra_name=trigger_name,
                ))
        return event_nodes

    def convert(self, state_machine: StateMachine) -> List[dsl_node.StateDefinition]:
        self.extra_roots = []
        # 处理主 Region
        main_substates, main_transitions, _ = self._convert_region(state_machine.regions[0])
        
        main_root = dsl_node.StateDefinition(
            name='Root',
            extra_name='<根状态>',
            events=self._extract_all_events(),
            substates=main_substates,
            transitions=main_transitions,
        )

        # 处理顶层并发
        for i in range(1, len(state_machine.regions)):
            self._push_extra_region(state_machine.regions[i], f"Root_Region_{i}", f"<根状态-并发区域{i}>")

        return [main_root] + self.extra_roots

    def _push_extra_region(self, region: Region, root_name: str, extra_name: str):
        substates, transitions, _ = self._convert_region(region)
        self.extra_roots.append(dsl_node.StateDefinition(
            name=root_name,
            extra_name=extra_name,
            events=self._extract_all_events(),
            substates=substates,
            transitions=transitions,
        ))

    def _convert_state(self, state: State) -> Tuple[dsl_node.StateDefinition, List[Transition]]:
        promoted = []
        if state.regions:
            # 递归处理 Region 0
            sub_s, sub_t, sub_p = self._convert_region(state.regions[0])
            promoted.extend(sub_p)
            
            # 拆分其他 Region
            for i in range(1, len(state.regions)):
                name = f"{self._get_state_id(state)}_Region_{i}"
                extra = f"{state.name or state.id} (Region {i})"
                self._push_extra_region(state.regions[i], name, extra)

            node = dsl_node.StateDefinition(
                name=self._get_state_id(state),
                extra_name=state.name or None,
                substates=sub_s,
                transitions=sub_t,
            )
        else:
            node = dsl_node.StateDefinition(
                name=self._get_state_id(state),
                extra_name=state.name or None,
            )
        return node, promoted

    def _convert_region(self, region: Region) -> Tuple[list, list, list]:
        states, transitions, promoted_out = [], [], []
        d_states = {s.id: s for s in region.states}

        for state in region.states:
            if state.type != 'uml:Pseudostate':
                node, child_promoted = self._convert_state(state)
                states.append(node)
                # 处理冒泡
                for t in child_promoted:
                    if t.target in d_states:
                        evt = self._get_event_name(t.event_trigger)
                        transitions.append(dsl_node.TransitionDefinition(
                            from_state=self._get_state_id(state),
                            to_state=self._get_state_id(d_states[t.target]),
                            event_id=dsl_node.ChainID([evt], is_absolute=True) if evt else None,
                            condition_expr=None, post_operations=[]
                        ))
                    else:
                        promoted_out.append(t)

        for transition in region.transitions:
            source = d_states.get(transition.source)
            target = d_states.get(transition.target)
            from_id = self._get_state_id(source) if source else '[*]'
            evt = self._get_event_name(transition.event_trigger)

            if target:
                transitions.append(dsl_node.TransitionDefinition(
                    from_state=from_id, to_state=self._get_state_id(target),
                    event_id=dsl_node.ChainID([evt], is_absolute=True) if evt else None,
                    condition_expr=None, post_operations=[]
                ))
            else:
                if from_id != '[*]':
                    transitions.append(dsl_node.TransitionDefinition(
                        from_state=from_id, to_state='[*]',
                        event_id=dsl_node.ChainID([evt], is_absolute=True) if evt else None,
                        condition_expr=None, post_operations=[]
                    ))
                promoted_out.append(transition)

        return states, transitions, promoted_out

def convert_state_machine_to_ast_node(state_machine: StateMachine, model: Model) -> List[dsl_node.StateDefinition]:
    # 保持原有接口不变，内部使用 Converter 类
    converter = SysMLConverter(model)
    return converter.convert(state_machine)

def convert_model_to_ast(model: Model):
    nodes = convert_state_machine_to_ast_node(model.clazz.state_machine, model)
    return nodes[0] if nodes else None