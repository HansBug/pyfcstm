pyfcstm.diagnostics.codes
========================================================

.. currentmodule:: pyfcstm.diagnostics.codes

.. automodule:: pyfcstm.diagnostics.codes


CODE\_REGISTRY
-----------------------------------------------------

.. autodata:: CODE_REGISTRY


CodesSchemaError
-----------------------------------------------------

.. autoclass:: CodesSchemaError


CodeFieldSpec
-----------------------------------------------------

.. autoclass:: CodeFieldSpec
    :members: name,type,required,description,enum,item_enum,exact_values


ForLlmSpec
-----------------------------------------------------

.. autoclass:: ForLlmSpec
    :members: summary,recommended_actions,do_not


SuggestedFixSpec
-----------------------------------------------------

.. autoclass:: SuggestedFixSpec
    :members: kind,target,anchor_ref,text_template,rationale


CodeSpec
-----------------------------------------------------

.. autoclass:: CodeSpec
    :members: canonical_code,is_deprecated,deprecated_since,required_fields,code,severity,description,refs_schema,example_dsl,capability,for_llm,emit_tier,suggested_fix,span_object,deprecated_in,removed_in,replaced_by


load\_codes
-----------------------------------------------------

.. autofunction:: load_codes


resolve\_diagnostic\_code
-----------------------------------------------------

.. autofunction:: resolve_diagnostic_code


canonicalize\_diagnostic\_code
-----------------------------------------------------

.. autofunction:: canonicalize_diagnostic_code
