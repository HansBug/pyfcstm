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


BmcSemanticRole
-----------------------------------------------------

.. autodata:: BmcSemanticRole


CLASSIFICATION\_SCOPES
-----------------------------------------------------

.. autodata:: CLASSIFICATION_SCOPES


MAX\_SOURCE\_EXCERPT\_CHARS
-----------------------------------------------------

.. autodata:: MAX_SOURCE_EXCERPT_CHARS


UNBUILT\_SLOTS
-----------------------------------------------------

.. autodata:: UNBUILT_SLOTS


STAGE\_FALLBACK\_SCOPES
-----------------------------------------------------

.. autodata:: STAGE_FALLBACK_SCOPES


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


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


BmcConflictNarrative
-----------------------------------------------------

.. autoclass:: BmcConflictNarrative
    :members: derivation_status,headline,summary


BmcConflictProof
-----------------------------------------------------

.. autoclass:: BmcConflictProof
    :members: scope,root_id


BmcInfeasibilityExplanation
-----------------------------------------------------

.. autoclass:: BmcInfeasibilityExplanation
    :members: __post_init__,to_canonical,requested_mode,achieved_mode,status,classification,core,proof,narrative,reason,elapsed_ms
