pyfcstm.bmc.region\_expand
========================================================

.. currentmodule:: pyfcstm.bmc.region_expand

.. automodule:: pyfcstm.bmc.region_expand


ATOM\_REGION\_DONE
-----------------------------------------------------

.. autodata:: ATOM_REGION_DONE


ATOM\_REGION\_ENTER
-----------------------------------------------------

.. autodata:: ATOM_REGION_ENTER


REGION\_DONE\_CASE\_PATH
-----------------------------------------------------

.. autodata:: REGION_DONE_CASE_PATH


FLUSH\_CASE\_PATH
-----------------------------------------------------

.. autodata:: FLUSH_CASE_PATH


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


RegionCase
-----------------------------------------------------

.. autoclass:: RegionCase
    :members: kind,label,unit_id,target_kind,target_state_id,target_state_path,condition,action_blocks,used_events,guard_requirements,priority_exclusions,consumed_events,failed_conditions,before_done,owed,plain_pending_after


RegionUnitFormal
-----------------------------------------------------

.. autoclass:: RegionUnitFormal
    :members: unit_id,kind,cases,failed


expand\_leaf\_unit
-----------------------------------------------------

.. autofunction:: expand_leaf_unit


expand\_init\_unit
-----------------------------------------------------

.. autofunction:: expand_init_unit


expand\_continue\_unit
-----------------------------------------------------

.. autofunction:: expand_continue_unit


expand\_cold\_unit
-----------------------------------------------------

.. autofunction:: expand_cold_unit


expand\_flush\_unit
-----------------------------------------------------

.. autofunction:: expand_flush_unit
