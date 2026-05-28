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


CodeSpec
-----------------------------------------------------

.. autoclass:: CodeSpec
    :members: required_fields,code,severity,description,refs_schema,example_dsl


load\_codes
-----------------------------------------------------

.. autofunction:: load_codes


