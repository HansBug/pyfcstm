pyfcstm.verify.search
========================================================

.. currentmodule:: pyfcstm.verify.search

.. automodule:: pyfcstm.verify.search


FrameTypeTyping
-----------------------------------------------------

.. autodata:: FrameTypeTyping


SearchFrame
-----------------------------------------------------

.. autoclass:: SearchFrame
    :members: get_history,solve,state,type,var_state,constraints,event,depth,cycle,prev_frame


StateSearchSpace
-----------------------------------------------------

.. autoclass:: StateSearchSpace
    :members: state,frames


StateSearchContext
-----------------------------------------------------

.. autoclass:: StateSearchContext
    :members: get_z3_event,queue,spaces,z3_events


bfs\_search
-----------------------------------------------------

.. autofunction:: bfs_search

