# FCSTM Language Support for JetBrains IDEs

Syntax highlighting support for FCSTM (Finite State Machine) DSL in JetBrains IDEs (IntelliJ IDEA, PyCharm, WebStorm, CLion, etc.)

## Installation

### Manual Installation

1. Locate your IDE configuration directory:
   - **Linux**: `~/.config/JetBrains/<Product><Version>/filetypes/`
   - **macOS**: `~/Library/Application Support/JetBrains/<Product><Version>/filetypes/`
   - **Windows**: `%APPDATA%\JetBrains\<Product><Version>\filetypes\`

2. Copy `fcstm.xml` to the `filetypes` directory

3. Restart your IDE

### Alternative: Import via IDE

1. Open your JetBrains IDE
2. Go to **Settings/Preferences** → **Editor** → **File Types**
3. Click the **+** button to add a new file type
4. Import the `fcstm.xml` file or manually configure:
   - Name: `FCSTM`
   - Line comment: `//`
   - Block comment start: `/*`
   - Block comment end: `*/`
   - Add file pattern: `*.fcstm`

## Supported Features

- Syntax highlighting for keywords, operators, and literals
- Comment toggling (`Ctrl+/` or `Cmd+/`)
- Block comment support (`Ctrl+Shift+/` or `Cmd+Shift+/`)
- Bracket matching
- String escape sequence highlighting
- Number literal highlighting (hex, float, integer)

## Supported Syntax

- Variable definitions (`def int`, `def float`)
- State definitions (`state`, `pseudo state`, `named`)
- Transitions (`->`, `::`, `:`, `!`)
- Lifecycle actions (`enter`, `during`, `exit`, `before`, `after`)
- Aspect-oriented actions (`>>`)
- Guard conditions and effects (`if`, `effect`)
- Expressions (arithmetic, bitwise, logical, conditional)
- Built-in functions (`sin`, `cos`, `sqrt`, etc.)
- Comments (`//`, `/* */`, `#`)

## Example

```fcstm
def int counter = 0;

state TrafficLight {
    state Red {
        enter { counter = 0; }
        during { counter = counter + 1; }
    }

    state Green;

    [*] -> Red;
    Red -> Green :: Change;
}
```

## Limitations

The JetBrains file type system provides basic syntax highlighting but does not support:
- Semantic highlighting
- Code completion
- Error checking
- Refactoring

For advanced IDE features, consider using the VSCode extension or contributing a full JetBrains plugin.

## Related Projects

- [pyfcstm](https://github.com/hansbug/pyfcstm) - FCSTM DSL parser and code generator

## License

LGPL-3.0
