pyfcstm.semantics.symbolic
========================================================

.. currentmodule:: pyfcstm.semantics.symbolic

.. automodule:: pyfcstm.semantics.symbolic


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


Checker
-----------------------------------------------------

.. autodata:: Checker


SYMBOLIC
-----------------------------------------------------

.. autodata:: SYMBOLIC


SymbolicFailure
-----------------------------------------------------

.. autoclass:: SymbolicFailure
    :members: __init__


DefinednessFact
-----------------------------------------------------

.. autoclass:: DefinednessFact
    :members: constraint,condition,guards,kind,node


FeasibilityCheck
-----------------------------------------------------

.. autoclass:: FeasibilityCheck
    :members: selector,status


ConditionObservation
-----------------------------------------------------

.. autoclass:: ConditionObservation
    :members: node,condition,path,definedness


SymbolicSession
-----------------------------------------------------

.. autoclass:: SymbolicSession
    :members: facts,assumptions,path_conditions,checker,timeout_ms,observe_conditions,track_definedness,definedness,checks,conditions


SymbolicContext
-----------------------------------------------------

.. autoclass:: SymbolicContext
    :members: session,guards,path


SymbolicInterpretation
-----------------------------------------------------

.. autoclass:: SymbolicInterpretation
    :members: literal,symbol,apply,unknown_operation,host_atom,truth,negate,decide,enter,constant,no_branch


translate
-----------------------------------------------------

.. autofunction:: translate
