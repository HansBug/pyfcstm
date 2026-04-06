# FCSTM Language Support for VSCode

Syntax highlighting support for FCSTM (Finite State Machine) DSL in Visual Studio Code.

## Project Positioning

This extension is intended to remain a lightweight, offline-capable VSCode extension for FCSTM authoring.

The main design principles are:

- The extension should remain language-neutral at runtime.
  - It may use JavaScript because that is native to the VSCode extension host.
  - It must not depend on Python, Java, or other external runtimes at extension runtime.
- The extension should remain compatible with a wide range of VSCode versions, including older and newer releases where practical.
- The extension should work fully offline for its core editor features.
- The FCSTM ANTLR grammar should remain the main source of truth for syntax-driven capabilities.
- Parser-related assets should be maintainable from within [editors/vscode/](.) through a local regeneration command.

## Current Scope

The extension currently provides:

- Syntax highlighting for FCSTM files (`.fcstm`)
- Comment toggling support (`//` and `/* */`)
- Bracket matching and auto-closing
- Code folding support through language configuration
- Authoring snippets for common FCSTM constructs
- **Syntax diagnostics** - Real-time error detection and reporting
- **Document symbols** - Outline view and breadcrumb navigation for states, variables, and events
- **Code completion** - IntelliSense for keywords, built-in functions, constants, and document symbols
- **Hover documentation** - Contextual help for FCSTM constructs

The extension is planned to grow toward lightweight parser-backed editing features, but it is not positioned as a full language server.

## Features

- **Syntax highlighting** for FCSTM files (`.fcstm`)
- **Comment toggling** support (`//` and `/* */`)
- **Bracket matching** and auto-closing
- **Code folding** support
- **Authoring snippets** for common FCSTM constructs
- **Syntax diagnostics** - Real-time error detection with clear error messages in the Problems panel
- **Document symbols** - Navigate your state machine structure via the Outline view
  - Variables (`def int`, `def float`)
  - States (leaf and composite)
  - Pseudo states
  - Events
  - Nested state hierarchies
- **Code completion** - IntelliSense support for:
  - Keywords (`state`, `def`, `event`, `enter`, `during`, `exit`, etc.)
  - Built-in constants (`pi`, `E`, `tau`, `true`, `false`)
  - Built-in functions (`sin`, `cos`, `sqrt`, `abs`, `log`, etc.)
  - Document-local symbols (variables, states, events)
  - Filtered in comments and strings
- **Hover documentation** - Contextual help for:
  - Event scoping operators (`::`, `:`, `/`)
  - Pseudo-state marker (`[*]`)
  - Keywords (`pseudo`, `effect`, `abstract`, `ref`, `named`, etc.)
  - Lifecycle aspects (`during before/after`, `>> during before/after`)
- Grammar-aligned language package foundation for future parser-backed editor features

## Installation

### From VSIX Package

1. Download the `.vsix` file from the [GitHub releases page](https://github.com/hansbug/pyfcstm/releases)
2. Install using command line:
   ```bash
   code --install-extension fcstm-language-support-0.1.0.vsix
   ```
   Or install via VSCode UI:
   - Open VSCode
   - Go to Extensions view (`Ctrl+Shift+X` or `Cmd+Shift+X`)
   - Click the `...` menu at the top of the Extensions view
   - Select "Install from VSIX..."
   - Choose the downloaded `.vsix` file
3. Reload VSCode

### Building from Source

If you want to build the extension from source:

#### Prerequisites

- **Node.js** (v20 or later) and npm
- **Java** (JDK 11 or later) - required for ANTLR parser generation
- **Python** (3.8 or later) - required for ANTLR setup
- **Git** - for cloning the repository

#### Build Steps

1. Clone the pyfcstm repository:
   ```bash
   git clone https://github.com/hansbug/pyfcstm.git
   cd pyfcstm
   ```

2. Download ANTLR (first-time setup):
   ```bash
   make antlr
   ```

3. Build the extension using the root Makefile (recommended):
   ```bash
   make vscode
   ```

   This command will:
   - Install npm dependencies
   - Copy TextMate grammar files
   - Generate JavaScript parser from ANTLR grammar
   - Bundle extension with esbuild (all-in-one)
   - Package the extension as `.vsix`

   The built extension will be available at `editors/vscode/build/fcstm-language-support-0.1.0.vsix`

4. Install the generated `.vsix` file:
   ```bash
   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix
   ```

#### Manual Build (from VSCode directory)

If you prefer to build from the VSCode extension directory:

```bash
cd editors/vscode

# Install dependencies
npm install

# Copy TextMate grammar
make syntaxes

# Generate JavaScript parser
make parser

# Bundle extension
make build

# Package extension
make package
```

#### Development Workflow

For active development:

```bash
cd editors/vscode

# Watch mode for development (with sourcemaps)
npm run watch

# Or build manually
make build-dev

# In another terminal, verify features
make verify
```

#### Regenerating Parser After Grammar Changes

When the ANTLR grammar pair (`pyfcstm/dsl/grammar/GrammarLexer.g4` and `pyfcstm/dsl/grammar/GrammarParser.g4`) changes:

1. From project root, regenerate Python parser:
   ```bash
   make antlr_build
   ```

2. Verify Python tests pass:
   ```bash
   make unittest
   ```

3. Regenerate JavaScript parser for VSCode:
   ```bash
   cd editors/vscode
   make parser
   ```

4. Rebuild and verify:
   ```bash
   make build
   make verify
   ```

## Testing and Verification

The extension includes comprehensive test suites to validate all parser-backed features:

### Verification Commands

```bash
cd editors/vscode

# Verify P0.2 - Parser Integration (32 tests)
make verify-p0.2

# Verify P0.3 - Syntax Diagnostics (35 tests)
make verify-p0.3

# Verify P0.4 - Document Symbols (35 tests)
make verify-p0.4

# Verify P0.5 - Code Completion (31 tests)
make verify-p0.5

# Verify P0.6 - Hover Documentation (36 tests)
make verify-p0.6

# Verify P1.B - Language Configuration Reinforcement
make verify-p1.b

# Run all verification tests (including bundle checks)
make verify
```

### Test Coverage

- **P0.2 Parser Integration**: 32 tests covering valid/invalid FCSTM inputs
- **P0.3 Syntax Diagnostics**: 35 tests covering error detection and messages
- **P0.4 Document Symbols**: 35 tests covering symbol extraction and hierarchies
- **P0.5 Code Completion**: 31 tests covering keywords, constants, functions, and document symbols
- **P0.6 Hover Documentation**: 36 tests covering operators, keywords, and lifecycle aspects
- **E2E Bundle Tests**: Comprehensive tests validating bundled extension functionality

All tests use real FCSTM code and provide detailed error reporting with emoji indicators (✅/❌) for easy debugging.

## Supported Syntax

The extension provides grammar-aligned syntax highlighting for the FCSTM language features supported by the repository grammar and shipped editor assets:

### Keywords

- **Declaration**: `state`, `pseudo`, `named`, `def`, `event`
- **Lifecycle**: `enter`, `during`, `exit`, `before`, `after`
- **Modifiers**: `abstract`, `ref`, `effect`
- **Control Flow**: `if`, `else`, `and`, `or`, `not`

### Types

- `int`, `float`

### Operators

- **Transitions**: `->`, `>>`, `::`, `:`, `/`, `!`
- **Arithmetic**: `+`, `-`, `*`, `/`, `%`, `**`
- **Bitwise**: `&`, `|`, `^`, `~`, `<<`
- **Comparison**: `<`, `>`, `<=`, `>=`, `==`, `!=`
- **Logical**: `&&`, `||`, `!`
- **Ternary**: `?`, `:`

### Literals

- **Integers**: `123`, `0xFF` (hex)
- **Floats**: `3.14`, `1e-5`, `2.5e10`
- **Booleans**: `True`, `False`, `true`, `false`
- **Strings**: `"text"`, `'text'` with escape sequences
- **Math Constants**: `pi`, `E`, `tau`

### Declaration Highlighting

The grammar gives more specific scopes to declaration forms so themes can distinguish declared names more clearly:

- Variable definitions: `def int counter = 0;`
- Pseudo state declarations: `pseudo state Junction;`
- State declarations: `state Running { ... }`
- Event declarations: `event Start;`

### Built-in Functions

- **Trigonometric**: `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`
- **Mathematical**: `sqrt`, `cbrt`, `exp`, `log`, `log10`, `log2`, `log1p`, `abs`, `ceil`, `floor`, `round`, `trunc`, `sign`

### Special Symbols

- **Pseudo-state**: `[*]`
- **Comments**: `//` (line), `/* */` (block), `#` (Python-style)

## Example

```fcstm
def int counter = 0;
def float temperature = 25.5;

state TrafficLight {
    >> during before {
        counter = counter + 1;
    }

    state Red {
        enter {
            counter = 0;
        }

        during {
            counter = (counter < 100) ? counter + 1 : 0;
        }
    }

    state Yellow;
    state Green;

    [*] -> Red;
    Red -> Green : if [counter >= 10 && temperature < 50.0];
    Green -> Yellow :: Change effect {
        counter = 0;
    }
    Yellow -> Red;
}
```

## Customizing Colors

Colors are controlled by your VSCode theme. The extension assigns semantic scopes to different syntax elements, and your theme determines the colors.

To customize colors, add token color customizations to your `settings.json`:

```json
{
  "editor.tokenColorCustomizations": {
    "textMateRules": [
      {
        "scope": "keyword.control.fcstm",
        "settings": {
          "foreground": "#FF6B6B",
          "fontStyle": "bold"
        }
      },
      {
        "scope": "keyword.operator.transition.fcstm",
        "settings": {
          "foreground": "#51CF66"
        }
      }
    ]
  }
}
```

## Language Configuration

The extension provides:

- **Comment toggling**: Use `Ctrl+/` (or `Cmd+/`) to toggle line comments
- **Block comments**: Use `Shift+Alt+A` (or `Shift+Option+A`) for block comments
- **Auto-closing pairs**: Automatic closing of braces, brackets, parentheses, quotes, and block comments
- **Selection wrapping**: Wrap selected text with braces, brackets, parentheses, or quotes
- **FCSTM-aware token selection**: Word navigation and double-click selection cover identifiers, dotted references, absolute events, local event names, pseudo-state tokens, and numeric literals
- **Code folding**: Fold code blocks using region markers
- **Snippets**: Expand common FCSTM templates such as states, transitions, events, and lifecycle blocks

## Snippets

The extension includes snippets for the most common FCSTM authoring patterns.

Representative snippet prefixes include:

- `defi`, `deff`
- `state`, `stateb`, `pstate`, `staten`
- `event`, `eventn`
- `init`, `trans`, `transe`, `transg`, `transeff`, `transfull`
- `enter`, `during`, `exit`, `dbefore`, `dafter`
- `globalbefore`, `globalafter`
- `eabstract`, `eref`

These snippets are intended to reduce repetitive boilerplate while keeping the extension fully offline-capable.

## Offline and Compatibility Notes

- Core editor behavior should remain available without network access.
- Planned parser-backed features are intended to run locally inside the extension host.
- New capabilities should be implemented conservatively to preserve compatibility across a wide range of VSCode versions.

## Grammar-Driven Development

The extension is intended to reuse the FCSTM ANTLR grammar as the source of truth for syntax-driven capabilities.

The long-term plan is to keep generated JavaScript lexer/parser assets and their regeneration command inside [editors/vscode/](.) so that the extension remains maintainable without depending on Python or the FCSTM CLI at runtime.

## Extension Architecture

### Parser Integration

The extension uses a pure JavaScript ANTLR parser generated from the canonical FCSTM grammar:

- **Grammar Source**: `pyfcstm/dsl/grammar/GrammarLexer.g4` and `pyfcstm/dsl/grammar/GrammarParser.g4` (single source of truth)
- **Generated Artifacts**: `editors/vscode/parser/` (GrammarLexer.js, GrammarParser.js)
- **Parser Adapter**: `src/parser.ts` (loads generated artifacts and normalizes diagnostics)
- **Runtime**: `antlr4` version 4.9.3 (exact match with generation toolchain)

The parser provides:
- Syntax validation with detailed error messages
- Real-time diagnostics in the Problems panel and inline squiggles
- Document symbols for outline navigation
- 0-based line/column positions for VSCode diagnostics
- Error message normalization matching Python parser behavior
- No Python or external runtime dependencies

### File Structure

```
editors/vscode/
├── src/
│   ├── extension.ts       # Extension entry point
│   ├── parser.ts          # Pure JS parser adapter
│   ├── diagnostics.ts     # Syntax diagnostics provider
│   ├── symbols.ts         # Document symbols provider
│   ├── completion.ts      # Code completion provider
│   └── hover.ts           # Hover documentation provider
├── parser/
│   ├── GrammarLexer.js    # Generated lexer (from ANTLR)
│   ├── GrammarParser.js   # Generated parser (from ANTLR)
│   ├── package.json       # Parser metadata
│   └── README.md          # Parser regeneration notes
├── syntaxes/
│   └── fcstm.tmLanguage.json  # TextMate grammar (copied from editors/)
├── snippets/
│   └── fcstm.code-snippets    # Code snippets
├── scripts/
│   ├── verify-p0.2.js     # Parser verification (32 tests)
│   ├── verify-p0.3.js     # Diagnostics verification (35 tests)
│   ├── verify-p0.4.js     # Symbols verification (35 tests)
│   ├── verify-p0.5.js     # Completion verification (30 tests)
│   ├── verify-p0.6.js     # Hover verification (35 tests)
│   ├── verify-p1.b.js     # Language configuration verification
│   └── test-e2e.js        # End-to-end bundle tests
├── dist/                  # Bundled extension (generated)
│   └── extension.js       # Single 246KB bundle
├── out/                   # TypeScript compilation (for verification)
├── build/                 # VSIX packages (generated)
├── esbuild.config.js      # esbuild bundling configuration
├── package.json           # Extension manifest
├── tsconfig.json          # TypeScript configuration
├── Makefile               # Build commands
└── README.md              # This file
```

### Build Pipeline

The extension uses **esbuild** for bundling, creating a single all-in-one `extension.js` file:

1. **Install Dependencies** (`npm install`)
   - Installs TypeScript, ANTLR runtime, esbuild, and build tools

2. **Copy TextMate Grammar** (`make syntaxes`)
   - Copies `editors/fcstm.tmLanguage.json` to `syntaxes/`

3. **Generate JavaScript Parser** (`make parser`)
   - Uses ANTLR 4.9.3 to generate JS artifacts from `GrammarLexer.g4` and `GrammarParser.g4`
   - Outputs to `parser/` directory

4. **Bundle Extension** (`make build`)
   - Uses esbuild to bundle all sources and dependencies into single file
   - Outputs to `dist/extension.js` (246KB)
   - Includes: ANTLR-generated parser (~104KB) + antlr4 runtime (~80KB) + sources (~20KB)
   - Build time: ~77ms (26x faster than TypeScript compiler)

5. **Package Extension** (`npm run package`)
   - Creates `.vsix` file in `build/` directory (83KB)

### Build Architecture

**All-in-One Bundle:**
- Single `dist/extension.js` file contains all dependencies
- ANTLR-generated lexer/parser files (GrammarLexer, GrammarParser) bundled
- antlr4 runtime library bundled
- All extension sources bundled
- No runtime dependency loading issues
- Faster extension activation

**Verification:**
- Separate TypeScript compilation (`make build-tsc`) for verification scripts
- Verification scripts use `out/` directory
- Extension uses bundled `dist/extension.js`
- All 167 tests pass (P0.2-P0.6)

### Grammar Synchronization

Both Python and JavaScript parsers are generated from the same canonical grammar pair:

- **Python Target**: `pyfcstm/dsl/grammar/` (for CLI and library)
- **JavaScript Target**: `editors/vscode/parser/` (for VSCode extension)

The grammar uses JavaScript-safe labels (e.g., `func_name` instead of `function`) to ensure cross-target compatibility.

## Related Projects

- [pyfcstm](https://github.com/hansbug/pyfcstm) - FCSTM DSL parser and code generator
- [FCSTM Documentation](https://pyfcstm.readthedocs.io/) - Complete language reference

## Development

The syntax highlighting is based on the TextMate grammar format and is synchronized with the FCSTM language definition in the repository.

When parser-backed capabilities are introduced, grammar-derived lexer/parser assets and their regeneration command should remain maintained under [editors/vscode/](.).

## License

LGPL-3.0

## Support

For issues, questions, or contributions, please visit the [pyfcstm repository](https://github.com/hansbug/pyfcstm).
