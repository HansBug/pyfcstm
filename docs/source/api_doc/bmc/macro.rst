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


GuardRequirement
-----------------------------------------------------

.. autoclass:: GuardRequirement
    :members: __post_init__,atom_name,to_canonical,requirement_id,owner_state_id,owner_state_path,transition_label,expr,polarity,reason,after_action_block_index


PriorityExclusion
-----------------------------------------------------

.. autoclass:: PriorityExclusion
    :members: __post_init__,to_canonical,decision_id,reason,excluded_case_labels,excluded_condition,event_paths,guard_requirement_ids


ActionBlock
-----------------------------------------------------

.. autoclass:: ActionBlock
    :members: __post_init__,to_canonical,block_kind,runtime_role,owner_state_id,owner_state_path,operations,action_name,transition_label,is_abstract,active_leaf_path,execution_state_path,named_ref


CycleCase
-----------------------------------------------------

.. autoclass:: CycleCase
    :members: __post_init__,to_canonical,kind,source_state_id,source_state_path,target_state_id,target_state_path,label,condition,action_blocks,used_events,guard_requirements,priority_exclusions,failed_conditions,domain


PartitionCheckResult
-----------------------------------------------------

.. autoclass:: PartitionCheckResult
    :members: to_canonical,variables,assignment_count,bucket_count


MacroStepFormal
-----------------------------------------------------

.. autoclass:: MacroStepFormal
    :members: __post_init__,cases,verify_partition,to_canonical,source,success_cases,delta_cases,build_diagnostic_conditions


case\_path\_condition
-----------------------------------------------------

.. autofunction:: case_path_condition


terminated\_absorb\_case
-----------------------------------------------------

.. autofunction:: terminated_absorb_case


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
