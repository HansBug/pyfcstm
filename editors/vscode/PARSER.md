# FCSTM Parser Integration for VSCode Extension

This document explains the parser integration for the FCSTM VSCode extension and how to regenerate parser artifacts when the grammar changes.

## Architecture Overview

The VSCode extension provides parsing capabilities for FCSTM documents to enable features like:
- Syntax diagnostics (P0.3)
- Document symbols/outline (P0.4)
- Code completion (P0.5)
- Hover documentation (P0.6)

## JavaScript Reserved Keyword Conflict

The ANTLR grammar (`pyfcstm/dsl/grammar/Grammar.g4`) uses `function` as a label name in:
- Line 112: `function=UFUNC_NAME` in `init_expression`
- Line 128: `function=UFUNC_NAME` in `num_expression`

This conflicts with JavaScript's reserved `function` keyword, preventing direct JavaScript code generation from ANTLR.

## Current Implementation: Python CLI Bridge

Since direct JavaScript parser generation is blocked, we use a **Python CLI bridge approach**:

1. **Parser Adapter** (`src/parser.ts`): Provides a clean API for parsing FCSTM documents
2. **Python CLI Integration**: Invokes the existing Python parser via subprocess
3. **Graceful Fallback**: Provides basic syntax checking when Python is not available

### Advantages of This Approach

- **Single Source of Truth**: No grammar duplication or maintenance burden
- **Battle-Tested**: Leverages the existing Python implementation
- **Structured Errors**: Returns parse errors with line/column information
- **Offline Support**: Basic syntax checking works without Python

### Requirements

For full parsing support:
- Python 3.x installed
- `pyfcstm` package installed: `pip install pyfcstm`

The extension will detect Python and pyfcstm availability automatically and fall back to basic syntax checking if unavailable.

## Grammar Regeneration Process

When the ANTLR grammar (`Grammar.g4`) changes:

### 1. Regenerate Python Parser (Required)

From the project root:

```bash
make antlr_build
```

This regenerates the Python parser used by the CLI bridge.

### 2. JavaScript Parser Generation (Currently Blocked)

JavaScript parser generation is currently blocked due to the `function` keyword conflict. If this is resolved in the future:

```bash
cd editors/vscode
make parser
```

## Future Enhancement Options

If pure JavaScript parsing becomes necessary:

### Option 1: Create JavaScript-Specific Grammar

1. Copy `Grammar.g4` to `GrammarJS.g4`
2. Rename conflicting labels:
   - `function=UFUNC_NAME` → `func=UFUNC_NAME`
3. Generate JavaScript parser from `GrammarJS.g4`
4. Maintain synchronization between grammars

**Pros**: Pure JavaScript, no Python dependency
**Cons**: Grammar duplication, maintenance burden, risk of divergence

### Option 2: Continue with Python CLI Bridge (Current)

**Pros**: Single source of truth, no duplication, battle-tested
**Cons**: Requires Python runtime for full parsing

### Option 3: Manual JavaScript Parser

**Pros**: Full control
**Cons**: High maintenance burden, risk of grammar drift

## Development Workflow

### Setting Up Development Environment

```bash
cd editors/vscode

# Install dependencies
npm install

# Build TypeScript
npm run compile

# Watch mode for development
npm run watch
```

### Testing Parser Integration

```bash
# Test parser availability
code --extensionDevelopmentPath=. test.fcstm
# Then run command: "FCSTM: Test Parser"
```

### Building Extension Package

```bash
cd editors/vscode
make package
```

This will:
1. Install npm dependencies
2. Compile TypeScript
3. Build VSIX package in `build/`

## File Structure

```
editors/vscode/
├── src/
│   ├── extension.ts       # Extension entry point
│   └── parser.ts          # Parser adapter (Python CLI bridge)
├── parser/
│   └── README.md          # Parser implementation notes
├── out/                   # Compiled JavaScript (generated)
├── node_modules/          # npm dependencies (generated)
├── package.json           # Extension manifest
├── tsconfig.json          # TypeScript configuration
├── Makefile               # Build commands
└── PARSER.md              # This file
```

## Troubleshooting

### Parser Not Available

If the extension shows "FCSTM parser is not available":

1. Check Python installation: `python3 --version`
2. Install pyfcstm: `pip install pyfcstm`
3. Verify installation: `python3 -m pyfcstm --version`

### Build Errors

If TypeScript compilation fails:

```bash
cd editors/vscode
rm -rf node_modules out
npm install
npm run compile
```

### ANTLR Generation Errors

If you attempt JavaScript generation and see the `function` conflict error, this is expected. Use the Python CLI bridge approach instead.

## References

- Main project: `/home/hansbug/oo-projects/pyfcstm`
- ANTLR grammar: `pyfcstm/dsl/grammar/Grammar.g4`
- Python parser: `pyfcstm/dsl/parse.py`
- VSCode extension roadmap: `editors/vscode/TODO.md`
