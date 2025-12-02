pyfcstm.model.model
=================================================


.. currentmodule:: pyfcstm.model.model

.. automodule:: pyfcstm.model.model


Operation
----------------------------------------------------------

.. autoclass:: Operation
    :members: var_name,expr,to_ast_node,var_name_to_ast_node


Event
----------------------------------------------------------

.. autoclass:: Event
    :members: name,state_path,path


Transition
----------------------------------------------------------

.. autoclass:: Transition
    :members: from_state,to_state,event,guard,effects,parent_ref,parent,to_ast_node


OnStage
----------------------------------------------------------

.. autoclass:: OnStage
    :members: stage,aspect,name,doc,operations,is_abstract,is_aspect,is_ref,parent,to_ast_node


OnAspect
----------------------------------------------------------

.. autoclass:: OnAspect
    :members: stage,aspect,name,doc,operations,is_abstract,is_aspect,is_ref,parent,to_ast_node


State
----------------------------------------------------------

.. autoclass:: State
    :members: is_leaf_state,parent,is_root_state,transitions_from,transitions_to,transitions_entering_children,transitions_entering_children_simplified,list_on_enters,abstract_on_enters,non_abstract_on_enters,list_on_durings,abstract_on_durings,non_abstract_on_durings,list_on_exits,abstract_on_exits,non_abstract_on_exits,list_on_during_aspects,abstract_on_during_aspects,non_abstract_on_during_aspects,iter_on_during_before_aspect_recursively,iter_on_during_after_aspect_recursively,iter_on_during_aspect_recursively,list_on_during_aspect_recursively,transition_to_ast_node,to_transition_ast_node,to_ast_node,to_plantuml,walk_states


VarDefine
----------------------------------------------------------

.. autoclass:: VarDefine
    :members: name,type,init,to_ast_node,name_ast_node


StateMachine
----------------------------------------------------------

.. autoclass:: StateMachine
    :members: defines,root_state,to_ast_node,to_plantuml,walk_states


parse_dsl_node_to_state_machine
----------------------------------------------------------

.. autofunction:: parse_dsl_node_to_state_machine