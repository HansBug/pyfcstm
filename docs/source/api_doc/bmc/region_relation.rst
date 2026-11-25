pyfcstm.bmc.region\_relation
========================================================

.. currentmodule:: pyfcstm.bmc.region_relation

.. automodule:: pyfcstm.bmc.region_relation


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


RegionCaseRelation
-----------------------------------------------------

.. autoclass:: RegionCaseRelation
    :members: step_index,case,selector,antecedent,consequent,implication,order,children,call_records,flushes


RegionFlushRelation
-----------------------------------------------------

.. autoclass:: RegionFlushRelation
    :members: step_index,order,scope,prefix,condition,call_records


RegionOccurrence
-----------------------------------------------------

.. autoclass:: RegionOccurrence
    :members: call_records,order,condition,case,flush,positions


PositionSnapshot
-----------------------------------------------------

.. autoclass:: PositionSnapshot
    :members: main,regions


RegionStepRelation
-----------------------------------------------------

.. autoclass:: RegionStepRelation
    :members: step_index,cases,constraints,flushes,rolled_back,start,owned,state_ids


region\_occurrences
-----------------------------------------------------

.. autofunction:: region_occurrences


reported\_call\_state
-----------------------------------------------------

.. autofunction:: reported_call_state


start\_position\_ids
-----------------------------------------------------

.. autofunction:: start_position_ids


region\_frame\_constraints
-----------------------------------------------------

.. autofunction:: region_frame_constraints


region\_error\_analysis
-----------------------------------------------------

.. autofunction:: region_error_analysis


build\_region\_core\_formula
-----------------------------------------------------

.. autofunction:: build_region_core_formula
