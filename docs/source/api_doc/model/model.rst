pyfcstm.model.model
========================================================

.. currentmodule:: pyfcstm.model.model

.. automodule:: pyfcstm.model.model


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


ComboOriginRef
-----------------------------------------------------

.. autoclass:: ComboOriginRef
    :members: origin_id,term_index,role,consumes_term,term_text,transition_span,trigger_span,term_span,value_span,removal_span


OperationStatement
-----------------------------------------------------

.. autoclass:: OperationStatement


Operation
-----------------------------------------------------

.. autoclass:: Operation
    :members: to_ast_node,var_name_to_ast_node,var_name,expr


IfBlockBranch
-----------------------------------------------------

.. autoclass:: IfBlockBranch
    :members: to_ast_node,condition,statements


IfBlock
-----------------------------------------------------

.. autoclass:: IfBlock
    :members: to_ast_node,branches


Event
-----------------------------------------------------

.. autoclass:: Event
    :members: __post_init__,path,path_name,to_ast_node,name,state_path,extra_name,declared,origins


Transition
-----------------------------------------------------

.. autoclass:: Transition
    :members: parent,parent,to_ast_node,from_state,to_state,event,guard,effects,event_scope,is_forced,forced_origin,combo_origin_refs,combo_projection_key,combo_projection_order_key,combo_reuse_group_id,combo_priority_run_identity,combo_priority_run_index,parent_ref


OnStage
-----------------------------------------------------

.. autoclass:: OnStage
    :members: parent,parent,is_ref,is_aspect,func_name,to_ast_node,stage,aspect,name,doc,operations,is_abstract,state_path,ref,ref_state_path,parent_ref


OnAspect
-----------------------------------------------------

.. autoclass:: OnAspect
    :members: parent,parent,is_ref,is_aspect,func_name,to_ast_node,stage,aspect,name,doc,operations,is_abstract,state_path,ref,ref_state_path,parent_ref


State
-----------------------------------------------------

.. autoclass:: State
    :members: __post_init__,is_leaf_state,is_stoppable,parent,parent,is_root_state,init_transitions,transitions_from,transitions_to,transitions_entering_children,transitions_entering_children_simplified,list_on_enters,abstract_on_enters,non_abstract_on_enters,list_on_durings,abstract_on_durings,non_abstract_on_durings,list_on_exits,abstract_on_exits,non_abstract_on_exits,list_on_during_aspects,abstract_on_during_aspects,non_abstract_on_during_aspects,iter_on_during_before_aspect_recursively,iter_on_during_after_aspect_recursively,iter_on_during_aspect_recursively,list_on_during_aspect_recursively,transition_to_ast_node,to_transition_ast_node,to_ast_node,to_plantuml,walk_states,resolve_event,name,path,substates,events,transitions,named_functions,on_enters,on_durings,on_exits,on_during_aspects,parent_ref,substate_name_to_id,extra_name,is_pseudo,is_combo_relay


VarDefine
-----------------------------------------------------

.. autoclass:: VarDefine
    :members: to_ast_node,name_ast_node,name,type,init


StateMachine
-----------------------------------------------------

.. autoclass:: StateMachine
    :members: to_ast_node,to_plantuml,walk_states,diagram,show,resolve_event,defines,root_state,forced_transitions,source_text,source_path


parse\_dsl\_node\_to\_state\_machine
-----------------------------------------------------

.. autofunction:: parse_dsl_node_to_state_machine
