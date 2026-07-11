:orphan:

FBMCQ Language Reference
=========================

FBMCQ (FCSTM bounded-model-checking query language) is the ``.fbmcq``
language accepted by :func:`pyfcstm.bmc.parse.parse_bmc_query`.  One file
selects an initial frame, optionally constrains the environment, and declares
exactly one bounded property.  This page is a lookup reference: examples are
small enough to use as parser or binder test cases.

Validity has three distinct levels.  A query can pass one level and fail at a
later one.

.. list-table:: Validation levels
   :header-rows: 1
   :widths: 18 29 25 28

   * - Level
     - Checks
     - Public failure
     - Principal source facts
   * - Parse
     - Tokens, clause order, punctuation, and expression categories.
     - :class:`pyfcstm.bmc.errors.BmcQueryParseError`
     - ``pyfcstm/bmc/grammar/BmcQueryLexer.g4`` and
       ``BmcQueryParser.g4``
   * - Bind
     - Positive bounds, selector ranges, atom contexts, and model names.
     - :class:`pyfcstm.bmc.errors.InvalidBmcQuery`, normally with a
       ``BmcBindingDiagnostic`` code and path
     - ``pyfcstm/bmc/query.py`` and ``binding.py``
   * - Lower
     - Whether the current Z3 encoding implements a parsed operation.
     - :class:`pyfcstm.bmc.errors.UnsupportedBmcQuery`
     - ``pyfcstm/bmc/relation.py`` and ``properties.py``

The bounded trace has frames ``0 .. N`` and executable macro steps (and event
inputs) ``0 .. N-1``.  Consequently, a frame selector may equal ``N`` while an
event or absolute call-step selector may not.

Complete file grammar
---------------------

The top-level order is fixed.  The ``init`` clause is optional, assumptions
may repeat, and one final ``check`` clause is required.  Every clause ends in
``;`` and trailing tokens are rejected.

.. code-block:: text

   query          ::= init_clause? assume_clause* check_clause EOF
   init_clause    ::= "init" init_target init_havoc? ("where" cond_expr)? ";"
   init_target    ::= "cold" | "terminated" | "state" "(" STRING ")"
   init_havoc     ::= "havoc" "*"
                    | "havoc" "{" init_var ("," init_var)* "}"
   init_var       ::= ID | STRING

   assume_clause  ::= "assume" ("always" | "at" INT) ":" cond_expr ";"
                    | "assume" "event" "(" STRING "," event_range ")"
                      ("==" | "!=") bool_literal ";"
                    | "assume" "events" "cardinality" "any" ";"
                    | "assume" "events" "cardinality" "at_most_one"
                      "{" STRING ("," STRING)* "}" ";"

   check_clause   ::= "check" property_kind "<=" INT ":" property_body ";"
   property_kind  ::= "reach" | "forbid" | "invariant" | "must_reach"
                    | "exists_always" | "response" | "cover"
   property_body  ::= cond_expr
                    | "trigger" cond_expr "->" "within" INT cond_expr

Defaults and normalization
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Defaults
   :header-rows: 1
   :widths: 26 30 44

   * - Omitted surface
     - Effective value
     - Boundary
   * - Entire ``init`` clause
     - ``init cold``
     - Declaration initializers remain enabled; no initial ``where`` predicate.
   * - Assumptions
     - Empty list
     - Events are otherwise unconstrained by FBMCQ.
   * - ``active(path)``, ``terminated()``, ``case(label)`` selector
     - ``current``
     - Explicit integer selectors parse but are rejected during binding in
       user property and assumption contexts.
   * - ``called(...)`` / ``call_count(...)`` step selector
     - Current property anchor
     - This is not spelled ``current``; that keyword is invalid here.
   * - Omitted call-filter field
     - No restriction on that call-record dimension
     - An entirely empty filter matches every recorded abstract call at the
       selected step.

ASCII decimal integers may contain leading zeroes and canonicalize to decimal:
``01`` becomes ``1`` and ``01 .. 03`` becomes ``1..3``.  A bound and a
``within`` window must be positive.  Hexadecimal and floating-point literals
are numeric-expression literals, not valid bounds or selectors.

Lexical surface
---------------

``ID`` is ``[A-Za-z_][A-Za-z0-9_]*``.  Double- and single-quoted strings accept
``\\b``, ``\\t``, ``\\n``, ``\\f``, ``\\r``, escaped quotes/backslashes,
octal escapes, ``\\xHH``, and ``\\uHHHH``.  Quoted names may therefore contain
Unicode or collide with keywords.  Comments are discarded in all three forms:
``// line``, ``# line``, and ``/* block */``.

.. code-block:: fbmcq

   // Default cold start; comments are trivia.
   assume always: var("temperature") >= -40;
   # The final check is still mandatory.
   check reach <= 01: active('Root.Ready');

Invalid lexical or file shapes include:

.. code-block:: fbmcq
   :caption: Invalid examples

   init cold check reach <= 1: true;       // missing init semicolon
   init cold;                              // missing check
   check reach <= 0x1: true;               // bound must use INT
   check reach <= 1: true; trailing        // trailing input is rejected
   check reach <= 1: active("Root.A);       // unterminated string

Initial frame: ``init``, ``havoc``, and ``where``
--------------------------------------------------

.. list-table:: Initial targets
   :header-rows: 1
   :widths: 19 30 51

   * - Form
     - Frame-0 control source
     - Variable behavior
   * - Omitted or ``init cold;``
     - Internal cold-start sentinel; normal entry expansion follows.
     - Every persistent declaration initializer constrains frame 0 unless
       selected by ``havoc``.
   * - ``init state("path");``
     - The named model state, resolved as a stable leaf or entry source.
     - The same declaration-initializer policy applies.  This is a symbolic
       hot start; it does not execute earlier entry actions to derive values.
   * - ``init terminated;``
     - Terminated sentinel.
     - The same declaration-initializer policy applies.

``havoc`` skips declaration initializers for selected persistent variables.  It
does not assign a random concrete value: the frame-0 symbol remains free and
can be constrained by ``where``.  ``havoc *`` selects every persistent
variable.  A named set must be non-empty, contain no duplicates, and resolve
to declared variables.  Reserved or non-identifier names can be quoted.

``where`` contributes a condition only to frame 0.  It may use frame variables,
literals, arithmetic, logical operators, ``active(...)``, and
``terminated()``.  Bare ``cycle``, ``event``, ``case``, ``called``, and
``call_count`` are not legal in this context.  A model variable literally
named ``cycle`` remains addressable as ``var("cycle")``.

Legal, non-equivalent cases:

.. code-block:: fbmcq

   check reach <= 1: true;  // implicit cold, no havoc, no where

.. code-block:: fbmcq

   init state("Root.Idle") havoc { retries, "cycle" }
       where retries >= 0 && var("cycle") == 1;
   check invariant <= 4: retries >= 0;

.. code-block:: fbmcq

   init terminated havoc * where terminated();
   check must_reach <= 1: terminated();

Boundary and invalid cases:

.. code-block:: fbmcq
   :caption: Boundary: havoc frees a variable and where constrains it

   init cold havoc { x } where x == 7;
   check reach <= 1: x == 7;

.. code-block:: fbmcq
   :caption: Invalid initial forms

   init state("Root.A") havoc {}; check reach <= 1: true;       // empty set
   init state("Root.A") havoc {x, x}; check reach <= 1: true;   // duplicate
   init cold where cycle == 0; check reach <= 1: true;          // cycle_not_allowed
   init cold where event("Root.E", current); check reach <= 1: true;
   init state("$STATE_INIT"); check reach <= 1: true;            // reserved path
   init state("Root.A") where x == 1 havoc {x}; check reach <= 1: true;

Environment assumptions
-----------------------

Assumptions conjoin constraints with the core trace; they do not change the
property polarity.

Frame assumptions
~~~~~~~~~~~~~~~~~

``assume always`` applies to all ``N+1`` frames.  ``assume at k`` applies to
one frame and requires ``0 <= k <= N``.  Frame predicates permit ``cycle`` and
current-frame ``active``/``terminated`` atoms, but not event, case, or call
atoms.

.. code-block:: fbmcq

   assume always: x >= 0;
   check invariant <= 3: x >= 0;

.. code-block:: fbmcq

   assume at 0: active("Root.Idle");
   check reach <= 2: active("Root.Done");

.. code-block:: fbmcq

   assume at 3: cycle == 3 && !terminated();
   check forbid <= 3: x < 0;

The third example is the legal upper boundary ``k == N``.  These are invalid:

.. code-block:: fbmcq

   assume at 4: true; check reach <= 3: true;                    // out of range
   assume always: event("Root.Tick", current); check reach <= 1: true;
   assume always: called("Root.Hook"); check reach <= 1: true;

Event assumptions
~~~~~~~~~~~~~~~~~

An event assumption addresses executable steps, so points and inclusive range
ends must satisfy ``0 <= k < N``.  ``*`` expands to every step.  ``!=`` is
normalized by inverting the boolean; for example ``!= false`` means expected
``true``.

.. code-block:: fbmcq

   assume event("Root.Tick", *) == false;
   check reach <= 3: true;

.. code-block:: fbmcq

   assume event("Root.Start", 0) == true;
   check reach <= 2: active("Root.Running");

.. code-block:: fbmcq

   assume event("Root.Reset", 1 .. 2) != false;
   check reach <= 3: terminated();

The legal last point is ``N-1``.  A reversed range is structurally invalid;
an end equal to ``N`` binds as out of range.

.. code-block:: fbmcq

   assume event("Root.Tick", 3) == true; check reach <= 3: true;
   assume event("Root.Tick", 2..3) == true; check reach <= 3: true;
   assume event("Root.Tick", 3..1) == true; check reach <= 4: true;

Cardinality assumptions
~~~~~~~~~~~~~~~~~~~~~~~

``any`` adds no cardinality restriction.  ``at_most_one`` constrains the
listed event set independently at every executable step.  Its list is
non-empty, unique, and model-resolved.  It does not imply that one event must
occur.

.. code-block:: fbmcq

   assume events cardinality any;
   check reach <= 1: true;

.. code-block:: fbmcq

   assume events cardinality at_most_one {"Root.Start"};
   check reach <= 2: active("Root.Running");

.. code-block:: fbmcq

   assume events cardinality at_most_one {
       "Root.Tick",
       "Root.Reset",
       "Root.Stop"
   };
   check forbid <= 4: terminated();

A singleton is a legal but logically vacuous boundary.  Empty and duplicate
sets are invalid:

.. code-block:: fbmcq

   assume events cardinality at_most_one {}; check reach <= 1: true;
   assume events cardinality at_most_one {"Root.E", "Root.E"};
   check reach <= 1: true;

Expressions
-----------

Numeric expressions
~~~~~~~~~~~~~~~~~~~

.. list-table:: Numeric primary forms
   :header-rows: 1
   :widths: 25 35 40

   * - Family
     - Forms
     - Notes
   * - Literals
     - ``0``, ``001``, ``0x2A``, ``.5``, ``1.``, ``3.5e1``
     - Hex uses lowercase ``0x``.  Floats lower to reals.
   * - Constants
     - ``pi``, ``E``, ``tau``
     - Encoded from Python floating constants as Z3 real values.
   * - Variables
     - ``x`` or ``var("any name")``
     - Bare names require ``ID`` and cannot be reserved; ``var`` supports
       keyword, Unicode, and punctuated model names.
   * - Frame index
     - ``cycle``
     - Current frame index; unavailable in initial ``where`` and call ``where``.
   * - Calls
     - ``call_count(...)``
     - Property contexts only; returns the number of matching call records.
   * - Unary
     - ``+x``, ``-x``
     - Numeric unary operators.
   * - Conditional
     - ``(condition) ? if_true : if_false``
     - Parentheses around the condition are required.

Numeric precedence, highest to lowest, is: parentheses/primaries; unary
``+ -``; right-associative ``**``; ``* / %``; ``+ -``; ``<< >>``; ``&``;
``^``; ``|``; conditional.  Representative legal forms are:

.. code-block:: fbmcq

   check reach <= 2: x + y * z ** 2 >= 10;
   check reach <= 2: ((active("Root.A")) ? x : var("fallback")) >= 0;
   check reach <= 2: sqrt(abs(x)) + round(y) >= pi;

Division and modulo add a nonzero-divisor definedness condition; ``sqrt`` adds
a nonnegative-operand condition.  An undefined predicate affects property
semantics as specified below, rather than being silently assigned a value.

All parser-recognized unary function names are:

.. code-block:: text

   sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh
   sqrt cbrt exp log log10 log2 log1p abs ceil floor round trunc sign

Current lowering implements ``sqrt``, ``abs``, ``ceil``, ``floor``, ``round``,
``trunc``, and ``sign``.  The remaining names parse and bind but raise
``UnsupportedBmcQuery``.  Integer bitwise/shift operators ``& | ^ << >>`` also
parse and bind but are unsupported by the current arithmetic (non-BitVec)
profile.  ``%`` is implemented for integer operands but a real modulo such as
``f % 1.0`` is unsupported.  These distinctions are intentional:

.. code-block:: fbmcq
   :caption: Parsed and bound, but unsupported during lowering

   assume always: sin(x) >= 0;
   check reach <= 1: true;

.. code-block:: fbmcq
   :caption: Invalid expression categories

   check reach <= 1: x + 1;                    // numeric value is not Boolean
   check reach <= 1: active("Root.A") + 1 > 2; // Boolean atom in arithmetic

Condition expressions
~~~~~~~~~~~~~~~~~~~~~

Condition primaries are boolean literals, comparisons, BMC atoms, and
parenthesized conditions.  Boolean literals accept ``true/True/TRUE`` and
``false/False/FALSE``.  Symbol and keyword aliases canonicalize to the symbol
operator shown below.

.. list-table:: Condition operators, high to low precedence
   :header-rows: 1
   :widths: 24 30 46

   * - Operation
     - Accepted spelling
     - Notes
   * - Negation
     - ``!p``, ``not p``
     - Canonical ``!``.
   * - Numeric comparison
     - ``< > <= >= == !=``
     - Both operands numeric.
   * - Boolean equality
     - ``== != iff``
     - Both operands Boolean; ``iff`` canonicalizes to ``iff``.
   * - Conjunction
     - ``&&``, ``and``
     - Short-circuit definedness is preserved.
   * - Exclusive or
     - ``xor``
     - Both operands are evaluated.
   * - Disjunction
     - ``||``, ``or``
     - Short-circuit definedness is preserved.
   * - Implication
     - ``=>``, ``implies``
     - Right-associative; both operand definedness conditions are retained.
   * - Conditional
     - ``(condition) ? if_true : if_false``
     - All three branches are conditions; only the selected branch contributes
       definedness.

.. code-block:: fbmcq

   check reach <= 3: !(x < 0) && active("Root.Ready");
   check reach <= 3: (x == 1) implies (y == 2);
   check reach <= 3: (active("Root.A")) ? !terminated() : y >= tau;

The boundary ``((true) ? 1 : (1 / 0)) == 1`` is defined because the invalid
branch is not selected.  ``((false) ? 1 : (1 / 0)) == 1`` is undefined.

BMC atoms and contextual legality
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Atom forms
   :header-rows: 1
   :widths: 18 37 45

   * - Atom
     - Grammar
     - Meaning and default
   * - Frame variable
     - ``var(STRING)``
     - Persistent variable at the current evaluation frame.
   * - Cycle
     - ``cycle``
     - Numeric current frame index.
   * - Active state
     - ``active(STRING[, current|INT])``
     - State is active; omitted selector means current.
   * - Termination
     - ``terminated([current|INT])``
     - Frame uses the terminated sentinel; omitted means current.
   * - Event
     - ``event(STRING, current|INT)``
     - Event input at a step.  The selector is mandatory.
   * - Case
     - ``case(STRING[, current|INT])``
     - Internal macro-step case label; user binding permits it only as the
       naked body of ``cover``.
   * - Called
     - ``called(call_filter?)``
     - At least one matching abstract-call record.
   * - Call count
     - ``call_count(call_filter?)``
     - Numeric number of matching records.

.. list-table:: Context matrix
   :header-rows: 1
   :widths: 24 11 11 11 11 14 18

   * - Context
     - ``cycle``
     - active / terminated
     - event
     - case
     - call atoms
     - Selector rule
   * - Initial ``where``
     - No
     - Yes
     - No
     - No
     - No
     - Current only
   * - Frame assumption
     - Yes
     - Yes
     - No
     - No
     - No
     - Current only
   * - Ordinary property body
     - Yes
     - Yes
     - No
     - No
     - Yes
     - Current only
   * - ``response`` trigger
     - Yes
     - Yes
     - ``current`` only
     - No
     - Yes
     - Current only
   * - ``response`` target
     - Yes
     - Yes
     - No
     - No
     - Yes
     - Current only
   * - ``cover`` body
     - No
     - No
     - No
     - Naked atom only
     - No
     - Omitted or ``current``
   * - Call ``where``
     - No
     - No
     - No
     - No
     - No
     - Snapshot variables and ordinary expression operators only

Legal, non-equivalent atom compositions are:

.. code-block:: fbmcq

   check reach <= 3: active("Root.A") && !terminated();

.. code-block:: fbmcq

   check response <= 3:
       trigger event("Root.Tick", current)
       -> within 1 active("Root.Ready");

.. code-block:: fbmcq

   check reach <= 3:
       cycle >= 0 && var("cycle") >= cycle && called();

The legal selector boundary ``active("Root.A", current)`` is equivalent to
omitting the selector.  In contrast, ``event("Root.Tick")`` is syntax-invalid
because an event atom must name its step selector.

Thus these grammar-valid forms are binding-invalid:

.. code-block:: fbmcq

   check reach <= 5: active("Root.Idle", 2);                 // explicit_frame_selector
   check reach <= 5: event("Root.Tick", current);            // event_not_allowed
   check response <= 5: trigger event("Root.Tick", 3)
       -> within 2 active("Root.Done");                       // event_not_allowed
   check reach <= 3: (cycle < 2) ? true : case("label");     // case_not_allowed

Abstract-call filters
~~~~~~~~~~~~~~~~~~~~~

``called`` is existential (equivalent to a matching count of at least one);
``call_count`` is numeric.  Both consume the same filter.  Positional arguments
must precede named arguments; ``where`` must be last; every dimension may occur
at most once.

.. list-table:: Call-filter dimensions
   :header-rows: 1
   :widths: 20 28 52

   * - Dimension
     - Accepted form
     - Constraint
   * - Action
     - first positional ``STRING`` or ``action=STRING``
     - Existing named abstract action path; omitted matches any action.
   * - Step
     - second positional selector or ``step=selector``
     - Omitted selects the anchor; absolute points are ``0 <= k < N``.
   * - Stage
     - ``stage=STRING``
     - Closed set: ``enter``, ``during``, ``exit``.
   * - Runtime role
     - ``role=STRING``
     - ``state_enter``, ``state_exit``, ``leaf_during``,
       ``plain_during_before``, ``plain_during_after``,
       ``aspect_during_before``, ``aspect_during_after``, or
       ``transition_effect``.
   * - State
     - ``state=STRING``
     - Public runtime state path.
   * - Active leaf
     - ``active_leaf=STRING``
     - Public active leaf path at the call.
   * - Named ref
     - ``named_ref=STRING`` or ``named_ref=null``
     - Existing named ref callsite, or explicitly no named ref.
   * - Snapshot predicate
     - ``where cond_expr``
     - Evaluated against persistent-variable values captured at call time.

Legal filters:

.. code-block:: fbmcq

   check reach <= 3: called("Root.A.Hook");

.. code-block:: fbmcq

   check reach <= 3:
       call_count("Root.A.Hook", step=*, stage="during", role="leaf_during") >= 2;

.. code-block:: fbmcq

   check reach <= 4:
       called(action="Root.Library.Shared", step=-2..+0,
              state="Root.A", active_leaf="Root.A",
              named_ref="Root.A.FirstRef", where x >= 0 && var("y") < 10);

An empty filter is legal: ``called()`` asks whether any abstract call occurred
at the current anchor, and ``call_count(step=*)`` counts all recorded calls in
the bounded trace.  Anonymous abstract blocks do not create user-visible call
records.

Step selectors are ``*``, an absolute point (``2``), a relative point
(``+0``, ``-1``), or an inclusive range.  Missing range endpoints mean the
current anchor, not a trace endpoint.  Relative results are clipped to
``[0, N)``.

.. list-table:: Step selector examples
   :header-rows: 1
   :widths: 22 33 45

   * - Selector
     - At anchor ``i``
     - Boundary
   * - omitted or ``+0``
     - step ``i``
     - At frame ``N`` this can select no executable step.
   * - ``*``
     - every ``0 .. N-1`` step
     - Independent of anchor.
   * - ``-2..+0``
     - current and previous two, clipped
     - At anchor 0 it contains only step 0.
   * - ``..+2``
     - current through two future steps, clipped
     - Missing start means current.
   * - ``+0..``
     - current only
     - Missing end means current, not ``N-1``.
   * - ``0..2``
     - absolute inclusive range
     - Both endpoints must be less than ``N``.

Invalid filters and unsupported call-``where`` atoms:

.. code-block:: fbmcq

   check reach <= 3: called(stage="during", 1);             // positional after named
   check reach <= 3: called("A", action="B");               // duplicate action
   check reach <= 3: called(foo="A");                       // unsupported argument
   check reach <= 3: called(step=current);                   // syntax-invalid selector
   check reach <= 3: called(step=3);                         // out of range when N=3
   check reach <= 3: called("A", stage="middle");           // call_stage
   check reach <= 3: called("A", where cycle == 0);         // cycle_not_allowed
   check reach <= 3: called("A", where active("Root.A"));   // call_where_atom_not_allowed

Properties
----------

All bounds are positive.  ``N`` includes frames ``0 .. N``; a property does
not claim anything beyond that finite horizon.  SAT has different polarity by
property: ``reach``, ``exists_always``, and ``cover`` seek desired witnesses;
``forbid``, ``invariant``, ``must_reach``, and ``response`` seek
counterexamples.

For a predicate ``p`` at a frame, let ``defined(p)`` denote all arithmetic
domain conditions, and define:

.. code-block:: text

   good(p)      = defined(p) and p
   bad_true(p)  = not defined(p) or p
   bad_false(p) = not defined(p) or not p

.. list-table:: Property semantics
   :header-rows: 1
   :widths: 18 20 36 26

   * - Kind
     - SAT polarity
     - Objective searched within the bound
     - Undefined predicate
   * - ``reach``
     - Desired witness
     - Some frame has ``good(p)``.
     - Does not witness reach.
   * - ``forbid``
     - Counterexample
     - Some frame has ``bad_true(p)``.
     - Counts as a violation.
   * - ``invariant``
     - Counterexample
     - Some frame has ``bad_false(p)``.
     - Counts as a violation.
   * - ``must_reach``
     - Counterexample
     - No frame has ``good(p)``.
     - Cannot satisfy the obligation.
   * - ``exists_always``
     - Desired witness
     - Every frame has ``good(p)`` on one trace.
     - Breaks the witness.
   * - ``cover``
     - Desired witness
     - The named transition/fallback case is selected on some step.
     - Not predicate-based.
   * - ``response``
     - Counterexample
     - Trigger undefined, or a defined-true trigger has no defined-true response
       in the next ``within`` frames.
     - Undefined trigger is a violation; undefined response cannot satisfy.

``reach``
~~~~~~~~~

.. code-block:: fbmcq

   check reach <= 4: active("Root.Done");
   check reach <= 4: x >= 10 && !terminated();
   check reach <= 4: called("Root.A.Hook", step=*) && call_count(step=*) >= 2;

Boundary: ``check reach <= 1: true;`` may witness at frame 0.  Invalid:
``check reach <= 0: true;``.  An event atom or explicit frame selector is a
binding error in the body.

``forbid``
~~~~~~~~~~

.. code-block:: fbmcq

   check forbid <= 5: active("Root.Fault");
   check forbid <= 5: temperature > 100 || retries > 3;
   check forbid <= 5: called(role="transition_effect", step=*);

Boundary: ``check forbid <= 1: false;`` has no true-predicate violation on a
defined trace.  Division by zero makes the predicate undefined and therefore
counts as a ``forbid`` violation.

``invariant``
~~~~~~~~~~~~~

.. code-block:: fbmcq

   check invariant <= 6: !terminated();
   check invariant <= 6: 0 <= pressure && pressure <= 200;
   check invariant <= 6: called("Root.A.Hook") implies active("Root.A");

Boundary: ``check invariant <= 1: true;`` checks frames 0 and 1.  A false or
undefined predicate at either frame is a counterexample.

``must_reach``
~~~~~~~~~~~~~~

.. code-block:: fbmcq

   check must_reach <= 6: active("Root.Done");
   check must_reach <= 6: progress == 100;
   check must_reach <= 6: called("Root.Commit", step=*);

Boundary: ``check must_reach <= 1: true;`` has no counterexample because frame
0 is already good.  SAT instead means a trace on which no frame is good; it is
not a desired reachability witness.

``exists_always``
~~~~~~~~~~~~~~~~~

.. code-block:: fbmcq

   check exists_always <= 4: active("Root.Safe");
   check exists_always <= 4: energy >= 0;
   check exists_always <= 4: !called(role="transition_effect") || x >= 0;

Boundary: ``check exists_always <= 1: true;`` requires both frames 0 and 1 to
be defined-true.  This is existential over traces, unlike ``invariant``, whose
SAT objective searches for a violating trace.

``cover``
~~~~~~~~~

The body must be exactly ``case("label")`` or ``case("label", current)``.
Conjunctions, fixed step selectors, and other atoms are rejected.  Compilation
requires the label schema ``source::kind::target::ordinal``, an existing label,
and ``kind`` equal to ``transition`` or ``fallback``.  ``initial``, ``absorb``,
and ``delta`` labels are known but not coverable.

.. code-block:: fbmcq

   check cover <= 4: case("Root.Idle::transition::Root.Run::0");
   check cover <= 4: case("Root.Run::fallback::Root.Run::0");
   check cover <= 4: case("Root.Run::transition::Root.Done::2", current);

Boundary: ``current`` is accepted and canonicalizes to the omitted selector.
The following fail at different levels:

.. code-block:: fbmcq

   check cover <= 4: active("Root.Run") && case("label");  // cover_predicate
   check cover <= 4: case("label", 2);                    // cover_predicate
   check cover <= 4: case("Root::initial::Root::0");      // not coverable
   check cover <= 4: case("missing");                     // bad/unknown schema

``response``
~~~~~~~~~~~~

The response window is positive and uses strict successors: a trigger at step
``i`` is answered only at frames ``i+1 .. i+within``.  The trigger is evaluated
for steps ``0 .. N-1`` and is the sole context where
``event(path, current)`` is legal.  The response side cannot use event atoms.

.. code-block:: fbmcq

   check response <= 8:
       trigger event("Root.Fault", current)
       -> within 3 active("Root.Recovering");

.. code-block:: fbmcq

   check response <= 5:
       trigger called("Root.Request", step=+0)
       -> within 2 called("Root.Acknowledge", step=-1..+0);

.. code-block:: fbmcq

   check response <= 6:
       trigger queue_depth > 0
       -> within 1 queue_depth == 0;

A ``within`` value larger than the remaining horizon is legal.  If a trigger
near the end has no response before frame ``N``, it contributes to the separate
``incomplete`` objective rather than being declared a violation without enough
future frames.  ``within`` need not be at most ``N``.  Boundary and invalid
forms:

.. code-block:: fbmcq

   check response <= 1: trigger true -> within 2 false;  // legal, may be incomplete
   check response <= 1: trigger true -> within 0 true;   // invalid positive window
   check response <= 2: true;                            // wrong property body
   check reach <= 2: trigger true -> within 1 true;      // response body on reach
   check response <= 3: trigger true
       -> within 1 event("Root.E", current);             // event_not_allowed

Legal, invalid, and unsupported summary
---------------------------------------

.. list-table:: Failure boundary quick reference
   :header-rows: 1
   :widths: 28 24 24 24

   * - Example
     - Parse
     - Bind
     - Lower
   * - ``check reach <= 1: sqrt(x) >= 0;``
     - Legal
     - Legal when ``x`` exists
     - Legal; ``x >= 0`` is required for definedness
   * - ``check reach <= 1: sin(x) >= 0;``
     - Legal
     - Legal when ``x`` exists
     - ``UnsupportedBmcQuery``
   * - ``check reach <= 1: x & 1 == 0;``
     - Legal
     - Legal when ``x`` exists
     - Unsupported current Int profile
   * - ``check reach <= 1: event("E", current);``
     - Legal
     - ``event_not_allowed``
     - Not reached
   * - ``check cover <= 1: case("bad");``
     - Legal
     - Legal naked cover shape
     - Invalid label schema or unknown label
   * - ``assume at 1: true; check reach <= 1: true;``
     - Legal
     - Legal frame upper boundary
     - Legal
   * - ``assume event("E", 1) == true; check reach <= 1: true;``
     - Legal
     - ``event_selector_out_of_range``
     - Not reached

Model-aware binding additionally rejects unknown state, event, variable,
abstract-action, and named-ref paths, whitespace-only quoted references, and
the reserved state paths ``$STATE_INIT`` and ``$STATE_TERMINATE``.  Structural
binding without a model can validate contexts and bounds but cannot prove that
names exist.

.. list-table:: Common stable binding diagnostic codes
   :header-rows: 1
   :widths: 31 69

   * - Code
     - Cause
   * - ``query_shape``
     - Non-positive or malformed query fields, whitespace-only references, or
       other AST shape violations.
   * - ``unknown_state`` / ``unknown_event`` / ``unknown_variable``
     - A model-aware reference does not exist.
   * - ``reserved_state_path``
     - User text names ``$STATE_INIT`` or ``$STATE_TERMINATE``.
   * - ``explicit_frame_selector``
     - A frame-local atom uses an integer instead of omitted/``current``.
   * - ``frame_selector_out_of_range``
     - ``assume at k`` violates ``0 <= k <= N``.
   * - ``event_selector_out_of_range`` / ``event_range_out_of_range``
     - An event assumption point or range violates ``0 <= k < N``.
   * - ``event_not_allowed`` / ``case_not_allowed``
     - An atom appears outside its permitted context.
   * - ``called_not_allowed`` / ``call_count_not_allowed``
     - A call predicate appears outside property context.
   * - ``cover_predicate``
     - ``cover`` does not contain a naked current-step ``case`` atom.
   * - ``call_step_out_of_range``
     - An absolute call step or endpoint is not in ``0 .. N-1``.
   * - ``call_stage`` / ``call_role``
     - A filter value is outside its documented closed set.
   * - ``call_where_atom_not_allowed`` / ``cycle_not_allowed``
     - A call snapshot predicate uses a trace atom or bare cycle.
   * - ``unknown_call_action`` / ``unknown_named_ref``
     - A model-aware call metadata path does not exist.

Source and test traceability
----------------------------

This reference was checked against:

* grammar and tokens: ``pyfcstm/bmc/grammar/BmcQueryParser.g4`` and
  ``BmcQueryLexer.g4``;
* AST, defaults, canonical text, and call filters: ``pyfcstm/bmc/ast.py`` and
  ``query.py``;
* contextual and model-aware legality: ``pyfcstm/bmc/binding.py``;
* cold/state/terminated source selection: ``pyfcstm/bmc/source.py``;
* definedness, call filters, seven objectives, and unsupported lowering:
  ``pyfcstm/bmc/relation.py`` and ``properties.py``;
* executable expectations: ``test/bmc/test_query_grammar.py``,
  ``test_query_parser.py``, ``test_query_binding.py``,
  ``test_query_expression_parity.py``, ``test_call_predicate_guards.py``,
  ``test_relation_environment.py``, and ``test_properties.py``.
