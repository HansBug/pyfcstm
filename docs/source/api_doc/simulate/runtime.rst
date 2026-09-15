pyfcstm.simulate.runtime
========================================================

.. currentmodule:: pyfcstm.simulate.runtime

.. automodule:: pyfcstm.simulate.runtime


SimulationRuntimeDfsError
-----------------------------------------------------

.. autoclass:: SimulationRuntimeDfsError


SimulationRuntimeTerminalStateError
-----------------------------------------------------

.. autoclass:: SimulationRuntimeTerminalStateError


SimulationRuntimeEventError
-----------------------------------------------------

.. autoclass:: SimulationRuntimeEventError


ExecutionTraceEntry
-----------------------------------------------------

.. autoclass:: ExecutionTraceEntry
    :members: __post_init__,__str__,to_dict,kind,state_path,vars,transition_label,action_path,resolved_action_path,inputs,parameters


CycleResult
-----------------------------------------------------

.. autoclass:: CycleResult
    :members: __post_init__,value,input_events,consumed_events,unconsumed_events,delta,trace,inputs


SimulationRuntimeExpressionError
-----------------------------------------------------

.. autoclass:: SimulationRuntimeExpressionError


SimulationRuntimeActionReferenceError
-----------------------------------------------------

.. autoclass:: SimulationRuntimeActionReferenceError


SimulationRuntime
-----------------------------------------------------

.. autoclass:: SimulationRuntime
    :members: __init__,cycle,parameters,last_inputs,control_variables,outputs,input_source_error,current_state,brief_stack,is_ended,is_error_state,error_info,abstract_handler_errors,abstract_error_mode,copy_session_configuration_to,register_abstract_handler,unregister_abstract_handler,clear_abstract_handler_session,clear_all_abstract_handlers,get_abstract_handlers,has_abstract_handlers,register_handlers_from_object,history_size
