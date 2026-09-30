pyfcstm.solver.proof.rules
========================================================

.. currentmodule:: pyfcstm.solver.proof.rules

.. automodule:: pyfcstm.solver.proof.rules


RuleAnalysis
-----------------------------------------------------

.. autoclass:: RuleAnalysis
    :members: __post_init__,kind,local_check


ProofRuleHandler
-----------------------------------------------------

.. autoclass:: ProofRuleHandler
    :members: __post_init__,rule,interpret


ProofAnalysis
-----------------------------------------------------

.. autoclass:: ProofAnalysis
    :members: graph,scope_check,rule_check,gaps,stop_reason


check\_arithmetic\_certificate
-----------------------------------------------------

.. autofunction:: check_arithmetic_certificate


check\_linear\_equality\_certificate
-----------------------------------------------------

.. autofunction:: check_linear_equality_certificate


check\_cardinality\_certificate
-----------------------------------------------------

.. autofunction:: check_cardinality_certificate


analyze\_proof
-----------------------------------------------------

.. autofunction:: analyze_proof
