pyfcstm.solver.context
========================================================

.. currentmodule:: pyfcstm.solver.context

.. automodule:: pyfcstm.solver.context


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


LINEAR\_PROBE
-----------------------------------------------------

.. autodata:: LINEAR_PROBE


SolveContextOwner
-----------------------------------------------------

.. autoclass:: SolveContextOwner
    :members: __init__,__slots__


Deferred
-----------------------------------------------------

.. autoclass:: Deferred
    :members: __slots__


IsolatedSolver
-----------------------------------------------------

.. autoclass:: IsolatedSolver
    :members: __init__,add,push,pop,set,check,model,unsat_core,reason_unknown,statistics,__slots__


current\_owner
-----------------------------------------------------

.. autofunction:: current_owner


solver\_context\_in\_use
-----------------------------------------------------

.. autofunction:: solver_context_in_use


isolated\_owner
-----------------------------------------------------

.. autofunction:: isolated_owner


is\_linear
-----------------------------------------------------

.. autofunction:: is_linear


declare
-----------------------------------------------------

.. autofunction:: declare


in\_solve\_context
-----------------------------------------------------

.. autofunction:: in_solve_context
