Use and extend UNSAT explanations
=================================

Start with the ``query`` and ``names`` from
:doc:`/tutorials/unsat_proofs/index`. These recipes use Python APIs; there is no
new solver-proof command in the BMC CLI. Complete runnable examples are in
:download:`proof.demo.py </tutorials/unsat_proofs/proof.demo.py>`.

Minimize conditions and reprove
-------------------------------

.. code-block:: python

    report = explain_unsat(query, names=names, minimize=True)
    print(report.core.core_ids)
    print(report.core.subset_minimality, report.proof_scope)

For the tutorial query the output is:

.. code-block:: text

    ('goal', 'initial', 'update')
    proven core

The original proof is retained as ``full_proof``. The selected subset is proved
again in a separate execution; its graph is ``proof``. Compare the two
``execution_id`` values rather than joining node IDs across graphs.
``proven`` means no surviving removable group can be deleted individually. It
does not mean fewest groups or shortest proof. If a trial returns UNKNOWN,
minimality can remain ``not_proven``; inspect ``stop_reason``.

Keep assumptions fixed
----------------------

Put conditions that must be present in every trial in ``background``:

.. code-block:: python

    fixed = UnsatQuery("fixed", (
        UnsatConstraint("goal", (after < 0,)),
    ), background=(UnsatConstraint("domain", (after >= 0,)),))
    result = explain_unsat(fixed, minimize=True)
    assert result.core.core_ids == ("goal",)

An inconsistent background produces the verified empty tuple ``()``. ``None``
means no core was verified. Neither value means that pyfcstm silently dropped
the background. To obtain only checked core evidence, use ``mode="core"``;
then ``proof_status`` is ``not_requested``.

Attach source locations at construction time
--------------------------------------------

Use ``SourceDescription`` directly as a condition group's ``source``. For
application objects, subclass ``SourceAdapter``. A separate expression binding
records construction or context, without inventing a logical premise:

.. code-block:: python

    from pyfcstm.solver import (
        ProofExtensions, SourceAdapter, SourceBinding, SourceDescription,
    )

    update = after == before + 1

    class Sources(SourceAdapter):
        def bindings(self):
            return (SourceBinding(update, SourceDescription(
                "increment", "Increment action", "virtual:policy",
                excerpt="balance@1 = balance@0 + 1",
            ), "construction"),)

    report = explain_unsat(query, names=names,
                           extensions=ProofExtensions(source_adapter=Sources()))
    assert report.reading.get_source("increment").document_id == "virtual:policy"

Here the document ID deliberately denotes a virtual source; it is not a claimed
file location. A real frontend should supply its actual document ID, one-based
half-open span and optional excerpt. Bind the original expression in its actual
Z3 context. Same-looking text or another context is not a substitute.

The runnable ``--case sources`` example implements ``describe(handle)`` for
configuration handles. Its complete output is:

.. literalinclude:: /tutorials/unsat_proofs/proof.demo.py.txt
   :language: text
   :start-after: BEGIN sources en
   :end-before: END sources en

Logical input origins, construction links and contextual links have different
meanings. An equal formula submitted twice retains alternative occurrences;
a source link alone does not establish that one particular statement was
necessary. Missing group descriptions can leave ``source_status="partial"``
while the mathematical reading is complete.

Give a deduction a domain title
-------------------------------

A folder proposes an existing proof slice; it does not supply a replacement
proof. This example titles only the final block:

.. code-block:: python

    from pyfcstm.solver import FoldProposal, ReadingFolder

    def title_root(reading):
        root = reading.get_block(reading.root_id)
        yield FoldProposal(
            root.block_id, (root.block_id,), root.premise_block_ids,
            root.claims, root.active_hypotheses,
            "The balance conditions conflict", "余额条件互相矛盾",
        )

    report = explain_unsat(query, names=names, extensions=ProofExtensions(
        reading_folders=(ReadingFolder(title_root),),
    ))
    details = report.reading.expand(report.reading.root_id)
    assert details

The reader checks connectivity, all external premises, exact conclusions,
open hypotheses and uses outside the slice. Omitting a premise or hiding a live
assumption raises ``ValueError``. The title is trusted application text, not an
independently verified natural-language theorem. ``expand`` returns original
reading blocks; ``evidence_node_ids`` connect them to the native graph. A fold
cannot promote a partial reading to complete.

Interpret another native rule
-----------------------------

Register one exact rule name and an interpreter that returns ``RuleAnalysis``:

.. code-block:: python

    from pyfcstm.solver import ProofRuleHandler, RuleAnalysis

    def interpret_instantiation(node, graph):
        return RuleAnalysis("logical", "trusted")

    extension = ProofExtensions(rule_handlers=(
        ProofRuleHandler("quant-inst", interpret_instantiation),
    ))

This example classifies an existing instantiation step; it does not claim to
check it. A real checker may return ``checked`` only after performing its own
check. Duplicate handlers are errors. ``asserted``, ``hypothesis`` and ``lemma``
are reserved: plugins cannot replace input binding or hypothesis discharge.
Plugin exceptions propagate. Registering a rule does not support every other
quantifier rule or remove their gaps.

Save and read offline
---------------------

.. code-block:: python

    import json
    from pyfcstm.solver import UnsatReport

    payload = json.dumps(report.to_canonical(), ensure_ascii=False)
    restored = UnsatReport.from_canonical(json.loads(payload))
    assert restored.to_canonical() == report.to_canonical()

``payload`` is a string; this example writes no file. Use ordinary file I/O if
persistence is needed. Reading a saved report imports no Z3 library and performs
no solve. The loader rejects malformed fields, references and cycles. It does
not authenticate the author of a snapshot or independently certify its claims.
Use the data contract shipped with the producing release; payloads contain no
schema-dispatch version field.

Handle incomplete work
----------------------

.. code-block:: python

    report = explain_unsat(query, timeout_ms=1000, minimize=True)
    if report.reading is not None:
        print(report.reading.to_text())
    print(report.solver_status, report.proof_status, report.stop_reason)

One deadline covers capture, minimization and assembly. An already completed
full proof survives optional minimization/reproof failure. A captured graph can
outlive timed-out assembly, with ``reading=None``. SAT, UNKNOWN and timeout do
not produce a fabricated contradiction. Deadlines are cooperative: a running
extension callback cannot be forcibly interrupted by this API.

For exact states and exception types, use :doc:`/reference/unsat_proofs/index`.
For future BMC frontend responsibilities, use
:doc:`/explanations/unsat_proofs/index`.
