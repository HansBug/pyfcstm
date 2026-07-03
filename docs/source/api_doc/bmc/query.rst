pyfcstm.bmc.query
========================================================

.. currentmodule:: pyfcstm.bmc.query

.. automodule:: pyfcstm.bmc.query


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


InitialSpec
-----------------------------------------------------

.. autoclass:: InitialSpec
    :members: __post_init__,to_canonical,__str__,mode,state_path,predicate


BmcAssumption
-----------------------------------------------------

.. autoclass:: BmcAssumption
    :members: to_canonical,__str__


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
    :members: __post_init__,to_canonical,__str__,kind,bound,predicate,trigger,response,within


BmcQuery
-----------------------------------------------------

.. autoclass:: BmcQuery
    :members: __post_init__,to_canonical,__str__,property,initial,assumptions
