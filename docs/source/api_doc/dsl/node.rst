pyfcstm.dsl.node
========================================================

.. currentmodule:: pyfcstm.dsl.node

.. automodule:: pyfcstm.dsl.node


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


INIT\_STATE
-----------------------------------------------------

.. autodata:: INIT_STATE


EXIT\_STATE
-----------------------------------------------------

.. autodata:: EXIT_STATE


ALL
-----------------------------------------------------

.. autodata:: ALL


ASTNode
-----------------------------------------------------

.. autoclass:: ASTNode


Identifier
-----------------------------------------------------

.. autoclass:: Identifier


ChainID
-----------------------------------------------------

.. autoclass:: ChainID
    :members: __str__,path,is_absolute


Expr
-----------------------------------------------------

.. autoclass:: Expr


Literal
-----------------------------------------------------

.. autoclass:: Literal
    :members: value,__str__,raw


Integer
-----------------------------------------------------

.. autoclass:: Integer


HexInt
-----------------------------------------------------

.. autoclass:: HexInt
    :members: __str__


Float
-----------------------------------------------------

.. autoclass:: Float
    :members: __str__


Boolean
-----------------------------------------------------

.. autoclass:: Boolean
    :members: __post_init__


Constant
-----------------------------------------------------

.. autoclass:: Constant
    :members: __str__,__KNOWN_CONSTANTS__


Name
-----------------------------------------------------

.. autoclass:: Name
    :members: __str__,name


Paren
-----------------------------------------------------

.. autoclass:: Paren
    :members: __str__,expr


UnaryOp
-----------------------------------------------------

.. autoclass:: UnaryOp
    :members: __post_init__,__str__,__aliases__,op,expr


BinaryOp
-----------------------------------------------------

.. autoclass:: BinaryOp
    :members: __post_init__,__str__,__aliases__,expr1,op,expr2


ConditionalOp
-----------------------------------------------------

.. autoclass:: ConditionalOp
    :members: __str__,cond,value_true,value_false


UFunc
-----------------------------------------------------

.. autoclass:: UFunc
    :members: __str__,func,expr


Statement
-----------------------------------------------------

.. autoclass:: Statement


OperationalStatement
-----------------------------------------------------

.. autoclass:: OperationalStatement


ConstantDefinition
-----------------------------------------------------

.. autoclass:: ConstantDefinition
    :members: __str__,name,expr


InitialAssignment
-----------------------------------------------------

.. autoclass:: InitialAssignment
    :members: __str__,name,expr


DefAssignment
-----------------------------------------------------

.. autoclass:: DefAssignment
    :members: __str__,name,type,expr


OperationalDeprecatedAssignment
-----------------------------------------------------

.. autoclass:: OperationalDeprecatedAssignment
    :members: __str__,name,expr


Condition
-----------------------------------------------------

.. autoclass:: Condition
    :members: __str__,expr


Preamble
-----------------------------------------------------

.. autoclass:: Preamble
    :members: __str__,stats


Operation
-----------------------------------------------------

.. autoclass:: Operation
    :members: __str__,stats


ImportMappingStatement
-----------------------------------------------------

.. autoclass:: ImportMappingStatement


ImportDefSelector
-----------------------------------------------------

.. autoclass:: ImportDefSelector


ImportDefExactSelector
-----------------------------------------------------

.. autoclass:: ImportDefExactSelector
    :members: __str__,name


ImportDefSetSelector
-----------------------------------------------------

.. autoclass:: ImportDefSetSelector
    :members: __str__,names


ImportDefPatternSelector
-----------------------------------------------------

.. autoclass:: ImportDefPatternSelector
    :members: __str__,pattern


ImportDefFallbackSelector
-----------------------------------------------------

.. autoclass:: ImportDefFallbackSelector
    :members: __str__


ImportDefTargetTemplate
-----------------------------------------------------

.. autoclass:: ImportDefTargetTemplate
    :members: __str__,template


ImportDefMapping
-----------------------------------------------------

.. autoclass:: ImportDefMapping
    :members: __str__,selector,target_template


ImportEventMapping
-----------------------------------------------------

.. autoclass:: ImportEventMapping
    :members: __str__,source_event,target_event,extra_name


ImportStatement
-----------------------------------------------------

.. autoclass:: ImportStatement
    :members: __post_init__,__str__,source_path,alias,extra_name,mappings


TransitionDefinition
-----------------------------------------------------

.. autoclass:: TransitionDefinition
    :members: __str__,from_state,to_state,event_id,condition_expr,post_operations


ForceTransitionDefinition
-----------------------------------------------------

.. autoclass:: ForceTransitionDefinition
    :members: __str__,from_state,to_state,event_id,condition_expr


StateDefinition
-----------------------------------------------------

.. autoclass:: StateDefinition
    :members: __post_init__,__str__,name,extra_name,events,imports,substates,transitions,enters,durings,exits,during_aspects,force_transitions,is_pseudo


OperationAssignment
-----------------------------------------------------

.. autoclass:: OperationAssignment
    :members: __str__,name,expr


OperationIfBranch
-----------------------------------------------------

.. autoclass:: OperationIfBranch
    :members: condition,statements


OperationIf
-----------------------------------------------------

.. autoclass:: OperationIf
    :members: __str__,branches


EventDefinition
-----------------------------------------------------

.. autoclass:: EventDefinition
    :members: __str__,name,extra_name


StateMachineDSLProgram
-----------------------------------------------------

.. autoclass:: StateMachineDSLProgram
    :members: __str__,definitions,root_state


EnterStatement
-----------------------------------------------------

.. autoclass:: EnterStatement


EnterOperations
-----------------------------------------------------

.. autoclass:: EnterOperations
    :members: __str__,operations,name


EnterAbstractFunction
-----------------------------------------------------

.. autoclass:: EnterAbstractFunction
    :members: __str__,name,doc


EnterRefFunction
-----------------------------------------------------

.. autoclass:: EnterRefFunction
    :members: __str__,name,ref


ExitStatement
-----------------------------------------------------

.. autoclass:: ExitStatement


ExitOperations
-----------------------------------------------------

.. autoclass:: ExitOperations
    :members: __str__,operations,name


ExitAbstractFunction
-----------------------------------------------------

.. autoclass:: ExitAbstractFunction
    :members: __str__,name,doc


ExitRefFunction
-----------------------------------------------------

.. autoclass:: ExitRefFunction
    :members: __str__,name,ref


DuringStatement
-----------------------------------------------------

.. autoclass:: DuringStatement


DuringOperations
-----------------------------------------------------

.. autoclass:: DuringOperations
    :members: __str__,aspect,operations,name


DuringAbstractFunction
-----------------------------------------------------

.. autoclass:: DuringAbstractFunction
    :members: __str__,name,aspect,doc


DuringRefFunction
-----------------------------------------------------

.. autoclass:: DuringRefFunction
    :members: __str__,name,aspect,ref


DuringAspectStatement
-----------------------------------------------------

.. autoclass:: DuringAspectStatement


DuringAspectOperations
-----------------------------------------------------

.. autoclass:: DuringAspectOperations
    :members: __str__,aspect,operations,name


DuringAspectAbstractFunction
-----------------------------------------------------

.. autoclass:: DuringAspectAbstractFunction
    :members: __str__,name,aspect,doc


DuringAspectRefFunction
-----------------------------------------------------

.. autoclass:: DuringAspectRefFunction
    :members: __str__,name,aspect,ref


