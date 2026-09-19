pyfcstm.solver.domain
========================================================

.. currentmodule:: pyfcstm.solver.domain

.. automodule:: pyfcstm.solver.domain


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


DomainSource
-----------------------------------------------------

.. autoclass:: DomainSource
    :members: label,step,snapshot,prefix_id,operation


DomainConstraint
-----------------------------------------------------

.. autoclass:: DomainConstraint
    :members: constraint,source


TranslationFailure
-----------------------------------------------------

.. autoclass:: TranslationFailure
    :members: kind,reason,source


BranchFeasibility
-----------------------------------------------------

.. autoclass:: BranchFeasibility
    :members: selector,status,source


ExpressionConstruction
-----------------------------------------------------

.. autoclass:: ExpressionConstruction
    :members: source,path,expression,path_conditions,definedness_constraints,failure


ExprDomain
-----------------------------------------------------

.. autoclass:: ExprDomain
    :members: z3_expr,expr_constraints,assumptions,definedness_constraints,failure,feasibility_checks,construction


translate\_expr\_domain
-----------------------------------------------------

.. autofunction:: translate_expr_domain


merge\_definedness\_constraints
-----------------------------------------------------

.. autofunction:: merge_definedness_constraints
