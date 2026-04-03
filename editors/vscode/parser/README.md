# FCSTM Parser for VSCode Extension

This directory contains the ANTLR4-generated JavaScript parser artifacts for the FCSTM DSL used by the VSCode extension.

## Current Design

The VSCode extension now uses a pure JavaScript parser path:

1. The canonical grammar remains `pyfcstm/dsl/grammar/GrammarLexer.g4` and `pyfcstm/dsl/grammar/GrammarParser.g4`
2. Python and JavaScript artifacts are both generated from that same grammar pair
3. The extension loads the generated lexer/parser from this directory at runtime
4. `src/parser.ts` normalizes ANTLR diagnostics into the extension's `ParseResult` contract

This keeps the ANTLR grammar as the single source of truth while avoiding any Python dependency at extension runtime.

## Why JavaScript Generation Now Works

The original grammar used the label `function=UFUNC_NAME` in UFUNC-related rules. That label was acceptable for the Python target, but it conflicted with JavaScript code generation because `function` is a reserved word.

The grammar was updated to use the JavaScript-safe label `func_name=UFUNC_NAME`, and the Python-side listener was updated accordingly. With that change, both Python and JavaScript parser artifacts can be generated from the same grammar revision.

## Runtime Notes

- The generated files in this directory are build artifacts and are ignored by git.
- `README.md` is intentionally kept in version control to document regeneration and integration behavior.
- The extension depends on `antlr4` version `4.9.3` to match the generated parser artifacts.

## Regeneration

When the grammar changes, regenerate artifacts in this order:

1. From the project root, regenerate Python parser artifacts:
   ```bash
   make antlr_build
   ```
2. If Python-side grammar consumers need updates, fix them and verify Python tests.
3. From `editors/vscode/`, regenerate JavaScript parser artifacts:
   ```bash
   make parser
   ```
4. Rebuild and verify the extension:
   ```bash
   npm run compile
   make verify-p0.2
   ```

## Generated Files

Typical generated files in this directory include:

- `GrammarLexer.js`
- `GrammarParser.js`

These files are replaced whenever `make parser` is run.
