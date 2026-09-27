pyfcstm.solver.proof\_text
========================================================

.. currentmodule:: pyfcstm.solver.proof_text

.. automodule:: pyfcstm.solver.proof_text


FoldProposal
-----------------------------------------------------

.. autoclass:: FoldProposal
    :members: root_id,block_ids,premise_block_ids,claims,active_hypotheses,title_en,title_zh


ReadingFolder
-----------------------------------------------------

.. autoclass:: ReadingFolder
    :members: __post_init__,propose


ReadingBlock
-----------------------------------------------------

.. autoclass:: ReadingBlock
    :members: block_id,kind,claims,premise_block_ids,active_hypotheses,evidence_node_ids,source_links,detail_block_ids,title_en,title_zh


ProofReading
-----------------------------------------------------

.. autoclass:: ProofReading
    :members: __post_init__,get_block,expand,get_source,to_canonical,to_text,query_id,solver_status,root_id,status,blocks,sources,gaps,graph,detail_blocks


build\_reading
-----------------------------------------------------

.. autofunction:: build_reading
