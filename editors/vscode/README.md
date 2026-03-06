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

The extension is planned to grow toward lightweight parser-backed editing features, but it is not positioned as a full language server.

## Features

- Syntax highlighting for FCSTM files (`.fcstm`)
- Comment toggling support (`//` and `/* */`)
- Bracket matching and auto-closing
- Code folding support
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

1. Clone the pyfcstm repository:
   ```bash
   git clone https://github.com/hansbug/pyfcstm.git
   cd pyfcstm
   ```

2. Install vsce (VSCode Extension Manager):
   ```bash
   npm install -g @vscode/vsce
   ```

3. Build using Makefile (recommended):
   ```bash
   make vscode
   ```

   Or build manually:
   ```bash
   cd editors/vscode
   vsce package --out build/
   ```

4. Install the generated `.vsix` file:
   ```bash
   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix
   ```

## Supported Syntax

The extension provides comprehensive syntax highlighting for all FCSTM language features:

### Keywords

- **Declaration**: `state`, `pseudo`, `named`, `def`, `event`
- **Lifecycle**: `enter`, `during`, `exit`, `before`, `after`
- **Modifiers**: `abstract`, `ref`, `effect`
- **Control Flow**: `if`, `and`, `or`, `not`

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

- **Integers**: `123`, `0xFF` (hex), `0b1010` (binary)
- **Floats**: `3.14`, `1e-5`, `2.5e10`
- **Booleans**: `True`, `False`, `true`, `false`
- **Strings**: `"text"`, `'text'` with escape sequences
- **Math Constants**: `pi`, `E`, `tau`

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
- **Auto-closing pairs**: Automatic closing of brackets, quotes, and comment blocks
- **Code folding**: Fold code blocks using region markers

## Offline and Compatibility Notes

- Core editor behavior should remain available without network access.
- Planned parser-backed features are intended to run locally inside the extension host.
- New capabilities should be implemented conservatively to preserve compatibility across a wide range of VSCode versions.

## Grammar-Driven Development

The extension is intended to reuse the FCSTM ANTLR grammar as the source of truth for syntax-driven capabilities.

The long-term plan is to keep generated JavaScript lexer/parser assets and their regeneration command inside [editors/vscode/](.) so that the extension remains maintainable without depending on Python or the FCSTM CLI at runtime.

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
