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
- independent unit tests
- npm pack / publish-ready package metadata

The package still does **not** yet contain the future unified AST, semantic model, workspace graph, or full language
server implementation. Those remain Phase 3+ work.

## Commands

```bash
# Install dependencies
npm install

# Generate parser artifacts and build dist/
npm run build

# Run unit tests
npm test

# Inspect what would be published
npm pack
npm publish --access public --dry-run
```

## Intended Package Name

The intended long-term package name is `@pyfcstm/jsfcstm`.

If the `@pyfcstm` scope is not ready yet, a temporary scope such as `@hansbug/jsfcstm` can be used during local
validation, but the repository plan treats `@pyfcstm/jsfcstm` as the preferred public identity.

## License

LGPL-3.0.
