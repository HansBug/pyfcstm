pyfcstm.solver.proof.core
========================================================

.. currentmodule:: pyfcstm.solver.proof.core

.. automodule:: pyfcstm.solver.proof.core


SourceDescription
-----------------------------------------------------

.. autoclass:: SourceDescription
    :members: __post_init__,source_id,title,document_id,span,excerpt


SourceLink
-----------------------------------------------------

.. autoclass:: SourceLink
    :members: source_id,relation,occurrence_id,term_id


SourceBinding
-----------------------------------------------------

.. autoclass:: SourceBinding
    :members: __post_init__,expression,source,relation


ProofSource
-----------------------------------------------------

.. autoclass:: ProofSource
    :members: term_id,description,relation


SourceAdapter
-----------------------------------------------------

.. autoclass:: SourceAdapter
    :members: describe,bindings


ProofExtensions
-----------------------------------------------------

.. autoclass:: ProofExtensions
    :members: __post_init__,rule_handlers,source_adapter,reading_folders


ProofParameter
-----------------------------------------------------

.. autoclass:: ProofParameter
    :members: kind,value


ProofTerm
-----------------------------------------------------

.. autoclass:: ProofTerm
    :members: term_id,kind,sort,operator,arguments,value,bindings,operator_kind,parameters


ProofInput
-----------------------------------------------------

.. autoclass:: ProofInput
    :members: occurrence_id,constraint_id,expression_index,term_id,background


ProofNode
-----------------------------------------------------

.. autoclass:: ProofNode
    :members: node_id,rule,parents,conclusion,operands,parameters,input_occurrences,open_hypotheses,discharged_hypotheses,local_check,bindings,inference_kind,certificate,cardinality,interval,divisibility,polynomial,linear_equality


TermEquality
-----------------------------------------------------

.. autoclass:: TermEquality
    :members: left_id,right_id,bound_indices


IntervalStep
-----------------------------------------------------

.. autoclass:: IntervalStep
    :members: term_id,lower,upper,lower_open,upper_open,rule,premises,bound_index,substitutions


IntervalCertificate
-----------------------------------------------------

.. autoclass:: IntervalCertificate
    :members: bounds,steps,conflict,equality


CountContribution
-----------------------------------------------------

.. autoclass:: CountContribution
    :members: term_id,weight,minimum,maximum


CardinalityCertificate
-----------------------------------------------------

.. autoclass:: CardinalityCertificate
    :members: minimum,maximum,assumptions,constraint_id,constraint_value,assignments,contributions


LinearBound
-----------------------------------------------------

.. autoclass:: LinearBound
    :members: term_id,negated,coefficients,constant,relation


ArithmeticCertificate
-----------------------------------------------------

.. autoclass:: ArithmeticCertificate
    :members: bounds,weights,constant,strict


DivisibilityCertificate
-----------------------------------------------------

.. autoclass:: DivisibilityCertificate
    :members: bound_pairs,weights,coefficients,lower,upper


LinearEqualityCertificate
-----------------------------------------------------

.. autoclass:: LinearEqualityCertificate
    :members: term_id,less,greater


PolynomialStep
-----------------------------------------------------

.. autoclass:: PolynomialStep
    :members: coefficients,strict,rule,premises,weights,term_id,negated,multiplier,factor


PolynomialCertificate
-----------------------------------------------------

.. autoclass:: PolynomialCertificate
    :members: steps


ProofGap
-----------------------------------------------------

.. autoclass:: ProofGap
    :members: reason,node_id,detail


ProofGraph
-----------------------------------------------------

.. autoclass:: ProofGraph
    :members: __post_init__,node,term,execution_id,root_id,nodes,terms,inputs,source_bindings


UnsatReport
-----------------------------------------------------

.. autoclass:: UnsatReport
    :members: to_canonical,from_canonical,query_id,solver_status,proof_status,proof,input_check,stop_reason,scope_check,rule_check,gaps,reading,reading_status,source_status,proof_scope,full_proof,core


CoreEvidence
-----------------------------------------------------

.. autoclass:: CoreEvidence
    :members: from_result,constraint_ids,background_ids,core_ids,core_check,subset_minimality,reduction,stop_reason


explain\_unsat
-----------------------------------------------------

.. autofunction:: explain_unsat
