Explain an unselected transition
================================

Use candidate diagnostics when a committed trace shows the path taken but omits the candidates rejected along the way. You need a pyfcstm version exposing ``cycle(diagnostics=True)`` and ``simulate --diagnostics``. The ordinary first-run tutorial remains :doc:`../../tutorials/simulation/index`; exact fields and command boundaries are in :doc:`../../reference/simulation/diagnostics`.

Capture the rejected successor
------------------------------

Download :download:`candidate_failure.fcstm` into an empty directory and run the examples there. This model offers ``A -> Blocked`` before ``A -> B``. Entering ``Blocked`` assigns ``x=100`` but its initial guard requires ``x < 0``.

.. literalinclude:: candidate_failure.fcstm
   :language: fcstm

.. code-block:: console

   $ pyfcstm simulate -i candidate_failure.fcstm \
     --diagnostics --no-color -e 'cycle; cycle Root.A.Go; why Root.A::0::A->Blocked --verbose'
   ...
   >>> cycle Root.A.Go
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Root.B
   Variables:
     x = 1
   ...
   >>> why Root.A::0::A->Blocked --verbose
   ────────────────────────────────────────────────────────────
   Cycle 2: cycle; Root.A -> Root.B
   ...
   #1 Root.A::0::A->Blocked [preflight] successor_rejected: successor validation failed; this candidate's speculative writes were not committed
   ...
       Guard x < 0: failed; values={'x': 100}
   ...

The second call ends in ``Root.B`` with ``x=1``. Its report contains ``successor_rejected`` for the first candidate and a guard check with ``x=100``. ``why`` prints that captured evidence without executing another cycle. No file is written. If it says ``No diagnostic report``, enable collection before reproducing the call; turning it on afterwards cannot recover past evidence.

The equivalent Python program prints the same report and the committed variables:

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_file("candidate_failure.fcstm")
   runtime = SimulationRuntime(model)
   runtime.cycle()
   result = runtime.cycle("Root.A.Go", diagnostics=True)
   print(result.diagnostics)
   print("vars:", dict(runtime.vars))

.. testoutput::

   Cycle 2: cycle; Root.A -> Root.B
   Result: cycle committed.
   Events: Root.A.Go
   Inputs: {}
   Parameters: {}
   Persistent values before: {'x': 0}
   Persistent values after:  {'x': 1}
   Committed micro-transitions (in execution order):
     #6 Root.A::1::A->B
   Candidate evidence (parent links describe validation, not execution order):
   #1 Root.A::0::A->Blocked [preflight] successor_rejected: successor validation failed; this candidate's speculative writes were not committed
     Event Root.A.Go: present
     source=.../candidate_failure.fcstm:11:5
     #2 Root.Blocked::0::INIT_STATE->Inner [validation] guard_false: guard failed; candidate not selected
       Guard x < 0: failed; values={'x': 100}
       Checked while validating candidate #1.
       Values at check (not final values): vars={'x': 100}; inputs={}; parameters={}
       source=.../candidate_failure.fcstm:7:9
   #3 Root.A::1::A->B [preflight] selected: selected in this phase; not committed
     Event Root.A.Go: present
     source=.../candidate_failure.fcstm:12:5
   #4 Root.A::0::A->Blocked [execution] successor_rejected: successor validation failed; this candidate's speculative writes were not committed
     Event Root.A.Go: present
     source=.../candidate_failure.fcstm:11:5
     #5 Root.Blocked::0::INIT_STATE->Inner [validation] guard_false: guard failed; candidate not selected
       Guard x < 0: failed; values={'x': 100}
       Checked while validating candidate #4.
       Values at check (not final values): vars={'x': 100}; inputs={}; parameters={}
       source=.../candidate_failure.fcstm:7:9
   #6 Root.A::1::A->B [execution] selected: committed
     Event Root.A.Go: present
     source=.../candidate_failure.fcstm:12:5
   vars: {'x': 1}

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

Download :download:`combo_diagnostics.fcstm` into the directory of the examples.

.. literalinclude:: combo_diagnostics.fcstm
   :language: fcstm

The program constructs a fresh runtime for each of three cases. All events in ``A + B`` are checked inside the same macro step, using that call's frozen input. It does not mean A on one cycle followed by B on another.

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_file("combo_diagnostics.fcstm")
   cases = [
       ("missing B", 12, ["Root.Start.A"]),
       ("target guard false", 3, ["Root.Start.A", "Root.Start.B"]),
       ("complete path", 12, ["Root.Start.A", "Root.Start.B"]),
   ]
   for title, sensor, events in cases:
       runtime = SimulationRuntime(
           model, parameters={"limit": 10}, input_source={"sensor": sensor}
       )
       runtime.cycle()
       runtime.cycle(events)
       print(title, "->", runtime.configuration, dict(runtime.vars))

.. testoutput::

   missing B -> Root.Fallback {'score': 121, 'reading': 0}
   target guard false -> Root.Fallback {'score': 121, 'reading': 0}
   complete path -> Root.Target.Good {'score': 11011, 'reading': 12}

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

The middle case's full report comes from a second program that runs only that case:

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SimulationRuntime

   model = load_state_machine_from_file("combo_diagnostics.fcstm")
   runtime = SimulationRuntime(
       model, parameters={"limit": 10}, input_source={"sensor": 3}
   )
   runtime.cycle()
   result = runtime.cycle(["Root.Start.A", "Root.Start.B"], diagnostics=True)
   print(result.diagnostics)

.. testoutput::

   Cycle 2: cycle; Root.Start -> Root.Fallback
   Result: cycle committed.
   Events: Root.Start.A, Root.Start.B
   Inputs: {'sensor': 3}
   Parameters: {'limit': 10}
   Persistent values before: {'score': 0, 'reading': 0}
   Persistent values after:  {'score': 121, 'reading': 0}
   Committed micro-transitions (in execution order):
     #8 Root.Start::1::Start->Fallback
   Candidate evidence (parent links describe validation, not execution order):
   #1 Root.Start -> Root.Target [combo: A + B] (term 1: A; prefix) [preflight] successor_rejected: successor validation failed; this candidate's speculative writes were not committed
     Event Root.Start.A: present
     source=.../combo_diagnostics.fcstm:22:5
     #2 Root.Start -> Root.Target [combo: A + B] (term 2: B; terminal) [validation] enabled: local conditions passed during search; not proof of a committed path
       Event Root.Start.B: present
       Checked while validating candidate #1.
       source=.../combo_diagnostics.fcstm:22:5
     #3 Root.Target::0::INIT_STATE->Good [validation] guard_false: guard failed; candidate not selected
       Guard reading >= limit: failed; values={'limit': 10, 'reading': 3}
       Checked while validating candidate #1.
       Values at check (not final values): vars={'score': 10011, 'reading': 3}; inputs={'sensor': 3}; parameters={'limit': 10}
       source=.../combo_diagnostics.fcstm:15:9
   ...
   #8 Root.Start::1::Start->Fallback [execution] selected: committed
   ...

The rejected path computes source exit ``+1``, terminal effect ``+10`` and ``reading=sensor``, then target entry ``+10000``. Its initial guard therefore sees 10011 and 3. Those are values at a speculative check. The fallback commits its own ``+1+20+100`` from the original boundary, yielding 121. Read ``vars_before`` and ``vars_after`` from the report itself; no extra runtime inspection is required to distinguish them from the failed check's snapshot.

There is no separate undo-action log. ``successor_rejected`` and child evidence explain the rejected path; the committed micro-transition list and boundary values show what survived. This does not promise rollback of arbitrary external callback effects. A candidate rollback is not automatically Delta: this example commits a fallback normally.

The default combo display identifies the authored source, target and canonical trigger. It is a readable semantic label, not replacement DSL. Verbose text and ``transition_label`` retain expanded addresses. A shared prefix explicitly lists multiple origins; committing that shared micro-transition does not prove every originating alternative committed. Check the terminal path and final boundary as well.

These programs write no files. If the expected target differs, first check that both fully qualified events were supplied in the same call and that the frozen input meets the target guard. Use ``report.to_text(check_id=3, verbose=True)`` or CLI ``why 3 --verbose`` to query the observed failure with its ancestors; IDs are local to that report. :doc:`../../reference/simulation/diagnostics` defines the selectors and fields.

Distinguish Delta from a normal stay-in-place cycle
---------------------------------------------------

Download :download:`delta_diagnostics.fcstm` into the directory of the examples.

.. literalinclude:: delta_diagnostics.fcstm
   :language: fcstm

The first frozen input is 3. The initial route computes ``score=110`` and ``reading=3`` but cannot leave the pseudo state for a stoppable state. The call returns Delta, retaining the original root boundary and zero persistent values; the committed trace is empty. The second input is 12, so initialization completes with ``score=1110`` and ``reading=12``. The first attempt's 110 is not accumulated.

.. testcode::

   from pyfcstm.model import load_state_machine_from_file
   from pyfcstm.simulate import SequenceInput, SimulationRuntime

   model = load_state_machine_from_file("delta_diagnostics.fcstm")
   runtime = SimulationRuntime(
       model, parameters={"limit": 10},
       input_source={"sensor": SequenceInput([3, 12])},
   )
   for _ in range(2):
       result = runtime.cycle(diagnostics=True)
       print(result.diagnostics)
       print("delta:", result.delta, dict(runtime.vars))

.. testoutput::

   Cycle 1 completed as Delta - State: Root; no stoppable successor was committed
   Cycle 1: delta; Root -> Root
   Result: no stoppable successor committed; state and persistent values unchanged; cycle and inputs advanced.
   Events: (none processed)
   Inputs: {'sensor': 3}
   Parameters: {'limit': 10}
   Persistent values before: {'score': 0, 'reading': 0}
   Persistent values after:  {'score': 0, 'reading': 0}
   Committed micro-transitions: (none)
   Candidate evidence (parent links describe validation, not execution order):
   #1 Root::0::INIT_STATE->Prepare [preflight] successor_rejected: successor validation failed; this candidate's speculative writes were not committed
     source=.../delta_diagnostics.fcstm:14:5
     #2 Root.Prepare::0::Prepare->Ready [validation] guard_false: guard failed; candidate not selected
       Guard reading >= limit: failed; values={'limit': 10, 'reading': 3}
       Checked while validating candidate #1.
       Values at check (not final values): vars={'score': 110, 'reading': 3}; inputs={'sensor': 3}; parameters={'limit': 10}
       source=.../delta_diagnostics.fcstm:15:5
   ...
   delta: True {'score': 0, 'reading': 0}
   Cycle 2: cycle; Root -> Root.Ready
   Result: cycle committed.
   Events: (none processed)
   Inputs: {'sensor': 12}
   Parameters: {'limit': 10}
   Persistent values before: {'score': 0, 'reading': 0}
   Persistent values after:  {'score': 1110, 'reading': 12}
   Committed micro-transitions (in execution order):
     #4 Root::0::INIT_STATE->Prepare
     #6 Root.Prepare::0::Prepare->Ready
   ...
   delta: False {'score': 1110, 'reading': 12}

A Delta warning is also logged to stderr, which is the first line of the output above. The program writes no files. Delta advances the cycle counter, history and input source; it does not rewind the environment. If the second call still fails, inspect the sequence and guard values rather than expecting the first sample to be reused. A normal stoppable leaf can stay active, run ``during`` and change outputs while ``decisions`` is empty; that is a normal cycle, and its report still contains inputs, parameters and both boundary snapshots. Ignored calls instead have ``inputs=None`` because no new sampling occurred.

When the same pseudo edge executes repeatedly within one macro step, each committed occurrence remains visible, even if its label repeats. Compact text folds only adjacent uncommitted checks whose evidence is identical apart from ID, retaining every ID and the count. Different variable values or validation parents are distinct facts. Verbose text and JSON always retain every original check. For the relationship to whole-path guard constraints, see :ref:`exec-diagnostic-boundaries`.

Provide inputs and parameters
-----------------------------

Write this separate model to ``sensor_gain.fcstm`` (it is not the ``controller.fcstm`` downloaded on other pages) and run it with an input vector and a parameter:

.. testcode::

   from pathlib import Path

   Path("sensor_gain.fcstm").write_text("""\
   input int sensor;
   param int gain = 2;
   output int reading = 0;
   state Controller {
       state Running { during { reading = sensor * gain; } }
       state High;
       [*] -> Running;
       Running -> High : if [sensor > 10];
   }
   """)

.. code-block:: console

   $ pyfcstm simulate -i sensor_gain.fcstm --param gain=3 --diagnostics --no-color \
     -e 'cycle --input sensor=4; cycle --input sensor=12; decisions'
   ...
   >>> cycle --input sensor=4
   ────────────────────────────────────────────────────────────
   Cycle: 1
   Current State: Controller.Running
   Variables:
     reading = 12
   ...
   >>> cycle --input sensor=12
   ────────────────────────────────────────────────────────────
   Cycle: 2
   Current State: Controller.High
   Variables:
     reading = 12
   ...
   >>> decisions
   ────────────────────────────────────────────────────────────
   ...
   Inputs: {'sensor': 12}
   Parameters: {'gain': 3}
   ...
     Guard sensor > 10: passed; values={'sensor': 12}
   ...

The first cycle sets ``reading=12``. The next call selects ``Running -> High`` with captured ``sensor=12`` and ``gain=3``; the latched output remains 12. There are no file side effects. A real input must be supplied on every actual cycle; ``cycle`` without ``--input sensor=...`` fails with ``E_INPUT_SOURCE_CONTRACT``. Repair the vector rather than expecting the previous value to persist. ``cycle 5 --input sensor=4`` explicitly repeats the vector five times. Parameters are construction-time values and cannot be changed by ``init`` or ``cycle``.

For custom generators or sensor callbacks, use the existing Python :doc:`input sources <../../reference/simulation/inputs>`. Diagnostics use the frozen vector and do not resample it. Imported inputs mapped onto parent controls/outputs are reported according to their final parent roles.

Collect machine-readable reports
--------------------------------

.. code-block:: console

   $ pyfcstm simulate -i candidate_failure.fcstm \
     --diagnostics --diagnostics-format jsonl --no-color \
     -e 'cycle; cycle Root.A.Go' > decisions.jsonl
   ...

.. testcode::

   import json

   with open("decisions.jsonl") as stream:
       rows = [json.loads(line) for line in stream]
   print(len(rows), rows[1]["state_after"])

.. testoutput::

   2 ['Root', 'B']

The script reads two reports, the second ending in ``Root.B``. The shell creates or overwrites ``decisions.jsonl``; it contains no command headers or ANSI escapes. Human transcripts and logs appear on stderr. Each report is produced by the same ``to_dict()`` used in Python. A rejected candidate is a normal successful run; a later invalid command stops the batch with a nonzero status, preserving earlier complete records.

If JSON parsing fails, first check that both ``--diagnostics`` and ``--diagnostics-format jsonl`` were supplied, and avoid combining stderr into the file. JSONL requires batch mode; REPL queries are human-readable. There is no automatic scenario loading, persistence or replay added here. Keep the model and experimental conditions in your own script when comparing separate runs.

In the REPL, ``setting diagnostics on``, ``cycle``, ``decisions`` and ``why <id|label>`` provide the same workflow; Tab completes captured check numbers and labels. Only the latest call is retained. A new failed call, ``init`` or ``clear`` removes the previous report, so a stale explanation cannot appear to describe the new state.
