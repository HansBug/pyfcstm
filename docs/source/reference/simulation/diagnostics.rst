Candidate decision diagnostics
==============================

This reference defines captured evidence from one simulator call. For a runnable investigation, see :doc:`../../how_to/simulation/diagnostics`. Execution ordering remains defined in :doc:`../../explanations/execution_semantics/index`; input-source contracts remain in :doc:`inputs`.

Collection and querying
-----------------------

.. list-table:: Python surface
   :header-rows: 1

   * - Surface
     - Default and contract
   * - ``runtime.cycle(events=None, *, trace=False, inputs=None, diagnostics=False)``
     - ``diagnostics`` is an independent opt-in boolean. The existing event, input, commit and exception rules apply. No file is written.
   * - ``result.diagnostics``
     - ``None`` when disabled; otherwise an immutable ``CycleDiagnostics``, including calls with no candidates, Delta and ignored calls. Exceptions return no partial report.
   * - ``report.decisions``
     - Tuple of ``TransitionDecision`` objects in observation order. Iterate or filter with ordinary Python. Each check owns detached value mappings.
   * - ``str(report)``
     - Plain-text explanation: cycle result, events, inputs, parameters, persistent values before/after, committed micro-transitions in execution order, then candidate evidence. Only adjacent identical uncommitted checks fold; all their IDs and their count remain visible. Different snapshots, parents or phases never fold; committed occurrences never fold. It is not a machine protocol.
   * - ``report.to_text(transition=None, check_id=None, verbose=False)``
     - Select an exact expanded transition label or a report-local check ID (integer or decimal string). The result includes matching checks, their descendants, required ancestors and blocking selections; unrelated siblings are omitted. Supplying both selectors raises ``ValueError``. Unknown selectors produce ``No recorded evidence``; they do not prove the source was inactive. Verbose output includes every check, expanded combo addresses, full snapshots and source spans. The cycle summary always describes the whole call, even in a filtered query.
   * - ``report.to_dict()``
     - Complete independent dictionary, with tuples represented as lists and read-only mappings as dictionaries. Changes to the dictionary do not change the report. Use ``json.dumps`` when serialization is required; no schema/version discriminator is added.

Reports belong to the caller, independently of runtime history retention. Formatting and querying do not evaluate guards, sample inputs, dispatch handlers or advance a cycle. Capturing snapshots costs memory proportional to recorded checks and their variable vectors. It does not retain an unbounded history inside the runtime.

Large integers in human text use the existing runtime digit-count notation, such as ``int<5001 digits>``. Structured values remain exact integers. Standard Python JSON integer conversion limits still apply when a caller serializes exceptionally large integers; the library does not change process-wide interpreter limits.

Report fields
-------------

All fields below appear in ``to_dict()``; absent optional values are ``None`` in Python and ``null`` in JSON.

.. list-table:: ``CycleDiagnostics``
   :header-rows: 1

   * - Field
     - Type
     - Meaning
   * - ``cycle_count``
     - integer
     - Runtime count after this call. An ignored call does not increase it.
   * - ``outcome``
     - string
     - ``cycle``: ordinary committed cycle; ``delta``: successful no-progress step; ``terminated``: this call terminated; ``noop``: an already ended/error runtime ignored this call.
   * - ``state_before`` / ``state_after``
     - path tuple or ``None``; JSON list or ``null``
     - Active stack-top path at each call boundary. ``None`` denotes termination; before cold initialization the root path is present.
   * - ``decisions``
     - tuple of decisions; JSON array
     - Actual check evidence and explicit selection short-circuits. Empty does not imply Delta or error.
   * - ``roles``
     - name-to-string mapping
     - Final assembled model roles: ``control``, ``output``, ``input``, ``param``. Imported names use their final parent binding.

   * - ``input_events``
     - tuple of strings; JSON array
     - Normalized event paths processed by this cycle. An ignored call has an empty tuple; its unprocessed arguments are not evidence.
   * - ``inputs``
     - numeric mapping or ``None``
     - Complete frozen input vector even when there are no candidate checks. ``{}`` means a real cycle of a model without inputs; ``None`` means an ignored call sampled nothing, not that previous inputs were reused.
   * - ``parameters``
     - numeric mapping
     - Fixed instance values, captured even on an ignored call.
   * - ``vars_before`` / ``vars_after``
     - numeric mappings
     - Persistent control/output snapshots at the call boundaries, not speculative values. A Delta or no-op retains identical values; a normal stay-in-place cycle may change them through ``during``. Use ``roles`` to distinguish control from output.

.. list-table:: ``TransitionDecision``
   :header-rows: 1

   * - Field
     - Type
     - Meaning
   * - ``id`` / ``parent_id``
     - positive integer / optional integer
     - Unique check number within this report and the enclosing candidate whose successor is being validated. IDs are not stable across edits or separate runs. Siblings can be alternative search branches, not a sequential execution path.
   * - ``transition_label``
     - string
     - Existing trace/BMC address ``source_path::index::source->target``. Expanded forced/combo edges use their model addresses. The synthetic root exit has index zero. Editing/reordering the model can change labels.
   * - ``combo_origins``
     - tuple of read-only mappings; JSON array of objects
     - Every authored combo origin represented by this expanded edge; empty for an ordinary edge. Shared prefixes retain multiple origins. Each object has ``origin_id``, ``source_path``, ``target_path``, canonical ``trigger``, zero-based ``term_index``, ``term_text``, ``role`` and ``consumes_term``. Initial sources use ``Owner.[*]``; exit targets use ``[*]``. Import assembly uses final parent paths. Origin IDs distinguish declarations, including identical triggers with different effects; they are not stable across arbitrary model edits.
   * - ``phase``
     - string
     - ``preflight``: whole-cycle precheck; ``execution``: actual selection pass; ``validation``: nested successor checks or search. Only ``committed`` proves final execution.
   * - ``state_path``
     - path tuple; JSON list
     - Source state for this check; owning composite for an initial transition.
   * - ``event`` / ``guard``
     - optional strings
     - Required canonical event / guard expression. ``None`` means that condition is absent, not false.
   * - ``event_result`` / ``guard_result``
     - optional booleans
     - Actual check result. ``None`` means unevaluated. When checked, an absent condition passes with ``True``. Missing events short-circuit guard evaluation.
   * - ``successor_result``
     - optional boolean
     - Aggregate successor-validation result, or ``None`` if validation was not requested. One failed search branch does not make this result false when another continuation succeeds.
   * - ``outcome``
     - string
     - ``event_missing``, ``guard_false``, ``successor_rejected``, ``selected``, ``enabled`` or ``not_evaluated``. ``enabled`` records a search candidate only; ``selected`` records selection in its stated phase.
   * - ``blocked_by``
     - optional check ID
     - Prior successful selection that caused this candidate to remain unevaluated. A prior true guard whose successor failed does not suppress later candidates.
   * - ``committed``
     - boolean
     - True only for a selection in the actual execution pass that survived whole-cycle commit. Always false for Delta and speculative checks.
   * - ``vars`` / ``inputs`` / ``parameters``
     - numeric mappings
     - Detached persistent control/output values at this check, frozen current-cycle inputs and immutable parameters. Use ``roles`` to separate control from output. Local action temporaries are not model variables.
   * - ``location``
     - mapping
     - Available ``line``, ``column``, ``end_line``, ``end_column`` and ``path``. Coordinates are one-based; the end column is exclusive. Synthetic/programmatically constructed edges may have an empty mapping, and parsing without a file loader may omit ``path``.
   * - ``to_dict()``
     - method
     - Independent dictionary for this check alone, using the same field meanings.

.. list-table:: Fields within each ``combo_origins`` entry
   :header-rows: 1

   * - Fields
     - Contract
   * - ``origin_id``
     - String identifying the authored declaration in this assembled model. Multiple entries can share an expanded edge without sharing this ID.
   * - ``source_path`` / ``target_path``
     - Original endpoints expressed in assembled model paths. Initial and exit endpoints use the forms described above; these are not generated relay names.
   * - ``trigger``
     - Complete canonical trigger text assembled from ordered term metadata. Event scope is evidenced by each check's resolved ``event`` field, not a guessed DSL separator.
   * - ``term_index`` / ``term_text``
     - Zero-based integer position and canonical text of the term represented by this edge. Human labels display positions starting at one.
   * - ``role`` / ``consumes_term``
     - Expanded-edge role (currently ``prefix`` or ``terminal``) and a boolean saying whether this edge consumes the referenced trigger term. Neither field alone means the complete authored path committed.

Human text uses the canonical ``Source -> Target [combo: terms]`` display, followed by the observed term and expanded-edge role. This is a semantic display, not round-trippable DSL. Actual event checks show resolved event paths, so event scope is not guessed from the display. Shared expanded edges list all origins without claiming that all those authored alternatives committed. Verbose output and JSON retain the exact expanded address for correlation with trace and BMC.

Human messages distinguish a missing event, a failed guard, a skipped check, local search success, phase-local selection and final commit. ``None`` results are displayed as “not evaluated”; absent conditions as “no requirement”. Parent links describe validation context, not execution order. In particular, a false guard below an accepted candidate can describe one unsuccessful search alternative; it is not automatically the cause of an outer rejection. Only the committed micro-transition list has execution-order meaning.

A rejected candidate's snapshots can contain speculative writes while ``vars_after`` contains the actual committed outcome of another path. There is no separate ``rollback`` event or undo-action log. Delta retains the pre-cycle state and persistent values while advancing the cycle count and input sources. Querying any view is read-only; it cannot undo arbitrary external callback side effects.

The report explains mechanical selection, not counterfactual reachability or arbitrary external handler behavior. Validation deliberately does not execute abstract handlers. An enabled edge is not proof that external code would succeed. No evidence does not mean a guard was false, a source never became active or the model is globally unreachable. ``trace`` continues to contain committed observations only.

CLI contract
------------

.. list-table:: Options and commands
   :header-rows: 1

   * - Form
     - Default / accepted values
     - Behavior and invalid cases
   * - ``--diagnostics``
     - off
     - Enable collection and human summaries for cycle commands. REPL equivalent: ``setting diagnostics on``.
   * - ``--diagnostics-format text|jsonl``
     - ``text``
     - JSONL requires both ``--diagnostics`` and batch ``-e``. Other values, missing prerequisites and disabling diagnostics inside a JSONL batch fail.
   * - ``--param NAME=VALUE``
     - declaration defaults; repeatable
     - Set parameters once at construction. Unknown/non-param names, duplicate names and wrong numeric types fail. ``--param gain=3`` is legal for an integer parameter; ``--param gain=3.5`` is not.
   * - ``cycle [count] [events...] [--input NAME=VALUE ...]``
     - count 1; repeatable input assignments
     - Every actual cycle requires the complete input vector, without zero-fill or implicit hold. ``cycle 5 --input sensor=3`` explicitly repeats that vector. Unknown/missing/duplicate names and wrong numeric types fail. An already ended/error runtime needs no new sample.
   * - ``decisions [--verbose]``
     - latest call
     - Read the latest report. If none exists, print ``No diagnostic report``; do not replay.
   * - ``why <check-id|transition-label> [--verbose]``
     - decimal check number or exact expanded label from completion
     - ``why 3`` selects check 3; ``why Root.A::0::A->B --verbose`` selects all checks of that edge. Include ancestors and blocking selections in either case. Missing selector, extra arguments or repeated ``--verbose`` fail. An unrecorded number/label yields a no-evidence message. Tab completes both numbers and labels; IDs refer only to the latest report.

Use decimal, hexadecimal, binary or floating-point numeric assignments; model types still apply. ``init`` and ``clear`` preserve parameter values, recreate the command-owned input adapter and clear the last report. They do not allow later parameter reassignment. An externally supplied Python input source still requires its owner to construct a fresh runtime when restarting. Failed calls and initialization attempts clear previous diagnostic evidence; disabled collection on the next cycle also clears it. The REPL retains only the latest call; a successful multi-cycle text command displays its collected reports and leaves only its last call queryable. JSONL reports stream after each successful call.

In text mode command transcripts use stdout and logs use stderr. With JSONL, stdout contains exactly one report per normally returned cycle call; command headers, tables, queries and logs use stderr. Reports never contain ANSI escapes. Both ``--no-color`` and the default color setting leave diagnostic text plain. Shell redirection creates files; this feature itself does not save a scenario or replay format. Existing ``export`` writes history, not candidate reports.

Successful batches return 0, including candidate rejections and Delta. Invalid CLI options return Click's nonzero usage status. Parse/construction errors and command/runtime failures return nonzero; a batch stops at its first failed command. Earlier successful JSONL records remain valid if a later call fails. Failed calls do not emit a success report. This changes the former behavior where several command errors printed a message but still exited 0.

For examples of rejected candidates, repeated checks, missing inputs and JSONL validation, see :doc:`../../how_to/simulation/diagnostics`. Source contracts are implemented in ``pyfcstm/simulate/diagnostics.py``, ``runtime.py`` and ``pyfcstm/entry/simulate/``; the public cases are exercised by ``test/simulate/test_decision_diagnostics.py`` and ``test/entry/test_simulate_diagnostics.py``.
