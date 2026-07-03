Release Notes
=============

v0.5.0
------

This release is a minor release rather than a ``v0.4.2`` patch release. It adds
new user-facing APIs, CLI surfaces, packaged LLM resources, verification-backed
diagnostics, DSL condition operators, and simulator semantic fixes. Existing
models should review the compatibility notes before upgrading.

Verification and Inspect
~~~~~~~~~~~~~~~~~~~~~~~~

- Added the :mod:`pyfcstm.verify` package as the public entry point for raw
  verification algorithms, registry metadata, complexity taxonomy, and inspect
  gating helpers.
- Added SMT-local verification algorithms for guards, effects, lifecycle
  relations, transition shadowing, and composite initialization checks.
- Integrated inspect-eligible verification algorithms into
  :func:`pyfcstm.diagnostics.inspect_model` and the ``pyfcstm inspect`` CLI.
  Verify-backed checks stay opt-in through ``enable_verify=True`` or
  ``pyfcstm inspect --enable-verify``.
- Added inspect safety gates for complexity tier, call-count scaling, and SMT
  timeout forwarding. BMC-style search remains outside the automatic inspect
  path.

Diagnostics and CLI
~~~~~~~~~~~~~~~~~~~

- Expanded the structured diagnostics catalog to 59 codes: 20 errors,
  32 warnings, and 7 infos.
- Added verify-backed diagnostic coverage while keeping the default inspect
  analysis path static unless verification is explicitly enabled.
- Added ``pyfcstm inspect`` as a default human-readable diagnostic report, with
  ``--format json`` preserving stable JSON output matching
  ``inspect_model(model).to_json()``.
- Improved the default human inspect report into a checker-style diagnostic layout with nearby source context, and added ``--color auto|always|never`` for ANSI color control while keeping files, pipes, and machine formats ANSI-free.
- Added stable LLM inspect report formats, ``--format llm-json`` and ``--format llm-md``, using schema ``pyfcstm.inspect.llm.v1`` with source context, provenance, repair guidance, and do-not notes for repair loops.
- Preserved Python / jsfcstm diagnostic-surface parity for normalized code,
  severity, and reference payloads used by editor integrations.

LLM Grammar Guide
~~~~~~~~~~~~~~~~~

- Added :mod:`pyfcstm.llm` with
  :func:`pyfcstm.llm.get_grammar_guide_prompt_for_llm`,
  :func:`pyfcstm.llm.get_grammar_guide_prompt_path_for_llm`, and
  :func:`pyfcstm.llm.get_grammar_guide_prompt_metadata_for_llm`.
- Packaged the official LLM-facing FCSTM grammar guide as
  ``pyfcstm/llm/fcstm_grammar_guide.md``.
- Added a packaged SHA-256 sidecar and runtime integrity verification for the
  grammar guide prompt. Callers may downgrade integrity failures to warnings
  when they intentionally need to inspect a damaged or development resource.
- Added standalone ``llm_eval/`` fixtures and reports for prompt-quality
  validation. These files are repository evaluation assets and are not packaged
  into PyPI distributions.

Simulation and Built-In Templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Hardened simulator semantics around speculative rollback, hot-start
  initialization, event normalization, lifecycle action references, abstract
  handler contracts, and cycle boundary behavior.
- Added a semantic fixture corpus for simulator and generated-runtime alignment.
- Stabilized generated Python runtime metadata, callback rollback behavior, and
  expression-error wrapping.
- The packaged built-in template flow remains available through
  ``pyfcstm generate --template ...``. Current packaged templates are
  ``python``, ``c``, and ``c_poll``; the VSCode extension has its own
  independent version line and is not versioned as ``0.5.0`` by this Python
  package release.

DSL Expression Operators
~~~~~~~~~~~~~~~~~~~~~~~~

This release extends ``cond_expression`` with three boolean operators for guard
conditions and other boolean expression sites:

- ``A => B`` and ``A implies B`` express implication. The canonical DSL spelling
  is ``=>``. Implication is right-associative, so ``A => B => C`` means
  ``A => (B => C)``.
- ``A xor B`` expresses boolean exclusive-or. Chained ``xor`` is a
  left-associative boolean parity chain, not an exactly-one-of-many operator.
- ``A iff B`` expresses boolean equivalence and is the readable spelling of
  boolean equality. Chained ``iff`` expressions use the same boolean equality
  precedence layer as ``==`` and ``!=``.

Compatibility Notes
~~~~~~~~~~~~~~~~~~~

``implies``, ``xor``, and ``iff`` are now reserved DSL keywords. Existing
machines that used these names for variables, states, or events must rename
those identifiers before using this release.

``->`` remains the state-transition arrow and is not an implication operator in
guard conditions. Use ``=>`` or ``implies`` instead.

``^`` remains the numeric bitwise XOR operator. It can be used inside arithmetic
expressions that are compared in a guard, for example:

.. code-block:: fcstm

   StateA -> StateB : if [(flags ^ 0xFF) == 0];

It is not a boolean XOR spelling:

.. code-block:: fcstm

   StateA -> StateB : if [a > 0 xor b > 0];   // valid
   StateA -> StateB : if [(a > 0) ^ (b > 0)]; // invalid
   StateA -> StateB : if [true ^ false];      // invalid

The verification and inspect APIs are new public surfaces in this release. They
are intended to be stable at the function and JSON-contract level, but callers
should still treat precise diagnostic wording and solver evidence text as
diagnostic payloads rather than hard-coded parsing targets.
