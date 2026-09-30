# Transition trigger contract

Implement the user-approved interface replacement for [issue #506](https://github.com/HansBug/pyfcstm/issues/506). Legacy Python constructor compatibility is intentionally not required. Legal DSL text and execution semantics remain unchanged.

## AST

`TransitionDefinition` has one `trigger: Optional[TransitionTrigger]`. `TransitionTrigger(scope_prefix, terms, trigger_span=None, legacy_guard_syntax=False)` holds a nonempty tuple of `EventTerm` or `GuardTerm`. Event terms contain `event_id`, `event_scope`, and existing source spans; guard terms contain `condition_expr` and existing spans. Single-term triggers represent ordinary transitions; multiple terms represent combo sequences. `None` alone represents unconditional transitions. Remove the old scalar transition fields and Combo-prefixed AST type names. Forced transition nodes use the same single trigger entry, restricted to one term.

Terms and triggers validate public construction and semantic assignment. Terms sequences are tuples; wrong types and empty sequences are rejected. AST provenance attachment remains possible. No duplicate guard alias storage. Existing spelling and event scope rules remain intact.

## Model

`Transition(from_state, to_state, trigger, effects, ...)` holds `None`, frozen `EventTrigger(event, scope=None)`, or frozen `GuardTrigger(condition)`. Constructors validate payload types. Transition trigger assignment validates before replacing, and old `event`, `guard`, `event_scope` assignments fail explicitly; no compatibility aliases. Model parent/provenance/effects remain editable. Combo expansion continues emitting one condition per edge, preserving relay sharing, priority, effects and provenance.

## Consumers and invariants

Migrate simulator, diagnostics, verify, BMC, diagram, PlantUML, import assembly, templates and public examples. Public inspect/BMC JSON field contracts remain unchanged. Do not add a diagnostic code or DSL grammar feature. Never flatten sequential combo conditions into a simultaneous conjunction. Python tests remain independent from JavaScript tests.

## Acceptance

TDD proves invalid construction/mutation fails, valid trigger replacement works, AST parser representation is canonical, and existing normal/initial/exit/combo behavior and DSL round trips remain correct. Regressions include source exit actions mutating guard variables, event absence, fallback priority, effects, event consumption and delta. All changed executable statements and branches must have 100% coverage through public paths. Run repository tests, doctests, generated RST and relevant documentation/template gates, independent review, then push a PR and watch all CI to ready-to-merge. Do not merge without separate authorization.

Python 3.7–3.14 and Windows/Linux/macOS remain supported; no new dependencies.
