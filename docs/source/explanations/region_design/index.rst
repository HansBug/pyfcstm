.. _sec-explanations-region-design:

Why regions run in order, and how other tools differ
====================================================

This page answers "why": why the regions of a state run one after another in the
order they are written, why events are inputs and not messages, why ``!`` forced
transitions and ``active()`` are shorthand, and what the first release leaves out
on purpose. It then sets FCSTM beside Stateflow and SCXML. For what the simulator
does in a cycle, see :doc:`/explanations/region_semantics/index`; for the exact
forms, see :doc:`/reference/region_model/index`.

Evidence rules for this page. Every statement about FCSTM below was checked by
running the shipped tools; the commands and outputs are on this page or on
:doc:`the semantics page </explanations/region_semantics/index>`, where the
statement links to them. Statements about Stateflow are the records of
experiments that were run on MATLAB R2020a Update 8 (Stateflow 10.2) while this
feature was designed. Each Stateflow cell below links to the issue that holds
the record (`issue #567 <https://github.com/HansBug/pyfcstm/issues/567>`_ for
parallel states and history, `issue #581
<https://github.com/HansBug/pyfcstm/issues/581>`_ for transitions that leave a
state with states inside); nothing about Stateflow here comes from memory, and
what was not recorded is marked ``not recorded``.
Statements about SCXML are quotes from the W3C SCXML 1.0 text, with section
numbers. UML state machines are not compared, because their text was not
checked while writing this page.

Why ordered, not concurrent and not unspecified
-----------------------------------------------

A model with regions can be given three meanings. Regions could run on real
threads, in an order the tool is free to choose, or in the order the author
wrote. The language chose the third, for three reasons that show up in everyday
use.

**Determinism.** The same model with the same inputs gives the same trace on
every run, on every machine. Two writers who share a variable do not have to
reason about interleavings, because there are none.

**The order is a modelling tool.** The interlock controller of the tutorial
needs the safety region to decide before the motion region acts. With ordered
regions that is one sentence in the model: write ``Safety`` first. The
:doc:`semantics page </explanations/region_semantics/index>` shows the same
inputs against the two orders; the motor switches off one cycle later when the
order is swapped. An unspecified order would make both outcomes legal for one
model.

**One meaning in every tool.** A model that is checked, simulated and run as
generated code has to mean one thing. The same swapped controller is run below
in the simulator and in the generated Python runtime, and then checked by
bounded model checking against the property "the motor is on only while
``permit`` is not 0":

.. code-block:: console

   $ pyfcstm generate -i controller_swapped.fcstm --template python -o out

.. testcode::

   import sys

   sys.path.insert(0, "out")
   from machine import ControllerMachine

   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.simulate import SimulationRuntime

   ready = {"fault": 0, "requested": 1}
   fault = {"fault": 1, "requested": 1}
   steps = [(None, ready), (["/Start"], ready), (None, ready), (None, fault), (None, fault), (None, ready)]
   model = load_state_machine_from_text(open("controller_swapped.fcstm").read())
   simulator = SimulationRuntime(model, input_source=ready)
   generated = ControllerMachine()
   for number, (events, inputs) in enumerate(steps, start=1):
       simulator.cycle(events, inputs=inputs)
       generated.cycle(events, inputs=inputs)
       same = str(simulator.configuration) == generated.configuration and all(
           simulator.vars[name] == generated.vars[name] for name in ("permit", "motor")
       )
       print(number, generated.configuration, generated.vars["permit"], generated.vars["motor"], same)

.. testoutput::

   1 Controller.Idle 0 0 True
   2 Controller.Running{Motion: Off, Safety: Watching} 1 0 True
   3 Controller.Running{Motion: On, Safety: Watching} 1 1 True
   4 Controller.Running{Motion: On, Safety: Watching} 0 1 True
   5 Controller.Running{Motion: Off, Safety: Watching} 0 0 True
   6 Controller.Running{Motion: Off, Safety: Watching} 1 0 True

.. literalinclude:: interlock.fbmcq
   :language: text
   :caption: ``interlock.fbmcq``

.. code-block:: console

   $ pyfcstm bmc -i controller.fcstm -q interlock.fbmcq
   BMC invariant <= 8: PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE
   Scenario: FEASIBLE
   Property verdict: SATISFIED WITHIN BOUND (NO COUNTEREXAMPLE)
   ...
   $ pyfcstm bmc -i controller_swapped.fcstm -q interlock.fbmcq
   BMC invariant <= 8: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND
   Scenario: FEASIBLE
   Property verdict: NOT SATISFIED WITHIN BOUND (COUNTEREXAMPLE FOUND)
   ...
   $ echo $?
   1

* The two runtimes agree in every cycle, including the cycle in which the
  swapped controller has ``permit=0`` and ``motor=1`` at the same time.
* The property holds within the bound for the controller with ``Safety`` first
  and is violated within it for the swapped controller (exit status ``1`` is the
  violation). The checker found the one-cycle lag that the trace shows, without a
  test being written for it.
* This does not prove the property for all time: the result is bounded to 8
  macro-steps, as the report itself says. See
  :doc:`/explanations/bmc_regions/index` for how a cycle with regions is
  encoded.

If regions ran in an unspecified order, the checker would have to consider every
order, the generated code would have to pick one, and "the simulator agrees with
the generated code" would stop being a property you can test. A real concurrent
semantics would multiply the cases of the checker by the interleavings. Ordered
execution keeps the cost proportional to the sum of the regions, which is the
subject of :doc:`/explanations/region_performance/index`.

The price. Order-sensitive models are easy to write by accident. For that reason
``pyfcstm inspect`` reports an earlier region that reads what a later region
writes, and a later region that silently overwrites an earlier write; see
:doc:`/explanations/diagnostics/index`.

Events are inputs, not messages
-------------------------------

An event in FCSTM is a flag that the caller supplies for a cycle. Everything in
the cycle sees the same set and using an event does not remove it. There is no
statement that raises an event, no broadcast, no queue and no acknowledgement.

The reason is the same as above. A queue inside the machine would add a second
kind of time (steps within a cycle), and the question "when is this event seen by
that region" would need an answer that every tool agrees on. With external events
the answer is "at its turn in the cycle, always the same set".

The language is built on that: an event that a region declares belongs to the
region, and a name that depends on the position is resolved once for every active
leaf and refused if it is ambiguous (see
:doc:`the semantics page </explanations/region_semantics/index>`). A region that
needs to tell another region something writes a variable, and the second region
reads it at its turn; the order decides which cycle it sees.

SCXML, which does have an internal queue, says: "The SCXML processor MUST place
the event that is generated at the rear of the session's internal event queue."
(W3C SCXML 1.0, section 4.2). FCSTM has no equivalent of that queue by design.

Forced transitions and ``active()`` are shorthand
-------------------------------------------------

Both are accepted by the language and removed before anything runs: the
simulator, the generated runtimes and the bounded model checker never see a
special case.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Written
     - What runs
     - Cost
   * - ``!P -> Off : if [x >= 2];`` on a state with regions
     - Two ``-> [*]`` transitions in every region (a starter that raises a
       hidden variable and a follower), and two transitions of the owner. See
       the expansion in the semantics page.
     - A hidden variable ``__forced_<n>`` in ``runtime.vars`` and in generated
       code; extra transitions; a longer exported text.
   * - ``active("Root.P.A.A2")``
     - A hidden variable ``__active_Root_P_A_A2``, set at the first line of the
       state's ``enter`` and cleared at the last line of its ``exit``.
     - A hidden variable, and an assignment in two blocks of the queried
       state.

Keeping them as shorthand has three consequences that the first release accepts:

* A model and the text exported from it behave the same in every stage. The
  check is a real run: the controller and its exported text produce identical
  cycles (the output is in the semantics page).
* Hidden variables are ordinary variables. A hot start has to supply them, and
  the runtime does not derive or check them. That is a burden for the caller and
  the price of having no special case.
* Where the expansion cannot reproduce another tool exactly, the difference is
  kept and recorded, for example two competing forced declarations in one owner
  (`issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_).

Drawings and the report of ``pyfcstm inspect`` show the model as written and
leave the hidden variables out. With ``--enable-verify`` a finding about how the
machine runs is judged on the machine that runs, so it can name a hidden
variable (see :doc:`/explanations/diagnostics/index`).

What the first release does not do
----------------------------------

Each item below is a deliberate boundary of the language. The grammar rejects
four of the five examples and the model builder rejects the jump between regions;
the output is real:

.. testcode::

   from pyfcstm.dsl.error import GrammarParseError
   from pyfcstm.model import load_state_machine_from_text
   from pyfcstm.utils.validate import ModelValidationError

   cases = [
       ("history written on an owner", "state Root { [*] -> P; state P { region R { [*] -> A; state A; } [H] -> A; } }"),
       ("child states mixed with a region", "state Root { [*] -> P; state P { state X; region R { [*] -> A; state A; } } }"),
       ("enter block inside a region", "state Root { [*] -> P; state P { region R { enter { } [*] -> A; state A; } } }"),
       ("jump from one region to another", "state Root { [*] -> P; state P { region R1 { [*] -> A; state A; } region R2 { [*] -> B; state B; B -> A; } } }"),
       ("variable declared in a region", "state Root { [*] -> P; state P { region R { def int x = 0; [*] -> A; state A; } } }"),
   ]
   for title, text in cases:
       try:
           load_state_machine_from_text(text)
       except (GrammarParseError, ModelValidationError) as error:
           # GrammarParseError: the grammar refuses the text; ModelValidationError: the model builder refuses it.
           print("==", title)
           print(type(error).__name__)
           print("\n".join(str(error).splitlines()[:2]))

.. testoutput::

   == history written on an owner
   GrammarParseError
   Found 2 errors during parsing:
   Error 1: Syntax error at line 1, column 65, near '[H]': Unexpected token '[H]'
   == child states mixed with a region
   GrammarParseError
   Found 3 errors during parsing:
   Error 1: Syntax error at line 1, column 42, near 'region': Unexpected token 'region'
   == enter block inside a region
   GrammarParseError
   Found 3 errors during parsing:
   Error 1: Syntax error at line 1, column 44, near 'enter': Unexpected token 'enter'
   == jump from one region to another
   ModelValidationError
   Unknown to state 'A' of transition:
   B -> A; (line 1)
   == variable declared in a region
   GrammarParseError
   Found 2 errors during parsing:
   Error 1: Syntax error at line 1, column 44, near 'def': Unexpected token 'def'

* **History on an owner.** An owner cannot declare ``[H]`` or ``[H*]`` next to
  its regions (the first example writes ``[H] -> A`` after the region). History
  of a composite state inside a region works.
* **Mixing child states with regions.** A state contains either ordinary child
  states or regions.
* **Lifecycle actions and variables in a region.** A region holds states,
  transitions, events and aspects. ``enter``, ``during``, ``exit`` and variable
  declarations belong to the owner or to a state.
* **Jumping between regions.** A transition cannot leave a region for a state of
  another region or enter a region's state from outside; transitions end at the
  owner. The fourth example writes ``B -> A`` in region ``R2`` for a state of
  ``R1``: ``A`` is not a state of ``R2``, so the model builder refuses it
  (``Unknown to state 'A' of transition``).
* **Internal events and queues.** Not offered; see above.
* **True parallelism.** Not offered; regions are logical concurrency only.

How FCSTM differs from Stateflow and SCXML
------------------------------------------

The table lists the topics of the task and what each source supports.
``not recorded`` means that no experiment or quote was available for this page; the
cell is deliberately empty of claims.

.. list-table::
   :header-rows: 1
   :widths: 16 28 28 28

   * - Topic
     - FCSTM (shipped tools)
     - Stateflow (R2020a experiments)
     - SCXML 1.0 (W3C text)
   * - Parts of a state that are active together
     - All regions of an active owner. A configuration lists one position per
       region, for example ``Controller.Running{Safety: Watching, Motion: On}``.
     - Parallel (AND) states under an owner; the experiments used one owner with
       two parallel children (`issue #567 <https://github.com/HansBug/pyfcstm/issues/567>`_).
     - "The <parallel> element encapsulates a set of child states which are
       simultaneously active when the parent element is active." (3.4)
   * - Order in which the parts run
     - Written order, observable and guaranteed (traces in the semantics page).
     - not recorded
     - not recorded
   * - Where events come from
     - Inputs of the cycle, shared by all regions, never removed. Regions have
       no way to raise an event.
     - not recorded
     - Events raised by the machine go to a queue: "The SCXML processor MUST place
       the event that is generated at the rear of the session's internal event
       queue." (4.2)
   * - Event scope
     - A region owns the events it declares; a name that depends on the position
       is resolved once per active leaf and refused when ambiguous.
     - not recorded
     - not recorded
   * - Meaning of completion
     - A region is Done when a ``-> [*]`` written in it is taken; the last Done
       region continues through the owner's outgoing transitions in the same
       cycle, or the completion is refused.
     - not recorded
     - "When all of the children reach final states, the <parallel> element itself
       is considered to be in a final state" (3.1.3)
   * - History
     - An owner cannot declare history. A composite state inside a region can,
       and an owner is entered through ``Owner.[H]`` or ``Owner.[H*]``.
     - The parallel (AND) state cannot hold a history junction directly (the model
       was refused at compile time); the OR states around and inside it can.
       With history only on the outer state, both parallel branches restart in
       their first state; with history on the outer state and on each branch,
       each branch restores its last state (`issue #567
       <https://github.com/HansBug/pyfcstm/issues/567>`_).
     - not recorded
   * - State query
     - ``active("Path")``, shorthand for a hidden flag; true from the start of
       ``enter`` to the end of ``exit``.
     - ``in(P.a2)`` in a transition condition. Measured: a condition that reads
       a state inside the source of a transition is satisfied when the machine
       rests in that state (`issue #581
       <https://github.com/HansBug/pyfcstm/issues/581>`_, second case).
     - not recorded
   * - A transition that leaves a state with states inside
     - Judged once, at the state the machine rests in; a target that cannot be
       entered makes the transition do nothing. With regions it expands as
       described above.
     - Measured on exclusive parents: the condition is judged once at the parent,
       the exit order is innermost first, and an exit action that changes the
       variable the condition reads does not cancel the transition. A target that
       cannot be entered was refused at compile time; with that diagnostic
       lowered to a warning the run stopped with a "State inconsistency" error
       (`issue #581 <https://github.com/HansBug/pyfcstm/issues/581>`_, cases 3
       and 6, and the section on a target that cannot be entered).
     - not recorded

The Stateflow cells for forced transitions come from the twelve comparison models
recorded in `issue #581 <https://github.com/HansBug/pyfcstm/issues/581>`_, all
with exclusive parents; eleven agree step by step with the current expansion and
the twelfth differs only in a way that does not involve the transition. They say
nothing about parallel states, and FCSTM's expansion into regions was compared
only against FCSTM itself (the shared fixtures). The two differences that remain
inside regions are in `issue #591
<https://github.com/HansBug/pyfcstm/issues/591>`_.

Moving from Stateflow
---------------------

These are the differences a Stateflow user meets first. Each is a fact about
FCSTM that you can check with the commands on this page; the Stateflow side is
marked where an experiment exists.

* **A region is a namespace, not a state.** Paths go through the region
  (``Controller.Running.Motion.On``) and the same state name may appear in two
  regions. A Stateflow parallel child is a state; the experiments treated it as
  one (`issue #567 <https://github.com/HansBug/pyfcstm/issues/567>`_).
* **Order is the text order.** In FCSTM the position of the ``region`` block is
  the order and there is nothing else to set. Rearranging blocks changes
  behaviour, as the swapped controller shows. How Stateflow orders parallel
  states was not measured for this page.
* **History is explicit.** A transition enters a history with ``Owner.[H]`` or
  ``Owner.[H*]``; nothing is remembered because a state contains a junction. An
  owner itself cannot be given a history.
* **Events do not travel.** Nothing sends an event between regions. Use a
  variable and an order.
* **The whole group leaves through** ``-> [*]``\ **.** Leaving a group by a forced
  transition is the expansion above, not a special case. The differences that
  remain are in `issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_.
* **Variables are inputs, controls and outputs.** Persistent variables are
  declared before the root state; the keyword ``log`` and other function names
  cannot be used as variable names.

Boundaries of this comparison
-----------------------------

* The Stateflow experiments used one product version (R2020a Update 8). They do
  not describe other versions.
* Order, event scope and completion were not measured for Stateflow, and no
  comparison is made for them.
* UML state machines are not compared.
* The SCXML quotes show what the text states; they do not show how any
  implementation behaves.
