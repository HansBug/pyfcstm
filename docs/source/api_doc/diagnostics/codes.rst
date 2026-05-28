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
    :members: name,type,required,description,enum


ForLlmSpec
-----------------------------------------------------

.. autoclass:: ForLlmSpec
    :members: summary,recommended_actions,do_not


CodeSpec
-----------------------------------------------------

.. autoclass:: CodeSpec
    :members: required_fields,code,severity,description,refs_schema,example_dsl,capability,for_llm


load\_codes
-----------------------------------------------------

.. autofunction:: load_codes


