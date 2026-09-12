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
    :members: __post_init__,to_dict,kind,state_path,vars,transition_label,action_path,resolved_action_path


CycleResult
-----------------------------------------------------

.. autoclass:: CycleResult
    :members: value,input_events,consumed_events,unconsumed_events,delta,trace


SimulationRuntimeExpressionError
-----------------------------------------------------

.. autoclass:: SimulationRuntimeExpressionError


SimulationRuntimeActionReferenceError
-----------------------------------------------------

.. autoclass:: SimulationRuntimeActionReferenceError


SimulationRuntime
-----------------------------------------------------

.. autoclass:: SimulationRuntime
    :members: __init__,cycle,current_state,brief_stack,is_ended,is_error_state,error_info,abstract_handler_errors,abstract_error_mode,copy_session_configuration_to,register_abstract_handler,unregister_abstract_handler,clear_abstract_handler_session,clear_all_abstract_handlers,get_abstract_handlers,has_abstract_handlers,register_handlers_from_object
