# jsfcstm

`jsfcstm` is the JavaScript/TypeScript package boundary for FCSTM-related logic in this repository.

The package was introduced first as a publishable skeleton in Phase 0/1. It has now grown into the main reusable
FCSTM implementation for JavaScript consumers, while the VSCode extension stays focused on editor-host integration
and delegates language logic to `jsfcstm`.

## Current Scope

At the current phase, this package provides:

- ANTLR-backed FCSTM parser runtime generated from the canonical repository grammar
- AST nodes aligned with `pyfcstm.dsl.node` semantics and stable `pyNodeType` mapping
- stable `pyfcstm.model`-aligned `src/model/` objects for `StateMachine`, `State`, `Transition`, `Event`, actions, operations, and expressions
- semantic model construction and import-aware multi-file workspace graph support
- workspace graph snapshots that expose AST, semantic, and stable model layers together
- source range helpers and document abstractions
- editor-facing diagnostics, document symbols, completion, hover, definition, and document links
- reusable LSP converters, language-server core, and bundled server bootstrap entry points
- independent TypeScript build output under `dist/`
- independent Mocha-based unit tests
- coverage reporting via `c8`, including uncovered line numbers in the terminal report
- npm pack / publish-ready package metadata

## Current Layout

`jsfcstm` now uses a layered internal structure aligned with the Python package boundary:

- `src/ast/`: pyfcstm-aligned AST nodes and AST builder
- `src/config/`: package metadata and future package-level configuration
- `src/dsl/`: parser entry points and generated grammar runtime
- `src/editor/`: diagnostics, symbols, completion, hover, definition, and document links
- `src/lsp/`: LSP converters, request handlers, language-server core, and stdio bootstrap
- `src/model/`: stable pyfcstm-aligned state-machine model and builders
- `src/semantics/`: semantic model construction and pyfcstm-aligned normalization rules
- `src/workspace/`: import resolution and workspace graph snapshots exposing AST, semantic, and model layers
- `src/utils/`: text ranges and document abstractions

The ANTLR JavaScript runtime is generated into `src/dsl/grammar/` during build time, then mirrored into
`dist/dsl/grammar/` so the published tarball keeps a self-contained parser runtime without exposing a legacy package-root
`parser/` directory.

## Commands

```bash
# Install dependencies
npm install

# Generate parser artifacts and build dist/
npm run build

# Run unit tests with coverage, uncovered lines, and HTML/LCOV reports
npm test

# Run the Mocha suite without coverage wrapping
npm run test:unit

# Re-run the coverage report directly
npm run test:coverage

# Inspect what would be published
npm pack
npm publish --access public --dry-run
```

The package root export remains `@pyfcstm/jsfcstm`, and the package now also exposes stable subpath entry points such
as `@pyfcstm/jsfcstm/ast`, `@pyfcstm/jsfcstm/dsl`, `@pyfcstm/jsfcstm/editor`, `@pyfcstm/jsfcstm/lsp`,
`@pyfcstm/jsfcstm/model`, `@pyfcstm/jsfcstm/semantics`, `@pyfcstm/jsfcstm/workspace`, `@pyfcstm/jsfcstm/utils`, and
`@pyfcstm/jsfcstm/config`.

## Intended Package Name

The intended long-term package name is `@pyfcstm/jsfcstm`.

If the `@pyfcstm` scope is not ready yet, a temporary scope such as `@hansbug/jsfcstm` can be used during local
validation, but the repository plan treats `@pyfcstm/jsfcstm` as the preferred public identity.

## Test Standard

`jsfcstm` now treats framework-based unit tests and explicit coverage output as part of the package contract:

- unit tests run under `mocha`
- coverage runs under `c8`
- terminal coverage output includes per-file percentages and uncovered line numbers
- HTML and LCOV artifacts are written under `coverage/`
- machine-readable summary data is written to `coverage/coverage-summary.json`
- overall coverage thresholds are enforced in the default test command

## License

LGPL-3.0.
