pyfcstm.dsl.node
=================================================

.. currentmodule:: pyfcstm.dsl.node

.. automodule:: pyfcstm.dsl.node


ASTNode
----------------------------------------------------------

.. autoclass:: ASTNode
    :members:


Identifier
----------------------------------------------------------

.. autoclass:: Identifier
    :members:


ChainID
----------------------------------------------------------

.. autoclass:: ChainID
    :members: path, is_absolute, __str__


Expr
----------------------------------------------------------

.. autoclass:: Expr
    :members:


Literal
----------------------------------------------------------

.. autoclass:: Literal
    :members: raw, value, __str__


Boolean
----------------------------------------------------------

.. autoclass:: Boolean
    :members: raw, value, __str__, __post_init__


Integer
----------------------------------------------------------

.. autoclass:: Integer
    :members: raw, value


HexInt
----------------------------------------------------------

.. autoclass:: HexInt
    :members: raw, value, __str__


Float
----------------------------------------------------------

.. autoclass:: Float
    :members: raw, value, __str__


Constant
----------------------------------------------------------

.. autoclass:: Constant
    :members: raw, value, __str__


Name
----------------------------------------------------------

.. autoclass:: Name
    :members: name, __str__


Paren
----------------------------------------------------------

.. autoclass:: Paren
    :members: expr, __str__


UnaryOp
----------------------------------------------------------

.. autoclass:: UnaryOp
    :members: op, expr, __str__, __post_init__


BinaryOp
----------------------------------------------------------

.. autoclass:: BinaryOp
    :members: expr1, op, expr2, __str__, __post_init__


ConditionalOp
----------------------------------------------------------

.. autoclass:: ConditionalOp
    :members: cond, value_true, value_false, __str__


UFunc
----------------------------------------------------------

.. autoclass:: UFunc
    :members: func, expr, __str__


Statement
----------------------------------------------------------

.. autoclass:: Statement
    :members:


ConstantDefinition
----------------------------------------------------------

.. autoclass:: ConstantDefinition
    :members: name, expr, __str__


InitialAssignment
----------------------------------------------------------

.. autoclass:: InitialAssignment
    :members: name, expr, __str__


DefAssignment
----------------------------------------------------------

.. autoclass:: DefAssignment
    :members: name, type, expr, __str__


OperationalDeprecatedAssignment
----------------------------------------------------------

.. autoclass:: OperationalDeprecatedAssignment
    :members: name, expr, __str__


Preamble
----------------------------------------------------------

.. autoclass:: Preamble
    :members: stats, __str__


Operation
----------------------------------------------------------

.. autoclass:: Operation
    :members: stats, __str__


Condition
----------------------------------------------------------

.. autoclass:: Condition
    :members: expr, __str__


TransitionDefinition
----------------------------------------------------------

.. autoclass:: TransitionDefinition
    :members: from_state, to_state, event_id, condition_expr, post_operations, __str__


ForceTransitionDefinition
----------------------------------------------------------

.. autoclass:: ForceTransitionDefinition
    :members: from_state, to_state, event_id, condition_expr, __str__


StateDefinition
----------------------------------------------------------

.. autoclass:: StateDefinition
    :members: name, substates, transitions, enters, durings, exits, during_aspects, force_transitions, __str__, __post_init__


OperationAssignment
----------------------------------------------------------

.. autoclass:: OperationAssignment
    :members: name, expr, __str__


EventDefinition
----------------------------------------------------------

.. autoclass:: EventDefinition
    :members: name, extra_name, __str__


StateMachineDSLProgram
----------------------------------------------------------

.. autoclass:: StateMachineDSLProgram
    :members: definitions, root_state, __str__


EnterStatement
----------------------------------------------------------

.. autoclass:: EnterStatement
    :members:


EnterOperations
----------------------------------------------------------

.. autoclass:: EnterOperations
    :members: operations, name, __str__


EnterAbstractFunction
----------------------------------------------------------

.. autoclass:: EnterAbstractFunction
    :members: name, doc, __str__


EnterRefFunction
----------------------------------------------------------

.. autoclass:: EnterRefFunction
    :members: name, ref, __str__


ExitStatement
----------------------------------------------------------

.. autoclass:: ExitStatement
    :members:


ExitOperations
----------------------------------------------------------

.. autoclass:: ExitOperations
    :members: operations, name, __str__


ExitAbstractFunction
----------------------------------------------------------

.. autoclass:: ExitAbstractFunction
    :members: name, doc, __str__


ExitRefFunction
----------------------------------------------------------

.. autoclass:: ExitRefFunction
    :members: name, ref, __str__


DuringStatement
----------------------------------------------------------

.. autoclass:: DuringStatement
    :members:


DuringOperations
----------------------------------------------------------

.. autoclass:: DuringOperations
    :members: aspect, operations, name, __str__


DuringAbstractFunction
----------------------------------------------------------

.. autoclass:: DuringAbstractFunction
    :members: name, aspect, doc, __str__


DuringRefFunction
----------------------------------------------------------

.. autoclass:: DuringRefFunction
    :members: name, aspect, ref, __str__


DuringAspectStatement
----------------------------------------------------------

.. autoclass:: DuringAspectStatement
    :members:


DuringAspectOperations
----------------------------------------------------------

.. autoclass:: DuringAspectOperations
    :members: aspect, operations, name, __str__


DuringAspectAbstractFunction
----------------------------------------------------------

.. autoclass:: DuringAspectAbstractFunction
    :members: name, aspect, doc, __str__


DuringAspectRefFunction
----------------------------------------------------------

.. autoclass:: DuringAspectRefFunction
    :members: name, aspect, ref, __str__


INIT_STATE
----------------------------------------------------------

.. autodata:: INIT_STATE


EXIT_STATE
----------------------------------------------------------

.. autodata:: EXIT_STATE


ALL
----------------------------------------------------------

.. autodata:: ALL