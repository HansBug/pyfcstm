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
    :members: stage,aspect,name,doc,operations,is_abstract,to_ast_node


State
----------------------------------------------------------

.. autoclass:: State
    :members: name,path,substates,events,transitions,on_enters,on_durings,on_exits,parent_ref,substate_name_to_id,is_leaf_state,parent,is_root_state,transitions_from,transitions_to,transitions_entering_children,transitions_entering_children_simplified,abstract_on_enters,non_abstract_on_enters,abstract_on_durings,non_abstract_on_durings,abstract_on_exits,non_abstract_on_exits,to_ast_node,to_transition_ast_node,to_plantuml,walk_states


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
