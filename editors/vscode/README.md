# FCSTM Language Support for VSCode

Syntax highlighting support for FCSTM (Finite State Machine) DSL in Visual Studio Code.

## Features

- Syntax highlighting for FCSTM files (`.fcstm`)
- Comment toggling support (`//` and `/* */`)
- Bracket matching and auto-closing
- Code folding support
- Full language support based on ANTLR grammar

## Installation

### From VSIX Package

1. Download the `.vsix` file from the releases page
2. Open VSCode
3. Go to Extensions view (`Ctrl+Shift+X` or `Cmd+Shift+X`)
4. Click the `...` menu at the top of the Extensions view
5. Select "Install from VSIX..."
6. Choose the downloaded `.vsix` file
7. Reload VSCode

### From Source

1. Clone the pyfcstm repository:
   ```bash
   git clone https://github.com/hansbug/pyfcstm.git
   cd pyfcstm
   ```

2. Copy the extension to your VSCode extensions folder:
   ```bash
   # Linux/macOS
   cp -r editors/vscode ~/.vscode/extensions/fcstm-language-support-0.1.0/

   # Windows
   xcopy /E /I editors\vscode %USERPROFILE%\.vscode\extensions\fcstm-language-support-0.1.0\
   ```

3. Reload VSCode

### Building from Source

To build a `.vsix` package:

1. Install vsce (VSCode Extension Manager):
   ```bash
   npm install -g @vscode/vsce
   ```

2. Navigate to the extension directory:
   ```bash
   cd editors/vscode
   ```

3. Package the extension:
   ```bash
   vsce package
   ```

4. Install the generated `.vsix` file:
   ```bash
   code --install-extension fcstm-language-support-0.1.0.vsix
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

## Related Projects

- [pyfcstm](https://github.com/hansbug/pyfcstm) - FCSTM DSL parser and code generator
- [FCSTM Documentation](https://pyfcstm.readthedocs.io/) - Complete language reference

## Development

The syntax highlighting is based on the TextMate grammar format and is synchronized with the Pygments lexer implementation in the pyfcstm project.

To contribute or modify the grammar:

1. Edit `syntaxes/fcstm.tmLanguage.json`
2. Test your changes by reloading VSCode (`Ctrl+R` or `Cmd+R` in Extension Development Host)
3. Run validation: `python editors/validate.py` in the pyfcstm repository
4. Submit a pull request

## License

LGPL-3.0

## Support

For issues, questions, or contributions, please visit the [pyfcstm repository](https://github.com/hansbug/pyfcstm).
