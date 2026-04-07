# jsfcstm

`jsfcstm` is the JavaScript/TypeScript package boundary for FCSTM-related logic in this repository.

The package is being introduced before large-scale feature migration on purpose. Phase 0/1 only establishes a
publishable, testable npm package skeleton so later work can move FCSTM parser, semantics, diagnostics, language
server core, and diagram logic into a dedicated package instead of growing them directly inside the VSCode extension.

## Current Scope

At the current phase, this package provides:

- package metadata exports
- independent TypeScript build output under `dist/`
- independent unit tests
- npm pack / publish-ready package metadata

The package does **not** yet contain the real FCSTM parser, semantics, or language-server implementation. Those are
intended to move here in later phases.

## Commands

```bash
# Install dependencies
npm install

# Build dist/
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
