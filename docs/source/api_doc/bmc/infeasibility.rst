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
    :members: name,status,started,elapsed_ms


ClassificationOutcome
-----------------------------------------------------

.. autoclass:: ClassificationOutcome
    :members: classification,scope,status,reason,checks


CoreExtraction
-----------------------------------------------------

.. autoclass:: CoreExtraction
    :members: groups,status,reason,checks


partition\_tracked\_groups
-----------------------------------------------------

.. autofunction:: partition_tracked_groups


classify\_infeasibility
-----------------------------------------------------

.. autofunction:: classify_infeasibility


extract\_source\_core
-----------------------------------------------------

.. autofunction:: extract_source_core
