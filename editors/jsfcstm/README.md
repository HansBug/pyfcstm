# jsfcstm

`jsfcstm` is the JavaScript/TypeScript package boundary for FCSTM-related logic in this repository.

The package was introduced first as a publishable skeleton in Phase 0/1. In Phase 2, the existing parser-backed
editor core has started to move here so the VSCode extension can stay focused on host integration instead of owning
FCSTM language logic directly.

## Current Scope

At the current phase, this package provides:

- ANTLR-backed FCSTM parser runtime generated from the canonical repository grammar
- source range helpers and document abstractions
- import resolution and lightweight workspace indexing
- document symbol extraction
- completion candidate generation
- hover metadata resolution
- syntax and import diagnostics helpers
- independent TypeScript build output under `dist/`
- independent Mocha-based unit tests
- coverage reporting via `c8`, including uncovered line numbers in the terminal report
- npm pack / publish-ready package metadata

The package still does **not** yet contain the future unified AST, semantic model, workspace graph, or full language
server implementation. Those remain Phase 3+ work.

## Current Layout

`jsfcstm` now uses a layered internal structure aligned with the Python package boundary:

- `src/config/`: package metadata and future package-level configuration
- `src/dsl/`: parser entry points and generated grammar runtime
- `src/workspace/`: import resolution and workspace indexing
- `src/editor/`: completion, hover, diagnostics, and symbol extraction
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
as `@pyfcstm/jsfcstm/dsl`, `@pyfcstm/jsfcstm/editor`, `@pyfcstm/jsfcstm/workspace`, `@pyfcstm/jsfcstm/utils`, and
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
