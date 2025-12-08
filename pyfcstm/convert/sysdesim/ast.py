import warnings

from .model import StateMachine, Model, State, Region, SignalEvent
from ...dsl import node as dsl_node
from ...utils import to_identifier


def _get_state_id(state: State):
    return to_identifier(state.name) if state.name else state.id


def convert_state_machine_to_ast_node(state_machine: StateMachine, model: Model):
    substates, transitions = convert_region_to_ast_node(state_machine.regions[0], model)
    return dsl_node.StateDefinition(
        name='Root',
        substates=substates,
        transitions=transitions,
    )


def convert_state_to_ast_node(state: State, model: Model):
    if state.regions:
        substates, transitions = convert_region_to_ast_node(state.regions[0], model)
        return dsl_node.StateDefinition(
            name=_get_state_id(state),
            is_pseudo=state.is_pseudo,
            substates=substates,
            transitions=transitions,
        )
    else:
        return dsl_node.StateDefinition(
            name=_get_state_id(state),
            is_pseudo=state.is_pseudo,
        )


def convert_region_to_ast_node(region: Region, model: Model):
    states, transitions = [], []
    d_states = {}
    for state in region.states:
        states.append(convert_state_to_ast_node(state, model))
        d_states[state.id] = state
    for transition in region.transitions:
        skip = False
        if transition.source not in d_states:
            warnings.warn(f'Transition {transition!r} source not in the same layer, skipped.')
            skip = True
        if transition.target not in d_states:
            warnings.warn(f'Transition {transition!r} target not in the same layer, skipped.')
            skip = True
        if skip:
            continue
        if transition.event_trigger:
            trigger = model.events[transition.event_trigger]
            if isinstance(trigger, SignalEvent):
                if trigger.signal and trigger.signal_object.name:
                    trigger_name = to_identifier(trigger.signal_object.name)
                else:
                    trigger_name = None
            else:
                warnings.warn(f'Event {trigger!r} not supported, skipped.')
                trigger_name = None
        else:
            trigger_name = None

        transitions.append(dsl_node.TransitionDefinition(
            from_state=_get_state_id(d_states[transition.source]),
            to_state=_get_state_id(d_states[transition.target]),
            event_id=dsl_node.ChainID([trigger_name], is_absolute=True) if trigger_name else None,
            condition_expr=None,
            post_operations=[]
        ))
    return states, transitions


def convert_model_to_ast(model: Model):
    return convert_state_machine_to_ast_node(
        state_machine=model.clazz.state_machine,
        model=model,
    )
