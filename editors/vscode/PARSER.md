# FCSTM Parser Integration for VSCode Extension

This document explains the parser integration for the FCSTM VSCode extension and how to regenerate parser artifacts when the grammar changes.

## Architecture Overview

The VSCode extension provides parsing capabilities for FCSTM documents to enable features like:
- Syntax diagnostics (P0.3)
- Document symbols/outline (P0.4)
- Code completion (P0.5)
- Hover documentation (P0.6)

## Current Implementation: Pure JavaScript ANTLR Parser

The extension now uses a pure JavaScript parser path built directly from the canonical ANTLR grammar:

1. **Canonical Grammar**: `pyfcstm/dsl/grammar/Grammar.g4`
2. **Generated JS Artifacts**: `editors/vscode/parser/GrammarLexer.js`, `GrammarParser.js`, `GrammarVisitor.js`
3. **Parser Adapter**: `src/parser.ts` loads the generated artifacts and exposes a stable `parse()` API
4. **Diagnostic Normalization**: `src/parser.ts` converts ANTLR JS syntax errors into the extension's `ParseResult` structure

This keeps the grammar as the single source of truth while satisfying the extension's requirement to avoid Python or CLI dependencies at runtime.

## Why the Earlier Conflict Happened

The original grammar used `function=UFUNC_NAME` as a labeled element in UFUNC-related rules. That label is acceptable for Python code generation, but it conflicts with JavaScript because `function` is a reserved word.

The grammar was updated to use `func_name=UFUNC_NAME` instead. After regenerating artifacts:

- Python parse-tree consumers were updated to use `ctx.func_name`
- JavaScript parser artifacts could be generated successfully
- Both Python and VSCode now consume parser artifacts derived from the same grammar revision

## Runtime Requirements

For extension-side parsing support:
- No Python installation is required
- No `pyfcstm` CLI invocation is required
- The extension depends on `antlr4` version `4.9.3`, matching the ANTLR tool/runtime used for generation

## Grammar Regeneration Process

When `Grammar.g4` changes, regenerate artifacts in this order.

### 1. Regenerate Python Parser

From the project root:

```bash
make antlr_build
```

If the grammar change affects generated accessor names or parse-tree structure, update Python-side consumers and run Python verification before continuing.

### 2. Verify Python Side

From the project root, run the relevant tests and then the full suite:

```bash
pytest test/dsl/test_stages.py
make unittest
```

### 3. Regenerate JavaScript Parser

From `editors/vscode`:

```bash
make parser
```

### 4. Rebuild and Verify the Extension

```bash
npm run compile
make verify-p0.2
```

## Development Workflow

### Setting Up Development Environment

```bash
cd editors/vscode

# Install dependencies
npm install

# Generate parser artifacts
make parser

# Build TypeScript
npm run compile

# Watch mode for development
npm run watch
```

### Testing Parser Integration

```bash
cd editors/vscode
make verify-p0.2
```

This verifies the parser adapter against a coverage-style checkpoint suite for valid and invalid FCSTM inputs.

### Building Extension Package

```bash
cd editors/vscode
make package
```

This will:
1. Install npm dependencies
2. Regenerate parser artifacts
3. Compile TypeScript
4. Build a VSIX package in `build/`

## File Structure

```
editors/vscode/
├── src/
│   ├── extension.ts       # Extension entry point
│   └── parser.ts          # Pure JS parser adapter
├── parser/
│   ├── GrammarLexer.js    # Generated lexer artifact
│   ├── GrammarParser.js   # Generated parser artifact
│   ├── GrammarVisitor.js  # Generated visitor artifact
│   └── README.md          # Parser regeneration notes
├── out/                   # Compiled JavaScript (generated)
├── node_modules/          # npm dependencies (generated)
├── package.json           # Extension manifest
├── tsconfig.json          # TypeScript configuration
├── Makefile               # Build commands
└── PARSER.md              # This file
```

## Troubleshooting

### Parser Runtime Not Available

If the extension shows that the parser runtime is unavailable:

1. Regenerate parser artifacts with `make parser`
2. Rebuild the extension with `npm run compile`
3. Ensure `parser/GrammarLexer.js` and `parser/GrammarParser.js` exist
4. Ensure `antlr4` is installed at version `4.9.3`

### Build Errors

If TypeScript compilation fails:

```bash
cd editors/vscode
rm -rf node_modules out
npm install
npm run compile
```

### ANTLR Runtime Mismatch

If the generated parser fails with runtime-constructor errors such as `PredictionContextCache is not a constructor`, check that the installed `antlr4` package version matches the generation toolchain. The extension currently expects:

```bash
npm ls antlr4
```

and it should resolve to `4.9.3`.

## References

- Main project: `/home/hansbug/oo-projects/pyfcstm`
- Canonical grammar: `pyfcstm/dsl/grammar/Grammar.g4`
- Python parser entrypoints: `pyfcstm/dsl/parse.py`
- VSCode extension roadmap: `editors/vscode/TODO.md`
