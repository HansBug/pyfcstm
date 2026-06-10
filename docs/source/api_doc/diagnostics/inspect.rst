pyfcstm.diagnostics.inspect
========================================================

.. currentmodule:: pyfcstm.diagnostics.inspect

.. automodule:: pyfcstm.diagnostics.inspect


DEFAULT\_DEEP\_HIERARCHY\_THRESHOLD
-----------------------------------------------------

.. autodata:: DEFAULT_DEEP_HIERARCHY_THRESHOLD


DEFAULT\_LARGE\_COMPOSITE\_THRESHOLD
-----------------------------------------------------

.. autodata:: DEFAULT_LARGE_COMPOSITE_THRESHOLD


DEFAULT\_VAR\_TO\_LEAF\_RATIO\_THRESHOLD
-----------------------------------------------------

.. autodata:: DEFAULT_VAR_TO_LEAF_RATIO_THRESHOLD


KNOWN\_SPANLESS\_CODES
-----------------------------------------------------

.. autodata:: KNOWN_SPANLESS_CODES


StateInfo
-----------------------------------------------------

.. autoclass:: StateInfo
    :members: path,name,parent_path,is_leaf,is_pseudo,is_composite,substates,initial_targets,entry_actions,during_actions,exit_actions,aspect_before,aspect_after,has_abstract_action,span


TransitionInfo
-----------------------------------------------------

.. autoclass:: TransitionInfo
    :members: from_path,to_path,event,event_scope,guard,effect,effect_self_assigns,is_forced,forced_origin,transition_index,span,effect_spans,effect_self_assign_spans


VariableInfo
-----------------------------------------------------

.. autoclass:: VariableInfo
    :members: name,type,init_value,read_in_states,written_in_states,read_in_guards,written_in_effects,affects_guard_directly,affects_guard_indirectly,abstract_actions_in_scope,float_literal_assignments,span,float_literal_assignment_spans


EventInfo
-----------------------------------------------------

.. autoclass:: EventInfo
    :members: qualified_name,scope,used_by,is_declared,is_used,span


ActionInfo
-----------------------------------------------------

.. autoclass:: ActionInfo
    :members: signature,state_path,name,stage,aspect,is_ref,ref_target,is_attached,span


ForcedTransitionInfo
-----------------------------------------------------

.. autoclass:: ForcedTransitionInfo
    :members: state_path,from_path,to_path,event,event_scope,guard,original_raw,expansion_count,span


ModelMetrics
-----------------------------------------------------

.. autoclass:: ModelMetrics
    :members: n_states_leaf,n_states_composite,n_states_pseudo,max_hierarchy_depth,n_transitions_normal,n_transitions_forced,n_events,n_variables,var_to_leaf_ratio,aspect_coverage,abstract_action_inventory


ModelInspect
-----------------------------------------------------

.. autoclass:: ModelInspect
    :members: to_json,root_state_path,states,transitions,variables,events,actions,forced_transitions,metrics,reachability_graph,event_emission_map,var_dataflow,aspect_impact_map,action_ref_graph,diagnostics


inspect\_model
-----------------------------------------------------

.. autofunction:: inspect_model
