# Generic UNSAT proofs

## Approved scope

Implement the standalone solver subsystem agreed in the design discussion. Its
public caller supplies an exact named conjunction and receives a native Z3
refutation, readable deductions, expandable evidence and optional source links.
Deliver a main-based pull request, TDD evidence, 100% branch coverage for changed
production code, a fresh review, passing required checks, and a new PR comment
showing real executable examples and their complete readable output.

The broader BMC integration is a subsequent consumer: this change supplies its
rule/source/reading extension contracts without replacing the BMC CLI in this
PR. Existing BMC behavior must keep passing. The user approved direct replacement
when that integration happens, without compatibility wrappers.

Full system design: https://scngnprmusv9.feishu.cn/wiki/BOKfwCZ7QiPuvhkMd8QcPmxan5f

## Inputs and public API

Reuse the previously developed shapes of `UnsatConstraint(stable_id,
expressions, source=None)` and `UnsatQuery(query_id, constraints,
background=())`. Every expression is Boolean in one Z3 context, identifiers are
nonempty and unique, background is explicit and never removed. Duplicate ASTs
can have multiple source occurrences. Sources are metadata, never premises.

`explain_unsat(query, *, mode="proof", minimize=False, timeout_ms=None,
names=None, extensions=None)` returns `UnsatReport`. `mode="core"` provides
checked conditions without claiming a derivation. `SymbolNames` binds actual
expressions, not decoded variable names. `SourceDescription` is the simple
serializable source form; a `SourceAdapter` handles application objects.

## Proof and reading

Create an isolated proof-enabled Z3 context and translate original expressions.
Record native DAG parent order, rule parameters, non-proof operands, typed term
references, definitions and input occurrence bindings. Never parse a pretty
printed proof to reconstruct it. Different executions have separate identities.

Propagate local hypotheses and discharge them according to the native rule.
An accepted refutation concludes False with no open hypotheses. Unknown rules
remain visible with partial status. Quantifier binders cannot be treated as
ordinary application arguments. Linear arithmetic uses exact coefficients and
strictness, not floating point or inferred certificates.

`ProofReading.to_text(language="en" | "zh")` prints a complete organized
derivation. `get_block`, `expand`, `get_source` and `to_canonical` support
machine navigation. Mechanical rewriting can be folded, but every conclusion
retains premises, scope and evidence. Important unsupported theory steps make
the reading partial. No LLM is required to produce text.

The minimum acceptance examples are:

1. `x0 >= 0`, `x1 == x0 + 1`, `x1 < 0`, plus an unrelated condition. Explain the
   arithmetic contradiction, and optionally establish group-subset minimality.
2. `x1 == If(x0 >= 0, x0 + 1, 0)`, `x1 < 0`. Explain the ITE bound or both
   exhaustive branches and their closed assumptions. Never assume a value for x0.
3. Fixed-background contradiction, duplicates, SAT, UNKNOWN, timeout, a
   source adapter for a non-BMC domain, a valid fold and a rejected unsound fold.

Exact sentences may vary with the native proof, but cannot become manually
authored answers keyed to an example. Any extra explanatory deduction requires
local evidence and cannot use the full UNSAT query to prove an arbitrary claim.

## Extensibility

An immutable per-call `ProofExtensions` holds `rule_handlers`, `source_adapter`
and `reading_folders`. Rule handlers interpret existing evidence; ambiguous
matches are errors. Folders propose subgraphs with explicit external premises,
conclusions, assumptions and source links. The core verifies the boundary before
accepting a fold. Source links distinguish logical, construction and context
relations. Untrusted serialized input is validated through the public loader.

The data reader must work without loading Z3. Exports share term and node tables
and contain no product/schema dispatch version fields. Public snapshots must be
isolated from mutable caller metadata. Plugins are trusted Python code, not an
independent certification boundary.

## Minimization, limits and failures

Save a full proof before optional core extraction/deletion. Accept a deletion
only on UNSAT. Keep candidates on UNKNOWN and do not claim minimality unless
deletion checks establish it. Reprove the retained subset; never splice proof
nodes across executions. Condition minimization does not promise shortest proof.

One monotonic budget covers a call's solving, minimization and assembly.
Rendering an already saved reading is independent of that budget. Timeouts are
cooperative, not hard process/memory isolation. Distinguish solver outcome,
proof availability, input/scope/rule checks, source and reading completeness,
minimization and stop reason. Invalid evidence is not a complete explanation.

## Compatibility and acceptance

Python 3.7–3.14; Windows, Linux and macOS; existing z3-solver dependency only.
Public APIs use reST docstrings with executable examples. Tests enter public
surfaces, exercise real Z3 behavior and have independently derived expectations.
Dependency timeout/UNKNOWN injection is allowed, forged internal state is not.
No coverage exclusions to hide changed branches. Deleted behavior is covered
by its replacement/regression tests; it has no executable final-branch arcs.

Verify all changed executable lines and branch destinations, all regression
tests, doctests, generated API docs, packaging/CI gates and real demo outputs.
Do not merge the PR; deliver it ready for merge.
