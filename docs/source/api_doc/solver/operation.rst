pyfcstm.solver.operation
========================================================

.. currentmodule:: pyfcstm.solver.operation

.. automodule:: pyfcstm.solver.operation


OperationSource
-----------------------------------------------------

.. autodata:: OperationSource


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


OperationFailure
-----------------------------------------------------

.. autoclass:: OperationFailure
    :members: kind,reason,source,translation_failure


OperationStep
-----------------------------------------------------

.. autoclass:: OperationStep
    :members: source,before,after,path_conditions,definedness_constraints


OperationBranch
-----------------------------------------------------

.. autoclass:: OperationBranch
    :members: __post_init__,branch_id,branch_kind,selector,path_conditions,status,result_env,definedness_constraints,failure


OperationExecution
-----------------------------------------------------

.. autoclass:: OperationExecution
    :members: env,visible_names,expr_constraints,definedness_constraints,steps,branches,failure


parse\_operations
-----------------------------------------------------

.. autofunction:: parse_operations


execute\_operations\_domain
-----------------------------------------------------

.. autofunction:: execute_operations_domain


merge\_operation\_definedness
-----------------------------------------------------

.. autofunction:: merge_operation_definedness


execute\_operations
-----------------------------------------------------

.. autofunction:: execute_operations
