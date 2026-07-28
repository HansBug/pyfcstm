pyfcstm.bmc.provenance
========================================================

.. currentmodule:: pyfcstm.bmc.provenance

.. automodule:: pyfcstm.bmc.provenance


MAX\_METADATA\_INT\_DIGITS
-----------------------------------------------------

.. autodata:: MAX_METADATA_INT_DIGITS


MAX\_METADATA\_DEPTH
-----------------------------------------------------

.. autodata:: MAX_METADATA_DEPTH


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
    :members: __post_init__,display_path,document,reference,excerpt,model_reference,query_reference,documents,display_root,query_documents


exact\_str
-----------------------------------------------------

.. autofunction:: exact_str


exact\_int
-----------------------------------------------------

.. autofunction:: exact_int


exact\_float
-----------------------------------------------------

.. autofunction:: exact_float


exact\_index
-----------------------------------------------------

.. autofunction:: exact_index


exact\_optional\_index
-----------------------------------------------------

.. autofunction:: exact_optional_index


json\_canonical
-----------------------------------------------------

.. autofunction:: json_canonical
