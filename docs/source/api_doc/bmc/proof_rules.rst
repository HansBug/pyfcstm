pyfcstm.bmc.proof\_rules
========================================================

.. currentmodule:: pyfcstm.bmc.proof_rules

.. automodule:: pyfcstm.bmc.proof_rules


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


UNREACHABLE\_RULE\_IDS
-----------------------------------------------------

.. autodata:: UNREACHABLE_RULE_IDS


CLOSURE\_EXCLUDED\_RULE\_IDS
-----------------------------------------------------

.. autodata:: CLOSURE_EXCLUDED_RULE_IDS


PROOF\_RULES
-----------------------------------------------------

.. autodata:: PROOF_RULES
   :no-value:


RuleApplication
-----------------------------------------------------

.. autoclass:: RuleApplication
    :members: rule_id,premises,conclusion


ProofRule
-----------------------------------------------------

.. autoclass:: ProofRule
    :members: rule_id,premise_kinds,conclusion_kind,side_condition


reachable\_rule\_ids
-----------------------------------------------------

.. autofunction:: reachable_rule_ids


check\_rule
-----------------------------------------------------

.. autofunction:: check_rule
