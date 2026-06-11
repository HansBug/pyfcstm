pyfcstm.verify.topology
========================================================

.. currentmodule:: pyfcstm.verify.topology

.. automodule:: pyfcstm.verify.topology


EXIT\_ROOT\_SINK
-----------------------------------------------------

.. autodata:: EXIT_ROOT_SINK


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


LeafLevelGraph
-----------------------------------------------------

.. autoclass:: LeafLevelGraph
    :members: __post_init__,nodes,edges


FinitenessReport
-----------------------------------------------------

.. autoclass:: FinitenessReport
    :members: finite,counterexamples


InevitabilityReport
-----------------------------------------------------

.. autoclass:: InevitabilityReport
    :members: inevitable,counterexample_path


build\_leaf\_level\_macro\_graph
-----------------------------------------------------

.. autofunction:: build_leaf_level_macro_graph


topological\_reachable\_set
-----------------------------------------------------

.. autofunction:: topological_reachable_set


unreachable\_states
-----------------------------------------------------

.. autofunction:: unreachable_states


strongly\_connected\_components
-----------------------------------------------------

.. autofunction:: strongly_connected_components


topological\_finite
-----------------------------------------------------

.. autofunction:: topological_finite


topological\_inevitable\_terminator
-----------------------------------------------------

.. autofunction:: topological_inevitable_terminator


event\_emission\_to\_consumer\_reachable
-----------------------------------------------------

.. autofunction:: event_emission_to_consumer_reachable


