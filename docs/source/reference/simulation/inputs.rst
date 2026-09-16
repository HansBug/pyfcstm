Input sources
=====================

Variables have distinct ownership and lifetimes. ``control`` and ``output``
remain in ``runtime.vars`` across cycles; outputs retain their last value until
assigned again. ``param`` values are fixed at construction and exposed through
``runtime.parameters``. ``input`` values belong to the environment and are
sampled once per cycle. Parameters and inputs never enter writable persistent
storage. Initializers remain name-free.

Constructing a runtime
----------------------

.. code-block:: python

    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model import parse_dsl_node_to_state_machine
    from pyfcstm.simulate import SimulationRuntime, SequenceInput

    model = parse_dsl_node_to_state_machine(parse_with_grammar_entry('''
        input float pressure;
        param float gain = 2.0;
        output float reading = 0.0;
        state Root {
            state Running { during { reading = pressure * gain; } }
            [*] -> Running;
        }
    ''', 'state_machine_dsl'))
    runtime = SimulationRuntime(
        model,
        parameters={'gain': 3.0},
        input_source={'pressure': SequenceInput([70.0, 80.0, 90.0])},
    )
    first = runtime.cycle()
    second = runtime.cycle(inputs={'pressure': 75.0})
    third = runtime.cycle()
    assert [first.inputs['pressure'], second.inputs['pressure'],
            third.inputs['pressure']] == [70.0, 75.0, 90.0]
    assert runtime.outputs['reading'] == 270.0

Construction checks complete source bindings without calling ``get()`` or
``cycle()``. Cold construction uses parameter defaults where not overridden,
then initializes persistent variables. Hot construction requires complete
``parameters`` and ``initial_vars`` and does not evaluate their initializers.
The first executed cold or hot cycle reads sample zero.

Explicit ``inputs`` overrides apply to one call. Every bound source is still
read and advanced on a successful cycle, even when all inputs are overridden.
An override cannot hide an exhausted or failing provider. Use a replay source
for deterministic replay. Invalid overrides and event arguments are rejected
before any sampling. Integer inputs require integers, excluding booleans;
float inputs accept integers and finite floats. Nonfinite values are rejected.

Custom generators
-----------------

The public structural interfaces ``ScalarInputPattern`` and
``IntegratedInputPattern`` require ``get()`` and ``cycle()``. Existing objects
can implement those interfaces without inheritance. Integrated sources also
expose immutable ``input_names``: a tuple exactly matching model declaration
order. Returned mappings must contain exactly those names, but their insertion
order is normalized by the runtime.

Subclass a caching base when writing new generators:

.. code-block:: python

    from pyfcstm.simulate import BaseScalarInputPattern

    class PressureRamp(BaseScalarInputPattern):
        def __init__(self, start, increment):
            super().__init__()
            self.start = start
            self.increment = increment

        def _sample(self, step):
            return self.start + self.increment * step

    source = PressureRamp(70.0, 5.0)
    assert source.get() == source.get() == 70.0
    source.cycle()  # Runtime owns this call when the source is bound.
    assert source.get() == 75.0

``BaseIntegratedInputPattern(input_names=(...))`` provides the equivalent
vector hook: ``_sample(step)`` returns a mapping. The base copies and freezes
successful snapshots. Both bases cache successful reads until advancement.
A failed sample leaves the current step retryable; sampling must not
irreversibly consume an external stream. ``cycle()`` only advances the logical
step and invalidates the cache, without reading the next sample or doing I/O.

Use a fresh provider instance for each runtime. Binding one scalar instance to
multiple inputs is rejected; use an integrated provider for correlated values.
Do not advance bound sources independently. Runtime/source pairs are serial,
non-reentrant objects. No runtime or output context is implicitly injected into
a provider; closed-loop plant wiring is outside this interface.

Built-in sources
----------------

* ``ConstantIntInput`` and ``ConstantFloatInput`` provide typed constants.
  Mapping literals are automatically wrapped as constants.
* ``SequenceInput(values, end='error')`` copies scalar samples. ``hold`` retains
  the last sample; ``loop`` repeats the sequence. An empty sequence permits
  only ``error``. Exhaustion raises on the next ``get()``, not on ``cycle()``.
* ``UniformIntInput(low, high, seed=...)`` uses inclusive integer bounds.
  ``UniformFloatInput`` provides finite floating-point bounds.
* ``NormalFloatInput(mean, stddev, seed=...)`` and ``NormalIntInput`` use an
  independent RNG per source. Integer normal sampling requires explicit
  ``rounding='round'``, ``'floor'``, ``'ceil'``, or ``'trunc'``; ``round`` uses
  ties-to-even. Standard deviation must be nonnegative.
* ``CallableInput(sample)`` calls ``sample(step)`` lazily and caches its value.
  ``IntegratedCallableInput(sample, input_names=(...))`` does the same for a
  complete vector; names are never inferred by probing the callable.
* ``IntegratedSequenceInput`` copies and validates every vector. Names can be
  explicit or inferred from the first mapping; empty sequences require names.
* ``ReplayInputPattern(snapshots, input_names=(...))`` is a finite deterministic
  vector sequence with error-on-exhaustion semantics.

Commit and failure boundaries
-----------------------------

Each cycle freezes one input vector for validation and committed execution.
Guards, operations, nested branches, lifecycle actions and abstract contexts
read this vector. State, history and result data are prepared before providers
advance; the runtime then publishes the prepared boundary.

.. list-table:: Cycle outcomes
   :header-rows: 1

   * - Outcome
     - Source advancement
     - Observable runtime boundary
   * - Success, Delta, or newly terminated
     - Exactly once per provider
     - Cycle count, history and last inputs commit together; Delta keeps
       pre-cycle machine state.
   * - Bad events or overrides
     - No reads or advancement
     - Unchanged.
   * - Read/type/runtime execution failure
     - No advancement
     - Candidate state and inputs are discarded. Healthy sources can retry
       the current index, subject to the runtime error's existing contract.
   * - Abstract handler raises in raise mode
     - No advancement
     - Runtime enters its existing error state; later calls are no-ops.
   * - Already ended or in error state
     - No reads or advancement
     - No new history or input snapshot.
   * - Custom provider raises during advancement
     - Earlier providers may already have advanced
     - Machine boundary is not committed; permanent ``input_source_error``
       prevents every subsequent provider call. Create fresh sources/runtime.

Read failures use ``E_INPUT_SOURCE_READ`` with the original exception as cause;
numeric failures use ``E_INPUT_SOURCE_TYPE``. Missing/unknown names use
``E_INPUT_SOURCE_MISSING`` / ``E_INPUT_SOURCE_UNKNOWN``. Malformed protocols and
advancement violations use ``E_INPUT_SOURCE_CONTRACT``. These diagnostics are
exposed by ``SimulationRuntimeInputSourceError.code``.

Abstract callbacks and observers can have external effects which cannot be
rolled back. They must tolerate failed execution attempts; no distributed
transaction or rollback of device I/O is promised.

Observing execution
-------------------

``CycleResult.inputs`` and ``runtime.last_inputs`` expose detached, read-only
snapshots. ``last_inputs`` is ``None`` before the first committed cycle; no-op
calls return empty result inputs without replacing it. History entries for
models with inputs include ``inputs``. ``history_size`` accepts only
``None`` or nonnegative integers; zero retains no history.

``ReadOnlyExecutionContext.inputs`` and ``.parameters`` expose external values
separately from persistent ``.vars``. Execution trace entries carry the same
role partitions and include nonempty input/parameter mappings in ``to_dict()``.
``runtime.control_variables`` and ``runtime.outputs`` are read-only projections.

The CLI accepts construction-time ``--param name=value`` and per-cycle ``cycle --input name=value``. Each actual cycle requires the complete vector with no implicit hold. Command-owned sources are recreated on ``init``/``clear`` and parameters remain fixed; other Python-supplied providers still require explicit runtime reconstruction. See :doc:`diagnostics` for the complete command and failure contract.
