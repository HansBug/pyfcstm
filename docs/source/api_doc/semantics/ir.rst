pyfcstm.semantics.ir
========================================================

.. currentmodule:: pyfcstm.semantics.ir

.. automodule:: pyfcstm.semantics.ir


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


Node
-----------------------------------------------------

.. autoclass:: Node
    :members: node_id,origin


Expr
-----------------------------------------------------

.. autoclass:: Expr


Literal
-----------------------------------------------------

.. autoclass:: Literal
    :members: value


Symbol
-----------------------------------------------------

.. autoclass:: Symbol
    :members: reference


Unary
-----------------------------------------------------

.. autoclass:: Unary
    :members: op,operand


Binary
-----------------------------------------------------

.. autoclass:: Binary
    :members: op,left,right


Conditional
-----------------------------------------------------

.. autoclass:: Conditional
    :members: test,if_true,if_false


Call
-----------------------------------------------------

.. autoclass:: Call
    :members: func,args


HostAtom
-----------------------------------------------------

.. autoclass:: HostAtom
    :members: key,payload,args


Stmt
-----------------------------------------------------

.. autoclass:: Stmt


Assign
-----------------------------------------------------

.. autoclass:: Assign
    :members: target,value


Arm
-----------------------------------------------------

.. autoclass:: Arm
    :members: test,body


If
-----------------------------------------------------

.. autoclass:: If
    :members: arms
