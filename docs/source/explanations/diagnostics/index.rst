.. _sec-explanations-diagnostics:

Diagnostics explanation
=======================

Inspect diagnostics are designed to answer three questions:

1. What does the current model contain?
2. Which parts look invalid, risky, unused, unreachable, or target-sensitive?
3. What structured context should a human, CI job, IDE, or LLM repair loop use
   next?

What inspect can do
-------------------

Default inspect is a static analysis pass over the parsed model. It can see
state hierarchy, transitions, events, variables, actions, derived reachability,
event emission, variable data flow, aspect impact, action references, combo
provenance, and registry-backed diagnostics.

This is why many diagnostics include ``span`` and ``refs``. The span points back
to source; refs name the variable, state, event, action, guard, target profile,
or provenance object that a repair loop should inspect.

What inspect cannot prove by default
------------------------------------

Default inspect is not a complete model checker. It does not explore every
runtime trace, every external event source, every abstract handler, or every
possible target-language deployment. It also does not run unbounded verification
algorithms automatically.

When you need bounded verify-backed diagnostics, opt in with ``--enable-verify``.
Even then, solver-backed checks can be affected by timeout, solver unknown
results, and the inspect policy envelope.

Severity is not the same as risk
--------------------------------

``error`` means pyfcstm cannot safely build or use the model as requested.
``warning`` means the model remains inspectable but a fact is suspicious,
risky, dead, redundant, or target-sensitive. ``info`` means the analyzer found a
non-blocking fact that often helps a reader decide whether a model is intentional.

A warning is not automatically a release blocker, but it must be explained when
it appears in checked tutorial or regression fixtures.

Why emit tier matters
---------------------

The registry contains more than default CLI output:

* ``static_pipeline`` codes can appear in ordinary inspect output.
* ``verify_pipeline`` codes need optional verify integration.
* ``lookup_api`` codes describe resolver API failures, not default static output.
* ``partial_static_pipeline`` codes may be emitted on one implementation side but not another.
* ``catalog_only`` codes preserve compatibility contracts even when current normal paths should not emit them.

A reference page that ignores this distinction will mislead CI filters and LLM
repair loops.

Why diagnostics help LLMs
-------------------------

LLM repair prompts are much safer when they can consume structured facts instead
of guessing from prose. A useful diagnostic tells the model:

* the stable ``code`` to look up;
* the ``severity`` to prioritize;
* the exact source span to edit or inspect;
* the ``refs`` payload to branch on;
* recommended actions and forbidden anti-patterns from the registry.

The LLM report formats expose those facts directly, but they still rely on the
same registry as full JSON diagnostics.
