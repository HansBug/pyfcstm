pyfcstm.solver.construction
========================================================

.. currentmodule:: pyfcstm.solver.construction

.. automodule:: pyfcstm.solver.construction


ConstructionCheck
-----------------------------------------------------

.. autoclass:: ConstructionCheck
    :members: status,reason,path


ConstructionValue
-----------------------------------------------------

.. autoclass:: ConstructionValue
    :members: identifier,name,kind,expression,source,path,reads,alternatives,path_conditions,definedness,subexpressions


ConstructionBranch
-----------------------------------------------------

.. autoclass:: ConstructionBranch
    :members: path,source,kind,selector,status,reads,path_conditions,result_versions,subexpressions


OperationConstruction
-----------------------------------------------------

.. autoclass:: OperationConstruction
    :members: __post_init__,check,statements,values,branches,initial_versions,final_versions,assumptions,prune_unreachable,path_conditions
