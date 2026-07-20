pyfcstm.bmc.provenance
========================================================

.. currentmodule:: pyfcstm.bmc.provenance

.. automodule:: pyfcstm.bmc.provenance


\_\_all\_\_
-----------------------------------------------------

.. autodata:: __all__


BmcSourceRef
-----------------------------------------------------

.. autoclass:: BmcSourceRef
    :members: __post_init__,to_canonical,kind,path,span


BmcTrackedConstraint
-----------------------------------------------------

.. autoclass:: BmcTrackedConstraint
    :members: __post_init__,stable_id,stage,category,expressions,source_ref,refs


SourceDocumentRegistry
-----------------------------------------------------

.. autoclass:: SourceDocumentRegistry
    :members: __post_init__,display_path,document,reference,excerpt,model_reference,query_reference,documents,display_root
