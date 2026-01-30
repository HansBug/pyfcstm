import warnings
from typing import List

from .model import StateMachine, Model, State, Region, SignalEvent, TimeEvent
from ...dsl import node as dsl_node
from ...utils import to_identifier

def _get_state_id(state: State):
    # 修改点：将返回 None 改为返回 '[*]'
    # 这样在打印 DSL 时，它会显示为 [*] -> ... 而不是 None -> ...
    if state.type == 'uml:Pseudostate':
        return '[*]' 
    return to_identifier(state.name) if state.name else state.id

def convert_state_machine_to_ast_node(state_machine: StateMachine, model: Model) -> List[dsl_node.StateDefinition]:
    results = []
    for i, region in enumerate(state_machine.regions):
        substates, transitions = convert_region_to_ast_node(region, model)
        name_suffix = f"_{i}" if len(state_machine.regions) > 1 else ""
        extra_suffix = f" (Region {i})" if len(state_machine.regions) > 1 else ""
        
        results.append(dsl_node.StateDefinition(
            name=f'Root{name_suffix}',
            extra_name=f'<根状态>{extra_suffix}',
            events=_extract_events(model),
            substates=substates,
            transitions=transitions,
        ))
    return results

def _extract_events(model: Model):
    event_nodes = []
    for _, event in model.events.items():
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

def convert_state_to_ast_node(state: State, model: Model):
    if state.regions:
        substates, transitions = convert_region_to_ast_node(state.regions[0], model)
        return dsl_node.StateDefinition(
            name=_get_state_id(state),
            extra_name=state.name or None,
            substates=substates,
            transitions=transitions,
        )
    else:
        return dsl_node.StateDefinition(
            name=_get_state_id(state),
            extra_name=state.name or None,
        )

def convert_region_to_ast_node(region: Region, model: Model):
    states, transitions = [], []
    d_states = {}
    for state in region.states:
        if state.type != 'uml:Pseudostate':
            states.append(convert_state_to_ast_node(state, model))
        d_states[state.id] = state

    for transition in region.transitions:
        source_state = d_states.get(transition.source)
        target_state = d_states.get(transition.target)

        # 跨层级跳转处理
        to_id = _get_state_id(target_state) if target_state else '[*]' # 改为 [*]
        
        if target_state is None:
            warnings.warn(f'Transition {transition.id} target is outside current region. Splitting as per PDF p.6.')
            to_id = '[*]' 

        trigger_name = None
        if transition.event_trigger:
            trigger = model.events.get(transition.event_trigger)
            if isinstance(trigger, SignalEvent):
                if trigger.signal and trigger.signal_object.name:
                    trigger_name = to_identifier(trigger.signal_object.name)
            elif isinstance(trigger, TimeEvent):
                trigger_name = to_identifier(f"After {trigger.expression}")

        transitions.append(dsl_node.TransitionDefinition(
            from_state=_get_state_id(source_state) if source_state else '[*]', # 改为 [*]
            to_state=to_id,
            event_id=dsl_node.ChainID([trigger_name], is_absolute=True) if trigger_name else None,
            condition_expr=None,
            post_operations=[]
        ))
    return states, transitions

def convert_model_to_ast(model: Model):
    nodes = convert_state_machine_to_ast_node(
        state_machine=model.clazz.state_machine,
        model=model,
    )
    return nodes[0] if nodes else None