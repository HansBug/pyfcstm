pyfcstm.bmc.domain
========================================================

.. currentmodule:: pyfcstm.bmc.domain

.. automodule:: pyfcstm.bmc.domain


STATE\_TERMINATE\_ID
-----------------------------------------------------

.. autodata:: STATE_TERMINATE_ID


STATE\_DIAGNOSTIC\_ID
-----------------------------------------------------

.. autodata:: STATE_DIAGNOSTIC_ID


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


StateDomainEntry
-----------------------------------------------------

.. autoclass:: StateDomainEntry
    :members: __post_init__,to_canonical,id,path,name,kind,parent_path,is_root,is_stoppable,is_sentinel,is_generated_combo_pseudo


EventDomainEntry
-----------------------------------------------------

.. autoclass:: EventDomainEntry
    :members: __post_init__,to_canonical,id,path,name,owner_state_path,owner_state_id,owner_is_generated_combo_pseudo


VarDomainEntry
-----------------------------------------------------

.. autoclass:: VarDomainEntry
    :members: __post_init__,to_canonical,id,name,declared_type


FrameRef
-----------------------------------------------------

.. autoclass:: FrameRef
    :members: __post_init__,name,role,to_canonical,__str__,index,bound


StepRef
-----------------------------------------------------

.. autoclass:: StepRef
    :members: __post_init__,name,to_canonical,__str__,index,bound


EventInputRef
-----------------------------------------------------

.. autoclass:: EventInputRef
    :members: __post_init__,name,to_canonical,step_index,event_id,event_path


BmcDomain
-----------------------------------------------------

.. autoclass:: BmcDomain
    :members: __post_init__,frame0_state_ids,recurrence_state_ids,state_by_id,state_by_path,state_path_to_id,state_id_to_path,event_by_id,event_by_path,event_path_to_id,event_id_to_path,variable_by_id,variable_by_name,variable_name_to_id,variable_id_to_name,event_input,to_canonical,bound,states,events,variables,frames,steps,event_inputs,initial_state_ids,stable_state_ids


build\_bmc\_domain
-----------------------------------------------------

.. autofunction:: build_bmc_domain
