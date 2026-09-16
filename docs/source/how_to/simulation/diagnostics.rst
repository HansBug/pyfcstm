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
   * - Repeated summaries are folded
     - The engine checked some edges multiple times. Use ``report.to_text(verbose=True)`` or ``decisions --verbose`` to see each check and its parent.

A false guard on one search branch does not prove that the entire candidate fails. Read the outer candidate's ``successor_result`` together with the child evidence. Likewise, ``not_evaluated`` with ``blocked_by`` means an earlier candidate was selected; it does not mean the later guard is false. A normal leaf can stay in place without producing Delta. These distinctions explain why the report records real checks rather than reevaluating conditions from final values.

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

In the REPL, ``setting diagnostics on``, ``cycle``, ``decisions`` and ``why <label>`` provide the same workflow; Tab completes captured labels. Only the latest call is retained. A new failed call, ``init`` or ``clear`` removes the previous report, so a stale explanation cannot appear to describe the new state.
