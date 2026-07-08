pyfcstm.bmc.ast
========================================================

.. currentmodule:: pyfcstm.bmc.ast

.. automodule:: pyfcstm.bmc.ast


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


BmcExpr
-----------------------------------------------------

.. autoclass:: BmcExpr
    :members: to_canonical,__str__


BmcNumExpr
-----------------------------------------------------

.. autoclass:: BmcNumExpr


BmcCondExpr
-----------------------------------------------------

.. autoclass:: BmcCondExpr


IntLiteral
-----------------------------------------------------

.. autoclass:: IntLiteral
    :members: __post_init__,value,raw,kind


CallStepPoint
-----------------------------------------------------

.. autoclass:: CallStepPoint
    :members: __post_init__,absolute,relative,to_canonical,__str__,kind,value


CallStepSelector
-----------------------------------------------------

.. autoclass:: CallStepSelector
    :members: __post_init__,omitted,all,point,range,to_canonical,__str__,kind,start,end


CallFilter
-----------------------------------------------------

.. autoclass:: CallFilter
    :members: __post_init__,effective_step,to_canonical,__str__,action,step,stage,role,state,active_leaf,named_ref,named_ref_is_null,where


FloatLiteral
-----------------------------------------------------

.. autoclass:: FloatLiteral
    :members: __post_init__,value,raw


BoolLiteral
-----------------------------------------------------

.. autoclass:: BoolLiteral
    :members: __post_init__,value,raw


NameRef
-----------------------------------------------------

.. autoclass:: NameRef
    :members: __post_init__,name


MathConst
-----------------------------------------------------

.. autoclass:: MathConst
    :members: __post_init__,name


NumUnaryOp
-----------------------------------------------------

.. autoclass:: NumUnaryOp
    :members: __post_init__,op,operand


NumBinaryOp
-----------------------------------------------------

.. autoclass:: NumBinaryOp
    :members: __post_init__,left,op,right


NumConditionalOp
-----------------------------------------------------

.. autoclass:: NumConditionalOp
    :members: __post_init__,condition,if_true,if_false


UFuncCall
-----------------------------------------------------

.. autoclass:: UFuncCall
    :members: __post_init__,func,operand


CondUnaryOp
-----------------------------------------------------

.. autoclass:: CondUnaryOp
    :members: __post_init__,op,operand


NumericComparison
-----------------------------------------------------

.. autoclass:: NumericComparison
    :members: __post_init__,left,op,right


CondBinaryOp
-----------------------------------------------------

.. autoclass:: CondBinaryOp
    :members: __post_init__,left,op,right


CondConditionalOp
-----------------------------------------------------

.. autoclass:: CondConditionalOp
    :members: __post_init__,condition,if_true,if_false


FrameVar
-----------------------------------------------------

.. autoclass:: FrameVar
    :members: __post_init__,name,spelling


Cycle
-----------------------------------------------------

.. autoclass:: Cycle


Active
-----------------------------------------------------

.. autoclass:: Active
    :members: __post_init__,state_path,frame


Terminated
-----------------------------------------------------

.. autoclass:: Terminated
    :members: __post_init__,frame


Event
-----------------------------------------------------

.. autoclass:: Event
    :members: __post_init__,event_path,selector


Case
-----------------------------------------------------

.. autoclass:: Case
    :members: __post_init__,label,frame


CallCount
-----------------------------------------------------

.. autoclass:: CallCount
    :members: __post_init__,filter


Called
-----------------------------------------------------

.. autoclass:: Called
    :members: __post_init__,call_filter,name,frame,filter
