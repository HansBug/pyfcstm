pyfcstm.bmc.witness
========================================================

.. currentmodule:: pyfcstm.bmc.witness

.. automodule:: pyfcstm.bmc.witness


BmcSolveStatus
-----------------------------------------------------

.. autodata:: BmcSolveStatus


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


BmcSolveResult
-----------------------------------------------------

.. autoclass:: BmcSolveResult
    :members: __post_init__,kind,polarity,incomplete,witness_found,counterexample_found,property_satisfied,outcome,to_canonical,pretty_print,to_text,__str__,formula,status,model,reason,elapsed_ms,timeout_ms,incomplete_status,incomplete_model,incomplete_reason,diagnostics


BmcEventDecodePolicy
-----------------------------------------------------

.. autoclass:: BmcEventDecodePolicy
    :members: __post_init__,to_canonical,pretty_print,to_text,__str__,include_debug_reads,include_property_support


BmcWitnessEvent
-----------------------------------------------------

.. autoclass:: BmcWitnessEvent
    :members: __post_init__,to_canonical,pretty_print,to_text,__str__,path,reason,model_value


BmcWitnessCallRecord
-----------------------------------------------------

.. autoclass:: BmcWitnessCallRecord
    :members: __post_init__,to_canonical,pretty_print,to_text,__str__,ordinal,action_name,stage,role,state,active_leaf,named_ref,snapshot


BmcWitnessFrame
-----------------------------------------------------

.. autoclass:: BmcWitnessFrame
    :members: __post_init__,to_canonical,pretty_print,to_text,__str__,index,state_id,state,sentinel,terminated,vars


BmcWitnessStep
-----------------------------------------------------

.. autoclass:: BmcWitnessStep
    :members: __post_init__,input_event_paths,to_canonical,pretty_print,to_text,__str__,index,source_frame,target_frame,case_label,case_kind,progress,source_state,target_state,delta,gamma,input_events,event_reads,abstract_calls,consumed_events,unconsumed_events


BmcWitnessTrace
-----------------------------------------------------

.. autoclass:: BmcWitnessTrace
    :members: __post_init__,to_canonical,pretty_print,to_text,__str__,property,solver,initial,frames,steps,diagnostics,schema_version


BmcRuntimeFrame
-----------------------------------------------------

.. autoclass:: BmcRuntimeFrame
    :members: __post_init__,to_canonical,pretty_print,to_text,__str__,index,state,terminated,vars


BmcRuntimeStep
-----------------------------------------------------

.. autoclass:: BmcRuntimeStep
    :members: __post_init__,to_canonical,pretty_print,to_text,__str__,index,input_events,consumed_events,unconsumed_events,abstract_calls,delta,cycle_count_before,cycle_count_after,history_entry


BmcRuntimeTrace
-----------------------------------------------------

.. autoclass:: BmcRuntimeTrace
    :members: __post_init__,to_canonical,pretty_print,to_text,__str__,frames,steps


BmcReplayMismatch
-----------------------------------------------------

.. autoclass:: BmcReplayMismatch
    :members: __post_init__,to_canonical,pretty_print,to_text,__str__,path,expected,actual,message,tolerance


BmcReplayResult
-----------------------------------------------------

.. autoclass:: BmcReplayResult
    :members: __post_init__,ok,to_canonical,pretty_print,to_text,__str__,witness,runtime_trace,mismatches


solve\_bmc\_property
-----------------------------------------------------

.. autofunction:: solve_bmc_property


decode\_bmc\_witness
-----------------------------------------------------

.. autofunction:: decode_bmc_witness


replay\_bmc\_witness
-----------------------------------------------------

.. autofunction:: replay_bmc_witness
