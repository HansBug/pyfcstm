pyfcstm.model.region
========================================================

.. currentmodule:: pyfcstm.model.region

.. automodule:: pyfcstm.model.region


Region
-----------------------------------------------------

.. autoclass:: Region
    :members: __post_init__,parent,parent,is_root_state,init_transitions,walk_states,walk_regions,resolve_event,list_on_during_aspects,iter_on_during_before_aspect_recursively,iter_on_during_after_aspect_recursively,to_plantuml,to_ast_node,name,path,substates,events,transitions,named_functions,on_during_aspects,doc,parent_ref,substate_name_to_id


namespace\_children
-----------------------------------------------------

.. autofunction:: namespace_children


namespace\_child
-----------------------------------------------------

.. autofunction:: namespace_child


ast\_namespace\_children
-----------------------------------------------------

.. autofunction:: ast_namespace_children


namespace\_actions
-----------------------------------------------------

.. autofunction:: namespace_actions


walk\_namespaces
-----------------------------------------------------

.. autofunction:: walk_namespaces


validate\_region\_structure
-----------------------------------------------------

.. autofunction:: validate_region_structure
