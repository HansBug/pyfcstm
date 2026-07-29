pyfcstm.bmc.explanation
========================================================

.. currentmodule:: pyfcstm.bmc.explanation

.. automodule:: pyfcstm.bmc.explanation


BmcInfeasibilityExplanationMode
-----------------------------------------------------

.. autodata:: BmcInfeasibilityExplanationMode


BmcInfeasibilityExplanationStatus
-----------------------------------------------------

.. autodata:: BmcInfeasibilityExplanationStatus


BmcInfeasibilityClassification
-----------------------------------------------------

.. autodata:: BmcInfeasibilityClassification


BmcConflictCoreScope
-----------------------------------------------------

.. autodata:: BmcConflictCoreScope


BmcConstraintStage
-----------------------------------------------------

.. autodata:: BmcConstraintStage


BmcCoreGranularity
-----------------------------------------------------

.. autodata:: BmcCoreGranularity


BmcCoreReduction
-----------------------------------------------------

.. autodata:: BmcCoreReduction


BmcSubsetMinimality
-----------------------------------------------------

.. autodata:: BmcSubsetMinimality


BmcDerivationStatus
-----------------------------------------------------

.. autodata:: BmcDerivationStatus


BmcReasoningStepKind
-----------------------------------------------------

.. autodata:: BmcReasoningStepKind


BmcSemanticRole
-----------------------------------------------------

.. autodata:: BmcSemanticRole


CLASSIFICATION\_SCOPES
-----------------------------------------------------

.. autodata:: CLASSIFICATION_SCOPES


CATEGORY\_ROLES
-----------------------------------------------------

.. autodata:: CATEGORY_ROLES


SCOPE\_AGGREGATES
-----------------------------------------------------

.. autodata:: SCOPE_AGGREGATES


MAX\_SOURCE\_EXCERPT\_CHARS
-----------------------------------------------------

.. autodata:: MAX_SOURCE_EXCERPT_CHARS


UNBUILT\_SLOTS
-----------------------------------------------------

.. autodata:: UNBUILT_SLOTS


STAGE\_FALLBACK\_SCOPES
-----------------------------------------------------

.. autodata:: STAGE_FALLBACK_SCOPES


INDEX\_REF\_KEYS
-----------------------------------------------------

.. autodata:: INDEX_REF_KEYS


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


EXPLANATION\_HEADLINES
-----------------------------------------------------

.. autodata:: EXPLANATION_HEADLINES


CLASSIFICATION\_PHRASES
-----------------------------------------------------

.. autodata:: CLASSIFICATION_PHRASES


BmcConstraintRef
-----------------------------------------------------

.. autoclass:: BmcConstraintRef
    :members: __post_init__,to_canonical,stable_id,stage,category,source,summary,frames,steps,refs


BmcCoreItem
-----------------------------------------------------

.. autoclass:: BmcCoreItem
    :members: __post_init__,to_canonical,constraint,semantic_role,source_excerpt,source_excerpt_truncated,normalized_fact,human_text,editable


BmcConflictCore
-----------------------------------------------------

.. autoclass:: BmcConflictCore
    :members: __post_init__,to_canonical,scope,formula_summary,granularity,reduction,subset_minimality,items


BmcReasoningStep
-----------------------------------------------------

.. autoclass:: BmcReasoningStep
    :members: __post_init__,to_canonical,kind,item_ids,proof_node_ids,text


BmcConflictNarrative
-----------------------------------------------------

.. autoclass:: BmcConflictNarrative
    :members: __post_init__,to_canonical,derivation_status,headline,summary,reasoning_steps,review_surfaces


BmcConflictProof
-----------------------------------------------------

.. autoclass:: BmcConflictProof
    :members: scope,root_id


BmcInfeasibilityExplanation
-----------------------------------------------------

.. autoclass:: BmcInfeasibilityExplanation
    :members: __post_init__,to_canonical,requested_mode,achieved_mode,status,classification,core,proof,narrative,reason,elapsed_ms


is\_printable\_ascii
-----------------------------------------------------

.. autofunction:: is_printable_ascii


human\_text\_for\_fact
-----------------------------------------------------

.. autofunction:: human_text_for_fact


category\_role
-----------------------------------------------------

.. autofunction:: category_role


constraint\_aggregate
-----------------------------------------------------

.. autofunction:: constraint_aggregate


index\_value
-----------------------------------------------------

.. autofunction:: index_value


depth\_line\_is\_needed
-----------------------------------------------------

.. autofunction:: depth_line_is_needed


build\_conflict\_narrative
-----------------------------------------------------

.. autofunction:: build_conflict_narrative


explanation\_text\_lines
-----------------------------------------------------

.. autofunction:: explanation_text_lines
