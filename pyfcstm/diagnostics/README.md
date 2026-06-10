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
