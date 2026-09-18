pyfcstm.solver.unsat
========================================================

.. currentmodule:: pyfcstm.solver.unsat

.. automodule:: pyfcstm.solver.unsat


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


UnsatConstraint
-----------------------------------------------------

.. autoclass:: UnsatConstraint
    :members: __post_init__,stable_id,expressions,source


UnsatQuery
-----------------------------------------------------

.. autoclass:: UnsatQuery
    :members: __post_init__,query_id,constraints,background


ProbeRecord
-----------------------------------------------------

.. autoclass:: ProbeRecord
    :members: name,status,started,elapsed_ms,reason


CoreExtraction
-----------------------------------------------------

.. autoclass:: CoreExtraction
    :members: groups,status,reason,checks,solver_status,core_check


MinimizedCore
-----------------------------------------------------

.. autoclass:: MinimizedCore
    :members: groups,reduction,subset_minimality,status,reason,record


UnsatExplanation
-----------------------------------------------------

.. autoclass:: UnsatExplanation
    :members: background_conflict,query,solver_status,core_ids,core_check,subset_minimality,reduction,stop_reason,checks,derivation_status,proof_status


explain\_unsat\_core
-----------------------------------------------------

.. autofunction:: explain_unsat_core
