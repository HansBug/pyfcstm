pyfcstm.bmc.relation
========================================================

.. currentmodule:: pyfcstm.bmc.relation

.. automodule:: pyfcstm.bmc.relation


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


BmcAbstractCallRecord
-----------------------------------------------------

.. autoclass:: BmcAbstractCallRecord
    :members: __post_init__,to_canonical,ordinal,action_name,stage,role,state_path,active_leaf_path,named_ref,snapshot


BmcSymbolSource
-----------------------------------------------------

.. autoclass:: BmcSymbolSource
    :members: kind,name,frame,step,display_name


BmcTraceSymbols
-----------------------------------------------------

.. autoclass:: BmcTraceSymbols
    :members: __post_init__,allocate,frame_state,frame_var,step_input,parameter,resolve_query_value,event_input,delta_flag,gamma_flag,active_state,case_selector,to_canonical,domain,frame_states,frame_vars,event_inputs,delta_flags,gamma_flags,case_selectors,step_inputs,parameters,names


BmcCaseRelation
-----------------------------------------------------

.. autoclass:: BmcCaseRelation
    :members: __post_init__,formula,to_canonical,step_index,case,selector,antecedent,consequent,implication,selector_constraint,post_var_exprs,guard_terms,definedness_constraints,call_records


BmcStepRelation
-----------------------------------------------------

.. autoclass:: BmcStepRelation
    :members: __post_init__,case_registry,to_canonical,step_index,formals,case_relations,formula,delta_constraint,gamma_constraint,progress_mutex_constraint


BmcCoreFormula
-----------------------------------------------------

.. autoclass:: BmcCoreFormula
    :members: __post_init__,to_canonical,context,symbols,domain_formula,initial_formula,transition_formula,environment_formula,core,steps,diagnostics,cone_slice


build\_bmc\_core\_formula
-----------------------------------------------------

.. autofunction:: build_bmc_core_formula
