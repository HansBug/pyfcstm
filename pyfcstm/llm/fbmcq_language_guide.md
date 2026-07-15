# FBMCQ Language Guide for LLMs

Use this guide when authoring, repairing, reviewing, or explaining `.fbmcq`
queries for an existing FCSTM model. A good query is tied to known model facts
and one concrete verification intent. Do not invent model facts: never invent
states, variables, events, actions, or cover-case labels.

The rule against invention is not a rule to avoid FBMCQ features. When the
task supplies the facts a feature needs, use every applicable documented
feature to express the intended question precisely. This guide therefore
describes the whole public FBMCQ authoring surface, including its supported
and explicitly unsupported expression forms.

This guide is limited to writing clear, valid, and meaningful FBMCQ. It does
not teach checking-engine internals or ask the author to reason about them.

## Full Capability Map

FBMCQ is deliberately richer than a small set of safe-looking query
templates. The following table is an authoring map, not a recommendation to
use every feature in every query. Select each capability when its required
model facts and verification intent are supplied.

| Capability family | Available authoring surface | Use it when the task provides |
|---|---|---|
| Initialization | omitted `init`; `init cold`; `init state("...")`; `init terminated`; explicit `havoc *` or `havoc { ... }`; explicit `where` | A start policy or initial-value constraint |
| Environment | frame assumptions (`always`, `at k`); event assumptions (`*`, point, or range); event cardinality (`any`, `at_most_one`) | Environmental timing, values, or event-exclusivity rules |
| Questions | `reach`, `forbid`, `invariant`, `must_reach`, `exists_always`, `cover`, and `response` | The intended witness, violation, coverage, or response meaning |
| Expressions | typed variables, `var()`, `cycle`, literals, constants, arithmetic, integer operators, comparisons, boolean logic, conditionals, and documented unary functions | A typed value relation that is actually part of the requirement |
| Model observations | `active()`, `terminated()`, response-trigger `event(..., current)`, `case()`, `called()`, and `call_count()` | Exact paths, labels, frame/step meaning, and call metadata |
| Call analysis | positional or named action filters; absolute/relative/open step ranges; stage, role, state, active leaf, named reference, and snapshot `where` | An abstract lifecycle-call requirement rather than only a state requirement |
| File syntax and status | quoted strings, all accepted boolean spellings, `//`, `#`, and `/* ... */` comments in ordinary files; source-valid versus executable-profile distinctions | A normal file or a request that intentionally requires a currently unsupported form |

The sections below define each row's exact context and boundary. A capability
that is source-valid but currently unsupported at execution time is still part
of the language: explain that status accurately instead of pretending that the
feature does not exist. Conversely, the availability of a form never permits
inventing the model fact it needs.

## Purpose And Scope

FBMCQ asks a bounded question about a model that already exists. It is not
a replacement for FCSTM source and it cannot supply missing model facts. Use it
to ask whether a desired execution can be found, whether a violation can be
found, or whether a named public execution case can be covered.

Use FBMCQ as a language, not as a small fixed template. Given authoritative
paths, values, timing, initialization policy, environment rules, action-call
metadata, or case labels, select the language form that states the question
directly. If the task does not provide a fact required by a form, ask for that
fact instead of guessing it or silently replacing the form with a weaker one.

When an outer task asks for a `.fbmcq` artifact, return only FBMCQ source. Do
not wrap it in a Markdown fence or inline-code backticks, and do not add
explanation before or after it. When the outer task asks for review or
explanation, prose is allowed, but do not mix prose into the query file.

For an artifact response, the first non-whitespace character must begin the
first FBMCQ clause (`init`, `assume`, or `check`) and the last non-whitespace
character must be the query's final semicolon. Do not add a title, label,
bullet, quote, Markdown fence, inline backtick, code-review panel, reasoning,
or postscript.

## Required Model Facts

Before writing a query, identify only the facts the chosen property uses:

| Query construct | Required facts | Never guess |
|---|---|---|
| `active()` | Exact state path, hierarchy, and state meaning | A path derived from a display name |
| bare variable or `var()` | Exact variable name, type, unit, range, and meaning | A variable that sounds plausible |
| `event()` | Exact event path and the relevant step | Event scope or an event at the final step |
| `called()` / `call_count()` | Exact action path, role, step range, and snapshot meaning | An action name or call role |
| `case()` | A tool-provided public case label | A label ordinal or internal case |
| `init state()` | Exact state path and a justified hot-start intention | A start state chosen only to change the result |
| `havoc` / `where` | Which initializers are intentionally relaxed and constrained | A relaxation used to avoid a counterexample |
| `assume` | A stated environmental constraint | An assumption added only to obtain a desired result |
| `response` | Trigger meaning, response meaning, and required window | That the trigger frame itself is a response |

Complete FCSTM source is not always necessary. A precise description of the
relevant state paths, variables, events, actions, and constraints can be
sufficient. If a required fact is missing, do not invent it. Ask for the fact
or state that the query cannot be written safely, according to the outer task.

When the task does supply those facts, preserve their distinctions. For
example, a state path is not an action path, a state frame is not an event
step, and a public cover-case label is not a transition description to infer.

## Output Contract

A complete file has exactly one query. Use one optional `init` clause, zero or
more `assume` clauses, and one `check` clause. End clauses with semicolons.

```fbmcq
init state("Root.Idle");
assume event("Root.Go", 0) == true;
check reach <= 1: active("Root.Done");
```

Do not return multiple candidate queries. When the outer task asks for a raw
artifact, do not add any comment, explanation, command, or alternative query:
although FBMCQ source files accept comments, they are not a channel for LLM
response prose. Ordinary `.fbmcq` files accept `//` line comments, `#` line
comments, and `/* block */` comments, but a raw LLM artifact accepts none of
them. A reviewer may explain alternatives outside the artifact, but the
artifact itself remains one complete query.

## Top-Level Query Structure

The query order is fixed:

```fbmcq-snippet
init_clause?
assume_clause*
check_clause
```

The `check` clause names a property kind and a positive bound. A query must
consume all input; trailing prose is not part of FBMCQ.

## Initialization

An omitted `init` and `init cold` both select ordinary cold initialization.
Use `init state("...")` for a justified hot start, and `init terminated` only
when the task is about the terminated boundary. Only an explicit `init` clause
can carry one optional `havoc` clause followed by one optional `where`
condition; omitted `init` has no clause to modify:

| Form | Use when the task says | Important limit |
|---|---|---|
| omitted `init` | normal initial entry with no explicit initialization policy | Declaration initializers constrain frame 0; it cannot carry `havoc` or `where` |
| `init cold` | normal initial entry with an explicit policy or permitted initial-value refinement | Declaration initializers constrain frame 0 unless permitted `havoc` relaxes them |
| `init state("Root.Leaf")` | a supplied hot-start state | It is not a history of earlier entry actions |
| `init terminated` | the supplied terminated boundary | It does not make ordinary active states available |
| `havoc *` | all persistent initial values are intentionally unconstrained | It relaxes values, not paths or events |
| `havoc { x, "other" }` | only the named declared variables are relaxed | The set is non-empty, unique, and model-resolved |
| `where condition` | a supplied frame-0 constraint | It constrains, rather than replaces, the selected initialization |

`where` may use frame variables, numeric and boolean operators, `active()`,
and `terminated()`. It cannot use `cycle`, `event()`, `case()`, `called()`, or
`call_count()`; a model variable literally named `cycle` remains addressable
as `var("cycle")`. Do not write `havoc {}`: omit `havoc` entirely when no
initial variable needs relaxation.

When the task names an exact initialization clause, preserve it exactly. In
particular, do not add `havoc` or `where` to a requested `init state("...")`
unless the task explicitly authorizes that relaxation.

```fbmcq
init state("Root.Idle") havoc { x } where x == 7;
check reach <= 1: x == 7;
```

Do not choose hot start, `havoc`, or `where` simply because it makes a desired
execution easier to find. Initial constraints that conflict with each other can
leave no legal execution, which is not evidence that the checked property is
healthy.

## Environment Assumptions

Use an assumption only when the task gives an environmental rule. FBMCQ has
three distinct assumption families; use the family that matches the supplied
rule rather than encoding one family as another.

| Family | Complete forms | Scope and boundary |
|---|---|---|
| Frame | `assume always: condition;` / `assume at k: condition;` | `always` applies to every visible frame; `at k` requires `0 <= k <= bound` |
| Event | `assume event("Path", selector) == true;` / `!= false;` | `selector` is `*`, one step, or an inclusive `start .. end` range; every selected step must be in `0 .. bound - 1` |
| Cardinality | `assume events cardinality any;` / `at_most_one { "A", "B" };` | `any` explicitly adds no restriction; `at_most_one` applies independently at each executable step |

Use event `==` and `!=` deliberately. Both compare an exact boolean event
input; `!= false` requires the event to be true, and `!= true` requires it to
be false. A cardinality list is non-empty and has unique, known event paths.
`at_most_one` does not require any listed event to occur, and a singleton list
is legal but vacuous. Frame assumptions can use `cycle`, `active()`, and
`terminated()`, but cannot use `event()`, `case()`, `called()`, or
`call_count()`.

```fbmcq
assume always: x >= 0;
assume event("Root.Go", 0) == false;
assume events cardinality at_most_one {"Root.Go"};
check invariant <= 1: x >= 0;
```

An assumption changes the executions being checked. It is not a restatement of
the conclusion. Never add an unrequested assumption to hide an unwanted
execution.

## Expressions

Numeric expressions and condition expressions have different roles. A bare
variable refers to a known model variable; `var("...")` is the explicit form
when a name needs quoting, for example `var("x")`. `cycle` is the built-in
cycle number and cannot be replaced by a bare model variable.

Numeric forms include decimal integers, hexadecimal integers such as `0x2A`,
decimal floating values such as `.5`, `1.`, and `3.5e1`, mathematical constants
`pi`, `E`, and `tau`, variables, `var("...")`, `cycle`, `call_count()`, unary
`+` / `-`, and the conditional form `(condition) ? number : number`. Numeric
operator precedence is parentheses and primaries; unary `+ -`; right-associative
`**`; `* / %`; `+ -`; `<< >>`; `&`; `^`; `|`; then the conditional expression.

Condition forms include `true` / `false` in any accepted capitalization,
numeric comparisons `< > <= >= == !=`, boolean equality `==`, `!=`, or `iff`, unary
`!` / `not`, conjunction `&&` / `and`, exclusive-or `xor`, disjunction `||` /
`or`, right-associative implication `=>` / `implies`, and
`(condition) ? condition : condition`. Numeric and boolean equality operands
must not be mixed. Use the supplied type and range information to choose a
meaningful expression, and parenthesize a conditional condition as shown.

All parser-recognized unary functions are:

```text
sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh
sqrt cbrt exp log log10 log2 log1p abs ceil floor round trunc sign
```

The current executable expression profile supports `sqrt`, `abs`, `ceil`,
`floor`, `round`, `trunc`, and `sign`. The other listed function names are
valid source and bind to model values, but currently produce an explicit
unsupported diagnostic when executed. Likewise, integer bitwise and shift
operators `& | ^ << >>` are accepted and bound but are not executable in the
current numeric profile; `%` is executable for integer operands but not for a
real-valued modulo. This is feature information, not permission to avoid a
supported feature: use an executable form whenever it exactly expresses the
given requirement, and report an unsupported form accurately when that is what
the requested query requires.

Division and modulo require a nonzero divisor, and `sqrt` requires a
non-negative operand. An expression can be valid source yet have an explicit
unsupported diagnostic; do not call that a syntax error.

```fbmcq
init state("Root.Idle");
check reach <= 2: var("x") == 0 && cycle >= 0;
```

```fbmcq
init cold havoc { x } where ((x >= 0) ? true : false);
assume at 0: abs(x) <= tau && (x == 0 implies true);
check reach <= 2: ((x >= 0) ? x : 0) >= 0;
```

## Model Observation Atoms

`active("State.Path")` is true when the named state is the active leaf or an
active ancestor. `terminated()` observes the terminated boundary.
`event("Event.Path", selector)` observes event input at an executable step,
not a state frame. `case("label")` refers to an authoritative public cover
case. `called()` asks whether one abstract lifecycle call matches and
`call_count()` returns how many calls match.

| Atom | Selector and context rule |
|---|---|
| `active("State.Path"[, current])` | Omitted or `current` only; legal in initial `where`, frame assumptions, ordinary property bodies, and response predicates |
| `terminated([current])` | Omitted or `current` only in the same frame-local contexts |
| `event("Event.Path", current)` | The selector is mandatory; legal only in a `response` trigger, where it must be `current`; it can be combined with the trigger's other legal frame-local forms |
| `case("Public.Label"[, current])` | Legal only as the naked body of `check cover` |
| `called(filter?)` / `call_count(filter?)` | Legal in ordinary property bodies, response triggers, and response predicates; not in initial `where` or frame assumptions |

Do not give `active`, `terminated`, or `case` an arbitrary frame number even
though the grammar accepts an integer selector. `cycle` is legal in frame and
property contexts, including a response trigger, but not in initial `where` or
a call-time `where`. A call-time
`where` is evaluated over the persistent-variable snapshot captured at that
call; it may use ordinary numeric and boolean expressions but not `cycle` or
observation atoms.

The source grammar also accepts a numeric event selector such as
`event("Root.Go", 0)`, but the public binding profile intentionally permits an
event atom only as `event("Root.Go", current)` in a response trigger. That is
a source-valid but binding-invalid property expression, not a way to inspect a
fixed event step. To constrain an event at a fixed step or range, use the event
assumption family, for example `assume event("Root.Go", 0) == true;`.

The complete call-filter surface is below. Positional arguments must come
first, the action string is the first positional argument, an optional step
selector is the second, named dimensions occur at most once, and `where` is
last. When the action is intentionally omitted, a step selector may be the
only positional argument: `called(*)` and `call_count(-1..+0)` ask about any
action in the selected step window. Prefer `step=...` when that spelling makes
the intended omission clearer.

| Dimension | Form | Meaning |
|---|---|---|
| Action | `"Root.A.Hook"` or `action="Root.A.Hook"` | Exact supplied abstract action path; omit to match any action |
| Step | `step=*`, `step=2`, `step=+0`, `step=-1`, `step=-2..+0`, `step=..+2`, `step=+0..` | All, absolute, relative, or inclusive clipped step range |
| Stage | `stage="enter"`, `stage="during"`, or `stage="exit"` | Lifecycle stage |
| Role | `role="state_enter"`, `role="state_exit"`, `role="leaf_during"`, `role="plain_during_before"`, `role="plain_during_after"`, `role="aspect_during_before"`, `role="aspect_during_after"`, or `role="transition_effect"` | Exact supplied runtime call role |
| State | `state="Root.A"` | State path associated with the call |
| Active leaf | `active_leaf="Root.A.Leaf"` | Active leaf at the call |
| Named reference | `named_ref="Root.A.Ref"` or `named_ref=null` | Exact named reference callsite or explicitly no named reference |
| Snapshot | `where x >= 0 && var("y") < 10` | Call-time persistent-variable condition |

For a call anchored at step `i`, omitted step and `+0` select `i`; `*` selects
all executable steps; omitted range endpoints mean the anchor; and relative
ranges are clipped to the available executable range. Absolute points and both
absolute range endpoints must be valid executable steps. Use each dimension
only when its supplied metadata is relevant; an empty `called()` filter is also
a valid question about any call at the current anchor.

```fbmcq
init state("Root.Idle");
check reach <= 1:
    called("Root.Idle.Tick", step=0, role="leaf_during", where x == 0)
    && call_count("Root.Idle.Tick", step=*) == 1;
```

Do not put a `case()` atom inside a general boolean expression. Do not read an
event at a step beyond the declared bound.

## Property Selection

Choose the property from the question, not from a preferred result:

Match the task's quantifier and named property exactly. A request for one
execution that remains true is `exists_always`, not `reach`; a request that
every trigger receives a later response is `response`, not `reach`. Do not
substitute a superficially easier property kind merely because it can mention
the same state or variable.

| Property | When finding an execution means | Typical question | Common mistake |
|---|---|---|---|
| `reach` | The desired state or condition is possible | Can this happen? | Treating it as a universal guarantee |
| `forbid` | A violating execution was found | Can this danger happen? | Negating the predicate to force a result |
| `invariant` | A violating frame was found | Does every visible frame obey this? | Confusing it with `exists_always` |
| `must_reach` | A complete execution missing the target was found | Must every execution reach this? | Replacing it with `reach` |
| `exists_always` | One execution keeps the condition true | Is there a continuously safe execution? | Treating it as universal |
| `cover` | The named public case was selected | Can this case be covered? | Guessing a case label |
| `response` | A trigger lacks the required later response | Does every trigger receive a response? | Counting the trigger frame as the response |

The property body must have the shape required by its kind:

| Kind | Required body shape |
|---|---|
| `reach`, `forbid`, `invariant`, `must_reach`, `exists_always` | One frame-local condition |
| `cover` | Exactly one naked `case("Public.Label")` atom, optionally with `current` |
| `response` | `trigger condition -> within positive_integer condition` |

The ordinary single-condition bodies can use frame variables, `cycle`,
`active()`, `terminated()`, and call atoms. They cannot use `event()` or
`case()`. A response trigger has that same frame-local expression surface and
additionally permits `event(..., current)`: it may combine an event atom with
variables, `cycle`, `active()`, `terminated()`, arithmetic/boolean expressions,
`called()`, and `call_count()`. The response predicate again uses the ordinary
frame-local condition surface. A response window is always a positive integer.
Do not put a response body after a non-response kind, or a general expression
around a `case()` body.

## Frames Steps And Bounds

Use the declared bound as the visible horizon of the query. State conditions
and variable conditions refer to visible model states; event selectors refer to
event inputs before a following state is observed. `current` means the
language-selected state or event position for the construct that contains it.

For a bound `N`, visible frames are `0 .. N`; executable event and call steps
are `0 .. N - 1`. Thus a frame assumption may use `at N`, an event assumption
may use at most `N - 1`, and a response window can extend beyond the visible
suffix of a late trigger. A call step range is inclusive; an open relative
endpoint means the call anchor, not the first or last trace step.

A result only speaks about the selected bound, initialization, and assumptions.
Do not describe a finite-bound result as an unbounded conclusion. Check that the
bound covers the event, state condition, and response window required by the
task.

## Definedness

Undefined arithmetic, such as division by zero, is not a harmless false value.
For witness-oriented properties, a predicate needs to be defined and true. For
safety-oriented properties, an undefined predicate can expose a violation.

Keep undefined trigger and false trigger distinct in a `response` query. An
undefined response predicate does not count as a successful response.

## Response And Incomplete Windows

A response begins at a strict successor of the trigger frame. With
`within W`, it must occur in one of the next `W` frames, never at the trigger
frame itself. A defined-false trigger creates no obligation; an undefined
trigger is a violation; an undefined response predicate never satisfies the
obligation. A trigger near the selected bound can leave too little visible
suffix to decide the full window; this is a response incomplete observation,
not a satisfied response and not a runtime error. Do not shorten the window to
avoid that classification: use the supplied positive window and a bound that
can observe it when the task requires a complete result.

```fbmcq-executable
init state("Root.Idle");
assume event("Root.Go", 0) == true;
check response <= 1:
    trigger event("Root.Go", current)
    -> within 1 active("Root.Done");
```

```fbmcq-executable
init state("Root.Idle");
assume event("Root.Go", 0) == true;
check response <= 1:
    trigger event("Root.Go", current)
    -> within 2 active("Root.Done");
```

```fbmcq-executable
init state("Root.Idle");
check response <= 1:
    trigger active("Root.Idle") && cycle == 0
        && called("Root.Idle.Tick", step=+0, role="leaf_during")
    -> within 1 active("Root.Idle");
```

## Avoiding Vacuous Queries

Before accepting a query, check all of the following:

- Initialization, `havoc`, `where`, assumptions, and bound allow at least one
  legal execution.
- Every state, variable, event, action, and case comes from known model facts.
- The selected property matches whether the task seeks a desired execution or a
  violating execution.
- The predicate is relevant and not a constant `true` or `false` substitute.
- An assumption is authorized and does not merely exclude the behavior under
  examination.
- A response query does not call an incomplete window a success.
- A changed model behavior that should affect the requirement would also affect
  this query.

## Complete Examples

The following executable examples use a model with `Root.Idle`, `Root.Done`,
integer `x`, event `Root.Go`, abstract action `Root.Idle.Tick`, and public cover
case `Root.Idle::transition::Root.Done::0`.

```fbmcq-executable
init state("Root.Idle");
check reach <= 1: active("Root.Idle");
```

```fbmcq-executable
init state("Root.Idle");
check forbid <= 1: active("Root.Done");
```

```fbmcq-executable
init state("Root.Idle");
check invariant <= 1: x == 0;
```

```fbmcq-executable
init state("Root.Idle");
check must_reach <= 1: active("Root.Idle");
```

```fbmcq-executable
init state("Root.Idle");
check exists_always <= 1: x == 0;
```

```fbmcq-executable
init state("Root.Idle");
assume event("Root.Go", 0) == true;
check cover <= 1: case("Root.Idle::transition::Root.Done::0");
```

```fbmcq-executable
init state("Root.Idle");
check reach <= 1:
    called("Root.Idle.Tick", step=0, role="leaf_during", where x == 0)
    && call_count("Root.Idle.Tick", step=*) == 1;
```

Each executable example is validated against the real model by deterministic
tests. When an execution trace is present, it is replayed through the runtime.

The following source-only example intentionally uses names from a hypothetical
supplied model. It documents legal authoring forms that cannot be bound to the
small executable example model above. Do not copy its paths into another task
without matching model facts.

```fbmcq
init terminated havoc * where terminated();
assume always: ((retries >= 0) && !terminated()) || terminated();
assume at 0: var("cycle") >= 0;
assume event("Root.Start", *) != true;
assume event("Root.Reset", 0..2) == false;
assume events cardinality any;
assume events cardinality at_most_one {"Root.Start", "Root.Reset"};
check exists_always <= 3:
    called(action="Root.Controller.Hook", step=-2..+0, stage="during",
           role="leaf_during", state="Root.Controller",
           active_leaf="Root.Controller.Active", named_ref=null,
           where abs(retries) >= 0)
    || call_count("Root.Controller.Hook", step=..+2) >= 0;
```

## Invalid Examples

The fence label identifies the expected failure stage. Do not call every error
a parser error.

```fbmcq-invalid-parse
check reach <= : true;
```

```fbmcq-invalid-structure
check cover <= 1: active("Root.Idle");
```

```fbmcq-invalid-model
check reach <= 1: active("Root.Unknown");
```

```fbmcq-invalid-unsupported
check reach <= 1: sin(x) > 0;
```

## Pre-Output Checklist

Before returning a query artifact, verify:

1. It contains only one complete `.fbmcq` query and no fence or prose.
   This remains true even when the task packet itself contains fenced examples.
2. Every path, variable, event, action, and case label is known and authorized.
3. The property kind and its result meaning match the stated intent.
4. The bound covers every referenced frame, step, and response window.
5. Initial state, `havoc`, `where`, and assumptions have explicit task support.
6. The predicate is defined where it is evaluated, relevant, and non-constant.
7. The query cannot pass only because its initial or environmental constraints
   rule out every execution.

## Good And Bad Query Patterns

| Dimension | Good FBMCQ | Bad FBMCQ |
|---|---|---|
| Model reference | Uses a supplied exact path and meaning | Guesses a path from prose |
| Property | Matches the desired witness or violation question | Changes property kind to force a result |
| Bound | Covers the requested frame or window | Uses an off-by-one or too-short bound |
| Initialization | Preserves the requested start policy | Hot-starts or relaxes variables without authority |
| Assumption | States an explicit environment rule | Silently removes a counterexample |
| Predicate | Tests a requirement-relevant, defined condition | Uses a constant or unrelated condition |
| Response | Requires a later response and reports incomplete windows | Counts the trigger frame or calls incomplete success |
| Explanation | Limits conclusions to the selected bound | Claims a finite query proves all future behavior |
