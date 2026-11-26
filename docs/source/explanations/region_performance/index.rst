What regions cost in models, simulation and generated runtimes
==============================================================

A region lets one owner state run several ordered sub-machines in the same
cycle.  This page answers three questions that a modeler asks before choosing
regions: how much smaller is the model than the flat machine you would write
without them, how much does one cycle cost in the simulator and in generated
code, and how large can a model grow before it stops being practical.  It
reports exact counts where they can be derived, fitted curves where only a
curve can be given, and measurements where only a measurement exists, and it
marks which is which.  For the meaning of the execution order itself, read
:doc:`/explanations/region_semantics/index`; for the syntax, read
:doc:`/reference/region_model/index`.

Short answers
-------------

* **Model size.**  For regions that do not read each other, the region form
  has :math:`\sum S` leaf states and the flat machine has :math:`\prod S`.
  This is exact and is checked on 20 small models.  The saving is in the model,
  not in the time per cycle: in the simulator the flat machine was faster on
  17 of the 20 checked models and slower only where it has 3840 or more
  transitions.
* **Simulator.**  Time per cycle is dominated by the number of regions
  :math:`R`; the fit is quadratic with a small second-order term.  It does not
  depend on the states per region :math:`S`, grows slowly with the transitions
  per state :math:`T`, and is linear in the variables written :math:`V`.
  Nesting :math:`D` levels costs about :math:`D` times one level; the memo of
  the simulator keeps the first entry polynomial.
* **Generated Python.**  The generated runtime was 2.6 to 8.4 times faster than
  the simulator on the same models (median 5.0).  It is still far from what a
  hand-written specialisation would do (see the :ref:`known gap <region-perf-python>`).
* **Generated C.**  Time per cycle grows faster than linearly in :math:`R`
  (log-log slope 1.43 over :math:`R = 1..64`), the size of one machine grows
  almost quadratically (slope 1.9 between :math:`R = 16` and :math:`R = 64`),
  and the first cycle that enters nested owners grows by a factor of about 2.2
  per level.  The capacity macros are exact functions of the model size.

How to read the numbers
-----------------------

Every statement below carries one of three labels.

.. list-table::
   :header-rows: 1
   :widths: 16 34 50

   * - Label
     - What it means
     - How to check it
   * - Exact
     - A formula derived from the definition, under stated assumptions.
     - Substitute small parameters and compare with the counts the tool prints.
       The page includes a script that does this on the public API.
   * - Fit
     - A least-squares curve through measured points, with its range and
       :math:`R^2`.  It describes the range that was measured and nothing else.
     - Re-fit :file:`data/e2.jsonl` and the other data files with
       ``python tools/measure_region_performance.py fit``.
   * - Measured
     - One number from one machine, one commit and one repeat count.
     - Rerun the tool.  Expect different absolute numbers on other hardware.

All measurements come from commit ``b054fbe3`` on an Intel Xeon Platinum 8581C
at 2.1 GHz with Python 3.11.15 and gcc 13.3.0 (``-O2 -std=c99``).  The machine
is shared with other users.  Simulator and Python figures are the median of 7
timed batches after a warm-up; C figures are the minimum of 7 runs; each
process is pinned to one core.  The same model, ``R=4 S=8 T=2 D=1 V=1``, was
measured once in each sweep, which gives a noise estimate: the simulator
values differ by 7 %, the generated Python values by 2 % and the C values by
16 %.  Differences smaller than that are not findings.  The models are
synthetic, built by ``sweep_model`` in the tool; they are not a sample of real
projects.

Symbols
-------

.. list-table::
   :header-rows: 1
   :widths: 14 86

   * - Symbol
     - Meaning
   * - :math:`R`
     - Number of regions of one owner
   * - :math:`S`
     - Number of states of each region
   * - :math:`T`
     - Number of transitions of each state
   * - :math:`D`
     - Number of nested owner levels
   * - :math:`V`
     - Number of variables written by each transition
   * - :math:`k`
     - Step bound of bounded model checking (used on :doc:`/explanations/bmc_scaling/index`)
   * - :math:`N`
     - Number of leaf states of a machine without regions
   * - :math:`W`
     - Number of transitions with assignments (used on the bounded model checking pages)
   * - :math:`Q_{\mathrm{reg}}`, :math:`Q_{\mathrm{flat}}`
     - Leaf states of the region form and of the flat expansion
   * - :math:`M_{\mathrm{reg}}`, :math:`M_{\mathrm{flat}}`
     - Ordinary transitions (not counting initial transitions) of the two forms
   * - :math:`P`
     - Number of scopes of a model: all states, owners and root included, plus all regions

The flat expansion is an ordinary machine, so :math:`N = Q_{\mathrm{flat}}`
whenever the two are compared.

Model size: regions against the flat expansion
----------------------------------------------

The counts (exact)
~~~~~~~~~~~~~~~~~~

Take one owner with :math:`R` regions.  Region :math:`i` has :math:`S_i`
leaf states and every state of it has :math:`T_i` outgoing transitions.  The
transitions of one region are guarded by values that only that region reads,
and the guards of one state exclude each other.  Under these assumptions
(called independent regions here) the two forms have these sizes.

.. math::
   :label: region-perf-states

   Q_{\mathrm{reg}} = \sum_{i=1}^{R} S_i,
   \qquad
   Q_{\mathrm{flat}} = \prod_{i=1}^{R} S_i

.. math::
   :label: region-perf-transitions

   M_{\mathrm{reg}} = \sum_{i=1}^{R} S_i T_i,
   \qquad
   M_{\mathrm{flat}} = \Bigl(\prod_{i=1}^{R} S_i\Bigr)\Bigl(\prod_{i=1}^{R} (T_i + 1) - 1\Bigr)

The first line counts the states of every region once, and a flat machine needs
one state per tuple of region states.  In the second line, one cycle of the
region form lets every region either fire one of its :math:`T_i` transitions
or stay and run its ``during`` action, so a flat state needs one transition
for each of the :math:`\prod (T_i + 1)` outcomes.  The outcome in which every
region stays is the ``during`` of the flat state, not a transition, hence the
:math:`-1`.  With :math:`S_i = S` and :math:`T_i = T` the formulas become the
following.

.. math::
   :label: region-perf-uniform

   \frac{Q_{\mathrm{flat}}}{Q_{\mathrm{reg}}} = \frac{S^{R}}{R\,S},
   \qquad
   \frac{M_{\mathrm{flat}}}{M_{\mathrm{reg}}} = \frac{S^{R-1}\bigl((T+1)^{R} - 1\bigr)}{R\,T}

For :math:`R = 4`, :math:`S = 4` and :math:`T = 2`, equation
:eq:`region-perf-states` gives 16 and 256 leaf states and equation
:eq:`region-perf-transitions` gives 32 and 20480 transitions.  The
figure shows the same growth on a logarithmic axis.

.. figure:: fig_model_size_en.plot.py.svg
   :alt: Leaf states and transitions of the region form and of the flat expansion against the number of regions
   :align: center
   :width: 96%

   Leaf states (left) and transitions (right) for :math:`T = 1` and
   :math:`S = 2, 3, 4`.  Markers are counts read from the models that the tool
   generated; solid lines are :math:`R\,S` and :math:`R\,S\,T`, dashed lines are
   :math:`S^R` and :math:`S^R(2^R-1)`.  The y axis is logarithmic.  The figure
   proves that the region form grows linearly while the flat form grows
   exponentially under the stated assumptions; it proves nothing about regions
   that read each other.  Source: :file:`data/e1.jsonl`; counts are exact, no
   repeats are involved.

Checking the counts and the equivalence
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The script below loads a region model and its flat expansion for
:math:`R = 2`, :math:`S = 3`, :math:`T = 1` through the public API, counts
leaf states and ordinary transitions, and runs both on the same 200 random
input vectors.

.. literalinclude:: size_and_equivalence.demo.py
   :language: python
   :caption: size_and_equivalence.demo.py

.. literalinclude:: size_and_equivalence.demo.py.txt
   :language: text
   :caption: size_and_equivalence.demo.py.txt

The two counts are 6 and 9 leaf states and 6 and 27 transitions, which equals
the formulas: :math:`2 \cdot 3 = 6`, :math:`3^2 = 9`, :math:`2 \cdot 3 \cdot 1 = 6` and :math:`3^2 (2^2 - 1) = 27`.  The variables ``c0``, ``u0``, ``c1`` and
``u1`` agree after every one of the 200 cycles.  This shows agreement on one
random sequence for one model; the full grid is in the next listing.

The two models are :file:`product_r2_s3.fcstm` (region form) and
:file:`expanded_r2_s3.fcstm` (flat form); the first is shown in full and the
second as its first 19 lines, which hold the nine states and the first
transitions.

.. literalinclude:: product_r2_s3.fcstm
   :language: fcstm
   :caption: product_r2_s3.fcstm

.. literalinclude:: expanded_r2_s3.fcstm
   :language: fcstm
   :caption: expanded_r2_s3.fcstm (first 19 lines of 45)
   :lines: 1-19

.. literalinclude:: summary_model_size.demo.py.txt
   :language: text
   :caption: summary_model_size.demo.py.txt (complete)

All 20 grid points match the formulas, and all 20 pairs gave the same
variables after every cycle on 5 random sequences of 200 cycles each.  The
last two columns show the cost: **the region form is not faster per cycle than
the flat form until the flat form has thousands of transitions.**  At
:math:`R = 2`, :math:`S = 3`, :math:`T = 1` the region form takes 0.32 ms and
the flat form 0.19 ms; at :math:`R = 4`, :math:`S = 4`, :math:`T = 1` (3840
flat transitions) the order flips, 0.66 ms against 1.59 ms, and at
:math:`R = 4`, :math:`S = 4`, :math:`T = 2` (20480 flat transitions) it is 0.78
ms against 8.06 ms.  The flat form has to test :math:`\prod (T_i+1) - 1` transitions per state and
the region form carries overhead per region (inference from the counts; the
simulator was not profiled for this comparison).  Nobody writes a 20480-transition machine by hand, which
is the practical meaning of the size saving.

When the regions read each other
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Equations :eq:`region-perf-states` to :eq:`region-perf-uniform` need
independent regions.  If a later region reads a variable that an earlier
region writes in the same cycle, the later region sees the new value, and a
flat machine whose guards are evaluated at the start of the cycle does not
reproduce that.  The next script uses four small models: region ``W`` writes
``p = x0`` in its ``during`` action, region ``V`` switches on ``p``, and the
two region forms differ in which region is written first.  The flat forms are
the naive expansion (the guard reads ``p``) and the expansion with the
guard rewritten to read ``x0``, which is what ``W`` writes.

.. literalinclude:: ordered_read.demo.py.txt
   :language: text
   :caption: ordered_read.demo.py.txt

Read the output this way.

* ``regions_reader_after_writer`` and ``flat_naive`` differ in 97 of 200
  cycles: the naive flat machine is one cycle late, because its guard reads the
  value of ``p`` from the previous cycle.
* ``regions_reader_before_writer`` equals ``flat_naive`` in all 200 cycles:
  when the reader is declared before the writer, it also reads the old value,
  and no rewriting is needed.
* ``flat_substituted`` equals ``regions_reader_after_writer`` in all 200
  cycles: replacing ``p`` in the guard by what ``W`` assigns restores
  equivalence.  The data file records the same on 1000 cycles (600 differing
  cycles for the two inequivalent pairs, 0 for the two equal pairs).

The conclusion is limited.  A flat expansion exists for this pair, and the
guard stays small because ``W`` assigns a single input.  What the experiment
does not show is how large the rewritten guards become when the writer
computes a long expression or when several regions form a chain of readers;
the tool does not measure that, and the size would grow with the substituted
expressions (inference, not measured).  The models are in
:file:`coupled_regions_reader_after_writer.fcstm`,
:file:`coupled_regions_reader_before_writer.fcstm`,
:file:`coupled_flat_naive.fcstm` and :file:`coupled_flat_substituted.fcstm`.

Simulator cost per cycle
------------------------

What was measured
~~~~~~~~~~~~~~~~~

The tool generates one family of models (``sweep_model``): ``D`` nested owners,
every owner has ``R`` regions, a ring region has ``S`` states, each state has
``T`` outgoing transitions guarded by ``a == 1`` to ``a == T`` and every
transition writes ``V`` variables.  One parameter changes at a time around the
base ``R=4 S=8 T=2 D=1 V=1``.  The input ``a`` follows a fixed pseudo-random
sequence, so about :math:`T/(T+1)` of the cycles fire a transition.  The
simulator runs with ``history_size=1`` so that the history does not grow.  The
small model below shows the shape; :file:`sweep_r2_s3_t1.fcstm` is
``R=2 S=3 T=1 D=1 V=1``.

.. literalinclude:: sweep_r2_s3_t1.fcstm
   :language: fcstm
   :caption: sweep_r2_s3_t1.fcstm

.. literalinclude:: summary_simulator.demo.py.txt
   :language: text
   :caption: summary_simulator.demo.py.txt (complete)

Fits
~~~~

.. figure:: fig_sim_sweeps_en.plot.py.svg
   :alt: Simulator time per cycle against R, S, T and V with fitted curves
   :align: center
   :width: 100%

   Median time per cycle of ``SimulationRuntime.cycle`` against :math:`R`,
   :math:`S`, :math:`T` and :math:`V`.  Axes are linear and start at zero;
   dashed lines are the fits named in each title.  Each point is the median of 7
   batches of at least 20 cycles after 50 warm-up cycles.  The figure proves
   that :math:`S` has almost no effect (the points stay within 0.62 to 0.74 ms
   over a 43-fold change) while :math:`R` and :math:`V` do.  Source:
   :file:`data/e2.jsonl`.

The fits in equation :eq:`region-perf-sim-fit` are Fit statements and hold
for the measured ranges, :math:`R = 1..128` and :math:`V = 1..64`, at the base
model.

.. math::
   :label: region-perf-sim-fit

   t_{\mathrm{sim}}(R) \approx 96 + 126\,R + 1.71\,R^{2}\ \mu\mathrm{s}
   \quad (R^2 = 0.9999),
   \qquad
   t_{\mathrm{sim}}(V) \approx 664 + 21.3\,V\ \mu\mathrm{s}
   \quad (R^2 = 0.990)

Read these as follows.

* The first term shows a per-region cost of about 126 µs at small
  :math:`R`, and the quadratic term adds 1.71 µs per region squared; at
  :math:`R = 128` the quadratic part is 28 ms of the measured 44 ms.  A purely
  linear fit has :math:`R^2 = 0.971` and misses the curvature.
* The quadratic term is measured; the cause is not.  The memoisation key of the
  simulator is built from the whole configuration, so a larger configuration
  makes every check more expensive (inference from reading
  :file:`pyfcstm/simulate/runtime.py`; it was not profiled).
* The per-transition effect :math:`T` is small: 33 µs per additional
  transition per state, linear :math:`R^2 = 0.886`, so treat it as "weak" and
  not as a rate.
* The two forms of growth can be added in a rough estimate, but the tool varies
  one parameter at a time, so interactions (for example :math:`R` and :math:`V`
  together) are not measured.

Nesting depth and memoisation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simulator entering a chain of nested owners decides at every level whether
a candidate can reach a stable position, and an enclosing level asks the same
question again.  The simulator remembers each answer for the rest of the cycle
(``_memo_get`` and ``_memo_put`` in :file:`pyfcstm/simulate/runtime.py`), so
the question is paid for once.  The claim to test is that nesting does not make
the first entry exponential.

.. figure:: fig_depth_en.plot.py.svg
   :alt: Simulator time per cycle and first-cycle time against the number of nested owner levels
   :align: center
   :width: 96%

   Left: steady time per cycle against :math:`D`.  Right: time of the first cycle
   (the cycle that enters every owner) against :math:`D`.  Both y axes are
   logarithmic.  ``R=1`` is a pure chain of owners; ``R=2`` has a nested region
   and a ring region at every level.  Steady: median of 7 batches; first cycle:
   minimum of 5 fresh runtimes.  The figure proves that the first entry grows
   polynomially in this family: from :math:`D = 1` to :math:`D = 12` the chain's
   first cycle grows from 340 µs to 7.2 ms, a factor of 21, while the
   exponential alternative would be a factor of about 2000.  Source:
   :file:`data/e2.jsonl`.

The steady time fits :math:`174 + 40\,D + 1.85\,D^{2}` µs for the chain
(:math:`R^2 = 0.998`, :math:`D = 1..12`).  The data support "memoisation keeps
the first entry polynomial in this family"; they do not show that no model can
make it exponential.

.. _region-perf-python:

Generated Python runtime
------------------------

This experiment generates the Python runtime of every
sweep model with ``pyfcstm generate --template python`` and times
``cycle(inputs=...)`` on the same input sequence.

.. literalinclude:: summary_python.demo.py.txt
   :language: text
   :caption: summary_python.demo.py.txt (complete)

.. figure:: fig_python_vs_simulator_en.plot.py.svg
   :alt: Generated Python and simulator time per cycle on the same sweeps
   :align: center
   :width: 100%

   Time per cycle of the simulator and of the generated Python runtime on the
   same models.  The y axis is logarithmic; :math:`R`, :math:`S` and :math:`V`
   are on logarithmic x axes.  Medians of 7 batches.  The figure proves that
   the generated runtime has the same shape as the simulator and is faster by a
   roughly constant factor, with the factor shrinking from 5.8 to 2.6 as
   :math:`R` grows from 1 to 128.  Source: :file:`data/e2.jsonl` and
   :file:`data/e3.jsonl`.

* The generated runtime is faster in all 47 points (2.6 to 8.4 times, median
  5.0) and its variables equal the simulator's after 1024 cycles in all 47.
* The quadratic term is smaller than the simulator's but present:
  :math:`58 + 15.5\,R + 0.918\,R^{2}` µs (:math:`R^2 = 1.000`, :math:`R = 1..128`).
* The generated ``machine.py`` grows with the model: 137 KB at :math:`R = 1`,
  3.6 MB at :math:`R = 64` and 7.1 MB at :math:`R = 128`, and importing it takes
  15 ms, 341 ms and 913 ms.  A model with hundreds of regions is therefore a
  deployment cost before it is a cycle cost.
* Nesting is cheap here: the chain's first cycle is 86 µs at :math:`D = 1` and
  1.75 ms at :math:`D = 12`.

The known gap is `issue #596 <https://github.com/HansBug/pyfcstm/issues/596>`_:
the generated module still carries a general frame-stack interpreter and the
two-stage "try on a copy, then run" structure.  The issue reports a
hand-written specialisation of the six-state ring that it profiles at about
2.98 million cycles per second, against about 11 thousand for the template on
that ring; those figures come from the issue and were not remeasured here.  The numbers on this
page therefore describe today's generator and will improve when the issue is
addressed.

Generated C runtime
-------------------

Time per cycle
~~~~~~~~~~~~~~

The C measurements use the same models, ``gcc -O2 -std=c99``, one pinned core,
the minimum of 7 runs of 2000 or more cycles (the driver picks the count so
that a run lasts about 0.25 s), and the same input sequence from a table in the
driver.

.. literalinclude:: summary_c.demo.py.txt
   :language: text
   :caption: summary_c.demo.py.txt (complete)

.. figure:: fig_c_speed_size_en.plot.py.svg
   :alt: Generated C time per cycle and code size against R and S
   :align: center
   :width: 78%

   Time per cycle (top) and :file:`.text` bytes (bottom) of the generated C
   against :math:`R` (left) and :math:`S` (right).  All axes are logarithmic.
   Minimum of 7 runs.  The figure proves that time grows faster than linearly
   in :math:`R` (slope 1.43, :math:`R = 1..64`; the last doubling alone gives
   slope 1.6) and that, unlike the simulator and the generated Python, C time
   depends on :math:`S` (302 ns at :math:`S = 3`, 1166 ns at :math:`S = 64`).
   Source: :file:`data/e4.jsonl`.

* Fit: :math:`-207 + 142\,R + 5.07\,R^{2}` ns, :math:`R^2 = 0.9999`,
  :math:`R = 1..64`.  The negative constant means the fit must not be used below
  :math:`R = 1` or far outside the range.
* Against the generated Python on the same models, C is 246 times faster
  (median over the :math:`R` sweep; 151 to 459), 337 times over :math:`S`, 321
  over :math:`T` and 445 over :math:`V`.
* The :math:`T` and :math:`V` sweeps are within the noise estimate of 16 % for
  small values; only the larger :math:`V` shows a rise (327 to 366 ns up to
  :math:`V = 8`, 525 to 576 ns from :math:`V = 16`).  No rate is given.

Code size, RAM and capacity macros
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default capacities are functions of the model size, readable in
``_plan_capacity`` in :file:`pyfcstm/render/c_kernel.py`.  With :math:`|Q|` the
number of states (root and owners included) and :math:`|\mathcal{R}|` the
number of regions, let :math:`P = |Q| + |\mathcal{R}|`.  Equation
:eq:`region-perf-capacity` gives the two defaults.

.. math::
   :label: region-perf-capacity

   \mathtt{ARENA\_CAPACITY} = \max(24,\ 12\,P),
   \qquad
   \mathtt{TRAIL\_CAPACITY} = 16 + 4\,P

The generator uses 8 and 4 instead for a model without regions and pseudo
states whose states are all leaves or the root.  The equations hold exactly
for all 63 models of the capacity grid (the listing above prints the counts).
:math:`P` is linear in :math:`R`, :math:`S` and :math:`D`, so the two macros
are too.  The storage of one machine, ``STORAGE_BYTES``, is the sum of a fixed part,
a configuration entry per arena slot and a smaller entry per trail slot, and
one configuration entry itself grows with :math:`P` (``context_size`` in the
same file; inference from reading it).  The measured size therefore grows
almost quadratically.

.. figure:: fig_c_capacity_en.plot.py.svg
   :alt: Capacity macros and size of one generated C machine against model size
   :align: center
   :width: 100%

   Left: ``ARENA_CAPACITY`` against the number of regions in the model for
   :math:`D = 1, 2, 4` (:math:`S = 8`).  Middle: ``TRAIL_CAPACITY`` against
   :math:`R` for :math:`S = 3, 8, 32`.  Right: ``sizeof`` of one machine in KiB
   against :math:`R`.  All axes are logarithmic.  The values are read from
   the generated header and from the compiled driver; no repeats are involved.
   The figure proves that capacities are linear in model size while ``sizeof``
   has slope 1.9 between :math:`R = 16` and :math:`R = 64`: 0.94 MiB at
   :math:`R = 16`, 3.5 MiB at :math:`R = 32` and 13.2 MiB at :math:`R = 64`.
   The slope of a size is a Fit; the capacity equations are exact.

Consequences for a deployment:

* One machine with 4 regions of 8 states is 90 KiB; with 8 regions it is 278 KiB;
  with 16 regions it is 958 KiB.  Keep large machines in static storage or on the
  heap, and read ``sizeof`` before placing one.
* The default capacities are derived from model size, not from a proven bound
  on the work of one cycle.  A machine whose defaults are too small reports the
  named macro in the error and is rebuilt with a larger value; a machine whose
  defaults are larger than needed pays for the difference in RAM.  Issue
  `#598 <https://github.com/HansBug/pyfcstm/issues/598>`_ reports that the
  default is far above the measured need on random region models (median
  about 44 times, one model below it); this page did not remeasure that.
* How to set the macros is in :doc:`/how_to/generation/index`.

First entry of nested owners
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. figure:: fig_first_cycle_engines_en.plot.py.svg
   :alt: First-cycle time of the simulator, generated Python and generated C against nesting depth
   :align: center
   :width: 70%

   Time of the first cycle (the cycle that enters every nested owner) of the
   ``R=1`` chain against :math:`D` for the three engines.  The y axis is
   logarithmic.  Simulator and Python: minimum of 5 fresh runs; C: minimum of 7
   runs.  The figure proves that the C runtime has no memo: its first cycle is
   3.3 µs at :math:`D = 1` and 2.1 ms at :math:`D = 12`, a factor that approaches 2.2
   per level (4.6 from :math:`D = 8` to 10 and 4.9 from 10 to 12).  At
   :math:`D = 12` it is slower than the generated Python (1.7 ms).  Source:
   :file:`data/e2.jsonl`, :file:`data/e3.jsonl` and :file:`data/e4.jsonl`.

Later cycles are unaffected: the steady time of the same C chain is 87 ns at
:math:`D = 1` and 1177 ns at :math:`D = 12`.  The cost is paid when the machine
enters the owners, and an application that enters them once at start-up and
never leaves can accept it.  Reentering a nested owner repeatedly would pay it
again; the sweep did not measure that case.

Against the template before regions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. figure:: fig_c_baseline_en.plot.py.svg
   :alt: Earlier C template and current C template on a region-free ring
   :align: center
   :width: 96%

   Time per cycle, :file:`.text` and ``sizeof`` of the ``c`` template before
   regions (commit ``ab9cae94``) and the current one on a region-free ring of 4,
   16 and 64 sibling states.  Minimum of 7 runs, same compiler flags.  The
   figure proves that region-free models run 1.7 to 2.5 times faster
   (125 to 128 ns against 50 to 74 ns) and pay for it in code size (:file:`.text`
   9.4 KB to 27.2 KB at 4 states) and RAM (1400 to 1688 bytes).  It says
   nothing about models with other structure; `issue #598
   <https://github.com/HansBug/pyfcstm/issues/598>`_ lists the families where
   the new template is slower, which were not remeasured here.  Source:
   :file:`data/e4_baseline.jsonl`.

Summary
-------

.. list-table::
   :header-rows: 1
   :widths: 18 16 30 36

   * - Stage
     - Label
     - Grows with
     - Measured range
   * - Model size
     - Exact
     - Regions: sum of :math:`S`; flat: product of :math:`S`
     - 6 and 9 leaf states at :math:`R = 2, S = 3`; 16 and 256 at :math:`R = 4, S = 4`
   * - Simulator, per cycle
     - Fit
     - :math:`R` (quadratic), :math:`V` (linear); not :math:`S`
     - 234 µs at :math:`R = 1`, 44 ms at :math:`R = 128`; 637 µs to 1.98 ms for :math:`V = 1..64`
   * - Simulator, nesting
     - Fit
     - :math:`D` (quadratic, memoised)
     - First cycle 340 µs to 7.2 ms for :math:`D = 1..12` (chain)
   * - Generated Python, per cycle
     - Fit
     - :math:`R` (quadratic), :math:`V`; not :math:`S`
     - 40 µs at :math:`R = 1`, 17 ms at :math:`R = 128`; 5.0 times faster than the simulator
   * - Generated Python, size
     - Measured
     - :math:`R`, :math:`S` (linear in states)
     - 137 KB at :math:`R = 1`, 7.1 MB and 913 ms import at :math:`R = 128`
   * - Generated C, per cycle
     - Fit
     - :math:`R` (slope 1.43), :math:`S`
     - 88 ns at :math:`R = 1`, 29.6 µs at :math:`R = 64`
   * - Generated C, RAM
     - Exact (macros), Fit (size)
     - :math:`P` (macros), almost :math:`P^2` (size)
     - 15 KB at :math:`R = 1`, 13.2 MiB at :math:`R = 64`
   * - Generated C, nesting
     - Measured
     - :math:`D`, about 2.2 times per level on the first cycle
     - 3.3 µs at :math:`D = 1`, 2.1 ms at :math:`D = 12`

Advice for modelers
-------------------

* **Choose regions for the model, not for speed.**  With independent regions
  the model text stays linear in :math:`R` while the flat machine is exponential
  (:eq:`region-perf-uniform`).  A hand-written flat machine of the same
  behaviour was faster per cycle in the simulator up to 1215
  transitions (17 of 20 checked models), so regions do not save simulator time.
* **Regions that read each other keep their order.**  A later region that reads
  what an earlier one wrote sees the new value (one cycle earlier than the
  reverse order).  A flat rewrite has to substitute the writes into the guards,
  so the saving in model size is smaller than equation
  :eq:`region-perf-uniform` suggests, and the rewritten form must be rechecked.
* **Count scopes before choosing a C target.**  RAM is almost quadratic in
  :math:`P`; with the default capacities 16 regions of 8 states need about 1 MiB
  per machine.  Set the macros as described in :doc:`/how_to/generation/index`
  only after you know your model's need; a smaller value is an error at run
  time, not silent misbehaviour.
* **Keep nesting shallow in C if the entry time matters.**  Each level multiplies
  the first cycle by about 2.2 once the depth passes 4; steady time does not.
* **Write fewer variables per transition if cycles matter.**  :math:`V` is the
  one parameter with a clean linear cost in the simulator (21 µs per variable)
  and in Python (5.5 µs per variable).
* **Prefer the generated Python or C runtime to the simulator for repeated
  execution**, and prefer C when the cycle time or the footprint is a hard
  requirement.

Limits of these numbers
-----------------------

The numbers will go out of date.  Issues `#596
<https://github.com/HansBug/pyfcstm/issues/596>`_ and `#598
<https://github.com/HansBug/pyfcstm/issues/598>`_ describe optimisations that
are expected to change the generated runtimes, and the simulator can change
too.  Every statement here is tied to a commit, and the tool regenerates all
of the data and, with it, every table and figure.

* The models are synthetic.  No claim is made about a real project's ratio of
  guards to assignments.
* One parameter changes at a time; interactions are not measured.
* The machine is shared.  The noise estimate above applies to every number.
* Only x86-64 Linux with gcc was measured.  32-bit, ARM, MSVC and macOS
  numbers are not given.
* The C stack need was not measured.
* The bounded model checking cost is on a separate page,
  :doc:`/explanations/bmc_scaling/index`.

To rerun and redraw, from the repository root with the generated templates
packaged (``make tpl``) and ``gcc`` available:

.. code-block:: bash

   python tools/measure_region_performance.py e1 --out docs/source/explanations/region_performance/data/e1.jsonl --core 3
   python tools/measure_region_performance.py e2 --out docs/source/explanations/region_performance/data/e2.jsonl --core 3
   python tools/measure_region_performance.py e3 --out docs/source/explanations/region_performance/data/e3.jsonl --core 3 \
       --sim-data docs/source/explanations/region_performance/data/e2.jsonl
   python tools/measure_region_performance.py e4 --out docs/source/explanations/region_performance/data/e4.jsonl --core 3 --part speed capacity
   python tools/measure_region_performance.py fit --data-dir docs/source/explanations/region_performance/data \
       --out docs/source/explanations/region_performance/data/fits.json

The baseline comparison needs the earlier template extracted from commit
``ab9cae94`` and ``--part baseline --old-template <directory>``.  The whole
run takes about an hour on the machine above.  After new data is in place, the
figures and the text tables are regenerated by the documentation build:
``make -f all.mk build`` from :file:`docs/source` runs the plot scripts and the summary
scripts, which read only the data files.  This command block is shown for
orientation and is not itself a generated output.
