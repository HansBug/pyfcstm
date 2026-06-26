# Diagnostics span and range contract

This directory owns the shared diagnostic contract used by `pyfcstm` and
`jsfcstm`. The contract separates three range layers that downstream tools must
not conflate.

## Range layers

- **problem range**: the published diagnostic location. It should identify the
  object described by the diagnostic `code`, `message`, and `refs` payload.
- **fix-edit range**: the insertion, deletion, or replacement range used by a
  suggested fix. This range is only for code-action/edit planning and may be an
  insertion point rather than the problem object.
- **related range**: a secondary location such as a previous declaration,
  duplicate transition, normal transition overridden by a forced transition, or
  shadowed declaration.

## `Span` coordinates

`pyfcstm` emits `Span` objects in `ModelDiagnostic.span` and in refs fields such
as `<object>_span` or `<object>_spans`.

A `Span` uses **1-based, end-exclusive** coordinates:

- `line` / `column` identify the first covered source position.
- `end_line` / `end_column` identify the first source position after the covered
  text.
- `end_line == line` and `end_column == column` is a point-style span; semantic
  diagnostics should avoid point-style spans unless the diagnostic is genuinely
  about an insertion point.

This matches Python source slicing by subtracting one from both start and end
columns. For example, a single-line span `{line: 2, column: 5, end_line: 2,
end_column: 8}` covers source columns 5, 6, and 7.

## LSP `Range` conversion

`jsfcstm` editor APIs publish LSP Range-compatible `Range` values, which are
**0-based, end-exclusive**. All inspect-derived conversions from pyfcstm-style
`Span` values to LSP `Range` values must go through the centralized
`spanToRange()` helper.

The conversion is mechanical:

- `start.line = line - 1`
- `start.character = column - 1`
- `end.line = end_line - 1`
- `end.character = end_column - 1`

Existing LSP-shaped ranges are already 0-based/end-exclusive and are accepted by
`spanToRange()` for compatibility with older jsfcstm inspect payloads and test
fixtures.

## Refs naming rules

`ModelDiagnostic.refs` is declared per code in `codes.yaml`.

- A field named `<object>_span` carries a `Span` for one related source object.
- A field named `<object>_spans` carries `list[Span]`; individual entries may be
  `null` when a specific related object has no source span.
- Related spans use the same 1-based, end-exclusive coordinate system as
  `ModelDiagnostic.span`.

`codes.yaml` also declares `span_object` for every code. This names the semantic
object that the primary problem range is expected to identify. Some diagnostics
allow reasonable precision differences across implementations: one side may
cover an identifier while the other covers the containing declaration or
transition, but both source slices must still hit the same problem object.

## C/C++ deployment profile numeric contract

The numeric diagnostics catalog also declares a target-specific contract for the
current C/C++ family templates. This contract is intentionally separate from the
core FCSTM model semantics: it describes risks that matter when a model is
rendered into C/C++ generated code, not target-independent model errors.

The default C/C++ deployment profile is:

- `target_family`: `c_family`
- `target_templates`: `c`, `c_poll`, `cpp`, `cpp_poll` in that order
- DSL `int`: `PYFCSTM_GENERATED_INT64`, a 64-bit signed integer with range
  `[-9223372036854775808, 9223372036854775807]`
- DSL `float`: C/C++ `double`

Python generated runtimes may not have the same risks. For example, Python
integers are not bounded to this 64-bit C-family profile, and Python exception
semantics for division by zero are not the same as a C/C++ deployment failure
policy. Numeric diagnostic messages and `refs` payloads therefore must state the
C/C++ target profile explicitly instead of reporting a generic FCSTM model
error.

### Numeric `refs` fields

Every C/C++ numeric warning in the shared catalog carries these target fields:

| Field | Contract |
|---|---|
| `target_family` | The string `c_family`. |
| `target_templates` | The ordered list `c`, `c_poll`, `cpp`, `cpp_poll`; Python is not included. |
| `runtime_note` | Human-readable note that distinguishes C/C++ deployment risk from Python generated runtime behavior. |
| `context` | One of `var_initializer`, `guard`, `transition_effect`, `lifecycle_action`. |
| `statement_kind` | Optional `operation_assignment` when the expression is an assignment right-hand side. |
| `expr_text` | Source text for the expression shape being diagnosed. |

Rule-specific fields are declared in `codes.yaml`. The first C/C++ numeric
contract covers:

- integer literals outside the default signed 64-bit range;
- constant `/` or `%` with a right-hand side that folds to zero;
- constant shift counts outside `0 <= count < 64`;
- float-shaped operands in bitwise or shift operators.

For the signed 64-bit boundary, a unary sign is interpreted together with the
literal for contract classification: `9223372036854775808` is outside the upper
bound, `-9223372036854775808` is the legal lower bound spelling, and
`-9223372036854775809` is below the lower bound.

### Lightweight constant folding boundary

The numeric contract only assumes a lightweight, literal-only constant folder.
It may fold numeric literals, unary `+` / `-`, parentheses, and literal-only
uses of `+`, `-`, `*`, `/`, `%`, `<<`, `>>`, `&`, `^`, and `|` when both ends can
represent the result consistently. It must not fold through division by zero,
negative shifts, oversized shifts, variables, function calls, cross-statement
constant propagation, block-local temporary inference, or algebraic rewrites such
as `a - a` and `0 * x`.

The numeric analyzer now emits these warnings under
`emit_tier: static_pipeline` on both pyfcstm and jsfcstm. Tests for these entries
must validate the shared catalog contract, Python `inspect_model()` /
`build_inspect_json()` output, jsfcstm `inspectModel()` output, and the
`collectDocumentDiagnostics()` editor surface. Numeric warnings are still
C/C++ deployment-profile diagnostics: Python generated runtimes are documented as
a different target semantics rather than part of the C/C++ target set.
