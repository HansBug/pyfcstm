# FCSTM Language Support for VSCode

Syntax highlighting support for FCSTM (Finite State Machine) DSL in Visual Studio Code.

## Features

- Syntax highlighting for FCSTM files (`.fcstm`)
- Comment toggling support
- Bracket matching and auto-closing
- Code folding

## Installation

### From Source

1. Copy the `editors/vscode` directory to your VSCode extensions folder:
   - **Linux/macOS**: `~/.vscode/extensions/fcstm-language-support/`
   - **Windows**: `%USERPROFILE%\.vscode\extensions\fcstm-language-support\`

2. Reload VSCode

### From VSIX (Future)

Once published to the VSCode Marketplace, you can install directly from the Extensions view.

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

## Related Projects

- [pyfcstm](https://github.com/hansbug/pyfcstm) - FCSTM DSL parser and code generator

## License

LGPL-3.0
