pyfcstm.semantics.catalog
========================================================

.. currentmodule:: pyfcstm.semantics.catalog

.. automodule:: pyfcstm.semantics.catalog


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


BOOL
-----------------------------------------------------

.. autodata:: BOOL


INT
-----------------------------------------------------

.. autodata:: INT


FLOAT
-----------------------------------------------------

.. autodata:: FLOAT


NUMBER
-----------------------------------------------------

.. autodata:: NUMBER


EAGER
-----------------------------------------------------

.. autodata:: EAGER


SHORT\_AND
-----------------------------------------------------

.. autodata:: SHORT_AND


SHORT\_OR
-----------------------------------------------------

.. autodata:: SHORT_OR


SHORT\_IMPLIES
-----------------------------------------------------

.. autodata:: SHORT_IMPLIES


CATALOG
-----------------------------------------------------

.. autodata:: CATALOG


COMPLEX\_POWER\_MESSAGE
-----------------------------------------------------

.. autodata:: COMPLEX_POWER_MESSAGE


MATH\_DOMAIN\_MESSAGE
-----------------------------------------------------

.. autodata:: MATH_DOMAIN_MESSAGE


cbrt
-----------------------------------------------------

.. autodata:: cbrt


ErrorRule
-----------------------------------------------------

.. autoclass:: ErrorRule
    :members: kind,raises,defined,description,message


OpSpec
-----------------------------------------------------

.. autoclass:: OpSpec
    :members: arity,error_rule,error_kind,token,kind,typing,concrete,symbolic,errors,control,unsupported


canonical\_token
-----------------------------------------------------

.. autofunction:: canonical_token


lookup
-----------------------------------------------------

.. autofunction:: lookup


cbrt\_fallback
-----------------------------------------------------

.. autofunction:: cbrt_fallback
