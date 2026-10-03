What an UNSAT explanation establishes
=====================================

The input is an exact conjunction. An UNSAT result says that no assignment
satisfies that conjunction. The explanation records how Z3 reached a
contradiction and connects that evidence to named inputs and caller-supplied
sources. A property verdict, source-language semantics and bounded horizon
still belong to the application that constructed the conjunction.

From original conditions to a reading
--------------------------------------

.. list-table:: Evidence flow
   :header-rows: 1
   :widths: 25 40 35

   * - Step
     - Operation
     - Retained evidence
   * - Capture
     - Translate every original condition into an isolated proof-enabled Z3 context and solve it.
     - Input occurrences, typed terms, native proof nodes and one execution ID.
   * - Analyze
     - Check input bindings and hypothesis closure; interpret native rules and exact arithmetic certificates.
     - Separate input, scope and rule checks; explicit gaps for unsupported evidence.
   * - Read
     - Fold mechanical rewrites, retaining actual arithmetic premises and expandable evidence.
     - Ordered claims, dependencies, active hypotheses and source relationships.
   * - Optionally minimize
     - Extract and recheck a core, delete groups only after UNSAT trials, then reprove the surviving subset.
     - The full original graph, the new subset graph, and qualified core evidence.

A shared node remains shared in the evidence graph. Human text is a view over
that graph, not the input to a second proof search. The default implementation
uses Z3 and deterministic Python assembly; no LLM writes the inference chain.

For the tutorial's integer balance, the readable arithmetic is:

.. code-block:: text

    -balance@0 <= 0
    balance@1 + 1 <= 0
    balance@0 - balance@1 + 1 <= 0
    --------------------------------
    2 <= 0

The second line uses integrality. The third follows from the update equality.
Every displayed weighted sum retains its native parameters and normalized
exact coefficients. Rational coefficients use ``Fraction``, not floating point.
Negative native inequality coefficients are interpreted using Z3's oriented
absolute-weight convention; equality coefficients retain their signs.

Maintaining the proof framework
-------------------------------

Native proof translation and local reconstruction have different jobs. Capture
preserves Z3's graph. Reconstruction supplies exact, readable evidence for a
theory lemma whose native hints do not already describe every arithmetic step.
It does not replace the native conclusion or discharge its hypotheses.

The internal implementation has three extension points:

* ``reconstruction.py`` selects the existing native fast paths and ordered local
  strategies. Its immutable ``Reconstruction`` result carries the inference
  kind, check status, evidence fields and diagnostics. The common analyzer owns
  hypothesis scopes, extension precedence and timeout handling.
* ``evidence.py`` lists certificate families explicitly. Each immutable
  ``CertificateHandler`` associates a canonical node field and payload type
  with an exact checker and a reading function. Online reconstruction and
  offline loading share replay dispatch; loading never reruns proof search.
* ``evidence_text.py`` renders each family using the common formula, language,
  detail and reference context. ``text.py`` retains source links, assumptions,
  domain folds and final claims. Validation order and presentation order are
  recorded separately to preserve existing multi-certificate snapshots.

To support another rule within an existing family, extend its producer, exact
checker and reading function where needed; add a failing example and a corrupt
certificate negative control first. A genuinely new certificate family also
needs a typed canonical record, strict decoding/reference validation in
``io.py``, and a catalog entry. The catalog does not automatically make a new
payload safe to deserialize. Preserve canonical roundtrips and compare complete
readings with ``text_aligner``.

The catalog is internal, fixed and has no mutable global plugin registration.
Applications, including BMC, continue to use ``ProofExtensions`` for native-rule
interpretation, source bindings and domain reading folds. Domain presentation
cannot turn an unexplained inference into checked evidence.

Strategy order remains part of behavior: local reconstruction stops at the
first produced candidate, and a rejected candidate remains an observable gap
rather than being hidden by another strategy. Polynomial production already
replays its candidate before returning, so the dispatcher does not replay it a
second time against the shared deadline. This organization introduces neither
proof ranking nor a shortest-proof guarantee; group subset-minimality retains
its existing meaning.

Local assumptions are not global facts
--------------------------------------

Consider ``after = If(before >= 0, before + 1, 0)`` and ``after < 0``. Assuming
``before >= 0`` gives a contradiction. That branch must then be closed before
using its negation to finish the other case. A proof whose final contradiction
still depends on an open local hypothesis is rejected as a closed refutation.

The complete branch output is reproduced below. Internal defining clauses
explain the solver-introduced symbol; they are not attributed to an authored
statement merely because their formulas resemble one.

.. literalinclude:: /tutorials/unsat_proofs/proof.demo.py.txt
   :language: text
   :start-after: BEGIN branches en
   :end-before: END branches en

Arithmetic theory lemmas can also prove a clause by refuting its negation.
Their temporary negated-conclusion assumptions are printed and discharged;
the intermediate contradiction is not presented as an unconditional fact.

Three distinct trust questions
------------------------------

* **Did Z3 return UNSAT?** ``solver_status`` answers this, even if later
  explanation work fails.
* **Is the graph accounted for?** Input and scope checks bind leaves to exact
  occurrences and prevent local assumptions from escaping.
* **Was every inference independently checked?** ``rule_check`` and each
  ``local_check`` answer this separately. Recognized mechanical rules remain
  solver-trusted. ``reading_status="complete"`` is not a certification by a
  complete independent proof kernel.

Unsupported nonlinear, quantifier or other theory rules retain their native
nodes and mark gaps. A readable title cannot erase those gaps. Extension
interpreters are trusted Python code; their own ``checked`` declarations do
not independently establish that their implementation is correct. Likewise,
loading a snapshot validates its structure and references, not its origin.

Minimization is relative to the chosen groups
---------------------------------------------

Suppose two identical formulas come from two source statements. A native leaf
can match both occurrences. A core may retain one occurrence without showing
that this particular source was uniquely necessary. Grouping several formulas
under one identifier deliberately makes them one deletion unit.

``subset_minimality="proven"`` means that every surviving removable group was
individually tested against the final set and fixed background, and its removal
returned SAT. UNKNOWN never justifies deletion or a minimality claim. Different
cores and different proof lengths may exist. Searching for the smallest core,
shortest proof or most useful human explanation is a separate optimization
problem.

The full proof is produced before minimization. Reproof gets another execution
ID; graph node IDs never move between executions. A deadline during optional
work preserves already completed evidence. The deadline is cooperative and
cannot bound arbitrary plugin runtime or memory use as a separate process would.

Source links and a future BMC consumer
--------------------------------------

``logical`` links identify submitted condition occurrences. ``construction``
links say where an exact expression was constructed. ``context`` links provide
surrounding application information. Only the first relation denotes a logical
input occurrence, and even that does not establish unique source necessity.
A whole case containing two assignments is not automatically a precise span for
one necessary assignment.

A BMC frontend can consume the generic API without adding BMC dependencies to
the solver layer:

1. While lowering initial conditions, transition relations, definedness and
   objectives, assign stable condition-group IDs and retain original expressions.
2. Preserve statement/query spans in source handles, and register exact term
   bindings at construction time. Avoid decoding generated variable names.
3. Submit the exact target conjunction and explicit fixed background through
   ``UnsatQuery``. Keep property polarity and horizon meaning in BMC.
4. Supply ``SourceAdapter`` and optional ``ReadingFolder`` instances for
   case/action descriptions. Folds must preserve the same evidence boundaries.
5. Interpret solver results into bounded property verdicts in BMC, retaining
   proof/source completeness and core-minimality qualifiers for humans and LLMs.

This describes the consumer boundary; the BMC adapter and replacement of its
existing explanation surface are not implemented by these solver APIs.
For calls you can run today, see :doc:`/how_to/unsat_proofs/index`.
