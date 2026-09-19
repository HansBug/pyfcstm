pyfcstm.bmc.construction
========================================================

.. currentmodule:: pyfcstm.bmc.construction

.. automodule:: pyfcstm.bmc.construction


BmcActionConstruction
-----------------------------------------------------

.. autoclass:: BmcActionConstruction
    :members: text_lines,index,block,before,after,execution,sources,source_paths


BmcConstructionUnit
-----------------------------------------------------

.. autoclass:: BmcConstructionUnit
    :members: parent_id,index,expression,source


BmcConstructionRefinement
-----------------------------------------------------

.. autoclass:: BmcConstructionRefinement
    :members: query,units,equivalence,explanation


BmcGuardConstruction
-----------------------------------------------------

.. autoclass:: BmcGuardConstruction
    :members: requirement,environment,expression,source,subexpressions,definedness


BmcCaseConstruction
-----------------------------------------------------

.. autoclass:: BmcCaseConstruction
    :members: query,step_index,case,expression,antecedent,before,actions,guards


BmcConstructionReport
-----------------------------------------------------

.. autoclass:: BmcConstructionReport
    :members: refine,check,core,group_ids,groups,cases


get\_bmc\_construction
-----------------------------------------------------

.. autofunction:: get_bmc_construction
