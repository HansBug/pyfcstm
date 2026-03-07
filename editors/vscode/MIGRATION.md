# Quick Migration Guide

## TL;DR

The extension now uses **esbuild** to create a single bundled `dist/extension.js` file. All dependencies are included, no more loading issues.

## What You Need to Know

### Building
```bash
# Before
make build  # → out/*.js (multiple files)

# After
make build  # → dist/extension.js (single bundle)
```

### Testing
```bash
# Still works the same
make verify  # All 167 tests pass
```

### Packaging
```bash
# Still works the same
make package  # Creates VSIX in build/
```

## Key Changes

1. **Main entry point**: `package.json` now points to `dist/extension.js`
2. **Bundle size**: 246KB (includes antlr4 + ANTLR-generated parser + sources)
3. **No dependency issues**: Everything bundled together (including GrammarLexer, GrammarParser, GrammarVisitor)
4. **Faster builds**: ~77ms with esbuild vs ~2s with tsc

## For Development

```bash
# Install dependencies (first time)
npm install

# Full build
make all

# Development build with sourcemaps
make build-dev

# Watch mode
npm run watch

# Clean everything
make clean
```

## Verification

All verification scripts still work:
- `make verify-p0.2` - Parser integration (32 tests)
- `make verify-p0.3` - Syntax diagnostics (35 tests)
- `make verify-p0.4` - Document symbols (35 tests)
- `make verify-p0.5` - Completion support (30 tests)
- `make verify-p0.6` - Hover documentation (35 tests)
- `make verify` - All tests (167 total)

## Troubleshooting

**Q: Extension not loading?**
A: Run `make clean && make all` to rebuild everything.

**Q: Verification tests failing?**
A: Make sure parser is generated: `make parser`

**Q: Want to see bundle contents?**
A: Check the bundle analysis output when running `make build`

## More Details

See [BUILD-IMPROVEMENTS.md](BUILD-IMPROVEMENTS.md) for complete documentation.
