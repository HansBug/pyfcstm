pyfcstm.model.expr
========================================================

.. currentmodule:: pyfcstm.model.expr

.. automodule:: pyfcstm.model.expr


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


Expr
-----------------------------------------------------

.. autoclass:: Expr
    :members: list_variables,__call__,__str__,to_ast_node


Integer
-----------------------------------------------------

.. autoclass:: Integer
    :members: to_ast_node,value


Float
-----------------------------------------------------

.. autoclass:: Float
    :members: to_ast_node,value


Boolean
-----------------------------------------------------

.. autoclass:: Boolean
    :members: __post_init__,to_ast_node,value


Op
-----------------------------------------------------

.. autoclass:: Op
    :members: op_mark


BinaryOp
-----------------------------------------------------

.. autoclass:: BinaryOp
    :members: __post_init__,op_mark,to_ast_node,__aliases__,x,op,y


UnaryOp
-----------------------------------------------------

.. autoclass:: UnaryOp
    :members: __post_init__,op_mark,to_ast_node,__aliases__,op,x


UFunc
-----------------------------------------------------

.. autoclass:: UFunc
    :members: to_ast_node,func,x


ConditionalOp
-----------------------------------------------------

.. autoclass:: ConditionalOp
    :members: op_mark,to_ast_node,cond,if_true,if_false


Variable
-----------------------------------------------------

.. autoclass:: Variable
    :members: to_ast_node,name


parse\_expr\_node\_to\_expr
-----------------------------------------------------

.. autofunction:: parse_expr_node_to_expr


