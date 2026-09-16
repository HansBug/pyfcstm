pyfcstm.simulate.diagnostics
========================================================

.. currentmodule:: pyfcstm.simulate.diagnostics

.. automodule:: pyfcstm.simulate.diagnostics


Number
-----------------------------------------------------

.. autodata:: Number


TransitionDecision
-----------------------------------------------------

.. autoclass:: TransitionDecision
    :members: __post_init__,to_dict,id,parent_id,transition_label,phase,state_path,event,guard,vars,inputs,parameters,location,event_result,guard_result,successor_result,outcome,blocked_by,committed,combo_origins


CycleDiagnostics
-----------------------------------------------------

.. autoclass:: CycleDiagnostics
    :members: __post_init__,to_dict,__str__,to_text,cycle_count,outcome,state_before,state_after,decisions,roles,input_events,inputs,parameters,vars_before,vars_after
