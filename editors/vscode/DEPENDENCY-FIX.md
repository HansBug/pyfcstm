# VSCode Extension Dependency Loading Fix

## Problem

The VSCode extension was failing to activate with the error:

```
Activating extension 'hansbug.fcstm-language-support' failed: Cannot find module 'antlr4'
Require stack:
- /home/hansbug/.vscode/extensions/hansbug.fcstm-language-support-0.1.0/out/parser.js
- /home/hansbug/.vscode/extensions/hansbug.fcstm-language-support-0.1.0/out/extension.js
```

## Root Cause

The `.vscodeignore` file was configured to exclude **all** `node_modules` from the packaged extension:

```
node_modules/**
```

This meant that when the extension was packaged into a `.vsix` file, the `antlr4` runtime dependency was not included. When VSCode tried to load the extension, the `require('antlr4')` call in `parser.ts` failed because the module was missing.

## Solution

Modified `.vscodeignore` to include an exception for the `antlr4` dependency:

```
node_modules/**
*.vsix
**/*.map

# Keep compiled output
!out/**/*.js

# CRITICAL: Include antlr4 runtime dependency
# VSCode extensions need runtime dependencies bundled
!node_modules/antlr4/**
```

The `!node_modules/antlr4/**` line creates an exception to the `node_modules/**` exclusion rule, forcing the `antlr4` module to be included in the packaged extension.

## Verification

After the fix, the packaged extension includes the `antlr4` module:

```bash
$ npm run package
$ unzip -l build/fcstm-language-support-0.1.0.vsix | grep antlr4
       39  2026-03-08 02:21   extension/node_modules/antlr4/.babelrc
      732  2026-03-08 02:21   extension/node_modules/antlr4/.project
      966  2026-03-08 02:21   extension/node_modules/antlr4/package.json
      ...
```

The extension now loads successfully:

```bash
$ code --install-extension build/fcstm-language-support-0.1.0.vsix --force
$ cd ~/.vscode/extensions/hansbug.fcstm-language-support-*/
$ node -e "const antlr4 = require('antlr4'); console.log('antlr4 loaded:', typeof antlr4.InputStream);"
antlr4 loaded: function
```

## Testing

Comprehensive tests confirm the fix works:

```bash
$ cd /home/hansbug/oo-projects/pyfcstm/editors/vscode
$ node -e "
(async () => {
    const parser = require('./out/parser.js');
    const p = parser.getParser();
    await new Promise(resolve => setTimeout(resolve, 1000));
    console.log('Parser available:', p.isAvailable());
    const result = await p.parse('state Root;');
    console.log('Parse success:', result.success);
})();
"
```

Output:
```
Parser available: true
Parse success: true
```

## Technical Details

### Why This Happens

VSCode extensions are packaged as `.vsix` files (ZIP archives) that contain only the files needed at runtime. The `.vscodeignore` file controls which files are included/excluded during packaging.

By default, most VSCode extension templates exclude `node_modules/**` because:

1. **Size reduction**: Most extensions use bundlers (webpack, esbuild) to bundle dependencies into compiled output
2. **Security**: Avoids accidentally including dev dependencies or sensitive files
3. **Performance**: Smaller packages load faster

However, this extension uses TypeScript compilation without bundling, so runtime dependencies must be explicitly included.

### Alternative Solutions

**Option 1: Use a bundler (recommended for production)**

Configure webpack or esbuild to bundle all dependencies into a single output file:

```javascript
// webpack.config.js
module.exports = {
  target: 'node',
  entry: './src/extension.ts',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'extension.js',
    libraryTarget: 'commonjs2'
  },
  externals: {
    vscode: 'commonjs vscode' // Don't bundle vscode module
  }
};
```

Benefits:
- Smaller package size (only includes used code)
- Faster loading (single file vs many files)
- No dependency conflicts

**Option 2: Include all production dependencies**

Modify `.vscodeignore` to include all production dependencies:

```
node_modules/**
!node_modules/antlr4/**
# Add other runtime dependencies as needed
```

Benefits:
- Simple configuration
- Works with existing build setup
- Easy to debug (source files preserved)

**Current approach**: Option 2 (include specific dependencies)

## Files Modified

1. **`.vscodeignore`**: Added exception for `antlr4` module
2. **`DEBUG-GUIDE.md`**: Added troubleshooting section for this issue

## Related Issues

- VSCode Extension API: https://code.visualstudio.com/api/working-with-extensions/bundling-extension
- ANTLR4 JavaScript Runtime: https://github.com/antlr/antlr4/tree/master/runtime/JavaScript

## Future Improvements

Consider migrating to a bundler (webpack/esbuild) for better performance and smaller package size. This would eliminate the need for `.vscodeignore` exceptions and provide better tree-shaking.
