pyfcstm.bmc.infeasibility
========================================================

.. currentmodule:: pyfcstm.bmc.infeasibility

.. automodule:: pyfcstm.bmc.infeasibility


AGGREGATE\_SELECTORS
-----------------------------------------------------

.. autodata:: AGGREGATE_SELECTORS


SCOPE\_TARGETS
-----------------------------------------------------

.. autodata:: SCOPE_TARGETS


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


TrackedGroupPartition
-----------------------------------------------------

.. autoclass:: TrackedGroupPartition
    :members: groups_for,domain,initial,transition,environment


ProbeRecord
-----------------------------------------------------

.. autoclass:: ProbeRecord
    :members: name,status,started,elapsed_ms,reason


ClassificationOutcome
-----------------------------------------------------

.. autoclass:: ClassificationOutcome
    :members: classification,scope,status,reason,checks


CoreExtraction
-----------------------------------------------------

.. autoclass:: CoreExtraction
    :members: groups,status,reason,checks


ExplanationOutcome
-----------------------------------------------------

.. autoclass:: ExplanationOutcome
    :members: explanation,checks


MinimizedCore
-----------------------------------------------------

.. autoclass:: MinimizedCore
    :members: groups,reduction,subset_minimality,status,reason,record


ForcedValue
-----------------------------------------------------

.. autoclass:: ForcedValue
    :members: variable,frame,value,supporting_ids


partition\_tracked\_groups
-----------------------------------------------------

.. autofunction:: partition_tracked_groups


classify\_infeasibility
-----------------------------------------------------

.. autofunction:: classify_infeasibility


extract\_source\_core
-----------------------------------------------------

.. autofunction:: extract_source_core


minimize\_source\_core
-----------------------------------------------------

.. autofunction:: minimize_source_core


derive\_forced\_values
-----------------------------------------------------

.. autofunction:: derive_forced_values


build\_core\_item
-----------------------------------------------------

.. autofunction:: build_core_item


check\_core\_bindings
-----------------------------------------------------

.. autofunction:: check_core_bindings


check\_case\_conditions
-----------------------------------------------------

.. autofunction:: check_case_conditions


check\_value\_carries
-----------------------------------------------------

.. autofunction:: check_value_carries


encodable\_fact\_kinds
-----------------------------------------------------

.. autofunction:: encodable_fact_kinds


explain\_infeasibility
-----------------------------------------------------

.. autofunction:: explain_infeasibility
