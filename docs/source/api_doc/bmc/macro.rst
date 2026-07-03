pyfcstm.bmc.macro
========================================================

.. currentmodule:: pyfcstm.bmc.macro

.. automodule:: pyfcstm.bmc.macro


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


BoolTemplate
-----------------------------------------------------

.. autoclass:: BoolTemplate
    :members: __post_init__,true,false,atom,not_,and_,or_,variables,evaluate,to_canonical,kind,name,operands


EventUse
-----------------------------------------------------

.. autoclass:: EventUse
    :members: __post_init__,to_canonical,event_id,path,polarity,reason


VarUpdate
-----------------------------------------------------

.. autoclass:: VarUpdate
    :members: __post_init__,to_canonical,variable_id,variable_name,expression,is_carry


CycleCase
-----------------------------------------------------

.. autoclass:: CycleCase
    :members: __post_init__,to_canonical,kind,source_state_id,source_state_path,target_state_id,target_state_path,label,condition,var_update,used_events,failed_conditions,domain,is_diagnostic


PartitionCheckResult
-----------------------------------------------------

.. autoclass:: PartitionCheckResult
    :members: to_canonical,variables,assignment_count,bucket_count


MacroStepFormal
-----------------------------------------------------

.. autoclass:: MacroStepFormal
    :members: __post_init__,cases,verify_partition,to_canonical,source,success_cases,delta_cases,build_diagnostic_conditions


carry\_var\_updates
-----------------------------------------------------

.. autofunction:: carry_var_updates


var\_update\_for
-----------------------------------------------------

.. autofunction:: var_update_for


build\_var\_updates
-----------------------------------------------------

.. autofunction:: build_var_updates


case\_antecedent\_condition
-----------------------------------------------------

.. autofunction:: case_antecedent_condition


terminated\_absorb\_case
-----------------------------------------------------

.. autofunction:: terminated_absorb_case


diagnostic\_absorb\_case
-----------------------------------------------------

.. autofunction:: diagnostic_absorb_case


build\_fallback\_case
-----------------------------------------------------

.. autofunction:: build_fallback_case


build\_semantic\_delta\_case
-----------------------------------------------------

.. autofunction:: build_semantic_delta_case


verify\_boolean\_partition
-----------------------------------------------------

.. autofunction:: verify_boolean_partition


verify\_source\_partition
-----------------------------------------------------

.. autofunction:: verify_source_partition
