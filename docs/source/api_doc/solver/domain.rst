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
    :members: label,step,snapshot,prefix_id


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


ExprDomain
-----------------------------------------------------

.. autoclass:: ExprDomain
    :members: z3_expr,expr_constraints,assumptions,definedness_constraints,failure,feasibility_checks


translate\_expr\_domain
-----------------------------------------------------

.. autofunction:: translate_expr_domain


merge\_definedness\_constraints
-----------------------------------------------------

.. autofunction:: merge_definedness_constraints
