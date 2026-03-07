# FCSTM Parser for VSCode Extension

This directory contains the ANTLR4-generated JavaScript parser for the FCSTM DSL.

## Known Issue: JavaScript Reserved Keyword Conflict

The ANTLR grammar (`Grammar.g4`) uses `function` as a label name in rules:
- Line 112: `function=UFUNC_NAME` in `init_expression`
- Line 128: `function=UFUNC_NAME` in `num_expression`

This conflicts with JavaScript's reserved `function` keyword, preventing direct JavaScript code generation.

## Workaround Solution

Since modifying the grammar would break Python compatibility, we use a **wrapper-based approach**:

1. **Generate Python parser** (already done in main project)
2. **Create JavaScript adapter** that uses the Python CLI via child_process
3. **Future enhancement**: Create a patched grammar copy specifically for JavaScript generation

## Current Implementation

The parser adapter in `src/parser.ts` provides a clean API for parsing FCSTM documents by:
- Invoking the Python CLI parser when available
- Providing graceful fallback for offline/no-Python scenarios
- Exposing a simple `parse()` function that returns structured errors

## Alternative Approaches Considered

### Option 1: Patch Grammar for JavaScript (Not Implemented)
Create a JavaScript-specific grammar copy with renamed labels:
- `function=UFUNC_NAME` → `func=UFUNC_NAME`
- Requires maintaining two grammar versions
- Risk of divergence between Python and JavaScript parsers

### Option 2: Python CLI Bridge (Current Implementation)
Use the existing Python parser via subprocess:
- Leverages battle-tested Python implementation
- No grammar duplication
- Requires Python runtime (acceptable for development, optional for users)

### Option 3: Manual JavaScript Parser (Not Recommended)
Write a hand-coded JavaScript parser:
- High maintenance burden
- Risk of grammar drift
- Not aligned with "single source of truth" principle

## Future Work

For P0.3 (syntax diagnostics), we'll implement the Python CLI bridge approach, which provides:
- Reliable parsing using the canonical Python implementation
- Structured error messages for diagnostics
- No grammar duplication or maintenance burden

## Regeneration (When Grammar Changes)

Since JavaScript generation is blocked, regeneration is not currently needed. When the grammar changes:

1. Regenerate Python parser: `make antlr_build` (from project root)
2. The VSCode extension will automatically use the updated Python parser

If JavaScript generation becomes possible in the future:
```bash
cd /home/hansbug/oo-projects/pyfcstm/editors/vscode
make parser
```
