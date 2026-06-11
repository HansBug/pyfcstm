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
`: /GlobalEvent` for events scoped from the root.

Guards use `: if [condition]`. Effects use `effect { ... }`. Do not combine
event syntax and guard syntax on the same transition.

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

        Up -> Down : if [(request_above == 0) xor (target_level < current_level)];
    }

    Stopped -> Moving : if [rank_ok > 0 && target_level != current_level];
    Moving -> Stopped : if [(target_level == current_level) iff (rank_ok > 0)];
}
```

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

Do not write `:/EventName`; that is a shorthand in prose, not valid DSL.

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

- Initial entry through a composite state runs the composite `enter`, then
  plain `during before`, then the selected child `enter`.
- A normal active-state cycle runs ancestor `>> during before`, then the active
  leaf `during`, then ancestor `>> during after`.
- A child-to-child transition runs source child `exit`, then transition effect,
  then target child `enter`. Plain composite `during before` and
  `during after` do not wrap child-to-child transitions.
- Exiting a composite state runs child `exit`, then plain composite
  `during after`, then composite `exit`.
- `>> during before` and `>> during after` are aspect actions for descendant
  leaf states; plain `during` is the ordinary active-state action.

## LLM Modeling Strategy

- Prefer events for discrete external triggers.
- Prefer guards for state-dependent or variable-dependent conditions.
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
model.

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

## Pre-Output Checklist

Before producing final FCSTM source, check:

- exactly one top-level root state
- all variables are declared before the root state
- every composite state has an initial transition
- each transition uses event syntax or guard syntax, not both
- `: /GlobalEvent` is used for root-scoped events
- `=>`, `implies`, `xor`, and `iff` are used only in conditions
- `^` is not used as boolean xor
- forced transitions have no effect block
- final output is raw `.fcstm` source, not Markdown
