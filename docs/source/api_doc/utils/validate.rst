pyfcstm.utils.validate
========================================================

.. currentmodule:: pyfcstm.utils.validate

.. automodule:: pyfcstm.utils.validate


Span
-----------------------------------------------------

.. autoclass:: Span
    :members: line,column,end_line,end_column


ModelDiagnostic
-----------------------------------------------------

.. autoclass:: ModelDiagnostic
    :members: __post_init__,is_error,format_line,code,severity,message,span,refs


ValidationError
-----------------------------------------------------

.. autoclass:: ValidationError


ModelValidationError
-----------------------------------------------------

.. autoclass:: ModelValidationError
    :members: __init__


ModelValueError
-----------------------------------------------------

.. autoclass:: ModelValueError


ModelLookupError
-----------------------------------------------------

.. autoclass:: ModelLookupError


IValidatable
-----------------------------------------------------

.. autoclass:: IValidatable
    :members: validate,__validators__
