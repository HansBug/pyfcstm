# FCSTM Inspect Repair Prompt Template

You are repairing one FCSTM model. Return only the repaired `.fcstm` source.
Do not include Markdown fences or prose.

## Repair rules

- Make the smallest source edit that preserves the apparent model intent.
- Use the official grammar guide as the syntax authority.
- Use the inspect report location, provenance, recommended actions, and do-not text before changing the model.
- Do not add dummy assignments, self-loops, unconditional exits, or guard constants only to silence diagnostics.
- Do not delete states or transitions unless the report and the model intent clearly justify deletion.
- If a diagnostic is `inspect-static`, do not treat it as an SMT proof.
- If a diagnostic is `verify-backed`, treat it as solver-backed evidence for the specific reported property.
- A repair is acceptable only when parse/model loading succeeds and all `error` and `warning` diagnostics are gone.
- `info` diagnostics may remain when the report says they can describe intentional modeling style, such as an unconditional fall-through.
- When you need to explain your choice, put the explanation outside any FCSTM fenced block; the evaluator will extract the fenced FCSTM source.
- If replacing a guarded transition with an event transition makes a variable unused, also remove that variable or keep a real guard-affecting data-flow path.
- Do not invent event declarations or standalone state event handlers; FCSTM events are introduced by transition syntax.

## Official grammar guide

# FCSTM Grammar Guide for LLMs

Use this guide when generating `.fcstm` source for pyfcstm. The goal is a
model that parses and passes model semantic validation on the first attempt.
This guide is not an ANTLR grammar replacement and it does not validate
business correctness, simulation coverage, or formal properties.

## Output Contract

Return only FCSTM source when the caller asks for a model. Do not wrap the
answer in Markdown fences. Do not add prose before or after the model.

Every generated model must have:

- zero or more root-level variable definitions
- exactly one top-level `state`
- one initial transition, `[*] -> Child;`, inside each composite state
- only declared variables in guards and operation blocks

## Top-Level Structure

Variable definitions come before the root state:

```fcstm
def int car_count = 0;
def int ambulance_detected = 0;
def int neighbor_green = 0;

state TrafficController {
    [*] -> Normal;

    state Normal {
        [*] -> NorthGreen;

        state NorthGreen {
            during { car_count = car_count + 1; }
        }

        state EastGreen;

        NorthGreen -> EastGreen : if [car_count > 10 && ambulance_detected == 0] effect {
            car_count = 0;
        }
        EastGreen -> NorthGreen : if [ambulance_detected > 0] effect {
            neighbor_green = 1;
        }
    }
}
```

## State Definitions

Use `state Name;` for a leaf state and `state Name { ... }` for a composite
state. A composite state must choose its first active child with an initial
transition. Use `pseudo state Name;` only for a leaf state that should skip
ancestor `>> during before` and `>> during after` aspect actions.

```fcstm
def int link_ok = 1;
def int command_ready = 0;

state MissionManager {
    [*] -> Standby;

    state Standby;

    state MissionMode {
        [*] -> ParseCommand;

        state ParseCommand;
        state FlyHome;

        ParseCommand -> FlyHome :: FlyHomeRequested;
        FlyHome -> ParseCommand : if [link_ok > 0];
    }

    state CommandMode;

    Standby -> MissionMode : if [command_ready > 0];
    MissionMode -> CommandMode : if [link_ok == 0];
    CommandMode -> MissionMode :: ManualReleased;
}
```

```fcstm
def int bypass_count = 0;

state PseudoExample {
    [*] -> Normal;

    >> during before {
        bypass_count = bypass_count + 1;
    }

    state Normal;
    pseudo state Bypass;

    Normal -> Bypass :: SkipAspect;
    Bypass -> Normal :: Resume;
}
```

## Transitions

Use plain transitions for unconditional movement, `:: EventName` for source
local events, `: EventName` for events scoped to the containing state, and
`: /GlobalEvent` for events scoped from the root. Absolute event paths start
below the root state; write `: /Bus.E1`, not `: /Root.Bus.E1` when the root
state is named `Root`.

Guards use `: if [condition]`. The pure guard alias `: [condition]` is also
valid and means the same thing as `: if [condition]`. Effects use
`effect { ... }`.

```fcstm
def int current_level = 0;
def int target_level = 0;
def int request_above = 0;
def int rank_ok = 1;

state Elevator {
    [*] -> Stopped;

    state Stopped;

    state Moving {
        [*] -> Up;

        state Up;
        state Down;

        Up -> Down : [(request_above == 0) xor (target_level < current_level)];
    }

    Stopped -> Moving : if [rank_ok > 0 && target_level != current_level];
    Moving -> Stopped : if [(target_level == current_level) iff (rank_ok > 0)];
}
```

Combo transition triggers are ordered `+` chains of event terms and bracketed
guard terms. They are syntax sugar: model construction expands them into
ordinary pseudo states and normal transitions. Runtime, verification, code
generation, and visualization consume the expanded model. Event terms match
events present in the current cycle; repeated identical event terms are allowed
and remain presence-based, so one matching input event can satisfy that repeated
term chain, although inspect reports it as a likely typo. Generated combo pseudo
states are visible in diagrams with stable names, and state names beginning with
`__combo_` are reserved for generated pseudo states.

```fcstm
def int ready = 1;
def int completed = 0;

state ComboProtocol {
    [*] -> Waiting;

    state Waiting;
    state Accepted {
        enter { completed = 1; }
    }
    state Retrying;

    Waiting -> Accepted :: Request + [ready > 0] + Confirm;
    Waiting -> Retrying :: Request;
    Retrying -> Waiting : [ready == 0];
}
```

Combo rules to keep in mind:

- `S -> T :: E1 + [x > 0] + E2;` uses source-local event terms.
- `S -> T : E1 + /Bus.E2 + [x > 0];` uses containing-scope event terms
  except for explicitly absolute event terms.
- `[*] -> S :: E1 + E2;` is valid; entry-transition events follow the legacy
  entry event rule and are scoped to the composite that owns the entry.
- `S -> [*] :: E1 + E2;` is valid; if later validation cannot reach a
  stoppable state, the transition chain rolls back like any pseudo-state chain.
- `::` combo triggers must contain at least one event term. Use `:` for
  all-guard chains such as `S -> T : [x > 0] + [y > 0];`.
- Do not append `if [condition]` after an event trigger. Write the condition as
  a bracketed combo term: `S -> T :: E + [x > 0];`.
- Do not mix a new `:` or `::` prefix inside one combo chain, and do not use
  combo triggers on forced transitions.
- Transition priority remains declaration order and first-accepted-wins, not
  longest-match-wins. Prefix sharing is allowed only when it preserves that
  order. For example, in `E1 + E2`, then plain `E1`, then `E1 + E3`, a cycle
  containing `E1` and `E3` selects the plain `E1` fallback because it is written
  before the later combo branch.

Combo inspect diagnostics keep the public report tied to the author-written
combo trigger, not to the generated pseudo states:

- `inspect` JSON exposes generated edges in `combo_transitions` and grouped
  source provenance in `combo_origins`.
- `W_COMBO_DUPLICATE_EVENT` means the same event term appears more than once in
  one combo trigger. The primary `span` points at the repeated term; `refs`
  include `origin_id`, `term_index`, `first_term_index`, `term_span`, and
  `first_term_span`.
- `W_COMBO_GUARD_CONST_TRUE` and `W_COMBO_GUARD_CONST_FALSE` are Python inspect
  warnings proven with Z3. The primary `span` points at the original bracketed
  guard term; `refs.value_span` points at the condition inside the brackets.
- `W_COMBO_GUARD_PREFIX_IMPLIED` means earlier guard terms in the same combo
  prefix already imply the current guard. `W_COMBO_GUARD_PREFIX_CONTRADICTS`
  means the earlier guard prefix makes the current guard impossible. Their
  primary `span` points at the current guard term, and `refs.prior_term_span`
  points at the decisive earlier guard.
- Guard warnings are conservative: if conversion to Z3 is unsupported, or an
  effect/lifecycle action may write variables read by the guard prefix, inspect
  skips the prefix warning instead of reporting a speculative result.
- `jsfcstm` does not reimplement these solver-backed guard warnings locally;
  downstream JavaScript tools should consume the Python inspect JSON when they
  need these codes.

## Nested State Targets

Transitions are resolved in their current state scope. Do not write a root-level
transition directly to a leaf state nested inside a composite state unless that
name is visible in the current scope.

For hierarchical controllers, prefer one of these patterns:

- Put transitions to internal child states inside the composite that owns those
  child states.
- From an outer state, transition to the composite state and let its initial
  transition choose the first child.
- For supervisor commands such as `Fly Home`, set or test a request variable at
  the outer scope, then transition inside the owning composite from a parser or
  dispatcher child to the requested behavior child.

```fcstm
def int fly_home_request = 0;
def int link_ok = 1;

state MissionManager {
    [*] -> Standby;

    state Standby;

    state MissionMode {
        [*] -> ParseCommand;

        state ParseCommand;
        state FlyHome;

        ParseCommand -> FlyHome : if [fly_home_request > 0 && link_ok > 0];
        FlyHome -> ParseCommand :: FlyHomeComplete;
    }

    Standby -> MissionMode : if [fly_home_request > 0];
}
```

Do not write `MissionMode -> FlyHome : /DataLinkLost;` at the outer scope when
`FlyHome` is nested inside `MissionMode`. Put the transition inside
`MissionMode`, or route the outer event through a declared request variable.

## Events

Event scopes are part of the model semantics:

- `Source -> Target :: EventName;` creates a source-local event.
- `Source -> Target : EventName;` creates or uses an event in the containing state scope.
- `Source -> Target : /EventName;` creates or uses a root-scoped event.

Combo event terms inherit the same scope rules from their leading prefix. A
continuation term may be absolute, for example `S -> T : E1 + /Bus.E2;`. Do not
write `:/EventName`; that is a shorthand in prose, not valid DSL.

## Forced Transitions

Forced transitions expand to multiple normal transitions. They cannot have
effect blocks. Put side effects in the target state's `enter` block when the
natural-language requirement needs a shared action.

```fcstm
def int error_count = 0;

state Plant {
    [*] -> Running;
    !* -> Error :: EmergencyStop;

    state Running {
        [*] -> Idle;
        state Idle;
        state Busy;
        Idle -> Busy :: Start;
        Busy -> Idle :: Done;
    }

    state Error {
        enter { error_count = error_count + 1; }
    }
}
```

## Lifecycle Actions

Use `enter`, `during`, and `exit` for state lifecycle behavior. Operation
blocks assign numeric expressions to variables. Undeclared names assigned
inside a block are temporary variables local to that block.

Use `abstract` when generated runtime code must provide the behavior. Use
`ref` only to reference a named lifecycle action that exists in the model.

```fcstm
def int boot_count = 0;
def int ready = 0;

state LifecycleExample {
    [*] -> Idle;

    enter SharedInit {
        boot_count = boot_count + 1;
    }
    exit abstract SharedCleanup;

    state Idle {
        enter ref /SharedInit;
        during abstract PollSensors;
        exit ref /SharedCleanup;
    }

    state Active {
        enter StartActive {
            ready = 1;
        }
        exit ref /SharedCleanup;
    }

    Idle -> Active : if [ready == 0];
}
```

## Aspect Actions

Use `>> during before` and `>> during after` on composite states when an action
must wrap descendant leaf-state cycles. Use plain `during` on leaf states.

```fcstm
def int monitor_count = 0;
def int local_count = 0;

state AspectExample {
    [*] -> Running;

    >> during before {
        monitor_count = monitor_count + 1;
    }
    >> during after abstract PublishSnapshot;

    state Running {
        [*] -> Work;

        state Work {
            during {
                local_count = local_count + 1;
            }
        }
    }
}
```

## Expressions

Arithmetic and boolean expressions are separate. Guards use boolean
conditions. Assignments use numeric expressions. Comparisons bridge numeric
expressions into boolean conditions.

Condition operators include:

- `&&` and `and`
- `||` and `or`
- `!` and `not`
- `=>` and `implies`
- `xor`
- `iff`
- `==` and `!=` between conditions

`=>` is material implication: `A => B` means `!A || B`. Use it only when a
requirement explicitly says that a true premise forces a conclusion. For normal
state-change guards, `&&` and `||` are usually clearer.

Do not use `->` for implication. It is transition syntax. Do not use `^` for
boolean xor in conditions; use `xor`. Numeric `^` remains bitwise xor inside
numeric expressions.

## Cycle Semantics

FCSTM models cycle-based control systems. One cycle executes active-state
behavior and enabled transitions according to pyfcstm semantics. The parser
and semantic validator check model structure and expression legality; they do
not prove that the model matches the physical timing or business requirement.

Execution-order essentials:

- Initial entry through a composite state runs the composite `enter`,
  selects and applies the initial transition, then runs plain `during before`,
  then enters the selected child. A plain `during before` action must not
  affect the guard decision for that same composite's current initial
  transition.
- A normal active-state cycle runs ancestor `>> during before`, then the active
  leaf `during`, then ancestor `>> during after`.
- A child-to-child transition runs source child `exit`, then transition effect,
  then target child `enter`. Plain composite `during before` and
  `during after` do not wrap child-to-child transitions.
- Exiting a composite state runs child `exit`, then plain composite
  `during after`, then composite `exit`.
- `>> during before` and `>> during after` are aspect actions for descendant
  leaf states; plain `during` is the ordinary active-state action.
- Combo transition triggers behave like the pseudo-state chains produced during
  model construction. All required events and guard terms in that chain must be
  available or true in the same cycle for the final target to be reached.

## LLM Modeling Strategy

- Prefer events for discrete external triggers.
- Prefer guards for state-dependent or variable-dependent conditions.
- Use combo triggers for ordered multi-event or event-plus-guard handshakes
  that must complete in one cycle. Keep the source order intentional, because
  transition priority follows the written order.
- Declare every persistent value as `def int` or `def float`.
- Use integer flags such as `flag > 0` instead of bare boolean variables.
- Do not invent syntax for timers, arrays, quantifiers, or assumptions unless
  the user explicitly targets a future extension outside current pyfcstm.
- When a natural-language requirement has a time delay, encode a counter
  variable only if that is sufficient for a legal discrete model.

## Worked Protocol Example

```fcstm
def int request_sent = 0;
def int agreement_received = 0;
def int merge_complete = 0;

state PlatoonJoin {
    [*] -> Cruising;

    state Cruising;
    state Requesting {
        enter { request_sent = 1; }
    }
    state Aligning;
    state Joined {
        enter { merge_complete = 1; }
    }

    Cruising -> Requesting :: JoinRequested;
    Requesting -> Aligning : if [request_sent > 0 && agreement_received > 0];
    Aligning -> Joined :: MergeComplete;
}
```

## Invalid Forms To Avoid

These examples are intentionally invalid and should not be copied into a final
model. Some are grammar-level errors; scope-path mistakes such as
`/Root.Bus.E1` can still parse but must be rejected by model validation because
absolute paths already start below the root state.

```fcstm-invalid
def int x = 0;
def int y = 0;
state BadXor {
    [*] -> A;
    state A;
    state B;
    A -> B : if [x > 0 ^ y > 0];
}
```

```fcstm-invalid
def int x = 0;
state BadGuardScope {
    [*] -> A;
    state A;
    state B;
    A -> B :: if [x > 0];
}
```

```fcstm-invalid
def int count = 0;
state BadForcedEffect {
    [*] -> Running;
    state Running;
    state Error;
    !* -> Error :: Emergency effect { count = count + 1; }
}
```


```fcstm-invalid
state BadEventGuardSuffix {
    [*] -> A;
    state A;
    state B;
    A -> B :: E if [1 > 0];
}
```

```fcstm-invalid
def int x = 0;
state BadLocalAllGuardCombo {
    [*] -> A;
    state A;
    state B;
    A -> B :: [x > 0] + [x < 10];
}
```

```fcstm-invalid
state BadForcedCombo {
    [*] -> A;
    state A;
    state B;
    !* -> B :: E1 + E2;
}
```

```fcstm-invalid
state BadMixedScopeCombo {
    [*] -> A;
    state A;
    state B;
    A -> B :: E1 + : E2;
}
```

```fcstm-invalid
state BadAbsoluteRootRepeat {
    [*] -> A;
    state A;
    state B;
    A -> B : /BadAbsoluteRootRepeat.Bus.E1 + /BadAbsoluteRootRepeat.Bus.E2;
}
```

## Pre-Output Checklist

Before producing final FCSTM source, check:

- exactly one top-level root state
- all variables are declared before the root state
- every composite state has an initial transition
- each transition uses plain, one-event, one-guard, or legal combo trigger syntax
- event-plus-guard requirements use combo terms such as `:: E + [x > 0]`, not
  `:: E if [x > 0]`
- `: /GlobalEvent` is used for root-scoped events, without repeating the root
  state name after `/`
- `=>`, `implies`, `xor`, and `iff` are used only in conditions
- `^` is not used as boolean xor
- forced transitions have no effect block
- final output is raw `.fcstm` source, not Markdown


## Input FCSTM

```fcstm
def int ready = 1;

state Root {
    [*] -> Waiting;

    state Waiting;
    state Accepted;

    Waiting -> Accepted :: Request + Request;
    Accepted -> [*];
}

```

## Inspect report

{
  "diagnostics": [
    {
      "code": "W_COMBO_DUPLICATE_EVENT",
      "do_not": [
        "Do not silently delete the repeated event; the explicit pseudo-chain shape may be intentional."
      ],
      "location": {
        "column": 38,
        "end_column": 45,
        "end_line": 9,
        "line": 9,
        "path": "input.fcstm"
      },
      "message": "Combo trigger repeats event 'Root.Waiting.Request'; this is legal but usually redundant.",
      "provenance": {
        "kind": "inspect-static",
        "verify_required": false
      },
      "recommended_actions": [
        {
          "kind": "inspect_terms",
          "rationale": "Check whether the second event was meant to be a different event.",
          "target": "transition"
        },
        {
          "kind": "keep_if_intentional",
          "rationale": "Keep it only if the explicit two-hop pseudo chain is intentional.",
          "target": "transition"
        }
      ],
      "refs": {
        "event_name": "Root.Waiting.Request",
        "first_term_index": 0,
        "first_term_span": {
          "column": 28,
          "end_column": 35,
          "end_line": 9,
          "line": 9
        },
        "first_term_text": "Request",
        "origin_id": "Root:Waiting->Accepted::: Request + Request",
        "term_index": 1,
        "term_span": {
          "column": 38,
          "end_column": 45,
          "end_line": 9,
          "line": 9
        },
        "term_text": "Request",
        "transition_span": {
          "column": 5,
          "end_column": 46,
          "end_line": 9,
          "line": 9
        },
        "trigger_span": {
          "column": 25,
          "end_column": 45,
          "end_line": 9,
          "line": 9
        }
      },
      "repair_guidance": [
        "Repeated identical event terms are presence-based and are usually redundant.",
        "If there is no evidence that the explicit two-hop pseudo chain is intentional, reducing the duplicated term to one event is the smallest semantic repair."
      ],
      "severity": "warning",
      "source": "inspect-static",
      "source_excerpt": {
        "caret": "                                     ^^^^^^^",
        "context": [
          {
            "caret": null,
            "is_anchor": false,
            "line": 8,
            "text": ""
          },
          {
            "caret": "                                     ^^^^^^^",
            "is_anchor": true,
            "line": 9,
            "text": "    Waiting -> Accepted :: Request + Request;"
          },
          {
            "caret": null,
            "is_anchor": false,
            "line": 10,
            "text": "    Accepted -> [*];"
          }
        ],
        "line": 9,
        "text": "    Waiting -> Accepted :: Request + Request;"
      },
      "summary": "The combo trigger contains the same resolved event twice, for example ``E1 + E1``. This is legal but normally redundant because one cycle's input event set already contains ``E1``."
    },
    {
      "code": "W_UNREFERENCED_VAR",
      "do_not": [
        "Do not add a dummy guard reference only to silence the diagnostic."
      ],
      "location": {
        "column": 1,
        "end_column": 19,
        "end_line": 1,
        "line": 1,
        "path": "input.fcstm"
      },
      "message": "Variable 'ready' does not affect any transition guard.",
      "provenance": {
        "kind": "inspect-static",
        "verify_required": false
      },
      "recommended_actions": [
        {
          "kind": "remove_variable",
          "rationale": "Remove the variable and related writes if it was speculative scaffolding.",
          "target": "variable_definition"
        },
        {
          "kind": "connect_to_guard",
          "rationale": "Add the missing data-flow path if the variable should affect a transition decision.",
          "target": "guard_or_assignment"
        }
      ],
      "refs": {
        "definition_delete_anchor": "ready",
        "init_value": "1",
        "suggested_fix": {
          "anchor": {
            "ref": "refs.definition_delete_anchor",
            "type": "ref"
          },
          "kind": "delete",
          "rationale": "Remove the declaration-only variable because it has no DSL reads or writes.",
          "target": "variable_definition",
          "text": ""
        },
        "var_name": "ready"
      },
      "repair_guidance": [
        "A declaration-only variable may be speculative scaffolding.",
        "Remove it only when no guard, assignment, abstract action, or external integration intent needs it."
      ],
      "severity": "warning",
      "source": "inspect-static",
      "source_excerpt": {
        "caret": "^^^^^^^^^^^^^^^^^^",
        "context": [
          {
            "caret": "^^^^^^^^^^^^^^^^^^",
            "is_anchor": true,
            "line": 1,
            "text": "def int ready = 1;"
          },
          {
            "caret": null,
            "is_anchor": false,
            "line": 2,
            "text": ""
          }
        ],
        "line": 1,
        "text": "def int ready = 1;"
      },
      "summary": "This variable does not participate in model decisions. It is dead from the DSL's guard-affect data-flow perspective."
    },
    {
      "code": "I_TRANSITION_NEVER_EVENT_TRIGGERED",
      "do_not": [
        "Do not add a meaningless event just to silence this info."
      ],
      "location": {
        "column": 5,
        "end_column": 21,
        "end_line": 10,
        "line": 10,
        "path": "input.fcstm"
      },
      "message": "Transition 'Root.Accepted' -> '[*]' has no event or guard.",
      "provenance": {
        "kind": "inspect-static",
        "verify_required": false
      },
      "recommended_actions": [
        {
          "kind": "keep_if_fallthrough",
          "rationale": "Keep it when the state should immediately advance.",
          "target": "transition"
        },
        {
          "kind": "add_trigger_or_guard",
          "rationale": "Add the missing event or guard if the transition should wait.",
          "target": "transition"
        }
      ],
      "refs": {
        "from_path": "Root.Accepted",
        "to_path": "[*]",
        "transition_index": 3,
        "transition_span": {
          "column": 5,
          "end_column": 21,
          "end_line": 10,
          "line": 10
        }
      },
      "repair_guidance": [],
      "severity": "info",
      "source": "inspect-static",
      "source_excerpt": {
        "caret": "    ^^^^^^^^^^^^^^^^",
        "context": [
          {
            "caret": null,
            "is_anchor": false,
            "line": 9,
            "text": "    Waiting -> Accepted :: Request + Request;"
          },
          {
            "caret": "    ^^^^^^^^^^^^^^^^",
            "is_anchor": true,
            "line": 10,
            "text": "    Accepted -> [*];"
          },
          {
            "caret": null,
            "is_anchor": false,
            "line": 11,
            "text": "}"
          }
        ],
        "line": 10,
        "text": "    Accepted -> [*];"
      },
      "summary": "The transition is not event-triggered and has no guard. This may be a deliberate unconditional fall-through, so treat it as context rather than a fix target."
    }
  ],
  "input": "input.fcstm",
  "repair_protocol": {
    "goal": "repair the FCSTM model with the smallest semantic source change",
    "rules": [
      "Make the smallest source edit that preserves the modeler's apparent intent.",
      "Use diagnostic source/provenance before choosing a fix; inspect-static warnings are not solver proofs.",
      "Do not mechanically stack all suggested actions when multiple diagnostics refer to the same region.",
      "Do not delete states or transitions unless the report explicitly says the element is unused and the design intent supports deletion.",
      "A repair should clear all error and warning diagnostics; info diagnostics may remain when the model intent supports them.",
      "If changing a guard into an event-only transition makes a variable declaration unused, remove that variable or keep a real guard-affecting data-flow path."
    ]
  },
  "schema_status": "stable",
  "schema_version": "pyfcstm.inspect.llm.v1",
  "status": "warning",
  "summary": {
    "errors": 0,
    "infos": 1,
    "leaf_states": 2,
    "root_state_path": "Root",
    "states": 4,
    "transitions": 4,
    "variables": 1,
    "warnings": 2
  }
}


Return the repaired FCSTM source now.
