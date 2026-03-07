# VSCode Extension Dependency Fix - Summary

## Issue
The VSCode extension failed to load with error: `Cannot find module 'antlr4'`

## Root Cause
The `.vscodeignore` file excluded all `node_modules`, preventing the `antlr4` runtime dependency from being packaged in the `.vsix` file.

## Solution
Modified `.vscodeignore` to include an exception for the `antlr4` module:

```diff
 node_modules/**
+
+# CRITICAL: Include antlr4 runtime dependency
+# VSCode extensions need runtime dependencies bundled
+!node_modules/antlr4/**
```

## Files Changed

1. **`.vscodeignore`** - Added exception for `antlr4` module
2. **`DEBUG-GUIDE.md`** - Added troubleshooting section
3. **`DEPENDENCY-FIX.md`** - Detailed technical documentation
4. **`Makefile`** - Added verification to `package` target
5. **`scripts/test-e2e.js`** - New end-to-end test script

## Verification

### Package Contents
```bash
$ npm run package
$ unzip -l build/fcstm-language-support-0.1.0.vsix | grep antlr4
# Shows 53 antlr4 files included
```

### Runtime Test
```bash
$ code --install-extension build/fcstm-language-support-0.1.0.vsix --force
$ cd ~/.vscode/extensions/hansbug.fcstm-language-support-*/
$ node -e "const antlr4 = require('antlr4'); console.log('OK');"
OK
```

### E2E Test
```bash
$ make test-e2e
=== FCSTM Extension E2E Test ===
✓ Package found
✓ antlr4 included (53 files)
✓ Parser files included (7 files)
✓ Compiled output included (6 files)
✓ Parser functionality verified
✓ Package size: 216.73 KB
=== All Tests Passed ===
```

## Testing Commands

```bash
# Build and test everything
make test-e2e

# Just build package
make package

# Install extension
code --install-extension build/fcstm-language-support-0.1.0.vsix --force

# Reload VSCode window
# Press Ctrl+Shift+P → "Developer: Reload Window"

# Check extension logs
# Press Ctrl+Shift+P → "Developer: Toggle Developer Tools" → Console tab
```

## Expected Console Output

After reloading VSCode with a `.fcstm` file open:

```
[FCSTM Extension] Starting activation...
[FCSTM Extension] Extension path: /home/.../.vscode/extensions/hansbug.fcstm-language-support-0.1.0
[FCSTM Extension] Parser instance created
[FCSTM Parser] Starting to load parser modules...
[FCSTM Parser] Parser directory: /home/.../parser
[FCSTM Parser] Lexer exists: true
[FCSTM Parser] Parser exists: true
[FCSTM Parser] Parser modules loaded successfully!
[FCSTM Extension] FCSTM Language Support extension is now active
```

## Package Size

- **Before fix**: Extension would fail to load (missing dependency)
- **After fix**: 216.73 KB (includes antlr4 runtime)

## Future Improvements

Consider using a bundler (webpack/esbuild) to:
- Reduce package size through tree-shaking
- Bundle all dependencies into a single file
- Improve loading performance
- Eliminate need for `.vscodeignore` exceptions

## Related Documentation

- **DEPENDENCY-FIX.md** - Detailed technical explanation
- **DEBUG-GUIDE.md** - Troubleshooting guide
- **TESTING-GUIDE.md** - Testing procedures
- **README.md** - User-facing documentation

## Status

✅ **FIXED** - Extension now loads successfully in VSCode with all parser features working.
