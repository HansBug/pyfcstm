pyfcstm.bmc.query
========================================================

.. currentmodule:: pyfcstm.bmc.query

.. automodule:: pyfcstm.bmc.query


CanonicalDict
-----------------------------------------------------

.. autodata:: CanonicalDict


FrameSelector
-----------------------------------------------------

.. autodata:: FrameSelector


QuerySelector
-----------------------------------------------------

.. autodata:: QuerySelector


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


InitialSpec
-----------------------------------------------------

.. autoclass:: InitialSpec
    :members: __post_init__,to_canonical,mode,state_path,predicate


BmcAssumption
-----------------------------------------------------

.. autoclass:: BmcAssumption
    :members: to_canonical


FrameAssumption
-----------------------------------------------------

.. autoclass:: FrameAssumption
    :members: __post_init__,kind,predicate,frame


EventAssumption
-----------------------------------------------------

.. autoclass:: EventAssumption
    :members: __post_init__,event_path,selector,expected


EventCardinalityAssumption
-----------------------------------------------------

.. autoclass:: EventCardinalityAssumption
    :members: __post_init__,kind,event_paths


BmcProperty
-----------------------------------------------------

.. autoclass:: BmcProperty
    :members: __post_init__,to_canonical,kind,bound,predicate,trigger,response,within


BmcQuery
-----------------------------------------------------

.. autoclass:: BmcQuery
    :members: __post_init__,to_canonical,property,initial,assumptions
