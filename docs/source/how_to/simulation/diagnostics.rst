Explain an unselected transition
================================

Use candidate diagnostics when a committed trace shows the path taken but omits the candidates rejected along the way. You need a pyfcstm version exposing ``cycle(diagnostics=True)`` and ``simulate --diagnostics``. The ordinary first-run tutorial remains :doc:`../../tutorials/simulation/index`; exact fields and command boundaries are in :doc:`../../reference/simulation/diagnostics`.

Capture the rejected successor
------------------------------

Run from the repository root, or download :download:`candidate_failure.fcstm` and adjust the path. This model offers ``A -> Blocked`` before ``A -> B``. Entering ``Blocked`` assigns ``x=100`` but its initial guard requires ``x < 0``.

.. literalinclude:: candidate_failure.fcstm
   :language: fcstm

.. code-block:: bash

   pyfcstm simulate -i docs/source/how_to/simulation/candidate_failure.fcstm \
     --diagnostics --no-color -e 'cycle; cycle Root.A.Go; why Root.A::0::A->Blocked --verbose'

The second call ends in ``Root.B`` with ``x=1``. Its report contains ``successor_rejected`` for the first candidate and a guard check with ``x=100``. ``why`` prints that captured evidence without executing another cycle. No file is written. If it says ``No diagnostic report``, enable collection before reproducing the call; turning it on afterwards cannot recover past evidence.

The equivalent Python program is executable as-is from the checkout:

.. code-block:: bash

   python docs/source/how_to/simulation/candidate_diagnostics.demo.py

.. literalinclude:: candidate_diagnostics.demo.py
   :language: python
   :start-at: from pathlib

Its complete compact report is:

.. literalinclude:: candidate_diagnostics.demo.py.txt
   :language: text

Read the evidence in this order:

.. list-table:: What this report proves
   :header-rows: 1

   * - Observation
     - Meaning
   * - ``A -> Blocked`` has ``successor_rejected``
     - Matching its event was insufficient; the continuation could not stabilize.
   * - Initial guard sees ``x=100``
     - This is a speculative entry value, not the final committed value.
   * - ``A -> B`` is ``selected`` in preflight
     - Whole-cycle checking found a viable selection. It has not yet committed.
   * - ``A -> B`` has ``committed`` in execution
     - This actual selection survived the cycle. Its transition is also in the committed trace.
   * - Identical adjacent checks are folded
     - Only identical uncommitted evidence folds; IDs and counts stay visible. Use ``report.to_text(verbose=True)`` or ``decisions --verbose`` to see each check and its parent.

A false guard on one search branch does not prove that the entire candidate fails. Read the outer candidate's ``successor_result`` together with the child evidence. Likewise, ``not_evaluated`` with ``blocked_by`` means an earlier candidate was selected; it does not mean the later guard is false. A normal leaf can stay in place without producing Delta. These distinctions explain why the report records real checks rather than reevaluating conditions from final values.

Inspect combo rollback and fallback
-----------------------------------

Download :download:`combo_diagnostics.fcstm` and :download:`combo_diagnostics.demo.py` into the same directory, or run the checked-in program from the repository root:

.. code-block:: bash

   python docs/source/how_to/simulation/combo_diagnostics.demo.py

.. literalinclude:: combo_diagnostics.fcstm
   :language: fcstm

The program constructs a fresh runtime for each of three cases. All events in ``A + B`` are checked inside the same macro step, using that call's frozen input. It does not mean A on one cycle followed by B on another.

.. literalinclude:: combo_diagnostics.demo.py
   :language: python
   :start-at: from pathlib

.. list-table:: Expected committed boundaries
   :header-rows: 1

   * - Input and events
     - Evidence
     - Final boundary
   * - ``sensor=12``, A only
     - B is missing; the target guard is not evaluated.
     - ``Root.Fallback``; ``score=121``, ``reading=0``.
   * - ``sensor=3``, A and B
     - Target initial guard fails with speculative ``score=10011``, ``reading=3``.
     - ``Root.Fallback``; ``score=121``, ``reading=0``.
   * - ``sensor=12``, A and B
     - Whole path succeeds; the fallback is not evaluated.
     - ``Root.Target.Good``; ``score=11011``, ``reading=12``.

The middle case's actual output is shown below; the other two cases are omitted here and are printed by the same program:

.. literalinclude:: combo_diagnostics.demo.py.txt
   :language: text
   :start-after: === target guard false ===
   :end-before: === complete path ===

The rejected path computes source exit ``+1``, terminal effect ``+10`` and ``reading=sensor``, then target entry ``+10000``. Its initial guard therefore sees 10011 and 3. Those are values at a speculative check. The fallback commits its own ``+1+20+100`` from the original boundary, yielding 121. Read ``vars_before`` and ``vars_after`` from the report itself; no extra runtime inspection is required to distinguish them from the failed check's snapshot.

There is no separate undo-action log. ``successor_rejected`` and child evidence explain the rejected path; the committed micro-transition list and boundary values show what survived. This does not promise rollback of arbitrary external callback effects. A candidate rollback is not automatically Delta: this example commits a fallback normally.

The default combo display identifies the authored source, target and canonical trigger. It is a readable semantic label, not replacement DSL. Verbose text and ``transition_label`` retain expanded addresses. A shared prefix explicitly lists multiple origins; committing that shared micro-transition does not prove every originating alternative committed. Check the terminal path and final boundary as well.

No files are written by this program. If the expected target differs, first check that both fully qualified events were supplied in the same call and that the frozen input meets the target guard. Use ``report.to_text(check_id=3, verbose=True)`` or CLI ``why 3 --verbose`` to query the observed failure with its ancestors; IDs are local to that report. :doc:`../../reference/simulation/diagnostics` defines the selectors and fields.

Distinguish Delta from a normal stay-in-place cycle
---------------------------------------------------

Download :download:`delta_diagnostics.fcstm` and :download:`delta_diagnostics.demo.py` together, or run:

.. code-block:: bash

   python docs/source/how_to/simulation/delta_diagnostics.demo.py

.. literalinclude:: delta_diagnostics.fcstm
   :language: fcstm

.. literalinclude:: delta_diagnostics.demo.py
   :language: python
   :start-at: from pathlib

The first frozen input is 3. The initial route computes ``score=110`` and ``reading=3`` but cannot leave the pseudo state for a stoppable state. The call returns Delta, retaining the original root boundary and zero persistent values; the committed trace is empty. The second input is 12, so initialization completes with ``score=1110`` and ``reading=12``. The first attempt's 110 is not accumulated.

.. literalinclude:: delta_diagnostics.demo.py.txt
   :language: text

A Delta warning is also logged to stderr. The program writes no files. Delta advances the cycle counter, history and input source; it does not rewind the environment. If the second call still fails, inspect the sequence and guard values rather than expecting the first sample to be reused. A normal stoppable leaf can stay active, run ``during`` and change outputs while ``decisions`` is empty; that is a normal cycle, and its report still contains inputs, parameters and both boundary snapshots. Ignored calls instead have ``inputs=None`` because no new sampling occurred.

When the same pseudo edge executes repeatedly within one macro step, each committed occurrence remains visible, even if its label repeats. Compact text folds only adjacent uncommitted checks whose evidence is identical apart from ID, retaining every ID and the count. Different variable values or validation parents are distinct facts. Verbose text and JSON always retain every original check. For the relationship to whole-path guard constraints, see :ref:`exec-diagnostic-boundaries`.

Provide inputs and parameters
-----------------------------

Save this separate model as ``controller.fcstm``:

.. code-block:: fcstm

   input int sensor;
   param int gain = 2;
   output int reading = 0;
   state Controller {
       state Running { during { reading = sensor * gain; } }
       state High;
       [*] -> Running;
       Running -> High : if [sensor > 10];
   }

.. code-block:: bash

   pyfcstm simulate -i controller.fcstm --param gain=3 --diagnostics --no-color \
     -e 'cycle --input sensor=4; cycle --input sensor=12; decisions'

The first cycle sets ``reading=12``. The next call selects ``Running -> High`` with captured ``sensor=12`` and ``gain=3``; the latched output remains 12. There are no file side effects. A real input must be supplied on every actual cycle; ``cycle`` without ``--input sensor=...`` fails with ``E_INPUT_SOURCE_CONTRACT``. Repair the vector rather than expecting the previous value to persist. ``cycle 5 --input sensor=4`` explicitly repeats the vector five times. Parameters are construction-time values and cannot be changed by ``init`` or ``cycle``.

For custom generators or sensor callbacks, use the existing Python :doc:`input sources <../../reference/simulation/inputs>`. Diagnostics use the frozen vector and do not resample it. Imported inputs mapped onto parent controls/outputs are reported according to their final parent roles.

Collect machine-readable reports
--------------------------------

.. code-block:: bash

   pyfcstm simulate -i docs/source/how_to/simulation/candidate_failure.fcstm \
     --diagnostics --diagnostics-format jsonl --no-color \
     -e 'cycle; cycle Root.A.Go' > decisions.jsonl
   python -c 'import json; rows=[json.loads(s) for s in open("decisions.jsonl")]; assert len(rows)==2; assert rows[1]["state_after"]==["Root","B"]; print("2 valid reports")'

Expected output from the second command is ``2 valid reports``. The shell creates or overwrites ``decisions.jsonl``; it contains no command headers or ANSI escapes. Human transcripts and logs appear on stderr. Each report is produced by the same ``to_dict()`` used in Python. A rejected candidate is a normal successful run; a later invalid command stops the batch with a nonzero status, preserving earlier complete records.

If JSON parsing fails, first check that both ``--diagnostics`` and ``--diagnostics-format jsonl`` were supplied, and avoid combining stderr into the file. JSONL requires batch mode; REPL queries are human-readable. There is no automatic scenario loading, persistence or replay added here. Keep the model and experimental conditions in your own script when comparing separate runs.

In the REPL, ``setting diagnostics on``, ``cycle``, ``decisions`` and ``why <id|label>`` provide the same workflow; Tab completes captured check numbers and labels. Only the latest call is retained. A new failed call, ``init`` or ``clear`` removes the previous report, so a stale explanation cannot appear to describe the new state.
