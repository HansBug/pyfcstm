pyfcstm.convert.sysdesim.ir
========================================================

.. currentmodule:: pyfcstm.convert.sysdesim.ir

.. automodule:: pyfcstm.convert.sysdesim.ir


IrDiagnostic
-----------------------------------------------------

.. autoclass:: IrDiagnostic
    :members: level,code,message,source_id,state_path


IrActionRef
-----------------------------------------------------

.. autoclass:: IrActionRef
    :members: action_id,raw_name,safe_name,display_name


IrVariable
-----------------------------------------------------

.. autoclass:: IrVariable
    :members: variable_id,raw_name,safe_name,display_name,type_name,default_value,is_synthetic


IrSignal
-----------------------------------------------------

.. autoclass:: IrSignal
    :members: signal_id,raw_name,safe_name,display_name


IrSignalEvent
-----------------------------------------------------

.. autoclass:: IrSignalEvent
    :members: event_id,signal_id,raw_name,safe_name,display_name


IrTimeEvent
-----------------------------------------------------

.. autoclass:: IrTimeEvent
    :members: time_event_id,raw_literal,is_relative,normalized_delay,normalized_unit


IrTransition
-----------------------------------------------------

.. autoclass:: IrTransition
    :members: transition_id,source_id,target_id,trigger_kind,trigger_ref_id,guard_expr_raw,guard_expr_ir,effect_action,source_region_id,target_region_id,is_cross_level,is_cross_region,origin_kind


IrRegion
-----------------------------------------------------

.. autoclass:: IrRegion
    :members: region_id,owner_state_id,vertices,transitions


IrVertex
-----------------------------------------------------

.. autoclass:: IrVertex
    :members: vertex_id,vertex_type,raw_name,safe_name,display_name,parent_region_id,entry_action,exit_action,state_invariant,regions,is_composite,is_parallel_owner


IrMachine
-----------------------------------------------------

.. autoclass:: IrMachine
    :members: __post_init__,walk_regions,walk_vertices,walk_transitions,rebuild_indexes,get_vertex,get_transition,get_region,get_signal,get_signal_event,get_time_event,get_variable,state_id_path,state_path,descendant_state_ids,region_count,lca_state_id,to_dict,machine_id,name,root_region,signals,signal_events,time_events,variables,diagnostics,safe_name,display_name


