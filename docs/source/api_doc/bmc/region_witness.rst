pyfcstm.bmc.region\_witness
========================================================

.. currentmodule:: pyfcstm.bmc.region_witness

.. automodule:: pyfcstm.bmc.region_witness


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


RegionCall
-----------------------------------------------------

.. autoclass:: RegionCall
    :members: action_name,stage,role,state,active_leaf,named_ref,snapshot,configuration


RegionStepSummary
-----------------------------------------------------

.. autoclass:: RegionStepSummary
    :members: case,kind,step_index,trace,local_cases,used_events,consumed_events,guard_requirements,action_blocks,antecedent


RegionStepTrace
-----------------------------------------------------

.. autoclass:: RegionStepTrace
    :members: paths,calls


trace\_region\_step
-----------------------------------------------------

.. autofunction:: trace_region_step


summarize\_region\_step
-----------------------------------------------------

.. autofunction:: summarize_region_step


frame\_configuration
-----------------------------------------------------

.. autofunction:: frame_configuration
